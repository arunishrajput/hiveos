# BUILD_PLAN.md — Phased roadmap

Seven phases, each sized for one Claude Code session. Strictly sequential except Phase 5, which is cuttable.

Every phase ends with: verify → update `PROGRESS.md` → update docs → inspect diff → commit → push → stop.

| # | Phase | Cuttable |
|---|---|---|
| 0 | Pre-project setup | No |
| 1 | WebSocket backbone | No |
| 2 | Scheduler + queue (no LLM) | No |
| 3 | Bedrock + agent + memory | No |
| 4 | Frontend HUD + public URL | No |
| 5 | Agent chat + 2D canvas | **Yes — cut first** |
| 6 | Demo readiness | No |

---

## Phase 0 — Pre-project setup

**Objective.** Every blocker resolved and the deployment pipeline proven before a single feature exists.

**Dependencies.** None.

### Tasks — in this order

1. **`MANUAL` Request Bedrock model access.** Start first; longest lead time. Console → Bedrock (`us-east-1`) → Model access → request Anthropic models. See `DEPLOYMENT.md` → Manual Action 2.
2. **`MANUAL` Configure AWS credentials.** `aws configure` or SSO. Verify: `aws sts get-caller-identity`.
3. **Verify Bedrock with a real call.** `aws bedrock list-inference-profiles`, then an actual `bedrock-runtime converse` that returns a completion. A list call proves nothing about entitlement. Record the exact working model ID in `CONTRACT.md`.
4. **`MANUAL` Start Docker Desktop.** Installed, daemon down. Required for `sam build --use-container`.
5. **Install SAM CLI.** `brew install aws-sam-cli`.
6. **Create an AWS Budget alarm** (~$20) as the backstop behind the in-app token ceiling.
7. **Inventory existing AWS resources** for name collisions on `hiveos*` across DynamoDB, SQS, Lambda, API Gateway, Amplify.
8. **Git and GitHub.** `git init`, `.gitignore`, `gh repo create`, initial commit, push.
9. **Deploy a minimal stack.** `template.yaml` with the DynamoDB table only → `sam build --use-container && sam deploy --guided`.
10. **Seed team metadata** — the `TEAM#alpha / METADATA` row with `token_budget` and `tokens_used = 0`.

**Primary files.** `template.yaml`, `samconfig.toml`, `.gitignore`, `scripts/seed.py`, `CONTRACT.md`

**Validation.**
- `aws sts get-caller-identity` returns an account
- A real `converse` call returns a completion
- `aws cloudformation describe-stacks --stack-name hiveos` shows `CREATE_COMPLETE`
- `put-item` / `get-item` round trip against the real table succeeds

**Completion criteria.** Stack deployed, table seeded, repo pushed, Bedrock model ID recorded. If Bedrock access is still pending, tasks 4–10 still proceed and the phase is marked `BLOCKED — WAITING FOR MANUAL ACTION` with the verification command in `PROGRESS.md`.

---

## Phase 1 — WebSocket backbone

**Objective.** Real-time broadcast working against deployed AWS, with stale connections handled correctly.

**Dependencies.** Phase 0 complete (stack exists).

### Tasks

1. Add the WebSocket API to `template.yaml` (`AWS::ApiGatewayV2::Api` with `ProtocolType: WEBSOCKET`, plus Integration, Routes, Deployment, Stage).
2. Router Lambda: `$connect` writes a `CONN#` row; `$disconnect` deletes it.
3. `broadcast_to_team()` in `backend/shared/` — **with the GoneException handler from day one** (`CONTRACT.md`).
4. `$default` route: echo/broadcast a test message so two clients can prove fan-out.
5. `state_snapshot` sent immediately on `$connect`.
6. Grant `execute-api:ManageConnections` in the Lambda IAM policy — a common and confusing omission.

**Primary files.** `template.yaml`, `backend/router/`, `backend/shared/broadcast.py`

**Validation.**
- Two `wscat` clients connect to the deployed `wss://` URL; a message from one reaches both
- Kill one client mid-broadcast; CloudWatch shows the GoneException branch firing and the `CONN#` row deleted
- No crash in the broadcast loop afterward

**Gate.** Two clients receive the same broadcast, and a dead connection is cleaned up without breaking delivery.

---

## Phase 2 — Scheduler and queue (no LLM)

**Objective.** The entire OS-scheduler mechanic proven **without** Bedrock latency or cost, using a stub echo agent.

**Dependencies.** Phase 1 complete.

### Tasks

1. Add SQS queue + DLQ to `template.yaml`; add the Agent Runner Lambda with an SQS event source.
2. Seed the two `AGENT#` slot rows as `IDLE`.
3. `claim_agent` handler: atomic conditional update per `CONTRACT.md`; on failure across all slots, write a `QUEUE#` item.
4. Queue position calculation and the `queue_update` broadcast.
5. **Stub agent** in the Runner — sleeps briefly, returns canned text, consumes no tokens.
6. Release logic in `try/finally`: set slot `IDLE`, dispatch the oldest `QUEUE#` item to SQS, delete that item, broadcast.

**Primary files.** `template.yaml`, `backend/router/`, `backend/agent_runner/`

**Validation.**
- Claim 1 → slot `coder` BUSY; claim 2 → slot `researcher` BUSY; claim 3 → `QUEUE#` item written and position 1 broadcast
- On completion of claim 1, the queued task is auto-dispatched and its slot goes BUSY
- Force the stub agent to raise — the slot still releases (no leak)
- DynamoDB inspected directly to confirm slot and queue state

**Gate.** Third claim queues; auto-dispatch fires on release; a failing task never leaks a slot.

> This is the highest-value phase. The queue mechanic *is* the product. Proving it without an LLM in the loop keeps it fast to iterate and impossible to blame on model latency.

---

## Phase 3 — Bedrock, agent, and memory

**Objective.** Replace the stub with a real agent; make the token meter real and enforced.

**Dependencies.** Phase 2 complete; Bedrock access verified in Phase 0.

### Tasks

1. Add Bedrock invoke permissions to the Agent Runner IAM role.
2. Integrate Strands Agents SDK. **Timebox packaging to one hour** — then fall back to boto3 `converse` per `ARCHITECTURE.md` decision 7. Record which path was taken.
3. Implement the three tools: `get_team_memory`, `set_team_memory`, `get_task_context`.
4. Load team memory into the system prompt **before** the model call.
5. Token accounting — read usage from the Bedrock response, `ADD` to `tokens_used`, broadcast `token_update`.
6. **Budget ceiling** — refuse to invoke Bedrock at 100%; broadcast `budget_exhausted`.
7. Cap `max_tokens` per call.

**Primary files.** `backend/agent_runner/`, `backend/shared/memory.py`, `template.yaml`, `CONTRACT.md`

**Validation.**
- A real task returns a real model response over WebSocket
- `tokens_used` delta matches the usage reported by Bedrock
- With `tokens_used` manually set at the ceiling, Bedrock is **not** called and `budget_exhausted` is broadcast
- User A saves a fact; User B's subsequent agent response reflects it without being told

**Gate.** Real agent response, accurate token accounting, enforced ceiling, memory crossing between users.

---

## Phase 4 — Frontend HUD and public URL

**Objective.** End-to-end deployed MVP. A judge can open a URL cold and see it working.

**Dependencies.** Phase 3 complete.

### Tasks

1. Vite + React app in `frontend/`.
2. WebSocket client: connect, render from `state_snapshot`, apply incremental events, auto-reconnect.
3. HUD — token meter (green <50%, amber 50–80%, red >80%), slot badges, queue position.
4. Name picker on entry; "Get Agent" button; task prompt input.
5. Build and deploy to Amplify Hosting via CLI (`create-app` → `create-branch` → `start-deployment` with a zip — no GitHub OAuth needed).
6. Record the public URL in `PROGRESS.md` and `README.md`.

**Primary files.** `frontend/`, `scripts/deploy-frontend.sh`, `DEPLOYMENT.md`

**Validation.**
- Public HTTPS URL opens in a fresh incognito window with zero local setup
- Two browsers side by side show identical token meter, slot states, and queue position
- Claiming in one browser visibly updates the other within ~2 seconds

**Gate.** **Deployed end-to-end MVP.** Everything after this point is enhancement. If time runs out here, there is still a submission.

---

## Phase 5 — Agent chat and 2D canvas *(cuttable)*

**Objective.** The visual workspace layer.

**Dependencies.** Phase 4 complete.

**Cut this entire phase if Phase 3 or 4 overran.** The HUD is the product; this is the wrapper.

> **Built, 2026-09-18.** Not cut. Phase 3 is blocked by an AWS account restriction rather than
> overrun, and every MVP-Critical item was finished and verified with two days left — the
> condition `CLAUDE.md` says MVP-Supporting work should be built under. "Blocked externally" is
> not "ran out of time"; conflating them cost an unnecessary cut. See `PROGRESS.md`.

### Tasks

1. Sidebar: agent chat, response display, "thinking" indicator, team memory facts list.
2. 2D canvas — fixed-size div, absolutely positioned character divs, CSS transitions on x/y.
3. `move_avatar` wired through the existing broadcast path.
4. Memory-saved toast on all connected browsers.
5. Per-task token cost shown on completion.

**Primary files.** `frontend/`

**Validation.** Two browsers see each other's avatars move; chat renders; memory toast appears on both.

**Gate.** Nothing downstream depends on this phase.

---

## Phase 6 — Demo readiness

**Objective.** Record and submit. **No new features.**

**Dependencies.** Phase 4 complete (Phase 5 optional).

### Tasks

1. Seed demo data — three members, clean token budget, empty queue.
2. `scripts/reset-demo.py` to restore a known state between takes.
3. Pre-warm both Lambdas immediately before recording.
4. Rehearse the full 3-minute script twice, end to end, without intervention.
5. Fix only what breaks during rehearsal.
6. Record in a single clean take; three browser windows visible.
7. Upload to YouTube (public or unlisted); **verify the link opens in a signed-out browser**.
8. Write the submission writeup: problem, build, where AWS fits, what was learned, AI tools used.
9. Submit before the deadline.

**Validation.**
- Full demo sequence runs twice without intervention
- Video is under 3 minutes and shows every claimed feature
- Public URL works from a device that has never visited it
- Repo is public and its history matches the event dates

**Gate.** Video and URL submitted.

### Demo script beats

| Time | Beat |
|---|---|
| 0:00–0:25 | The problem — Uber burned its 2026 AI budget in four months; 79% of enterprises had overruns; only 36% have controls. Address Munder Difflin: *local harness for one dev's own CLI agents vs. cloud governance layer for a team.* |
| 0:25–0:45 | Three browsers, one workspace. The token meter is identical on every screen. |
| 0:45–1:30 | **The queue moment.** Two claims fill both slots; the meter ticks; a third user gets a real position. |
| 1:30–2:15 | **The memory moment.** Alice saves a team fact; a badge appears everywhere; a slot frees; Charlie is auto-dispatched and his agent already knows the fact. |
| 2:15–2:45 | Where AWS fits — API Gateway WebSocket, Lambda, SQS, DynamoDB, Bedrock, Amplify. Use the accurate SQS wording from `ARCHITECTURE.md`. |
| 2:45–3:00 | What was learned. |

### Fallback ladder

Fix only what is broken. **Never add features to rescue a demo.**
1. HUD works → demo the HUD only
2. WebSocket broken → record components separately
3. Bedrock unavailable → mock responses, stated honestly

---

## Phase 7 — Canvas-first workspace *(added 2026-09-18, user decision)*

**Objective.** Invert the interface hierarchy so the pixel-art office floor is the primary
surface and the HUD becomes chrome over it. Reference aesthetic: Munder Difflin — pixel art,
**top-down, not isometric**.

**Dependencies.** Phases 1–6 complete. Branch `feat/pixel-canvas` off `main`.

**Why this exists.** Phase 5 built a working floor, but a 100 px strip inside a 760 px vertical
panel stack reads as a dashboard with a decoration in it, whatever is drawn inside. The feel
being aimed at comes from the *world being the interface*, which is a shell change, not a
component restyle.

### Non-negotiables

- **Frontend only.** `components.jsx`, `App.jsx`, `styles.css`. No backend, no protocol, no
  `CONTRACT.md` edits. Every event needed already exists and is verified.
- **Coordinates stay percentages (0–100).** `CONTRACT.md` line 168. Desks and decor are
  positioned in percentages too, or they drift out of alignment with the pawns at other widths.
- **`ws_smoke.py` 58/58 before merge.** Close every browser tab on the deployed URL first, or
  four connection-leak checks fail for unrelated reasons.
- **Verify with a screenshot, not `scrollHeight === innerHeight`.** That measurement has already
  reported success once for a layout `overflow: hidden` had amputated.

### Slices — in this order, each leaving a working app

Ordered so the risky restructure is **last and cuttable**. Stop after any slice and the app
still works and still demos.

1. **Floor foundation.** Grow the floor to the hero surface. Checkerboard tile pattern, desk
   rectangles at the two slot positions, CSS monitor shapes, plant/decor in the corners. No
   sprite or layout changes yet. *Pure addition — biggest visible win per hour.*
2. **Pixel sprites.** Replace the emoji pawns with CSS `box-shadow` 16×16 sprites, three
   designs, 2-frame idle/busy via `@keyframes`. Keep `translate(-50%, -50%)` centring and the
   `busyUsers` flag driving the busy frame.
3. **Desks wired to slot state.** A desk's monitor lights up while its slot is BUSY and shows
   who holds it. This is the slice that makes the floor *mean* something rather than decorate —
   the scheduler becomes visible in the world.
4. **Chrome inversion.** Quota meter to a top bar, member status bar along the bottom, remaining
   panels collapsed or moved around the canvas. *The risky one. Everything above ships without
   it.*
5. **Demo format.** Re-measure the board, pick the new window size, update `DEMO.md`'s window
   dimensions and pre-flight, re-run `rehearse.py --takes 2`.

### Validation

- `python scripts/ws_smoke.py` → 58/58
- `python scripts/rehearse.py --takes 2` → 12/12 twice
- Screenshot at the demo window size with nothing clipped and no horizontal scroll
- Sprites legible at **actual recording size**, not at desktop zoom
- Two browsers still agree on every avatar position

**Gate.** The floor reads as a room, the scheduler is visible in it, and the demo still passes.

> **Feature freeze with 6 hours left on the clock, whatever state this is in.** The submission
> is already complete and banked on `main` (`df8282a`); Phase 7 is upside. If it is not merged
> and rehearsed by the freeze, record from `main` and ship that.

---

## Phase 8 — Depth pass *(added 2026-09-18, user decision)*

**Objective.** Close the gaps between what HiveOS *claims* and what it does, and stop the app
living in a 760 px column.

**Dependencies.** Phase 7 merged and deployed.

### Slices — in this order

Ordered so each lands on top of a verified state, and so the shell exists before anything new is
put inside it.

1. **Avatar identity (bug).** The marker chosen at the entry gate is ignored on the floor — the
   sprite is picked by `index % 3`, so two people can look identical and *your own character
   changes when somebody joins or leaves*. Key the sprite on the chosen avatar, stable per
   `user_id`. Frontend only.
2. **Full-screen responsive shell.** `.board` is capped at 760 px. Go to a real app layout on
   wide screens — room large, side rail for activity/memory/request, quota across the top,
   members across the bottom — collapsing to today's single column below ~1100 px.
   **Responsive, not fixed-wide**, so three 640 px windows still work for a side-by-side demo.
   Frontend only.
3. **Task history + spend audit.** A `TASK#` entity: who ran what, what it cost, when. This is
   what a governance product is actually for, and it is the reason `get_task_context` was never
   built. Unlocks a per-user spend breakdown. Backend + `CONTRACT.md` + a panel.
4. **Per-user fairness.** The pitch is *fair queueing* and OS-style scheduling; the mechanism is
   one shared pool and FIFO. Nothing stops one person taking slots turn after turn and starving
   the rest. Add a per-user allowance or round-robin so the scheduler matches the claim.
   Backend + `CONTRACT.md`.
5. **Real tool calling.** The model decides to call `set_team_memory` itself, instead of
   `memory.directive()` parsing `remember: k = v`. The last place the agent differs in *kind*
   from a real one. Backend only; the regex stays as the fallback path.

### Non-negotiables

- `ws_smoke.py` green before each slice is committed. Close every browser tab on the deployed
  URL first, or the connection-leak checks fail for unrelated reasons.
- Slices 3 and 4 change the protocol or the schema — `CONTRACT.md` is updated **in the same
  commit**, never after.
- `main` holds a recordable submission at all times. Anything risky goes on a branch.

**Gate.** Each slice: verified against deployed AWS, `rehearse.py --takes 2` still 12/12.

---

## Phases 12–16 — The expansion *(added 2026-09-19, user decision)*

**Context.** Phases 9–11 closed with a submittable product. The user chose to spend the
remaining window expanding rather than recording, taking
[Munder Difflin](https://munderdiffl.in/) as the reference for finish: a warm light "paper
office", a real public front door, and a floor with named agents working in rooms.

**What is borrowed and what is not.** Munder Difflin is a *local* harness — one person, many
clones, on their own machine. HiveOS is the cloud inverse — many people, one shared budget. The
expansion borrows the **finish**, never the architecture: nothing here moves HiveOS toward being
a CLI harness, and the never-build list in `CLAUDE.md` still stands.

**Ordering rationale.** The reskin is first because everything after it is built in the new
palette and would otherwise be painted twice. The landing page is second because it is the
highest-value thing a judge sees and it is independent of the backend. Named agents are third
because the floor rebuild needs identities to put in rooms, and the handoff needs both.

| # | Phase | Touches | Depends on |
|---|---|---|---|
| 12 | Paper-office light theme | frontend only | — |
| 13 | Public landing page | frontend only | 12 |
| 14 | Named agents at each desk | backend + `CONTRACT.md` + frontend | 12 |
| 15 | Multi-room floor rebuild | frontend only | 12, 14 |
| 16 | Agent-to-agent handoff | backend + `CONTRACT.md` + frontend | 14, 15 |

### Phase 12 — Paper-office light theme

**Objective.** Re-tokenise the whole app from the graphite operator console to a warm light
theme, so the later phases have one palette to build in.

The colour rule that governs everything after this: **brand amber is a fill, never text; state
hues are text-weight.** `#ffca54` on cream is 1.6:1 and cannot carry a word; darkened jade,
ochre, blue and red carry every machine-state label. The two never collide — nothing amber
means anything, and nothing meaningful is brand amber. It is written at the top of `styles.css`
and is the first thing to read before touching colour in this project.

### Phase 13 — Public landing page

**Objective.** A front door at `/`, with the workspace behind an "Enter the workspace" CTA.
Hero, the cost-overrun evidence already written up in `SUBMISSION.md`, how-it-works, a live
board preview, footer. Alternating cream/sand bands; one ink-dark terminal card, which is the
one place the old graphite is allowed back.

**Watch for.** The workspace is currently mounted at `/` with an entry gate. Moving it behind a
route must not break the deep link a judge is given, and Amplify's SPA rewrite already returns
`404-200` on deep links (harmless — see `PROGRESS.md`).

### Phase 14 — Named agents at each desk

**Objective.** Slots stop being interchangeable. Each desk holds a named agent with a role and
a system prompt; the requester picks one; the ledger records which agent ran the task.

**Schema and protocol change** — `CONTRACT.md` in the same commit.

> **Done, 2026-09-19.** `coder` and `researcher` are the desks of **Ada** and **Iris**. The
> roster lives in `backend/shared/agents.py` rather than in DynamoDB — the `AGENT#` rows are
> written conditionally, so names on the row would have needed a backfill for every existing
> workspace. The phase's real find was in the ledger: the SQS message carried the *requested*
> agent and the runner recorded it as the one that ran the task, which was a harmless mislabel
> while the slots were interchangeable and a misattribution the moment they had names. See
> `PROGRESS.md`.

### Phase 15 — Multi-room floor rebuild

**Objective.** Replace the single open floor with a multi-room office — project rooms, a desk
bank, a waiting area where queued members visibly wait — and a camera that scales it.

**This is the highest-risk phase in the expansion.** The floor took two phases to get right the
first time. It goes on a branch, and `main` keeps a recordable build throughout.

> **Done, 2026-09-19.** Two project rooms against the back wall with a corridor between them,
> and a waiting area below where queued members stand in queue order. The rooms were the
> visible half; the **waiting area was the meaningful one** — a queued member is placed by
> exactly the mechanism that seats a slot holder at a desk, so dispatch off the front of the
> queue became a walk out of the waiting area and into a room, with no protocol change at all.
> The camera is the existing `--furn` knob, raised 1.45 → 1.8 on wide screens because the plan
> is in percentages and the rooms grew with the floor while the furniture did not.
>
> **The column was not re-laid, deliberately.** The floor stayed 250px and the rebuild happened
> inside it, so the 838px measurement `DEMO.md` records still holds and this phase does not by
> itself invalidate the framing. The phase's real find was a Phase 12 leftover: pawn name labels
> carried a dark halo behind dark text, which one name on a tile field survives and three side
> by side in a waiting area does not. See `PROGRESS.md`.

### Phase 16 — Agent-to-agent handoff

**Objective.** An agent can pass work to another desk: an envelope crosses the floor, the
receiving agent picks it up, and both legs bill to the same team budget under one task id.

**The budget ceiling still governs the whole chain** — a handoff must not become a way to spend
past the ceiling one leg at a time. That check is the reason this phase is last.

> **Done, 2026-09-19.** `handoff_to_agent` is a real tool the model chooses to call; Ada passes
> a fact-finding question to Iris, an envelope crosses the corridor, and both legs write ledger
> rows under one `task_id`. The ceiling needed no new check — each leg meets the existing one
> immediately before its own model call, so a chain can overshoot by at most one leg exactly
> like a single task. The phase's two real finds were elsewhere: **a handoff must not fall back
> to another desk**, which made `pinned_slot` a queue-row concept and changed `take_next_task`
> from "take the next row" to "take the next row this desk may run"; and **the loop guard has to
> be the tool's absence, not an instruction** — verified against a prompt that explicitly told
> the two agents to pass the work back and forth, which still produced exactly two legs.
>
> It also surfaced a latent bug that was never about handoffs: `gpt-oss-120b` charges its
> reasoning tokens against `MAX_TOKENS_PER_CALL`, and at 400 a call spent 398 on reasoning and
> returned nothing — billing the team in full for a stubbed answer. Raised to 900. See
> `PROGRESS.md`.

---

## Phase 17 — The office *(added 2026-09-19, user decision)*

**Not a feature — a pivot.** The product was *a team queues for two shared agent slots*, and the
scheduler was the headline. It is now *a floor you staff*: agents are hired, named, briefed and
given a character, and they sit at desks people can watch. The scheduler, the fair queue and the
enforced ceiling did not go anywhere — they stopped being the pitch and became the governance
layer inside the office, which is a better pitch and was ~80% already built.

**What was settled before building, because it is not negotiable.** Munder Difflin spawns local
PTY processes running your own CLI agents against folders on your disk. A Lambda behind a public
URL cannot attach to a judge's terminal. This phase takes the reference's *interaction model* and
never its mechanism: every inspector tab is bound to data this board actually holds, and there is
no fake terminal anywhere.

**Shipped as two slices**, each deployed and verified before the next — the Phase 8 precedent, so
there was a submittable deliverable at every point.

1. **The shell** (`ff6a723`, frontend only). The 760 px panel column became a three-region app:
   title bar, floor filling the left at full height, one agent in depth on the right, every desk
   along the bottom. Zero backend files, so `ws_smoke.py` and `rehearse.py` stayed valid.
2. **The roster is data** (`edea677`, `77053e4`). `agents.py` was a fixed tuple, identical in
   every workspace; it is an `AGENT#` row per agent now, carrying identity beside the `status`
   and `current_user` it already held. `spawn_agent` / `dismiss_agent` are real actions any
   member may take, capped at `MAX_AGENTS`.

> **Done, 2026-09-19.** Deployed and verified against real AWS: hiring is live for everyone on
> the public URL (a second socket hired Dwight; a browser that never reloaded drew him seated and
> moved its app bar to `0/3 working`), a hired agent runs a real task credited by name, a
> dismissed agent's finished work stays attributed to it, and a floor cannot be emptied of every
> agent. `ws_smoke.py` **108/112** with 14 new hiring checks — the four failures are the
> documented live-visitor case. The Phase 16 handoff still crosses.
>
> **Five decisions are recorded in `ARCHITECTURE.md` 11 and 12**, including why `MAX_AGENTS` is
> 4 (measured against what the floor can draw, not chosen), why there is no migration, and why
> the engine step is a readout rather than a model picker.
>
> **This phase invalidated the demo framing.** Three 640×950 portrait windows, earned over Phases
> 7–15, cannot hold a landscape app shell — at 640 px it renders its stacked mobile layout.
> `DEMO.md` was re-measured and re-rehearsed against the deployed office in `d670fb2`, and
> `rehearse.py` gained the hiring beat: **15/15**, twice.

---

## If you are behind schedule

Cut in this order:
1. Phase 16, then 15, then 14 — the expansion is enhancement, and cutting from the back always
   leaves a coherent product. Phases 12 and 13 are what a judge sees in the first five seconds;
   cut those last.
2. Phase 5 entirely
3. Per-task cost breakdown, task history, announcements
4. The second agent slot — one slot still demonstrates queueing
5. Shared memory — the queue plus token meter alone still tells the story

**Never cut:** the deployed public URL, the token meter, or the demo video. Those three are the submission.
