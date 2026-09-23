# CLAUDE.md — How to work on HiveOS

Conventions, guard rails and workflow for anyone — human or agent — changing this codebase.
Read this, then `README.md`, then only the docs the change actually needs: `CONTRACT.md` before
touching the schema or the protocol, `DEPLOYMENT.md` before any AWS work, `ARCHITECTURE.md`
before proposing a new component or dependency.

---

## The project is complete and deployed

HiveOS is finished, live, and in a steady state. There is no roadmap queued and nothing is owed
to anyone. **Every change from here is an improvement to something that already works**, and the
bar it has to clear is that it does not break what is already there.

**"Start the next phase" has nothing to take.** The build ran in phases and all of them shipped;
the record is in `docs/internal/PROGRESS.md` and `docs/internal/BUILD_PLAN.md`, kept as history
of how things stood when each closed. Those are **not** live to-do lists, and a line in one is
never a reason to reopen closed work. If you are asked to start a phase, say plainly that the
plan is finished rather than inventing work.

**Where it stands.** Nine looks in the picker — Paper Office (the default), Night Watch,
Enchanted Forest, Reef Station, Alien Colony, Cloud City, Arctic Base, Desert Outpost, Ancient
Ruins. A CSS cross-fade carries the board between any two, Random World picks one you are not in,
the picker is keyboard-correct, and all nine pass a 36-cell contrast matrix measured on rendered
pixels. Paper Office is the default and is byte-for-byte unchanged from the day it shipped.

**Open items are recorded, not queued.** `docs/internal/PROGRESS.md` → *Known issues and
discoveries* is the list, and each entry says whether it was fixed, closed, or left deliberately.
Do not start on one uninvited.

---

## Project identity

**HiveOS** is a cloud-deployed office where a team hires and runs a floor of AI agents together —
everyone watches them work at their desks in real time, on one shared, server-enforced token
budget. Built on AWS.

**One sentence:** hire a floor of AI agents, watch them work, and run the whole office on one
enforced budget.

Teams sharing AI agents have no visibility into usage, no fairness mechanism for access, and no
real-time governance over token spend. One heavy agentic task can drain a monthly budget in
minutes and nobody sees it happen. Operating systems solved this for CPU fifty years ago:
scheduling, quotas, fair queueing. HiveOS applies that abstraction to team AI compute.

> **The product pivoted on 2026-09-19.** It was "a team queues for two shared agent slots" and
> the scheduler was the headline. It is now a floor you staff: agents are hired, named and
> briefed, and they sit at desks. The scheduler, the fair queue and the enforced ceiling did not
> go anywhere — they became the governance layer inside the office rather than the pitch.

---

## Source of truth

When sources disagree, higher wins:

1. **Deployed AWS state** — what actually exists and runs
2. **Repository code** — what is actually implemented
3. **`CONTRACT.md`** — shared interfaces that must not drift
4. **`PRD.md`** — what the product does and does not do
5. **`ARCHITECTURE.md`** — how the system is intended to fit together
6. **`docs/internal/`** — the build record
7. Other docs
8. **Conversation history** — background, never an automatic override

Never assume documentation is current. On a discrepancy: detect it, determine what actually
exists, determine what was intended, correct the appropriate source, and say so. Escalate when
the gap materially changes scope, security, cost, or core architecture.

---

## Scope control

Touch only what the task asks for. Before implementing anything, ask whether it is in `PRD.md`'s
feature set, whether it unblocks required work, and whether it is needed for the deployment to
keep working. If no to all, it is future work — propose it, do not build it.

Priority order, always:

> **Working deployed software > architectural correctness > feature count > documentation polish**

### Never build

Phaser.js or any game engine · Google OAuth / Gmail / Calendar · CPU-style token preemption
mid-generation · multiple DynamoDB tables · a mobile app · voice or video · an agent marketplace ·
multi-team analytics · Cognito · any AWS service not already in `ARCHITECTURE.md`

Each of these was considered and rejected with reasons recorded in `ARCHITECTURE.md`. Do not
reintroduce them.

---

## AWS workflow

**All infrastructure lives in `template.yaml` and is deployed with SAM.** Never create a
stack-managed resource with a one-off `aws ... create-*` command — CloudFormation owns the
inventory, and side-created resources cause drift and duplicates.

```bash
sam build --use-container      # builds in the Lambda image; local Python would produce
sam deploy                     # wrong-platform wheels. Config lives in samconfig.toml
```

Prefer the AWS CLI for everything else: identity checks, inspecting resources, reading logs,
testing deployed endpoints, verifying deployments.

**Before creating any resource, check whether it already exists.**
`aws cloudformation describe-stacks --stack-name hiveos` is the authoritative answer.

### Deployment is never assumed

A zero exit code is not proof. A deployment is verified only when the deployed system **behaves
correctly**: a real request returns a real response, logs show the expected path, the database
holds the expected item.

**Amplify is in manual-deploy mode** — no build fires on `git push`. A frontend commit is only
live once `./scripts/deploy-frontend.sh` has been run for it. Settle it on the bytes: `curl` the
live `index.html` for its asset hash and compare against `frontend/dist/`.

### Manual actions

Some steps cannot be done from the CLI. When one is required, output exactly this and stop work
that depends on it:

```
MANUAL ACTION REQUIRED

Reason:          <why this is needed>
Location:        <exact AWS Console path>
Steps:           1. ... 2. ... 3. ...
Expected result: <what you should see afterward>
Verification:    <the exact command that confirms it>
Resume by:       <what to say once done>
```

Never write "configure this in AWS." Give the exact path, the exact setting, the exact value.
Continue with anything that does *not* depend on the manual action.

---

## Cost control

The AWS account is a Free Plan with limited credit. Ordinary use costs a few dollars; a runaway
loop does not.

- The token ceiling is **enforced in code** — the Agent Runner refuses to call the model once
  `tokens_used >= token_budget`. This is a product feature *and* a spend guard. Never disable it
  to make something work.
- Keep `max_tokens` low per call.
- An AWS Budget alarm is the backstop. Do not remove it.

---

## Git workflow

Solo maintainer: **work directly on `main`.**

- Commit at meaningful checkpoints, not once at the end of a long change.
- Inspect `git diff` before every commit.
- Push after every commit.
- Never force-push.
- `main` requires one approving review; merges go through `gh pr merge --admin`.

### Never commit

AWS credentials or access keys · API keys or tokens · `.env` files · `samconfig.toml` if it ever
contains secrets · anything under `.aws/` · generated build artifacts (`.aws-sam/`,
`node_modules/`, `dist/`)

Check the diff for these every time. If a secret was ever committed, stop and say so — rotation is
required, not just a revert.

---

## Testing

Test what can break the product:

- **Critical path** — desk claim, queue, dispatch, token accounting, broadcast
- **Integration** — components actually working together against deployed AWS
- **Deployment** — the deployed system genuinely responds
- **Smoke** — the app still starts and the core flow still runs

Do not write tests for coverage numbers. The gates are `pytest tests/` (no AWS),
`npm test` in `frontend/` (no AWS), and `scripts/ws_smoke.py` (against the deployed stack).

Two lessons this suite paid for, both worth keeping:

- **A unit test can agree with the code and both be wrong about the service.** A fake that
  encodes the same misunderstanding as the code passes happily while every real call fails. When
  a test doubles an AWS API, assert the shape that was *measured* against the real service.
- **Diagnose from logs, not from plausibility.** A symptom that reads like a livelock can be a
  serialization bug; one `filter-log-events` call settles in seconds what a day of code reading
  cannot.

---

## Debugging

1. Reproduce it.
2. Read the actual logs (`sam logs -n <fn> --stack-name hiveos --tail`) — do not guess.
3. Find the smallest plausible root cause.
4. Fix that.
5. Re-run the failing verification.
6. Re-run related checks for regressions.

Never rewrite large areas of working code to chase a bug.

---

## Security

Never commit secrets. Never hardcode credentials. Never log credentials or full request bodies
that might contain them. Never disable a security control to make something work. Never delete or
overwrite an AWS resource without understanding what depends on it — and for anything destructive,
explain the intended action and confirm first.

The deployed URL is public and unauthenticated by design. That is an accepted, documented
tradeoff — which is exactly why the server-side token ceiling is mandatory.

---

## Working on the frontend

**Worlds have contracts that are not inferable from the code.** If a world is ever added or
changed, read `docs/internal/BUILD_PLAN.md` → the `## Phases 18–27` intro for the recolour test
and the state-legibility contract, and the findings under Phases 19–27 for the traps. The short
version:

- A world is **not** a colour scheme. If the whole diff is values inside the token block, nothing
  has been built.
- A world may **never** reassign what a colour means. Busy blue, queued ochre, budget jade and
  over-budget red carry the governance story and are re-tuned, never repurposed — and the scenery
  has to be checked against all four, not just the one being worked on.
- **Paper Office is the default and must stay byte-for-byte unchanged.** It is also the *control*
  that tells a world's defect from the floor's: when the frozen default fails a contrast cell
  identically, the cell is base geometry.
- **A contrast number is a claim about the pixels under the glyphs** — not a token table, which
  cannot see a composite.
- A world stylesheet must never set `--walk-top` (the registry owns it; the walk math in
  `components.jsx` reads the same number) but usually has to *read* it, because
  `.worldlayer--ground` is `inset: 0` and will otherwise paint the ground onto the sky.
- **Size anything shaped on the floor off `--tile-size`, never as a floor percentage** — and know
  the token has three values: 44px below 900, 52px from 900, 62px from 1500.
- **End every shaped gradient layer in `transparent`** — a `radial-gradient`'s last colour fills
  its whole box, not just to the radius, and hides every layer under it.
- On a bright world the whole lighting method inverts: you cannot add light to a white floor, so
  light is painted as the shadow it casts.

A world change is frontend only: no backend, no protocol, no schema, no new dependency.

---

## When the plan and reality diverge

You will find things the docs got wrong — an AWS limit, an unsuitable dependency, an approach
that cannot work. Do not blindly follow the doc.

1. Name the discrepancy.
2. State the practical impact.
3. Choose the simplest solution that preserves the product's behaviour.
4. Update the affected docs.
5. Continue if the change is safe.

Stop and ask only when the change materially alters product scope, security, cost, or core
architecture.

---

## Working style

- Backend before frontend. The scheduler must work headlessly before any UI depends on it.
- Thin vertical slices — build, verify, then expand.
- Prefer boring and obvious over clever. Fewer moving parts, fewer dependencies, simpler deploys.
- Surface assumptions before acting on them. If requirements conflict, ask rather than guess.
- Push back when an approach has a real problem. Explain the concrete downside and propose an
  alternative.
- Report outcomes honestly — if a check fails, say so with the output; if a step was skipped, say
  that.
