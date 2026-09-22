# PROGRESS.md

> Current execution state. A fresh Claude Code session reads this to know exactly where things stand.
> Keep it operational and short. Not a diary — history lives in git.

**Last updated:** 2026-09-22

---

## Project status

| | |
|---|---|
| **Project** | HiveOS — a cloud office where a team hires and runs a floor of AI agents on one enforced budget |
| **Track** | Ship It (deployed, public URL) |
| **Deadline** | 2026-09-20 — **met. Submitted.** |
| **🏁 Submission** | ✅ **DONE — confirmed by the user 2026-09-21. The hackathon deliverable is in. Nothing in this repo is waiting on a submission step; do not raise one again.** |
| **▶ Current phase** | **None. The build plan is finished.** Phase 27 shipped 2026-09-22 and was the last one; every phase 0–27 is `COMPLETE`. There is nothing for "start the next phase" to take — a session told to start one should say so rather than invent work. Three real defects this run turned up and did **not** fix are open under *Known issues and discoveries*, and acting on any of them needs the user to ask |
| **Phase status** | **Phase 6 `COMPLETE` — all nine tasks, submission included.** Phase 27 `COMPLETE` — deployed and verified 2026-09-22. **Nine looks in the picker** — Paper Office (the Phase 12 default, not a world phase), Night Watch, Enchanted Forest, Reef Station, Alien Colony, Cloud City, Arctic Base, Desert Outpost, Ancient Ruins — the board wears any of them, and a cross-fade carries it between any two. Gates after Phase 27: `pytest` **112/112** · `ws_smoke.py` **109/113**, unchanged from its recorded score, the four failures the documented CONN# false positive and *proved* false again by scanning DynamoDB immediately after (the only two `CONN#` rows in the table were the suite's own `TEAM#alpha`/`dana` fixture and a stale row from the Phase 24 session) · **the full 36-cell contrast matrix measured on rendered pixels at both demo framings — all eight worlds ≥ 5.54:1 worst, against 10 failing cells before the phase** · a **45-cell responsive sweep** with zero overflow and zero console output · every animation gone under `prefers-reduced-motion` in all nine worlds · and Paper Office proven unchanged by a **150-element, 81,951-computed-field** diff against a built HEAD with **zero deltas**. |
| **🎬 Demo video** | **https://www.youtube.com/watch?v=VBSuDCQa4y4** — 2:38, public, verified unauthenticated. Scene map in `DEMO.md` → *As recorded* |
| **Deployment state** | Stack `hiveos` live in `us-east-1`, `UPDATE_COMPLETE` (last updated **2026-09-22T06:01Z**). DynamoDB + WebSocket API + Router + SQS/DLQ + Agent Runner. Frontend live on Amplify — **job 42, 2026-09-22**: the Phase 27 polish build *plus* the handoff-inspector fix `5473dfa`, which job 41 predated by 35 minutes and therefore never carried. **`main`, the stack and the deployed frontend are all in step** — verified by hash, not by timestamp. The last backend change is **PRs #9, #8, #11 and #10 — bugs F, E, H and G — merged in that order and deployed 2026-09-22**; they superseded PR #7 as the head of the backend. DynamoDB TTL is `ENABLED` on `expires_at`, and **three** SK prefixes now set it (`IDEMPOTENCY#` a day, `ACTIVE#` an hour, `DLQ_REDRIVE#` fourteen days). |
| **🌐 Public URL** | **https://main.dbavt8jr66qxx.amplifyapp.com** — the landing page, verified cold, zero setup |
| **🖥 Straight to the board** | **https://main.dbavt8jr66qxx.amplifyapp.com/#/workspace** — what the recording windows point at |
| **WebSocket endpoint** | `wss://mel2gpat9c.execute-api.us-east-1.amazonaws.com/prod` |
| **Amplify app** | `dbavt8jr66qxx`, branch `main` — **not in CloudFormation** (see below) |
| **Repository** | https://github.com/arunishrajput/hiveos (public, `main`) |
| **AWS account** | `890608337320` · `us-east-1` · IAM user `hiveos-dev` (AdministratorAccess) |

> **The deliverable shipped and was submitted.** The Phase 4 gate — a deployed public URL
> showing live shared state — was met long before the deadline, and the submission went in.
> Everything remaining is enhancement, and none of it is owed to anyone.

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
| 17 | The office — shell, and a floor you staff | `COMPLETE` — deployed and verified 2026-09-19 |
| 18 | World system foundation | `COMPLETE` — deployed and verified 2026-09-20. The only one of the ten that touches shared code; ships no new world, by design |
| 19 | Night Watch | `COMPLETE` — deployed and verified 2026-09-20. The picker is a control now |
| 20 | Enchanted Forest | `COMPLETE` — deployed and verified 2026-09-21. Four worlds in the picker; the first non-human cast |
| 21 | Reef Station | `COMPLETE` — deployed and verified 2026-09-21. Five worlds in the picker; the hardest contrast case in the set, and it holds |
| 22 | Alien Colony | `COMPLETE` — deployed and verified 2026-09-20. Built out of order on the user's instruction; it was the third look in the picker at the time |
| 23 | Cloud City | `COMPLETE` — deployed and verified 2026-09-21. Six worlds in the picker; the only world brighter than Paper Office, and the one where every dark world's lighting trick stops working |
| 24 | Arctic Base | `COMPLETE` — deployed and verified 2026-09-21. Seven worlds in the picker; the first world split down the middle — snow below the walk line, aurora above it — and the one the ambient-warm/cool-state rule was written for |
| 25 | Desert Outpost | `COMPLETE` — deployed and verified 2026-09-22. Eight worlds in the picker; the world whose ground **is** a state hue, and the one that had to stop separating by hue altogether |
| 26 | Ancient Ruins | `COMPLETE` — deployed and verified 2026-09-22. Nine looks in the picker; the last world, the one with two light sources, and the first whose contrast was measured against rendered pixels rather than against tokens |
| 27 | World polish and Random World | `COMPLETE` — deployed and verified 2026-09-22. **The last phase in the plan.** The cross-fade, the four missing micro-animations, the 36-cell contrast matrix measured on rendered pixels, the responsive sweep, the keyboard-correct picker and Random World |
| 6 | Demo readiness | `COMPLETE` — **all nine tasks.** Tasks 4 and 5 were re-done on 2026-09-19 against the Phase 17 office: `rehearse.py` covers hiring and passes **15/15** twice, and `DEMO.md`'s framing and beat timings were corrected against measurement. **Tasks 6 and 7 — record and upload — were done by the user on 2026-09-20** and the link is verified public from an unauthenticated fetch. **Task 9 — submit — was done by the user and confirmed 2026-09-21** |

**All ten of Phases 18–27 are `COMPLETE` as of 2026-09-22, and the build plan is finished.**
Their briefs and findings stay in `BUILD_PLAN.md` as the record of how each was decided; the
notes below describe how the run worked and are kept for anything added later.
Every one is frontend-only and leaves `main` recordable, because Paper Office stays the default.
**19–26 depend on 18 and on nothing else**, so their order can be reshuffled — or any of them
dropped — without touching the rest. 27 depends on whichever worlds actually shipped.
**A world should now read the four findings under each of Phases 19, 20, 21, 22, 23 and 24 in
`BUILD_PLAN.md` before starting** — they are the shared-code traps a costume change walks into, and
most of them have a fix already in `worlds/nightsky.css`, `worlds/forest.css`,
`worlds/underwater.css` or `worlds/alien.css` to copy rather than rediscover. Between them: the
pre-paint key, the three `--ink`-means-dark overrides, the pale-sheet split, the honey/amber hue
separation, the world-card hover fix, the mid-floor `daylight` fixture, the
ambient-is-about-confusability reading, the meaning of `--tile`, **when a texture may tile and when
it may not — and that a surface can be periodic and continuous at once**, **why a gradient radius
must be a length and never a floor percentage**, **why every shaped gradient layer has to end in
`transparent` or it fills its whole box**, **that `.worldlayer--ground` has to be pulled below
`--walk-top` before anything is painted on the ground**, **how to solve a `background-position`
onto a layout constant**, **that a world has to check its cast, its handoff *and its scenery*
against the four state meanings before drawing any of them**, **that a 9x10 sprite carries its
identity in rows 0 and 1 and nowhere else**, **that on a world brighter than Paper Office every lighting technique the three
dark worlds established stops working, because there is no headroom above white: a bright world
reports by going DOWN in value, by going up in saturation, and by painting the shadow instead of
the light**, and — new at Phase 24 and the two that matter most for Desert Outpost — **that the
brighter a world is, the more its own real-world palette is pushed onto the four state hues,
because "high-visibility" and "reads as a state" are the same problem**, and **that a world with
more than one value register has to re-pitch `--dim` and `--faint` against the darkest of them or
the two collapse into each other.**

> **▶ Resumed 2026-09-21, on user decision. These phases are the active work.** They were
> deferred — never cut — when the 2026-09-20 deadline forced the user to take **Phase 22 only**
> and close the project out for the recording. Two world phases shipped during the hackathon (19
> and 22) and **Phases 20, 21, 23 and 24 shipped on 2026-09-21**, so six of eight are done. The
> submission is in, so the user is finishing the rest.
>
> **A session told "Start the next phase" builds the first phase in the board above that is not
> `COMPLETE` — right now that is Phase 25, Desert Outpost.** Then 26, and
> **27 last**, because it depends on whichever worlds actually shipped. 19–26 depend only on 18,
> so that order is a convention the user may reorder or cut from; 27's position is not.
>
> Nothing in those briefs was ever deleted or reduced — `BUILD_PLAN.md` carries each in full.
> There is no deadline behind any of it, which changes the pace, not the bar: **the shared
> Validation block and the recolour test still gate every one of them.**

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

**Phase 27 — World polish and Random World — 2026-09-22 — deployed and verified. The last phase
in the build plan.**

**The 36-cell contrast matrix, measured on rendered pixels.** Worst ratio per world per hue,
across the 540 and 960 framings, `before` = the HEAD build at commit `71ceae1`:

| world | `--cool` | `--honey` | `--safe` | `--alarm` |
|---|---|---|---|---|
| Paper Office *(frozen)* | 2.59 → **2.59** | 2.31 → **2.31** | 3.95 → **3.95** | 5.26 → **5.26** |
| Night Watch | 5.66 → **8.35** | 6.27 → **8.38** | **8.43** | **6.37** |
| Enchanted Forest | 4.61 → **8.21** | 5.79 → **7.54** | **8.94** | **6.23** |
| Reef Station | 3.71 → **6.22** | 5.31 → **6.15** | **8.80** | **7.28** |
| Alien Colony | 3.12 → **9.14** | 6.39 → **8.16** | **8.91** | **7.66** |
| Cloud City | 4.38 → **6.36** | 4.41 → **5.54** | **6.26** | **7.02** |
| Arctic Base | 2.84 → **7.01** | 5.34 → **6.75** | **7.96** | **7.70** |
| Desert Outpost | 3.49 → **6.42** | 5.21 → **6.74** | **9.16** | **9.26** |
| Ancient Ruins | 4.28 → **7.29** | 6.80 → **7.81** | **8.38** | **6.82** |

**Ten cells failed the 4.5:1 bar before, three after. All seven of the fixes are in the eight
worlds; the three that remain are Paper Office's, and they are identical to what they were —
which is the proof that the change never reached it.** Paper Office has been below the bar since
Phase 19 recorded it (2.63–5.26 then) and is pixel-frozen for the recording, not retuned.

**How the matrix is measured, because the method is the finding.** Three photographs of the same
staged frame — every state-hue caption forced white, forced black, forced transparent. Glyph
coverage per pixel is `(white − black) / 255`; the background is the transparent shot, with each
caption's own `text-shadow` still painted; only pixels over the stroke core (coverage ≥ 0.5)
count. Targets are found by walking the DOM for any element whose computed `color` resolves to
one of the four hue tokens, so nothing is measured by a hand-written selector list. Busy people
are staged at the four desk-side spots `components.jsx` can put them at and queued people on the
five waiting spots, because those are the only places a state caption ever appears — a
freely-walked pawn reads `idle`, which is `--faint`. Busy classes are forced for the photograph
rather than raced against a real agent, per Phase 25's note.

**What shipped:**

| | |
|---|---|
| **The cross-fade** | A veil at `z-index: 45` — above the board, below the modal, so the board dissolves behind the open picker. 200ms up, the world changes under it, 200ms down, and its own `background-color` tweens the old world's `--cream` into the new one's while it is opaque. The opacity fade is deliberately **40ms shorter** than the half-period: run at the full 200ms it measured **0.99974** opaque on the frame of the swap, which is a hairline rather than a margin. |
| **The sprite hazard** | Solved by freezing the gait, not by timing the swap. `:root[data-swap] .pawn--walking .sprite::before { animation: none }` pins every character to its whole `--art` frame for the duration. Verified by changing world mid-walk: `animation-name: none` and frame `art` on every sample through both halves, the walk itself still running, `walk-cycle` resuming when the fade settles, and the pawn's DOM node never remounted — which is also what leaves an in-flight envelope transition untouched. |
| **The nameplate defect Phase 26 handed over** | Fixed for the eight worlds. Two of its three parts are load-bearing — neither `--cool` may move, and the narrow layout's geometry may not — so the fix is the third: `--halo-plate` and `--halo-state`, Paper Office's own halos hoisted to tokens on bare `:root` and thickened from a wash of `--floor` to a plate of it inside each world's own block. |
| **Micro-animations** | Four worlds had ambient drift and no beat on any object. **Night Watch** — the signal beacon breathes (5.2s, warm, halo only, no value change on the lamp head). **Enchanted Forest** — the canopy branch rocks 3° (11s), which is what finally makes the four chinks read as holes *through* something. **Arctic Base** — the anemometer turns (7s, linear, no `alternate`). **Desert Outpost** — blown sand crossing the sun's raking pool, as **geometry only**: the pool's shape moves and its opacity, colour and saturation do not, because Phase 25 measured this world's sun at 1.9° from `--honey`. |
| **Random World** | `randomWorldId` draws from the other eight rather than drawing from nine and retrying. **9,000 draws returned the current world 0 times**, distribution 978–1,025 across the eight. It persists the world it landed on, not the fact that it was random — verified by reload. |
| **The picker's keyboard** | It was nine tab stops and no arrow keys, which is not what `role="radiogroup"` promises. Now one tab stop (roving `tabindex`), arrows and Home/End moving focus and selection together, the current world focused on open, and Escape to close. |

**Validation:**

| | |
|---|---|
| Contrast matrix | ✅ **36 cells**, rendered pixels, both framings. All eight worlds ≥ **5.54:1** worst (Cloud City `--honey`). Paper Office unchanged and below the bar, by decree |
| Paper Office frozen | ✅ **0 deltas** across **150 elements × 81,951 computed fields** at both framings, built HEAD vs built working tree, pseudo-elements included. 3 new `:root` custom properties, **0 changed values on the 73 that existed** |
| Responsive sweep | ✅ **1440 / 1100 / 900 / 540 / 390 × 9 worlds = 45 cells** clean, plus spot checks at 1600 / 1500 / 1499 / 899. No horizontal overflow, **0 console errors, 0 warnings**. Landing page checked separately at four widths |
| Reduced motion | ✅ `document.getAnimations()` returns **empty in all nine worlds** under `prefers-reduced-motion: reduce`, and the world change becomes a cut with the veil never visible |
| Mid-walk switch | ✅ gait frozen, frame `art` throughout, no remount |
| `pytest` | ✅ **112/112** (`.venv/bin/python`) |
| `ws_smoke.py` | ✅ **109/113** — unchanged from its recorded score, and the four failures are the documented `CONN#` false positive. Proved again by scanning DynamoDB immediately after: the only two `CONN#` rows in the table were `TEAM#alpha`/`dana` (the suite's own fixture racing its disconnect cleanup) and a stale `TEAM#p24arctic`/`claude` row left by the Phase 24 session. Neither belongs to this phase's browsers |
| Deployment | ✅ Amplify job **41**, `SUCCEED`. Everything above re-run against **the deployed URL**, not a local preview: the 36-cell matrix reproduces exactly, and the 45-cell sweep is clean |
| The whole flow, on the deployed board | ✅ A **real** task in Ancient Ruins — busy at 491 ms, done at 5,924 ms, **1,185 tokens** — which the model then **handed to Iris**. The world was changed to Cloud City **while that envelope was crossing**: same DOM node on every frame, position monotonic 119.6 → 340.9 px through both halves of the fade, second leg done at **1,179 tokens**. **0 console errors, 0 warnings** across the whole run |

**Three things this phase found and deliberately did not fix** — all real, none in any brief, all
recorded under *Known issues and discoveries*: a **last-agent dismissal race** in the backend, a
**stale `CONN#` row** from an old session, and the **waiting line crowding** at six or more
queued.

---

**PR #7 — the budget ceiling under concurrency — 2026-09-21 — merged, deployed and verified**

Community PR from @Phantom9869, reviewed, reworked and merged. The bug it found is real: the
ceiling *read* `tokens_used` and decided, then committed the spend at the end of the task, so two
runners arriving together both saw room and both invoked the model. Overshoot grew with the size
of the floor instead of staying at the one task's worth `CONTRACT.md` promises.

`state.reserve_budget` now asks and commits in one conditional update whose condition is the
admission rule itself — `tokens_used < token_budget`, both sides attribute paths, so DynamoDB
evaluates it against the committed row and not against a number the Lambda read a moment ago. The
second runner is tested against the first one's hold. `state.add_tokens` settles the hold against
what the provider counted (usually a credit back), and the runner's `finally` releases it on every
path that never reached a reply.

**Three things the PR had wrong, and they are the transferable part:**

1. **A hold the size of the prompt is not a hold.** The PR reserved `len(prompt)/4` — about a
   dozen tokens against a task that costs ~800. Each admission left the counter near enough to
   where it was found that the next desk still read room, so a floor of four could still walk
   through a ceiling with one token left in it. `RESERVATION_CEILING` is
   `(MAX_TOOL_ROUNDS + 1) * MAX_TOKENS` instead — derived from the two constants that bound what
   a task may emit, roughly twice a measured task. **Sizing is the whole mechanism here, not a
   detail of it.**
2. **A hold must not be able to read as a spent quota.** Unclamped, a 1,806-token hold on the
   1,600-token board `DEMO.md` documents for the ceiling beat would push `tokens_used` past
   `token_budget`, and `useHive.js` latches the refused state on exactly that comparison from both
   frames that carry the ceiling — red banner, disabled send, on a board with budget to spare, for
   as long as one task ran. It is clamped to the remainder, which parks the counter *exactly* on
   the ceiling: high enough to refuse everybody else, never higher than the meter can honestly
   show. **A server-side placeholder is a client-visible number on this product.**
3. **A refund in `except` misses the paths that `return`.** Moved to `finally`, ahead of the slot
   release and fully swallowed — the release is the invariant that outranks it, so nothing in
   front of it may raise. The hold also moved off the `task` dict into a local: `task` is an SQS
   body the ledger and the handoff read back.

The PR's own race test stubbed `reserve_budget` out and fed it scripted answers, which proves
nothing about the condition. `tests/test_budget_ceiling_race.py` was rewritten around a fake
METADATA row that evaluates the real condition against live state, and every claim in it was
checked by mutation — shrinking the hold, dropping the clamp, dropping the `ConditionExpression`
and dropping the settlement each fail tests that name the failure.

**Verified on the deployed stack, not just locally.** `pytest` **65/65**; `sam build
--use-container && sam deploy` at 17:54 UTC (runner `CodeSha256 nIcfOCnE19…`, was
`jmqvPgsr6t…`); `ws_smoke.py` **109/113** — the same four documented `CONN#` false positives and
nothing else, with section 17 (the ceiling refusal) and section 24's `chain=2007, team total=2007`
both passing, which is the settlement reconciling exactly across two legs of a handoff. Unlike the
Phase 24 run, the post-run scan found **three** lingering `CONN#` rows rather than zero (two on
`alpha` from the run's own sockets, one on `p24arctic` from an earlier browser session) — the same
ungraceful-`$disconnect` residue the four checks have always been tripping on, and nothing this PR
touches.

A throwaway workspace then drove the three things the smoke test does not reach, because they are
new. Numbers as measured:

| | |
|---|---|
| The hold is taken *before* the model answers | `tokens_used` went **0 → 1,805** while the task ran, then settled to **633** |
| It is the size of a task, not of a prompt | **1,805** held against a task that cost **633** |
| It settles with no residue | METADATA **633** = the `token_update` frame's **633** |
| Clamped at the ceiling | started at **99,999/100,000**, the hold parked the counter on **exactly 100,000** and never above it |
| The settlement is still exact there | **100,625** = 99,999 + the **626** the task really cost |
| A refusal takes no hold | parked at **100,000/100,000**, `budget_exhausted` broadcast, counter **unchanged** |

The scratch workspace was deleted afterwards; the public board was never touched.

**The world picker on the landing page — 2026-09-21 — deployed and verified**

User request, and a small one: the `◑` button that opens the world picker now sits in the landing
page's nav as well as in the workspace's title bar. A visitor can choose the look before they have
entered anything.

**It needed no new plumbing.** `Landing` already renders inside `WorldProvider` — App.jsx wraps
every route, because the preview floor draws the sprite system and somebody who picked a world
should not meet a paper-office character at the door. So the same `WorldModal` the app bar opens
works here unchanged, writes the same two `localStorage` keys, and the whole page (nav, bands and
preview floor) was already repainted by each world's token block.

**The button is deliberately identical to `.appbar__gear`** — same 26px square, same hairline, same
raised fill, same glyph, same `aria-label="Change world"` — because it is one control in two
places rather than two controls. It is a separate rule rather than a shared class on purpose: the
app bar is a fixed-height row with its own width crisis (the 520px wordmark rule Phase 18 had to
add), and coupling the two would mean a future fix to one silently moved the other.

**What changed:** `frontend/src/landing.jsx` (the button, the `useState`, and the modal render) ·
`frontend/src/styles.css` (one new `.lp-nav__world` block, landing-scoped).

**Verified:**

| Check | Result |
|---|---|
| `npm run build` | clean; `./scripts/deploy-frontend.sh` job **36 → SUCCEED** |
| **The width risk — Phase 18's trap** | a second control in a nav row is exactly what pushed a 390px phone into horizontal scroll in Phase 18. Swept **1440 / 1100 / 960 / 900 / 560 / 540 / 430 / 390 / 360**: **zero horizontal overflow at every one**, the nav itself never scrolls, and the button is a full 26×26 and inside the viewport at all nine. No new breakpoint was needed, so neither demo framing moved |
| The modal over a **sticky** nav | `.lp-nav` is `position: sticky; z-index: 20` and `.modal` is `position: fixed; z-index: 50` — `elementFromPoint` at the centre of the nav returns the scrim, so the dialog genuinely covers it. Checked at 540, at 390 **scrolled 1200px down**, and at 1440 |
| The dialog itself | `role="dialog"`, `aria-modal="true"`, a `radiogroup` of all six worlds, click-away close — all inherited from `WorldModal`, none of it re-implemented |
| Picking a world from the landing page | repaints the page live (body and nav), updates `theme-color` and `color-scheme`, writes `hiveos.world` **and** `hiveos.world.paint`, and **carries into the workspace and back** |
| Button legibility, all six worlds | glyph on its own fill **6.65–8.69:1** at rest and **11.72–15.87:1** hovered. Its fill against the nav is 1.07–1.32:1 and the hairline carries the edge at 1.30–1.79:1 — which is the same construction `.appbar__gear` has against its own bar (1.11–1.20:1), so this matches the product's existing icon-button standard rather than introducing a weaker one. **If icon-button boundaries should be strengthened, that is a deliberate change to both bars and not this one.** |
| **The workspace is untouched** | Paper Office at 540 against a `c3da8ca` build: **73/73 custom properties identical**, **5,828 computed fields across 62 elements — 6 differences, all `#rect`**: one live pawn and its two labels standing somewhere else between the two loads, and two sprites caught 1px apart mid-`pawn-idle`. **Zero style diffs**, page height 1164 identical. Cloud City the same way: 6,014 fields, 14 diffs, every one a live animation frame or a pawn's position |
| Cold visitor on the deployed URL | lands on Paper Office (`#fff8e7`), the button is present and labelled, zero overflow, **zero console errors or warnings** |

**Not re-run:** `pytest`, `ws_smoke.py`, `rehearse.py`. No backend file changed and no protocol,
schema or shared workspace behaviour moved — the diff is one component's markup and one
landing-scoped CSS block, and the workspace parity above is the check that actually covers it.

---

**Phase 26 — Ancient Ruins — 2026-09-22 — deployed and verified**

The ninth look, **the last world in the set**, and the one with two light sources. A temple
complex worked by an expedition: pillared stone chambers standing against a carved wall under a
glyph frieze, a mosaic runner down the corridor between two standing torches, an urn throwing a V
of two shadows, a colonnade where the queue waits, vines over a fallen column and a broken roof
letting daylight onto the flags.

**Files:** `frontend/src/worlds/ruins.css` (new, 2,014 lines), `frontend/src/worlds.js` (+228,
additive), `frontend/src/main.jsx` (+1 import). `styles.css`, `components.jsx` and `sprites.js`
were **not touched** — the seventh world in a row inside the two-file seam Phase 18 built, plus
the one import line.

**The problem this world exists to solve.** Torch amber *is* `--honey` in a costume. On a dark
ground the warn hue has to come up to carry a word, so it is an orange at 25deg — and firelight
is an orange at 25-35deg. A world that painted its torchlight as light would lay the queued
colour across every chamber floor, not as a prop that could be recoloured but as the
illumination itself; the brief's own non-negotiable (flicker must not read as an alert) is the
same problem from the other end. Phase 25's finding 3 transfers whole: **when the ambient light's
colour collides with a state hue, state the light as geometry.** The flame is a near-white core
rather than an orange one, the tint is held at 0.31 saturation against honey's 0.59 and never
painted above 0.10 alpha, and what actually says "torchlight" is the *shape* — two pools
spreading across the flags and the V of two shadows the urn between them throws.

**Measured against the tokens — worst case across all eight of this world's surfaces:**

| token | worst | binding surface |
|---|---|---|
| `--cool` | **6.38:1** | the lit chamber floor |
| `--safe` | **6.05:1** | the lit chamber floor |
| `--honey` | **6.58:1** | the lit chamber floor |
| `--alarm` | **4.92:1** | the lit chamber floor |
| `--screen-on` (indicator, bar 3.0) | **7.65:1** | the lit chamber floor |
| `--ink` | **9.87:1** | the lit chamber floor |
| `--dim` | **7.17:1** | the lit chamber floor |
| `--faint` | **4.95:1** | the lit chamber floor |

**And then measured against the pixels, which is new and is the finding that matters.** A caption
does not sit on a token — it sits on whatever is painted under it, which in a lit world is the
surface plus every pool, wash and glow over it. Hiding the text, screenshotting, and sampling
every pixel inside each caption's own box found **two failures the token table passed**: the busy
chamber's cool wash at **2.39:1** under the `ENGINEER` caption, and the tablet's own spill rising
into the caption two pixels above it at **3.41:1**. Both fixed; after the fixes every caption
clears the bar against its real background at both framings — **worst 4.52:1 at 540 and 5.19:1 at
960**, with the busy role caption going 3.41 → 5.71.

| check | result |
|---|---|
| `npm run build` | ✅ clean, zero warnings |
| `./scripts/deploy-frontend.sh` | ✅ **job 40 `SUCCEED`**, Amplify app `dbavt8jr66qxx` |
| Ruins live on the **deployed** URL, chosen through the real picker | ✅ `data-world=ruins`, `--floor #2b2721`, `theme-color #16130f`, pre-paint key written |
| picker now offers | ✅ **9 cards**, Ancient Ruins ninth |
| real tasks run on the deployed board in this world | ✅ two, **1,406 real tokens** (711 + 695) on `TEAM#p24arctic`; the busy beat sampled in-page from **8,172 ms to 12,322 ms**, with `.room--busy`, `.desk--busy` and the pawn reading `working` all in lockstep |
| every rule scoped to `:root[data-world='ruins']` | ✅ **55/55**, checked by parsing the file; 0 `!important` |
| `--walk-top` never set, only read | ✅ **0 declarations, 4 reads** |
| `@keyframes` name collisions | ✅ none — all four prefixed `ruins-`, 0 hits in the other seven stylesheets |
| background layer lists aligned | ✅ every multi-layer rule's `image`/`size`/`position`/`repeat` counts match (22, 15, 16, 21 layers on the four big ones) |
| the queue read against the colonnade at 540 px | ✅ three queued members between the columns, `queued #N` in `--honey` at **6.48:1**, names at **9.20-9.90:1** |
| `WAITING AREA` caption on the stylobate | ✅ **5.34:1** in `--faint` |
| idle chamber and busy chamber in one frame | ✅ warm torch top-left, lit glyph panel top-right, at both demo framings |
| **the quiet-floor gate** | ✅ 30 s sampled on an idle deployed floor: torch **0.860-1.000**, pool **0.860-1.000** — a 14% excursion over 6.3-9.3 s loops, 60 distinct dust transforms, nothing that steps or blinks |
| switch to Paper Office and back, no reload | ✅ tokens, `theme-color` and the floor recipe (back to exactly **3** gradient layers, out to 18) all restored, `navigations: 1` throughout |
| **Paper Office unchanged** | ✅ **zero style deltas** across **73 custom properties** and **115,401 computed fields** over **70 elements**, against a HEAD worktree build served side by side; the only 6 deltas are the live pawn's own coordinates, which differ between page loads because they are real state. Floor rect identical at 516×260 |
| Phase 22's world-card hover fix, in this world | ✅ selected **8.30:1 at rest, 6.84:1 hovered**; unselected **13.68:1 / 14.64:1** |
| cold load | ✅ `data-world` stamped pre-paint, `color-scheme: dark` on root **and** meta, `theme-color #16130f`, body already the world's ground — no cream flash |
| demo framings | ✅ floor **516×260** at 540 and **515×536** at 960 — the documented numbers, unmoved |
| responsive sweep 1440 / 1100 / 900 / 540 / 390 | ✅ **zero horizontal overflow at every one** |
| console | ✅ **0 errors, 0 warnings** on the deployed board |
| `prefers-reduced-motion: reduce` | ✅ all six animations report `animationName: none`, **0 running animations**; they return under `no-preference`, and the two torches and two pools run at different periods with different offsets |
| `pytest` | ✅ **112/112** (`.venv/bin/python`) |
| `python scripts/ws_smoke.py` | ✅ **109/113**, unchanged — the four documented CONN# false positives |
| stack state | ✅ `hiveos` `UPDATE_COMPLETE`, untouched — nothing was deployed to it |

**On the CONN# four, a fifth confirmation.** Browser closed before the run, then the whole table
scanned after it: **two** `CONN#` rows, both `TEAM#alpha` / user `dana` — the smoke suite's own
fixtures racing its own disconnect cleanup. None in the live workspace, none from a stranger.
Identical to what Phase 25 found.

**One thing this phase found that it could not fix, and it belongs to Phase 27.** The busy room's
nameplate box overlaps its own `--cool` top border — `.desk`'s flex column starts at the room's
top edge, and `.room--busy` turns that 2px border `--cool` in every world while the label takes
`--cool` too. Measured on **Paper Office** at the same framing it reads **1.00:1**, identical, so
it is base geometry rather than this world's, and Paper Office is pixel-frozen. Phase 27's
contrast matrix will meet it in all nine worlds at once.

**Four findings recorded in `BUILD_PLAN.md` under Phase 26**, all four for Phase 27. In short:
**a length is a percentage in disguise too**, because `--tile-size` is 44px at 540 and **52px at
960** — stable across the two narrow demo framings and nowhere else, which is narrower than the
rule five phases have been writing down; **measuring a token against a token is not measuring the
contrast**, and the pixel method that caught this world's two real failures should be how Phase
27 runs its 36-cell matrix; **the base geometry puts the dimmest text in the system directly on
top of a light source**, so a lit desk's role caption needs `--dim` — Phase 24's register finding
applied to a light rather than to a surface; and **a world's light has to stand where the floor
plan lets it be seen**, after both the chamber doorways and the carved wall turned out to be
blind.

---

**Phase 25 — Desert Outpost — 2026-09-22 — deployed and verified**

The eighth look, and **the world whose ground is a state hue**. A research outpost in the dunes an
hour before sunset: adobe outposts under stretched shade canopies, a solar array and its charge
controller on each back wall, field stations under sun-hooded readouts, a water cask, a caravan
track with marker posts across the middle of the floor, cacti and agave, and a dune ridge along
the back with the sun going down behind it.

**Files:** `frontend/src/worlds/desert.css` (new, 1,843 lines), `frontend/src/worlds.js` (+240,
additive), `frontend/src/main.jsx` (+1 import). `styles.css`, `components.jsx` and `sprites.js`
were **not touched** — this is the sixth world in a row that stayed inside the two-file seam Phase
18 built, plus the one import line.

**The problem this world exists to solve.** `--honey` means *queued, and 50-80% of the budget
spent*, and it is a deep ochre. A dune field is the same family of colour covering the **largest
surface in the product** — the corridor every pawn stands on and every small caption sits over.
Reef Station had the same shape of problem in the busy blue, but its blue was the *band*; this is
the floor. The resolution was to stop using the hue axis at all: honey is left 14.5deg from the
sand, that gap is asked to carry nothing, and the whole separation is value (0.42 against 0.94)
and saturation (0.98 against 0.28). Underneath it is the guarantee that has held since Phase 19 —
**amber is only ever a fill and honey is only ever a word**, and a floor is never a word.

**Measured, not eyeballed — worst case across all eight of this world's surfaces:**

| token | worst | binding surface |
|---|---|---|
| `--cool` | **4.94:1** | the lit outpost deck |
| `--safe` | **4.85:1** | the lit outpost deck |
| `--honey` | **4.92:1** | the lit outpost deck |
| `--alarm` | **4.90:1** | the lit outpost deck |
| `--screen-on` (indicator, bar 3.0) | **3.30:1** | the lit outpost deck |
| `--dim` | **6.54:1** | the lit outpost deck |
| `--faint` | **4.71:1** | the lit outpost deck |

The binding surface is `--room-floor-busy` every single time, which is Phase 24's finding 2
arriving exactly as it predicted: a world with a second value register has to clear its small type
against the **darkest** of them, not against the page. `--faint` carries `.desk__role` under every
nameplate and a nameplate is inside an outpost, so pulling it down to clear 4.71:1 there walked it
into `--dim`, and `--dim` had to come down with it. The pair is held **1.47:1** apart against the
1.39-1.43 Paper Office, Cloud City and Arctic Base each hold.

| check | result |
|---|---|
| `npm run build` | ✅ clean, zero warnings |
| `./scripts/deploy-frontend.sh` | ✅ **job 38 `SUCCEED`**, Amplify app `dbavt8jr66qxx` |
| Desert live on the **deployed** URL, chosen through the real picker | ✅ `data-world=desert`, `--floor #efddad`, `theme-color #f8eddc`, pre-paint key written |
| picker now offers | ✅ **8 cards**, Desert Outpost eighth |
| real tasks run on the deployed board in this world | ✅ several, **~2,800 real tokens** spent on `TEAM#p24arctic`; the busy beat sampled in-page at `.room--busy` + `.desk--busy` from **507 ms to 4,645 ms** with the pawn reading `working` |
| the queue, read against the dunes at 540 px | ✅ `queued #1` in `--honey` on the caravan track, **6.65:1**, between two marker posts |
| `WAITING AREA` caption on the track | ✅ **6.37:1** in `--faint` |
| idle outpost and busy outpost in one frame | ✅ warm shaded adobe against cool deck, lit controller, lit readout — at both demo framings |
| switch to Paper Office and back, no reload | ✅ tokens, `theme-color` and the floor recipe (back to exactly 3 gradient layers) all restored |
| **Paper Office unchanged** | ✅ **zero deltas** across **73 custom properties** and **4,611 computed fields** over **159 records**, against a HEAD worktree build, animations pinned to t=0 |
| Phase 22's world-card hover fix, in this world | ✅ selected card **9.37:1 at rest, 6.83:1 hovered**; unselected **16.40:1 / 13.61:1** |
| the brand fill stays findable on a warm page | ✅ amber **1.70:1** against the page where Paper Office manages 1.43:1, and **1.52:1** against its own empty track |
| demo framings | ✅ floor **516×260** at 540 and **515×623** at 960 — the documented numbers, unmoved |
| responsive sweep 1440 / 1100 / 960 / 900 / 540 / 390 | ✅ **zero horizontal overflow at every one** |
| console | ✅ **0 errors, 0 warnings**, local and deployed |
| `prefers-reduced-motion: reduce` | ✅ all three animations report `animationName: none`, **0 running animations**; they return under `no-preference` |
| `pytest` | ✅ **65/65** (`.venv/bin/python` — the system 3.14 has no `botocore`) |
| `python scripts/ws_smoke.py` | ✅ **109/113**, unchanged — the four documented CONN# false positives |
| stack state | ✅ `hiveos` `UPDATE_COMPLETE`, untouched — nothing was deployed to it |

**On the CONN# four, a fourth independent confirmation — and this one names the cause.** Phase 19
blamed the developer's own browser tabs, Phase 22 corrected that to "one cause, not the only one",
Phases 23 and 24 found a stranger's row and then none at all. This run closed the browser first
and then scanned the whole table: **two** `CONN#` rows, and both were `TEAM#alpha` / user `dana` —
**the smoke suite's own fixtures**, racing its own disconnect cleanup. None in the live workspace,
none from a stranger. The failures are the suite observing itself, which is the most benign
explanation yet offered and the first one that is directly evidenced.

**Four findings recorded in `BUILD_PLAN.md` under Phase 25**, all four of which belong to worlds
26 and 27 rather than to this one. In short: **a gradient ANGLE is a percentage in disguise** — a
`linear-gradient(100deg …)` is a diagonal bar in a 175×125 room and a full-height vertical streak
in a 175×299 one, which is Phase 20's finding 2 in the one form it did not cover and is harder to
catch because the angle genuinely is framing-independent; **when a world's ground IS a state hue
the hue axis is spent and the right move is to stop using it**, and the cost lands on the identity
palette, where the ochre wedge is unavailable twice over because a warm-brown hood is both the
ground it stands on and the word hanging under it; **a light whose colour IS a state hue has to be
painted as its shadow**, which is a second and independent route to Cloud City's rule — low raking
sun measures 1.9deg from `--honey`, so the sun is stated as geometry (long shadows, dark dunes with
lit crests) and never as colour; and **a smooth closed curve on an even surface is a spill**, so
Phase 24's rim trick needs its shapes to overlap — the rims that run *through* a neighbour stop
being outlines and become the crack network the world would otherwise have drawn as forbidden
strokes.

**Two things worth knowing before Phase 26.** The solar array is **room-level**, not per-desk as
the brief has it: `.desk` is a centred flex column with a two-line nameplate above the stack and
the open desks sit at floor x 8 and x 91, so there is no free space either above or to the side —
the array and the controller live in the two top corners the nameplate and the speech bubble never
reach, which is Cloud City's placement finding taken as given. And **a real task finishes in about
four seconds**, which is shorter than a screenshot round trip; the busy beat was verified by
sampling the DOM from inside the page, and a world phase that wants the busy state in a photograph
should force the class and say so rather than race the agent.

---

**Phase 24 — Arctic Base — 2026-09-21 — deployed and verified**

The seventh look, and **the first world split down the middle**: packed snow below the walk line,
a twilight sky with an aurora above it. A polar research station — insulated cabins with heavy
doors and drifted thresholds, survey stations under frosted instrument windows, an ice-core rack,
antenna masts standing in their own snowdrifts, a route of black flags across swept ice, and a
weather board on a post against the ridge.

**What landed.** `frontend/src/worlds/arctic.css` (new, 49 scoped rules), a registry entry plus a
five-explorer cast, a four-penguin agent cast and an eight-colour palette in `worlds.js`, one
import line in `main.jsx`. **Three files and nothing else** — the diff is `+1` line in
`main.jsx`, `+235` in `worlds.js`, and one new file.

**The problem this world exists to solve.** Cloud City is bright everywhere and the three dark
worlds are dark everywhere. A polar station at midwinter is neither, because snow is bright
*precisely by reflecting the whole sky dome* and the sky is what is left over. So both halves of
the project's lighting experience apply here, each on its own side of one line — and that line is
`--walk-top`, the one number a world file may read and may never set.

| | below the line | above the line |
|---|---|---|
| **regime** | Cloud City's: no headroom above white | Night Watch's: additive light on near-black |
| **surfaces** | eight, value 0.88–1.00, saturation 0.01–0.18 | sky 0.09–0.50, carries no word, not walkable |
| **how relief reads** | as the **shadow** it casts — sastrugi, boot tracks, the berm, the door drift | as the **light** it emits — aurora, stars, afterglow |
| **the fixture in the band** | — | **pale**, where Cloud City's had to be dark |

That last row is the transferable half. `.fixture--board` is the same element in both worlds and
took the opposite treatment, for the same reason both times: **the only object that reads against
a band is one on the other side of it from the band.** A world that picked one lighting register
and applied it everywhere gets this exactly backwards.

**The three value registers, and why they are what makes the phase's gate passable.**

| register | token | value | against |
|---|---|---|---|
| the snow outside | `--floor` `#f2f7fb` | L 0.924 | — |
| a cabin deck | `--room-floor` `#cfdae1` | L 0.688 | **1.32:1 below the snow** |
| a lit cabin deck | `--room-floor-busy` `#b9d1e1` | L 0.614 | **1.11:1 below idle, at 2.3× the saturation** |
| the band | `--sky-deep` → `--sky-low` | L 0.017–0.11 | — |

A sky harbour's pavilion is open deck at value 0.99, so both of its lights had to report by going
*down* and the warm one could not exist at all. A polar cabin is a sealed box, so its deck is
allowed to be darker than the ground outside — and that gap is headroom. It buys the thing the
brief's gate actually asks for: **the two lights move in opposite directions.** The living
window's warm pool goes **up** in value against the cabin deck; the instrument port's cool wash
goes **down**. A viewer never has to tell warm from cool at 540px on a compressed recording —
only lighter from darker, which survives compression, a bad projector and a colourblind reader.

**The recolour test.**

| requirement | what changed |
|---|---|
| ground-plane **structure** | `.floor` is rebuilt from 3 layers to 12: a berm line, a near ridge, a far ridge, the afterglow, an opaque twilight sky, one sastrugi field, three drift shadows and three bare-ice plates. Not one checker remains |
| **two of three** decoration slots | all three — sky: aurora curtains + a star field; ground: trodden aprons, boot grain and a drifting ground blizzard; air: falling snow |
| the **sprite design table** | two new tables: five parka'd explorers (`PARKA_TEAM`) and four penguins (`PENGUINS`), the third world to use `agentDesigns` |
| **three of five** fixtures | all five — weather board, ice-core rack, frosted pane with icicles, the low sun's raking pool, antenna masts |
| the **form** of a state expression | busy moves off the desk and onto the **cabin's back wall**: an instrument port beside the living window, dark when idle and cool-lit when working, in a place the nameplate and the speech bubble never reach |

**The state-legibility contract — measured, not eyeballed.** Every state hue against **all eight**
of this world's surfaces; worst case per hue:

| | `--cool` | `--safe` | `--honey` | `--alarm` | `--screen-on` (indicator) |
|---|---|---|---|---|---|
| **worst of eight** | **5.84:1** | **5.13:1** | **4.96:1** | **4.96:1** | **3.47:1** |
| binding surface | a lit cabin deck, every time | | | | |
| hue | 196.9° | 148.2° | 31.0° | 4.7° | 196.2° |
| saturation | 0.92 | 0.90 | 0.96 | 0.83 | 0.93 |

Bar is 4.5:1 for anything carrying a word and 3:1 for an indicator. Text tokens clear it too —
`--ink` 10.48:1, `--dim` 6.75:1, `--faint` **4.71:1**, all worst-case against the same lit deck.
The brand fill carries its own dark label at **9.80:1** and still carries no meaning. `--honey`
and `--amber` separate by **4.16:1 in value** at only 8.3° of hue, which is the separation a
bright world gets back and a dark one cannot have.

| check | result |
|---|---|
| `npm run build` | ✅ clean |
| `./scripts/deploy-frontend.sh` | ✅ **job 37 `SUCCEED`** → https://main.dbavt8jr66qxx.amplifyapp.com |
| every rule scoped to `:root[data-world='arctic']` | ✅ **49/49**, checked by parsing the file |
| `--walk-top` never set, only read | ✅ 0 declarations, 11 reads; deployed value still `14%` |
| `@keyframes` name collisions | ✅ none — all five prefixed `arctic-`, 0 hits in the other six stylesheets |
| **Paper Office unchanged** | ✅ **73/73 custom properties and 37,959 computed fields, ZERO deltas** against a HEAD worktree build served side by side |
| world switch with no reload | ✅ arctic → paper → arctic, tokens and floor repaint both ways |
| cold load | ✅ `data-world` stamped pre-paint, `theme-color` `#eef3f8`, body ground already arctic — no cream flash |
| hire + run on the deployed board | ✅ Jim and Pam hired through the real UI; **21,688 real tokens** spent on `TEAM#p24arctic` |
| every desk lit at once | ✅ **4/4 `BUSY`** confirmed in DynamoDB while the browser rendered it |
| queue + handoff in frame | ✅ `queued #1–#4` in `--honey` on the ice path, and the dispatch tube crossing the corridor — **see the note below on how this frame was produced** |
| responsive sweep | ✅ **zero horizontal overflow** at 1440 / 1100 / 960 / 900 / 540 / 390 / 360; the nav never scrolls and the world button is a full 26×26 inside the viewport at 360 |
| `prefers-reduced-motion: reduce` | ✅ all five animations → `none`; `document.getAnimations()` returns **0** |
| console | ✅ **0 errors, 0 warnings** |
| `pytest` | ✅ **42/42** |
| `ws_smoke.py` | ✅ **109/113** — unchanged, the four documented CONN# false positives |
| stack state | ✅ `hiveos` `UPDATE_COMPLETE`, untouched — nothing was deployed to it |

**On the CONN# four, a third independent confirmation.** Phase 19 blamed the developer's own
browser tabs, Phase 22 corrected that to "one cause, not the only one". This run scanned the whole
table immediately after the suite and found **zero `CONN#` rows anywhere** — not two belonging to
a stranger, as at Phase 23, but none at all. The rows the suite reads are transient and gone
before the scan; there is no leak.

**On the queue-and-handoff frame, stated plainly.** Both were photographed by setting the states
on the **deployed** page — the real build, the real stylesheet, the real DOM — rather than by
winning a race against the scheduler. The reason is the scheduler being correct rather than
anything being broken: `ws_smoke.py`'s own wording is *a preference is not a reservation*, so on a
four-desk floor N simultaneous claims never queue at all, and N+k queue only for as long as the
first task runs (~8s). Five separate attempts across three workspaces, with claims fired from 8
identities at once, produced real 4/4 `BUSY` floors but never a queue that outlived the poll. The
CSS under test is the same either way — `.pawn--waiting .pawn__state` renders `rgb(125,67,5)`,
exactly `--honey` — and the scheduler's own queue behaviour is covered unchanged by `ws_smoke.py`
and `pytest`. **A later world phase that wants the queue live should shrink the floor to two desks
first.**

**Four findings recorded in `BUILD_PLAN.md` under Phase 24**, all four of which belong to worlds
25 and 26 rather than to this one: **the split-world rule** (both lighting regimes apply, each on
its own side of `--walk-top`; a fixture inside the band takes the band's regime, not the world's;
and a building darker than its ground buys the opposite-directions trick a uniformly bright world
cannot have); **that every value register you add costs a re-pitch of `--dim` and `--faint`**,
because the small type has to clear the darkest one and `--faint` walks into `--dim` on the way
down; **that a bright world's collisions with the state hues are systematic rather than
incidental**, because "high-visibility" is defined as *what stands out against white* and that is
the same job the four state hues do — an orange parka, a red route flag, a green aurora and an
orange bill are four props and four state hues in one world, and **Desert Outpost is made of
`--honey`**; and **that a crack is not a line but an edge between two materials**, which took a
graph-paper failure and a scratched-lens failure to arrive at.

**Four notes that are not corrections.** The room-level state expression sits on the cabin's back
wall beside the living window, which is Cloud City's placement finding taken as given rather than
rediscovered — and the pair is separated by **shape** as well as hue, a wide low instrument pane
against a small square with a cross mullion, because at 540px shape is the stronger channel. The
penguins carry **no `F` layer**, because a penguin's white front is the first thing anybody draws
and it is not visible from directly above; `--sp-skin` therefore stays unambiguously human, the
same tell the colony's robots and the harbour's drones carry. The handoff's `.envelope__flap` is
**reused** as the tube's strap rather than stood down as Cloud City stood its down — a courier
bird is a silhouette and a second shape on a silhouette becomes the average of the two, but a
tube is a solid object and a strap is a **line**, and lines survive at 24×10 real pixels where
blobs do not. And the aurora was **rebuilt once**: the first version was a repeating gradient of
evenly spaced rays with an opaque veil cutting its top and foot, which rendered as a barcode *and*
painted over the ridge the band most needed; it is now eleven soft lozenges at hand-picked
positions, in an element whose height is `calc(var(--walk-top) - var(--tile-size) * 0.34)` so it
stops above the ridge by construction instead of being covered up.

---

**Phase 23 — Cloud City — 2026-09-21 — deployed and verified**

The sixth look, and the only one of the nine brighter than the paper office. The workspace floats:
stone platforms with gaps of open air between them, open pavilions with beacons on their roofs, a
windsock, a departures board, a railed opening onto the sky, and the cloud line running along the
back of the deck with a very small airship above it.

**What landed.** `frontend/src/worlds/cloudcity.css` (new, 50 scoped rules), a registry entry plus
a five-pilot cast, a four-drone agent cast and an eight-colour palette in `worlds.js`, one import
line in `main.jsx`. **Three files and nothing else.**

**The problem this world exists to solve, and it is the inverse of every world before it.** The
three dark worlds all report state the same way — a state is bright and the world is not — and
none of that is available here, for reasons that are arithmetic rather than aesthetic:

| | the harbour | the state |
|---|---|---|
| **value** | eight surfaces 0.94–0.99, sky 0.91 | `--cool` **0.46**, `--screen-on` **0.64** |
| **saturation** | surfaces 0.02–0.16, sky 0.47, scenery ≤0.43 | `--cool` **0.91**, all four 0.81–0.95 |
| **light** | there is no headroom above white | the sun is painted as the **shadow** it is interrupted by |

The brightest cyan that still clears the 3:1 indicator bar against this world's own surfaces is
value **0.64 — darker than the floor it sits on**, and darker than `--screen-on` is in any other
world. So a bright thing up here is weather and a deep saturated one is a desk spending money,
which is Reef Station's argument turned exactly upside down.

**The state expression whose form changed.** Paper Office tints a working room's floor; a bay
lights its dome; a module lights its antenna array; a hollow glows from inside; a dome lights its
porthole. **A pavilion lights the beacon on its roof** — the one object on this floor whose entire
purpose is to be seen from a distance, which is why a harbour has one. It sits on the front-LEFT
corner rather than on the ridge, and that is measured rather than stylistic: `.desk` is centred in
the room and its two-line nameplate rides above the desk stack, so a beacon at `left: 50%` is
directly behind the `ENGINEER` caption. It matters more here than the equivalent would anywhere
else, because the base stylesheet's speech bubble covers the monitor whenever an agent has
anything to say — in every world — so the signal lamp cannot be the thing a viewer is relied on to
see.

**The handoff.** A courier bird, and **the first handoff object in the product that is dark**.
Every one before it is pale — a paper envelope on cream, a pale envelope on navy, a pale leaf on
moss, a near-white capsule in dark water, a near-white pulse on regolith — four of them because the
floor is dark and one because it is literally paper. Here the floor is the brightest surface in
the product, so the same reasoning gives the opposite answer. Near-neutral at 0.12 saturation
besides, for the reason the reef's capsule was not cyan.

**Verified, not assumed:**

| Check | Result |
|---|---|
| `npm run build` | clean; `./scripts/deploy-frontend.sh` job **35 → SUCCEED** |
| **The gate this phase is named for** | every small mono label read at 540: `--faint` pulled two steps darker than Paper Office's to carry `.pawn__state`, `.desk__role` and `WAITING AREA` on the brightest surface in the product — **4.74:1**, where Paper Office's weight does not survive here |
| Real task in Cloud City on the **deployed** board | **679 tokens**; pavilion entered `--cool` at **458 ms**, border `rgb(11,90,118)`, beacon lit to `--screen-on` and pulsing `cloud-beacon 2.4s`, lens opacity 1, label `Ada`, role `Engineer`, pawn `working` — all unchanged |
| Busy artwork, computed, after the base 220 ms transition settles | `.desk--busy .desk__monitor` resolves to `rgb(11,90,118)` = `--cool`; the world's (0,4,0) rules beat the base state rules correctly |
| **Whole flow walked in this world, deployed** | hired Zed and Nox, then drove **five identities across five browser contexts**: **4/4 desks lit at once** (both pavilions *and* both open desks, `for alice`/`for bob`/`for carol`/`for eve`), and a real queue with a **settled** `queued #1` in `--honey` `rgb(138,78,7)`, eve standing on a painted bay mark on the boarding platform |
| **Real agent-to-agent handoff, deployed, at 960 and 540** | two of them, Ada → Iris; label `"Ada passed this task to Iris."`, `role="status"`, `aria-live="polite"` — untouched. The courier legible as a dark silhouette against the bright deck at both viewports |
| **`ENVELOPE_MS` contract** | computed `transition-duration` **1.1s, 1.1s** at both viewports — inherited from the base stylesheet, untouched; this world declares **zero** transitions of its own |
| **Paper Office unchanged** | **73/73 custom properties identical** and **4,752 computed fields compared across 54 elements — 4 differences, all four the bounding box of one live pawn and its two labels**, i.e. where a person was standing between the two page loads. **Zero style diffs**, and document `scrollWidth`/`scrollHeight` **540×1164** identical |
| Layout parity between worlds | floor box, both rooms, the waiting area and `--walk-top` byte-identical, switching live with no reload |
| Switch to Paper Office and back, no reload | returns identical on every sampled measure |
| **Contrast, measured live from the deployed board's computed values** | `--cool` **5.80** · `--safe` **4.79** · `--honey` **5.00** · `--alarm` **5.38** — worst case each, across **nine** surfaces rather than eight, because a queued member's `--honey` label stands on `--rug` and that is where all four worst cases land; `--screen-on` **3.50** as an indicator; `--dim` 6.67, `--faint` 4.74, `--ink` 13.55; `--on-amber` on `--amber` **9.98**. All clear their bar |
| All three budget bands, on the deployed board | healthy at 3.4%, `--honey` warn at **78.0%** (both the figure and the strip fill in `rgb(138,78,7)`, unmistakably not the brand amber), `--alarm` at **81.2%** in `rgb(165,42,32)` |
| Hue separation | cool↔safe **46.6°**, honey↔alarm **28.0°** (the widest of the six worlds), cool↔screen-on 0.5° — one hue at two weights, 0.46 → 0.64 in value. honey↔amber is only 7.0° **and separates by luminance at 3.61:1**, where Paper Office manages 2.29 and no dark world can do it at all |
| Identity palette | all eight clear **4.0:1** on the platform, a pavilion deck, a busy pavilion deck and a gap (worst 4.05), at saturation 0.15–0.61 against the state hues' 0.81–0.95 |
| Every world rule scoped | **50/50** carry `:root[data-world='cloudcity']`; 0 unscoped, and 0 unscoped inside the reduced-motion block |
| Colour literals outside the token block | **zero** — 59 hexes, all inside `:root[data-world='cloudcity']`; zero raw `rgb()` anywhere |
| `--walk-top` never set by the world | confirmed — the registry owns it; read 7 times, including the ground slot's `top` |
| `!important`, or `content:` carrying a word | **none of either** |
| `prefers-reduced-motion` | verified **at runtime** with `emulateMedia`, not structurally: under `reduce` all six of this world's animations resolve to `none`, the base `screen-flicker` too, the pawn to `none` and the envelope transition to `0s`. **The beacon stops LIT and the lens stays at opacity 1**, so BUSY survives as a static state |
| Pre-paint / cold load | stored paint `{"scheme":"light","themeColor":"#e9f2fb"}`, and **the registry's `themeColor` literal matches the world's own `--cream` token exactly — asserted for all six worlds**, dark and light |
| Responsive sweep | 1440 / 1100 / 960 / 900 / 540 / 390 — **zero horizontal page overflow at every width**, workspace and landing page |
| Console, deployed | **zero errors, zero warnings** — workspace and landing page |
| Landing page in this world | repaints; preview floor shows two lit pavilions, `for alice` / `for bob`, `working` and a `queued #1` |
| Phase 22's world-card hover fix, in this world | holds — the selected card reads **9.98:1 at rest and 7.09:1 hovered**; an unselected card reads 17.67:1 at rest and 15.83:1 hovered |
| Picker, deployed | **six looks**, Cloud City selected and persisted |
| `pytest` | **42/42** |
| `ws_smoke.py` | **109/113** — the four documented CONN# false positives; a scan immediately after found exactly **two** `CONN#` rows, both belonging to the stranger `dana` on `TEAM#alpha`. **`TEAM#p23cloud` had none** — every connection this session opened, across five browser contexts, was gone |

**Four findings recorded in `BUILD_PLAN.md` under Phase 23**, all four of which belong to worlds
24–26 and the first of which is the largest in the set so far: **every lighting technique the three
dark worlds established stops working on a world brighter than Paper Office**, because there is no
headroom above white — so a bright world reports by going *down* in value, by going *up* in
saturation, and by painting the shadow instead of the light. Also: **Phase 19's findings 2 and 3
are dark-world findings and lapse entirely here** (no scrim overrides, no chair re-point, no
`--sheet`), while finding 4 *inverts* and gives the value separation back; **`--tile` was wrong a
third time in a third direction** — a gap in a sky harbour shows the sunlit cloud below and is
therefore *brighter* than the deck, and correcting it moved every contrast number in the world;
and **a gap needs an asymmetric pair of lips or it is a line rather than a hole.**

**Three notes that are not corrections.** The beacon moved off the ridge because the nameplate is
there — see above, and every remaining world should place its room-level state expression where
neither the nameplate nor the speech bubble reaches. The **courier bird is one `clip-path` polygon
rather than three stacked boxes**, and the first attempt was the other way round: at 22×10 real
pixels a body, a wing bar and a head rendered as a dark blob with a pale blob on it — which is
Phase 21's "drawn twice" lesson in another key, that below a certain size a shape assembled from
overlapping boxes becomes the average of its parts and only an outline survives. And **the windsock
is charcoal and white rather than orange**, which is the Phase 21 coral trap for the second world
running; the same check caught brass fittings sitting 1.8° from `--honey` at 0.49 saturation and
riding on every pawn through `--sp-accent`, so every metal fitting in this world is galvanised
steel and the goggle leather is held at 0.26 against honey's 0.95.

**One thing found that is not this phase's and may not be fixed here.** A queued member's
`queued #1` label renders in `--faint` rather than `--honey` for as long as they are still walking
to the waiting area. `components.jsx` derives the *text* from `position` and the `pawn--waiting`
*class* from `waiting && !isWalking`, so the two disagree for about a second. It is identical in
every world including Paper Office, it is shared code a world phase may not touch, and it resolves
correctly the moment the walk ends — confirmed on the deployed board, `rgb(138,78,7)`. Recorded
for **Phase 27**, which is the phase allowed to touch shared code.

**Not re-run:** `rehearse.py`. No backend file changed, Paper Office is the demo world and is
proven unchanged above, and the shared Validation block only requires it when a world changes the
demo framing — which none of them may.

**Test partition left in the table:** `p23cloud` (created here; budget set via the admin panel to
20,000 so a full floor, a queue and two handoffs all fit — ~16,300 tokens spent across about a
dozen tasks and two handoff chains, which also walked the meter through all three budget bands).
Inert, like the others — Phase 9 partitions every row by team.

---

**Phase 21 — Reef Station — 2026-09-21 — deployed and verified**

The fifth look, and the one the plan singled out as the hardest contrast case in the set: a blue
world that has to keep a blue busy state legible. The office is submerged — research domes on
settled deck plating, sand ripples between them, kelp and coral in the corners, and everything lit
from a surface far enough above that only a net of caustics and a few shafts of it arrive.

**What landed.** `frontend/src/worlds/underwater.css` (new, 56 scoped rules), a registry entry plus
a five-design cast and an eight-colour palette in `worlds.js`, one import line in `main.jsx`.
**Three files and nothing else.**

**The problem this world exists to solve, and how it is solved.** Every world before it separated
its busy state from its scenery by **hue** — cyan against navy, against moss, against regolith.
Here the scenery *is* blue, so hue is not available:

| | the water | the state |
|---|---|---|
| **value** | all eight surfaces 0.14–0.31 | `--cool` **0.94**, `--screen-on` **0.97** |
| **saturation** | caustics 0.11, identity palette 0.13–0.39, sprite body 0.22 | `--cool` **0.74** |
| **motion** | nothing on this floor turns | the sonar sweep goes round once every **2.6 s**, and only while BUSY |

So a pale blue thing down here is scenery and a saturated bright one is a desk spending money —
and the busy indicator earns the rest of its separation from a rotating bearing line, which is the
brief's "brightness *and* the flicker" taken literally. The base `screen-flicker` is kept on top of
it.

**The state expression whose form changed.** Paper Office tints a working room's floor; a bay
lights its dome; a module lights its antenna array; a hollow glows from inside. **A dome lights its
porthole** — one small hard-edged bright disc on the shell facing the corridor, which is the
loudest thing this world can do at 540 px precisely because it is small and round. The deck takes
the wash, and note what the wash does *not* do: it is the same **value** as the idle deck at half
again the saturation, because forty metres down "lit" is not "lighter", and making the deck
brighter would have spent the brightness the porthole and the scope need.

**The handoff.** A sealed sample capsule, near-white at 0.09 saturation. The obvious capsule for a
reef station is a glowing cyan one, and that is the single worst object this board could have: a
state hue detaching from a desk and flying across the room. Same decision the Forest's pale leaf
made, under more pressure.

**Verified, not assumed:**

| Check | Result |
|---|---|
| `npm run build` | clean; `./scripts/deploy-frontend.sh` job **34 → SUCCEED** |
| **The gate this phase is named for** | busy-versus-idle screenshot pair at 540 px: the working dome carries a `--cool` border, a lit scope, a bright cyan porthole and a cyan deck against an idle dome's dark scope and grey porthole. Unmistakable on a compressed frame |
| Real task in Reef Station on the **deployed** board | **661 tokens**; dome entered `--cool` at **318 ms**, border `rgb(63,211,240)`, scope `rgb(94,232,247)` = `--screen-on`, sweep opacity 1, label `Ada`, `working` — all unchanged |
| **Whole flow walked in this world, deployed** | hired Zed and Nox, then drove **five identities across five browser contexts**: **4/4 desks lit at once** (both domes *and* both open desks, `for alice`/`for bob`/`for carol`/`for dave`), and a real queue with `queued #1` in `--honey` `rgb(255,171,107)`, eve standing on a mooring plate in the current channel |
| **Real agent-to-agent handoff, deployed, at 960 and 540** | Ada → Iris, **1,934 tokens** across two desks; label `"Ada passed this task to Iris."`, `role="status"`, `aria-live="polite"` — untouched. Capsule legible against dark water at both viewports |
| **`ENVELOPE_MS` contract** | computed `transition-duration` **1.1s, 1.1s** at both viewports — inherited from the base stylesheet, untouched |
| **Paper Office unchanged** | **73/73 custom properties identical** and **5,580 computed-style properties compared across 62 elements — 5 differences**: four `left/top/right/bottom` on `.pawn[2]`, i.e. where a live pawn was standing, and one `.sprite` transform caught mid-`pawn-idle`. **Zero style diffs** |
| Layout parity between worlds | floor, waiting area, both rooms, both desks, both nameplates and **all six fixture/decor centres byte-identical**, switching live with no reload |
| Switch to Paper Office and back, no reload | returns identical on every sampled measure |
| Contrast, measured from computed values | `--cool` **5.47** · `--safe` **5.48** · `--honey` **5.24** · `--alarm` **4.53** — worst case each, across all eight surfaces; `--screen-on` **6.67** as an indicator; `--on-amber` on `--amber` **9.23**. All clear 4.5:1 |
| Hue separation | cool↔safe **47.1°**, honey↔amber **15.3°**, honey↔alarm **18.6°**, cool↔screen-on **3.9°**; and the two scenery collisions this world had to solve — safe↔kelp **68.6°**, alarm↔coral **80.3°** |
| Identity palette | all eight clear **4.0:1** on the seabed, a dome deck and the plating (worst 4.06), at saturation 0.13–0.39 against the state hues' 0.48–0.74 |
| Every world rule scoped | **56/56** carry `:root[data-world='underwater']`; 0 unscoped |
| Colour literals outside the token block | **zero** — 65 hexes, all inside `:root[data-world='underwater']`; zero raw `rgb()` anywhere |
| `--walk-top` never set by the world | confirmed — the registry owns it; the ground slot *reads* it |
| `!important`, or `content:` carrying a word | **none of either** |
| `prefers-reduced-motion` | verified **at runtime** with `emulateMedia`, not structurally: under `reduce` all five of this world's animations resolve to `none`, the base `screen-flicker` too, the envelope transition to `0s` and the pawn to `0s`. The sweep's opacity still reads 1 busy / 0 idle, so BUSY survives as a static bearing line |
| Pre-paint / cold load | stored paint `{"scheme":"dark","themeColor":"#071a24"}`, and **the registry's `themeColor` literal matches the world's own `--cream` token exactly — asserted for all five worlds** |
| Responsive sweep | 1440 / 1100 / 900 / 540 / 390 — **zero horizontal page overflow at every width**, and the roster-strip items that sit past 390 do so identically in Paper Office |
| Console, deployed | **zero errors, zero warnings** — workspace and landing page |
| Landing page in this world | repaints; preview floor shows two lit domes, `for alice` / `for bob`, charlie `queued #1`, and the warn strip at 56.9% using `--honey` rather than the brand amber |
| Phase 22's world-card hover fix, in this world | holds — the selected card reads **9.23:1 at rest and 7.14:1 hovered**; an unselected card hovered reads 15.44:1 |
| Picker, deployed | **five looks**, Reef Station selected and persisted across a reload |
| `pytest` | **42/42** |
| `ws_smoke.py` | **109/113** — the four documented CONN# false positives; a scan immediately after found exactly **one** `CONN#` row, belonging to the stranger `dana` on `TEAM#alpha`, connected before the run. Every connection the suite opened was gone, and `TEAM#p21reef` had none |

**Four findings recorded in `BUILD_PLAN.md` under Phase 21**, all four of which belong to worlds
23–26. The most expensive is that **a `radial-gradient` paints its last colour across its whole
box, not out to its radius** — three portholes that ended on their rim colour rendered as one pale
slab with a single disc in it. Also: `.worldlayer--ground` is `inset: 0` and has to be pulled down
to `--walk-top` before anything is painted on the ground, or it paints on the sky; **a surface can
be periodic *and* continuous at once** — sand ripples are genuinely periodic while the sand is not,
which is a third case the Phase 19/20/22 texture rule did not have; and motion defeats a lattice
but `prefers-reduced-motion` takes that defence away, so the static pair still has to hold.

**Two notes that are not corrections.** The cast was **drawn twice**, and the lesson generalises:
identity in a 9x10 top-down sprite lives in **rows 0 and 1 and nowhere else**, because rows 6–9 are
the walk machinery and rows 2–5 are dominated by the eyes. And this is the **first world whose
`--sp-accent` could not carry a hue** — a translucent aqua fin is a small bright cyan mark on every
pawn, in the world whose whole argument is that only desks are cyan. The same check caught the
defect that nearly shipped: the brief names the busy blue as this world's risk, and the one about
to go on the floor was a **red-orange coral**, 6° from `--alarm`, sitting permanently in the corner
of a board whose job is to say when you have gone over budget. The coral is mauve.

**One stale thing found while writing this up, and it was not this phase's.** `README.md` and
`SUBMISSION.md` both listed the worlds by name — "Paper Office, Night Watch or Alien Colony" —
and **Phase 20 never added Enchanted Forest to either**, so the two files a judge actually opens
were a world behind before this phase started and would have been two behind after it. Both now
list all five. This is the same defect the 2026-09-19 documentation pass recorded and named: a
phase's doc sweep reaches `PROGRESS.md` and `BUILD_PLAN.md` and stops short of the judge-facing
files. **A world phase has to grep for the world list, not just append to the phase record.**

**Not re-run:** `rehearse.py`. No backend file changed, Paper Office is the demo world and is
proven unchanged above, and the shared Validation block only requires it when a world changes the
demo framing — which none of them may.

**Test partition left in the table:** `p21reef` (created here; budget set via the admin panel to
3,000 to paint the meter into the healthy band at 22.0%, then to 20,000 so a full floor, a queue
and a handoff all fit — ~9,000 tokens spent across eight tasks and one handoff chain). Inert, like
the others — Phase 9 partitions every row by team.

---

**Phase 20 — Enchanted Forest — 2026-09-21 — deployed and verified**

The fourth look, and the first whose cast is not human. The office becomes a clearing inside a
large wood: hollow stumps for rooms, carved benches for desks, a trodden path between them, and
woodland animals working the floor.

**What landed.** `frontend/src/worlds/forest.css` (new, 49 scoped rules), a registry entry plus a
five-design cast and an eight-colour palette in `worlds.js`, one import line in `main.jsx`. **Three
files and nothing else** — the first world to stay inside the two-file budget the brief predicted,
because Phase 19's `index.html` pre-paint key covers every dark world after it.

**The first non-human cast.** Fox, owl, badger, hare and stag, and the `A`/`D` layers Phase 18
added are load-bearing for the first time: an ear, a beak and an eye are exactly what a recoloured
office worker cannot have. Seen from directly above the silhouette above the eyes is the whole of
identity, which is lucky — ears are the one part of an animal that reads instantly from overhead.
Every design is a different pair of them; the badger, which has none worth drawing, is identified
by its blaze instead.

**One cast, deliberately, and for Night Watch's reason rather than the colony's.** A clearing where
the animals work the benches together makes the same claim the night deck does: the agents live
here. The obvious second species would be will-o'-wisps — and that is precisely the one this world
may not have, because **the wisp is already what a working slab lights up as**, and a floor with
wisps walking about could not also use one to mean BUSY.

**The state expression whose form changed.** Paper Office tints a working room's floor; a bay
lights its dome; a module lights its antenna array. **A hollow glows from inside** — the
will-o'-wisp at the slab fills the stump and comes up its inner wall. Same `--cool` token, same
label text, and the light wells up from the middle rather than falling from above.

**The world where ambient-warm/cool-state is first actually visible.** The lantern hanging in each
hollow does not change when the agent starts working. It is deliberately not restated under
`.room--busy`: the warm light was always there and means nothing, the cool light is what arrived.

**Verified, not assumed:**

| Check | Result |
|---|---|
| `npm run build` | clean; `./scripts/deploy-frontend.sh` job **33 → SUCCEED** |
| Real task in Enchanted Forest on the **deployed** board | **758 tokens**; hollow entered `--cool` at **325 ms**, border `rgb(86,207,238)`, label `Ada`, pawn state `working` — all unchanged |
| Busy artwork, computed | `.desk--busy .desk__monitor` resolves to `rgb(110,230,245)` = `--screen-on` once its 220 ms transition settles; the world's (0,4,0) rules beat the base state rules correctly |
| **Paper Office unchanged** | **73/73 custom properties identical** and **2,329 computed-style properties compared across 57 elements — 4 differences, all four `left/top/right/bottom` on `.pawn--mine`**, i.e. where a live pawn was standing, set inline from the socket. Zero style diffs |
| Layout parity between worlds | floor box **516×260** at 540 and **515×622** at 960, and page height **1166**, byte-identical in both worlds, switching live |
| Switch to Paper Office and back, no reload | returns byte-identical on every sampled property |
| Contrast, measured from computed values | `--cool` **7.19** · `--safe` **6.98** · `--honey` **6.74** · `--alarm` **4.86** — worst case each, across all eight surfaces; `--screen-on` **8.90** as an indicator; `--on-amber` on `--amber` **8.51**. All clear 4.5:1 |
| **The gate this phase is named for** | `--safe` at hue 142.6° vs `--foliage` at 90.0° — a **52.6°** gap where *Paper Office's own* jade-vs-ferns gap is 25.4°. No scenery green exceeds value **0.60** against the jade's **0.83**. Confirmed visually with the meter painted into the healthy band at 24.2% directly above the clearing |
| Hue separation | cool↔safe **49.6°**, honey↔amber **15.8°**, honey↔alarm **19.8°** |
| Every world rule scoped | **49/49** carry `:root[data-world='forest']`; 0 unscoped |
| Colour literals outside the token block | **zero** — 64 hexes, all inside `:root[data-world='forest']`; zero raw `rgb()` anywhere |
| `--walk-top` never set by the world | confirmed — the registry owns it |
| `!important`, or `content:` carrying a word | **none of either** |
| `prefers-reduced-motion` | **structurally** verified: both animations and both `@keyframes` are the only ones in the file and all four sit inside the single `no-preference` block. The world declares **zero** transitions of its own |
| `ENVELOPE_MS` contract | computed `transition: left, top` at **1.1s, 1.1s** — inherited from the base stylesheet, untouched |
| Pre-paint / cold load | stored paint `{"scheme":"dark","themeColor":"#0e1710"}`, inline script stamps `color-scheme: dark` before CSS, and **the registry's `themeColor` literal matches the world's own `--cream` token exactly** — asserted for all four worlds |
| Responsive sweep | 1440 / 1100 / 900 / 540 / 390 — **zero horizontal overflow** at every width |
| Console, deployed | **zero errors, zero warnings** — workspace and landing page |
| Landing page in this world | repaints; preview floor shows two lit hollows, `for alice` / `working`, charlie queued, and the warn strip using `--honey` (`#ffa565`) rather than the brand amber |
| Full floor, deployed | four desks — Ada and Pam in hollows, Zed and Nox at open desks with their path spurs under them |
| Picker, deployed | **four looks**, Enchanted Forest selected and persisted across a reload |
| Phase 22's world-card hover fix, in this world | holds — the selected card reads **8.51:1 at rest and 6.74:1 hovered**, against the 1.00–1.02:1 the pre-fix bug measured in dark worlds |
| `pytest` | **42/42** |
| `ws_smoke.py` | **109/113** — the four documented CONN# false positives; a scan immediately after found exactly **one** `CONN#` row, belonging to the stranger `dana` on `TEAM#alpha`, connected before the run and still there after. Every connection the suite opened was gone |

**Four findings recorded in `BUILD_PLAN.md` under Phase 20**, three of which belong to worlds 21
and 23–26. The largest is a **correction to a rule both previous world phases recorded**: "two
lattices whose tile sizes share no useful factor" is right for star fields and crater pocks and
wrong for moss, because that rule is about surfaces made of *discrete things*. A continuous
surface may not tile at all — two attempts at it shipped a visible dot grid before the texture
became eight non-repeating blotches. Also: a gradient radius must be a **length** off
`--tile-size` and never a floor percentage, because the floor is 516×260 at one demo framing and
515×622 at the other; a `background-position` can be **solved** onto a layout constant and the
answer is framing-independent; and a world must check its cast and its handoff against the four
state meanings before drawing either — which is why the handoff leaf is the *pale underside* of a
leaf rather than a green one.

**Not re-run:** `rehearse.py`. No backend file changed, Paper Office is the demo world and is
proven unchanged above, and the shared Validation block only requires it when a world changes the
demo framing — which none of them may.

**Test partition left in the table:** `p20fern` (created here, budget set to 3,000 via the admin
panel to paint the meter into the healthy band, ~725 tokens spent). Inert, like the others —
Phase 9 partitions every row by team.

---

**PR #6 — 2026-09-21 — the demo budget stopped tracking the cost of a task**

An outside contribution (Phantom9869) against `reset-demo.sh`, raising its default
`TOKEN_BUDGET`. The one-line change was **right about the bug and wrong about the number**, and
reviewing it turned up a second copy of the same defect.

**The bug.** `reset-demo.sh` defaulted to **5,000**, calibrated in Phase 3 when the agent was a
stub costing ~58 tokens a task — one task, one segment of the strip. A task costs **~800** now (a
real model plus tool schemas in every prompt), so 5,000 is **four or five tasks and the board is
spent**. Harmless while the only thing reading that default was a camera; not harmless once the
URL is public and judges arrive cold, because the second visitor finds a dead floor.

`rehearse.py:595` had tracked this correctly for the ceiling beat — 60 → 500 → 1600, with a
comment saying *"if a task's cost changes again, this has to follow it"*. The standard budget
never got the same treatment. It is the same class of defect, in the number nobody re-derived.

**Why not the 500,000 the PR proposed.** One task would move the meter 0.16% — about a ninth of a
segment on a ~1.5%-per-segment strip. That reproduces on the demo board exactly the defect
already recorded under *Known issues* for self-created workspaces at 1,000,000: an unpainted bar
on a product whose headline mechanic is the meter. **100,000** is the Phase 3 calibration
re-derived at the real cost — ~125 tasks of headroom, one task at 0.8%, so the bar visibly moves
across a short session. User's call, taken on the arithmetic above.

**The second door, which the PR did not close.** `rehearse.py` held `STANDARD_BUDGET = 5000` and
restores it in a `finally`, so every rehearsal reset the live board to the small budget anyway.
One constant was doing two jobs: what a take *runs on* and what the board is *left on*. Split
into `RECORDING_BUDGET = 5000` and `STANDARD_BUDGET = 100_000`, which is now the normal restore
path rather than only the `--ceiling` cleanup.

**What changed:** `scripts/reset-demo.sh` (default 100,000; the comment block that argued for
5,000 rewritten, since it had been left standing and arguing against the PR's own value; stale
`TOKEN_BUDGET=60` in the header corrected to 1600) · `scripts/rehearse.py` (constant split) ·
`DEMO.md` (a take now asks for `TOKEN_BUDGET=5000` explicitly — the bare command is the live
board, not the recording board).

**Verified:** `bash -n` and `ast.parse` clean on both scripts; both constants traced to their use
sites; no harness asserts on an absolute budget — every check is relational (`>=`, identical
across screens, the 100% clamp), so `ws_smoke.py` and `rehearse.py` are unaffected by the value.
**Not re-run against AWS:** no backend file changed, and re-running `rehearse.py` would spend
real tokens on the live board for a change to two operator scripts and a run sheet.

**The general shape, worth keeping:** a constant calibrated against a measured cost is only
correct until that cost moves. This one was derived from a stub, survived the stub's removal, and
stayed wrong for four phases because nothing asserts on it — the harnesses all check
*relationships* between numbers, which is what let the absolute value rot unnoticed.

**Phase 22 — Alien Colony — 2026-09-20 — deployed and verified**

The third world, and the one the plan singled out to restyle the handoff. The office becomes an
off-world colony: command modules on landing pads, purple-teal regolith under two moons and a
ringed planet, and a message crossing the floor as a transmission rather than as an object.

**Built out of order, on the user's instruction** — the remaining worlds (20, 21, 23–26) and 27
are **not cut**, only deferred past submission. Phases 19–26 depend on 18 and on nothing else, so
taking 22 next is exactly the reshuffle `BUILD_PLAN.md` says is allowed.

**What landed.** `frontend/src/worlds/alien.css` (new, 42 scoped rules), a registry entry plus two
casts in `worlds.js`, one import line in `main.jsx` — and, unplanned, two rules in `styles.css`;
see finding 1 below.

**The first world whose agents are a different species.** Phase 18 built `agentDesigns` and
nothing had used it. Here the people are colonists — wide domed cranium over a narrow torso,
which is the opposite proportion to an office worker — and the agents are service robots with a
sensor band instead of a face and manipulator arms where a colonist has hands. An agent at a desk
is now *visibly* not one of the people watching it.

**The state expression whose form changed.** Paper Office announces a working room by tinting its
floor. A module announces it by **lighting its antenna array** — the mast and both dishes on the
roof come up cool, visible over the hull from anywhere on the floor, and the deck takes the wash.
Same `--cool` token, same label text, a different object doing the announcing.

**The handoff, restyled.** The envelope becomes a pulse: a near-white core inside a violet aura,
trailing a streak, inside a ring that expands in step with the crossing. Pale rather than teal on
purpose — a teal pulse would be the busy hue detaching from a desk and flying across the room.
Path, duration and accessible label untouched.

**Verified, not assumed:**

| Check | Result |
|---|---|
| `npm run build` | clean; `./scripts/deploy-frontend.sh` job **31 → SUCCEED** |
| Real task in Alien Colony on the **deployed** board | **648 tokens**; array lit, readout up, `--cool` border, `Ada`/`working`/`for judge` unchanged |
| **Real agent-to-agent handoff, deployed, at 960** | Ada → Pam, **1,202 tokens**; label `"Ada passed this task to Pam."`, `role="status"`, `aria-live="polite"` — all untouched |
| **The same handoff at 540** | second live handoff, same label, no overflow; pulse legible against the regolith |
| **Whole flow walked in this world, deployed** | hired Zed and Nox to fill the floor, then drove **six identities across six browser contexts**: **4/4 desks lit at once** (both modules *and* both open desks), and a real queue formed with `queued #1` in `--honey` `rgb(255,158,92)`, the queued colonist standing on a landing-strip marker |
| **`ENVELOPE_MS` contract** | computed `transition-duration: 1.1s, 1.1s`; ring animation `alien-pulse` also 1.1s |
| **Paper Office unchanged** | **73/73 custom properties and 211/211 computed-style records identical** to a HEAD build served side by side. Zero diffs |
| Every world rule scoped | 42/42 carry `:root[data-world='alien']`; 0 unscoped |
| Layout parity between worlds | floor box **516×260** and `scrollWidth` **540** identical in both, switching live |
| Contrast, measured | `--cool` 7.15 · `--safe` 6.24 · `--honey` 6.18 · `--alarm` 5.37 — worst case each, across all eight surfaces; `--screen-on` 8.52 as an indicator. All clear 4.5:1 |
| Hue separation | honey↔amber **16.5°**, honey↔alarm 19.3°, **cool↔safe 46.5°**, ambient violet 82–137° from every state hue |
| Cold load, no CSS | Alien Colony's first frame is **dark** (`#120b1f`), Night Watch's dark, Paper Office's light. No flash; no `index.html` change needed |
| `prefers-reduced-motion: reduce` | all three of this world's animations resolve to `none`; envelope transition to `0s` |
| Responsive sweep | 1440 / 1100 / 900 / 540 / 390 — zero horizontal overflow |
| Console, deployed | **zero errors, zero warnings** |
| Colour literals outside the token block | **zero** (all 50 inside `:root[data-world='alien']`) |
| `pytest` | **27/27** |
| `ws_smoke.py` | **109/113** — the four documented CONN# false positives, and this run proves *why* they are false positives (below) |
| `rehearse.py` | **15/15**, one clean unattended take, **15.3s** of product time against a 110s allowance — the recorded sequence is unregressed |
| Cold visitor on the deployed URL | landing page renders Paper Office (`#fff8e7`, `light`) with its preview floor; **zero console errors**; picker offers all three worlds with Paper Office selected |

**One defect found and fixed, and it was not this world's.** Hovering the *selected* card in the
world picker replaced its amber fill with the page ground while keeping near-black text —
`.worldcard:hover` is (0,2,0) and `.worldcard--on` is (0,1,0). On cream that is 17.25:1 and
invisible as a bug. Measured on dark: **1.00:1 in Night Watch, 1.02:1 in Alien Colony** — the name
of the world you are in disappears the moment you point at it, which is the normal way to look at
it, not an edge case. Phase 19 shipped this. Fixed in `styles.css`; after the fix all three worlds
read 6.74–8.72:1 hovered and 8.30–12.02:1 at rest. **This is the only change in the phase not
scoped to the world**, and it does alter Paper Office's chrome — the selected card deepens on
hover instead of going cream. Not on the floor, not in any recorded frame.

**Four findings recorded in `BUILD_PLAN.md` under Phase 22**, three of which belong to worlds
23–26: the world-card hover defect above; a world may not put a celestial object on
`.fixture--daylight`, because that fixture is mid-floor (23 and 25 have the same problem in their
briefs); "ambient warmth decorates" is a rule about confusability rather than temperature, and a
violet ambient satisfies it better than a forced warm one; and `--tile` means "the other ground
colour", not "lighter than the floor".

**A correction to Phase 19's correction: `ws_smoke.py` scored 109/113 with no browser attached at
all.** Phase 19 recorded that the four CONN# failures are "the developer's own browser tabs —
close them and all 113 pass". That is one cause, and it is too strong as a rule. This run was made
with every tab closed, and it still scored 109/113. Scanning `hiveos-state` for `CONN#` rows
immediately afterwards found exactly two, both on `TEAM#alpha`, belonging to **`divyansh`
(14:40:58Z) and `dana` (15:09:08Z)** — real visitors on the public URL, which is what the original
Phase 17 diagnosis said.

> **The invariant is what matters, and this run is the cleanest evidence of it yet.** Across a
> whole session of opening and closing connections on `TEAM#qaverify` and `TEAM#alienlab`, the
> scan afterwards showed **zero `CONN#` rows for either team** — every connection this session
> opened was gone, while the two strangers' rows remained. That is precisely the property the four
> checks are trying to assert; they fail only because they assert the table is *globally* empty,
> which a live public URL makes untrue for reasons that are not a defect.
>
> **So: 113/113 is reachable but not guaranteed, because it depends on nobody else being on the
> public URL.** Do not quote 113/113 as the expected score. Quote 109/113 and check the `CONN#`
> rows — `aws dynamodb scan --table-name hiveos-state --filter-expression "begins_with(SK, :c)"
> --expression-attribute-values '{":c":{"S":"CONN#"}}'` — to confirm none of them are yours.

---

**Phase 19 — Night Watch — 2026-09-20 — deployed and verified**

The first world, and what turns a one-entry picker into a control. The office becomes a night
observation deck: the floor under a star field, quiet, lit by instruments rather than by daylight.

**What landed.** `frontend/src/worlds/nightsky.css` (new), a registry entry and a five-design cast
in `worlds.js`, one import line in `main.jsx` — and, unplanned, a change to `index.html`; see
finding 1 below. The stylesheet is a token block that repaints every surface in the product
including the chrome and the landing page, plus 41 scoped rules that re-dress the objects:
sky-and-deck-grid ground plane, glass-roofed bays with the walls dropped to railings, telescope
consoles, a star chart, a signal beacon, an open sky, a moon-pool, antenna masts, a moonlit
platform reached along a lit path, two constellations, and drifting motes.

**The state expression whose form changed.** Paper Office announces a working room by tinting its
floor. A bay announces it by **lighting its dome** — a pool of cool-white falling from the roof.
Same `--cool` family, same label text, different shape of light.

**Verified, not assumed:**

| Check | Result |
|---|---|
| `npm run build` | clean; `./scripts/deploy-frontend.sh` job **30 → SUCCEED** |
| Real task in Night Watch on the **deployed** board | **494 tokens**, bay lit, `for judge` / `working` read correctly |
| Two bays, queue and handoff on the deployed floor | pale envelope legible on navy; `queued #1` in honey orange on the lit path |
| **Paper Office unchanged** | **73 custom properties and 89 computed-style records identical** before/after; only diff was `.sprite` `transform: matrix(1,0,0,1,0,0)` vs `none` — the same identity transform caught mid-animation |
| Every rule scoped | 41/41 carry `:root[data-world='nightsky']`; Paper Office cannot change by construction |
| Layout parity | `scrollHeight`, `scrollWidth` and floor box **byte-identical** between the two worlds at 540 |
| Contrast, measured | `--cool` 6.36 · `--safe` 6.03 · `--honey` 6.56 · `--alarm` 4.56 — worst case each, across all eight surfaces; `--screen-on` 7.63 as an indicator. All clear 4.5:1 |
| Cold load, no CSS **and** no JS | Night Watch's first frame is **dark**, Paper Office's is light. No cream flash |
| `prefers-reduced-motion: reduce` | both drift animations resolve to `none` |
| Responsive sweep | 1440 / 1100 / 900 / 540 / 390 — zero horizontal overflow, workspace and landing page |
| Console | **zero errors, zero warnings** |
| `pytest` | **27/27** |
| `ws_smoke.py` | **113/113** — see the correction below |
| Colour literals outside the token block | **zero** |

**Two corrections to things this file previously recorded as true:**

1. **`ws_smoke.py` scores 113/113, not 109/113.** The four "known stranger-connection false
   positives" carried in this file since Phase 17 were never a backend defect: they were *the
   developer's own browser tabs*, each holding a live `CONN#` row against the deployed backend.
   Run the suite with a browser attached and five checks fail; close the browser and all 113 pass.
   **Close every tab on the deployed URL before running `ws_smoke.py`.**

   > **Overstated, and corrected at Phase 22 — see that entry above.** Your own tabs are *one*
   > cause, not the only one. A Phase 22 run with every tab closed still scored **109/113**, and a
   > `CONN#` scan immediately afterwards found two live rows belonging to real visitors
   > (`divyansh`, `dana`) on the public URL. Closing your tabs is still the right first step; it
   > just does not guarantee 113. Check the rows rather than assuming the cause.
2. **The ≥4.5:1 contrast bar in `BUILD_PLAN.md` is not met by Paper Office.** Its state hues run
   **2.63:1 to 5.26:1** against their own surfaces — `--honey` on a busy room floor is 2.98:1.
   Night Watch clears the bar on all eight of its surfaces. The bar stands as written and Paper
   Office is *not* being retuned: it is pixel-frozen for the recording, and changing it now would
   invalidate a rehearsed demo to chase a number no judge will measure.

**Four findings that belong to worlds 20-26, not to this one.** Recorded in full in
`BUILD_PLAN.md` under Phase 19: a dark world needs the `hiveos.world.paint` pre-paint key (done
once, in `index.html` — 20-26 inherit it and stay two files); `--ink` inverts but its three
*dark*-meaning uses do not, so `.modal`, `.drawer` and `.desk__chair` need re-pointing in every
dark world; `--paper` is both a panel surface and a sheet of paper, so "handoff unchanged"
requires an active override; and on a dark ground `--honey` has to separate from the brand amber
by **hue** rather than by value, because value is not available.

---

**Phase 18 — world system foundation — 2026-09-20 — deployed and verified**

The seam every world phase from 19 on plugs into. Frontend only; no backend, protocol, schema or
`CONTRACT.md` change, and no new dependency. Three commits: `0b6aaee` (slice 1), `3501633`
(slices 2–3), and the app-bar fix below.

**The mechanism.** `data-world` on `document.documentElement`. Bare `:root` is Paper Office; a
world adds `:root[data-world="<id>"]` in its own file under `frontend/src/worlds/`, imported from
`main.jsx`. It outranks the default on *specificity* rather than load order, so nothing needs
`!important` and no import has to be ordered. An id matching no file renders as Paper Office —
which is why an unknown stored value is harmless rather than a blank board.

**What landed:** `worlds.js` (registry + `WorldProvider` + `useWorld`, one entry); the sprite
layer alphabet widened 3→5 and made per-world, with the generator, `SCALE` and the 9×10 grid
untouched; `lookFor` taking the world as a third argument at all six call sites and a fourth for
worlds whose agents are a different species; `walkTop` moved into the registry, which stamps
`--walk-top` for CSS and hands the same number to the walk math; a pre-paint script in
`index.html`; three empty `.worldlayer` slots in the floor; and a title-bar picker everyone gets.
38 colour literals became tokens — **zero remain outside `:root`** — including eleven channel
tokens for the alphas a hex cannot express. The dead `.hotdesk` rules, orphaned since Phase 17,
are gone.

**Verified, not assumed:**

| Check | Result |
|---|---|
| Paper Office unchanged, 540 and 960 | **byte-identical** full-page screenshots vs the pre-phase build |
| Computed style of every element (slice 1) | **0 of 226 differ** |
| Scratch world repaints everything | every world *and* chrome surface moved; state words unchanged |
| `--walk-top` drives both halves | registry 22 → CSS `100% 22%` **and** the walk math together |
| Picker persists across a reload | yes, with no pre-paint flash |
| Unknown `hiveos.world` value | falls back to Paper Office, board fully rendered |
| `pytest` / `ws_smoke.py` | 27/27 · 109/113 — **unchanged**, same four known false positives |
| Deployed task on the real board | Ada replied, **494 tokens**, meter and ledger updated |
| Responsive 1440/1100/960/900/540/390 | no horizontal overflow, zero console errors |

**Two things did not go to plan, and both are recorded rather than smoothed over.**

**1. The daylight cone is scaled off `--tile-size`, not converted to percentages.** The brief
asked for percentages. That is arithmetically impossible while keeping Paper Office
pixel-identical: the workspace floor runs at `--tile-size: 44px` at the 540 framing and **52px**
at 960, so any floor-relative percentage differs at one of them. `--tile-size` is the floor's own
scale knob, is 44 at *both* narrow framings and 60 in the wide layout, so the cone is exact where
it is measured and finally grows with the room where it was frozen. Written as
`calc(var(--tile-size) * 190 / 44)`: CSS divides a length by a number but **not by another
length**, so the intuitive ratio token yields `1px`, `190px * 1px` is invalid, and the cone
computes to 0×0 — caught by the computed-style diff, which is the only reason it was not shipped.

> **The one place Paper Office is not byte-identical.** At the **960** framing the cone is now
> 224×177 rather than a frozen 190×150. Measured: **1.46% of the floor's pixels differ, worst
> channel delta 7/255** on a 0.34-alpha decorative gradient that reports nothing. At 540 it is
> unchanged. This is a deliberate call — the fix is what the phase asked for and the element is
> explicitly decoration — but it *is* a deviation from the pixel-identical non-negotiable, and it
> is one line to revert in `styles.css` if the recording should be bit-for-bit with Phase 17.

**2. The world button caused a real regression at 390px, found and fixed.** The title bar is a
fixed-size flex row with no graceful floor; a second button put an administrator's row 32px past
a 390px phone — a horizontal scrollbar on the whole page. Fixed by hiding `.appbar__name` below
**520px** — the wordmark is the one genuinely redundant item, sitting beside the mark that says
the same thing. **520, not 560: the demo records at 540 and the breakpoint must not reach it.**
A first attempt used 560 and would have quietly rewritten a demo framing.

---

**Full-system QA pass — 2026-09-20 — everything exercised against the deployed URL**

The whole product was driven end to end against `https://main.dbavt8jr66qxx.amplifyapp.com`
with three simultaneous browser identities and the two harnesses, rather than read.

Gates, before the fixes and again after them:

| Gate | Before | After the fixes |
|---|---|---|
| `pytest tests/` | 22/22 | **27/27** — 5 new, in `tests/test_state_bootstrap.py` |
| `scripts/ws_smoke.py` | 110/112 | **109/113** — 1 new check, in section 26 |
| `scripts/rehearse.py` | 15/15 | **15/15 ×2 takes**, 14.1s of product time against a 110s allowance |

**Every `ws_smoke` failure across all runs is the documented CONN#-leak false positive** — a
real visitor, `dana`, sat on the public URL's default workspace throughout. One run caught two
rather than four only because it overlapped less of their session. That was verified rather
than assumed, two ways: the row carried a live `connected_at` and a connection id that changed
between runs, and the invariant itself was then checked the way this file's standing note
prescribes — open two connections, close them, confirm *our* `CONN#` rows **and their
`CONN#/TEAM` index rows** are gone while the stranger's remain. Both were. No connection leaks.

> **Updated at Phase 19: the suite does reach 113/113, and this note should not be read as
> "109 is the ceiling".** The diagnosis above is right about the cause and wrong about the
> remedy — the other connection does not have to be a stranger, and usually is not. Any tab the
> developer has open on the deployed URL holds its own `CONN#` row and trips the same five
> checks. Close every one of them, wait a few seconds, and all 113 pass. Do that before quoting
> a score.

**`ws_smoke.py` gained the check that would have caught defect 1** (section 26): a dismissal is
still true for the *next* person to connect. The rest of that section asserted the floor from
the connection that did the dismissing, which is why 110 deployed checks passed over the bug.

**What was confirmed working, on the deployed build, by watching it happen:** the landing page
cold; the entry gate and self-bootstrapping workspaces; a real model round trip with
provider-reported tokens into the meter, the stream and the ledger; three identities with
per-connection membership deduped to one marker per person; hiring, broadcast to every floor
with no refresh; dismissal; the queue and auto-dispatch onto a freed desk; shared memory
crossing between users; the admin panel; and **the agent-to-agent handoff, which `PROGRESS.md`
still called an unrehearsed beat** — Ada judged a literature review to be Iris's, the envelope
crossed, and the ledger recorded one `task_id` across two desks at 1,197 + 936 tokens.

The ceiling was tested the way it actually matters — by bypassing the UI. With the send button
disabled and the banner up, a raw `claim_agent` frame over the socket was refused with
`budget_exhausted` and **`tokens_used` did not move by one**. The control is real.

**Four defects found and fixed. Three were invisible to every existing test**, because all
three harnesses build state up and never take it away:

1. **A dismissed starting desk came back on the next `$connect`** (`state.ensure_team`).
   `ensure_team` runs on every connection and re-wrote Ada and Iris conditionally on the row
   being absent — which is exactly what `dismiss_agent` leaves behind. So dismissing Iris held
   only until the next person joined, or until your own socket reconnected after a blip, and
   the desk returned with no `agent_spawned` frame, nothing in the activity log and no way to
   tell from the board that anything had happened. Reproduced on the deployed stack
   (`resurrect1`), fixed, re-verified (`resurrect2`). The roster is now seeded only on the
   branch where the `METADATA` write actually succeeded, plus a repair clause for a floor with
   zero desks — unreachable through the product, but permanently dead if it ever happened.
   Five regression tests in `tests/test_state_bootstrap.py`; two of them fail on the old code.
2. **Raising the budget did not unblock the board** (`useHive.js`). `budget_exhausted` latches
   the client, and only `state_snapshot` cleared it. `admin_set_budget` broadcasts
   `token_update`, which is deliberately *not* in `RESYNC_EVENTS`, so nothing pulled a
   snapshot: the meter fell to 14.2% while the red "Quota reached" banner stayed up and the
   send button stayed disabled, with no way out but a reload. The admin's one lever for the
   ceiling appeared not to work. `token_update` now recomputes the flag — it carries used and
   budget together, which is the whole question.
3. **Any frame whose `action` was not a string answered `"internal error"`** and logged a stack
   trace (`router/app.py`). `action.startswith("admin_")` was the first thing to touch it.
   Now answered `"frame must carry a string action"`; the socket was never at risk either way.
4. **Two hires in the same second could reorder the floor** (`state.hire_agent`). `created_at`
   was second-granularity, so a tie fell through to the `slot_id` tiebreak, which is slugged
   from the name — the desks would come back alphabetical. `now_iso_micros()`, the same fix
   `QUEUE#` sort keys already carry.

**The general shape of (1), worth keeping:** a bootstrap that runs on every request is an
idempotent *write*, and an idempotent write is an undo for anything that legitimately deletes
what it writes. Anything self-healing needs to ask whether the state it restores was lost or
given up.

**One thing deliberately not changed, and it needs a decision — see *Manual actions pending*.**
`DEFAULT_TEAM_BUDGET` is 1,000,000, so a judge who types their own workspace name gets a meter
that does not visibly move: a 666-token task is 0.1% and paints no bar at all. The recording
path is unaffected — `reset-demo.sh` seeds `alpha` at 5,000 and `DEMO.md` records there — so
this is about the judge who explores rather than the video. At 8,000 the same board reads
81.2% in vivid red and the mechanic is unmistakable. Changing it is a one-line
`parameter_overrides` edit plus a redeploy, but it is a spend-policy call, so it is the user's.

**Documentation pass — 2026-09-19 — the judge-facing files catch up with the office**

The Phase 17 doc commit (`aaced4e`) updated `CLAUDE.md`, `CONTRACT.md`, `DEMO.md` and `PRD.md`
and **skipped the two files a judge actually opens**: `README.md` and `SUBMISSION.md` both still
led with *"The OS scheduler for your team's shared AI budget"*, described "two named agents" as
a fixed roster, and never mentioned hiring. `ARCHITECTURE.md` had not been touched since
2026-09-18 and so recorded neither Phase 16 nor Phase 17.

**What was wrong, and is now corrected:**

- **`README.md`** — rewritten around the office. Its screenshot, `docs/hud.png`, was the
  single-column pre-pivot HUD showing "AGENT SLOTS", `coder`/`researcher` and the line *"the
  agent is stubbed"*, which has been false since Phase 3 closed. Replaced with three captures
  of the deployed build: `docs/office.png`, `docs/working.png`, `docs/hire.png`. Stale counts
  fixed (`94/98` → `108/112`, `12/12` → `15/15`, "79 checks" removed); repo layout updated for
  `addagent.jsx`, `landing.jsx`, `sprites.js` and `tests/`.
- **`SUBMISSION.md`** — pitch, feature list and three stale numbers (`85/85`, `12/12`,
  "49 checks"). Its "What I learned" section was accurate and was left alone.
- **`ARCHITECTURE.md`** — decisions **11** (the roster is per-workspace data, `MAX_AGENTS`,
  no migration, hiring open to any member, the engine step as a readout) and **12** (handoff
  bounded to one hop, guarded by tool availability) added. Data-flow diagrams for hiring and
  handoff added. Decision 8 had said *"the HUD is the product; the canvas is the wrapper"* —
  the pivot inverted exactly that, so it now records the inversion **and** why a game engine is
  still rejected even though the floor became load-bearing.
- **`BUILD_PLAN.md`** — Phase 17 was missing entirely; the plan stopped at Phase 16.
- **`DEPLOYMENT.md`** — **two different sections were both numbered `MANUAL ACTION 2b`**, and a
  cross-reference pointed at the ambiguous pair. The key-provisioning one is now `2c`. One
  remaining `python scripts/…` fixed to `python3`.

**Two things found by running rather than reading:**

1. **The unit tests do not run on this machine.** `PROGRESS.md` claims 14/14, and that is true —
   but only with `boto3` installed, and system Python 3.14 here has no `botocore`, so collection
   fails before a single test executes. Verified in a throwaway venv: **14 passed**. The claim
   was right and the instructions were incomplete; `README.md` and `SUBMISSION.md` now give the
   venv line. **Anything asserting "the tests pass" must say what they need to pass.**
2. **The entry gate still described the old product.** `App.jsx` told every arriving visitor
   *"A workspace shares two agent slots and one token budget"* — the pre-pivot sentence, on the
   first screen of the deployed app, contradicting the floor behind it. Also *"their own budget,
   slots, queue and memory"*. Both corrected, rebuilt, deployed as Amplify **job 26**, and
   verified live by reading the strings back out of the deployed DOM. Product copy is
   documentation that ships; the doc sweep did not look at it, and it was the most-read sentence
   of all of them.

**Verified:** `vite build` clean · Amplify job 26 `SUCCEED` · both gate strings read back from
the deployed page · console **0 errors, 0 warnings** · unit tests **14/14** in a venv · a real
task end to end on the deployed URL (1,234 provider-reported tokens, memory fact saved, desk
lit and released) — which is also where `docs/office.png` and `docs/working.png` come from.

**Not re-run:** `ws_smoke.py` and `rehearse.py`. No backend file changed, and the frontend change
was two sentences of copy in the entry gate — neither script asserts on that text. The `108/112`
and `15/15` figures quoted above are the last recorded runs, not new ones.

**`p17live` now holds Jim and ~1,234 spent tokens** from the screenshot session. Inert, like the
other test partitions — Phase 9 partitions every row by team, so `alpha` and `p6stage` cannot
see it.

---

**Phase 6 tasks 4–5 — 2026-09-19 — the run sheet catches up with the office**

Phase 17 changed what is on screen and left `DEMO.md` describing a board that no longer
exists. Its own warning boxes said so: *"No pixel figure below has been re-verified"* and
*"`rehearse.py` does not cover hiring"*. Both are now closed by measurement. **No product
code changed** — this is the harness and the run sheet only.

**Five defects in the run sheet, each found by running it rather than reading it:**

1. **Every command in `DEMO.md` was unrunnable.** They all said `python scripts/…`; this
   machine has no `python` on `PATH` and exits `command not found`. The first thing the
   operator would have typed on recording night. Now `python3` throughout.
2. **`~900×760` for the secondary window sat one pixel from a cliff.** The shell stacks at
   `max-width: 899px`: at **900** it is the landscape office and the page does not scroll,
   at **899** it is a single column **1164 px** tall and it does. A size written as
   "about 900" is a coin flip on camera.
3. **The framing it prescribed was arithmetically impossible on this machine.** Two windows
   at ≥900 need 1800 px; the logical desktop here is **1512×982**. "Side by side — do not
   overlap them" could never have been followed. Replaced with a measured configuration
   that fits: office **960** + witness **540** = 1500, both screenshotted, or three
   **504**-wide windows = 1512 if all three must be visible.
4. **It called charlie optional.** *"A third, charlie 🦉, only if you are demonstrating the
   queue with every desk busy"* — which is the 0:40–1:25 beat, the centrepiece. With the
   two-desk roster alice and bob fill both desks and **charlie is the queue**. Three
   identities are mandatory even though two windows are on camera.
5. **The narration still counted three screens** throughout, after the framing box above it
   had already cut to two.

**The claim that anything under 900 px is "the mobile layout, not the product" is wrong,
and it was the expensive part.** The narrow column is a real responsive layout of the same
live board — at 540×870 the whole floor, both rooms, the waiting area, the nameplates, the
meter and the chat input all sit above the fold with no horizontal overflow. Believing it
was a degraded view is what left the framing with no option that fits the screen.

**`rehearse.py` covers hiring now — as Beat 5, and the position is load-bearing.** The
queue only forms when every desk is busy, so a third desk hired before Beat 2 means alice
and bob fill two of three, charlie is dispatched straight into the spare, and the queue
position, the walk into the waiting area and the auto-dispatch all silently do not happen
— with nothing failing to warn you. On camera that is a take that looks fine and proves
nothing. Both the harness comment and `DEMO.md` record the ordering and why.

| Check | Result |
|---|---|
| `rehearse.py --takes 2`, before the change | ✅ 12/12 twice, `REAL` provider usage |
| `rehearse.py --takes 2`, with Beat 5 | ✅ **15/15**, run twice (four takes), 91–95 s of headroom |
| A hire reaches a bystander's screen | ✅ **305–433 ms**, carrying name, role, character, project |
| A browser opening cold after the hire | ✅ same three desks, roster order, hire last |
| Take 2 cleaned up take 1's hire | ✅ `seed.sh` deletes non-starting `AGENT#` rows, so the beat is self-cleaning |
| Deployed shell at 1440×900 | ✅ lays out to exactly 900 (44 + 777 + 79), no overflow either axis |
| Deployed shell at 960×870 and 540×870 | ✅ both read; console **0 errors, 0 warnings** |
| Stack state | ✅ `hiveos` `UPDATE_COMPLETE`, unchanged — nothing was deployed |

Rehearsed in a private workspace (`DEMO_TEAM=p6stage`) rather than the default, which is
what `DEMO.md` already prescribes and what keeps live visitors out of the assertions. That
partition joins the inert test partitions already in the table.

---

**Phase 17 — 2026-09-19 — the office**

User decision, and a deliberate pivot rather than a feature: *"I think our
project is drifting drastically from Munder Difflin… I think we need a big
decision/goal/workflow change."* The product was **a team queues for two
shared agent slots**. It is now **a floor you staff** — agents are hired,
named, briefed and given a character, and they sit at desks people can watch.

**What was raised before building, because it is not negotiable.** Munder
Difflin spawns local PTY processes running your own Claude Code / Codex CLIs
against folders on your disk. That is a desktop app, and a Lambda behind a
public URL cannot attach to a judge's terminal. So this took the reference's
*interaction model* and never its mechanism — the inspector's four tabs are
bound to data this board actually holds, and there is no fake terminal
anywhere. The scheduler, the fair queue and the enforced ceiling did not go
anywhere; they stopped being the pitch and became the governance layer inside
the office, which is a better pitch and was ~80% already built.

Shipped as two slices, each deployed and verified before the next — the Phase
8 precedent, and the reason there was a submittable deliverable at every point.

**Slice 1 — the shell (`ff6a723`), frontend only.** The 760px panel column
became a three-region app: title bar, floor filling the left at full height,
one agent in depth on the right, every desk along the bottom. Zero backend
files, so `ws_smoke.py` and `rehearse.py` stayed valid without being re-run.

**Slice 2 — the roster is data (`edea677`, `77053e4`).** `agents.py` was the
roster: one tuple, fixed at deploy time, identical in every workspace. It is
an `AGENT#` row per agent now, carrying identity beside the `status` and
`current_user` it already held.

**Five decisions worth the space:**

1. **The chair belongs to the agent.** Before hireable agents, holding a slot
   and doing the work were the same thing, so the floor sat the *human* at the
   desk. Now the agent sits there and the person who asked stands beside it.
   That one swap is the product change made visible, and it kept the walk-in
   animation that is the best thing on the floor.
2. **No migration, and that is the design.** `ensure_team` writes slot rows
   conditionally, so every board created before today still has a bare
   `AGENT#coder` row. `agents.from_row` falls back field by field to
   `STARTING_ROSTER`, so all of them read as Ada and Iris with no backfill and
   no scan-and-update against a live table. `seed.sh` and `ws_smoke.py` now
   write those bare rows **on purpose**, so the compatibility path is
   exercised on every seed and every smoke run rather than assumed.
3. **Hiring is open to any member, not to the owner.** Hiring costs nothing;
   *running* an agent spends the budget, and the ceiling governs that
   identically however many desks share it. A permissions wall in front of the
   one interaction this product is now about would be governing the wrong
   thing.
4. **The ledger writes `agent_name` at run time.** With a fixed roster a late
   join was equivalent. With hiring it is not — a dismissed agent's rows would
   report a raw slot id, or be credited to whoever holds that id next. Proven
   rather than argued: `ws_smoke.py` dismisses Jim and then asserts his
   finished task is still his.
5. **The engine step is a readout, not a picker.** One model is configured per
   deployment. A per-agent model picker would let one hire quietly change what
   the team spends per call, which is the opposite of what this product is
   for. It says which model runs and why it is not a choice.

**`MAX_AGENTS` is 4, and the number was measured rather than chosen.** The plan
was six. The floor's lower band is 38% tall with the waiting-area rug across
the middle, so the only free places are the left and right margins; two rows
per side does not fit, and it failed *on screen* — row one's character lands on
row two's nameplate and row two's character falls off the bottom edge.
Shrinking further makes a nameplate unreadable at recording size. A cap above
what the floor can draw would let someone hire an agent the roster strip lists
and the room cannot show.

**Four defects found by looking rather than by reading:**

1. **A visitor's sprite painted over the agent's speech bubble**, which read as
   truncated text. Found on the landing preview, where the room is small enough
   that it covered four characters. The bubble now lifts above every pawn and
   caps at 18ch.
2. **`Workspace` returned `<Deleted />` before a `useMemo`** — a latent
   rules-of-hooks violation that would have thrown on the exact frame it was
   meant to handle gracefully. Pre-existing; fixed while restructuring.
3. **`--px-n` was inert on `.agentface`.** The scale transform that makes the
   baked 4px art grow lives on `.sprite::before`, and the portrait rule never
   got it — so the character picker asked for 6px and silently kept rendering
   at 4, showing eight near-identical shapes with none of the three
   silhouettes the art actually has.
4. **Two identical roster queries on the hottest path.** `_claim_agent` read
   the roster and then `claim_any` read it again. Caught by the unit tests
   rather than by review. `claim_any` now takes the list the caller already
   has, and `_release_agent` answers "does this desk exist" and "who holds it"
   from one `GetItem` — strictly less I/O than before this phase.

**Verified against deployed AWS, not exit codes:**

| Check | Result |
|---|---|
| `sam build --use-container` + `sam deploy` | ✅ `UPDATE_COMPLETE`, twice |
| `vite build` + Amplify | ✅ jobs 22 and 24 `SUCCEED` |
| `ws_smoke.py` | ✅ **108/112** — 14 new hiring checks, all passing. The 4 failures are the documented live-visitor case |
| `rehearse.py --takes 1` | ✅ **12/12**, 97s of headroom |
| Unit tests | ✅ 14/14 |
| AST undefined-name pass over all 10 backend modules | ✅ 0 problems |
| **Hiring is live for everyone** | ✅ on the deployed URL: bob hired Dwight from a separate socket; alice's browser, never reloaded, drew him seated at an open desk, added his roster card and moved the app bar to `0/3 working` |
| A hired agent runs a real task, credited by name | ✅ 622 real tokens, ledger row `agent_name=Jim` |
| A dismissed agent's past work stays attributed | ✅ asserted after the dismissal |
| A floor cannot be emptied of every agent | ✅ refused |
| Phase 16 handoff still crosses | ✅ chain 1,952 tokens across two desks |
| `seed.sh` | ✅ dismissed a hired desk and restored the starting roster |
| `reset-demo.sh` | ✅ `snapshot clean — 2 desks IDLE (Ada, Iris)` — which also proves the bare-row fallback |
| Console on the deployed page | ✅ zero errors, zero warnings |
| Horizontal overflow at 1440 / 1100 / 900 / 390 | ✅ none |

**The demo framing is dead and `DEMO.md` says so at the top.** Three 640×950
portrait windows were carefully earned over Phases 7–15 and cannot hold a
landscape app shell — at 640px the shell renders its stacked mobile layout.
The replacement is one 1440×900 primary plus one ~900×760 secondary. **No
pixel figure in `DEMO.md`'s checklist has been re-measured against the new
shell**; that is the user's first job before a take.

**`rehearse.py` does not cover hiring.** It still drives the Phase 2–8
sequence and passes 12/12. `ws_smoke.py` section 26 covers hiring fully
against deployed AWS, so the mechanism is verified — what is unrehearsed is
the *timing* of doing it on camera.

**Test partitions left in the table**, alongside the existing ones:
`smokehiring` (the smoke test's own workspace, reset at both ends of its
section), `p17shell`, `p17hire`, `p17live` and `p17demo` from driving the real
UI against deployed AWS. All inert — Phase 9 partitions every row by team, so
`alpha` cannot see them.

**Phase 6's deferred tasks are unchanged and still the user's.** This phase
did not touch them.

---

**PR #1 — 2026-09-19 — the release path is now guarded (Phantom9869 / Kamal Choubey)**

First outside contribution. Two real defects on the release path, both
correctly identified, both merged with changes:

1. **`set_idle` wrote unconditionally.** SQS redelivers, so a task can
   finish and reach its release long after the desk was freed and
   handed to the next person in the queue. That write ended a
   stranger's task and then broadcast `IDLE` for a desk that was
   genuinely working — the board lying about the scheduler, in the one
   product that claims it cannot. Now conditional on `current_user`,
   like `try_claim` is conditional on `status`.
2. **`release_agent` authorised nothing.** Any connected client could
   send `{"action":"release_agent","agent_type":"coder"}` and cut short
   a teammate's task. The UI only ever drew the button for your own
   desk; there was simply no server-side half of that rule.

**What review changed, and why:**

- **The PR was cut before Phase 16.** It conflicted on the `scheduler`
  docstring and predated both `dispatch_next` and the handoff dispatch
  in the runner's `finally`. Merged onto current `main` with the
  handoff block intact.
- **Holder-only would have broken the escape hatch.** `release_agent`
  exists so a wedged desk can be freed from the UI. If a runner dies
  holding a desk and its owner closes the tab, holder-only means the
  desk is stuck for the rest of the demo — the hatch works only for
  people who do not need it. Admins may now free any desk, using the
  actual holder as the expected value, not themselves.
- **Holder-only also broke `ws_smoke.py` section 25.** That test frees
  an *already idle* desk to make the scheduler look at a pinned
  handoff again. The PR's check refused it, so the deployed gate for
  queued handoffs would have failed. An idle desk is now neither an
  error nor a release: it pokes `dispatch_next` and nothing else, which
  can only start work that is already queued at a desk that is already
  free.
- **Exceptions became a return value.** The PR raised
  `ConditionalCheckFailedException` out of `set_idle` and caught it in
  two callers, one of which imported `botocore` inside an `except`
  block. `set_idle` now returns a bool exactly like `try_claim` —
  claiming and releasing are two halves of one mechanism and should
  fail the same way. Both try/except blocks and the router's `botocore`
  import are gone. A non-conditional `ClientError` still raises;
  throttling must not be laundered into "somebody else holds it".
- **The router kept its DynamoDB access in `state.py`.** The PR read
  `state.table()` directly in two places; that is the only raw table
  access anywhere in `router/app.py`. Added `state.slot_holder`.
- **Authorisation reads the `CONN#` row, not `_user_for`.** `_user_for`
  falls back to `user_id` on the frame, which is fine for labelling a
  chat line and would have made the whole check decorative here.

**Tests.** `tests/` is new — the repo had no unit tests, only
`ws_smoke.py` against deployed AWS. 14 tests, `unittest.mock` only, no
moto and no AWS. Verified by mutation rather than by passing: removing
the `ConditionExpression` and the authorisation branch fails 3 of them.
`conftest.py` puts `backend/` on the path, which is the layout
`CodeUri: backend/` actually produces, rather than aliasing
`sys.modules` as the PR did.

**Not addressed, and deliberately.** SQS duplicate delivery still
double-charges the meter — the guard stops a redelivery from taking
someone else's desk, not from running. The author flagged it as
separate work and it is Post-Hackathon. **Closed on 2026-09-20 by
PR #4, from the same author — see below.**

---

**PR #3 — 2026-09-19 — dispatch recovers when the send to SQS fails
(Phantom9869 / Kamal Choubey)**

Second outside contribution, same author, and a real hole on the other
half of the scheduler. `take_next_task` deletes the `QUEUE#` row first
— that delete *is* the exactly-once gate, so it cannot come second —
and `dispatch` then hands the task to SQS. Between those two the task
exists nowhere but in memory and the desk is already claimed and
already announced `BUSY`. A failed send lost both: no DLQ message to
redrive (nothing ever reached the queue), and a desk sitting `BUSY`
with nothing in it until someone freed it by hand. `dispatch` is now
wrapped; the desk is released, the row restored at its original SK,
and the `BUSY` frame corrected.

**What review changed, and why:**

- **The `task_id` half was dropped.** The PR also changed `enqueue` to
  store `task_id or sk`, on the stated grounds that "`enqueue()` stored
  `task_id` as `None` for ordinary tasks". It does not —
  `router/app.py` mints one with `new_task_id()` before it ever calls
  `enqueue`, and `hand_off` carries the parent's through. The branch
  was unreachable, it fixed nothing about the dispatch failure (nothing
  dedupes or recovers on `task_id`), and where it *did* fire it would
  have written a `QUEUE#<ts>#<uuid>` string into the ledger column that
  otherwise holds 12-hex chain ids — two id formats in the one column
  the ledger joins a handoff's two rows on.
- **The `IDLE` broadcast is now conditional on the release.** The PR
  ignored `set_idle`'s return value and announced `IDLE` regardless.
  That is the exact defect PR #1 was merged to close, reintroduced two
  functions away: an `IDLE` frame must only ever follow a write that
  actually happened.
- **The desk is freed before the requeue, not after.** If the requeue
  also fails, one person has lost one task; a desk left `BUSY` with
  nothing running in it deadlocks the floor for everyone. Ordering the
  two writes by which failure is worse costs nothing.

**The reason this is worth more than the PR claimed.** `dispatch_next`
runs inside the Agent Runner's `finally`, and `lambda_handler` lets
exceptions propagate on purpose. So a failed send did not merely strand
a desk — it failed the invocation of a task that had **already
completed and already charged the team**, SQS redelivered it, and the
model ran a second time. A real second charge against the ceiling the
whole product is built around. The release half of that `finally` is
still deliberately unwrapped, for the opposite reason recorded there: a
leaked desk *is* worth a redelivery. A failed dispatch is not, because
this path frees the desk itself.

**Tests.** `tests/test_scheduler_dispatch_atomicity.py`, 8 tests, same
`unittest.mock`-only arrangement as PR #1. Rewritten from the PR's six,
which asserted by substring (`SLOT_ID in str(call)`) rather than on
arguments, and one of which only covered the dropped `task_id` change.
Verified by mutation: against the pre-fix `scheduler.py` the six
recovery tests fail and the two success-path tests pass. Suite is 22.

---

**PR #4 — 2026-09-20 — the runner charges for a task once
(Phantom9869 / Kamal Choubey)**

Third outside contribution, same author, and it closes the hole PR #1
recorded as deliberately left open: SQS is at-least-once, and a
redelivered task called the model again and charged the team twice for
one piece of work. The fix is an `IDEMPOTENCY#<task_id>` row written
with `attribute_not_exists(SK)` — whoever wins the put owns the task,
the same shape as the `QUEUE#` delete being the dispatch gate. The
mechanism was right as submitted. Where it sat was not.

**What review changed, and why:**

- **The gate moved inside the `try`.** This is the whole of the review.
  The PR ran it before the try/finally and returned on a duplicate — so
  a duplicate never reached the release. That inverts the runner's
  first invariant. The `finally` is deliberately unwrapped because a
  failed release leaks a desk and **an SQS redelivery is the only thing
  that can still free it** — the reasoning is in the code, and PR #3's
  record above restates it. A Lambda timeout, an OOM, or a throwing
  `release_and_dispatch` would have written the marker, kept the desk
  `BUSY`, and then had the one recovery path return early: the desk
  deadlocks forever and every task queued behind it stops. The PR
  traded a double charge for a dead workspace. Inside the try, both
  hold — a duplicate is not charged *and* still releases the desk.
- **A non-conditional `ClientError` is no longer raised out.** With the
  gate inside the try it is caught like any other mid-task failure:
  ledger row, error to the requester, desk freed. That matches the
  adjacent `_refuse_over_budget`, whose `budget_state` read has always
  been treated this way. What still must not happen — and is tested —
  is a throttle being read as "already ran", which would drop the task
  while looking like a successful skip.
- **The markers expire.** The PR's rows were permanent. Nothing reads
  them back, and `state_snapshot` queries the whole partition on every
  `hello`, so they were unbounded growth on a hot read. Added
  `state.ttl_after`, an `expires_at` a day out (the queue retains for
  one hour), and `TimeToLiveSpecification` on the table.
  **This is the one part that needs a deploy to take effect.**
- **`CONTRACT.md` gained the row.** A new SK prefix that is not in the
  schema authority is exactly the drift `CLAUDE.md` warns about.
- **An orphaned comment and a misplaced import.** The PR was cut from a
  base 19 commits behind `main` and re-added a `# The roster, read once
  for the whole task.` line that already exists, leaving it duplicated
  after the merge. `botocore` was imported between two stdlib imports.

**The tests did not run — they hung.** Written against that stale base,
they patch `shared.state.table` but not `shared.state.roster`, and
`_handle` has read the roster since Phase 17. `state.query_team`
paginates until `LastEvaluatedKey` is falsy and a bare `MagicMock`
returns a truthy one forever, so two of the five spun in an infinite
loop — CI would hang, not fail. Also: `_reply` was stubbed, which made
"a duplicate does not charge the team" vacuously true, since
`add_tokens` is only reachable through it.

**The bug the deploy gate caught — and the unit tests did not.**
Keying the marker on `task_id` was wrong, and it was wrong in the PR
as submitted, not in the review. `task_id` identifies the *chain*, not
the delivery — `scheduler.dispatch` says so in its own docstring — and
both legs of a handoff carry one `task_id` deliberately, because that
is what ties them together in the ledger and on `agent_response`. So
the receiving leg collided with the handing leg's marker: Iris claimed
the desk, skipped her model call, and went IDLE again without ever
answering. On the board that is a desk flickering BUSY and going quiet.

`ws_smoke.py` scenario 24 caught it on the first deploy — **83/88,
`alice: timed out waiting for 'agent_response'`** — which is exactly
why `CLAUDE.md` says a zero exit code is not proof. Every unit test
passed, the PR's five and my eleven alike, because none of them ran two
legs of one chain against one table.

Fixed by keying on the leg: `IDEMPOTENCY#<taskId>#<hops>`. A redelivery
repeats `hops`; a handoff increments it. Redeployed, and `ws_smoke.py`
is back to **109/113** with only the four known CONN# false positives.
Verified in the table itself — a handoff chain now holds `…#0` at
`coder` and `…#1` at `researcher`. Four un-suffixed rows from the first
deploy remain; they carry `expires_at`, cannot collide with the new
key, and TTL will sweep them.

**Tests.** `tests/test_runner_idempotency.py`, 14 tests, rewritten.
`_reply` runs for real against stubbed dependencies, and there is a
positive control asserting a *first* delivery does charge — without it
the duplicate assertions prove nothing. The handoff tests drive two
deliveries through **one table stand-in that actually enforces
`attribute_not_exists(SK)`**; a bare `MagicMock` accepts every put, so
asserting on a single leg in isolation can never see two legs claiming
one marker. That was the hole the deployed bug walked through.

Verified by mutation: hoisting the gate back out of the try fails 2,
re-keying on `task_id` alone fails 3, dropping the
`ConditionExpression` fails 1, dropping `expires_at` fails 1. Suite is
**42**, and runs in 0.11s.

---

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
- `SUBMISSION.md` — the writeup (`BUILD_PLAN.md` task 8). *The video link was left blank here
  and was filled in on 2026-09-20, along with a timestamp map of the finished cut.*

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

**Left to the user at the time this phase was written:** recording the take, uploading to
YouTube and verifying it signed-out, and submitting.

> **All three are now done, and Phase 6 is `COMPLETE`.** The take was recorded and uploaded at
> <https://www.youtube.com/watch?v=VBSuDCQa4y4> on 2026-09-20 and the signed-out check passed;
> **the submission went in and was confirmed by the user on 2026-09-21.** Nothing from this
> phase is outstanding.

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

> **Carried. 2026-09-20, scene s13 at 2:20** — *"Bedrock is blocked account-wide on this
> account, so inference is a single outbound call to Groq. Everything else is AWS."* Said
> plainly, in the recorded take, ahead of the closing line rather than buried.

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

**Nothing stands between the repo and the submission any more — it is in.** Everything buildable
is done, deployed and rehearsed; the video is recorded, uploaded and verified; the deliverable was
submitted. Items 1–3 below are kept as the closed record of how that happened, **not as a to-do
list.** Only items 4 and 5 are live, and neither blocks anything.

1. ~~**Record the demo.**~~ ✅ **Done 2026-09-20.** Recorded as a narrated 14-scene cut — five
   scenes of the deployed board inside nine deck scenes, voiced by Amazon Polly (Matthew,
   generative). `DEMO.md` → *As recorded* has the scene map and why it diverged from the
   single-take run sheet.
2. ~~**Upload to YouTube.**~~ ✅ **Done 2026-09-20.**
   **<https://www.youtube.com/watch?v=VBSuDCQa4y4>** — 2:38 (`lengthSeconds: 158`), under the
   3:00 limit. **The signed-out check is done and passed**, by fetching the watch page
   unauthenticated: `playabilityStatus: OK`, `isPrivate: false`, `isUnlisted: false`. The link
   is in `SUBMISSION.md`, `README.md`, `BUILD_PLAN.md` and `DEMO.md`.
3. ~~**Submit** with the public URL, the repo link and `SUBMISSION.md`.~~ ✅ **Done — confirmed
   by the user 2026-09-21.** The deadline was met. **This item is closed. Do not re-raise it, do
   not ask whether it happened, and do not treat it as pending in any future session.**

Housekeeping, not blocking:

3b. **Decide the default token budget for self-created workspaces.** `DEFAULT_TEAM_BUDGET`
   is 1,000,000, which makes the headline mechanic invisible to a judge who types their own
   workspace name: a real 666-token task moves the meter 0.1% and paints no bar. **The
   recording is not affected** — a take seeds `alpha` at 5,000 explicitly and `DEMO.md` records
   there — so this only touches the judge who explores after watching. Measured on the
   deployed build 2026-09-20: the same board at a 8,000 ceiling reads 81.2% in vivid red.
   Not changed unilaterally because it is a spend-policy call. If you want it:

   > **Half of this is done as of PR #6 (2026-09-21).** The *seeded* boards now default to
   > 100,000 — one ~800-token task at 0.8%, ~125 tasks of headroom. This item is now only
   > about `DEFAULT_TEAM_BUDGET`, the workspace a judge creates by typing a new name, which
   > is a stack parameter and needs a redeploy rather than a reseed. 25,000 below is still
   > the suggestion; it is the same reasoning applied to a board nobody reseeds.

   ```bash
   # samconfig.toml → parameter_overrides, NOT template.yaml's Default:
   # (CloudFormation keeps existing parameter values on update — see Known issues)
   #   TokenBudget=25000        # ~35 tasks, ~2.6% per task, clearly visible
   sam deploy
   ```

4. **Confirm AWS Budget notification email** — check `arunishrajput7@gmail.com` for the
   `hiveos-guardrail` subscription confirmation.
5. **Optional, post-hackathon: open an AWS Support case** about the account-level Bedrock
   restriction (42 of 43 per-day token quotas at zero, `adjustable=False`, first-party Amazon
   Nova included). Nothing waits on it any more — inference runs on Groq and Phase 3 is closed.

Items 1–3 **were** the submission and are **all closed**. Items 4 and 5 never blocked it and
still don't — 4 is a two-minute inbox click worth doing, 5 is optional and post-hackathon.

---

## Known issues and discoveries

- **✅ FIXED 2026-09-22 — a handoff looked like it stopped at the crossing, and the cause was not
  in the handoff.** Reported as "the receiving agent never produces the final answer": the board
  showed ADA → IRIS and the interaction appeared to end. **Every backend suspect was traced and
  cleared.** The deployed Lambda package was unzipped and diffed file-by-file against `main` —
  `agent_runner/app.py`, `router/app.py` and all eight `shared/` modules are **byte-identical**, so
  the per-leg idempotency key from `eb01e31` (`IDEMPOTENCY#<task_id>#<hops>`) is genuinely the code
  running. A live handoff driven against `wss://mel2gpat9c…/prod` showed both legs completing in
  10.1s: Ada's reply, the `agent_handoff` frame, then Iris's `agent_response` carrying the real
  answer, `user_id: alice`, `handoff_from: coder` and the **same** `task_id`. CloudWatch confirms
  the receiving leg is dispatched to SQS, is **not** skipped as a duplicate, and does call the
  model; DynamoDB holds `IDEMPOTENCY#<id>#0` **and** `#1` per chain, plus two `TASK#` rows.
  The one "duplicate delivery" line in three days of logs is dated **2026-09-20 16:28**, prints the
  pre-fix message format (no `hop N`), and therefore predates the fix being deployed.
  **The break was the last link: `activityFor` in `frontend/src/useHive.js`.** The inspector shows
  one desk at a time and filters activity by desk. `agent_handoff` was deliberately dual-homed
  (`agent` = sender, `agentTo` = receiver) so the crossing could not vanish from one terminal — but
  the **answer the crossing produces** was filed under the receiving desk alone. The user had typed
  into Ada's inspector, so Ada's terminal is what they were watching, and Iris's answer was one
  unclicked desk away. Fixed by giving the handed-over response the same dual-homing —
  `agentTo: frame.handoff_from ?? null` — and hoisting the filter into an exported `belongsToDesk`
  so the rule is stated once rather than copied. Verified in a real browser against the deployed
  backend: Ada's terminal now reads Ada's reply → the ADA → IRIS crossing → `Iris → alice · handed
  over by Ada` with the answer. Regression tests: `frontend/src/useHive.test.js`, 10 cases under
  plain `node --test` (**no new dependency**), `npm test` in `frontend/`. With the one-line fix
  reverted the key test fails with `actual: ['response','handoff']` against
  `expected: ['response','handoff','response']` — the reported symptom exactly.
  **Deployed 2026-09-22 as Amplify job 42 (23:48:50–23:48:58 IST).** The fix was briefly
  committed-but-unshipped: pushed at 23:43, while job 41 had gone out at 23:08, so for five
  minutes the public URL still had the bug that `main` no longer had. Caught by the next
  session's deployment check rather than by anything that watches for it. Proven by the bundle rather than the clock — the shipped
  `index-DFs9rVOB.js` held **2** occurrences of `agentTo` (the pre-fix count: the crossing in
  `useHive.js` and the inline filter in `App.jsx`), and job 42's `index-BBFAQh6W.js` holds
  **3**, including `agentTo:f.handoff_from??null` in the `agent_response` case, which is the
  one-line fix itself. The live file is byte-identical to a local build of `main`
  (SHA-256 `8a312c6e…858e58`) and the CSS hash is unchanged from job 41, so nothing about the
  nine worlds moved. `npm test` 10/10 before the build.

  *Lesson worth keeping: a symptom that reads as "the backend dropped the second leg" can be a
  frontend filter, and the cheapest way to tell them apart is to watch the wire — one `websockets`
  client against the deployed socket answered in one run what a day of code reading could not.*

- **✅ CLOSED 2026-09-22 — a green push is not a deployed frontend, and nothing in the repo
  says so.** Caught early here, but worth stating once: Amplify is in
  **manual-deploy mode** — `aws amplify get-app` reports `repository: None` — so **no build
  fires on `git push`**, and the branch's `enableAutoBuild: true` is inert without a connected
  repo, which makes it actively misleading to read. A frontend commit is only live once
  `./scripts/deploy-frontend.sh` has been run for it. The tell is cheap: a manual deploy takes
  ~8 seconds end to end, so compare the newest job's `endTime` against the commit time, and
  when they disagree settle it on the bytes — `curl` the live `index.html` for its asset hash
  and compare with `frontend/dist/`. This is deliberate (no GitHub OAuth, no build role — see
  *The Amplify app is not managed by CloudFormation* below) and is not a defect to fix; it is a
  step that has to be remembered, and a session that verifies deployment state by reading
  `PROGRESS.md` will get it wrong.

- **⚠ OPEN — the last-agent guard is not atomic, so a floor can be emptied of every agent.**
  Found by `ws_smoke.py` on 2026-09-22, during Phase 27's frontend-only gate run. Check 26 sends
  two `dismiss_agent` frames back to back — `coder` then `researcher` — and expects the second to
  be refused with "at least one agent". On one of three runs **both succeeded** and the harness
  aborted: `alice: timed out waiting for 'error'; saw [agent_dismissed researcher,
  agent_dismissed coder]`. The other two runs passed it, so it is a race rather than a
  regression: each invocation reads the roster, sees two agents, and deletes — neither sees the
  other's write. Classic TOCTOU on a guard that has to be a condition expression on the write
  rather than a read followed by a write, which is exactly the shape PR #7 fixed for the budget
  ceiling. **Not caused by and not fixable within Phase 27** — the world phases are frontend-only
  by their brief and this phase touched no backend file. Recorded rather than fixed; it needs a
  backend change and the user's say-so. Consequence if it fires in front of anyone: an empty
  floor, which `ensure_team` repopulates on the next `$connect`, so it is recoverable rather than
  destructive.
- **⚠ OPEN — a stale `CONN#` row from the Phase 24 session is still in the table, and it is what
  keeps `ws_smoke.py` at 109/113.** `TEAM#p24arctic` / `CONN#gbRBow8DXQAYKEiVrA==` / `claude`.
  The four "no `CONN#` rows leak" checks scan the whole table, not the team under test, so any
  row left by any browser fails all four of them — which is precisely the "documented false
  positive" every phase note since Phase 19 has been carrying. Two rows exist today: this one and
  `TEAM#alpha`/`dana`, which is the suite's own fixture racing its disconnect cleanup and is
  genuinely transient. **Deleting the `p24arctic` row would take the suite to 111/113 and is one
  `aws dynamodb delete-item` call, but it is a destructive write to live shared state and nobody
  asked for it.** It also means that workspace shows a phantom member. Left for the user to
  decide.
- **⚠ OPEN — the waiting line crowds at six or more queued, and Paper Office is the worst case.**
  Found by Phase 27's contrast rig. `WAIT_PER_ROW` is 5 and `WAIT_DY` is −12, so the overflow row
  sits 12% of the floor above the first — which at the 540 framing is 31px against a 40px
  character. Row two's `queued #N` caption lands on the head of the pawn standing in row one:
  **1.00:1 on Paper Office**, 1.08–1.98 across the eight worlds. With row one empty the same
  captions measure 4.68–8.63, so it is occlusion and not colour. The captions also run into each
  other horizontally at 540 — `WAIT_DX` is 9% ≈ 46px against a caption wider than that — which is
  visible with five queued, not six. **Base geometry in `components.jsx`, identical in all nine
  worlds, and therefore excluded from the 36-cell matrix: a defect the pixel-frozen default shares
  exactly is not something a world did.** Not in Phase 27's brief and it moves the floor layout
  the demo was framed against, so it is the user's call rather than a session's.
- **A clean textual merge is not a clean semantic merge, and the token meter is where that bit.**
  Bug F (PR #9) made `history.record` raise instead of swallowing, so `_reply` could now fail
  *after* `state.add_tokens` had already settled the task. Its rollback backed out
  `result.tokens`. But PR #7 had since landed on `main`, and `_reply` settles
  `result.tokens - reserved` — so the rollback was also releasing the reservation, and
  `_handle` only clears its `reserved` local *after* `_reply` returns, meaning the `finally`
  released the same placeholder a second time. Git merged the two hunks without a conflict
  because they never touched the same lines. A task whose ledger write failed left
  `tokens_used` at **-1805** on a fresh workspace: negative, on the number the whole product is
  about. Fixed by rolling back `reserved - result.tokens`, the exact inverse of the settling
  write, which leaves the hold outstanding for the `finally` to release once.
  **The lesson to carry: when two PRs change the same function for unrelated reasons, the
  absence of a conflict marker is evidence of nothing.** Read the merged function.

- **The DLQ redrive tool can cut a live task short, and that is documented rather than fixed.**
  A redrive clears the task's `IDEMPOTENCY#` marker on purpose — that is what makes the replay
  run — so the replayed task ends like any other, releasing `slot_id` with
  `expected_holder=<user_id>`. That names a *user*, not a task. If the same person has since
  claimed the same desk, the replay frees it under them and clears the `ACTIVE#` admission
  Bug E added. Narrowing the release would mean putting a task id on the `AGENT#` row, which is
  a schema change a recovery tool should not drag in. `DEPLOYMENT.md`'s runbook now says to
  check `--inspect` output against the board before `--redrive-all`.

- **`ACTIVE#` locks a user out for up to an hour if a runner dies without its `finally`.**
  By design — the TTL is the orphan net and it matches `TaskQueue`'s `MessageRetentionPeriod`.
  Every ordinary path releases it (`set_idle` on completion, the rollback in `_claim_agent`,
  the handoff's failure branch), so this is reachable only by a hard Lambda kill. Worth knowing
  before debugging a "you already have an agent running or queued" that looks impossible:
  the row is at `TEAM#<team>` / `ACTIVE#<userId>` and deleting it by hand is safe.

- **A queued person's label loses its ochre for the ~700 ms they are walking. Not fixed, and
  deliberately not fixed now.** `components.jsx:1368` assigns `pawn--waiting` only when
  `waiting && !isWalking`, so while a newly-queued member crosses to the waiting area their
  `queued #N` label falls back to `--faint` and goes `--honey` on arrival. The *word* is correct
  throughout; only the hue is late. Found in Phase 22 while driving six identities at once —
  measured `rgb(164,150,194)` on the walker and `rgb(255,158,92)` on the one already standing on
  a marker. It is shared behaviour, identical in Paper Office, and the exclusion is there so
  `pawn--walking` wins the animation. Touching pawn class logic on submission day to chase a
  700 ms hue transient is the wrong trade; a fix belongs in Phase 27, and the honest shape of it
  is to split the animation class from the state class rather than to widen the condition.

- **A bootstrap that runs on every request is an undo for anything that legitimately deletes
  what it writes.** `ensure_team` re-created Ada and Iris on every `$connect`, conditional on
  the row being absent — which is precisely the state `dismiss_agent` leaves behind, so a
  dismissal survived only until the next person connected. The conditional write looked like
  the careful choice and was the bug: "only write if it is missing" and "put back whatever
  somebody removed" are the same code. Anything self-healing has to ask whether the state it
  restores was *lost* or *given up*. Found by dismissing a desk in one browser and watching it
  reappear when a second client connected — no test caught it, because all three harnesses
  build state up and never take it away.
- **Two client frames sent back to back are not ordered.** `ws_smoke.py` section 26 sends
  `dismiss_agent coder` then `dismiss_agent researcher` to prove a floor cannot be emptied.
  Whichever Lambda lands first wins and the other is refused as the last desk — so *which*
  seeded desk survives is genuinely nondeterministic, and it has been observed both ways. The
  existing check is fine because it only asserts that one of them was refused. The new
  dismissal-persistence check hardcoded `["researcher"]` and failed on the first run against
  the fixed code: the invariant was stated wrong, not violated. It now compares the roster
  before and after a join, which is what is actually guaranteed — connecting does not change
  the roster — and is order-independent.
- **A latched UI flag needs every frame that can honestly clear it, not just the cheapest
  one.** `budget_exhausted` blocks the client; only `state_snapshot` cleared it. An admin
  raising the budget broadcasts `token_update`, which is deliberately outside `RESYNC_EVENTS`
  (re-reading the board after every task is the one thing that would make the meter
  expensive) — so the meter dropped to 14.2% while the red banner stayed up and the send
  button stayed disabled, with no way out but a reload. The rule: if a frame carries enough to
  answer the question, it must answer it; do not rely on a re-sync that was tuned away for
  good reasons. Same family as the `estimated` flag riding only on `token_update`.
- **A bug in the one direction the tests never go is invisible however many tests there are.**
  110 smoke checks, 15 rehearsal checks and 22 unit tests all passed over the dismissal bug —
  and `ws_smoke.py` section 26 *does* dismiss a desk and assert it is off the floor. It passes
  because it asserts on the same connection that did the dismissing, and the resurrection
  needs a **new** `$connect` to happen. The gap was never "dismissal is untested"; it was that
  nothing dismissed and then kept using the board. Coverage of the *happy expansion* is not
  coverage.
- **`isinstance(x, str)` before `x.startswith(...)`, on anything off the wire.**
  `body.get("action")` reached `.startswith("admin_")` unchecked, so `{}`, `{"action": null}`
  and `{"action": 7}` all became `AttributeError` → `"internal error"` → a stack trace per
  frame. The generic handler did its job; it just answered for the wrong party.
- **The default token budget makes the product's headline mechanic invisible.**
  `DEFAULT_TEAM_BUDGET` is 1,000,000 and a real task costs ~600-800, so a self-created workspace
  shows 0.1% and an unpainted bar. Not a bug — `reset-demo.sh` owns the seeded boards — but it is
  what a judge sees if they open the URL and make their own room. See *Manual actions pending*
  item 3b for the one-line change. **PR #6 (2026-09-21) fixed the seeded half of this**: the demo
  default is 100,000, sized so one task is 0.8% and the bar moves. `DEFAULT_TEAM_BUDGET` is the
  half still outstanding, and it is a stack parameter, so it needs a redeploy rather than a
  reseed.
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
- **`pytest tests/` fails to collect on this machine** — system Python 3.14 has no `botocore`,
  and `scheduler.py` imports it, so the failure is a `ModuleNotFoundError` at *collection*, not
  a test failure. Nothing is wrong with the tests: `python3 -m venv .venv && .venv/bin/pip
  install boto3 pytest && .venv/bin/python -m pytest tests/` is **14/14**. The `.venv/` is
  gitignored. Do not "fix" the tests in response to this error.
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
| SQS `hiveos-agent-tasks` + DLQ | ✅ both empty, nothing dead-lettered. **DLQ now has recovery tooling** (`scripts/recover_dlq.py`, `backend/shared/dlq.py`) — `--inspect` verified against the live queue 2026-09-22. Export `hiveos-DeadLetterQueueUrl` exists; `DLQ_URL` is on the runner's environment |
| Agent Runner `hiveos-agent-runner` | ✅ verified end to end — **real model**, provider-reported tokens, the PR #7 budget-ceiling reservation, **and bugs F/E/H/G** (deployed **2026-09-22 06:01 UTC**, `CodeSha256 KWn/4lZ+4KXjKM60ydKMmS8WJ1f8FfCST99V5ljpV8g=`). `DLQ_URL` present in its environment |
| SSM `/hiveos/groq-api-key` | ✅ SecureString, read at runtime, IAM-scoped to the Agent Runner |
| Amplify app `hiveos` / public URL | ✅ `dbavt8jr66qxx` → https://main.dbavt8jr66qxx.amplifyapp.com — **job 42** (2026-09-22), the Phase 27 polish build plus the handoff-inspector fix. Live bundle `index-BBFAQh6W.js`, SHA-256 `8a312c6e…858e58`, **byte-identical** to a local build of `main`; the CSS is still `index-CXyWO1wF.css`, the same hash job 41 served, so all nine worlds and the pixel-frozen default are untouched by the deploy |
| Worlds shipped in the deployed bundle | ✅ **Paper Office (default), Night Watch, Enchanted Forest, Reef Station, Alien Colony, Cloud City, Arctic Base, Desert Outpost, Ancient Ruins** — all nine read back from the live picker |
| Demo video | ✅ **https://www.youtube.com/watch?v=VBSuDCQa4y4** — 2:38, public, `playabilityStatus: OK` on an unauthenticated fetch |

**The Amplify app is not managed by CloudFormation.** This is deliberate and matches
`BUILD_PLAN.md` Phase 4 task 5 and `DEPLOYMENT.md`: manual-deploy mode needs no GitHub OAuth
and no build service role, which makes it fully scriptable. The consequence is that
`describe-stacks` will never mention it — `scripts/deploy-frontend.sh` finds it by **name**
(`hiveos`) so repeat runs across `/clear` sessions reuse it instead of creating duplicates.
`sam delete` will not remove it; teardown needs `aws amplify delete-app --app-id dbavt8jr66qxx`.

---

## Next recommended action

### ✅ Nothing is queued. The build plan is finished.

**Phase 27 shipped on 2026-09-22 and it was the last one.** Every phase in `BUILD_PLAN.md` is
`COMPLETE` — the hackathon set (0–17), the world set (18–26) and the polish pass (27). There is
no "next phase" to start; a session told to start one should say so rather than invent work.

**The state this leaves.** Nine looks in the picker, all nine passing a 36-cell contrast matrix
measured on rendered pixels, a cross-fade between any two of them, a Random World entry, a
keyboard-correct picker, and Paper Office still the default and still proven byte-for-byte
unchanged. The submission is in, the video is up, the stack is live, and `main` and the deployed
frontend are in step.

**If the user wants more work, it has to come from the user.** The three things this run turned
up and deliberately did **not** do are listed under *Known issues and discoveries* — a
last-agent dismissal race in the backend, a stale `CONN#` row left by an old session, and the
waiting line crowding at six or more queued. None is in any brief; all three are real.

**Nothing backend is outstanding either.** Bugs F, E, H and G went in on 2026-09-22 as PRs #9,
#8, #11 and #10, in that order, and the stack was redeployed for the DLQ wiring #10 needs.
`pytest` 112/112.

**Why the world phases were live work at all.** The hackathon is over and **the submission is
in** — the video is recorded, uploaded and verified public
(**<https://www.youtube.com/watch?v=VBSuDCQa4y4>**, 2:38), and the user confirmed on 2026-09-21
that it was submitted inside the deadline. Phase 6 is closed, task 9 included. With that done,
the user finished the world phases the deadline had cut short: two shipped during the hackathon
(**19 Night Watch and 22 Alien Colony**), **20, 21, 23 and 24 on 2026-09-21**, and **25, 26 and
27 on 2026-09-22**.

> **To any future session: do not tell the user to submit.** It is done. Do not ask whether it
> was done, do not list it as outstanding, and do not reopen it because an older line further
> down this file still reads as though it were pending — those are historical records of phases
> as they closed, and this section outranks them. The only reason to raise submission again is
> if the user brings it up first.

**The bar the world phases were held to, kept for anything added later.** The shared
**Validation** block, the **recolour test** and the **state-legibility contract** gated every one
of them, and Phase 27 added one clause to how the last of those is measured: a contrast number is
a claim about the pixels under the glyphs, so the rig forces each caption white, black and
transparent and samples only the stroke core. A token table is a floor, not the measurement.

> **The run sheet below is retained on purpose, not by neglect.** It is what the board segments
> of the recorded take were shot against, and it is what would make a re-take possible if one
> were ever wanted. `DEMO.md` → *As recorded* explains how the finished cut differs
> from it: a narrated 14-scene edit with an Amazon Polly voice track, rather than one continuous
> three-window capture. Everything about framing, identities and beat order still applies.

**How the deferred phases ended up.** On 2026-09-20 the user asked for Phase 22 only and then for
the project to be finalised for the recording. Phases **20, 21, 23–27 were deferred, not cut** —
every brief in `BUILD_PLAN.md` stayed intact, and **all of them have now shipped**.

**The route into a world phase, retained in case a tenth world is ever wanted:**

- Read the `## Phases 18–27` section of `BUILD_PLAN.md` first — it carries two contracts (the
  recolour test and the state-legibility contract) a session will otherwise not infer, and both
  are applied at every world gate.
- Then read **the four findings under each of Phases 19–27**, in the same file. Between them they
  cover every shared-code trap found so far, and most have a fix already written in one of the
  eight world stylesheets to copy rather than rediscover. **Start with the ones for a world of
  the same key** — a dark world needs the five `--ink`-inverts overrides and a light one needs
  none of them, and every lighting technique the dark worlds established stops working above
  Paper Office's brightness.
- Copy the shape of an existing registry entry in `worlds.js`. A dark world sets
  `colorScheme: 'dark'` and a `themeColor` matching its own page ground; a light one sets
  `'light'`, exactly as Cloud City and Arctic Base do.
- The floor's objects are all tokens — `--mug`, `--board-face`, `--bottle`, `--cooler-body`,
  `--glass-sky`, the five fixtures, the three `.worldlayer` slots. **The recolour test is real:
  if the whole diff is values inside the token block, the phase is not done.**
- `agentDesigns` is live as of Phase 22 — use it when the agents should be a different species
  from the people, and leave it `null` when they should not. Both are real answers.
- **A world stylesheet must never set `--walk-top`** — the registry owns it, because the walk
  math in `components.jsx` reads the same number and CSS cannot tell it anything.
- Pick a breakpoint carefully if you touch one: **the demo records at 960 and 540.**
- **Size anything shaped on the floor off `--tile-size`, never as a percentage of the floor.**
  Phase 20's finding 2: the floor is **516×260** at the 540 framing and **515×622** at 960, so a
  percentage gradient radius is a different shape at each. **But the token is not one number** —
  Phase 26 found 44px at 540 against 52px at 960, and Phase 27's sweep adds **62px at 1500 and
  above**, with the 900 cliff as the 44→52 step. Check every register you care about, in pixels.
- **A gradient *angle* is a percentage in disguise** (Phase 25's finding 1): a directional
  gradient in a box whose aspect ratio changes between framings is a different shape at each,
  which is exactly what makes it look safe.
- **A continuous surface may not tile.** Phase 20's finding 1 corrects the "two lattices" rule
  Phases 19 and 22 recorded: that rule holds for fields of *discrete* objects (stars, crater
  pocks) and fails for anything continuous (moss, sand, snow), where any periodicity reads as a
  rendering artefact. Use large non-repeating blotches instead.
- **Phase 21's own trap, from its brief:** it is the hardest contrast case in the set — a blue
  world that has to keep a blue busy state legible. Phase 20 hit the same shape of problem with
  green and solved it by hue distance measured rather than eyeballed; do the same here, and
  record the four numbers.

> **The deadline (2026-09-20) was met and the submission is in.** `main` stayed recordable
> throughout: Paper Office is still the default and is proven byte-for-byte unchanged, so no world
> phase ever put the recording at risk. Four looks are in the picker — Paper Office, Night
> Watch, Enchanted Forest, Alien Colony — which is more than enough to make the world switch a
> real beat on camera if a future re-cut ever wants one.

**`DEMO.md` has been re-measured and re-rehearsed against the office (2026-09-19). Follow it
as written — the figures in it are measured, not estimated.** What it now says, in brief:

- **Windows: office 960 wide, witness 540, side by side = 1500 on this 1512 px desktop.**
  900 CSS px is a cliff, not a slope — 900 is the landscape office, 899 is a 1164 px
  scrolling column. Never write a window size as "about 900". Two landscape windows need
  1800 px and do not fit this machine; the old instruction to put them side by side without
  overlapping was impossible.
- **Three identities are mandatory, two windows are on camera.** Alice and bob fill the two
  desks; **charlie is the queue**. `DEMO.md` used to call him optional, which would have
  cost the centrepiece beat.
- **Hiring is Beat 5 and runs after the queue beat, never before.** A third desk hired early
  means charlie is dispatched into the spare and the queue, the walk and the auto-dispatch
  silently do not happen. `rehearse.py` covers it now and enforces the order.
- **A handoff is still an unrehearsed beat and is still not in the run sheet.** One request,
  two agents, one bill — but it costs ~1,900 tokens and `rehearse.py` does not drive it.
  Decide deliberately, then rehearse it; do not improvise it on camera.

> **Standing note, recorded once so it stops being re-raised.** Every feature in `PRD.md`'s
> Must list is built, deployed and verified, and the product has been submittable since Phase
> 4. The user chose to spend the window expanding rather than recording — first on 2026-09-19
> (Phases 12–17, now finished) and again on 2026-09-20 (Phases 18–27, the worlds). Everything
> from here is upside; the recording is the only thing that is not optional. **It happened on
> 2026-09-20 and is public. Submitting is now the only thing that is not optional.**
>
> **A world phase must never invalidate this run sheet.** Phase 17 did exactly that — it killed
> the 640×950 framing overnight — which is why Paper Office stays the default and why no world
> may change the floor's percentage coordinates or its composition. If one ever does, `DEMO.md`
> is re-measured and `rehearse.py` re-run **in the same phase**, not afterwards.

```bash
# python3, not python — this machine has no `python` on PATH
DEMO_TEAM=p6stage DEMO_PASSPHRASE='…' python3 scripts/rehearse.py --takes 2   # 15/15
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

> **Re-checked 2026-09-20 on user request. Still blocked, identically. Inference stays on
> Groq and no code changed.** Both failure modes are byte-for-byte what Phase 3 recorded, so
> nothing about the account has moved in three days:
>
> | Probe | Result |
> |---|---|
> | `converse` → `us.amazon.nova-lite-v1:0` | `ThrottlingException: Too many tokens per day` |
> | `converse` → `us.amazon.nova-micro-v1:0` | `ThrottlingException: Too many tokens per day` |
> | `converse` → `us.anthropic.claude-haiku-4-5…` | `AccessDeniedException: INVALID_PAYMENT_INSTRUMENT` |
> | `service-quotas` "tokens per day", `us-east-1` | **35 of 35 are `0.0`, and `0 of 35` are adjustable** |
>
> The quota table is the part that closes this. Every per-day token quota on the account is
> zero **and** carries `Adjustable: false`, so there is no Service Quotas request that can
> raise one — it is an account-level restriction that only AWS Support can lift, and not
> inside the hackathon window. **Do not re-run this probe.** It costs nothing but it answers
> the same way every time, and the answer has been the same since Phase 3.

### Standing gotchas for the recording

- **Point the recording windows at `/#/workspace`, not `/`.** `/` is the landing page now. It is
  the right thing for a judge arriving cold and the wrong thing for a take — every window
  needing an extra click before the gate is another chance to be caught mid-scroll. `DEMO.md`
  has the link.
- **Every command in the run sheet is `python3`.** `python` is not on this machine's `PATH`
  and exits `command not found`. Both `DEMO.md` and this file said `python` until 2026-09-19;
  it would have been the first thing typed on recording night.
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
- **The 640×950 three-window layout is dead and the figures that went with it are gone.** It
  described the single-column HUD that Phase 17 replaced. Re-measured on the deployed office,
  2026-09-19: the shell is `100dvh` and **never scrolls at ≥900 px wide**, so height is no
  longer a fit problem — at a 1440×900 viewport it lays out to exactly 900 (44 title bar +
  777 floor/inspector + 79 roster). Width is the only hard constraint and it is a **cliff at
  900**: 899 stacks into a 1164 px scrolling column. `DEMO.md`'s framing box has the measured
  window sizes; use those and nothing else.
- Each browser needs a **different profile or a cleared localStorage** to hold a separate
  identity: the entry gate persists to `localStorage['hiveos.identity']`, so two tabs of the
  same origin share one name.
