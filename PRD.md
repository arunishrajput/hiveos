# PRD.md — HiveOS product specification

What HiveOS is, who it is for, what it must do, and what it deliberately does not do.
`ARCHITECTURE.md` explains how it is built; `CONTRACT.md` is the interface it must not drift
from.

---

## Product

A cloud-deployed office where a team hires and runs a floor of AI agents together — you watch
them work at their desks in real time, and the whole office runs on one shared, server-enforced
token budget. Built on AWS.

**The one-sentence test.** If someone can say *"HiveOS is a floor of AI agents your team hires,
watches and runs on one enforced budget"* — the product landed. Every implementation decision
should serve that sentence.

> **The framing changed on 2026-09-19, and deliberately.** It used to be *"the OS scheduler for
> your team's shared AI budget"*, and the scheduler was the headline. The scheduler, the fair
> queue and the enforced ceiling are all still here and all still load-bearing — they moved from
> being the product to being the governance layer *inside* it. The reason is that a queue is a
> thing you explain and an office is a thing you see.

---

## Problem

Teams sharing AI agents have **no visibility into usage, no fairness mechanism for access, and
no real-time governance over token spend**. One heavy agentic task can burn a team's entire
monthly budget in minutes — and nobody can see it happen while it happens.

This is verified, not assumed:

- Uber burned its entire 2026 AI coding budget in four months *(Fortune / The Information, May 2026)*
- One internal Uber demo cost $1,200 in two hours
- 79% of enterprises had AI cost overruns in the past 12 months *(DoiT / Sapio Research, Feb 2026)*
- Only 36% of organisations have any token or usage controls *(PointFive Research, Jul 2026)*
- Agentic workflows consume 10–30× more tokens than simple queries *(Forbes Tech Council, Aug 2026)*

**The insight.** Operating systems solved exactly this for CPU fifty years ago: process
scheduling, time slices, resource quotas, fair queue allocation. HiveOS applies that abstraction
to team AI compute — making invisible resource allocation visible and fair.

---

## Target user

Remote or hybrid teams of 3–6 people who share AI agent access. The default roster is a software
team (an engineer and a researcher), but the product is general-purpose, not coding-only — an
agent's role and persona are set when it is hired.

---

## Core user journey

1. Open the public URL. Pick a name. Land on a floor.
2. See the office: Ada and Iris at their desks, the team's token meter above them — **identical
   on every screen**.
3. Pick a desk and send that agent a task. It goes BUSY on everyone's screen and the meter moves
   as it works.
4. **Hire a third agent.** Name it, pick its character, write its briefing. It appears at a desk
   on *everyone's* floor, with no refresh.
5. Give the new agent work. A third member asks while every desk is busy → stands in the waiting
   area at "queued #1".
6. Tell an agent to remember a team fact. A badge appears on every screen.
7. A desk frees → the queued member walks into the room and is auto-assigned → their agent
   already knows the team fact.

---

## Features

### Shipped and deployed

| Feature | Behaviour |
|---|---|
| Team workspaces | Any number of isolated workspaces, each with multiple concurrent members. `alpha` is only the default |
| A floor you staff | Two agents to start, up to four; hire with a name, role, character and persona; dismiss to free the desk |
| Real-time token meter | `tokens_used / token_budget`, identical across all browsers, updates without refresh |
| **Enforced budget ceiling** | Server-side refusal to invoke the model at 100% — a real control, not a gauge |
| Fair queue | Claims made while every desk is busy wait in order, by fairness rather than arrival |
| Queue position display | "queued #1", updated live for the whole team |
| Auto-dispatch | A queued task is assigned automatically the moment a desk frees |
| WebSocket sync | Desk state, token count, queue, roster and memory pushed to all connected clients |
| Shared team memory | An agent saves a fact; the next member's agent loads it automatically, through model-invoked tools |
| Agent-to-agent handoff | An agent may pass a task to a better-suited desk — one request, two agents, one bill, bounded to one hop |
| Per-person spend ledger | Who spent what, and which agent actually ran it |
| Workspace passphrases | Optional PBKDF2-verified passphrase and an owner who can set the budget or delete the workspace |
| Worlds | Nine looks for the same board, switched per-viewer with no reload and no change to meaning |
| Public deployment | Public HTTPS URL, opens cold with zero setup |
| GoneException handling | Stale WebSocket connections cleaned up on every broadcast |

### Future work

User accounts and identity · a retention policy on the task ledger · priority queue bump ·
per-user budgets · usage analytics across workspaces · an agent marketplace

### Out of scope — never build

Phaser.js or any game engine · tilemaps, physics, pathfinding · Google Calendar / Gmail / OAuth ·
CPU-style token preemption mid-generation · multiple DynamoDB tables · mobile app · voice or
video · multi-team analytics

Each was considered and rejected with reasons recorded in `ARCHITECTURE.md`.

---

## Functional requirements

- A member may hold at most one agent desk at a time.
- Desk claims are atomic — two simultaneous claims never both succeed on the same desk.
- Token accounting is atomic and never lost to a race between concurrent agent runs.
- Queue ordering is fair, resolved at dispatch rather than by arrival timestamp alone.
- Every state change is broadcast to all connected workspace members.
- Team memory persists across sessions and is loaded into every new agent task.
- The model is not invoked when the budget is exhausted.
- A floor can never be emptied of its last agent.

## Non-functional requirements

- **Reliability outranks feature count.** One feature that runs beats five that almost do.
- State changes visible across browsers in under ~2 seconds.
- The public URL works from a cold browser with no local setup.
- Everything serverless, scaling to zero — no always-on resources.
- No secrets in the repository.
- Every state colour clears 4.5:1 against every surface the world it sits in paints.

---

## Acceptance criteria

All of the following are met on the deployed system, and each is checked by a runnable gate
rather than by inspection — see **Verify** in `README.md`.

- The public URL loads and shows live shared state across multiple browsers
- Desk claim, release and auto-dispatch work end to end
- The ceiling refuses the model at 100% and spends nothing past it
- A fact saved by one member reaches the next member's agent
- A handoff bills both legs to one budget under one task id
- Workspaces are isolated from one another, including under a passphrase
- Every world clears the contrast bar at both common framings
