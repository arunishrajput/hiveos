# PROGRESS.md

> Current execution state. A fresh Claude Code session reads this to know exactly where things stand.
> Keep it operational and short. Not a diary — history lives in git.

**Last updated:** 2026-09-19

---

## Project status

| | |
|---|---|
| **Project** | HiveOS — OS-style scheduler for a team's shared AI agent budget |
| **Track** | Ship It (deployed, public URL) |
| **Deadline** | 2026-09-20 |
| **Current phase** | **Phase 6 — demo readiness** (the expansion is finished) |
| **Phase status** | `READY`. Phase 16 (agent-to-agent handoff) complete, deployed and verified 2026-09-19 — `ws_smoke.py` 94/98 with all four failures traced to live visitors on the public URL, `rehearse.py --takes 2` 12/12 twice. **Phases 12–16 are all done; there is no further build phase planned.** Phase 6 is the only thing left and its remaining tasks are the user's |
| **Deployment state** | Stack `hiveos` live in `us-east-1`. DynamoDB + WebSocket API + Router + SQS/DLQ + Agent Runner. Frontend live on Amplify. |
| **🌐 Public URL** | **https://main.dbavt8jr66qxx.amplifyapp.com** — the landing page, verified cold, zero setup |
| **🖥 Straight to the board** | **https://main.dbavt8jr66qxx.amplifyapp.com/#/workspace** — what the recording windows point at |
| **WebSocket endpoint** | `wss://mel2gpat9c.execute-api.us-east-1.amazonaws.com/prod` |
| **Amplify app** | `dbavt8jr66qxx`, branch `main` — **not in CloudFormation** (see below) |
| **Repository** | https://github.com/arunishrajput/hiveos (public, `main`) |
| **AWS account** | `890608337320` · `us-east-1` · IAM user `hiveos-dev` (AdministratorAccess) |

> **There is a submittable deliverable as of now.** The Phase 4 gate — a deployed public URL
> showing live shared state — is met. Everything remaining is enhancement.

---

## Phase board

| # | Phase | Status |
|---|---|---|
| 0 | Pre-project setup | `COMPLETE` (Bedrock abandoned — see below) |
| 1 | WebSocket backbone | `COMPLETE` |
| 2 | Scheduler + queue (no LLM) | `COMPLETE` |
| 3 | Model + agent + memory | `COMPLETE` — real model, real provider-reported token counts, enforced ceiling |
| 4 | Frontend HUD + public URL | `COMPLETE` |
| 5 | Agent chat + 2D canvas (cuttable) | `COMPLETE` — **un-cut** by user decision, 2026-09-18 |
| 7 | Canvas-first pixel workspace | `COMPLETE` — merged, deployed, rehearsed 2026-09-18 |
| 8 | Depth pass — identity, full screen, ledger, fairness, tools | `COMPLETE` — 2026-09-18 |
| 9 | Per-team isolation | `COMPLETE` — 2026-09-18 |
| 10 | Workspace passphrases | `COMPLETE` — 2026-09-18 |
| 11 | Workspace administration | `COMPLETE` — 2026-09-18 |
| 12 | Paper-office light theme | `COMPLETE` — deployed and verified 2026-09-19 |
| 13 | Public landing page | `COMPLETE` — deployed and verified 2026-09-19 |
| 14 | Named agents at each desk | `COMPLETE` — deployed and verified 2026-09-19 |
| 15 | Multi-room floor rebuild | `COMPLETE` — deployed and verified 2026-09-19 |
| 16 | Agent-to-agent handoff | `COMPLETE` — deployed and verified 2026-09-19 |
| 6 | Demo readiness | `BLOCKED — WAITING FOR MANUAL ACTION` ← **here** — tasks 1–5 and 8 done; 6, 7, 9 are the user's. The expansion has landed, so the deferral is over. The rehearsed take and the 640×950 framing in `DEMO.md` predate the reskin and need re-rehearsing; `rehearse.py --takes 2` passes 12/12, so the *sequence* is sound and it is the narration and framing that need a pass |

**Phase 3 is complete as of 2026-09-18**, but not as planned — Bedrock was abandoned, not
integrated. See *Blocked* below for the evidence, and `ARCHITECTURE.md` decision 7 for the
reasoning.

| Phase 3 task | State |
|---|---|
| 1. Bedrock IAM permissions | **not done, and correctly so.** Bedrock is never called, so granting it would be an unused permission. `template.yaml` records where it would go if Bedrock is ever unblocked. |
| 2. Strands SDK vs boto3 `converse` | **neither.** Both assumed Bedrock. `shared/llm.py` calls Groq with one stdlib `urllib` POST — no SDK, nothing to package. |
| 3. The memory tools | `get_team_memory` / `set_team_memory` **done**. `get_task_context` deliberately not built — no task history exists to return; see `CONTRACT.md`. |
| 4. Load memory before the call | **done** — and verified crossing between users against the deployed URL |
| 5. Token accounting + `token_update` | **done, and the numbers are now real** — `total_tokens` as the provider reports it, `estimated=False` |
| 6. Budget ceiling + `budget_exhausted` | **done, enforced, verified** — rehearsed at 675/500, refused, not one token spent |
| 7. Cap `max_tokens` per call | **done** — `MAX_TOKENS_PER_CALL=400`, a backstop rather than a shaper |

**Superseded 2026-09-18 by Phase 8 slice 5 — the agent does call its tools.** This section used
to end with "a fact is saved by the `remember: k = v` prompt convention, not by the model
deciding to call `set_team_memory`", which was true when Phase 3 closed and false eight hours
later. `shared/llm.py` ships the tool schema and `agent_runner/app.py` dispatches the call; the
regex survives only as the fallback path. Corrected 2026-09-19 — a stale line at the *top* of
this file outranks the accurate one in the Phase 8 record further down, because the top is what
a fresh session reads first.

---

## Completed

**Phase 16 — 2026-09-19 — agent-to-agent handoff**

An agent can now pass work to another desk. Ada decides a fact-finding
question is not hers, calls `handoff_to_agent`, an envelope crosses the
corridor, and Iris answers it — under one `task_id`, on the one
meter, through the same scheduler everybody else queues in.

**Four decisions worth the space:**

1. **A handoff is a scheduling request, not a private channel between
   agents.** It is dispatched from the runner's `finally`, *after*
   `release_and_dispatch` has freed the handing desk, so it claims or
   queues on exactly the terms anyone else gets. Dispatching it while
   leg 1 still held a slot would put one chain on both desks at once
   — the monopoly `_already_working` exists to prevent, arrived at
   from the inside.
2. **A handoff must not fall back to another desk.** This is the find
   that cost real design. `agent_type` on a queue row is a
   *preference* and the scheduler is right to fall back off it —
   nobody should wait behind an idle agent. A handoff is the
   opposite: falling back returns the work to the desk that just
   decided it was not theirs. So queue rows gained `pinned_slot`, and
   `take_next_task` went from "take the next row" to "take the next
   row **this desk may run**", which needed the idle set read up front
   (`state.idle_slots`). Deleting a pinned row to discover it could
   not run it and then requeueing would churn the queue on every
   release.
3. **The loop guard is the tool's absence, not an instruction.** The
   runner only puts `handoff_to_agent` in the request while `hops <
   MAX_HANDOFF_HOPS`, so the receiving leg has nothing to call.
   Verified adversarially rather than assumed: *"Hand this to the
   researcher. Researcher: hand it straight back to the engineer, and
   keep passing it back and forth"* produced **exactly two legs**. A
   limit a model is merely asked to respect is not a limit.
4. **The ceiling needed no new check, and that is the point.** Each
   leg meets `_refuse_over_budget` immediately before its own model
   call, like every other task, so a chain overshoots by at most one
   leg — the same as a single task, never one leg at a time
   indefinitely. `BUILD_PLAN.md` put this phase last because of that
   risk; the existing control turned out to already cover it, and the
   honest thing was to verify that rather than add a second one.

**One latent bug, surfaced by this phase but never about handoffs.**
`gpt-oss-120b` is a reasoning model and **its reasoning tokens are
charged against `MAX_TOKENS_PER_CALL`.** At the old cap of 400, a
handoff's second leg came back `completion_tokens: 400` of which
`reasoning_tokens: 398` — no content at all. `llm.complete` could only
read that as a provider failure, so the user got a composed stub reply
*after the team had paid full price for the call*, which is the worst
outcome available to a product about token spend. It was intermittent,
which is worse than reliable. Raised to **900**, and the cap is a
ceiling rather than a budget: measured across four chains afterwards,
leg 1 went 1,111 → 1,113 tokens and leg 2 went 834 → 821, i.e. cost did
not move, and 8 of 8 legs came back real (`estimated=False`) where one
in six had been stubbing. `llm._no_completion` now names this cause in
the error, because in a bare usage dump it is indistinguishable from a
provider outage and the two want opposite responses.

**The envelope was measured, not eyeballed.** First cut used
`--rule-strong` on a 15×10 box; it reads in the corridor and
disappears inside a room, and both ends of its journey are inside
rooms. Four candidates were rendered at real size on the deployed
floor and compared: 18×12, a `--envelope-edge` hairline one step
darker, and a two-layer shadow whose *tight* layer is the load-bearing
half — a soft warm shadow alone reads as the room's own lighting,
while a 1px contact line lifts the paper off whatever it is over. No
hue, deliberately: a coloured envelope would be claiming to be a
state, and this floor's two meaningful colours are already a lit
monitor and an ochre queue label.

**Verified against deployed AWS, not exit codes:**

| Check | Result |
|---|---|
| `sam build --use-container` + `sam deploy` | ✅ `UPDATE_COMPLETE`, `MAX_TOKENS_PER_CALL` reads **900** on the deployed function |
| `vite build` + Amplify | ✅ job 21 `SUCCEED`, 79.28 KB gzipped JS |
| `ws_smoke.py` | ✅ **94/98** — 13 new checks, all passing. The 4 failures are the documented live-visitor case, evidenced below |
| `rehearse.py --takes 2` | ✅ **12/12 twice**, unattended, 93–95s of headroom |
| `rehearse.py --ceiling` | ✅ **5/5** — 2,259/1,600 after four real tasks, clamped to 100%, **not one token spent** on the refused one |
| **The engineer decides, unprompted by a tool name** | ✅ *"This is a fact-finding question rather than an engineering one — pass it to the researcher"* → `handoff_to_agent({'agent': 'researcher', 'note': '…'})` |
| **One task id across two desks** | ✅ ledger `[('researcher','coder',869), ('coder',None,1113)]`, chain 1,982, team total 1,982 |
| **A handed-over task cannot hand on again** | ✅ 2 legs from a prompt explicitly demanding a ping-pong |
| **A handoff to a busy desk queues pinned, and the idle desk does not take it** | ✅ `pinned_slot=researcher` while `coder` sat IDLE |
| Once its own desk frees, the waiting handoff runs there | ✅ same `task_id`, `handoff_from=coder` |
| The envelope actually crosses, on the deployed URL | ✅ **23.1% → 76.9%** over 43 sampled frames — Ada's desk centre to Iris's — then removed |
| An ordinary engineering task does **not** spuriously hand off | ✅ 695 tokens, answered at the desk it was asked of |
| A research-flavoured prompt with no handoff request | ✅ also answered in place — the tool description is not over-firing |
| The memory beat still works with the extra tool present | ✅ saved, 1,043 tokens |
| Console on the deployed page | ✅ zero errors, zero warnings |
| Horizontal overflow at 390 / 640 / 1500 | ✅ none; envelope inside the floor box at every width, `--furn` 1 → 1.8 |
| Demo column | ✅ floor still **250px**, no panel added — `DEMO.md`'s framing is untouched by this phase |

**About those four `ws_smoke` failures — they are not a regression.**
All four are the connection-leak checks, which assert the table holds
*no* `CONN#` rows, and the public URL had real strangers on it
(`BoyKraken`, `Kamal`, `divyansh`) throughout. The invariant itself was
verified directly instead: two connections opened by the harness,
closed, and confirmed gone from DynamoDB while the strangers' rows
stayed. The docstring has warned about this since Phase 11 and this is
the second phase to hit it; it is now simply the condition of testing
against a URL people are actually using.

**Two things worth knowing before a recording:**

- **`rehearse.py` has no `open_timeout` and no retry**, so a network
  blip during the opening handshake aborts a whole take with
  `TimeoutError` rather than retrying. Seen twice in a row and then
  not at all: nine sequential connects measured ~1s each immediately
  afterwards, and two clean takes followed. Not a code fault — but if
  it happens mid-recording it looks like one, so re-run rather than
  debug.
- **The meter now reaches ~2,460–2,860 of 5,000** on a rehearsed take,
  against the ~2,250 recorded at Phase 8. A handoff chain on top of
  that costs ~1,900. `--ceiling` seeds 1,600 and a plain task is ~700,
  so the refusal beat still lands on the third task.

**Test partitions left in the table**, alongside Phase 15's `TEAM#p15`:
`smokehandoff` (the smoke test's own workspace, reset at the start and
end of its section) plus `p16*` partitions from driving real handoffs
against the deployed board. All inert — Phase 9 partitions every row by
team, `alpha` cannot see them, and `reset-demo.sh` only inspects
`alpha`. Left rather than bulk-deleted, which is a destructive
operation on a live table for no benefit.

**Phase 15 — 2026-09-19 — the multi-room floor**

The single open floor is now a plan. Two project rooms stand against
the back wall with a corridor between them, one per agent slot, and a
**waiting area** below where queued members physically stand in queue
order. Hot desks along the left, cooler and plants at the edges.
Frontend only — `components.jsx` and `styles.css`, nothing else.

**Four decisions worth the space:**

1. **The waiting area is the phase, not the rooms.** Rooms were the
   visible half; the queue was the meaningful half. A queued member is
   drawn on a numbered spot by *exactly* the mechanism that seats a slot
   holder at a desk, and with the same promise — the coordinate the
   server holds is never touched, so leaving the queue walks them back
   to where they were actually standing. Dispatch off the front of the
   queue is now a walk out of the waiting area and into a room, which is
   the scheduler made visible. Nothing in the protocol changed to do it.
2. **A corridor, bought by making the rooms smaller.** Two rooms filling
   the floor edge to edge left a 76px desk adrift in a 267px room and no
   way to read the plan except as "two boxes". 34% wide each with 20%
   between them gives the office circulation and gives the furniture a
   room it can fill. The floor is a wide, short box (606×250 at the demo
   window) and that is what the plan had to be composed for.
3. **The room's corner and the desk's centre are kept as separate
   fields.** The desk is drawn room-locally (`left: 50%`, `top:
   DESK_IN_ROOM`), but the person seated at it is a pawn on the *floor*
   like any other. The first version derived the corner back out of a
   centre at each use site; `deskX`/`deskY` now sit beside `x`/`y`
   instead, because deriving one from the other at two call sites is how
   they drift.
4. **The desk bank is furniture and is labelled as such.** Two plain hot
   desks, nothing bound to them, nothing lighting up. They answer "why
   is this person standing here" — without them the lower half is an
   empty field with a rug in it. They are deliberately smaller and
   flatter than an agent desk: anything competing for attention with the
   two desks that report scheduler state would be costing the room the
   thing it is for.

**Two bugs found by building this, both measured rather than eyeballed:**

- **Pawn name labels had an `--ink` halo behind `--ink` text** — dark
  glow behind dark text, left over from the graphite theme.
  `.desk__label` was corrected when the theme flipped in Phase 12 and
  this was missed. It survived a whole phase because one name on a tile
  field reads as a slightly heavy label; three side by side in the
  waiting area is what made it obvious. Now haloed in `--floor`, like
  the desk labels.
- **The waiting-area caption is fixed-size text while the spots are
  percentages**, so the gap between them shrinks with the floor: every
  left-hand position that cleared at 606px collided at the 430px the
  landing preview renders. Moved to the far end of the line, which is
  the only position that holds at every width.

**The column height is unchanged — 838px, same as Phase 14.** Measured
on the deployed build at 640px: a populated board is 1,002px of which
the spend panel is 164; a clean board is the same **838px** against
`DEMO.md`'s 862px viewport. The floor stayed at 250px and the rebuild
happened inside it, so `DEMO.md`'s framing survives this phase intact.
`BUILD_PLAN.md` anticipated re-laying the column here; that was not
needed and deliberately not done — the measurement was already
known-good and re-laying it would have invalidated it for no gain.

**Verified against deployed AWS, not exit codes:**

| Check | Result |
|---|---|
| `vite build` | ✅ clean, 81.63 KB gzipped JS (was 80.95) |
| Deployed | ✅ Amplify job 19 `SUCCEED`, bundle `index-Cdc7hv_S.js` |
| `ws_smoke.py` | ✅ **85/85** — unchanged from Phase 14, no regression |
| `rehearse.py --takes 2` | ✅ **12/12 twice**, unattended, 94s of headroom |
| Rooms light with their slot, on the deployed URL | ✅ both rooms blue, `carol` at Ada's desk, `dave` at Iris's |
| A queued member stands in the waiting area | ✅ `bob` on spot 1, captioned `queued #1` in ochre |
| `/` and `/#/workspace` HTTP status | ✅ **200** and **200** |
| Console on the deployed page | ✅ zero errors, zero warnings |
| Horizontal overflow at 390 / 640 / 1500 | ✅ none at any width |
| Wide layout (≥1100px) | ✅ rooms scale with the floor; `--furn` 1.45 → 1.8 |
| Landing preview renders the same floor | ✅ from canned props, caption clear of the queue |

**Known cosmetic limits, recorded rather than fixed.** Five or more
people queued puts the fifth under the "WAITING AREA" caption — the
mildest failure available, and 5 queued is far outside the demo. At
390px the rooms are cramped and `RESEARCHER` crowds its room edge;
mobile is not the demo case and there is no overflow at that width.
Two people standing on the same coordinate still overlap, exactly as
before this phase.

**A `TEAM#p15` partition is left in the table.** ~30 rows of test data
from driving real busy/queued state against the deployed board — the
only honest way to verify a floor that renders scheduler state. It is
inert: Phase 9 partitions every row by team, so `alpha` cannot see it,
`ws_smoke.py` passed with it present, and `reset-demo.sh` only inspects
`alpha`. Left rather than bulk-deleted from the live table, which is a
destructive operation for no benefit. Remove it with the workspace's
own admin delete if it ever matters.

**Phase 14 — 2026-09-19 — named agents at each desk**

Slots stop being interchangeable. `coder` and `researcher` are now the desks of
**Ada, the Engineer** and **Iris, the Researcher** — each with a role, a
tagline and its own persona in the system prompt. The requester picks one, the
floor captions each desk with its nameplate, and the ledger records which agent
actually ran the task.

**Four decisions worth the space:**

1. **The roster is code, not rows** (`backend/shared/agents.py`). Names on the
   `AGENT#` row was the obvious move and needed a backfill for every workspace
   that already exists — `ensure_team` writes slot rows *conditionally*, so an
   existing row is never updated and every board created before today would
   have opened with nameless desks. The row keeps `status` and `current_user`;
   `state_snapshot` joins the rest. One tuple, one edit, no migration.
2. **The ids stay `coder` and `researcher`.** They are in deployed rows, in
   `seed.sh`, in `ws_smoke.py` and in every queued task. Adding a name to an id
   is free; changing the id is a migration that buys nothing.
3. **A preference is still not a reservation — but the substitution is now
   said out loud.** This is the phase's real find: the SQS message carried one
   `agent_type` holding *what the user asked for*, and the runner recorded that
   as the agent that ran the task. While the slots were interchangeable it was
   a harmless mislabel. The moment they have names it is the ledger crediting
   Ada for Iris's work — and a governance product whose ledger misattributes
   work is the criticism it levels at everything else. The message now carries
   `slot_id` (ran) and `requested_agent` (asked), and `agent_response` names
   both. Nobody queues behind an idle agent; they are just told who took it.
4. **`persona` never leaves the backend.** It is the model's instruction, not
   board state. `agents.public()` sends name, role and tagline only, and
   `ws_smoke.py` asserts the persona's absence from the snapshot.

**Verified against deployed AWS, not exit codes:**

| Check | Result |
|---|---|
| `sam build --use-container` + `sam deploy` | ✅ `UPDATE_COMPLETE`, `shared/agents.py` present in both function bundles |
| `ws_smoke.py` | ✅ **85/85** (79 before, +6 for this phase) |
| Snapshot carries each desk's identity, in roster order | ✅ `[('coder','Ada'), ('researcher','Iris')]` |
| Persona leaks to a client | ✅ **no** — snapshot keys are `agent_type, current_user, name, role, slot_id, status, tagline` |
| An agent answers in character | ✅ live on the deployed board: *"I'm Ada, the Engineer at HiveOS's agent desks. I handle engineering tasks like coding, debugging…"* — 549 real tokens |
| Substitution reported honestly | ✅ bob asked `coder`, got `researcher`: response `agent_name=Iris, requested_name=Ada`; ledger row `agent_type=researcher, requested_agent=coder` |
| An unsubstituted task records nothing | ✅ `requested_agent` null on alice's row |
| Floor, picker and attribution on the deployed URL | ✅ nameplates read *Ada / ENGINEER* and *Iris / RESEARCHER*, the busy desk's name goes blue, activity reads `ADA → DANA 549 TOKENS` |
| Landing preview | ✅ same nameplates from canned props |

**The demo column got 41 px taller, and the margin is now thin.** Measured on
the deployed build at 640 px wide: the clean board is **838 px** of content,
against the **862 px viewport** `DEMO.md` records for a 640×950 window. It
still fits — with ~24 px to spare where it had ~65. The picker is the whole of
the increase, and 16 px of it was bought back by laying the picks on one
baseline below 1100 px (`styles.css`).

How thin that margin is depends on the browser: this session's Chrome carries
~145 px of its own chrome rather than ~88, giving a 806 px viewport, and at
that height the team-chat input sits ~32 px below the fold. The page scrolls
rather than clipping, and the chat box is the least load-bearing control on the
board — but **re-measure in the actual recording browser before a take**.
Deliberately not fixed by shrinking the room: Phase 15 re-lays this column.

> **The line that used to be in this file — "the board is 933 px tall, so it
> fits 950 with ~17 px to spare" — was wrong and is now deleted.** It compared
> board height against *window* height, ignoring the browser's chrome
> entirely. `DEMO.md`'s 862-into-862 figure was the sound one, and is the
> measurement the number above replaces.

**Phase 13 — 2026-09-19 — the public landing page**

A front door at `/`: hero with the board beside it, the cost-overrun evidence
from `SUBMISSION.md` with its sources attached, four how-it-works steps, the
AWS pipeline in the one ink-dark terminal card the theme allows, and a footer.
Alternating cream and sand bands, divided by hairlines. Frontend only — the
backend was not touched and neither was any protocol.

**Three decisions, each of which had a plausible alternative:**

1. **The route is a hash, `#/workspace`, not a path.** A real `/workspace`
   would be served through Amplify's `404-200` SPA rewrite — the app boots, but
   the response is an HTTP **404**, which is already recorded below as a wart
   worth not adding to. A hash never leaves `/`, so the link handed to a judge
   or a teammate is a clean 200 and is still bookmarkable, shareable and
   back-button-correct. Verified with `curl`: both `/` and the hash link return
   **200**. No router library — same reasoning that kept out Tailwind and a
   state library.
2. **The board preview does not connect, and that is the whole point.** A live
   preview socket was the obvious idea and is wrong: `$connect` writes a `CONN#`
   row, so every visitor to the front page would appear as a phantom member on
   the default board, inflate the member count *on camera* during a take, and
   fail `ws_smoke.py`'s four connection-leak checks. There is no read-only
   observer in the protocol and inventing one for a marketing page is the wrong
   trade. Instead the preview renders the **real** `QuotaBar` and `CanvasPanel`
   from canned props, so the picture cannot drift from the product.
3. **`useHive` stays inside `Workspace`**, so the landing route opens no socket
   at all. Proven rather than asserted — `window.WebSocket` was wrapped with a
   counter on the deployed page: **0** sockets while on `/`, **1** the moment
   the workspace mounted.

`CanvasPanel` gained one guard: with no `onMove` it drops its click handler,
its tab stop and its "click or use arrow keys" affordance, and becomes
`role="img"` rather than `role="application"`. A still room that advertises an
interaction it does not have is worse than one that says nothing.

**Verified against the deployed public URL, not exit codes:**

| Check | Result |
|---|---|
| `vite build` | ✅ clean, 80.95 KB gzipped JS (was 78.4) |
| Deployed | ✅ Amplify job 16 `SUCCEED` |
| Landing renders at `/` on the deployed URL | ✅ hero, 3 stat cards, 4 steps, terminal card, footer |
| Preview shows the product working | ✅ 2 lit desks, 3 people, `queued #1`, meter ochre at 56.9% |
| CTA → gate → board | ✅ and the board came up `live`, real quota 2,439/5,000, real memory and ledger |
| Sockets opened on the landing route | ✅ **zero** — counted, not assumed |
| Back and forward across the route | ✅ both directions render the right page |
| `/` and `/#/workspace` HTTP status | ✅ **200** and **200** |
| Console on the deployed page | ✅ zero errors, zero warnings |
| 390 px viewport | ✅ no horizontal overflow anywhere; nav fits; the ASCII diagram scrolls inside its own card |
| `ws_smoke.py` | ⏸️ **not run** — zero backend files changed. Not evidence of a pass; there was nothing in its scope to regress |

**The ASCII diagram is column-aligned by hand and will break silently.** The
`│` drops from the centre of *Router Lambda* to `SQS` and the `▲` rises from
*Runner* to *DynamoDB*; edit any label and the arrows keep pointing at whatever
now occupies that column. It still looks like a diagram while saying something
false. There is a comment on it in `landing.jsx` and a note below.

**Phase 12 — 2026-09-19 — the paper office**

Re-tokenised the whole app from the graphite operator console to a warm light
theme, taking [Munder Difflin](https://munderdiffl.in/) as the reference. The
palette is measured from that site's computed styles, not eyeballed: cream
`#fff8e7`, paper `#fffdf7`, sand `#fbefd2`, amber `#ffca54`, ink `#1a1320`,
hairline `#e6d9bc`. Inter replaces IBM Plex Sans, JetBrains Mono replaces IBM
Plex Mono — both self-hosted through `@fontsource`, so a cold load still never
waits on a CDN.

**The rule that governs every later phase: brand amber is a fill, never text;
state hues are text-weight.** `#ffca54` on cream is 1.6:1 and cannot carry a
word; under ink it is 11:1. So amber paints buttons, the chosen marker chip,
the logo and the daylight on the floor, and every machine-state label — jade,
ochre, blue, red — was darkened until it passes on paper. Nothing amber means
anything and nothing meaningful is amber, which is what lets the room be warm
and decorative while the quota strip stays the one loud instrument. It is
written at the top of `styles.css`.

Backend untouched — the diff is eight files, all frontend.

| Check | Result |
|---|---|
| `vite build` | ✅ clean |
| Deployed | ✅ Amplify job 15 `SUCCEED` |
| Live board connects | ✅ verified in a real browser against the deployed URL: `live`, 4 online, real quota 2,439/5,000, memory and ledger populated from a genuine `state_snapshot` |
| `ws_smoke.py` | ⏸️ **not run** — zero backend files changed, and its connection-leak checks fail whenever a browser is on the board, which one was. Not evidence of a pass; there was simply nothing in its scope to regress |

**Phase 11 — 2026-09-18 — workspace administration**

**The blocker was named before building: you cannot have owners without
identities.** A display name is something anyone can type at the gate, so an
owner identified by name would be enforceable in the UI and nowhere else.
Administration therefore hangs off a secret the creator holds. Sharing that
secret is what an invite is here — the honest mechanism available without
accounts, and saying so beats pretending otherwise.

Three actions, the ones a governance product actually needs: set the budget,
rotate the passphrase, delete the workspace.

| Check | Result |
|---|---|
| `ws_smoke.py` | ✅ **79/79** (seven new admin checks) |
| `rehearse.py --takes 2` | ✅ 12/12 twice, default **and** private workspace |
| Creator becomes administrator | ✅ |
| Ordinary member | ✅ not an administrator |
| Forged admin token | ✅ grants nothing |
| **Server refuses a member's privileged action** | ✅ not the UI hiding it |
| Owner sets budget | ✅ 4242, seen by every member |
| Delete | ✅ every row gone, members told |
| Admin salt/hash reaching a client | ✅ never |

**Decisions worth keeping:**

- **The token is minted by the client, never returned by the server.** Whoever
  creates a workspace already holds it, so there is nothing to hand back and no
  window in which it could be intercepted.
- **Rights are decided at the handshake and stored as `is_admin` on the `CONN#`
  row.** Admin frames check the row, not the message — the same rule that makes
  `user_id` trustworthy.
- **`admin_delete_workspace` collects its audience before deleting**, because
  `broadcast_to_team` finds recipients by reading the `CONN#` rows the delete
  removes. Caught while writing it, not after.

**A stranger walked into a rehearsal, and that turned out to matter.** The
public URL has real visitors now — `Kamal` appeared in a member list a take was
asserting on. Two real bugs surfaced from chasing it, both introduced by team
isolation and both invisible until a second workspace existed:

1. `reset-demo.sh` seeded the workspace it was told to and then **verified a
   different one** — its probe connected without a team, landing in the
   default. It reported another board's tokens and members as though they were
   yours.
2. `rehearse.py` read `TEAM#alpha` straight from DynamoDB while driving a
   different workspace over the socket, so it compared one board's row against
   another board's snapshot.

Both are the same shape: a team-aware write paired with a team-blind read.
`DEMO_TEAM` and `DEMO_PASSPHRASE` now steer both scripts, and `DEMO.md` says to
record in a protected workspace — which is the actual fix for strangers on the
public URL.

**Phase 10 — 2026-09-18 — workspace passphrases (not Cognito)**

User asked for authentication. Cognito is on `CLAUDE.md`'s **never-build** list
— not a deferral like "multiple teams" was, but an explicit considered-and-
rejected — so this was raised before building rather than after. The recorded
reason still holds and is the important one: *"for a judge opening a URL cold,
zero-login is actively better."* A login wall in front of the public URL costs
the submission more than it protects.

**Built instead, on the user's choice: a passphrase per workspace.** Whoever
creates one may set a passphrase; joining it afterwards requires it. That
closes the actual gap — anyone who knew a workspace *name* could walk into it —
without touching the property that makes the demo work, because a workspace
with no passphrase stays open.

This is authentication of the **workspace**, not of the person. There are still
no accounts and no identity behind a display name. Said plainly in
`ARCHITECTURE.md` decision 9 rather than implied.

| Check | Result |
|---|---|
| `ws_smoke.py` | ✅ **72/72** (six new passphrase checks) |
| `rehearse.py --takes 2` | ✅ 12/12, twice |
| Wrong passphrase | ✅ refused at the handshake, no socket |
| No passphrase on a protected workspace | ✅ refused |
| Right passphrase | ✅ joined |
| Salt and hash reaching a client | ✅ never — snapshot sends `protected` only |
| **Open workspace still opens cold** | ✅ asserted as hard as the closed case |

**Decisions worth keeping:**

- **Refused at `$connect` with 403**, so no socket and no `CONN#` row exist for
  a failed attempt. Accepting and closing after an error frame would leave a
  connected client with no team binding, and a frame sent in that window
  resolves to the *default* workspace.
- **`hmac.compare_digest`**, because `==` returns early on the first differing
  byte and leaks the matching prefix length to anyone willing to time it.
- **PBKDF2-HMAC-SHA256, 100k iterations** — in the standard library, where
  argon2 and bcrypt would need a Lambda layer. ~50ms, paid once per handshake,
  never per frame, so it does not touch the latency the demo is measured on.
- **The client cannot read a 403.** A browser surfaces a refused WebSocket
  handshake as an ordinary close with no readable status, so `useHive` infers
  it: a socket that never opened, twice running, is a refusal rather than a
  blip, and it stops retrying and says so instead of spinning silently.

**Known tradeoff, recorded not hidden:** the passphrase travels in the
`$connect` query string, because a browser cannot set headers on a WebSocket
handshake. TLS covers it in transit; it would appear in API Gateway access logs
if those were ever enabled, which they are not.

**Phase 9 — 2026-09-18 — per-team isolation**

A documented deferral, reversed on user decision. `PRD.md` listed "multiple
teams" as won't-build and `ARCHITECTURE.md` had "single hardcoded team" under
intentionally-simplified; both are updated rather than left contradicting the
code. (`CLAUDE.md`'s never-build list bans multi-team *analytics*, which this
is not.)

Every row is partitioned by team and every backend function takes the team as
its first argument. Two people typing different workspace names get genuinely
separate boards, and a new team creates itself on first join — requiring a
seeding script would have made isolation a deployment step rather than a
property of the product.

**The awkward bit was routing.** API Gateway exposes `queryStringParameters` on
`$connect` and nothing after it, so every later frame carries a connection ID
and no team. Resolved with a `CONN#<id>/TEAM` index row outside the team
partitions. The obvious alternative — have the client send its team per frame —
was rejected for the same reason `CONTRACT.md` already resolves the *sender*
from the stored row: a value the client supplies is a value it can forge, and
forging this one means reading another team's board.

| Check | Result |
|---|---|
| `ws_smoke.py` | ✅ **66/66** (five new isolation checks) |
| `rehearse.py --takes 2` | ✅ 12/12, twice |
| Member lists isolated | ✅ alpha=['alice'] acme=['zara'] |
| New team self-bootstraps | ✅ budget and 2 slots on first join |
| Agent activity never crosses | ✅ nothing reached alpha while acme ran a task |
| Spend and memory isolated | ✅ alpha 0 tokens / 0 facts while acme spent 775 |

**Two bugs, both from mechanical edits rather than design:**

1. `fair_order` read `team` without taking it — a `NameError` that only fired
   on the enqueue path. My first static check verified every *caller* passed
   team and never checked the *callee* accepted it; an AST pass comparing
   parameters against names read in the body caught it.
2. A blind string replacement inserted `team,` twice into `broadcast_queue`,
   so the payload argument received the string `"team"`. Two overlapping
   indentation patterns matched the same site.

Both are the same lesson: a 17-call-site mechanical refactor needs a checker
that reads the code, not a regex that reads lines.

**Known simplification:** orphaned `CONN#…/TEAM` index rows are not cleaned up
by `seed.sh`. Harmless — each is only ever read by a connection ID that will
never recur — but they accumulate.

**Phase 8 — 2026-09-18 — identity, full screen, the ledger, fairness, and tools**

Five slices, each deployed and verified before the next. Ordered so the shell
existed before new panels went into it, and the ledger existed before fairness
read from it.

1. **Avatar identity (bug).** The marker chosen at the gate was ignored by the
   floor — sprites came from `index % 3`, so two of four people were identical
   and *your own character changed when somebody joined*. Now keyed on the
   marker, which is yours and does not move.
2. **Full-screen responsive shell.** Above 1100 px the 760 px cap comes off:
   room left, text rail right, quota top, members bottom. Below it, unchanged —
   three side-by-side demo windows still work. Widening the room exposed that
   everything in it was a fixed pixel size, so the floor is now driven by three
   tokens (`--px-n`, `--furn`, `--tile-size`).
3. **Task history.** A `TASK#` ledger, written at all three outcomes. A refused
   task records **zero** tokens — the clearest evidence the ceiling is a control
   and not a gauge. `history[]` and `spend[]` ride on `state_snapshot`, so a
   cold client sees the whole ledger.
4. **Fair queueing.** Dispatch is now least-recently-served first, arrival only
   as tie-break, read off the ledger. Closes the gap between claiming *fair
   queueing* and implementing FIFO.
5. **Model-invoked tools.** `set_team_memory` and `get_task_context` are real
   tools the model chooses to call.

**Verified against deployed AWS:**

| Check | Result |
|---|---|
| `ws_smoke.py` | ✅ **61/61** (was 58 — three fairness checks added) |
| `rehearse.py --takes 2` | ✅ 12/12, twice |
| `rehearse.py --ceiling` | ✅ 5/5 — 1744/1600, clamped, nothing spent |
| Model *decides* to save a fact | ✅ *"Please make a note for the whole team that our staging URL is staging.hiveos.dev"* → `set_team_memory('staging URL', 'staging.hiveos.dev')` |
| That fact reaches another user's agent | ✅ bob: *"The staging URL is staging.hiveos.dev."* |
| `get_task_context` | ✅ summarised the ledger back to a third user |
| Fairness beats FIFO live | ✅ alice queues first, bob shown **and** dispatched first |

**The trap in fairness was not the algorithm.** `state_snapshot` sorted the
queue by SK *itself*, separately from `queue_view`. Changing dispatch order
without touching it would have left the board numbering by arrival while the
runner picked by fairness — position 1 on screen would have been wrong about
who goes next. One `fair_order`, three consumers.

**A task now costs ~800 tokens, not ~270.** Tool calling is two round trips plus
the tool schemas in every prompt. Consequences already absorbed: the demo meter
reaches ~2,250/5000 (45%, was 20%) and `--ceiling` seeds 1600 (was 500). That
number has now moved three times with the cost of a task; it has to keep
tracking it or the ceiling beat stops being watchable.

**`get_team_memory` is deliberately not a tool.** Team facts load into the
system prompt before the call, because *a queued user's agent already knows the
team's facts the moment its turn starts* is a guarantee. As a tool it would be
conditional on the model remembering to ask.

**The `remember: k = v` regex survives as a safety net** — it runs only when the
model did not save, either because it declined or because the provider was
unreachable. A tool call is probabilistic where a regex is not, and the memory
beat is the strongest thing the product does.

**Phase 7 — 2026-09-18 — canvas-first pixel workspace (merged and deployed)**

User decision: the interface was "too basic" next to the reference aesthetic. The honest
diagnosis was that the *layout* was the problem, not the art — a 100 px strip inside a 760 px
vertical panel stack reads as a dashboard with a decoration in it whatever is drawn inside it.
So the hierarchy was inverted rather than the floor restyled. Four slices, each leaving a
working app, with the risky restructure last:

- **Canvas-first shell.** The room is the primary surface; the quota became a 70 px chrome bar
  (was a 148 px panel) and a pinned member status bar went along the bottom.
- **The room.** Back wall with a baseboard, a window and the light it throws, contact shadows,
  rug, whiteboard, cooler, plants; warm laminate desks with a mug, papers and a keyboard; a lit
  monitor that spills light onto its own desk.
- **Walking.** A two-frame gait, 700 ms travel, derived from the rest frame.
- **Sitting.** Holding a slot walks you to that slot's desk and sits you down; releasing it
  walks you back.

**`SlotsPanel` and `QueuePanel` were dropped from the layout.** Not to save space — because the
room now *says* what they said. A lit monitor is the slot being BUSY; a person sitting at a desk
is its holder; a `queued #1` label under someone is their queue position. Keeping the cards
would have been the same state rendered twice, and they cost 266 px of a viewport the floor
needs. Both are still exported and unchanged.

**The seat is a rendering override, never a write to the stored position.** That one decision is
why releasing a slot walks you back for free, why the room never edits a coordinate the server
owns, and why a client reconnecting mid-task still sees the holder at the desk — the slot table
says so, and no position had to be broadcast.

**Verified on the deployed public URL:**

| Check | Result |
|---|---|
| `python scripts/rehearse.py --takes 2` | ✅ 12/12, twice, clean |
| `python scripts/rehearse.py --ceiling` | ✅ 5/5 — 694/500, clamped, nothing spent |
| `python scripts/ws_smoke.py` (pre-merge, clean board) | ✅ 58/58 |
| Board fits 640×950 with nothing clipped | ✅ 862 px into an 862 px viewport |
| Walk → sit → walk back, through a real claim | ✅ recorded from DOM state |

**Four bugs found, all mine, all from the rewrite rather than from the original code:**

1. **Every character stood beside its own name label.** `.sprite` was itself the single
   box-shadow pixel, clawed back over its centre with a negative margin, which fought the flex
   centring.
2. **The member-bar portraits never painted.** `--sp-skin` / `--sp-shirt` were scoped to
   `.sprite`, and the chips draw the same art from a different class, so the shadow colours were
   undefined. Moved to `:root`.
3. **Nobody walked, then walked at the wrong speed.** The canvas-first pass dropped the `.pawn`
   transition while leaving the comment that said movement was a transition. The fix then did
   nothing, because a *second* `.pawn` transition already lived in the
   `prefers-reduced-motion: no-preference` block and won on source order — I had introduced a
   competing pattern instead of following the file's own.
4. **One spawn in five put somebody inside the back wall.** Rendering now maps the 0–100 range
   onto the walkable strip below the wall, with the click handler applying the inverse from the
   same constant.

**And one found by rehearsing rather than by reading:** with four agent responses the board grew
222 px past a 640×950 window, so the floor and the newest answer could not be on screen at the
same time. `.board` is now capped to the viewport so the activity log's own `overflow-y: auto`
finally engages. **This is not the `overflow: hidden` amputation recorded below** — that one
clipped panels which had no scroll of their own and made them unreachable; here the log scrolls
and every entry stays reachable. The floor went 270 → 250 px in the same change, which is what
takes the log from 85 px (two lines) to 104 px (a full response).

**Phase 3 closed — 2026-09-18 — real model inference on Groq, Bedrock abandoned**

User decision, after one last verification probe: *"if bedrock is not doable then drop it, we
will use anything else."* Bedrock was re-tested first, per this file's own standing instruction
— `us-east-1`, `us-west-2` and `ap-south-1`, both vendor classes, all still refusing. Provider
chosen for zero payment friction, which is what had already cost this project a phase.

- **`backend/shared/llm.py`** — one `urllib` POST. No SDK, so `sam build` has nothing extra to
  package and there is no compiled wheel to resolve against a local Python 3.14 that does not
  match the runtime.
- **The key is an SSM SecureString read at runtime**, cached per container, IAM-scoped to that
  one parameter. Never in `template.yaml`, the stack, an env var, or git. A redeploy cannot wipe
  it, and it goes live without one — the runner retries the read on every task until it succeeds.
- **The stub is retained as an automatic fallback**, flagged `estimated`. A provider blip
  degrades the answer instead of breaking the workspace mid-take.
- `MIN_SLOT_SECONDS` (4s) replaces `STUB_DELAY_SECONDS` (5s) — it pads the **slot**, not the
  model, because a 1.5s call would leave BUSY and a queue position illegible on camera.

**Verified against deployed AWS and the public URL, not exit codes:**

| Check | Result |
|---|---|
| `python scripts/ws_smoke.py` | ✅ **58/58** |
| `python scripts/rehearse.py --takes 2` | ✅ 12/12, twice, unattended |
| `python scripts/rehearse.py --ceiling` | ✅ 5/5 — 675/500, clamped to 100%, **nothing spent** |
| Token provenance | ✅ `estimated=False`, provider-reported `total_tokens` |
| **Memory crosses users with a real model** | ✅ *"Your next deploy is scheduled for Friday at 16:00 UTC"* |
| Real task driven from the public URL in a browser | ✅ 378 tokens, no `~` prefix, answer used the team fact |
| Zero app console errors on the deployed page | ✅ (three warnings, all from the Grammarly extension) |
| Auto-dispatch latency, correctly anchored | ✅ **64–84 ms** |

**Four real failures, each found by running it rather than reading it:**

1. **Cloudflare answers urllib's default User-Agent with HTTP 403 `error code: 1010`.** It looks
   exactly like a rejected API key and is not one. Only reading the response *body* separated
   them. Any honest `User-Agent` gets through.
2. **`llama-3.3-70b-versatile` no longer exists on Groq.** The name this was first written
   against was already retired, and a wrong model fails at **runtime**, not at deploy. Now
   listed from `GET /v1/models` rather than guessed twice.
3. **Editing a template `Default:` does not change a deployed stack.** CloudFormation keeps
   existing parameter values on update, so a clean `sam deploy` left the Lambda still calling the
   dead model while the template said otherwise. Pinned in `samconfig.toml`'s
   `parameter_overrides`.
4. **Three test assertions encoded the stub's behaviour rather than the system's guarantee.**
   Two asserted `estimated is True`; the Phase 3 memory gate asserted the literal substring
   `Friday 16:00 UTC` and failed when the model wrote *"Friday **at** 16:00 UTC"* — while the
   memory load was perfectly correct. Rewritten as the real invariants, which hold in both modes
   and are strictly stronger.

**One ordering change with a consequence worth recording.** Saving a fact now happens *before*
the model call (so it persists even when the model is unreachable, and lands in its own call's
context) rather than after a stub's sleep. That made `memory_updated` overtake the frame
`rehearse.py` was waiting on — and its `expect()` **discarded** what it read, so the frame was
gone by the time the next assertion looked for it. It now buffers per socket. Arrival order is
the only thing a broadcast harness is not entitled to assume, and this is the second time that
exact trap has cost time.

**A measurement broke silently in the same change.** Dispatch latency was anchored on
`memory_updated`, which now fires at task *start* — so it reported 3,454 ms for what is actually
a 64–84 ms dispatch. Re-anchored on the slot's IDLE broadcast. A number that merely gets worse,
rather than failing, is the kind a green test will happily carry onto a slide.

**Phase 5 — 2026-09-18 — workspace floor, team chat, toasts**

**Phase 5 was previously marked "cut" and that call was wrong.** It was cut on a time-pressure
argument, but the deadline is 2026-09-20 and every MVP-Critical item was already built and
verified — which is exactly the condition `CLAUDE.md` says MVP-Supporting work should be built
under. `BUILD_PLAN.md` says to cut Phase 5 *"if Phase 3 or 4 overran"*; Phase 3 is blocked on an
AWS account restriction, which is not the same thing as overrunning. Un-cut on user decision.

- **`move_avatar` end to end.** Client action → `CONN#` row update → `avatar_moved` broadcast.
  The action was in `CONTRACT.md` since Phase 0 but had no handler and, like `send_message`
  before it, **no matching server event** — `avatar_moved` is now specified.
- `state.spawn_point()` — scatters people on join, derived from a hash of the connection ID.
  Everyone previously spawned at `(0, 0)`, which stacked every marker in one corner.
- `state.move_connection()` — conditional on the row existing, so a move racing `$disconnect`
  cannot resurrect a dead connection as a ghost member.
- **`CanvasPanel`** — absolutely positioned markers in a fixed-ratio box, moved with a CSS
  transition. No canvas element, no animation loop, no game engine. Click or arrow keys.
  Coordinates are percentages, so every window agrees regardless of width.
- **`ChatComposer`** — `send_message` has been broadcasting since Phase 1, but nothing in the UI
  could send one, so the activity log could render a `chat_message` no client could produce.
- **`ToastStack`** — memory-saved and quota-reached toasts, auto-expiring after 4.5 s.
- Per-task token cost and the "thinking" pulse already existed from Phase 4; no work needed.

**Verified against the deployed public URL, not exit codes:**

| Check | Result |
|---|---|
| `python scripts/ws_smoke.py` — now includes an avatar section | ✅ **58/58** |
| `python scripts/rehearse.py --takes 2` — no demo regression | ✅ 12/12, twice |
| A move painted on a **second, observing browser** | ✅ **270–294 ms** |
| Three markers render, positioned, one per person | ✅ |
| A marker shows `busy` exactly while its owner holds a slot | ✅ |
| Memory toast fires on a browser that did not save the fact | ✅ |
| Toast auto-expires (~4.5 s) | ✅ |
| Zero console errors or warnings on the deployed page | ✅ |
| Out-of-range coordinates clamp; non-numeric ones are refused | ✅ |

**Two real bugs found by running it rather than reading it:**

1. **`Decimal(24.92)` raises `decimal.Inexact` inside boto3 — moves were silently lost.**
   Building a `Decimal` from a float carries the full binary expansion
   (`24.920000000000001705…`) and boto3's `DYNAMODB_CONTEXT` refuses it rather than rounding.
   The mover's own optimistic UI still moved, so they appeared somewhere **nobody else saw
   them** — the exact divergence the board is supposed to be incapable of.
   Fixed with `Decimal(str(x))`.

   **The verification that missed it is the instructive part.** The first test used `73.5` and
   `21.25` — deliberately fractional, and both *exactly* representable in binary floating point,
   so they passed. Only a real mouse click produced a coordinate that was not.
   `ws_smoke.py` section 19 now asserts on `24.92` specifically.

2. **`overflow: hidden` clipped the chat and activity log off the board entirely.** Adding the
   floor pushed the panel stack to 1055 px against a 880 px window. Pinning the board to
   `height: 100dvh; overflow: hidden` made `scrollHeight === innerHeight` report success — while
   silently making two panels **unreachable**, which is strictly worse than scrolling to them.
   Caught by looking at a screenshot, not by the measurement that said it was fine.

   Fixed properly: the board grows naturally, the run queue and team memory sit **side by side**
   (two short lists, one row instead of two), and the floor is 100 px. The board is now **933 px**
   and fits a **640×950** window with nothing clipped.

**The demo window size changed: 640×950, not 640×880.** `DEMO.md` and the gotchas below are
updated. On a 1080p screen three browsers at that size still sit side by side.

**Phase 6 — 2026-09-18 — demo readiness (everything except the recording itself)**

No new features, per `BUILD_PLAN.md`. Two scripts and two documents:

- `scripts/reset-demo.sh` — the one command to run between takes. Wraps `seed.sh` (which still
  owns the DynamoDB demo state — duplicating it would let the two definitions drift) and adds
  the four things that are invisible until they are on camera: **stale `CONN#` rows** from a
  crashed tab, **in-flight SQS messages** from the previous take, **cold Lambdas**, and
  **verification**. It defaults to `TOKEN_BUDGET=5000`.
- `scripts/rehearse.py` — drives the recorded sequence as three WebSocket clients and
  wall-clock times every beat. Distinct from `ws_smoke.py` on purpose: `ws_smoke` asks *is the
  system correct*, this asks *does the sequence I am about to record work, in that order, in
  the time I have*. Every assertion is something a viewer can see on screen.
- `DEMO.md` — the run sheet: pre-flight checklist, beat-by-beat narration, the exact wording
  for the SQS claim, the stub sentence, and the mid-take fallback table.
- `SUBMISSION.md` — the writeup (`BUILD_PLAN.md` task 8), with the video link left blank.

**Rehearsed against deployed AWS — `python scripts/rehearse.py --takes 2`, 12/12 twice:**

| Check | Result |
|---|---|
| The token meter reads identically on all three screens | ✅ |
| Every screen lists all three members | ✅ |
| Alice's claim lands on a bystander's screen | ✅ 282–310 ms |
| The third request gets a real queue position, not a failure | ✅ position 1 |
| The whole team sees Charlie waiting — the queue is shared state | ✅ |
| Alice's fact reaches a teammate's screen, attributed to her | ✅ |
| **Charlie is auto-dispatched into the freed slot** | ✅ 187–234 ms |
| **Charlie's agent already knows Alice's fact — nobody told it** | ✅ |
| A browser opening the URL cold is told the counts are estimates | ✅ |
| That cold browser renders the whole board from one frame | ✅ |

Ceiling beat, separately (`--ceiling`, 5/5): real tasks drive the meter to the ceiling, the
next request is refused before the agent is invoked, and **not one token is spent on it**.

**Total product time is ~14 seconds** across all four beats — 96 s of headroom inside the
110 s allowance. The demo is not time-constrained; the narration is.

**The beat order changed, and the change matters.** `PROGRESS.md`'s earlier run sheet had Alice
claim a slot and *then* save a fact. She cannot — the scheduler refuses a second concurrent
claim from the same user, so that is two rounds and ~15 extra seconds. Folding the save into
her claim prompt makes the fact land at the exact moment her slot frees and Charlie is
dispatched into it, which is `BUILD_PLAN.md`'s beat and one continuous shot. `DEMO.md` has the
corrected order.

**Two traps found by rehearsing rather than by reading:**

1. **`--ceiling` left a 60-token budget behind and broke the next `ws_smoke.py` run.**
   `ws_smoke` resets `tokens_used` but never `token_budget`, so it inherited the tiny ceiling
   and failed two checks for reasons unrelated to the code — one of them a confusing
   *"a second concurrent claim is refused"* failure that was really a quota refusal. Fixed:
   `rehearse.py` restores the standard budget in a `finally`, including on the failure path.
2. **Bare `reset-demo.sh` seeded 1,000,000.** It inherited `seed.sh`'s production-shaped
   default, at which a ~58-token task moves the meter 0.006% — invisible, which is the one
   thing the recording cannot afford, and `DEMO.md` tells the operator to run it bare. The
   demo-facing script now defaults to 5,000; `seed.sh` keeps its generic default.

Neither was a product bug, and `python scripts/ws_smoke.py` is **49/49** with the board
correctly seeded. But both would have cost real time at 2 a.m. the night before a deadline.

**Not done — these are the user's, and Phase 6 is not complete until they are:**
recording the take, uploading to YouTube and verifying it signed-out, and submitting.
See *Manual actions pending*.

**Phase 3 without Bedrock — 2026-09-18 — memory, token accounting, enforced ceiling**

- `backend/shared/memory.py` — `facts()`, `as_context()`, `remember()`, `directive()`.
- `MEMORY#` rows keyed by a **slug of the fact's key**, not a UUID, so a re-save is an upsert.
  The UUID the contract originally specified made `set_team_memory` non-idempotent and produced
  duplicate facts in the snapshot. `CONTRACT.md` corrected.
- `state.budget_state()` / `state.add_tokens()` / `state.pct_used()` — atomic `ADD` with
  `ALL_NEW` so the broadcast and the row can never disagree.
- Agent Runner: ceiling check before the agent runs, memory loaded before the agent runs,
  token accounting after, `token_update` + `agent_response` + `memory_updated` broadcasts.
- Token provenance (`estimated` / `usage_estimated`) so no client can present an estimate as
  billed model usage — including a client that loaded cold.
- Demo budget seeded at **5,000** (`TOKEN_BUDGET=5000 ./scripts/seed.sh`), see below.

**Verified against deployed AWS — `python scripts/ws_smoke.py`, 49/49:**

| Check | Result |
|---|---|
| Saving a fact broadcasts `memory_updated` team-wide, attributed to its author | ✅ |
| `MEMORY#` row written; SK derived from the key | ✅ |
| **Another user's later agent already knows the fact without being told** | ✅ Phase 3 gate |
| Re-saving a key upserts — the team still knows exactly one deploy window | ✅ |
| `token_update` carries the new total and budget; DynamoDB agrees | ✅ |
| The increment equals the cost the response reported — no lost increment | ✅ |
| `pct_used` matches `tokens_used / token_budget` | ✅ |
| A cold client's snapshot also reports the usage as estimated | ✅ |
| `budget_exhausted` broadcast with the numbers that caused it | ✅ |
| **At the ceiling the agent is genuinely not invoked — not one token spent** | ✅ Phase 3 gate |
| A refused task still releases its slot — no leak on the refusal path | ✅ |

Confirmed live on the public URL too: the meter ticks (0 → 42 → 109 tokens), the memory panel
appears with the fact, and a later task's response contains the loaded context.

**The honesty problem, and what was done about it.** The stub spends no real tokens, so a
meter that moved would be reporting invented numbers — on a product whose entire pitch is
token governance. Three things keep it straight:

1. The count is `len(prompt + context + response) / 4` over the **real** strings — the standard
   heuristic, not a fabricated figure.
2. Every frame carrying a count sets `estimated`, and the snapshot carries `usage_estimated`
   for clients that loaded cold. The UI says *"estimated, the agent is stubbed"* next to the
   number and prefixes per-task costs with `~`.
3. `README.md` and this file say so in plain text.

**A hole in that safeguard was found and fixed during verification.** The `estimated` flag
originally rode only on live `token_update` frames, so a browser loading the public URL cold —
which is *every judge* — saw an unlabelled total that was in fact estimated. Fixed by
persisting `usage_estimated` on the METADATA row and returning it on `state_snapshot`. There is
now a smoke-test check for exactly that case.

**Why the demo budget is 5,000.** At 1,000,000 a ~68-token stub task moves the meter 0.007% —
invisible. The strip is ~68 segments, so one segment is 1.48%; a 5,000 budget puts one task at
1.36%, i.e. almost exactly one segment per task. This is not a trick to inflate the numbers:
5,000 with 68-token tasks is the same *fraction of the meter* that 1,000,000 would be with
13,600-token tasks, which is the order `PRD.md` cites for agentic workloads. Change it with
`TOKEN_BUDGET=<n> ./scripts/seed.sh`; nothing in code hardcodes it.

**Phase 4 — 2026-09-18 — Frontend HUD and public URL**

- Vite + React app in `frontend/`. No Tailwind, no component library, no router, no state
  library — React plus one CSS file. 74 KB gzipped JS, 444 KB total.
- `src/useHive.js` — the WebSocket client. Owns all board state, applies every server event in
  `CONTRACT.md`, reconnects with 1/2/4/8s backoff, re-sends `hello` on reconnect.
- `src/components.jsx` — quota strip, slot cards, run queue, activity log, team memory.
- `src/App.jsx` — entry gate (name + marker, persisted to localStorage), request form, layout.
- `scripts/deploy-frontend.sh` — idempotent Amplify manual-mode deploy. Resolves the WebSocket
  URL from the stack output, builds, **greps the bundle to prove the URL actually got baked in**,
  zips, finds-or-creates app and branch, uploads, starts, and polls to `SUCCEED`.
- Amplify app `dbavt8jr66qxx` created with an SPA rewrite (`/<*>` → `/index.html`, 404-200).

**Verified against the deployed public URL, not exit codes:**

| Check | Result |
|---|---|
| Public HTTPS URL opens cold with zero setup | ✅ |
| Board renders entirely from one `state_snapshot` | ✅ |
| Zero console errors or warnings on the deployed page | ✅ |
| **Claim propagates to a second browser in 282 ms** (gate allows ~2 s) | ✅ Phase 4 gate |
| Same, measured localhost → public Amplify origin | ✅ 282 ms |
| Both slots BUSY + a real server-assigned queue position rendered | ✅ |
| **Auto-dispatch visible in the UI 160 ms after a slot freed** | ✅ Phase 4 gate |
| Meter thresholds at 49.9/50.0/80.0/80.1/100 % → jade/amber/amber/coral/coral | ✅ |
| Quota strip fill stays tick-aligned with the track at every width | ✅ |
| `python scripts/ws_smoke.py` — backend regression | ✅ 29/29 |

Measured by installing a 20 ms DOM sampler in the *observing* browser and comparing its
absolute timestamps against the acting browser's click — so the figures are click-to-paint
across two clients, not a server-side round trip.

**Two real frontend bugs found and fixed:**

1. **A user dropped themselves from their own member list.** Membership is per-connection
   server-side (one `CONN#` row each), but `user_left` carries only `user_id`. Two connections
   for one person collapsed into a single member entry, so closing one tab removed them
   entirely while their own socket was still live. The member count is on screen for the whole
   recording, so this would have shown. Fixed by deduping members by `user_id` and adding
   `user_joined`/`user_left` to the re-sync set so the authoritative snapshot corrects any
   collapse.

2. **The queue ETA was erased ~500 ms after appearing.** `queue_update` carries
   `estimated_wait_seconds`; `state_snapshot.queue[]` does not (`state.py` `queue_view`,
   `CONTRACT.md`). The debounced re-sync therefore overwrote a correct `~8s` with `—`. Caught
   on the timestamped trace at exactly the 460 ms mark. Fixed by deriving the ETA from
   `queue_position` client-side — the server's figure is exactly
   `position * ESTIMATED_TASK_SECONDS`, so this is equivalent rather than an approximation, and
   it additionally gives a user who *reconnects while queued* an ETA the snapshot alone could
   not supply.

**Phase 2 — 2026-09-18**

- SQS `hiveos-agent-tasks` + `hiveos-agent-tasks-dlq` (maxReceiveCount 5, visibility 360s)
- Agent Runner Lambda `hiveos-agent-runner`, SQS event source, `BatchSize: 1`
- `backend/shared/scheduler.py` — one slot state machine used by both Lambdas
- `claim_agent`: atomic conditional claim, falls back across slots, else writes `QUEUE#`
- `release_agent` + automatic release in the runner's `finally`
- Auto-dispatch of the oldest queued task on every release
- Stub agent — 5s, canned text, **zero tokens**; `__hiveos_fail__` injects a failure
- `scripts/ws_smoke.py` extended to 29 checks (sections 7–12 are the Phase 2 gate)

**Verified against deployed AWS, not exit codes** — `python scripts/ws_smoke.py`, 29/29,
run 3 consecutive times clean:

| Check | Result |
|---|---|
| First claim takes `coder`; second falls back to `researcher` | ✅ |
| DynamoDB confirms both slots BUSY with the right holders | ✅ |
| **Third claim writes a `QUEUE#` row and broadcasts position 1** | ✅ Phase 2 gate |
| Queue position is broadcast team-wide, not just to the queued user | ✅ |
| **Queued task auto-dispatches into the freed slot** | ✅ Phase 2 gate |
| Queue empties in DynamoDB; every slot returns to IDLE | ✅ |
| **A raising task still releases its slot — no leak** | ✅ Phase 2 gate |
| Failing task reports `error` to its requester | ✅ |
| A user's second concurrent claim is refused | ✅ |
| DLQ empty, main queue empty, no `CONN#`/`QUEUE#` rows leaked | ✅ |

**Real bug found and fixed — frame ordering.** `claim_agent` dispatched to SQS *before*
broadcasting `agent_state_update` BUSY, so a fast-failing task posted its reply ahead of
the BUSY frame. A client would then apply BUSY *after* the IDLE release and show a slot
stuck BUSY for the rest of the demo. Failed ~50% of runs; found from the delivered=True
log proving the backend sent it, which ruled out delivery and left ordering. Both
`_claim_agent` and `release_and_dispatch` now broadcast before dispatching.
`CONTRACT.md` records the guaranteed sequence.

**Phase 1 — 2026-09-18**

- WebSocket API `hiveos-ws` + Router Lambda `hiveos-router` in `template.yaml`
- `$connect` writes a `CONN#` row and broadcasts `user_joined`; `$disconnect` deletes it and broadcasts `user_left`
- `backend/shared/broadcast.py` — fan-out with the mandatory GoneException branch
- `backend/shared/state.py` — single-table access, Decimal-safe JSON, `state_snapshot()`
- `$default` handles `hello` (→ `state_snapshot`) and `send_message` (→ `chat_message`)
- `execute-api:ManageConnections` granted on the Router role
- `scripts/ws_smoke.py` — 14-check end-to-end harness against deployed AWS
- `samconfig.toml` created and committed (was missing; see below)

**Verified against deployed AWS, not exit codes** — `python scripts/ws_smoke.py`, 14/14:

| Check | Result |
|---|---|
| `state_snapshot` has every field a cold client renders from | ✅ |
| Snapshot reports both slots `IDLE`, budget `0/1000000` | ✅ |
| Two clients connected; `user_joined` delivered to the other | ✅ |
| **One client's message reached both clients** | ✅ Phase 1 gate |
| Sender resolved from the `CONN#` row, not the frame | ✅ |
| **Broadcast past a dead connection still delivered to live clients** | ✅ Phase 1 gate |
| **GoneException branch deleted the stale `CONN#` row** | ✅ Phase 1 gate |
| Unknown action / malformed JSON return `error`, socket survives | ✅ |
| No `CONN#` rows leak after everyone disconnects | ✅ |

CloudWatch confirms the branch fired rather than the test merely passing:

```
[broadcast] gone connection=gaylUe9avQAYKEixkA== — deleting CONN# row
[broadcast] event=chat_message delivered=2 stale=1
```

No traceback anywhere in the run.

**Phase 0 — 2026-09-18** (commits `32fd214`, `f303cba`)

- Repository scaffold: 8 docs + SAM template
- AWS credentials configured; root keys retired in favour of IAM user `hiveos-dev`
- Anthropic use-case form submitted and confirmed cleared
- SAM CLI 1.166.2 installed; Docker 29.7.2 running
- Stack `hiveos` deployed to `us-east-1` — **deployment pipeline proven**
- `scripts/seed.sh` — idempotent seed/reset for demo state
- Seeded `TEAM#alpha` metadata + both agent slots `IDLE`
- AWS Budget `hiveos-guardrail` ($20, 80% alert)
- Public GitHub repo created and pushed

**Verified against deployed AWS, not exit codes:**

| Check | Result |
|---|---|
| `sts get-caller-identity` | `user/hiveos-dev` |
| `sam validate --lint` | valid |
| CloudFormation stack status | `CREATE_COMPLETE` |
| `put-item` / `get-item` round trip | item returned correctly |
| Atomic `ADD tokens_used` | returned new total `1234` — `CONTRACT.md` pattern works |
| `seed.sh` re-run | idempotent, table state correct |

---

## Blocked

| Blocker | Blocks | Status |
|---|---|---|
| **Bedrock unusable — account-level zero quotas; card added and did NOT fix it** | *Nothing any more* | **Closed 2026-09-18 — abandoned, not fixed.** Re-verified in three regions, then inference moved to Groq. Post-hackathon AWS Support ticket at most. |

### What the Bedrock blocker cost, and what closed it

**Closed 2026-09-18.** It cost the Phase 3 ordering and roughly a day of diagnosis. It no longer
costs the demo anything: the agent is real, the token counts are the provider's own, and every
beat in the demo script is demonstrable with nothing caveated away.

The one honest line the video must still carry: **inference runs on Groq because Bedrock is
quota-blocked on this account; everything else is AWS.** `DEMO.md` has the wording. Do **not**
say the agent is stubbed — that was true until 2026-09-18 and is now false.

The diagnosis below is kept because it is the evidence for that sentence, and because a future
session must not waste hours re-testing Bedrock hoping for a different answer. One `converse`
call is enough to detect if it ever unlocks.

### ⛔ Card added 2026-09-18 — did not unblock Bedrock

The user added a card. Verified in the console: **Visa •••• 3306, set as Default**; UPI AutoPay
removed; billing address and contact email updated. The payment instrument is genuinely fixed.

**Bedrock did not change.** Re-tested ~25 minutes after the card landed, well past the
"try again after 2 minutes" window AWS's own error suggests:

| Test | Result |
|---|---|
| Anthropic Haiku 4.5, us-east-1 | `INVALID_PAYMENT_INSTRUMENT` — unchanged |
| Anthropic Haiku 4.5, us-west-2 | `INVALID_PAYMENT_INSTRUMENT` — identical |
| Amazon Nova Lite / Micro, us-east-1 | `ThrottlingException: Too many tokens per day` |
| Nova Lite without inference profile | `ThrottlingException` |
| Per-day token quotas | **still 42 of 43 at zero, 0 adjustable** |
| Marketplace active subscriptions | still 0 |
| Retry poll, 10 attempts over 7 min (03:15–03:22Z) | `AccessDeniedException` every single time |

**So the missing card was real but was not the root cause.** The deeper problem is the one
that was visible all along and is not payment-related: **Amazon Nova is first-party, needs no
Marketplace subscription and no payment instrument, and still hits a hard zero per-day quota.**
A zero, non-adjustable per-day quota across 42 models is an **account-level Bedrock
restriction** — most likely because the account is new (created 2026-04-27) and AISPL. No
console setting changes it; `adjustable=False` means it cannot even be raised by request.

**This is an AWS Support ticket, and support will not turn around before the 2026-09-20
deadline. Plan Phase 3 on the fallback (`ARCHITECTURE.md` decision 7). Do not spend more
session time re-testing Bedrock** — one quick converse call at the start of Phase 3 is enough
to detect if it ever unlocks.

### ✅ CORRECTED DIAGNOSIS (2026-09-18, verified in the AWS Console)

**The "Free Plan" theory below was wrong. There is no Paid Plan to upgrade to on this
account, and chasing one is a dead end. Do not re-open it.**

Verified directly in the console (Console Home, Billing Home, Account, Free Tier, Getting
Started, notifications) — **no Free Plan / Paid Plan UI exists anywhere on this account**:

| Evidence | Finding |
|---|---|
| Service provider | **Amazon Web Services India Private Limited (AISPL)** — not AWS Inc. |
| Account created | 2026-04-27, verified (`CUSTOMER VERIFICATION SUCCESS`), currency INR |
| Console Home | **No Free Plan banner** — Free Plan accounts always show one |
| Free Tier page | Legacy model (`AWS Free Usage Tier`, "Always Free"), not credits-based Free Plan |
| Account page | No plan section, no upgrade CTA |
| Credits | **$254.62 active** (incl. $100 WeMakeDevs, expires 2027-07-31) |
| Real spend | $0.46 MTD / $0.84 last month — the account bills normally |

**The actual blocker is the payment instrument:**

| Evidence | Finding |
|---|---|
| Payment methods | **1 of 1 — UPI AutoPay (GooglePay). No credit or debit card.** |
| Backup payment method | Disabled |
| AWS Marketplace active subscriptions | **0 — "You have no subscriptions"** |
| Anthropic / AI21 invoke | `AccessDeniedException: INVALID_PAYMENT_INSTRUMENT` |
| Bedrock Model access page | "For models served from **AWS Marketplace**, a user … must invoke the model once to enable it" |

Anthropic, AI21 and Mistral on Bedrock are served **through AWS Marketplace**. Marketplace
will not complete a subscription with UPI as the only instrument — it requires a card. That
is precisely what `INVALID_PAYMENT_INSTRUMENT` reports, and why the subscription list is empty.

**Unresolved residue — do not claim the card fixes everything.** `us.amazon.nova-lite-v1:0`
is first-party, needs no Marketplace subscription, and *still* fails with
`ThrottlingException: Too many tokens per day` against a zero quota. Plausibly the same root
(no payment-verified Bedrock entitlement), but that is inference, not proof. If Nova still
throttles after a card verifies, it is an AWS Support ticket, not a config fix.

**Action required (user only — Claude must not enter card details):** add a credit/debit card
at `https://console.aws.amazon.com/billing/home#/paymentpreferences`, then re-run the
verification command in *Manual actions pending*.

---

### ⛔ SUPERSEDED — original Bedrock quota investigation (2026-09-18)

> Kept for the quota data, which is still accurate and still reproduces. The *conclusion*
> ("account on the AWS Free Plan") is **wrong** — see the corrected diagnosis above.

Every model invocation fails `ThrottlingException: Too many tokens per day`, including
models with non-zero per-minute quota. Root cause in Service Quotas (1123 quotas inspected):

| Finding | Value |
|---|---|
| Per-model **per-day** token quotas at zero | **42 of 44** |
| Of those, **adjustable** | **0** — `adjustable=False`, cannot be raised by request |
| Anthropic token quotas non-zero | 0 of 21 |
| Amazon Nova token quotas non-zero | 0 of 33 |
| Account pool `L-E3F10727` | 150,000,000/day, `adjustable=False`, not the binding limit |
| Only tpm headroom | GPT-5.6 Terra/Luna/Sol (bedrock-mantle), AI21 Jamba 1.5 (3k tpm) |

Tested empirically — two different vendors, identical failure:

```
us.anthropic.claude-haiku-4-5-20251001-v1:0   ThrottlingException: Too many tokens per day
ai21.jamba-1-5-mini-v1:0                      ThrottlingException: Too many tokens per day
```

**Not** a permissions, model-access, or use-case-form problem — all three are resolved.
~~Hard zeros that cannot be raised via Service Quotas indicate an account still on the AWS
**Free Plan**.~~ **← WRONG. Superseded by the corrected diagnosis above: the account is
AISPL and has no Free/Paid plan concept; the binding failure is the missing card.**

**Decision (user, 2026-09-18):** proceed with Phases 1–2, which need no Bedrock. If a card is
added and Bedrock unlocks, real Bedrock drops into Phase 3 unchanged. If not, fall back per
`ARCHITECTURE.md` decision 7.

#### Re-check after Phase 1 (2026-09-18) — error signature changed, quotas did not

Still **not** on the Paid Plan. Quotas are byte-for-byte identical to the first
investigation: 1123 quotas, **42 of 43 per-day token quotas at zero, 0 adjustable**, only
the 150,000,000 `Cross-Model Account-Level Tokens Per Day` pool non-zero.

What *did* change is the error for third-party models:

| Model | Before | Now |
|---|---|---|
| `us.anthropic.claude-haiku-4-5` | `ThrottlingException: Too many tokens per day` | `AccessDeniedException: INVALID_PAYMENT_INSTRUMENT` |
| `ai21.jamba-1-5-mini` | `ThrottlingException: Too many tokens per day` | `AccessDeniedException: INVALID_PAYMENT_INSTRUMENT` |
| `us.amazon.nova-lite-v1:0` | — | `ThrottlingException: Too many tokens per day` (unchanged) |

```
Model access is denied due to INVALID_PAYMENT_INSTRUMENT: A valid payment
instrument must be provided.. Your AWS Marketplace subscription for this model
cannot be completed at this time.
```

The split is diagnostic. Third-party models need an AWS Marketplace subscription, which
requires a valid payment instrument — that is now the binding failure. Amazon's own Nova
needs no subscription, so it falls straight through to the Free Plan per-day quota of zero.

**Conclusion: the upgrade did not complete. The card on the account is missing, declined,
or unverified.** Fixing the payment instrument is the prerequisite; the plan upgrade cannot
complete without it. There is no AWS API that reports plan tier directly — this is inferred
from quota state plus the two error signatures.

**Impact is confined to Phase 3.** Phase 2 already specifies a stub agent, so the queue,
slot scheduler, token accounting, WebSocket sync and the deployed URL are all buildable now.

---

## Resolved

- **Anthropic use-case form** — submitted, gate cleared. Proven by the error changing from
  `ResourceNotFoundException` ("use case details have not been submitted") to a quota throttle.
- **IAM permissions** — `AdministratorAccess` attached to `hiveos-dev`. Proven by the error
  changing from `AccessDeniedException` to a quota throttle.
- **Root access keys retired** — now using IAM user credentials.

---

## Manual actions pending

> Two actions that used to sit here are **done**. The card: Visa •••• 3306 is on the account and
> set as default — it did not unblock Bedrock, do not repeat it. The model API key: the SSM
> SecureString `/hiveos/groq-api-key` exists and the agent is live against it.

**These three are the only things standing between the repo and a submission.** Everything
buildable is done, deployed and rehearsed.

1. **Record the demo.** Follow `DEMO.md` exactly. Run `./scripts/reset-demo.sh` first (it
   pre-warms the Lambdas and verifies the board), and `python scripts/rehearse.py --takes 2`
   before that to confirm the sequence still passes. Three browsers, ~640 px wide, separate
   profiles. Under 3:00.
2. **Upload to YouTube** (public or unlisted) and **open the link in a signed-out browser.**
   An accidentally-private video scores zero regardless of what was built. Paste the link into
   `SUBMISSION.md`.
3. **Submit** before 2026-09-20, with the public URL, the repo link and `SUBMISSION.md`.

Housekeeping, not blocking:

4. **Confirm AWS Budget notification email** — check `arunishrajput7@gmail.com` for the
   `hiveos-guardrail` subscription confirmation.
5. **Optional, post-hackathon: open an AWS Support case** about the account-level Bedrock
   restriction (42 of 43 per-day token quotas at zero, `adjustable=False`, first-party Amazon
   Nova included). Nothing waits on it any more — inference runs on Groq and Phase 3 is closed.

Items 4 and 5 do not block the submission. Items 1–3 **are** the submission.

---

## Known issues and discoveries

- **A reasoning model's thinking is charged against `max_tokens`, and a cap sized for the answer
  buys nothing.** `gpt-oss-120b` spent 398 of a 400-token output cap on `reasoning_tokens` and
  returned empty content. Every layer above read that correctly and still produced the wrong
  outcome: `llm.complete` raised "no usable completion", the runner fell back to `_stub_agent`,
  and the user got composed text flagged `estimated` — after the team had been billed in full
  for the call. The bug is not in any of those layers; it is that the cap was sized for a
  three-sentence answer while the model needs room to think first. Raising it cost nothing —
  measured across four chains, per-call tokens moved by single digits — because `max_tokens` is
  a ceiling, not a budget. Intermittent, too: it only fires on prompts hard enough to provoke
  long reasoning, which is why it survived three phases of tool use before a handoff's longer
  prompt exposed it.
- **A fallback that is only offered to the *preference* case will silently do the wrong thing
  for a routing case.** `claim_any` falls back off a busy desk, which is right for "I'd like
  Ada" and wrong for "Ada says this is Iris's". The same line of code, the same data shape, two
  opposite correct behaviours — separated only by *why* the desk was named. Anything that adds a
  second reason for naming a slot has to ask whether the existing fallback still means what it
  meant.
- **The only loop guard a model cannot argue with is a tool it cannot see.** The handoff hop
  limit is enforced by leaving `handoff_to_agent` out of the request, not by the sentence in the
  prompt that also asks for it. Tested against a prompt that explicitly instructed both agents
  to pass the work back and forth indefinitely; it produced exactly two legs. The prompt line
  stays as belt-and-braces, but it is not what is doing the work.
- **An element whose meaning is its motion needs a text equivalent, and the animation needs two
  frames to start.** The envelope carries `role="status"` with a visually-hidden sentence,
  because a screen reader gets nothing from a 1.1s translation. It also has to be mounted at the
  origin and moved on the *second* `requestAnimationFrame`: with one, React can batch the
  position change into the same paint as the mount, and an element that has never been painted
  at its start position simply appears at the destination with no transition to run.
- **A marketing page that connects to the product is a write to the product.** The obvious way
  to build a "live board preview" is to open a socket. Here that writes a `CONN#` row, which
  means every visitor to the front page joins the default workspace: the member count on camera
  is wrong, and `ws_smoke.py`'s leak checks fail for reasons that have nothing to do with the
  code. Render the real components from canned props instead — the picture still cannot drift
  from the product, and the page stays free.
- **Hand-aligned ASCII in a `<pre>` breaks silently when its labels are edited.** The pipeline
  diagram in `landing.jsx` puts its `│` and `▲` under specific columns of the line above. Rename
  a service and the arrows point at whatever moved into that column — it goes on looking like a
  diagram while saying something untrue. Nothing checks this; the column arithmetic is in a
  comment above the constant.
- **Wide-layout rules written for `.board` leak onto anything that reuses its components.**
  `@media (min-width: 1100px)` releases `.floor` to `height: auto; flex: 1` so the room fills its
  grid column. Outside that grid there is nothing to fill, and a box whose contents are all
  absolutely positioned then collapses to zero height. The landing preview pins `.lp-preview
  .floor` explicitly. Reusing a board component anywhere new means checking what that media
  query does to it.
- **Inverting a theme inverts what a colour is *for*, not just its value.** Three bugs in the
  Phase 12 reskin were all the same shape. `--ink` was the page background *and* the halo behind
  desk labels — flipping it to a text colour would have blacked out every label on the floor.
  `@keyframes engage` flashed *from* dark *to* raised, which on paper had to become a tint
  settling down. The logo's hexagon was stroked amber because amber was the brightest thing
  available on graphite, and a `#f0a714` hairline on cream is barely there. Grep for the token,
  then read every use — a token whose value flips has usages that flip with it.
- **A track that was defined by its background stops existing when the background matches the
  page.** The quota strip's ticks sat on transparent gaps that fell through to a dark panel; on
  cream the gaps and the page became the same colour and the *unfilled* part of the meter
  vanished, so 12% spent looked identical to a meter that only went up to 12%. Anything that
  reads as a proportion needs its empty half painted explicitly.
- **Glow is additive, so it costs more against a light surface.** The lit-monitor spill was
  tuned at 0.55/0.2 alpha against a near-black room. At the same alphas on a cream floor the
  screen lit up and nothing around it changed — the beat reads as "a rectangle turned blue"
  rather than "that desk is working". Raised to 0.72/0.34.
- **Translating a colour between themes is a *value* move, not a hue move.** The lounge rug sat
  4% off the floor on graphite and read as a soft surface. Translated as a hue shift instead it
  became a lilac slab that read as a UI panel dropped on the room — the single loudest thing on
  a floor whose job is to stay quiet. Keep the relationship, not the recipe.
- **A frame has to out-contrast what it hangs *on*, not what it contains.** A white whiteboard
  framed in the standard hairline, mounted on a near-white wall, read as an outlined card
  floating in space.
- **A test asserting a placeholder's behaviour will fail when the placeholder improves.** Three
  checks broke on the model swap and none was a product bug: two asserted `estimated is True`
  (only ever true of the stub) and the Phase 3 memory gate demanded the literal substring
  `Friday 16:00 UTC`, failing on a model's natural *"Friday **at** 16:00 UTC"*. Write the
  guarantee, not the current implementation's phrasing.
- **Cloudflare rejects urllib's default User-Agent with HTTP 403 `error code: 1010`**, which is
  indistinguishable from a bad API key until you read the response *body*. Any outbound call
  from a Lambda to a third-party API needs an explicit `User-Agent`.
- **Changing a `Default:` in `template.yaml` does not change a deployed stack.** CloudFormation
  keeps existing parameter values on update. A clean `sam deploy` will happily leave the old
  value in place — pin it in `samconfig.toml`'s `parameter_overrides` instead.
- **Groq retires model names.** `llama-3.3-70b-versatile` was already gone. A wrong model id
  fails at runtime, not at deploy. List with `GET https://api.groq.com/openai/v1/models`.
- **`expect()` discarding frames it read is a permanent trap, not a one-off.** It has now cost
  time twice. `rehearse.py` buffers per socket; `ws_smoke.py` still filters on identifying
  fields instead, which works but is weaker. If `ws_smoke` ever flakes on a missing frame, port
  the buffer across.
- **A silently-wrong measurement survives a green test.** Dispatch latency was anchored on
  `memory_updated`; moving the memory save earlier turned that number into "alice's whole task"
  (3,454 ms vs the true 64–84 ms) and every check still passed. Anchor a timing on the event it
  actually names.
- **Never build a `Decimal` from a float for DynamoDB.** `Decimal(24.92)` carries the binary
  expansion and boto3's `DYNAMODB_CONTEXT` raises `decimal.Inexact`; `Decimal(str(24.92))` is
  exact. Anywhere a non-integer reaches DynamoDB, this is waiting. It only reproduces with
  values that are not binary-representable — `73.5` and `0.25` pass, `24.92` does not — so a
  test with tidy fractions proves nothing.
- **A layout measurement can report success for a clipped layout.** `scrollHeight ===
  innerHeight` is true both when content fits and when `overflow: hidden` amputates it. Look at
  a screenshot before believing a fit. Clipping is worse than scrolling: scrolled content is
  still reachable.
- **`ESTIMATED_TASK_SECONDS` is not the only cross-language duplicate any more** — the avatar
  coordinate space (0–100, clamped) is asserted in `router/app.py` `_coord` and again in
  `useHive.js` `moveAvatar`. Both clamp, so a disagreement degrades rather than breaks, but they
  should change together.
- **A demo-facing script must not inherit a production-shaped default.** `reset-demo.sh` called
  `seed.sh` without a budget and got 1,000,000, at which the meter does not visibly move —
  defeating the entire point of the 5,000 calibration two phases earlier. The general shape:
  when a wrapper exists *for one specific purpose*, it owns the defaults for that purpose.
- **A test that resets some state but not all of it poisons the next run.** `ws_smoke.py`
  resets `tokens_used` and clears `MEMORY#`, but never reseeds `token_budget` — so a
  `rehearse.py --ceiling` run left a 60-token ceiling behind and `ws_smoke` failed two checks
  with messages that pointed nowhere near the cause. Anything that changes `token_budget` must
  put it back; `rehearse.py` does so in a `finally`.
- **The last task before the ceiling always overshoots it** (62 of 60). A task's cost is only
  known once it has produced a response, so it cannot be charged in advance. The UI clamps
  (`Math.min(100, pctUsed)`, `Math.max(0, remaining)`), so the meter reads 100.0% and 0
  remaining rather than 103% — correct, and worth knowing before it appears on camera.
  `ws_smoke.py` never saw this because it forces the counter to exactly the ceiling.
- **A user holding a slot cannot claim another one**, so "claim, then save a fact" is two
  rounds, not one. Folding `remember: …` into the claim prompt is what makes the memory beat a
  single continuous shot. Cost ~15 s of demo time to discover by rehearsing.
- **Amplify's `404-200` rule serves the right body with the wrong status.** A deep link like
  `/some/deep/link` returns HTTP **404** but the body is `index.html`, so the app boots
  normally. The custom rule is applied exactly as written (`aws amplify get-app --app-id
  dbavt8jr66qxx --query 'app.customRules'` confirms it). Harmless for the MVP — there is one
  route, `/`, and it returns a clean 200. Not worth a redeploy; do not chase it.
- **A flag that only rides on incremental events is invisible to a cold client.** The
  `estimated` token-provenance flag shipped on `token_update` only, so the browser most likely
  to see the board — a judge opening the URL for the first time — got an unlabelled number.
  Anything that qualifies what the board *shows* has to be on `state_snapshot` too. Same family
  of bug as the queue ETA below; the snapshot is the only thing a cold client ever reads.
- **`ws_smoke.py` assumes it is the only client.** Four CONN#-leak checks fail if any browser
  anywhere is pointed at the deployed URL. Not a regression — close the tabs.
- **`state_snapshot` is less detailed than the incremental events it replaces.** The re-sync
  pattern in `useHive.js` trades exactness for self-healing, and anything carried *only* on an
  incremental frame gets wiped when the snapshot lands. `estimated_wait_seconds` was the first
  casualty. Before adding a field to an incremental event, check whether the snapshot carries it
  too — or derive it client-side.
- **Membership is per-connection, but `user_left` is per-user.** Anyone with two tabs breaks a
  naive client-side member list. Deduped by `user_id` in `useHive.js`; see the Phase 4 bugs.
- **The frontend's `ESTIMATED_TASK_SECONDS` must track `scheduler.py`'s.** Two copies of the
  same constant in two languages. If the backend's estimate is retuned (Phase 3 should, once
  real Bedrock latency is known), `frontend/src/useHive.js` has to change in the same commit.
- **No `StrictMode` in `main.jsx`, on purpose.** Its dev-only double render opens two
  WebSockets and writes two `CONN#` rows, which makes the member count lie while developing.
- **`claimed_at` is not in `state_snapshot`.** A cold client cannot know how long a BUSY slot
  has been running, which is why the slot cards show a pulsing indicator and no elapsed timer —
  a timer would read differently on a browser that watched the transition than on one that
  joined mid-task, and "identical on every screen" is the whole claim.
- **Broadcast the state change before dispatching to SQS.** See the Phase 2 bug above. The
  general rule: a frame describing committed state must go out before the work that could
  produce the *next* frame. `CONTRACT.md` → *Frame ordering*.
- **`state_snapshot` had no `queue` field**, so a client reconnecting while queued could
  not render its own position. Added `queue[]`; `CONTRACT.md` updated in the same commit.
- **`QUEUE#` sort keys needed microsecond precision.** `now_iso()` is second-granularity,
  so two claims in the same second ordered by UUID — i.e. randomly. `state.now_iso_micros()`
  is used for queue SKs only.
- **The smoke test races the product.** A queued task only exists while the task ahead of
  it runs. Two sequential AWS CLI round trips (~0.7s each) outlasted that window and read
  an empty queue that really had been there. Both assertions now come from one
  `scheduler_rows()` query.
- **`expect()` swallowed the frame it was looking for.** It discards non-matching frames,
  so a check written as "wait for BUSY, then wait for error" silently eats the error if it
  arrives first — and then fails 20s later with no clue. Every `where=` now filters on the
  identifying field (`current_user`), not just `status`, and a timeout prints the frames it
  actually saw. This is what surfaced the ordering bug.
- **Lambda-to-client sends are invisible on success.** `send_to_connection` only logged
  `GoneException`, so "did the backend send it?" was unanswerable from CloudWatch. The
  runner now logs `delivered=` on its error replies — that single line is what turned the
  ordering bug from a guess into a diagnosis.

- **`state_snapshot` cannot be pushed from `$connect`.** API Gateway does not finish
  establishing the connection until the `$connect` integration returns, so
  `post_to_connection` against it fails with `GoneException`. `BUILD_PLAN.md` Phase 1
  task 5 said "sent immediately on `$connect`". Corrected: the client sends
  `{"action":"hello"}` on socket open and the server replies with the snapshot. Same
  behaviour, one extra ~50 ms round trip. `CONTRACT.md` documents the handshake.
- **`send_message` had no matching server event.** Added `chat_message`
  `{user_id, text, ts}` to `CONTRACT.md`.
- **`samconfig.toml` was missing from the repository.** Phase 0's `sam deploy --guided`
  writes it, but it was never committed, so `sam deploy` had no config to read. Created
  and committed — it holds no secrets. Do not run `--guided` again; it would overwrite it.
- **Only `$connect` / `$disconnect` / `$default` routes exist**, with
  `RouteSelectionExpression: $request.body.action`. Every action lands in one handler, so
  new actions are code changes only. This matters because `AWS::ApiGatewayV2::Deployment`
  is an immutable route-table snapshot — adding a route later requires renaming that
  resource's logical ID (noted in `template.yaml`).
- **Lambda packaging:** both functions build from `CodeUri: backend/` with handlers like
  `router.app.lambda_handler`, so `shared/` is importable as a top-level package. No layer.
- **DynamoDB returns `Decimal`** and `json.dumps` rejects it. Every outbound frame goes
  through `state.dumps()`.
- **Bedrock *Model access* page is retired.** Serverless models auto-enable on first invoke
  across all commercial regions. The Anthropic use-case form now lives as a banner on the
  **Model catalog** page, not Model access. `DEPLOYMENT.md` Manual Action 2 reflects this.
- **Local Python is 3.14**, newer than any Lambda runtime. Compiled dependencies would get
  wrong-platform wheels if built locally. **Always `sam build --use-container`.**
- **npm global prefix `~/.local/lib` does not exist** — `npm install -g` may fail. Use `npx`.
- **AWS CLI `configure` cannot run** through the `!` prefix in Claude Code (no TTY). Interactive
  AWS commands must be run in a normal terminal.

---

## Current deployment state

| Resource | Status |
|---|---|
| CloudFormation stack `hiveos` | ✅ `UPDATE_COMPLETE` (`us-east-1`) |
| DynamoDB `hiveos-state` | ✅ seeded — METADATA + 2 IDLE slots |
| AWS Budget `hiveos-guardrail` | ✅ $20, 80% alert |
| GitHub repo | ✅ https://github.com/arunishrajput/hiveos |
| WebSocket API `hiveos-ws` | ✅ `mel2gpat9c`, stage `prod` |
| Router Lambda `hiveos-router` | ✅ verified end to end |
| SQS `hiveos-agent-tasks` + DLQ | ✅ both empty, nothing dead-lettered |
| Agent Runner `hiveos-agent-runner` | ✅ verified end to end — **real model**, provider-reported tokens |
| SSM `/hiveos/groq-api-key` | ✅ SecureString, read at runtime, IAM-scoped to the Agent Runner |
| Amplify app `hiveos` / public URL | ✅ `dbavt8jr66qxx` → https://main.dbavt8jr66qxx.amplifyapp.com |

**The Amplify app is not managed by CloudFormation.** This is deliberate and matches
`BUILD_PLAN.md` Phase 4 task 5 and `DEPLOYMENT.md`: manual-deploy mode needs no GitHub OAuth
and no build service role, which makes it fully scriptable. The consequence is that
`describe-stacks` will never mention it — `scripts/deploy-frontend.sh` finds it by **name**
(`hiveos`) so repeat runs across `/clear` sessions reuse it instead of creating duplicates.
`sam delete` will not remove it; teardown needs `aws amplify delete-app --app-id dbavt8jr66qxx`.

---

## Next recommended action

**Phase 6 — record the demo. There is no build phase left.** Phases 12–16 are all complete,
deployed and verified, and no further phase is planned. What remains is the recording, the
upload and the submission, all of which are the user's — see *Manual actions pending*.

**Before a take, the three things that changed under `DEMO.md` since it was last rehearsed
on camera:**

- **The floor is a room plan now, not an open field**, and agents have names. `DEMO.md`'s
  narration was updated for that in Phase 14/15 and reads correctly; what has *not* been
  re-verified is the framing on a real recording browser.
- **The column fills the viewport at 640×862** — re-measured on the deployed build after
  Phase 16 at **864 px of content**, with `.panel--grow` absorbing the difference so the
  activity log scrolls rather than the page. Phase 16 added nothing to the column: the floor
  is still 250 px and the envelope lives inside it. Measure in the actual recording browser
  before a take, because its chrome is what decides the viewport.
- **A handoff is a new beat available to the demo and is not in the run sheet.** It is the
  strongest 15 seconds the product has — one request, two agents, one bill — but adding it
  costs ~1,900 tokens and a beat that is not rehearsed is a beat that goes wrong on camera.
  Decide deliberately, then rehearse it; do not improvise it.

> **Standing note, recorded once so it stops being re-raised.** Every feature in `PRD.md`'s
> Must list is built, deployed and verified, and the product has been submittable since Phase
> 4. The user chose to spend the window expanding rather than recording (2026-09-19); that
> expansion is now finished, so the recording is the remaining work and `DEMO.md` needs
> re-rehearsing because the reskin changed what is on screen.

```bash
python scripts/rehearse.py --takes 2   # still the way to confirm the sequence passes
./scripts/reset-demo.sh                # clean board, warm Lambdas, verified
```

> **`DEMO.md` is the only run sheet.** The earlier list that lived in this section had Alice
> claim a slot and then save a fact, which the scheduler does not allow — rehearsal caught it.
> Two run sheets is how a wrong one gets followed at 2 a.m.

If Bedrock is ever unblocked: one `bedrock-runtime converse` call to detect it and nothing
more — the evidence says it needs AWS Support. Then swap the body of `shared/llm.py:complete`
and add `bedrock:InvokeModel` to the Agent Runner role in `template.yaml` (the Phase 3 section
records where). Nothing else changes — which is the point of having moved the call behind that
seam.

### Standing gotchas for the recording

- **Point the recording windows at `/#/workspace`, not `/`.** `/` is the landing page now. It is
  the right thing for a judge arriving cold and the wrong thing for a take — three windows each
  needing an extra click before the gate is three chances to be caught mid-scroll. `DEMO.md` has
  the link.
- **Close stray browser tabs before running `ws_smoke.py`.** Its CONN#-leak checks assert the
  table holds no connection rows, so one live browser fails four checks that have nothing to do
  with the code. `reset-demo.sh` warns when it finds live rows. **This is no longer fully in
  your control** — the public URL has real visitors, and Phase 16's run failed the same four
  checks with `BoyKraken`, `Kamal` and `divyansh` on the board. When those four are the only
  failures, verify the invariant directly instead: open two connections, close them, and confirm
  their rows are gone while the strangers' remain.
- **`rehearse.py` has no `open_timeout` and does not retry a failed handshake.** A network blip
  while the three clients connect aborts the whole take with `TimeoutError` and prints
  *"fix this before recording"*, which looks like a product failure and is not one. Seen twice
  consecutively in Phase 16, then nine sequential connects measured ~1 s each and two takes ran
  clean. Re-run before debugging.
- Three browsers at **640×950** each is the layout the single-column HUD is designed for. The
  height figure that used to be here compared the board against the *window* height and ignored
  the browser's own chrome; `DEMO.md`'s viewport-to-viewport measurement is the one to trust.
  Re-measured on the deployed build 2026-09-19: a clean board is **838 px of content**, which
  fits `DEMO.md`'s recorded 862 px viewport with ~24 px to spare. **Check it in the recording
  browser** — a Chrome with a bookmarks bar and an extension or two gives ~806 px instead, and
  the team-chat input drops below the fold.
- Each browser needs a **different profile or a cleared localStorage** to hold a separate
  identity: the entry gate persists to `localStorage['hiveos.identity']`, so two tabs of the
  same origin share one name.
