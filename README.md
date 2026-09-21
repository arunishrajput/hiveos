# HiveOS

**A cloud-deployed office where a team hires and runs a floor of AI agents together.** You
watch them work at their desks in real time, and the whole office runs on one shared,
server-enforced token budget.

> HiveOS is Munder Difflin for teams, in the cloud — hire a floor of AI agents, watch them
> work, and the whole office runs on one enforced budget.

Teams sharing AI agents have no visibility into usage, no fairness mechanism for access, and no
real-time governance over token spend — one heavy agentic task can drain a monthly budget in
minutes and nobody sees it happen. Operating systems solved this for CPU fifty years ago with
scheduling, quotas, and fair queueing. HiveOS applies that abstraction to team AI compute, and
then puts it somewhere you can actually look at it: a floor, with desks, with agents at them.

Built for the **First Commit** hackathon (WeMakeDevs × AWS), Ship It track.

**Live URL:** **https://main.dbavt8jr66qxx.amplifyapp.com** — opens cold, no setup, no sign-in.
The front page explains the product; the office itself is one click behind it, at
[`/#/workspace`](https://main.dbavt8jr66qxx.amplifyapp.com/#/workspace).

**Demo video (2:38):** **https://www.youtube.com/watch?v=VBSuDCQa4y4** — the problem, then the
deployed board running a task, queueing, enforcing the ceiling and hiring an agent, then the
architecture and where AWS fits. `SUBMISSION.md` has the timestamp map.

![The HiveOS office — three agents on the floor, one shared meter, a real answer priced in tokens](docs/office.png)

---

## What it does

**The floor.** A workspace is an office you walk into. Agents sit at desks; the people who
asked for them stand beside them. A desk lights up when its agent is working, and the person
who asked walks over to it — live, on every screen at once, not just the screen that clicked.

![Ada working for alice — her desk lit, alice walked over, a fact saved to team memory](docs/working.png)

**Staffing it.** A new workspace opens with two agents — Ada, who takes engineering work, and
Iris, who researches. Any member can hire more, up to four: name them, give them a role and a
character, and brief them with a persona that becomes their system prompt. They walk onto the
floor and take a desk. Dismiss them and the desk goes with them.

![Hiring an agent — identity, workspace, engine, briefing](docs/hire.png)

**The governance underneath.** This is the part that was the whole product before the office
was built around it, and none of it went away:

- A team shares one **token budget**, and the meter is **identical on every member's screen**
- The budget is an **enforced ceiling, not a gauge** — the server refuses to call the model
  once the workspace is at its limit, and not one token is spent past it
- Asking for a specific agent is a **preference, not a booking** — if Ada is busy, another
  free agent takes the work, and the reply and the ledger both say who actually ran it
- When every desk is busy, further requests **queue** with a real position, visible team-wide
- A freed desk **auto-dispatches** the next queued task — nobody has to re-ask
- A **per-person spend ledger** records who spent what, and which agent ran it

**What the agents share.** Team memory: a fact one member saves is loaded into the next
member's agent before their task starts, via model-invoked tools rather than string-stuffing.
An agent can also **hand work to another desk** when it is a better fit — the envelope crosses
the floor, the receiving agent answers, and both legs bill to the same budget under one task
id. Bounded to one hop, so a chain cannot ping-pong through the budget.

**Per workspace.** Each is fully isolated — its own budget, agents, queue, memory and ledger —
created on first join with no provisioning step, and optionally **passphrase-protected** with
an owner who can set the budget or delete it.

**Worlds.** The same board can wear a different place. A picker — in the title bar on the floor,
and in the nav on the front page — swaps the whole workspace between **Paper Office** (warm
daylight and cream tiles), **Night Watch** (a deck under a star field, lit by its instruments),
**Enchanted Forest** (hollow stumps and carved benches under a dappled canopy), **Reef Station**
(research domes on the seabed, under caustics from a surface far above), **Alien Colony** (command
modules on landing pads under two moons), **Cloud City** (a sky harbour of platforms and pavilions,
above the cloud line) and **Arctic Base** (cabins and antenna masts on packed snow, under a winter
aurora) — same sockets, same scheduler, same rows in DynamoDB, re-dressed.
It is a personal setting, stored in your own browser, and it changes nothing anyone else sees.

A world is not a colour scheme and it is never allowed to change what anything *means*. The busy
blue, the queued ochre, the budget jade and the over-budget red carry the whole governance story,
so each is re-tuned for its world's surfaces and **measured** — every state hue clears 4.5:1
against all eight of that world's surfaces — and none is ever reassigned. What does change is the
form: a working desk is a lit monitor in the office, a lit observation dome on the night deck, and
a lit antenna array on a command module. Even the handoff re-dresses — the paper envelope becomes
a transmission pulse on the colony, on the same path, at the same 1100 ms, with the same
screen-reader announcement.

### Status

Everything above is live, deployed and verified against real AWS. Last recorded full runs:
**109/113** end-to-end checks (`scripts/ws_smoke.py`), **27/27** unit tests, and the demo
sequence **15/15**, twice unattended (`scripts/rehearse.py`). The agents are real and the token
counts are the provider's reported usage, not estimates.

> The four non-passing checks are all the same one: they assert the connection table is *empty*,
> and the public URL now has real visitors on it during a run. The invariant itself is verified
> directly — connections opened by the harness are gone from DynamoDB the moment they close.

> **One honest note: model inference is the only thing not running on AWS.** Amazon Bedrock is
> blocked account-wide here — `us-east-1`, `us-west-2` and `ap-south-1` all refuse, Marketplace
> models with `INVALID_PAYMENT_INSTRUMENT` and first-party Amazon Nova against a per-day token
> quota of zero that reports `adjustable=False`. 42 of 43 quotas sit at zero. That is an
> account-level restriction, not a setting.
>
> Inference therefore calls out to Groq (`openai/gpt-oss-120b`) over HTTPS. The API Gateway
> WebSocket, both Lambdas, SQS, DynamoDB and Amplify are unchanged — one outbound HTTP call is
> the entire difference, and it touched exactly one function.
>
> If the model is ever unreachable the workspace still answers, from composed text, and flags
> those counts `estimated` everywhere they appear — including on `state_snapshot`, so a browser
> loading cold is told too. A degraded answer never gets laundered into a billed-looking meter.

See `PROGRESS.md` for the full evidence and `ARCHITECTURE.md` decision 7 for the reasoning.

---

## Architecture at a glance

```
Browser ──wss──► API Gateway WebSocket ──► Router Lambda ──► DynamoDB
                                                │                 ▲
                                                ▼                 │
                                               SQS ──► Agent Runner Lambda ──► Groq
```

One DynamoDB table holds everything, partitioned by workspace: the roster (`AGENT#`), the
queue (`QUEUE#`), team memory (`MEMORY#`), the ledger (`TASK#`) and live connections (`CONN#`).
React frontend on Amplify Hosting. Everything serverless, scaling to zero.

Full detail and the reasoning behind each choice: **`ARCHITECTURE.md`**.

---

## Documentation map

Read in this order:

| File | Read it for |
|---|---|
| **`CLAUDE.md`** | How to work on this project. **Start here.** |
| **`PROGRESS.md`** | Where things stand right now |
| **`BUILD_PLAN.md`** | The phases and what each must deliver |
| `PRD.md` | What the MVP is and is not |
| `ARCHITECTURE.md` | System design and every rejected alternative |
| `CONTRACT.md` | Schemas, protocols, and interfaces that must not drift |
| `DEPLOYMENT.md` | AWS setup, deploy commands, manual actions, troubleshooting |
| `DEMO.md` | The recording run sheet — checklist, beats, fallbacks, and the as-recorded scene map |
| `SUBMISSION.md` | The hackathon writeup, with the video's timestamp map |

**Fastest path to understanding:** `README.md` → `PROGRESS.md` → `ARCHITECTURE.md`.

---

## Setup

Requires: AWS CLI (configured), AWS SAM CLI, Docker (running), Node 20+, Python 3.11+.

```bash
brew install aws-sam-cli
aws configure                 # see DEPLOYMENT.md, Manual Action 1
```

The agents need a model API key before they will answer. It is read at runtime from SSM
Parameter Store and never stored in this repository:

```bash
aws ssm put-parameter --name /hiveos/groq-api-key --type SecureString \
  --value 'gsk_...' --region us-east-1 --overwrite
```

Get a free key at <https://console.groq.com> (no card required). Without it the office still
runs — every task falls back to composed text flagged `estimated`.

---

## Deploy

```bash
# Backend — always --use-container; local Python is newer than the Lambda runtime
sam build --use-container
sam deploy

# Frontend — resolves the WebSocket URL from the stack, builds, zips, publishes
./scripts/deploy-frontend.sh
```

`deploy-frontend.sh` is idempotent: it reuses the existing Amplify app and branch rather than
creating duplicates, and it fails loudly if the WebSocket URL did not make it into the bundle.

For local development against the deployed backend:

```bash
cd frontend
npm install
VITE_WS_URL="$(aws cloudformation describe-stacks --stack-name hiveos \
  --query "Stacks[0].Outputs[?OutputKey=='WebSocketURL'].OutputValue" --output text)" \
  npm run dev
```

Stack outputs (WebSocket URL, table name, queue URL):

```bash
aws cloudformation describe-stacks --stack-name hiveos \
  --query 'Stacks[0].Outputs' --output table
```

---

## Verify

Check that the deployed backend actually behaves — multiple live clients, fan-out, hiring,
handoff, the ceiling, and stale-connection cleanup, all against real AWS:

```bash
pip install websockets
./scripts/reset-demo.sh                # clean floor, SQS drained, Lambdas warm — and verified
python3 scripts/ws_smoke.py            # backbone, scheduler, memory, ceiling, fairness,
                                       # isolation, passphrases, admin, hiring
python3 scripts/rehearse.py --takes 2  # the recorded demo sequence, unattended, beat-timed
```

The unit tests cover the desk-release path and need no AWS, but they do import `botocore`,
so they need `boto3` present — which a bare system Python usually does not have:

```bash
python3 -m venv .venv && .venv/bin/pip install boto3 pytest
.venv/bin/python -m pytest tests/      # 14 passed
```

> **`python3`, not `python`** — this machine has no `python` on `PATH`.

Close any browser tab pointed at the deployed URL first — the connection-leak checks assert the
table holds no `CONN#` rows, so a live browser fails four of them. `reset-demo.sh` warns you
when it finds live rows. The public URL has real visitors, so this is no longer entirely in
your control; when those four are the only failures, verify the invariant directly instead.

`ws_smoke.py` asks whether the system is **correct**; `rehearse.py` asks whether the sequence
about to be **recorded** works, in order, inside the time available, and times every beat.

Full procedure, verification steps, and troubleshooting: `DEPLOYMENT.md`.

---

## Repository layout

```
backend/
  router/            Connection lifecycle, claiming, queueing, hiring, broadcast
  agent_runner/      SQS consumer, agent execution, token accounting, dispatch
  shared/agents.py   The roster as data — hire, dismiss, personas, the MAX_AGENTS cap
  shared/scheduler.py  Desk claiming, the fair queue, auto-dispatch
  shared/memory.py   Team memory — MEMORY# rows, context loading, memory_updated
  shared/llm.py      The one seam the model call lives behind
  shared/            Broadcast helper, task history, DynamoDB access
frontend/
  src/useHive.js     WebSocket client — owns all board state, reconnect, re-sync
  src/App.jsx        Entry gate, app shell, routing
  src/components.jsx The floor, the quota strip, the inspector, the roster strip
  src/addagent.jsx   The four-step hire form
  src/landing.jsx    The front door at `/`
  src/sprites.js     The pixel characters, derived from a marker string
tests/               Unit tests for the slot-release path — no AWS, no moto
scripts/             Seeding, demo reset, smoke test, demo rehearsal, frontend deploy
template.yaml        SAM — all AWS infrastructure
```

---

## Current MVP scope

**Built and deployed:** a shared floor you staff · **hiring and dismissing agents** with names,
characters and briefed personas · shared token meter · **fair queueing** with live position ·
auto-dispatch · shared team memory via **model-invoked tools** · **agent-to-agent handoff**
billed as one job across two desks · **per-person spend ledger** naming the agent that ran each
task · enforced budget ceiling · workspace isolation and passphrases · team chat · public URL.

**Not built:** user accounts. Workspaces can be passphrase-protected and have an owner, but
there is no identity behind a display name — administration hangs off a secret the creator
holds, not off who anyone claims to be. Also unbuilt: any retention policy on the task ledger.

**Deliberately excluded:** authentication, game-engine graphics, token-level preemption,
calendar/email integrations, a per-agent model picker. See `PRD.md` and `ARCHITECTURE.md` for
why each was rejected.

> **On the reference.** Munder Difflin spawns local PTY processes running your own CLI agents
> against folders on your disk. A Lambda behind a public URL cannot attach to a judge's
> terminal, so HiveOS takes the *interaction model* and never the mechanism: the inspector's
> tabs are bound to data this board actually holds, and there is no fake terminal anywhere.

---

## Built with

AWS Lambda · API Gateway WebSocket · DynamoDB · SQS · SSM Parameter Store · AWS SAM ·
Amplify Hosting · React + Vite

Model inference runs on Groq because Amazon Bedrock is blocked account-wide on this account —
see **Status** above.

Developed with Claude Code as the implementation assistant.
