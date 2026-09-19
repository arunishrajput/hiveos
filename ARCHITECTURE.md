# ARCHITECTURE.md — HiveOS

Intended system design and the decisions behind it. Interfaces that must not drift live in `CONTRACT.md`.

---

## System overview

```
┌──────────────┐
│   Amplify    │  React + Vite, static hosting, public HTTPS URL
│   Hosting    │
└──────┬───────┘
       │  browser loads app, opens wss://
       ▼
┌──────────────────┐        ┌─────────────────────────────────────┐
│  API Gateway     │        │           Router Lambda             │
│  WebSocket API   │◄──────►│  $connect / $disconnect / $default  │
│                  │        │  desk claim (atomic)                │
│  $connect        │        │  hire / dismiss agents              │
│  $disconnect     │        │  enqueue + queue position           │
│  $default        │        │  broadcast + GoneException handler  │
│                  │        └───────────┬─────────────────┬───────┘
└──────────────────┘                    │                 │
       ▲                                ▼                 ▼
       │                        ┌──────────────┐   ┌─────────────┐
       │ post_to_connection     │  DynamoDB    │   │     SQS     │
       │                        │ single table │   │ agent-tasks │
       │                        │              │   │   + DLQ     │
       │                        │ team meta    │   └──────┬──────┘
       │                        │ connections  │          │
       │                        │ agent roster │          ▼
       │                        │ queue items  │   ┌──────────────────┐
       │                        │ team memory  │◄──┤  Agent Runner    │
       │                        │ task ledger  │   │  Lambda          │
       │                        └──────────────┘   │                  │
       │                                           │                  │
       └───────────────────────────────────────────┤  load memory     │
                                                   │  call the model  │
                                                   │  token accounting│
                                                   │  release the desk│
                                                   │  dispatch next   │
                                                   │  or hand off     │
                                                   └────────┬─────────┘
                                                            ▼ HTTPS
                                                   ┌──────────────────┐
                                                   │ Groq             │
                                                   │ gpt-oss-120b     │
                                                   │ (the only hop    │
                                                   │  that is not AWS)│
                                                   └──────────────────┘
```

---

## Components

| Service | Role | Why this service |
|---|---|---|
| **API Gateway WebSocket** | Persistent browser connections; routes `$connect`, `$disconnect`, `$default` | The only AWS service providing persistent WebSocket connections with a serverless backend. No alternative. |
| **Router Lambda** | Connection lifecycle, message routing, atomic desk claiming, hiring and dismissing agents, enqueue, broadcast, GoneException handling | Serverless, scales to zero, direct DynamoDB and SQS access |
| **DynamoDB** (single table) | All state: team metadata, connection IDs, the agent roster, queue entries, team memory, the task ledger | Serverless, fast, PK/SK pattern fits every access pattern; single table means fewer IAM grants and simpler debugging |
| **SQS** (+ DLQ) | Durable at-least-once handoff of every agent task to the runner | Makes task execution survive Lambda restarts, with retry and a dead-letter queue |
| **Agent Runner Lambda** | Consumes SQS, loads team memory, calls the model, accounts tokens, broadcasts, releases the desk, and then either dispatches the next queued task or forwards a handoff to another desk | Isolated from the Router so model latency never blocks connection handling |
| **Groq** (`openai/gpt-oss-120b`) | Foundation model inference — **the only component not on AWS** | Bedrock is blocked account-wide on this account (decision 7). Reached with one stdlib `urllib` POST; the key is an SSM SecureString read at runtime |
| **Amplify Hosting** | Static React frontend, public HTTPS URL | Fastest path to an HTTPS URL a judge can open cold; deployable from the CLI |

---

## Data flow

### Claiming an agent

```
Browser ──claim_agent──► Router Lambda
                           │
                           ├─ conditional UpdateItem: status IDLE → BUSY
                           │
                    ┌──────┴──────┐
              succeeded        failed (all slots busy)
                    │                │
         send task to SQS      write QUEUE#<ts> item
                    │                │
         broadcast slot state   broadcast queue position
                    │
                    ▼
            Agent Runner Lambda
                    │
                    ├─ load team memory from DynamoDB
                    ├─ check budget ceiling → refuse if exhausted
                    ├─ save any `remember:` fact (before the call)
                    ├─ call the model → Groq
                    ├─ ADD tokens_used (atomic)
                    ├─ broadcast token_update + agent_response
                    ├─ set slot IDLE
                    └─ claim slot for oldest QUEUE# item → SQS → broadcast
```

### Hiring an agent

```
Browser ──spawn_agent──► Router Lambda
                           │
                           ├─ count AGENT# rows → refuse at MAX_AGENTS
                           ├─ slug the name into a free slot id
                           ├─ PutItem AGENT#<id>  (identity + status IDLE)
                           └─ broadcast agent_spawned
```

`dismiss_agent` is the mirror, and refuses to remove the last agent — a floor with no
desks cannot be recovered from through the UI. Finished `TASK#` rows keep the
`agent_name` they were written with, so a dismissed agent's past work stays attributed.

### Handing work to another desk

```
Agent Runner (first leg, hops=0)
       │
       ├─ model calls handoff_to_agent(target, note)
       ├─ release this desk FIRST, then act on the handoff
       ▼
   claim the target desk ──► SQS ──► Agent Runner (second leg, hops=1)
       │  busy? queue the row                     │
       │  pinned to that desk                     ├─ ADD tokens_used (same budget)
       ▼                                          └─ agent_response, same task_id
   broadcast agent_handoff
```

Both legs bill to one budget under one `task_id`, so the ledger shows one request that cost
what both agents spent, as two rows sharing that id.

**The loop guard is tool availability, not a refusal.** `MAX_HANDOFF_HOPS` is 1, and the runner
simply leaves `handoff_to_agent` out of the request once the hop budget is spent — the second
leg is never offered the tool, so there is no instruction for a model to disregard. The release
comes before the handoff always, for the frame-ordering reason in `CONTRACT.md`: a handoff is a
scheduling request, and the desk it came from must already be free when it is made.

**A queued handoff is pinned to its target desk** rather than falling back to any free agent.
Ordinary work prefers a named agent but will take an open one; falling back on a handoff would
hand the work straight back to the desk that just gave it away.

### Broadcasting

Every state change fans out the same way: query connection IDs for the team from DynamoDB → `post_to_connection` per connection → on `GoneException`, delete that connection row immediately.

---

## Key decisions

### 1. The queue is gated by DynamoDB; SQS is the durable handoff

**Considered:** gate on SQS itself, using Agent Runner reserved concurrency equal to the slot count so waiting tasks physically sit in the queue.

**Rejected because:** it introduces Lambda throttling and retry behaviour, visibility-timeout tuning, and `maxReceiveCount` → DLQ risk under exactly the conditions the demo creates. Worse, per-user **queue position** becomes very hard to compute — SQS exposes approximate depth, not "where am I in line."

**Chosen:** the Router atomically claims a slot with a DynamoDB conditional update. If the claim succeeds, the task goes to SQS for execution. If it fails, a `QUEUE#<timestamp>` item is written and position is a trivial count of earlier items.

This is deterministic, race-free, and makes position display straightforward. SQS still does genuine work: every agent task is a durable, at-least-once, DLQ-backed message.

> **Narration consequence.** The demo must say *"every agent task runs through a real SQS queue, and waiting tasks auto-dispatch the moment a slot frees."* It must **not** claim a waiting user is parked inside SQS. Overclaiming on the video is the same failure as a feature that only exists in the writeup.

### 2. Task-level cooperative scheduling, never token-level preemption

Pausing an LLM mid-generation when a time slice expires is not practically feasible. A task takes a slot, runs to completion (or a turn limit), releases the slot, and the next queued task starts. **Final — do not revisit.**

### 3. Single DynamoDB table, PK/SK pattern

One table for every entity type. Simpler to manage, lower latency for co-located data, fewer IAM permissions, far easier to debug under time pressure. Schema in `CONTRACT.md`. **Final.**

### 4. The token budget is an enforced ceiling

The Agent Runner refuses to invoke the model once `tokens_used >= token_budget`. This exists for two independent reasons: it is the product thesis (governance that actually governs), and the deployed URL is public and unauthenticated, so it is the primary spend guard. An AWS Budget alarm backstops it. **Never disable this to make a demo work.**

### 5. Atomic token accounting

`tokens_used` is updated with a DynamoDB `ADD` UpdateExpression, never read-then-write. Concurrent agent runs would otherwise lose updates.

```
UpdateExpression='ADD tokens_used :n'
ExpressionAttributeValues={':n': token_count}
```

### 6. GoneException handling is mandatory from the first broadcast

Lambda is stateless. When a browser closes, its connection ID stays in DynamoDB until a broadcast fails with `GoneException` (HTTP 410). Unhandled, the broadcast loop crashes and every subsequent user stops receiving updates mid-demo. Every `post_to_connection` call is wrapped, and a `GoneException` deletes the connection row immediately.

### 7. Inference calls out to Groq; everything else is AWS

> **Superseded, 2026-09-18.** The original decision was "Strands Agents SDK, with a boto3
> `converse` fallback", chosen so the project stayed fully AWS-native. Both options assumed
> Bedrock was reachable. It is not, on this account, and no amount of configuration fixes it.

**What was tried.** Bedrock refuses across `us-east-1`, `us-west-2` and `ap-south-1`. Marketplace-served models (Anthropic, AI21, Mistral) return `AccessDeniedException: INVALID_PAYMENT_INSTRUMENT`; a valid card was added and did not change it. First-party Amazon Nova needs no Marketplace subscription and still fails with `ThrottlingException: Too many tokens per day` against a per-day quota of zero that reports `adjustable=False` — so it cannot even be raised by request. 42 of 43 per-day token quotas are zero. That is an account-level restriction, not a setting, and AWS Support will not turn it around before the deadline.

**The decision.** Inference moves to Groq (`openai/gpt-oss-120b`) over HTTPS from the Agent Runner. The API Gateway WebSocket, both Lambdas, SQS, DynamoDB and Amplify are unchanged. One outbound HTTP call is the entire difference.

**Why this is defensible rather than a retreat.** A governance layer that only works against one vendor's models is a worse governance layer. The scheduler does not care where a token was spent, only that it was counted — and the swap proved that concretely: it touched one function, `_run_agent`, plus a new 130-line `shared/llm.py`. Nothing about the queue, the slot state machine, the atomic accounting or the enforced ceiling moved.

**What it costs.** The project is no longer end-to-end AWS, and the demo says so out loud rather than hiding it. Against the alternative — shipping a stub and calling the token meter an estimate on a product whose entire pitch is token governance — this is the better trade. The counts are now the provider's reported `total_tokens`, so the meter means what it says.

**Implementation notes that cost real time:**
- `urllib` from the stdlib, no SDK: nothing extra to package, and no compiled wheel to resolve against a local Python 3.14 that does not match the Lambda runtime.
- The key is an SSM SecureString read at runtime, never a CloudFormation parameter — so a redeploy cannot wipe it and it never enters git.
- Cloudflare rejects urllib's default User-Agent with HTTP 403 `error code: 1010`, which is indistinguishable from a bad key until you read the body.
- The stub is retained as an automatic fallback, flagged `estimated`, so a provider outage degrades the answer instead of breaking the workspace.

### 8. DOM/CSS for the workspace canvas — never a game engine

Hackathon teams routinely lose two to three days to tilemaps, collision, and sprite animation. The floor is a fixed-size div with absolutely positioned character divs; movement is x/y updates with CSS transitions. **Final.**

**The 2026-09-19 pivot inverted which half is the product, and not the technique.** This decision used to end "the HUD is the product; the canvas is the wrapper." It is now the other way round: the floor is what you look at and the panels are the governance layer inside it. That made the canvas load-bearing, which is an argument *for* a game engine — and it is still rejected, because everything the floor does is a div moving to a coordinate, and none of it is collision, physics or z-ordered tile rendering. The cost of an engine did not change; the reason to pay it still has not appeared.

### 9. No authentication for the MVP

Cognito costs roughly a day of setup, and it is still not built — it remains on the never-build list, because a judge who meets a sign-up form before seeing the board is a worse outcome than an unauthenticated demo.

**Workspaces can be protected by a passphrase instead** (2026-09-18). Whoever creates one may set a passphrase; joining it then requires that passphrase, verified server-side at `$connect` against a PBKDF2 hash. This closes the actual gap — that anyone who knew a workspace *name* could walk into it — without putting a wall in front of the public URL, because a workspace with no passphrase stays open. It is authentication of the *workspace*, not of the person: there are still no accounts and no identity, and members pick a display name on entry. For a judge opening a URL cold, zero-login is actively better. This is an accepted, documented tradeoff — and the reason the server-side token ceiling is mandatory. Cognito is Post-Hackathon.

### 10. Infrastructure as a SAM template

All stack resources live in `template.yaml`. CloudFormation owns the inventory, which is what prevents a fresh session after `/clear` from recreating resources it has forgotten about. Lambdas are **arm64** — cheaper, faster, and building natively under `--use-container` on Apple Silicon.

### 11. The roster is per-workspace data, not deploy-time configuration (2026-09-19)

`agents.py` used to be the roster: one tuple, fixed at deploy time, identical in every workspace. It is now an `AGENT#` row per agent, carrying identity — name, role, character, project, tagline, persona — beside the `status` and `current_user` it already held. Hiring writes a row; dismissing deletes one.

**No migration, and that is the design.** `ensure_team` writes roster rows conditionally, so every workspace created before the change still has a bare `AGENT#coder` row with no identity fields. `agents.from_row` falls back field by field to `STARTING_ROSTER`, so all of them read as Ada and Iris with no backfill and no scan-and-update against a live table. `seed.sh` and `ws_smoke.py` write those bare rows **on purpose**, so the compatibility path is exercised on every seed and every smoke run rather than assumed.

**Seeding the roster belongs to creating a workspace, not to joining one (corrected 2026-09-20).** `ensure_team` runs on every `$connect`, and the conditional write above made it re-create any seeded desk whose row was absent — which is precisely what `dismiss_agent` leaves behind. Dismissing Iris held only until the next person connected, or until your own socket reconnected after a blip, and the desk came back with no frame and no log line to explain it. The roster is now written only on the branch where the `METADATA` put actually succeeded. The one exception is a repair: a floor with zero desks is re-seeded, because such a floor accepts tasks it can never dispatch and is otherwise unrecoverable — that state is only reachable if a bootstrap died between the two writes. **The general shape: a bootstrap that runs on every request is an idempotent *write*, and an idempotent write is an undo for anything that legitimately deletes what it writes.**

**Hiring is open to any member, not just the owner.** Hiring costs nothing; *running* an agent spends the budget, and the ceiling governs that identically however many desks share it. A permissions wall in front of the one interaction this product is about would be governing the wrong thing.

**`MAX_AGENTS` is 4, and the number was measured rather than chosen.** The plan was six. The floor's lower band is 38% tall with the waiting-area rug across the middle, so the only free places are the left and right margins; two rows per side fails *on screen* — row one's character lands on row two's nameplate and row two's character falls off the bottom edge. A cap above what the floor can draw would let someone hire an agent the roster strip lists and the room cannot show, and a board whose whole claim is that it shows real state cannot have a desk that exists but is not drawn.

**The ledger writes `agent_name` at run time** rather than joining it on at read time. With a fixed roster the two were equivalent; with hiring they are not — a dismissed agent's rows would otherwise report a raw slot id, or be credited to whoever holds that id next.

**The engine step in the hire form is a readout, not a picker.** One model is configured per deployment. A per-agent model picker would let one hire quietly change what the team spends per call, which is the opposite of what this product is for.

### 12. An agent may hand work to another desk, bounded to one hop (2026-09-19)

An agent that judges a task a better fit for another desk can forward it. The envelope crosses the floor, the receiving agent answers, and **both legs bill to the same budget under one task id** — one request, two agents, one bill.

The bound is the load-bearing part: a handoff is a model decision, and an unbounded chain of model decisions is an unbounded way to spend a shared budget. One hop means the worst case is two calls, which is bounded by the same ceiling as everything else. The alternative — letting agents negotiate until they settle — is a more impressive demo and a governance hole in a product whose entire claim is governance.

---

## Intentionally simplified for the MVP

| Simplification | Real-world version |
|---|---|
| ~~Single hardcoded team~~ — **built 2026-09-18**: every row is team-partitioned and teams self-bootstrap on first join | Team *administration* — ownership, invites, renaming, deletion |
| No authentication | Cognito user pools |
| ~~Fixed 2 agent slots~~ — **built 2026-09-19**: a workspace opens with two and any member may hire up to `MAX_AGENTS` (4), capped by what the floor can draw | Capacity bounded by budget and licensing rather than by pixels; per-agent model selection |
| FIFO only | Priority queues, fair-share scheduling |
| Team memory never expires | TTL, relevance ranking, embeddings |
| Estimated wait is a rough constant | Historical task duration modelling |
| Hardcoded token budget | Billing integration, per-user quotas |

---

## Rejected — do not reintroduce

| Rejected | Why |
|---|---|
| Phaser.js / any game engine | Consumes days of hackathon time for no judged benefit |
| Token-level preemption | Not practically feasible mid-generation |
| Google OAuth / Gmail / Calendar | Consent screen verification and token vaults cost a full day |
| Multiple DynamoDB tables | More IAM surface, more latency, harder to debug |
| Cognito (for MVP) | Roughly a day of setup; a login wall hurts a cold-open demo |
| In-memory task queue | Lost on Lambda restart; would make the queue a fiction |
| A per-agent model picker in the hire form | Would let one hire quietly change what the team spends per call — the opposite of what this product governs. The engine step is a readout |
| Unbounded agent-to-agent negotiation | A handoff is a model decision; an unbounded chain of them is an unbounded way to spend a shared budget. Capped at one hop |
| Any AWS service not listed above | Every service must do real work or it does not belong |
