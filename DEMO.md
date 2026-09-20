# DEMO.md — the recording run sheet

> ## ✅ RECORDED AND UPLOADED — 2026-09-20
>
> **<https://www.youtube.com/watch?v=VBSuDCQa4y4>** · 2:38 · 1920×1080 / 25fps · H.264 + AAC
>
> Verified public from an unauthenticated fetch of the watch page: `playabilityStatus: OK`,
> `isPrivate: false`, `isUnlisted: false`, `lengthSeconds: 158`. The signed-out check that step
> 2 of *After recording* demands is therefore done — and it is the check that turns a whole
> build into a zero when it is skipped.
>
> **Everything below this box is still the run sheet, and it is still correct** — it is what the
> board segments were recorded against. Read *As recorded* next for how those segments were cut
> together, then use the rest of this file unchanged for any re-take.

---

## As recorded

The take is a **narrated 14-scene cut**, not the single continuous screen capture the run sheet
was written for. Five scenes are the live board; nine are deck. The voice is **Amazon Polly**
(Matthew, generative engine), scripted rather than spoken.

| Scene | Start | On screen |
|---|---|---|
| s01 | 0:00 | deck — 79% overran their AI budget, 36% have real-time control |
| s02 | 0:13 | deck — the OS analogy: scheduling, quotas, fair queueing |
| **s03** | **0:23** | **board** — one workspace, one floor, every member on the same board |
| **s04** | **0:30** | **board** — alice gives Ada a task; the desk lights up on every screen |
| **s05** | **0:39** | **board** — every desk busy → charlie queues → a freed desk picks it up |
| **s06** | **0:48** | **board** — one shared meter, enforced server-side · team memory |
| **s07** | **0:57** | **board** — hiring a third agent, live on everyone's floor |
| s08 | 1:03 | deck — React 19 on Vite, no game engine, one WebSocket held open |
| s09 | 1:13 | deck — Router Lambda, the atomic conditional claim, SQS vs. queue item |
| s10 | 1:30 | deck — Agent Runner: memory, ceiling, model, accounting, release, dispatch, broadcast |
| s11 | 1:43 | deck — one SAM template, one CloudFormation stack, 16 resources |
| s12 | 1:52 | deck — API Gateway, two Lambdas, DynamoDB, SQS + DLQ, SSM, Amplify, scoped IAM |
| s13 | 2:20 | deck — the honest note: Bedrock blocked account-wide, inference calls out to Groq |
| s14 | 2:31 | deck — scales to zero, live right now |

**Why it was cut this way.** The live sequence `rehearse.py` drives is ~95 seconds of board
time, and `BUILD_PLAN.md`'s beat table spends 30 seconds on the problem and 45 on architecture —
narration that was assumed to ride *over* the board. It cannot. The queue beat and the memory
beat both need the viewer reading one number on two windows at once, and talking across them
buries the exact thing the product exists to show. Cutting to a deck for the framing gave the
board its 40 seconds uninterrupted, and a scripted track holds 2:38 exactly instead of drifting
past 3:00 on the fourth retake.

**Three claims in the narration were checked against the deployed system before upload**, because
a number said out loud cannot be edited later: the stack really has **16 resources**
(`describe-stack-resources`), the Lambdas really are **Python 3.13 on arm64** (`template.yaml`),
and the frontend really is **React 19 on Vite** (`frontend/package.json`).

**What did not survive the cut:** the *"what was learned"* beat, and the world-switch beat below.
Fifteen seconds of lessons cost fifteen seconds of board, and the board wins. The lessons are in
`SUBMISSION.md`, which judges read.

---

Everything needed to record the 3-minute video in one take. **No new features from here.**

The sequence below is rehearsed automatically and passes 15/15 against deployed AWS:

```bash
python3 scripts/rehearse.py --takes 2
```

Run that first. If it fails, do not record — fix what it names.

> **`python3`, not `python`.** This machine has no `python` on `PATH` — the bare name
> exits `command not found`, and every command in this file used to be written that way.
> Caught by running them, 2026-09-19.

---

## Before you hit record

**Record in a private workspace, not the default one.** The public URL has real
visitors now — one of them walked into the middle of a rehearsal and appeared in
a member list a take was asserting on. A passphrase-protected workspace cannot
be joined by someone who happens to be reading the README.

```bash
export DEMO_TEAM=demo-stage
export DEMO_PASSPHRASE='pick something'

python3 scripts/rehearse.py --takes 2  # rehearses in that workspace
./scripts/reset-demo.sh                # clean board, SQS drained, Lambdas warm, verified
```

Both scripts honour those two variables. Unset, everything behaves exactly as
before and uses the open default workspace.

At the gate, each browser enters the same **workspace** name and the same
**passphrase**. The first one in creates it and becomes its administrator.

**Point the recording windows at the board directly:**

```
https://main.dbavt8jr66qxx.amplifyapp.com/#/workspace
```

`/` is the public landing page now, and the board is one CTA click behind it.
That is right for a judge arriving cold and wrong for a take — every window
needing an extra click before the gate is another chance to be caught
mid-scroll on camera. The hash link goes straight to the gate.

Show `/` itself in the opening seconds if you want the pitch on screen, then
cut to the board windows. It is a still page; nothing on it moves and nothing
on it connects.

It prints `snapshot clean — 2 desks IDLE (Ada, Iris), 0/5000 tokens, queue and memory empty`.
If it prints `DIRTY`, or warns that connection rows were live, **close every browser tab
pointed at the deployed URL and run it again.**

> ### The framing, measured on the deployed build (2026-09-19)
>
> Everything here used to say *three browser windows, 640×950, side by side*, earned over
> Phases 7–15. Phase 17 killed it: HiveOS is a landscape app shell now — floor on the left,
> agent inspector on the right, roster along the bottom. These figures replace it and were
> taken against the deployed URL, not estimated.
>
> **900 CSS px wide is a cliff, not a slope.** At **900** the shell is the landscape office
> and the page does not scroll. At **899** it becomes a single stacked column 1164 px tall
> and the page scrolls. One pixel decides it, so never write a window size as "about 900".
>
> **Height is not a fit problem.** The shell is `100dvh` and fills whatever it is given —
> at a 1440×900 viewport it lays out to exactly 900 (44 title bar + 777 floor/inspector +
> 79 roster), with no overflow on either axis and a clean console. Height only decides how
> big the room is, and the room is the shot.
>
> **Two landscape windows do not fit on this machine.** Two windows at ≥900 need 1800 px of
> desktop. This Mac's logical desktop is **1512×982** (`osascript … bounds of window of
> desktop`), so "side by side, both landscape" is arithmetically impossible here. The
> instruction that used to be in this box could not have been followed.
>
> **The configuration that does fit, both windows fully visible, nothing overlapping:**
>
> | Window | Size | What it is |
> |---|---|---|
> | **Primary — 960×957** | viewport ≈ 960×870 | The landscape office. Floor renders 515×548. This is the shot |
> | **Witness — 540×957** | viewport ≈ 540×870 | The stacked layout, and it is *not* a degraded one — the whole floor, both rooms, the waiting area, the nameplates, the meter and the chat input all sit above the fold |
>
> 960 + 540 = **1500**, inside 1512. Both screenshotted at these sizes and both read.
>
> **The stacked layout is the product, not a fallback.** The previous note called anything
> under 900 px "the mobile layout, not the product". That is wrong and it cost the framing
> its only workable option: the narrow column is a real responsive layout of the same live
> board, and on camera a second window that is visibly a *different shape* makes "one shared
> board, any screen" read faster than two identical rectangles do.
>
> If you record on an external display with ≥1800 px of width, two 900-wide landscape
> windows side by side is the nicer shot. Check `osascript -e 'tell application "Finder" to
> get bounds of window of desktop'` before planning it.

Then:

- [ ] `rehearse.py --takes 2` passed within the last hour
- [ ] Windows sized per the box above — **960 wide** for the office, **540** for the witness.
      Verified on the deployed URL at both: no horizontal overflow, no page scroll, zero
      console errors and zero warnings, both rooms and both nameplates legible. The roster
      strip scrolls inside itself once the floor is fully staffed, which is by design.
- [ ] **Three identities, and the third is not optional.** The queue beat is the centrepiece
      and it only forms when *every* desk is busy: alice takes Ada, bob takes Iris, and it is
      **charlie** who gets position 1. With the two-desk starting roster there is no queue
      without him. (This checklist used to call him optional. He is the beat.)
- [ ] Identities entered: **alice 🐝** (office window), **bob 🦊** (witness), **charlie 🦉** —
      same workspace, same passphrase
- [ ] **Where charlie's window goes.** 960 + 540 fills this desktop, so his window sits behind
      bob's and comes forward for his one request. His *proof* — walking into the waiting area
      — renders on alice's and bob's screens, so his own window never has to be the shot. If
      you would rather have all three visible at once, three **504**-wide windows total 1512
      and each shows the whole floor above the fold; you trade the landscape office for it.
- [ ] Each window is a **separate browser or profile**. The entry gate persists to
      `localStorage['hiveos.identity']`, so two tabs of the same origin share one identity and
      you will end up with two "Alice"s.
- [ ] Every window shows the same meter — `0 / 5000` — and the same desks IDLE
- [ ] **Browser extensions disabled, or record in a clean profile.** Grammarly injects a
      floating icon *into the prompt textarea* and it is clearly visible on camera. Found while
      verifying the deployed page — it was the only thing in the console, and the only thing on
      screen that is not HiveOS.
- [ ] Beat 4 of `rehearse.py` printed **`REAL — provider-reported usage`**. If it printed
      `ESTIMATED`, the model was unreachable: the board still works but the counts are
      heuristics, and the narration has to say so. Fix it before recording rather than
      explaining it on camera.
- [ ] Screen recorder capturing every window you plan to show
- [ ] Notifications silenced

The reset takes ~8 seconds. Between takes, run it again — it is idempotent.

---

## The take

Product time is ~16 seconds across five beats; the rest is narration over a live board.
Rehearsed timings are in brackets, and the harness reports 91–95 s of headroom against its
110 s allowance.

> ### The hiring beat is rehearsed now, and it runs last for a reason
>
> **Hiring an agent on camera.** Click `+ add agent` in the office window, type a name, pick
> a character, hit `spawn` — and the desk appears on the *witness* window's floor, seated and
> named, with nobody touching it. It is the clearest single proof in the product that this is
> one live shared board, and far more legible than matching numbers.
>
> `rehearse.py` now drives it as **Beat 5** and it passes: across four takes the hire reached
> a bystander's screen in **305–433 ms**, carrying its name, role, character and project, and
> a browser opening cold afterwards saw the same three desks in the same order.
>
> **Hire after the queue beat, never before it.** The queue only forms when every desk is
> busy. Hire a third desk first and alice and bob fill two of three, charlie is dispatched
> straight into the spare, and there is no queue position, no walk into the waiting area and
> no auto-dispatch — the two strongest beats in the demo silently do not happen, and nothing
> on screen tells you they didn't. The harness enforces the order for the same reason.

### 0:00–0:25 · The problem

Talking over the windows, before touching anything.

> Uber burned through its 2026 AI budget in four months. 79% of enterprises had overruns last
> year; only 36% have any real-time control. Teams share AI agents with no visibility, no
> fairness, and no way to stop a single heavy task draining the month. Operating systems solved
> this for CPU fifty years ago — scheduling, quotas, fair queueing. HiveOS applies that to a
> team's shared AI compute.

If asked how this differs from a local agent harness: **that governs one developer's own CLI
agents on their own machine; this is a cloud governance layer for a team sharing one budget.**

### 0:25–0:40 · Two windows, one workspace

Click once on the **workspace floor** in the office window, so your marker visibly moves on the
witness screen too. This is the cheapest possible proof that the windows are one live board —
much stronger than pointing at matching numbers, which a viewer could assume were screenshots.

> Three people, one workspace, one budget. Two agent rooms on the floor — Ada, who takes
> engineering work, and Iris, who researches — and a waiting area between them and us. Same
> meter, same queue, same rooms, on every screen, live. When I move here, it moves there.

Keep saying **three people** — there are three identities on this board even though two windows
are on camera, and charlie is about to be visible on both of them.

Keep it to one click — the floor is the opening handshake, not the point of the demo. The
nameplates are legible at recording size, so the agents introduce themselves; do not stop to
read them out, and do not narrate the floor plan. It pays off twice in the next two beats and
explaining it up front spends that twice.

### 0:40–1:25 · The queue moment `[~1s of product time]`

1. **Alice** picks **Ada** and requests an agent with the prompt:
   ```
   remember: deploy window = Friday 16:00 UTC
   ```
   → Ada's desk goes BUSY on **every** screen *(rehearsed 2026-09-19 over four takes:
   331–433 ms to a bystander, measured on bob's socket rather than alice's)*

2. **Bob** picks **Iris** — any prompt, e.g. `summarise yesterday's incident review`
   → Iris's desk goes BUSY. Both desks now full.

3. **Charlie** requests an agent with:
   ```
   when is our next deploy?
   ```
   → Charlie gets **queue position 1** — and on both visible screens he **walks into the
   waiting area and stands there**, captioned `queued #1`. This is why his own window never
   has to be on camera: the proof renders on everyone else's floor.

> Both agents are busy, so Charlie doesn't get a failure and he doesn't get a spinner — he gets
> a real position in line, he's standing in it, and the whole team can see him waiting.

**Let the walk land before you talk over it.** Charlie crossing the floor into the waiting area
is the queue becoming a place rather than a number, and it is the setup for the auto-dispatch
walk in the next beat. It takes ~700 ms.

**Have Bob pick Iris deliberately, not "Either".** If both of them ask for Ada, the second
request silently lands on Iris and the activity log says *"Iris → bob · Ada was busy"* — which
is true and is a feature, but it is an extra thing to explain in a beat that is about the
queue. Save the substitution for the Q&A.

**Say this, it is the accurate wording:** *every agent task runs through a real SQS queue, and
waiting tasks auto-dispatch the moment a slot frees.*

**Do not say** that Charlie is "parked inside SQS" — he is not. The queue is gated in DynamoDB;
SQS is the durable at-least-once handoff for tasks that are actually running.
(`ARCHITECTURE.md` decision 1.)

### 1:25–2:05 · The memory moment `[~8–10s of product time]`

This runs itself. Alice's task finishes, and three things happen in sequence — let them land.

1. A **toast** fires on every screen and Alice's fact appears in **team memory**,
   attributed to her — this lands as her task *starts*, so give it a beat before the rest
2. Her slot frees → **Charlie is auto-dispatched into it** *(rehearsed 2026-09-19: 0–118 ms
   after the desk went idle — one take landed both frames in the same millisecond)*. Watch the
   floor: Charlie **walks out of the waiting area, into Ada's room, and sits down**; the room
   and its monitor light up around him. Alice **walks back** to where she was standing. Nobody
   told either of them to move — the room is rendering the scheduler.
3. ~6 seconds later Charlie's response arrives — **already carrying Alice's fact**

> **The floor is worth narrating here.** A lit room *is* the slot being BUSY, someone sitting at
> the desk inside it *is* the holder of that slot, and the waiting area *is* the queue. There is
> no separate slot card and no queue card any more because there is nothing left for either to
> say.

**This walk is the single best three seconds in the demo.** It is one continuous shot of a
scheduler dispatching: a person leaves the queue, crosses the floor, enters the room, and the
room comes on. Do not cut away from it to point at a panel.

> Alice saved one fact for the team. Her slot frees, Charlie is dispatched automatically — he
> never asked twice — and his agent already knows the deploy window. Nobody told it. That's
> shared memory across a team's agents.

The meter has moved to roughly **2,450-2,860 / 5000** — about 50-57%, so it is unmistakably
visible. A task costs more now that the agent has tools: two round trips plus the tool schemas
in every prompt, roughly 700-1,100 tokens against roughly 270 before. An agent-to-agent handoff
is two agent runs and costs roughly **1,900** for the pair.

### 2:05–2:20 · The floor is staffed, not fixed `[~2s of product time]`

The Phase 17 beat, and the one that says what this product *is*. Do it here — **after** the
queue has paid off, for the reason in the box above.

1. In the office window, click **`+ add agent`**
2. Name it **Dwight**, role **Analyst**, pick a character that is not a teammate's avatar
3. Hit **spawn**

→ The desk appears on the **witness** window's floor, seated, named and idle, with nobody
touching that window *(rehearsed 2026-09-19: 305–433 ms)*. The roster strip gains a card and
the app bar goes to `0/3 working`.

> These two agents aren't the product — the floor is. You hire onto it. Dwight didn't exist
> ten seconds ago, nobody touched that second screen, and he's already at a desk with a name
> on it. Same budget, same ceiling, same queue — one more desk sharing them.

**Four desks is the cap** (`MAX_AGENTS = 4`), and it is a measured limit rather than a chosen
one: the floor's lower band cannot draw a fifth without a character landing on someone else's
nameplate. Do not hire more than twice on camera.

### 2:20–2:45 · Where AWS fits

> API Gateway WebSocket for the live board. Lambda for the router and the agent runner. SQS as
> the durable task handoff, with a dead-letter queue. DynamoDB as a single-table store, with
> atomic conditional writes doing the slot claiming and atomic counters doing the token
> accounting. Amplify hosts the frontend. All serverless, scaling to zero.

**Then say the inference sentence — once, plainly, do not bury it:**

> One honest note: Bedrock is quota-blocked on this AWS account, so model inference calls out
> to Groq. Everything else you just saw is AWS. And the token counts are real — they're the
> usage the provider reports, not an estimate.

**Do not say the agent is stubbed. It is not — that changed, and the counts are now real.**
The old caveat undersold a working system; saying it now would be false. If the model is ever
unreachable mid-take the workspace still answers, but from composed text, and every count it
produces is flagged `estimated` on screen. `rehearse.py` prints which mode the board is in —
`REAL` or `ESTIMATED` — in Beat 4. Check it before you record.

### 2:45–3:00 · What was learned

> The hard part wasn't the AI. It was making three browsers agree on one number, ordering the
> frames so a slot never looks stuck, and making a budget ceiling that actually refuses instead
> of just turning red.

---

## Optional: the ceiling beat

Worth 15 seconds if the edit has room. It needs its own near-spent board, so it is a **separate
take** — do not try to reach the ceiling during the main sequence.

```bash
TOKEN_BUDGET=1600 ./scripts/reset-demo.sh
```

Run two tasks. The second tips the meter over; the next request is **refused before the agent
is invoked** and `budget_exhausted` goes out team-wide.

> At the ceiling the agent is not called at all. Not throttled, not queued — not invoked. Zero
> tokens spent. That's the difference between a quota and a gauge.

The meter displays **100.0%** and **0 remaining**, even though the underlying count overshoots
(rehearsed at 1744 of 1600) — a task's cost is only known once it has run, so it cannot be
charged in advance, and the UI clamps. Rehearse it with `python3 scripts/rehearse.py --ceiling`.

**1600, and this number has moved twice.** 60 when the agent was stubbed (~58 a token a task),
500 once a real model call landed (~200–400), 1600 now the model has tools (~700–1,100). It
tracks the cost of a task; if that changes again, this has to follow or the climb stops being
watchable. Re-checked after Phase 16 and left at 1600: a plain task is ~700, so two land and the
third is still refused.

---

## Optional: the world beat

Worth 8–10 seconds, and it is the cheapest beat in the whole run sheet — it costs **zero tokens**
and cannot fail, because it is a CSS swap in one browser. Use it only if the edit has room after
everything above; **it is not part of the rehearsed 15/15 sequence and must not be inserted into
it**, because the main take's timings were measured without it.

Where it fits, if it fits: at the very end, over the closing line, on the **office window only**.
Leave the witness window in Paper Office — the contrast between the two is the point.

1. Click **◑** in the title bar (it is beside the gear, and unlike the gear everyone sees it).
2. Pick **Night Watch**, then **Alien Colony**, a beat apart. No reload, no reconnect, no
   flicker — the same board, still live, still connected.
3. Say one line over it and stop.

> The board doesn't care what it looks like. Same sockets, same scheduler, same rows in DynamoDB —
> the office is just the costume. What never moves is what the colours *mean*: busy is still busy,
> queued is still queued, over-budget is still red, in every one of them.

**What this buys and what it costs.** It buys "this is a real product with a real design system"
in under ten seconds. It costs the risk of looking like a toy if it runs long — so two clicks,
one line, out. **If the take is already at 3:00, cut this, not the queue beat and not the
ceiling.**

**Do not switch the witness window.** The claim of the whole demo is that every screen shows the
same state; two differently dressed screens showing the same state proves it harder, and two
identically dressed screens showing it prove it fine. Switching both proves nothing and loses the
comparison.

---

## If something breaks mid-take

From `BUILD_PLAN.md`'s fallback ladder. **Fix only what is broken — never add a feature to
rescue a demo.**

| Symptom | Do this |
|---|---|
| A slot looks stuck BUSY | `./scripts/reset-demo.sh`, start the take over |
| A browser shows a stale board | Reload it — the client re-syncs from `state_snapshot` |
| Member count looks wrong | A stray tab is connected. Close it, reset, re-record |
| WebSocket won't connect | Record the components separately rather than abandoning |
| Everything is slow on the first click | Lambdas went cold — rerun `reset-demo.sh` to warm them |

---

## After recording

1. Upload to YouTube, **public or unlisted**
2. **Open the link in a signed-out browser** — an accidentally-private video is a zero
3. Confirm the video is **under 3:00**
4. Confirm both doors still open cold — the landing page at
   <https://main.dbavt8jr66qxx.amplifyapp.com> and the board one click behind it at
   <https://main.dbavt8jr66qxx.amplifyapp.com/#/workspace>
5. Submit with the writeup in `SUBMISSION.md`
