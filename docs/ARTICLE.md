# Your Team's AI Budget Needs a Scheduler, Not a Dashboard

**I built a cloud office on AWS where a team hires a floor of AI agents, watches them work in real time, and shares one server-enforced token budget. Here is what the build actually taught me — including the part where the hard problem turned out to have nothing to do with AI.**

---

## The $1,200 demo

Uber burned through its entire 2026 AI coding budget in four months. One internal demo cost $1,200 in two hours. *(Fortune / The Information, May 2026.)*

That number is not an outlier, it is the pattern. 79% of enterprises reported AI cost overruns in the past twelve months *(DoiT / Sapio Research, Feb 2026)*. Only 36% of organisations have any token or usage controls at all *(PointFive Research, Jul 2026)*.

The instinct is to reach for a dashboard. I think that instinct is wrong, and the reason is in the numbers above: two hours. A dashboard reports yesterday. By the time a chart turns red, the money is gone, the agent has finished, and you are reading a receipt.

The gap is not reporting. The gap is **real-time, shared, enforced** governance — four questions a dashboard structurally cannot answer:

- Who is using the agents *right now*?
- What is it costing, on a number everyone sees at the same time?
- Whose turn is next?
- And what actually happens when the budget runs out?

That last one is the whole thing. If the answer is "a notification fires," you do not have a budget. You have a gauge.

---

## We already solved this, in 1970

Multiple users contending for one expensive, finite compute resource is not a new problem. It is *the* operating systems problem, and it was solved fifty years ago with three ideas: **scheduling**, **quotas**, and **fair queueing**.

Your OS does not email you when a process is using too much CPU. It preempts it. `nice` is not a chart.

HiveOS applies that abstraction to a team's shared AI compute. Agents are a scheduled resource. Tokens are a quota. Waiting is a queue with a real position in it. The ceiling is not advisory — the server refuses to call the model, and not one token is spent past the limit.

The part I got wrong at first was thinking that was the product. It is the *mechanism*. A queue is a thing you have to explain; an office is a thing you can just look at.

---

## So I built an office

A workspace is a floor you walk into. Agents sit at desks. The people who asked for them stand beside them. A desk lights up when its agent is working — live, on every member's screen at once, not just the screen that clicked.

![The HiveOS office — three agents on the floor, one shared meter, a real answer priced in tokens](https://raw.githubusercontent.com/arunishrajput/hiveos/main/docs/office.png)

You staff it yourself. A new workspace opens with two agents — Ada, who takes engineering work, and Iris, who researches — and any member can hire more: name them, give them a role and a character, and brief them with a persona that becomes their system prompt. They walk onto the floor and take a desk. Dismiss them and the desk goes with them.

![Hiring an agent — identity, workspace, engine, briefing](https://raw.githubusercontent.com/arunishrajput/hiveos/main/docs/hire.png)

The governance is all still there, it just moved inside the room:

- One shared **token budget**, and the meter is **identical on every member's screen**
- The budget is an **enforced ceiling** — at 100% the server will not invoke the model
- Asking for a specific agent is a **preference, not a booking** — if Ada is busy, another free desk takes the work, and the reply says who actually ran it
- When every desk is busy, requests **queue with a real position**, visible team-wide
- A freed desk **auto-dispatches** the next task — nobody re-asks
- A **per-person ledger** records who spent what, and which agent ran it

![Ada working for alice — her desk lit, alice walked over, a fact saved to team memory](https://raw.githubusercontent.com/arunishrajput/hiveos/main/docs/working.png)

Agents also share **team memory**: a fact one person saves is loaded into the next person's agent before their task starts. And an agent can **hand work to another desk** when it is a better fit — one request, two agents, **one bill** under a single task id, bounded to exactly one hop. An unbounded chain of model decisions is an unbounded way to spend a shared budget.

---

## How it is put together

Everything is serverless and scales to zero. Sixteen resources, one SAM template, one CloudFormation stack.

![HiveOS architecture — Amplify, API Gateway WebSocket, two Lambdas, DynamoDB, SQS, SSM](https://raw.githubusercontent.com/arunishrajput/hiveos/main/docs/architecture.png)

| Service | Job |
|---|---|
| **API Gateway (WebSocket)** | The live board. Every member holds an open socket; the server fans out every state change |
| **Lambda ×2** | Router owns connections, claims and queueing. Agent Runner executes tasks. Split so model latency never blocks connection handling |
| **DynamoDB** | Single table, partitioned by workspace. Conditional writes claim desks; atomic counters bill tokens |
| **SQS** (+ DLQ) | Durable, at-least-once handoff of every agent task |
| **Amplify Hosting** | The React frontend and the public URL |
| **SSM Parameter Store** | The model API key as a SecureString, read at runtime — never in the template, the stack, or git |
| **SAM / CloudFormation** | All infrastructure in one `template.yaml` |
| **AWS Budgets** | A spend backstop behind the in-app ceiling |

---

## Three decisions that carry the whole product

### 1. The queue lives in DynamoDB, not in SQS

This is the one I expected to get pushback on, so let me argue it properly.

The obvious approach is to gate on SQS itself: set the Agent Runner's reserved concurrency equal to the desk count and let waiting tasks physically sit in the queue. It is elegant, it is one config line, and I rejected it.

It buys you Lambda throttling behaviour, visibility-timeout tuning, and `maxReceiveCount` → DLQ risk under *exactly* the conditions a busy floor creates. But the disqualifying problem is smaller and more stubborn than any of those: **SQS exposes approximate depth, not "where am I in line."** For a product whose entire promise is that waiting is visible and fair, "roughly a few ahead of you" is not an answer.

So the Router claims a desk with an atomic conditional write. If the claim fails, it writes a `QUEUE#<timestamp>` item, and position is a trivial count of earlier rows. Deterministic, race-free, and position display comes out free.

```python
table.update_item(
    Key={"PK": team_pk(team), "SK": f"AGENT#{slot_id}"},
    UpdateExpression="SET #s = :busy, #u = :user, claimed_at = :now",
    ConditionExpression="#s = :idle",          # <- the entire scheduler
    ...
)
```

Two people clicking the same desk in the same second: one wins, one gets `ConditionalCheckFailedException` and a queue position. No lock, no coordinator, no race.

SQS still does real work — every running task is a durable, DLQ-backed message. It is just not where the line lives.

![One request end to end — the atomic claim, the fork, and auto-dispatch](https://raw.githubusercontent.com/arunishrajput/hiveos/main/docs/lifecycle.png)

### 2. The ceiling is checked one line before the model call

Not at claim time. This looks like a detail and it is a correctness bug waiting to happen: a task can sit in the queue while the tasks *ahead* of it burn what was left. Claim time is simply the wrong moment to decide, because the answer can change before the task runs.

```python
used, budget = state.budget_state(team)
if not budget or used < budget:
    return False          # proceed
# otherwise: no model call, zero tokens, and the ledger records the refusal
```

A refusal gets written to the ledger with `tokens=0` and a `REFUSED` status. That row is the most telling thing in the product — it is the artifact that proves the ceiling is a control rather than a gauge.

This is also the spend guard for a public, unauthenticated URL, which is exactly why it never gets disabled to make a demo work.

### 3. Every token is an atomic `ADD`

```python
UpdateExpression="ADD tokens_used :n"
```

Never read-then-write. Two agents finishing simultaneously would silently lose an update, and the number on everyone's screen would quietly drift away from the truth. On a product about token accounting, that is not a rounding error — it is the whole claim falling over.

---

## The hard part was not the AI

It was making three browsers agree on one number. Every genuinely painful bug in this build was a distributed-state bug wearing a costume.

### Frame ordering is a correctness property, not a detail

`claim_agent` dispatched to SQS *before* broadcasting the BUSY state. A fast-failing task could therefore post its reply ahead of its own BUSY frame — the client would apply BUSY *after* the release, and show a desk stuck busy for the rest of the session.

It failed about half the time, which is the worst failure rate there is: too often to ignore, too rarely to reproduce on demand.

> **The rule that came out of it:** a frame describing committed state must go out *before* the work that could produce the next frame.

### `73.5` was lying to me

Avatar moves were silently failing in production. `Decimal(24.92)` built from a float carries its full binary expansion, and boto3 raises `decimal.Inexact` rather than rounding.

My test passed. It passed because I had picked `73.5` and `21.25` as "obviously fractional" coordinates — and both are exactly representable in binary floating point. Only a real mouse click ever produced one that was not.

The failure mode was the nastiest kind for this product: the mover's optimistic UI still moved them, so they were standing somewhere **nobody else could see**. The board was lying, confidently, to everyone except the person who caused it.

> Choosing awkward test data is a skill. Tidy numbers are a trap.

### A green measurement can describe a broken screen

A new panel overflowed the window, so I pinned the board to the viewport with `overflow: hidden`. My check — `scrollHeight === innerHeight` — went green.

It was green because the layout had been *amputated*. Two panels were not merely off-screen, they were unreachable. A screenshot showed it in one second.

> Verify the artifact, not the proxy.

### The client that matters most reads exactly one frame

Twice I shipped something that was correct for a *watching* client and wrong for a *joining* one. The token-provenance flag rode only on live update frames, so a browser opening the URL cold — **which is every new teammate** — saw an unlabelled number. Same shape of bug erased a queue ETA 500 ms after it appeared, because the snapshot did not carry it.

Every check in this repo runs against deployed AWS for this reason. A zero exit code proves a command succeeded, not that the system behaved.

Measured against the deployed stack, not localhost — click-to-paint across two separate browsers, sampled at 20 ms in the *observing* browser:

| | |
|---|---|
| A claim reaching a second browser | **282 ms** |
| Auto-dispatch visible after a desk frees | **187 ms** |
| An avatar move painted on a second browser | **270–294 ms** |
| End-to-end checks against real AWS | **113/113** |

---

## The honest note: Bedrock was blocked account-wide

Model inference is the one thing in this project not running on AWS, and I would rather say that plainly than bury it.

**Amazon Bedrock is blocked account-wide on this account.** 42 of 43 per-day token quotas sit at zero and are marked `adjustable=False` — so they cannot be raised even by request. That includes first-party Amazon Nova, which needs no Marketplace subscription and no payment instrument.

I lost real hours assuming this was my problem: permissions, model access, a region thing, a config thing. It was none of them. Third-party models failed with `INVALID_PAYMENT_INSTRUMENT`; adding a valid card fixed that genuine and entirely separate failure, and Nova still returned `ThrottlingException: Too many tokens per day` against a quota of zero. I re-verified in `us-east-1`, `us-west-2` and `ap-south-1` before accepting it.

What finally resolved the diagnosis was reading 1,123 service quotas and noticing that **two different vendors were failing identically** — which ruled out everything in my codebase in a single step.

> **Diagnose the account, not the code.** When two independent things fail the same way, the cause is underneath both of them.

So inference calls out to Groq (`openai/gpt-oss-120b`) over one HTTPS request. Everything else — the WebSocket API, both Lambdas, SQS, DynamoDB, SSM, Amplify, SAM — is AWS.

I have come to think this is the right architecture rather than a retreat, for a reason the product itself argues: **a governance layer that only works against one vendor's models is a worse governance layer.** The scheduler does not care where a token was spent, only that it was counted. The swap proved it concretely — it touched exactly one function plus a new 130-line client, and nothing about the queue, the slot state machine, the atomic accounting or the enforced ceiling moved at all.

And the counts are real: `tokens_used` is the provider's reported `total_tokens`, not an estimate. If the model is ever unreachable the workspace still answers from composed text, but every frame carrying such a count sets an `estimated` flag, the UI says so, and the flag is sticky. A degraded answer never gets laundered into a billed-looking meter.

---

## What I would tell you to steal

1. **A conditional write is a scheduler.** If you are reaching for a lock or a coordinator to arbitrate a shared resource, try one `ConditionExpression` first. The loser of the race gets a clean, typed exception you can build a queue position out of.
2. **Check quotas at the moment of spend, not the moment of request.** Anything that waits in a line can have its assumptions invalidated while it waits.
3. **Order your broadcasts before your side effects.** In any fan-out system, a frame describing committed state must precede the work that generates the next one.
4. **Test the frames arriving at an observing client**, not the values your function returns. Both of my worst bugs were invisible to unit tests and obvious the first time I asserted on a second browser.
5. **Ship the thing that survives being cut.** I built the deployed public URL *before* the model integration, against my own plan's ordering. That inversion is the reason there is a submission at all.

---

## Try it

- **Live, no sign-in, opens cold:** <https://main.dbavt8jr66qxx.amplifyapp.com>
- **Straight to the office:** <https://main.dbavt8jr66qxx.amplifyapp.com/#/workspace>
- **Demo video (2:38):** <https://www.youtube.com/watch?v=VBSuDCQa4y4>
- **Source:** <https://github.com/arunishrajput/hiveos>

Open it in two browser windows side by side. Ask an agent something in one and watch the other. That is the whole pitch in about four seconds.

---

*Built solo in about 72 hours. Claude Code was the implementation assistant; the repository itself was its memory — a `CLAUDE.md` defining a source-of-truth hierarchy where deployed AWS state outranks documentation, so a fresh session after a context reset reads three files and knows the phase, the blocker, and the next step.*
