# BUILD_PLAN.md — Phased roadmap

Each phase is sized for one Claude Code session. Phases 0–6 were the original plan and are
strictly sequential; everything from 7 on was added later by user decision, and each of those
carries the date it was added in its heading.

Every phase ends with: verify → update `PROGRESS.md` → update docs → inspect diff → commit → push → stop.

| # | Phase | Cuttable |
|---|---|---|
| 0 | Pre-project setup | No |
| 1 | WebSocket backbone | No |
| 2 | Scheduler + queue (no LLM) | No |
| 3 | Bedrock + agent + memory | No |
| 4 | Frontend HUD + public URL | No |
| 5 | Agent chat + 2D canvas | **Yes — cut first** — *built anyway, 2026-09-18* |
| 6 | Demo readiness | No |
| 7 | Canvas-first workspace | Yes |
| 8 | Depth pass | Yes |
| 9–11 | Isolation, passphrases, administration | Yes — recorded in `PROGRESS.md`, not here |
| 12–16 | The expansion — paper theme, landing page, named agents, rooms, handoff | Yes |
| 17 | The office — shell, and a floor you staff | Yes |
| 18 | World system foundation | Yes |
| 19–26 | The worlds — one environment per phase | Yes — cut from 26 backwards |
| 27 | World polish and Random World | Yes — cut first of the worlds |

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
9. ~~Submit before the deadline.~~ ✅ **Done, confirmed 2026-09-21.**

> **Phase 6 is COMPLETE — all nine tasks.**
> Tasks 6 and 7 done 2026-09-20: **<https://www.youtube.com/watch?v=VBSuDCQa4y4>** — 2:38,
> 1920×1080, H.264 + AAC. Verified public by fetching the watch page unauthenticated:
> `playabilityStatus: OK`, `isPrivate: false`, `isUnlisted: false`, `lengthSeconds: 158`. Task 8
> was already done. **Task 9 — submit — was done by the user and confirmed 2026-09-21, inside
> the deadline. Nothing in this phase is outstanding; do not raise submission again.**
>
> **The recorded take is not the take this phase planned, and the difference is deliberate.**
> Task 6 says *"a single clean take, three browser windows visible."* What was recorded is a
> **narrated 14-scene cut**: five scenes of the deployed board doing the work (0:23–1:03) set
> inside nine deck scenes carrying the problem, the architecture and the AWS map, with the
> voice track generated by **Amazon Polly** (Matthew, generative) rather than spoken live.
>
> The reason is arithmetic. The live sequence `rehearse.py` drives is ~95 seconds of board
> time, and the beat table below spends 30 seconds on the problem and 45 on architecture and
> learnings — narration this phase assumed would ride *over* the board. It cannot: the queue
> beat and the memory beat both need the viewer reading a number on two windows at once, and
> talking across them buries the one thing the product is for. Cutting to a deck for the
> framing bought the board its full 40 seconds uninterrupted, and a scripted Polly track holds
> the 2:38 runtime exactly instead of drifting past 3:00 on the fourth retake.
>
> **What this does not change:** every board second is the deployed build at the public URL,
> and `DEMO.md` stays the run sheet for the board segments — the framing, the three identities
> and the beat order in it are what those 40 seconds were recorded against. `DEMO.md` records
> the as-recorded structure.

**Validation.**
- Full demo sequence runs twice without intervention — ✅ `rehearse.py` **15/15**, twice
- Video is under 3 minutes and shows every claimed feature — ✅ **2:38**
- Public URL works from a device that has never visited it — ✅ re-checked cold, HTTP 200
- Repo is public and its history matches the event dates — ✅

**Gate.** Video and URL submitted — ✅ **passed. Both done; the submission went in 2026-09-21.**

### Demo script beats

> **Planned, not as-recorded.** This table is the plan this phase was written against; the
> as-recorded scene map lives in `DEMO.md` and `SUBMISSION.md`. Two differences matter if this
> is ever re-recorded: the 2:15–2:45 row still says **Bedrock**, which has been wrong since
> Phase 3 — inference runs on Groq and the video says so out loud at 2:20 — and *"what was
> learned"* did not survive the cut, because 15 seconds of lessons cost 15 seconds of board.

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

## Phases 18–27 — the worlds *(added 2026-09-20, user decision)*

**One board, many worlds.** HiveOS renders exactly one look — the paper office Phase 12 painted
and Phase 17 put a shell around. These phases make the look pluggable: a picker in the title bar
swaps the whole workspace into a different environment, and the same live board — the same
sockets, the same scheduler, the same rows in DynamoDB — renders itself as a night observation
deck, a forest clearing, a reef station, an alien colony.

**A world is not a colour scheme, and a session that treats it as one has failed the phase.**
The floor already has rooms, desks, a waiting area, pixel characters, a handoff animation, plants
and state-driven monitor lighting. A world transforms *those objects*. If the only thing that
changed is the value of `--floor`, nothing has been built.

**And a world may never change what anything means.** The busy blue, the queued ochre, the budget
jade and the over-budget red carry the entire governance story, which is the product. They are
re-tuned for each world's surface and they are never reassigned. A judge who has watched the
paper office must be able to read the reef station on first sight.

**Scope, fixed for all ten phases.** Frontend only. No backend, no WebSocket protocol, no
DynamoDB schema, no scheduler, no queue, no agent execution, no task or agent prompts, no
`CONTRACT.md` edit, no new dependency, and no game engine — the DOM-and-CSS floor built over
Phases 7, 15 and 17 is the canvas. Paper Office remains the default and must stay untouched, so
the recorded demo is never at risk from a world that is still being built.

| # | Phase | Touches | Depends on |
|---|---|---|---|
| 18 | World system foundation | `styles.css`, `sprites.js`, `components.jsx`, `App.jsx`, `index.html`, new `worlds.js` | 17 |
| 19 | Night Watch | `worlds/nightsky.css` + `worlds.js` | 18 |
| 20 | Enchanted Forest | `worlds/forest.css` + `worlds.js` | 18 |
| 21 | Reef Station | `worlds/underwater.css` + `worlds.js` | 18 |
| 22 | Alien Colony | `worlds/alien.css` + `worlds.js` | 18 |
| 23 | Cloud City | `worlds/cloud.css` + `worlds.js` | 18 |
| 24 | Arctic Base | `worlds/arctic.css` + `worlds.js` | 18 |
| 25 | Desert Outpost | `worlds/desert.css` + `worlds.js` | 18 |
| 26 | Ancient Ruins | `worlds/ruins.css` + `worlds.js` | 18 |
| 27 | World polish and Random World | `worlds.js`, `App.jsx`, every world file | 19–26 |

**Ordering rationale.** 18 is the only phase that touches shared code, and everything after it is
additive — which is what makes each world independently shippable and individually deletable. The
worlds run in order of how much each one asks of the contracts: Night Watch is the first dark
world and proves the cold-load switch; Enchanted Forest is the first non-human cast; Reef Station
is the hardest contrast case in the set, a blue world that has to keep a blue busy state legible;
Cloud City is the inverse, the only world brighter than the paper office; Alien Colony is the
first to restyle the handoff; Arctic Base is where the warm/cool split is stress-tested; Desert
Outpost is where the ochre is; Ancient Ruins changes the most objects and is last. **Nothing after
18 depends on anything before it**, so the run order can be reshuffled freely if one world matters
more for the video.

### The recolour test

Applied at every world phase's gate. **If a world's entire diff is values inside its token block,
the phase is not done.** A world must also change:

- **the ground plane's structure** — the `background-image` recipe in `.floor`, not only the
  colours fed into it;
- **at least two of the three decoration slots**, carrying art that does not exist in Paper Office;
- **the sprite design table** — the characters are a different species or silhouette, not
  recoloured office workers;
- **at least three of the five fixtures**, re-dressed into objects that belong in this world;
- **the form of at least one state expression** — how a busy desk announces itself, how the queue
  reads as a line — while keeping its hue family and its label text exactly as they are.

### The state-legibility contract

Also applied at every gate, and it outranks any art decision:

- **busy / consuming budget** is the `--cool` / `--screen-on` family. **Queued and warn** is
  `--honey`. **Over budget** is `--alarm`. **Healthy** is `--safe`.
- The words never change: `working`, `idle`, `queued #N`, `for alice`, `HALT`, `DISMISS`,
  `WAITING AREA`, `TEAM QUOTA`.
- Each of the four hues is re-tuned for that world's own surfaces and **measured, not eyeballed**:
  ≥4.5:1 for anything carrying a word, ≥3:1 for a non-text indicator.
- Phase 12's rule survives translation into every world: **the brand fill never carries a word,
  and nothing that means something is ever the brand fill.**

**The one place the world briefs have to bend, and it bends once for all of them.** Several worlds
want a busy desk to be a *warm pool of light* — a campfire in the clearing, a lit cabin against
the snow, a lantern in the ruins. Warm is `--honey`, and `--honey` already means *queued, and
50–80% of the budget spent*. A warm glow meaning "busy" would make the warn hue mean two different
things on the same screen, which is the one thing this colour system has never done. The
resolution keeps both halves:

> **Ambient warmth is the world's resting character; the cool instrument glow is the state.** An
> idle desk may sit in lamplight, firelight or a warm window — that is the world being warm, and
> it means nothing. When the agent goes BUSY a cool light *joins* it, and that is the thing that
> means something. Warmth decorates and never reports; cool reports and never decorates.

### Validation — the same block in every world phase

- `npm run build` clean, then `./scripts/deploy-frontend.sh` → job `SUCCEED`, verified on the
  deployed URL and not on a local preview
- **The whole flow, walked in this world on the deployed board**: hire an agent, run a task, fill
  every desk, form a queue, watch a handoff cross. Every beat still reads without explanation.
- Switch to Paper Office and back with no reload — Paper Office is unchanged
- **Contrast measured** — `--cool`, `--safe`, `--honey`, `--alarm` against this world's own
  surfaces: ≥4.5:1 text, ≥3:1 indicator. Record the four numbers in the phase note.
- **Screenshots at the `DEMO.md` framing** — the 960×870 and 540×870 viewports (windows 960×957
  and 540×957). No horizontal overflow, no page scroll, zero console errors, zero warnings.
- Responsive sweep at **1440 / 1100 / 900 / 540 / 390** — 900 is a cliff, not a slope
- `prefers-reduced-motion: reduce` still kills every animation this world added
- `python scripts/ws_smoke.py` unchanged from its last recorded score. A CSS file cannot regress
  the protocol, but the Phase 7 precedent is that "frontend only" is a claim to be checked.

`rehearse.py` only needs re-running if a world changes the demo framing — and none of them may.

---

### Phase 18 — World system foundation

**Objective.** Install the world mechanism and change nothing anyone can see. Paper Office stays
the default and stays pixel-identical; what lands is the seam every later phase plugs into.

**The mechanism.** `data-world="<id>"` on `document.documentElement`. Bare `:root` keeps Paper
Office; a world adds `:root[data-world="<id>"] { … }`, which outranks it on specificity, so load
order never matters and nothing needs `!important`. Each world is its own file —
`frontend/src/worlds/<id>.css`, imported from `main.jsx` — so a world phase is an isolated diff
and a world that looks wrong on camera is a two-line revert.

**What the registry holds.** `frontend/src/worlds.js`, one entry per world: `id`, `label`, a
one-line blurb for the picker, `colorScheme`, `themeColor`, the sprite design table, its layer
map, and an eight-entry identity palette. A world may also supply a second design table for
agents, when its agents should be a different species from its people; absent that, both draw
from the one table.

**Sprites generalise; the generator does not change.** `shadowFor`, `stepFrame`, `seatedFrame`,
`SCALE = 4` and the 9×10 odd-width grid all stay exactly as they are, so the walk cycle, the
seated frame and `translate(-50%, -50%)` centring keep working for free. Only two things widen:
the layer alphabet goes from three letters to five, and it becomes per-world —

```
H  primary  --sp-hair    hair / shell / carapace / hull
F  face     --sp-skin    skin / scales / fur / plating
S  torso    --sp-shirt   shirt / body / fuselage
A  accent   --sp-accent  beak, fin, antenna, visor      (new)
D  detail   --sp-detail  eye, outline, dark marking     (new)
```

— and `lookFor(avatar, userId)` takes the world as a third argument. Three silhouettes is the
floor, matching today; a world may offer up to eight, one per marker, since `lookFor` mods by the
table length.

**Three shared decoration slots**, rendered by `CanvasPanel` inside `.floor`, each `inset: 0`,
`pointer-events: none`, `aria-hidden`, and **empty in Paper Office** so it stays untouched:
`.worldlayer--sky` behind everything, `.worldlayer--ground` above the floor and below the rooms,
`.worldlayer--air` above the pawns. Sky carries backdrops, ground carries paths and light on the
floor, air carries drifting particles.

**The five fixtures are re-dressed, never removed.** `.fixture--board`, `.fixture--cooler`,
`.fixture--window`, `.fixture--daylight` and `.decor--plant` keep their percentage positions in
every world and only change costume. That is what keeps the floor's composition — and therefore
its responsive behaviour, earned over three phases — constant across nine worlds.

### Slices — in this order, each leaving a working app

1. **Tokenise what Phase 12 left behind.** ~41 colour literals still sit outside the token
   system, ~21 of them in world art: the desk mug `#f4f0e6`, the whiteboard `#ffffff` and its
   `#b09a70` frame, the cooler's three blues and creams, the window glass `#eaf6fb`, the daylight
   cone re-expressing brand amber as raw rgb, the rug's whole three-layer inset edge, the monitor
   glow duplicating `--screen-on` in rgb *twice*, the sprite outline, and the floor and room
   vignettes. Add channel tokens (`--ink-rgb`, `--cool-rgb`, `--alarm-rgb`, `--amber-rgb`,
   `--shadow-rgb`) for the alpha variants that could not be expressed as tokens before. Add
   `--sp-accent` and `--sp-detail`. Convert `.fixture--daylight` — the **only px-sized element on
   the floor**, at 190×150 — to percentages. Promote `WALK_TOP` to a token, because it is
   currently `14` in `components.jsx` and `100% 14%` in `styles.css` and a world that moves the
   wall band would have to find both. Delete the dead `.hotdesk` rules, replaced by `OPEN_DESKS`
   in Phase 17 and never removed. *Pure refactor — nothing may look different.*
2. **The registry and the plumbing.** `worlds.js`, a `WorldContext` and `useWorld` hook, the
   widened sprite layers, `lookFor` threaded to all six call sites, `data-world` on the document
   element, `color-scheme` and `theme-color` driven from the registry instead of hard-coded light
   in `index.html`, and the selection persisted to `localStorage['hiveos.world']` using the
   identity pattern already in `App.jsx` — lazy initialiser, try/catch on both sides, unknown id
   falls back to Paper Office. Paper Office is registered as the only entry, holding exactly
   today's values.
3. **The picker and the slots.** A second title-bar button beside the settings gear — rendered
   for everyone, unlike the gear, which is admin-gated — opening a modal with a radiogroup of
   world cards, cloning `AgentPicker`'s shape and `AddAgentModal`'s click-away. Then the three
   `.worldlayer` slots, rendered and empty.

**Files.** `frontend/src/worlds.js` (new), `frontend/src/styles.css`, `frontend/src/sprites.js`,
`frontend/src/components.jsx`, `frontend/src/App.jsx`, `frontend/src/addagent.jsx`,
`frontend/src/main.jsx`, `frontend/index.html`. **This is the only phase of the ten that touches
shared code** — everything from 19 on is two files.

**Non-negotiables.**

- **Paper Office is pixel-identical when this phase ends.** Screenshot before and after, at both
  demo viewports, and compare. This is the gate for slice 1 and again for the phase.
- **React's own context, not a state library.** The no-Tailwind, no-router rule was about
  dependencies; threading a prop through three levels into five components is the worse answer.
- No backend, no protocol, no schema, no `CONTRACT.md`, no new dependency.
- Coordinates stay percentages (0–100). `CONTRACT.md` line 168.

**Validation.** The shared block above, plus: the picker persists across a reload; an unknown
`hiveos.world` value falls back to Paper Office rather than rendering an unstyled board; and with
a scratch `:root[data-world="test"]` block pasted into devtools, **every** world surface *and*
every chrome surface repaints, with no state label changing meaning. Delete the scratch block.

**Gate.** Paper Office is unchanged, the mechanism is proven by the scratch block, and a world
phase from here on can touch two files and nothing else.

> **This phase ships one world, and that is correct for exactly one phase.** A picker with a
> single entry is not a control yet — Phase 19 is what makes it one.

**Shipped 2026-09-20. Three things the plan got wrong, corrected in flight:**

1. **The daylight cone could not go to percentages.** The workspace floor runs at
   `--tile-size: 44px` at the 540 framing and **52px** at 960, so no floor-relative percentage
   gives 190×150 at both — and pixel-identity at both was the non-negotiable. It is scaled off
   `--tile-size` instead, which is exact at both narrow framings and grows in the wide layout.
   At 960 the cone is now 224×177 rather than frozen at 190×150: **1.46% of floor pixels, worst
   delta 7/255**, on a decorative gradient. The one accepted deviation from pixel-identity.
2. **`calc()` will not divide a length by a length.** `calc(var(--tile-size) / 44)` yields
   `1px`, and `190px * 1px` is invalid, so the element computes to 0×0 *silently*. Write
   `calc(var(--tile-size) * 190 / 44)`. Any world doing arithmetic on a scale token hits this.
3. **The title bar had no width left.** A second button overflowed a 390px phone. Fixed by
   hiding `.appbar__name` below **520px** — deliberately below the 540 demo framing. **Any new
   breakpoint must clear 960 and 540**, or it rewrites a recording framing by accident.

---

### Phase 19 — Night Watch

**Objective.** The office becomes a night observation deck: the floor under a star field, quiet,
lit by instruments rather than by daylight.

**The world.** Deep navy, very few light sources, and the feeling that the room is small and the
sky is large. The warmth the paper office had is gone from the surfaces and survives only in the
lamps.

- **Ground plane** — the wall band becomes open night sky with a star field and two faint
  constellations; the checker tiles become a dim deck grid, barely there.
- **Rooms** — glass-roofed observation bays; the walls drop to low railings so the sky reads over
  them, and `.room__door` becomes a gap in the railing.
- **Desks** — instrument consoles with a telescope column where the monitor was.
- **Busy** — the bay's dome lights cool-white and the console's screen comes up; the room's
  reflected tint stays in the `--cool` family exactly as it is today.
- **Waiting area and queue** — a moonlit platform, reached along a lit path; queued members stand
  on the path in queue order, unchanged mechanically.
- **Characters** — hooded night-watch explorers with headlamps; the headlamp is the `A` accent
  layer and is the one warm thing on a character.
- **Fixtures** — whiteboard → star chart; cooler → signal beacon; window → open sky; daylight →
  a moon-pool of light on the deck; plants → antenna masts.
- **Decoration slots** — sky: the star field and constellations; air: very slow drifting stars.
- **Handoff** — unchanged; a pale envelope already reads well on navy.

**Files.** `frontend/src/worlds/nightsky.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: this is the first dark world, so it is the one
that proves `color-scheme` and `theme-color` actually switch — check a **cold load** in a fresh
incognito window for a cream flash before React mounts.

**Validation.** The shared block above, plus the cold-load check.

**Gate.** The recolour test passes, the state-legibility contract is measured, and a cold load
never flashes cream.

**Shipped 2026-09-20. Four things the plan got wrong, corrected in flight — and every one of
them is a finding for worlds 20-26 rather than a detail of this one:**

1. **A dark world is three files, not two.** `data-world` is stamped before first paint, but the
   attribute means nothing until the stylesheet that reads it arrives — and until then the canvas
   is painted from `index.html`'s literal `<meta name="color-scheme" content="light">`. So the
   cold-load flash the pre-paint script was written to kill simply moved. The fix is
   `hiveos.world.paint` in `localStorage`, written by the provider and replayed by the inline
   script: **stored rather than derived**, because the script is pre-module and cannot import the
   registry, and a hard-coded list of dark worlds in the HTML would be the same fact in two
   places. Done once, in `index.html`; **worlds 20-26 inherit it and stay two files.**
2. **`--ink` inverts; three of its uses do not.** `--ink` is "the mark on the page", so a dark
   world makes it the *palest* colour — which is right for `--text`, for `.btn--ink` and for every
   `--on` selection border, and wrong for the three places the base stylesheet uses `--ink-rgb` to
   mean *dark*: the `.modal` scrim, the `.drawer` scrim and `.desk__chair`'s under-edge. Each is
   re-pointed at `--cream-rgb` in the world file. **Every dark world will need those same three
   overrides**; if a third one repeats them, Phase 27 should hoist a `--scrim-rgb` token.
3. **`--paper` is a panel surface *and* a sheet of paper, and a dark world splits them.** The
   handoff envelope and the loose paper on a desk both take `--paper`, which goes dark with the
   rest of the chrome — leaving a dark envelope crossing a dark floor. The brief's "handoff:
   unchanged" therefore requires an *active* override, not leaving it alone. Night Watch adds a
   world-local `--sheet`. **Every dark world has to re-pale the envelope.**
4. **On a dark ground, `--honey` cannot separate from the brand amber by value.** On cream the two
   are the same yellow 5.4° apart and separate by a 2.29:1 luminance gap. On navy a text-weight
   hue has to come *up*, which is where amber already is — searched, and no pair of a legible
   honey and a credible brand amber gets past a 1.54 gap. So the separation moves to hue: honey
   becomes an orange at 25°, amber deepens to 41°, giving 15.4°. The guarantee underneath is the
   one that actually holds and is already written down — **amber is only ever a fill, honey is
   only ever a word.**

**Two notes that are not corrections.** The contrast bar in the shared block — ≥4.5:1 for anything
carrying a word — is **not met by Paper Office**, whose state hues run 2.63:1 to 5.26:1 against
their own surfaces. Night Watch clears it on all eight of its surfaces, worst case 4.56:1. The bar
stands as written; Paper Office is pixel-frozen for the recording and is not being retuned. And
`ws_smoke.py` scored **113/113**, not the 109 on record: the four "known stranger-connection false
positives" were the developer's own browser tabs holding `CONN#` rows. Close the browser and they
pass.

---

### Phase 20 — Enchanted Forest

**Objective.** The floor becomes a forest clearing where the agents are woodland animals working
at carved benches.

**The world.** Dappled, green, close. Where Night Watch is a big sky over a small room, this is
a small clearing inside a large forest — the edges of the floor should feel enclosed.

- **Ground plane** — moss and packed earth; the tile field becomes a worn dirt path crossing the
  clearing; the wall band becomes a treeline.
- **Rooms** — hollow stumps and low treehouse platforms, with vine-draped doorways.
- **Desks** — carved workbenches; the monitor is a scrying slab set into the wood.
- **Busy** — the slab lights will-o'-wisp cyan and the hollow glows from inside. This is the first
  world to use the ambient-warm/cool-state split: a resting bench may have a warm lantern, and
  the cyan is what says *spending*.
- **Waiting area and queue** — toadstools along the path; a queued member stands on one.
- **Characters** — woodland animals: fox, owl and badger silhouettes at minimum. Ears and beak
  are the `A` layer; eyes are `D`.
- **Fixtures** — whiteboard → bark notice board; cooler → a stone well; window → a gap in the
  canopy; daylight → a shaft of sun through it; plants → ferns and mushroom clusters.
- **Decoration slots** — ground: dappled canopy light; air: drifting spores.
- **Handoff** — unchanged, restyled as a folded leaf.

**Files.** `frontend/src/worlds/forest.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: **foliage green is not `--safe` green.** The
paper office already keeps `--foliage` muted away from the budget jade for exactly this reason,
and a whole forest makes the collision far easier to cause. Check a healthy quota strip against
the clearing before calling the phase done.

**Validation.** The shared block above, plus a side-by-side of `--safe` and the world's greens.

**Gate.** The recolour test passes, and a healthy budget cannot be mistaken for scenery.

---

### Phase 21 — Reef Station

**Objective.** The office is submerged: a research station on the seabed, lit from a surface far
above.

**The world.** Blue on blue, with depth carried by layered light rather than by contrast. The
first world with continuous motion in it.

- **Ground plane** — seabed sand with ripple marks; the wall band becomes the water column rising
  out of frame; the tile grid becomes settled deck plating.
- **Rooms** — pressurised research domes, rounded rather than square at the corners.
- **Desks** — console pods; the monitor becomes a sonar screen.
- **Busy** — the dome's porthole and the sonar screen light cyan, which is the one world where
  the state hue is also the ambient hue — so the busy indicator must earn its separation by
  **brightness and by the flicker**, not by hue. Measure it.
- **Waiting area and queue** — a kelp-marked current channel; queued members drift in line along
  it.
- **Characters** — fish, a turtle and a ray. Fins and tail are the `A` layer.
- **Fixtures** — whiteboard → a chart riveted to hull plate; cooler → an air tank; window → a
  porthole; daylight → a surface light shaft; plants → kelp and coral.
- **Decoration slots** — ground: slow-moving caustics; air: rising bubbles.
- **Handoff** — the envelope becomes a sealed capsule.

**Files.** `frontend/src/worlds/underwater.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: **the busy state must survive a blue world.**
If a busy dome cannot be told from an idle one at 540 px on a compressed recording, the phase is
not done regardless of how good the reef looks. And both moving layers must go fully still under
`prefers-reduced-motion: reduce`.

**Validation.** The shared block above, plus a busy-versus-idle screenshot pair at 540 px.

**Gate.** Busy reads instantly in a world made of the busy colour, and motion respects the
reduced-motion preference.

---

### Phase 22 — Alien Colony

**Objective.** The floor becomes an off-world colony — landing pads, command modules and strange
flora under two moons.

**The world.** Purple and teal, artificial light, nothing organic about the architecture. The
first world where a message crossing the floor is a transmission rather than an object.

- **Ground plane** — purple-teal regolith; the tile field becomes shallow crater pocks and pad
  markings; the wall band becomes an alien horizon with two moons.
- **Rooms** — command modules on landing pads, with an airlock where the door was.
- **Desks** — command stations; the monitor is a tall readout panel.
- **Busy** — the module's antenna array lights and its readout comes up cool-teal.
- **Waiting area and queue** — a lit landing strip; queued members stand at its markers.
- **Characters** — aliens and small service robots. Antennae and visors are the `A` layer.
- **Fixtures** — whiteboard → holo-panel; cooler → fuel cell; window → viewport; daylight → a
  ringed planet low on the horizon; plants → bulb flora.
- **Decoration slots** — sky: the two moons and the ringed planet; ground: pad markings and
  crater shadow.
- **Handoff** — **this is the phase that restyles it**: the envelope becomes a transmission pulse
  travelling the same path, with the same 1100 ms timing and the same accessible label.

**Files.** `frontend/src/worlds/alien.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: the handoff's **path, duration and
`aria-live` label are untouched** — `ENVELOPE_MS` stays 1100 and stays in sync with the CSS
transition. Only the thing travelling changes. And a pulse that is easy to miss is worse than an
envelope: check it at 540 px before calling it done.

**Validation.** The shared block above, plus a handoff watched end-to-end at both viewports.

**Gate.** A handoff is at least as easy to follow as the paper envelope, and its timing contract
is intact.

**Shipped 2026-09-20. Four things the plan got wrong, corrected in flight — and the first three
are findings for worlds 23–26 rather than details of this one:**

1. **The hover state of the selected world card is illegible in every dark world.** Not this
   world's bug — `.worldcard:hover` in `styles.css` is (0,2,0) and `.worldcard--on` is (0,1,0),
   so pointing at the card for the world you are *currently in* replaced its amber fill with the
   page ground while leaving `--on-amber` — near-black — as the text. On cream that is 17.25:1
   and invisible as a defect; measured on dark it is **1.00:1 in Night Watch and 1.02:1 in Alien
   Colony**. Phase 19 shipped it. Fixed here in the base stylesheet, because a second dark world
   shipping the same unreadable control is worse than a world phase touching a third file:
   `.worldcard:not(.worldcard--on):hover` for the unselected case, and a `--amber-deep` hover for
   the selected one. **This is the one change in this phase that is not scoped to the world**,
   and it changes Paper Office's chrome — the selected card now deepens on hover instead of going
   cream. Not on the floor, not in any recorded frame.
2. **A world may not put a celestial object on `.fixture--daylight`.** The brief asks for the
   ringed planet here, but that fixture sits at (17%, 46%) — the middle of the floor — so a
   planet rendered at it is a planet lying on the ground. The planet goes in the **sky slot**,
   where the brief's own decoration-slot line also puts it, and the fixture carries the *light*
   it throws. That keeps the fixture's actual role, which is a pool of illumination in a fixed
   place. **Every remaining world whose brief names a sky object for `daylight` has the same
   problem** — 23's sun over the cloud line and 25's low desert sun both do.
3. **"Ambient warmth decorates" is a rule about confusability, not about temperature.** The
   shared resolution names warmth because `--honey` makes warmth the awkward case. This world's
   ambient is a magenta-violet, which is measured at **82–137° from all four state hues** where a
   warm ambient sits 3° off honey. A world should pick the ambient its own setting wants and
   measure the separation, rather than forcing warmth in to satisfy the letter of the rule.
4. **The `--tile` token means "the other ground colour", not "lighter than the floor".** Paper
   Office's tile is a laid surface catching light, so it is lighter than `--floor`. A crater is a
   hollow, so here it is *darker* — and the recipe has to supply a lit rim, or the pocks read as
   stains rather than as depressions. Worth knowing before 24's snow and 26's flagstones.

**Two notes that are not corrections.** The `agentDesigns` field Phase 18 built is used for the
first time here — colonists for the people, service robots for the agents — and it earns its
keep: an agent at a desk is visibly not one of the people watching it. Night Watch's decision to
give both casts the same art was right for a deck the crew works together, and would have been
wrong here. And the pock field needed Phase 19's two-lattice trick as much as the drifting motes
did: a single tiled dot field at exactly `--tile-size` reads as a rendering artefact, and the fix
is two fields whose tile sizes share no useful factor (1.34× and 0.79× of the tile).

---

### Phase 23 — Cloud City

**Objective.** The workspace floats: a sky harbour of platforms and towers above the cloud line.

**The world.** Bright, high-key, airy — the one world lighter than the paper office. Its risk is
the opposite of every other world's: not enough contrast rather than too little colour.

- **Ground plane** — floating tile platforms with gaps of open sky between them; the wall band
  becomes the cloud line and sky above it.
- **Rooms** — pavilions and control towers, with an open arch for the door.
- **Desks** — harbour control desks; the monitor becomes a signal lamp housing.
- **Busy** — the tower lights its beacon and the lamp comes up.
- **Waiting area and queue** — a boarding platform; queued members wait at its edge.
- **Characters** — birds, pilots and small sky-drones. Wings and goggles are the `A` layer.
- **Fixtures** — whiteboard → a departures board; cooler → a windsock; window → open air;
  daylight → high sun; plants → topiary in sky-planters.
- **Decoration slots** — sky: layered clouds and a drifting airship; air: occasional wisps.
- **Handoff** — the envelope becomes a small courier bird or drone on the same path.

**Files.** `frontend/src/worlds/cloud.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: **a bright world is where text goes to die.**
Every one of the four state hues needs re-darkening against near-white surfaces, and the pawn
name labels — which already lost a dark halo once, in Phase 15 — need checking against the
brightest platform.

**Validation.** The shared block above, plus every small mono label read at 540 px.

**Gate.** Nothing on a white platform is hard to read, and the four state hues all pass.

---

### Phase 24 — Arctic Base

**Objective.** A polar research station: cabins and antennae on snow, under an aurora.

**The world.** Cold, low-saturation, with the warmth strictly indoors. This is the world the
ambient-warm/cool-state split was written for.

- **Ground plane** — packed snow with ice-crack tiles and boot-tracked paths; the wall band
  becomes a ridge under aurora.
- **Rooms** — insulated cabins with heavy doors.
- **Desks** — survey stations; the monitor is an instrument window.
- **Busy** — a cabin at rest glows **warm** from its living window and that means nothing; when
  its agent goes BUSY the instrument window comes up **cool** beside it, and that is the state.
  Both are visible at once, which is the point and the test.
- **Waiting area and queue** — a flag-marked ice path; queued members wait between flags.
- **Characters** — penguins and parka'd explorers. Hoods and beaks are the `A` layer.
- **Fixtures** — whiteboard → a weather board; cooler → an ice-core rack; window → a frosted
  pane; daylight → a low winter sun; plants → antenna masts.
- **Decoration slots** — sky: the aurora; air: falling snow.
- **Handoff** — unchanged, restyled as a sealed dispatch tube.

**Files.** `frontend/src/worlds/arctic.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: **the two lights must be unmistakable side by
side.** Screenshot one idle cabin and one busy cabin in the same frame; if a viewer has to think
about which is which, the warm light is too strong or the cool one too weak.

**Validation.** The shared block above, plus the idle-and-busy-in-one-frame screenshot.

**Gate.** Warmth reads as atmosphere and cool reads as state, with no ambiguity in a single frame.

---

### Phase 25 — Desert Outpost

**Objective.** A research outpost in the dunes at low sun — canopies, solar arrays, long shadows.

**The world.** Warm sand and long raking light. Its hazard is that the whole world is the colour
of the warn state, so `--honey` has to be re-pitched hard.

- **Ground plane** — dune sand with wind ripples; the tile field becomes sun-baked hardpan; the
  wall band becomes a ridge against a low sun.
- **Rooms** — adobe outposts under shade canopies.
- **Desks** — field stations with a solar array behind them; the monitor is a shaded readout.
- **Busy** — the array's inverter and the readout light cool against all that sand, which makes
  this the easiest busy state to see in the set.
- **Waiting area and queue** — a caravan line: queued members stand in a visible file along a
  marked track, which is the clearest literal reading of the fair queue in any world.
- **Characters** — a fennec, a lizard and a hooded traveller. Ears, tail and hood are `A`.
- **Fixtures** — whiteboard → a route map; cooler → a water barrel; window → a shuttered opening;
  daylight → the setting sun; plants → cacti and scrub.
- **Decoration slots** — ground: wind-scoured ripples and long shadows; air: drifting dust.
- **Handoff** — unchanged, restyled as a courier satchel.

**Files.** `frontend/src/worlds/desert.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: **`--honey` cannot be sand.** In a world made
of warm ochre, the queued state and the 50–80% budget tone must still announce themselves. Push
them darker and more saturated until they do, and measure.

**Validation.** The shared block above, plus a queue of three read against the dunes at 540 px.

**Gate.** A queued member and a half-spent budget are both obvious in a world the colour of both.

---

### Phase 26 — Ancient Ruins

**Objective.** A temple complex: stone chambers, glyph walls and torchlight, worked by
archaeologists.

**The world.** Heavy, dark stone with two light sources — torch amber that decorates, and glyph
cyan that reports. The last world, and the one that restyles the most objects.

- **Ground plane** — stone flags and cracked mosaic; the wall band becomes a carved wall with a
  glyph frieze.
- **Rooms** — pillared chambers; the door becomes a stone lintel, and the room's silhouette
  changes rather than just its fill.
- **Desks** — stone worktables strewn with finds; the monitor becomes a glyph tablet.
- **Busy** — the chamber's glyph wall and the tablet light arcane cyan, while the torches stay
  warm and mean nothing.
- **Waiting area and queue** — a colonnade; queued members wait between the columns.
- **Characters** — adventurers and archaeologists; hats, packs and lamps are the `A` layer.
- **Fixtures** — whiteboard → a carved stele; cooler → an urn; window → a broken roof; daylight →
  a shaft of light through it; plants → overgrown vines.
- **Decoration slots** — ground: torch-flicker shadow across the flags; sky: the frieze.
- **Handoff** — the envelope becomes a scroll.

**Files.** `frontend/src/worlds/ruins.css` (new), `frontend/src/worlds.js`.

**Non-negotiables.** The shared scope above, plus: **torch flicker is decoration and must not
read as an alert.** Keep it slow and low-amplitude, keep it out of the `--honey` and `--alarm`
hues, and make sure it stops dead under `prefers-reduced-motion: reduce`.

**Validation.** The shared block above, plus a full minute watched with an idle floor — nothing
in the ambience should ever look like something happening.

**Gate.** The recolour test passes, and a quiet floor looks quiet.

---

### Phase 27 — World polish and Random World

**Objective.** Make the set feel like one system rather than eight separate builds, and add the
one piece of new UI the roadmap allows.

**No new product behaviour.** Nothing here touches what HiveOS does — only how it looks doing it.

**What lands.**

1. **The transition.** A cross-fade between worlds. **The one real hazard is the sprite**: a pawn
   mid-walk is animating between `--art` and `--art-step`, and a world change swaps both under
   it. Either freeze the gait for the duration of the fade or swap at a frame boundary; a
   half-swapped character is the failure to watch for.
2. **Micro-animations**, world by world, all gated behind `prefers-reduced-motion` and all
   audio-free.
3. **The contrast matrix** — four state hues × nine worlds, all 36 measured and recorded in the
   phase note. **Any world that fails is fixed here or removed from the registry**; a world that
   cannot carry the state colours is not shippable, however good it looks.
4. **A responsive sweep of every world** at 1440 / 1100 / 900 / 540 / 390, and a keyboard pass on
   the picker.
5. **Random World** — a "surprise me" entry that picks a world other than the current one. It
   persists the world it landed on, not the fact that it was random, so a reload is stable.

**Files.** `frontend/src/worlds.js`, `frontend/src/App.jsx`, every world CSS file.

**Non-negotiables.** The shared scope above, plus: no new dependency for the transition — a CSS
cross-fade, not an animation library. And Random World never picks the world already showing.

**Validation.** The shared block above, run against **every** world, plus: switch worlds while a
pawn is walking and while a handoff is crossing, and confirm neither breaks.

**Gate.** All nine worlds pass the contrast matrix, switching is smooth from any world to any
other at any moment, and Paper Office is still the default.

---

## If you are behind schedule

Cut in this order:
1. Phase 27, then the worlds from 26 backwards. Each world is a self-contained file plus a
   registry entry, so cutting one leaves every other world intact and Paper Office untouched.
   **Phase 18 is the only one of the ten with anything behind it** — cut it and the whole set
   goes, so if it has landed, ship it and cut worlds instead.
2. Phase 16, then 15, then 14 — the expansion is enhancement, and cutting from the back always
   leaves a coherent product. Phases 12 and 13 are what a judge sees in the first five seconds;
   cut those last.
3. Phase 5 entirely
4. Per-task cost breakdown, task history, announcements
5. The second agent slot — one slot still demonstrates queueing
6. Shared memory — the queue plus token meter alone still tells the story

**Never cut:** the deployed public URL, the token meter, or the demo video. Those three are the submission.
