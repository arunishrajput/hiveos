# CONTRACT.md — Shared interfaces

Everything here must stay consistent across backend, frontend, and infrastructure. Changing anything in this file means updating every consumer in the same commit.

Ranks 3rd in the source-of-truth hierarchy — above `PRD.md`, below deployed AWS state and actual code.

---

## Naming and environment

| Constant | Value |
|---|---|
| Stack name | `hiveos` |
| Region | `us-east-1` |
| DynamoDB table | `hiveos-state` |
| SQS queue | `hiveos-agent-tasks` |
| SQS dead-letter queue | `hiveos-agent-tasks-dlq` |
| Default team | `alpha` — teams are **not** hardcoded; this is only where a connection lands if it names none |
| Agent slot IDs | `coder`, `researcher` — the ids; the agents at those desks are **Ada** and **Iris** (below) |
| Lambda architecture | `arm64` |
| Lambda runtime | `python3.13` |
| WebSocket stage | `prod` |
| WebSocket URL | `wss://mel2gpat9c.execute-api.us-east-1.amazonaws.com/prod` |

The WebSocket URL is a stack output (`WebSocketURL`). Read it from CloudFormation rather than pasting it — it changes if the API is ever replaced.

### Lambda packaging

Both functions are built from `CodeUri: backend/` with handlers like `router.app.lambda_handler`, so `backend/shared/` is importable as a top-level `shared` package from either one. No Lambda layer — a layer buys nothing at this size and costs build complexity.

### Lambda environment variables

| Variable | Set on | Meaning |
|---|---|---|
| `TABLE_NAME` | both | DynamoDB table name |
| `TEAM_ID` | both | Team partition (`alpha` in the MVP) |
| `QUEUE_URL` | Router | SQS queue URL |
| `WS_ENDPOINT` | both | API Gateway management endpoint (`https://{api}.execute-api.{region}.amazonaws.com/{stage}`) |
| `BEDROCK_MODEL_ID` | Agent Runner | Resolved in Phase 0 — see below |
| `TOKEN_BUDGET` | Agent Runner | Team token ceiling |
| `MAX_TOKENS_PER_CALL` | Agent Runner | Per-invocation output cap |

### Inference model

```
openai/gpt-oss-120b   via Groq   (https://api.groq.com/openai/v1/chat/completions)
```

**Not Bedrock.** Bedrock is blocked account-wide on this AWS account: `us-east-1`, `us-west-2` and `ap-south-1` all refuse, Marketplace models with `INVALID_PAYMENT_INSTRUMENT` and first-party Amazon Nova with a hard zero per-day token quota that reports `adjustable=False`. Verified again on 2026-09-18 before the switch. See `PROGRESS.md`.

Every other component is AWS. Only inference leaves.

| | |
|---|---|
| Client | `backend/shared/llm.py` — one `urllib` POST, no SDK |
| Credential | SSM SecureString `/hiveos/groq-api-key`, read at runtime, cached per container. **Never** in the template, the stack, an env var, or git |
| Model | `GROQ_MODEL` env var, pinned in `samconfig.toml` |
| Output cap | `MAX_TOKENS_PER_CALL` = 900 |

**This model's reasoning tokens are charged against the output cap.** `gpt-oss-120b` thinks before it answers, and that thinking counts as completion tokens. A cap sized for the *answer* can therefore be spent entirely on reasoning and return empty content — which the runner can only read as a provider failure, so the user gets a stubbed reply after the team has paid full price for the call. Observed at the old cap of 400: `completion_tokens: 400`, of which `reasoning_tokens: 398`. Raised to 900 in Phase 16. **The cap is a ceiling, not a budget** — a call still bills only what it emits, and measured per-task cost did not move when it was raised. Size it for reasoning *plus* the answer; the three-sentence limit is enforced by the system prompt, never by this.

`llm._no_completion` names this case explicitly in the error, because in a bare usage dump it is indistinguishable from a generic provider failure and the two want opposite responses.

**Never guess the model name.** Groq retires them: `llama-3.3-70b-versatile`, the name this was first written against, was already gone and failed at runtime rather than at deploy. List the current ids with `GET https://api.groq.com/openai/v1/models` before changing it.

**A `Default:` change does not reach a deployed stack.** CloudFormation keeps an existing stack's parameter values on update, so the model name is pinned in `samconfig.toml`'s `parameter_overrides`, not left to the template default.

If Bedrock is ever unblocked, swap the body of `llm.py:complete` and add `bedrock:InvokeModel` to the Agent Runner role. Nothing else changes.

---

## The agent roster

**The roster is data, one `AGENT#` row per agent, and it is per workspace.**
Two boards do not have the same desks. `state.roster(team)` is the single
answer to "which agents exist here", and every caller that used to iterate a
module constant reads it instead — so the slot rows, the claim fallback order
and the desks on the floor cannot disagree.

`state.SLOT_IDS` and `scheduler.SLOTS` are **gone**. A constant cannot answer a
per-workspace question.

### What stays in `backend/shared/agents.py`

| | |
|---|---|
| `STARTING_ROSTER` | who a new workspace opens with — Ada the Engineer (`coder`) and Iris the Researcher (`researcher`) |
| `CHARACTERS` | the eight faces the hire form offers. **Must stay in step with `AVATARS` in `frontend/src/sprites.js`** — the art derives a look from this string |
| `MAX_AGENTS` | **4.** A floor limit, not a cost limit. It is how many places the floor plan has: two project rooms and two open desks |
| `MAX_NAME` … `MAX_PROJECT` | what a hired field is truncated to, server-side |

### The starting roster

| id | name | role | takes |
|---|---|---|---|
| `coder` | **Ada** | Engineer | code, debugging, design, implementation |
| `researcher` | **Iris** | Researcher | finding, checking, summarising |

Order is meaningful and comes from `created_at`: it is both the fallback order
for a claim and the order the desks sit in on the floor. The two seeded rows
carry an index suffix on their timestamp so they cannot tie, and a hire always
sorts after them — hiring never reshuffles a room somebody is watching. A hire's
`created_at` is **microsecond** precision (`now_iso_micros`), for the same
reason `QUEUE#` sort keys are: at second granularity two hires in the same
second tie and fall through to the `slot_id` tiebreak, which is slugged from the
name — so the floor would reorder itself alphabetically.

**The starting roster is written once, when the workspace is created.**
`ensure_team` runs on every `$connect`, and until 2026-09-20 it re-wrote the two
seeded rows every time. The write is conditional on the row being absent, which
is exactly what `dismiss_agent` leaves behind — so the next person to connect
silently put the dismissed desk back, with no `agent_dismissed` reversal, no
`agent_spawned` frame and nothing in the activity log. An automatic reconnect
after a network blip was enough. The roster is now seeded only on the branch
where the `METADATA` write actually succeeded, plus one repair case: a floor
with **no** desks at all is re-seeded, because such a floor can never dispatch
anything and is only reachable if a bootstrap died between the two writes.

### The fallback that means no board needs a migration

`ensure_team` writes slot rows **conditionally**, so a row that already exists
is never updated. Every workspace created before the roster became data still
holds a bare `AGENT#coder` row with no name on it.

`agents.from_row` therefore falls back **field by field** to `STARTING_ROSTER`
by slot id. Those boards read as Ada and Iris exactly as before — no backfill,
no scan-and-update against a live table. `seed.sh` and `ws_smoke.py` both write
those bare rows deliberately, so the compatibility path is exercised on every
seed and every smoke run instead of being assumed.

**The ids `coder` and `researcher` are not renamed.** They are in deployed
rows, in `seed.sh`, in `ws_smoke.py` and in every queued task. A hired agent
gets a fresh id slugged from its name plus four random hex characters —
`jim-a3f2` — readable in a log line, and unique without a read or a lock.

**`persona` never leaves the backend.** `agents.public()` drops it: the persona
is the model's instruction, not board state, and shipping it on every snapshot
would make a prompt edit a frontend concern *and* hand anyone on a public URL
the text steering the agents. `ws_smoke.py` asserts its absence from both
`state_snapshot` and `agent_spawned`.

### Hiring is not an admin action

Anyone in a workspace may `spawn_agent`. Hiring costs nothing; **running** an
agent spends the budget, and the ceiling governs that identically however many
desks share it. Requiring the owner to add a colleague would be governing the
wrong thing.

`dismiss_agent` has two rules, both because the scheduler reads this roster:
only while the desk is `IDLE` (deleting a row mid-task leaves the runner
holding a desk that no longer exists, and its release would write the row back
as a nameless ghost), and never the last desk (a floor with no desks accepts
tasks it can never dispatch).

**A dismissal is permanent**, including for the two seeded desks — see *The
starting roster* above for the bootstrap rule that makes that true.

### Requested versus ran

`agent_type` on a claim is a **preference**, and was one before the agents had
names (see the claim table below): it is tried first, then the remaining desks.
Nobody queues behind an idle agent, and that does not change now that the desks
differ — but the substitution must be *visible* rather than silent.

| Carries the agent that **ran** | Carries the agent that was **asked for** |
|---|---|
| SQS `slot_id`; `agent_response.agent_type` / `.agent_name`; `TASK#.agent_type` | SQS `requested_agent`; `agent_response.requested_agent` / `.requested_name`; `TASK#.requested_agent`; `QUEUE#.agent_type`; `queue[].agent_type` |

The two *requested* fields on a finished task are null unless somebody actually
got a different agent — a ledger that repeated the same id in both columns on
every row would bury the one case that matters.

Before this, the SQS message carried a single `agent_type` holding the
preference, and the runner recorded **that** as the agent which ran the task.
With interchangeable slots it was a harmless mislabel; with named agents it is
the ledger crediting Ada for Iris's work.

---

## DynamoDB single-table schema

Table `hiveos-state` · PK `PK` (string) · SK `SK` (string) · on-demand billing.

| PK | SK | Attributes |
|---|---|---|
| `TEAM#<team>` | `METADATA` | `name`, `token_budget` (N), `tokens_used` (N), `created_at` |
| `TEAM#<team>` | `CONN#<connectionId>` | `user_id`, `avatar`, `x` (N), `y` (N), `connected_at` |
| `TEAM#<team>` | `AGENT#<slotId>` | `status` (`IDLE`\|`BUSY`), `current_user`, `slot_id`, `claimed_at`, **plus its identity**: `name`, `role`, `tagline`, `persona`, `character`, `project`, `created_at`. A row written before the roster became data has the runtime fields only and is filled in from `STARTING_ROSTER` by `agents.from_row` |
| `TEAM#<team>` | `QUEUE#<ts>#<uuid>` | `user_id`, `agent_type`, `prompt`, `connection_id`, `enqueued_at` |
| `TEAM#<team>` | `MEMORY#<slug(key)>` | `key`, `val`, `updated_by`, `created_at` |
| `TEAM#<team>` | `ACTIVE#<userId>` | `user_id`, `task_id`, `claimed_at`, `expires_at` (N, epoch seconds). Enforces single-task admission per user. Carries TTL (3600s) as an orphan safety net. |
| `TEAM#<team>` | `IDEMPOTENCY#<taskId>#<hops>` | `slot_id`, `user_id`, `claimed_at`, `expires_at` (N, epoch seconds). **The only row in the schema that expires.** Written conditionally by the runner; its existence *is* the value and nothing ever reads it back. **Keyed on the leg, not the chain** — see below |

### Teams

Every row above is partitioned by team, and every backend function takes the
team as its first argument. Two people who type different workspace names get
genuinely separate boards: separate budget, slots, queue, memory, ledger and
broadcasts.

**A team creates itself on first join** (`state.ensure_team`), with conditional
writes so several people arriving at a new name in the same second cannot each
reset it. Requiring `seed.sh` before a name worked would make isolation a
deployment step rather than a property of the product.

**Team names are untrusted input that ends up in a partition key**, so they are
validated against `^[a-z0-9][a-z0-9_-]{0,30}$` and lowercased — anything else
falls back to the default. Lowercasing matters: `Alpha` and `alpha` must be one
room, not two that look identical and cannot see each other.

| PK | SK | Attributes |
|---|---|---|
| `CONN#<connectionId>` | `TEAM` | `team`, `connected_at` |

### Workspace passphrases

A workspace is **open** unless the person who created it set a passphrase.
Whoever creates it sets it; it is never changed afterwards by this code.

| Field on METADATA | Meaning |
|---|---|
| `pass_salt` | 16 random bytes, hex. Absent on an open workspace |
| `pass_hash` | PBKDF2-HMAC-SHA256, 100k iterations, hex |

- **Verified on `$connect`, and refused with HTTP 403.** No socket and no
  `CONN#` row ever exist for a failed attempt. Accepting the socket and closing
  it after an error frame would leave a connected client with no team binding,
  and a frame sent in that window resolves to the default workspace.
- **Compared with `hmac.compare_digest`.** A plain `==` returns early on the
  first differing byte, which leaks the matching prefix length to anyone
  willing to time it.
- **`state_snapshot` carries `protected` (a boolean) and never the salt or
  hash.** The METADATA row is read wholesale to build the snapshot, so this is
  the one place they could leak; the snapshot names the fields it sends.
- **The passphrase travels in the `$connect` query string**, because a browser
  cannot set headers on a WebSocket handshake. TLS covers it in transit. It
  would appear in API Gateway access logs if those were enabled — they are not.
  Recorded as a known tradeoff rather than left implicit.
- **The default workspace stays open.** Zero-login on the public URL is a
  deliberate property (`ARCHITECTURE.md` decision 9): a stranger has to be able
  to open the board cold. `ws_smoke.py` asserts the open case as hard as the
  closed one.

### Workspace administration

Whoever creates a workspace may also present an `admin_token`; its hash is
stored the same way a passphrase's is. **There are no accounts, so rights hang
off a secret the creator holds, not off a display name anyone could type.**
Sharing that secret is what an invite is here.

| Field on METADATA | Meaning |
|---|---|
| `admin_salt` / `admin_hash` | PBKDF2 of the admin token. Absent on a workspace with no owner |

| Client action | Effect |
|---|---|
| `admin_set_budget` | `{token_budget}` — broadcasts `token_update` to the whole workspace |
| `admin_rotate_passphrase` | `{passphrase}` — empty removes protection. Locks out the *next* joiner; everyone already connected stays |
| `admin_delete_workspace` | Deletes every row the workspace owns, including its members' `CONN#/TEAM` index rows, then sends `workspace_deleted` |

- **The token is minted by the client and never returned by the server.**
  Whoever creates a workspace already holds it, so there is nothing to hand
  back and no window in which it could be intercepted.
- **Rights are decided once, at the handshake, and stored as `is_admin` on the
  `CONN#` row.** Admin actions check the row, not the frame — the same rule
  that makes `user_id` trustworthy. A client cannot grant itself rights by
  adding a field to a message.
- **`state_snapshot` carries `owned` and `is_admin` as booleans, never the salt
  or hash.**
- **`admin_delete_workspace` collects its audience before deleting.**
  `broadcast_to_team` finds recipients by reading `CONN#` rows, which the
  delete removes — broadcasting afterwards would reach nobody.

PBKDF2 rather than argon2 or bcrypt because it is in the standard library —
Lambda has neither without a layer, and a layer for one function costs more
than it buys here. 100k iterations is ~50ms, paid once per handshake and never
per frame.

**The `CONN#…/TEAM` index is not redundant.** API Gateway exposes
`queryStringParameters` on `$connect` and on nothing afterwards, so every later
frame carries a connection ID and no team. Without this row, resolving a
connection's team would mean scanning every team.

The obvious alternative — have the client send its team on each frame — is
rejected for exactly the reason `CONTRACT.md` already resolves the *sender*
from the stored row rather than the frame: a value the client supplies is a
value the client can forge, and forging this one would mean reading another
team's board.

It is deleted on `$disconnect` alongside the member row. An orphaned index row
is harmless — it is only ever read by a connection ID that will never recur —
but it is not cleaned up by `seed.sh`, which is a known MVP simplification.

### Entity rules

- **METADATA** — one per team. `tokens_used` is only ever updated with `ADD`, never read-then-write.
- **ACTIVE#** — one per user currently holding a desk claim or queued task. Enforces single-task admission per user (`state.acquire_user_admission`). Carries `expires_at` (TTL 3600s / 1 hour matching `TaskQueue` retention) as an orphan-recovery safety net if a function crashes before release.
- **CONN#** — one per live WebSocket connection. Deleted on `$disconnect` **and** on any `GoneException` during broadcast. **One row per connection, not per user** — the same `user_id` with two tabs open has two rows, so `state_snapshot.members[]` can contain duplicates. `user_left`, by contrast, carries only a `user_id`, so a client that trusts it blindly removes someone who still has a live socket. The frontend dedupes `members[]` by `user_id` and re-syncs on both membership events.
- **AGENT#** — one per slot. `IDLE → BUSY` on claim, `BUSY → IDLE` on completion. `current_user` is `null` when `IDLE`.
- **QUEUE#** — the SK leads with a microsecond timestamp, so sorting by SK gives arrival order. **Arrival order is not dispatch order.** Deleted when dispatched. The timestamp is **microsecond** precision (`%Y-%m-%dT%H:%M:%S.%fZ`), not the second-precision `now_iso()` used everywhere else: at second granularity two people clicking within the same second tie and fall back to UUID order, i.e. random. `connection_id` is carried so the runner can reply directly to the requester once the task finally starts.

  **Dispatch order is fair queueing, not FIFO** (`state.fair_order`): sorted by
  how long each person has gone without a turn — read off the `TASK#` ledger —
  with arrival as the tie-break only. Someone who has never run outranks
  someone who just did, so a user who re-requests the instant their task
  finishes cannot jump a colleague who has been waiting. With one task each and
  nobody having run yet, this is indistinguishable from FIFO, which is why the
  demo sequence is unaffected.

  **There is exactly one definition of that order and all three consumers use
  it** — `take_next_task`, `broadcast_queue`, and `state_snapshot`. If the
  board numbered positions by arrival while the runner picked by fairness, the
  position on screen would be wrong about who goes next.

  **`pinned_slot` makes a row dispatchable at one desk only.** Set on a handoff
  and on nothing else. `agent_type` on an ordinary row is a *preference* the
  scheduler is right to fall back off — nobody should wait behind an idle
  agent — but falling back on a handoff would return the work to the desk that
  just decided it was not theirs. `take_next_task` therefore **skips** a pinned
  row whose desk is not in the idle set rather than taking it and requeueing
  it. A pinned row also carries `task_id`, `hops` and `handoff_from`. See
  *Agent-to-agent handoff*.
- **TASK#** — the ledger: one row per task that reached the runner, including
  the ones that never ran. `status` is `done`, `failed` or `refused`; a refused
  task records **zero** tokens, which is the clearest evidence that the ceiling
  is a control and not a gauge. `agent_type` is the agent that **ran** it —
  always the slot it ran on — and `requested_agent` is set only when that was
  not the one asked for. See *Requested versus ran*.

  **`agent_name` and `handoff_from_name` are written onto the row at the moment
  the work ran, not joined on when the ledger is read.** While the roster was a
  fixed constant the two were equivalent. They are not now: an agent can be
  dismissed, so a late join would report its finished work under a raw slot id
  — or, worse, credit it to whoever is hired into that id next. A ledger is a
  record of what happened and who did it is part of what happened. Rows written
  before this fall back to the id, which for those rows is `coder` or
  `researcher`. It also drops N lookups from every snapshot.

  **`task_id` is the job; the row is one leg of it.** A handed-over task runs
  as two agent tasks and writes two rows, and they share one `task_id` — that
  is what lets the ledger say "this piece of work cost the team 1,982 tokens
  across two desks" rather than showing two unrelated tasks that happen to sit
  next to each other. `handoff_from` is set on the receiving row only, and
  names the desk that passed it on. Both are null on a task nobody handed over.

  Sort key is microsecond-precision for the same
  reason `QUEUE#` is: at second granularity two tasks finishing together tie
  and fall back to UUID order, i.e. random. Cleared by `seed.sh` — the spend
  breakdown aggregates every row, so stale rows would open the board showing a
  team that had already spent its budget.

- **MEMORY#** — key/value facts saved by agents. No expiry in the MVP.

  **The SK is derived from the key, not a UUID** (`memory._slug`: lowercased,
  non-alphanumerics collapsed to `_`). This file previously specified
  `MEMORY#<uuid>`, which made `set_team_memory` non-idempotent — saving the
  same key twice left two rows carrying the same `key`, and `state_snapshot`
  handed a client both of them as separate facts. A key/value store keyed by
  the key makes a write an upsert, which is the behaviour every consumer
  already assumed. Two keys differing only in case or punctuation collapse to
  one fact; that is deliberate.

  `created_at` is the **write** time, so an upsert refreshes it and `facts()`
  orders by most-recently-set.

- **IDEMPOTENCY#** — one per *delivery* that reached the runner. SQS is
  at-least-once, so the same task can arrive twice; without this the second
  arrival called the model again and charged the team for one piece of work
  twice. The row is written with `attribute_not_exists(SK)` and never read
  back — winning the put *is* the answer, exactly like the `QUEUE#` delete
  being the dispatch gate.

  **The key is `<taskId>#<hops>`, not `<taskId>`.** `task_id` identifies the
  piece of work; `hops` identifies which leg of it this is. Both legs of a
  handoff carry one `task_id` on purpose — it is what ties them together in
  the ledger and on `agent_response` — so keying on it alone made the
  receiving leg collide with the handing leg's marker: Iris claimed the desk,
  skipped her model call, and went IDLE again without ever answering. A
  redelivery repeats `hops`; a handoff increments it.

  **The gate runs inside the runner's `try`, not before it.** A redelivery is
  also the only thing that can free a desk whose previous run died holding it,
  so the duplicate must still fall through to the `finally` that releases the
  slot. Returning earlier would make a leaked desk permanent — trading a
  double charge for a deadlocked workspace, which is the worse of the two.

  **The only row in the schema with an expiry.** `expires_at` is epoch seconds
  (DynamoDB TTL accepts nothing else) and is set a day out, comfortably past
  the queue's one-hour `MessageRetentionPeriod`. Nothing reads these rows, and
  `state_snapshot` queries the whole partition on every `hello`, so keeping
  them forever would grow that read without bound.

- **METADATA `usage_estimated`** — set when any spend folded into
  `tokens_used` was an estimate rather than billed model usage. Sticky: never
  cleared by the runner, only by `seed.sh` rewriting the row. See
  *Token provenance* below.

### Atomic slot claim

The only correct way to claim a slot. Two simultaneous claims must never both succeed.

```python
table.update_item(
    Key={'PK': f'TEAM#{team_id}', 'SK': f'AGENT#{slot_id}'},
    UpdateExpression='SET #s = :busy, current_user = :u, claimed_at = :t',
    ConditionExpression='#s = :idle',
    ExpressionAttributeNames={'#s': 'status'},
    ExpressionAttributeValues={
        ':busy': 'BUSY', ':idle': 'IDLE',
        ':u': user_id, ':t': now_iso,
    },
)
# ConditionalCheckFailedException  =>  slot was taken; try the next one, else enqueue
```

### Atomic token accounting

```python
table.update_item(
    Key={'PK': f'TEAM#{team_id}', 'SK': 'METADATA'},
    UpdateExpression='ADD tokens_used :n',
    ExpressionAttributeValues={':n': token_count},
    ReturnValues='UPDATED_NEW',   # returns the new total for broadcasting
)
```

---

## WebSocket protocol

All frames are JSON. Client frames carry `action`; server frames carry `event`.

The API's `RouteSelectionExpression` is `$request.body.action`, but only `$connect`, `$disconnect` and `$default` are declared as routes. Every action therefore lands in one handler. **Adding a client action is a code change, never a CloudFormation change** — which matters because `AWS::ApiGatewayV2::Deployment` is an immutable snapshot of the route table.

### Connection handshake

`user_id` and `avatar` are passed as query-string parameters on the socket URL:

```
wss://…/prod?user_id=alice&avatar=%F0%9F%90%9D
```

Both are optional. A missing `user_id` becomes `guest-<first 6 chars of connection id>`.

### Client → server

| `action` | Payload | Handler behaviour |
|---|---|---|
| `hello` | — | Reply `state_snapshot` to this connection only. Sent once, immediately after the socket opens |
| `claim_agent` | `{agent_type, prompt, user_id}` | Try atomic claim → dispatch to SQS, or enqueue and return position |
| `release_agent` | `{agent_type}` | Free the slot if the sender holds it, then dispatch the next waiting task |
| `send_message` | `{text}` | Broadcast to team chat as `chat_message` |
| `move_avatar` | `{x, y}` | Update `CONN#` row, broadcast `avatar_moved` |
| `spawn_agent` | `{name, role, tagline, persona, character, project}` | Hire a desk onto this floor. **Any member may** — see *Hiring is not an admin action*. Every field is truncated server-side; refused with an error once the floor holds `MAX_AGENTS`. Broadcasts `agent_spawned` |
| `dismiss_agent` | `{agent_type}` | Take a desk off the floor. Refused while it is `BUSY`, and refused for the last desk. Broadcasts `agent_dismissed` |

**`action` must be a string.** A frame without one — or carrying a number, a
list or `null` — is answered `error: "frame must carry a string action"`. It
used to reach `action.startswith("admin_")` and raise `AttributeError` into the
top-level handler, which replied the generic `"internal error"` and logged a
stack trace: the wrong answer twice over, since it is the caller's frame that is
malformed rather than the server. A malformed frame never closes the socket.

**`agent_type` on `claim_agent` is a preference, not a reservation.** It is tried first, then the remaining slots in `SLOTS` order. Nobody queues behind an idle agent — and the agent that actually took it is named in the reply. Anything not in `SLOTS` becomes "no preference" rather than an error.

**One active task per user.** A `claim_agent` from a user who already holds a slot or sits in the queue is refused with `error`. Without it a double-clicked button lets one person hold both slots — precisely the monopoly the product claims to prevent.

**A desk can only be freed by whoever is sitting at it.** `release_agent` is refused with `error` unless the sender is the slot's `current_user` or was admitted with the workspace admin token; the admin case is what keeps the escape hatch usable when a runner dies holding a desk and its owner has closed the tab. The sender is resolved from the `CONN#` row, never from `user_id` on the frame — which is why that field is no longer listed above. Releasing a desk that is already idle is not an error and frees nothing; it only asks the scheduler to look at the queue again.

**A release names the holder it expects.** Both halves of the slot mechanism are conditional writes: `claim` requires the desk to be `IDLE`, and the release requires `current_user` to still be the task's own user. SQS redelivers, so a task can finish and reach its release long after the desk was handed on — an unconditional write there would end a stranger's task and then broadcast `agent_state_update: IDLE` for a desk that is genuinely working. A refused release changes nothing, broadcasts nothing, and dispatches nothing.

**Neither `send_message` nor `move_avatar` takes a `user_id`.** It is resolved from the sender's `CONN#` row, because a frame is whatever the client chose to type and the row is what `$connect` actually recorded — trusting the frame would let any client move someone else's avatar or speak as them. (This table previously listed `user_id` on both; the handlers never read it.)

**Avatar coordinates are percentages of the canvas (0–100), not pixels.** Three browsers at different widths have to agree on where everyone is standing, and a pixel coordinate breaks that on the first mismatched window. The Router clamps to the range and rejects non-numeric values, so a hand-crafted frame cannot push an avatar off the board for everyone else.

**A position is stored per connection but drawn per user.** The `CONN#` row carries `x`/`y`, so someone with two tabs open has two stored positions — but `state_snapshot.members[]` carries no `connection_id` (deliberately: it is an internal address used only by `post_to_connection`, and broadcasting it to every client buys nothing). The frontend therefore dedupes `members[]` by `user_id` for both the count and the canvas, and `avatar_moved` is keyed by `user_id`, so a second tab moves the same avatar. One person, one marker, which is also the reading that makes sense on a team board.

### Server → client

| `event` | Payload | Sent when |
|---|---|---|
| `state_snapshot` | `{team, agents[], tokens_used, token_budget, pct_used, usage_estimated, members[], memory[], queue[], history[], spend[]}` | In reply to `hello` — a new client must be able to render everything from this one frame |

`agents[]` entries are `{slot_id, agent_type, status, current_user, name, role, tagline}`, **in roster order** — which is desk order on the floor and fallback order for a claim. A client must not re-sort them: that order agreed with alphabetical only by the accident of `coder` preceding `researcher`. A slot row whose id is no longer on the roster still renders, last, under its id.
| `chat_message` | `{user_id, text, ts}` | `send_message` runs. `user_id` is resolved from the sender's `CONN#` row, not trusted from the frame |
| `agent_state_update` | `{agent_type, status, current_user, slot_id}` | Any slot state change. **State only — no name.** Identity rides on `state_snapshot`; a client merges this patch over what it already holds, so a desk keeps its nameplate, and a slot it has never seen renders under its raw id until the 500 ms re-sync names it |
| `token_update` | `{tokens_used, token_budget, pct_used, estimated}` | After every agent call that spent tokens |
| `queue_update` | `{user_id, queue_position, estimated_wait_seconds}` | Queue add or removal |
| `agent_response` | `{user_id, agent_type, agent_name, requested_agent, requested_name, task_id, handoff_from, handoff_from_name, text, tokens_used_this_call, estimated}` | Agent task completes. `agent_type`/`agent_name` are the agent that **ran** it; the two `requested_*` fields are null unless a different one was asked for; the two `handoff_from_*` fields are null unless another desk handed this task over |
| `agent_handoff` | `{task_id, user_id, from_agent, from_name, to_agent, to_name, note, queued}` | An agent chose to pass its task to another desk. `queued` is true when that desk was busy and the work is waiting for it |
| `memory_updated` | `{key, val, updated_by}` | `set_team_memory` runs |
| `budget_exhausted` | `{tokens_used, token_budget}` | Bedrock invocation refused at the ceiling |
| `user_joined` | `{user_id, avatar, x, y}` | `$connect` |
| `user_left` | `{user_id}` | `$disconnect` or `GoneException` |
| `avatar_moved` | `{user_id, x, y}` | `move_avatar` runs |
| `agent_spawned` | `{slot_id, agent_type, name, role, tagline, character, project, status, current_user, created_at, hired_by}` | A desk was hired onto this floor. Carries everything needed to draw it, so a client appends rather than waiting for the next snapshot. **No `persona`.** The receiving client guards against a duplicate — the 500 ms re-sync can land a snapshot already carrying this desk |
| `agent_dismissed` | `{slot_id, agent_type, dismissed_by}` | A desk was taken off the floor |
| `error` | `{message}` | Any handled failure worth surfacing |

`queue[]` entries are `{user_id, agent_type, queue_position}`, oldest first, `queue_position` 1-based.

**`queue[]` deliberately carries no `estimated_wait_seconds`, unlike `queue_update`.** The
client derives it as `queue_position * ESTIMATED_TASK_SECONDS`, which is byte-for-byte what
`scheduler.broadcast_queue` computes. This matters because the frontend re-reads the snapshot
after every board-moving event (see below), so a field present only on the incremental event
gets overwritten — the ETA used to blank out ~500 ms after appearing for exactly this reason.
`ESTIMATED_TASK_SECONDS` therefore exists **twice**: `backend/shared/scheduler.py` and
`frontend/src/useHive.js`. Retune both in the same commit or the queue will lie.

### Snapshot re-sync (client behaviour)

`queue_update` is broadcast once per *waiting* user and there is **no removal frame** — nothing
tells a client that someone has been dispatched or has left the queue. The client therefore
applies increments for instant feel and re-sends `hello` on a 500 ms debounce after any
`agent_state_update`, `queue_update`, `agent_response`, `user_joined` or `user_left`, letting
the authoritative snapshot correct any drift.

Two consequences anyone touching the protocol must know:

1. **The snapshot must stay a superset of what the incremental events convey**, or the re-sync
   destroys information (see the ETA above).
2. **`state_snapshot` must never be in the re-sync trigger set** — it would feed itself.

**`state_snapshot` is load-bearing.** A client joining mid-demo must render correct state from it alone, without waiting for the next incremental event. `queue[]` exists for exactly this reason: a user who reconnects while waiting would otherwise have no way to learn their own position until somebody else's action happened to move the queue.

### `history[]` and `spend[]`

Both are derived from `TASK#` rows and both ride on `state_snapshot`, because
the client most likely to want *"who spent what"* is the one that just opened
the public URL.

| Field | Shape | Notes |
|---|---|---|
| `history[]` | `{user_id, agent_type, agent_name, requested_agent, task_id, handoff_from, handoff_from_name, tokens, estimated, status, prompt, at}` | Newest first, capped at 12 — every client parses the snapshot on connect, and nobody reads the 40th most recent task off a board. Two rows sharing a `task_id` are the two legs of one handed-over job |
| `spend[]` | `{user_id, tokens, tasks}` | Biggest spender first |

**`spend[]` aggregates every task row, not the twelve in `history[]`.** The
whole point is the total; a breakdown of only the last twelve would be a
different and much less useful number. Refusals and failures count as *tasks*
but not as *spend*, which is what they are.

### Token provenance — `estimated` / `usage_estimated`

Every frame carrying a token count says where the number came from, because
not every number is billed model usage:

| Field | On | Means |
|---|---|---|
| `estimated` | `agent_response`, `token_update` | the total this frame reports includes estimated spend |
| `usage_estimated` | `state_snapshot` | the same fact, for a client that loaded cold |

**Normally both are false.** `tokens_used_this_call` is the `total_tokens` the
provider reported for that call — actual counted usage, typically 200–400 per
task.

They go true only on the **fallback path**: if the model is unreachable, the
Agent Runner still answers, from composed text, and charges
`len(prompt + memory_context + response) / 4` — the standard rough heuristic
over the real strings, not an invented number. A degraded answer is better
than a broken workspace, but it must never be laundered into a billed-looking
meter, which is what these two flags prevent.

**The snapshot field is not optional.** A client that was not connected when
the spend happened — which is every judge opening the public URL — has no
other way to learn the total is partly estimated, and would otherwise render
it as billed usage. The flag is sticky once set: an estimate already folded
into the total does not stop being one. Only `seed.sh` clears it.

### The budget ceiling

Enforced in the Agent Runner immediately before the agent is invoked, never at
claim time: a task can sit in the queue while the tasks ahead of it spend what
was left, so the only honest moment to decide is the last one.

**METADATA is the single source of truth for the ceiling**, not the
`TOKEN_BUDGET` env var. It is the same row the counter increments and the same
number `state_snapshot` shows a client, so the guard can never disagree with
the meter a user is looking at. `TOKEN_BUDGET` supplies only the default
`seed.sh` writes.

On refusal the runner broadcasts `budget_exhausted`, replies `error` to the
requester, spends nothing, and **still releases the slot** — the refusal path
is subject to the same no-leak invariant as every other path.

**Clients must clear the refused state from `token_update`, not only from
`state_snapshot`.** `budget_exhausted` latches the client into a blocked state,
and the only two frames carrying the whole ceiling — used *and* budget — are
`state_snapshot` and `token_update`. `admin_set_budget` broadcasts exactly the
latter, so a client that recomputed on the snapshot alone went on refusing every
task under a meter that had dropped to 12%: red banner, disabled send button, no
way out but a reload. `token_update` is deliberately **not** in the frontend's
`RESYNC_EVENTS` — re-reading the whole board after every completed task is the
one thing that would make the meter expensive — so the frame has to answer the
question itself. The server was never wrong here: it re-reads `METADATA` before
every model call, so the ceiling was always enforced correctly. This was the
board misreporting it.

### Frame ordering

**A slot's `agent_state_update` BUSY is broadcast before its task is handed to SQS.** Dispatching first lets a fast-failing task post its `agent_response` / `error` ahead of the BUSY frame, so the client applies BUSY *after* the release and shows a slot that never goes idle again. Verified: with the old order the Phase 2 smoke test failed about half of all runs.

The guaranteed per-task sequence a client can rely on:

```
agent_state_update BUSY  →  agent_response | error  →  agent_state_update IDLE
```

**Why `hello` exists.** API Gateway does not finish establishing a connection until the `$connect` integration returns, so `post_to_connection` against it inside that handler fails with `GoneException`. The snapshot cannot be pushed from `$connect`; the client pulls it on its first frame instead. Verified on the deployed stack in Phase 1.

### Client connect sequence

```
open wss://…/prod?user_id=alice&avatar=🐝
  → server writes CONN# row, broadcasts user_joined to everyone else
send {"action": "hello"}
  → server replies state_snapshot on this connection
render, then apply incremental events as they arrive
```

---

## Broadcast with GoneException handling

Mandatory in every function that broadcasts. No exceptions.

```python
def broadcast_to_team(team_id, payload, apigw, table):
    for conn_id in get_team_connections(team_id, table):
        try:
            apigw.post_to_connection(
                ConnectionId=conn_id,
                Data=json.dumps(payload).encode(),
            )
        except apigw.exceptions.GoneException:
            table.delete_item(Key={
                'PK': f'TEAM#{team_id}',
                'SK': f'CONN#{conn_id}',
            })
```

---

## SQS message format

```json
{
  "team_id": "alpha",
  "slot_id": "researcher",
  "user_id": "alice",
  "requested_agent": "coder",
  "prompt": "Write a user creation function",
  "connection_id": "abc123=",
  "task_id": "d6dd9a84eb6e",
  "hops": 0,
  "handoff_from": null,
  "enqueued_at": "2026-09-18T10:30:00Z"
}
```

`slot_id` is the desk that won the claim, and therefore the agent that will run this. `requested_agent` is the preference the user sent — here Ada was busy, so Iris took it — and is `null` when they asked for nobody in particular. **The runner reads the agent from `slot_id` and never from the preference.**

`task_id` identifies the piece of work rather than this leg of it, and is minted by the Router where the work is *requested* — it survives a spell in the queue and a handoff unchanged. `hops` counts how many times the work has been passed between desks, and is what the runner checks before offering the handoff tool at all. `handoff_from` names the desk that passed it, and is `null` on a task nobody handed over.

This message used to carry `agent_type` instead, holding the preference; the runner then recorded it as the agent that ran the task. A message still in flight across a deploy is handled: the runner ignores the old field, `requested_agent` reads as absent, and a message predating the handoff fields reads as `hops: 0` with no chain id.

`connection_id` is the requester's connection, used for directed replies. It may be stale by the time the runner executes — handle `GoneException` and continue.

---

## Agent tools

| Tool | Implemented as | Behaviour |
|---|---|---|
| `get_team_memory` | `memory.facts()` / `memory.as_context()` | Read all `MEMORY#` rows; return a context block for the system prompt |
| `set_team_memory` | `memory.remember(key, val, updated_by)` | Upsert a `MEMORY#` row; broadcast `memory_updated` |
| `get_task_context` | `history.as_context()` | Recent tasks, who ran them and what each cost — read from `TASK#` |
| `handoff_to_agent` | `scheduler.hand_off(team, task, target, note)` | Pass this task to another desk. **Offered only while `hops < MAX_HANDOFF_HOPS`** — see *Agent-to-agent handoff* |

Memory is loaded **before** the model call, not on demand, so a queued user's agent already knows the team's facts the moment it starts.

**The system prompt is `identity + rules + memory`, in that order.** Identity is the roster entry's persona for the desk the task is running at, or `SHARED_ROLE` if the slot is not on the roster. The rules — brevity, the tool instructions — are shared by every agent and come *after* the persona, where a persona cannot read as qualifying them. `get_task_context` names the agent that ran each task, so an agent asked where the budget went answers in names rather than slot ids.

**These are real tools now.** The model is given their schemas and decides
whether to call them; `llm.complete` runs the loop and the Agent Runner
executes them. Verified with phrasing the old convention could never have
matched — *"Please make a note for the whole team that our staging URL is
staging.hiveos.dev"* — where the model chose `set_team_memory` and extracted
the key and value itself.

**`get_team_memory` is deliberately not a tool.** The team's facts are loaded
into the system prompt before the call, because *a queued user's agent already
knows the team's facts the moment its turn starts* is a product claim. As a
tool it would be conditional on the model remembering to ask, and a model that
forgot would silently break the demo's strongest beat.

**One round of tools, not a loop.** Each round is a full round trip inside a
Lambda holding an agent slot, and an unbounded loop is an unbounded bill. The
second request is sent without the tool list so the model answers in prose
rather than calling again.

**The tool list is per-task, not constant** (`llm.tools_for`). It is a
parameter because what an agent may do depends on the task in hand: a task that
arrived by handoff is not offered `handoff_to_agent`. Tool *availability* is
the loop guard — see *Agent-to-agent handoff*.

**Tokens are summed across every round.** A tool call is two requests, and
charging for one of them would under-report spend on the one product whose
entire subject is spend. A task costs roughly 800 tokens with tools, against
roughly 270 without — the tool schemas ride in every prompt.

**How a fact gets saved: the model decides.** It calls `set_team_memory`, and
`memory.remember` owns the row and the broadcast exactly as before.

`memory.directive()` — the `remember: <key> = <value>` convention — is still
there, demoted to a safety net. It runs only when the model did *not* save:
either it declined, or the call failed outright and there was no model in the
loop at all. A tool call is a probabilistic act where a regex is not, the
memory beat is the strongest thing the product does, and the fallback costs one
match against a string already in hand.

**The save happens before the model call, not after it.** The fact is the
user's explicit instruction, so it must persist even when the model is
unreachable; and saving first puts it in its own call's context. One
consequence worth knowing: `memory_updated` now broadcasts at the *start* of a
task rather than at the end, so it can overtake frames a client might expect to
see first. Anything asserting on frame order has to buffer rather than assume.

---

## Agent-to-agent handoff

One piece of work, two desks, one budget. Ada decides a task is research rather
than engineering, calls `handoff_to_agent`, and Iris answers it — under the
same `task_id`, on the same meter, through the same scheduler.

**There is no client action for this.** A handoff is the *agent's* decision, so
it arrives as a tool call and leaves as a broadcast. Nothing a browser can send
initiates one, which is also why nothing a browser can send can be used to
start a chain.

### The sequence

```
claim_agent           → Ada's desk BUSY, task dispatched with hops=0
  model calls handoff_to_agent(agent, note)
  Ada answers in prose: "I've passed this to Iris"
agent_response        → Ada's leg, its own token cost, handoff_from=null
agent_state_update    → Ada's desk IDLE            ← released FIRST
agent_handoff         → the envelope crosses the floor
agent_state_update    → Iris's desk BUSY  (or queue_update, if Iris is busy)
agent_response        → Iris's leg, handoff_from="coder", same task_id
agent_state_update    → Iris's desk IDLE
```

**The release comes before the handoff, always.** A handoff is a scheduling
request and must compete for a desk on the same terms as anyone in the queue.
Dispatching it while the handing task still held its slot would let one chain
occupy both desks at once — precisely the monopoly `_already_working` exists to
prevent.

### Rules

- **`MAX_HANDOFF_HOPS = 1`**, and it is enforced by *absence*: the runner only
  puts the handoff tool in the request while `hops < MAX_HANDOFF_HOPS`, so the
  receiving leg has nothing to call. Verified adversarially — a prompt
  explicitly instructing the two agents to pass the task back and forth
  produced exactly two legs. A limit the model is merely *asked* to respect is
  not a limit.
- **The ceiling governs every leg.** Each leg meets `_refuse_over_budget`
  immediately before its own model call, exactly like any other task. A chain
  can therefore overshoot by at most one leg's worth — the same as a single
  task — and a handoff is not a way to spend past the ceiling incrementally.
  Deliberately *not* re-checked at handoff time: a handoff can sit in the queue
  while the tasks ahead of it spend what was left, so the last moment is the
  only honest one.
- **A queued handoff is pinned** (`pinned_slot`). It runs at the desk it was
  handed to or it waits. See the `QUEUE#` entity rules.
- **`requested_agent` equals `slot_id` on a handoff leg**, so nothing is
  reported as a substitution. The handoff is the story; a "Ada was busy" notice
  on top of it would be two explanations for one event.
- **A handoff recorded before a failed model call is dropped.** The fallback
  has already answered the user from this desk, and spending a second leg on a
  question that has a reply on screen is spending the team's budget twice.
- **The note is capped at `MAX_HANDOFF_NOTE` (400 chars)** so it cannot grow
  into a second copy of the prompt riding on every frame.

### The leg-2 prompt

Composed once, by `scheduler.handoff_prompt`, and carried as the leg's ordinary
`prompt`. The receiving agent is a normal task in every other respect — same
ceiling check, same memory load, same accounting — and the fewer special cases
it has, the fewer ways the second leg can behave unlike the first.

```
This task was passed to you by Ada, the Engineer, who judged it a better fit
for your desk.
Their note: <the agent's own note>
The original request, from alice: <the original prompt>
Answer it directly. Do not hand it on again.
```

The last line restates a limit the tool list already enforces. Belt and braces:
the structural guard is that the tool is absent.

---

## Slot state machine

```
        claim_agent (atomic conditional update)
IDLE ──────────────────────────────────────────► BUSY
  ▲                                                │
  │           agent task completes or fails        │
  └────────────────────────────────────────────────┘
                        │
                        ▼
        dispatch oldest QUEUE# item, if any
```

Invariants:
- A slot is `BUSY` only with a non-null `current_user`.
- A slot must be released even when the agent task **fails** — otherwise it leaks and the demo deadlocks. Wrap the runner body in try/finally.
- Dispatching the next queued task happens after the release, in the same invocation.
- **The `QUEUE#` delete is the exactly-once gate.** Two runners finishing at the same instant both see the same head-of-queue item; the conditional delete (`attribute_exists(SK)`) decides which one owns it, and the loser moves to the next item. Without this the same task dispatches twice.
- If a task is won but every slot is then taken before it can be claimed, it is **re-written under its original SK** so the user keeps their place rather than being sent to the back of the line.

### Fault injection

A prompt containing `__hiveos_fail__` makes the Agent Runner raise. This is a deliberate hook so the no-slot-leak invariant stays verifiable against deployed AWS (`scripts/ws_smoke.py` section 10) rather than only in a local test. Worst case a user types the sentinel and gets an `error` frame.
