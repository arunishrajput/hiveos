# DEMO.md — the recording run sheet

Everything needed to record the 3-minute video in one take. **No new features from here.**

The sequence below is rehearsed automatically and passes 12/12 against deployed AWS:

```bash
python scripts/rehearse.py --takes 2
```

Run that first. If it fails, do not record — fix what it names.

---

## Before you hit record

**Record in a private workspace, not the default one.** The public URL has real
visitors now — one of them walked into the middle of a rehearsal and appeared in
a member list a take was asserting on. A passphrase-protected workspace cannot
be joined by someone who happens to be reading the README.

```bash
export DEMO_TEAM=demo-stage
export DEMO_PASSPHRASE='pick something'

python scripts/rehearse.py --takes 2   # rehearses in that workspace
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

> ### ⚠ The framing changed in Phase 17. Three portrait windows no longer work.
>
> Everything below used to say *three browser windows, 640×950, side by side*, and that
> measurement was carefully earned over Phases 7–15. **It is dead.** HiveOS is a landscape
> app shell now — floor on the left, agent inspector on the right, roster along the bottom —
> and it stacks into a single scrolling column below 900 px wide. A 640 px window shows the
> mobile layout, not the product.
>
> **The new framing is one wide window plus one small one:**
>
> | | |
> |---|---|
> | **Primary — 1440×900** | The office. This is the shot. Everything happens here |
> | **Secondary — ~900×760** | One teammate's view, for the beats that have to be proved on a *second* screen: hiring, the meter moving, the queue |
>
> Two windows rather than three. The third was there to make "everyone sees the same board"
> legible, and one witness proves that as well as two while leaving the office big enough to
> read. Put the secondary window beside or below the primary — do not overlap them.
>
> **Re-measure before recording.** No pixel figure below has been re-verified against the new
> shell at 1440×900.

Then:

- [ ] `rehearse.py --takes 2` passed within the last hour
- [ ] Primary window **1440×900**, secondary **~900×760**. Verified on the deployed URL at
      1440: no horizontal overflow, zero console errors, the floor and all four desks on
      screen at once. The roster strip scrolls inside itself if the floor is fully staffed,
      which is by design — but with four desks it does not need to.
- [ ] Each window is a **separate browser or profile**. The entry gate persists to
      `localStorage['hiveos.identity']`, so two tabs of the same origin share one identity and
      you will end up with two "Alice"s.
- [ ] Identities entered: **alice 🐝** (primary), **bob 🦊** (secondary) — same workspace,
      same passphrase. A third, **charlie 🦉**, only if you are demonstrating the queue with
      every desk busy
- [ ] Both windows show the same meter — `0 / 5000` — and the same desks IDLE
- [ ] **Browser extensions disabled, or record in a clean profile.** Grammarly injects a
      floating icon *into the prompt textarea* and it is clearly visible on camera. Found while
      verifying the deployed page — it was the only thing in the console, and the only thing on
      screen that is not HiveOS.
- [ ] Beat 4 of `rehearse.py` printed **`REAL — provider-reported usage`**. If it printed
      `ESTIMATED`, the model was unreachable: the board still works but the counts are
      heuristics, and the narration has to say so. Fix it before recording rather than
      explaining it on camera.
- [ ] Screen recorder capturing all three windows
- [ ] Notifications silenced

The reset takes ~8 seconds. Between takes, run it again — it is idempotent.

---

## The take

Product time is ~15 seconds; the rest is narration over a live board. Rehearsed timings are in
brackets.

> ### ⚠ Phase 17 added a beat, and it is probably the strongest one
>
> **Hiring an agent on camera.** Click `+ add agent` in the primary window, type a name, pick
> a character, hit `spawn` — and the desk appears on the *secondary* window's floor, seated
> and named, with nobody touching it. It is the clearest single proof in the product that this
> is one live shared board, and it is far more legible than three matching numbers.
>
> `rehearse.py` does **not** cover it — that harness predates hiring and still drives the
> Phase 2–8 sequence. `ws_smoke.py` section 26 covers it fully against deployed AWS, so the
> mechanism is verified; what has not been rehearsed is the *timing* of doing it on camera.
> Run through it once before a take.
>
> The narration below still describes the old two-desk board. Re-read it against what is
> actually on screen — the floor now has up to four desks, people stand *beside* an agent's
> desk rather than sitting at it, and "agent slots" are "desks" everywhere in the UI.

### 0:00–0:25 · The problem

Talking over the three windows, before touching anything.

> Uber burned through its 2026 AI budget in four months. 79% of enterprises had overruns last
> year; only 36% have any real-time control. Teams share AI agents with no visibility, no
> fairness, and no way to stop a single heavy task draining the month. Operating systems solved
> this for CPU fifty years ago — scheduling, quotas, fair queueing. HiveOS applies that to a
> team's shared AI compute.

If asked how this differs from a local agent harness: **that governs one developer's own CLI
agents on their own machine; this is a cloud governance layer for a team sharing one budget.**

### 0:25–0:45 · Three browsers, one workspace

Click once on the **workspace floor** in each window, so each marker visibly moves on the other
two screens. This is the cheapest possible proof that the three windows are one live board —
much stronger than pointing at three identical numbers, which a viewer could assume were
screenshots.

> Three people, one workspace, one budget. Two agent rooms on the floor — Ada, who takes
> engineering work, and Iris, who researches — and a waiting area between them and us. Same
> meter, same queue, same rooms, on every screen, live. When I move here, it moves there.

Keep it to one click each — the floor is the opening handshake, not the point of the demo. The
nameplates are legible at recording size, so the agents introduce themselves; do not stop to
read them out, and do not narrate the floor plan. It pays off twice in the next two beats and
explaining it up front spends that twice.

### 0:45–1:30 · The queue moment `[~1s of product time]`

1. **Alice** picks **Ada** and requests an agent with the prompt:
   ```
   remember: deploy window = Friday 16:00 UTC
   ```
   → Ada's desk goes BUSY on **all three** screens *(rehearsed: 282–310 ms)*

2. **Bob** picks **Iris** — any prompt, e.g. `summarise yesterday's incident review`
   → Iris's desk goes BUSY. Both desks now full.

3. **Charlie** requests an agent with:
   ```
   when is our next deploy?
   ```
   → Charlie gets **queue position 1** — and on all three screens he **walks into the waiting
   area and stands there**, captioned `queued #1`.

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

### 1:30–2:15 · The memory moment `[~10s of product time]`

This runs itself. Alice's task finishes, and three things happen in sequence — let them land.

1. A **toast** fires on all three screens and Alice's fact appears in **team memory**,
   attributed to her — this lands as her task *starts*, so give it a beat before the rest
2. Her slot frees → **Charlie is auto-dispatched into it** *(rehearsed: 64–84 ms)*. Watch the
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

### 2:15–2:45 · Where AWS fits

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
charged in advance, and the UI clamps. Rehearse it with `python scripts/rehearse.py --ceiling`.

**1600, and this number has moved twice.** 60 when the agent was stubbed (~58 a token a task),
500 once a real model call landed (~200–400), 1600 now the model has tools (~700–1,100). It
tracks the cost of a task; if that changes again, this has to follow or the climb stops being
watchable. Re-checked after Phase 16 and left at 1600: a plain task is ~700, so two land and the
third is still refused.

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
