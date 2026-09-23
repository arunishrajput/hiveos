# DEPLOYMENT.md — HiveOS

Operational AWS guide: how to deploy HiveOS, how to verify it actually works, and what to do
when it does not. Steps are tagged **`AUTOMATED`** (a command runs it) or
**`MANUAL HUMAN ACTION`** (only a human with console access can).

| | |
|---|---|
| Region | `us-east-1` |
| Stack | `hiveos` |
| Account | Free Tier, Free Plan — a deployment costs a few dollars; the guard is the enforced token ceiling, not the plan |

---

## Prerequisites

| Requirement | State on this machine |
|---|---|
| AWS CLI | ✅ 2.36.47 |
| AWS credentials | ✅ IAM user `hiveos-dev` (Manual Action 1 done) |
| Bedrock model access | ⛔ **Blocked account-wide, and abandoned** — not a config problem. Inference runs on Groq; see `ARCHITECTURE.md` decision 7 |
| Model API key | ✅ SSM SecureString `/hiveos/groq-api-key`, read at runtime |
| Docker daemon | ✅ running (Manual Action 3 done) |
| AWS SAM CLI | ✅ 1.166.2 |
| Node / npm | ✅ 26.8.2 / 11.19.1 |
| Python | ⚠️ 3.14 locally — **newer than any Lambda runtime** |
| git + gh | ✅ authenticated as `arunishrajput` |

> **Why Docker is mandatory.** Local Python is 3.14; Lambda runs 3.13. Building dependencies locally produces wrong-platform wheels for compiled packages like `pydantic-core`. `sam build --use-container` builds inside the official Lambda image and sidesteps this entirely. Always use it.

---

## MANUAL ACTION 1 — Configure AWS credentials

**Reason:** No credentials exist on this machine. Every AWS call currently fails at credential resolution, so nothing can be created, inspected, or deployed.

**Location:** AWS Console → top-right account menu → **Security credentials** → **Access keys** → *Create access key* → choose **Command Line Interface (CLI)**.

**Steps:**
1. Create the access key and copy both the Access Key ID and Secret Access Key.
2. In your terminal run `aws configure`.
3. Enter the Access Key ID, then the Secret Access Key.
4. Default region: `us-east-1`
5. Default output format: `json`

**Expected result:** `~/.aws/credentials` now exists with a `[default]` profile.

**Verification:**
```bash
aws sts get-caller-identity
```
Returns `UserId`, `Account`, and `Arn`.

**Resume by:** telling Claude Code *"credentials configured"*.

> **Never paste the secret key into a file in this repo, a commit, or a chat message.** `aws configure` writes it to `~/.aws/credentials`, which is outside the repo and git-ignored by location.

---

## Bedrock is not used — and cannot be, on this account

HiveOS calls **Groq**, not Amazon Bedrock. This is not a preference: Bedrock is blocked
account-wide here and the block is not a setting anyone can flip. `us-east-1`, `us-west-2` and
`ap-south-1` all refuse; 42 of 43 per-day token quotas are `0` and report `adjustable=False`, so
a Service Quotas increase cannot even be requested; and first-party Amazon Nova — which needs
neither a Marketplace subscription nor a payment instrument — fails identically. The Anthropic
use-case form was submitted and cleared, and a paid card was added; neither lifted it.

**Do not spend time re-attempting it, and do not upgrade the billing plan to try.** Both were
tried and neither worked. `ARCHITECTURE.md` decision 7 records the full reasoning, and
`backend/shared/llm.py` is the one seam a different provider would be swapped at.

If it ever does unlock, one call is enough to detect it:

```bash
aws bedrock-runtime converse --region us-east-1 \
  --model-id "<INFERENCE_PROFILE_ID>" \
  --messages '[{"role":"user","content":[{"text":"Say OK"}]}]' \
  --inference-config '{"maxTokens":16}'
```

---

## MANUAL ACTION 2 — Provision the model API key

**Reason:** The Agent Runner reads its model API key from SSM Parameter Store at runtime.
Without it every task falls back to composed text flagged `estimated`.

**Location:** <https://console.groq.com> → sign in (Google/GitHub, free, **no card required**)
→ **API Keys** → **Create API Key**. The key is shown once and begins with `gsk_`.

**Steps:** run this in a normal terminal — not through an agent session, where the key would
land in a transcript:

```bash
aws ssm put-parameter \
  --name /hiveos/groq-api-key \
  --type SecureString \
  --value 'gsk_...' \
  --region us-east-1 \
  --overwrite
```

**Expected result:** JSON containing `"Version": 1`. **No redeploy is needed** — the Lambda
retries the SSM read on every task until it succeeds, so the key goes live by itself.

**Verification:**

```bash
aws ssm get-parameter --name /hiveos/groq-api-key --region us-east-1 --query 'Parameter.Type'
# → "SecureString"   (reads the type only, never the value)
python3 scripts/ws_smoke.py   # 58/58, and token frames report estimated=False
```

**Status:** done, 2026-09-18. Verified live on the public URL.

> The key never enters `template.yaml`, `samconfig.toml`, an environment variable, or git. The
> Agent Runner's IAM grant is scoped to this one parameter.

---

## MANUAL ACTION 3 — Start Docker Desktop

**Reason:** `sam build --use-container` needs a running Docker daemon to build Lambda packages against the correct Python runtime.

**Location:** macOS Applications → **Docker Desktop** → launch and wait for the whale icon to show *Running*.

**Verification:**
```bash
docker info
```
Prints server info rather than a socket connection error.

**Resume by:** telling Claude Code *"Docker running"*.

---

## MANUAL ACTION 4 — Verify the AWS Budget alarm

**Reason:** Second line of defence behind the in-app token ceiling. The public URL is unauthenticated by design.

Claude Code creates the budget with `aws budgets create-budget`; you must confirm the notification email.

**Location:** email inbox for `arunishrajput7@gmail.com` → AWS notification subscription confirmation.

**Verification:**
```bash
aws budgets describe-budgets --account-id "$(aws sts get-caller-identity --query Account --output text)"
```

---

## `AUTOMATED` — Backend deploy

```bash
brew install aws-sam-cli          # once
sam build --use-container         # always --use-container (see note above)
sam deploy                        # config comes from samconfig.toml, which is committed
```

`samconfig.toml` is in the repository and holds no secrets — stack name, region, and build flags only. `--guided` is not needed; running it would only overwrite that file.

**Deployment order is handled by CloudFormation** — do not create stack resources by hand. A one-off `aws dynamodb create-table` produces drift and duplicate resources across `/clear` sessions, which is exactly what the SAM template exists to prevent.

### Reading stack outputs

```bash
aws cloudformation describe-stacks --stack-name hiveos \
  --query 'Stacks[0].Outputs' --output table
```

Outputs include the WebSocket URL, table name, and queue URL.

---

## `AUTOMATED` — Frontend deploy

Amplify Hosting in **manual deploy mode** — no GitHub OAuth, no build service role, fully
scriptable. One command:

```bash
./scripts/deploy-frontend.sh
```

| | |
|---|---|
| Amplify app | `hiveos` — app id **`dbavt8jr66qxx`** |
| Branch | `main` |
| Public URL | **https://main.dbavt8jr66qxx.amplifyapp.com** |

The script is idempotent and safe to re-run for every redeploy. It:

1. reads `WebSocketURL` from the stack output — the URL is never pasted by hand;
2. builds with `VITE_WS_URL` set;
3. **greps the built bundle for that URL and aborts if it is absent** — a frontend that loads
   but never connects is the likeliest failure here, and this catches it before publishing;
4. zips `dist/` with the files at the archive root;
5. finds-or-creates the app **by name** and the branch, so repeat runs never duplicate them;
6. uploads, starts the deployment, and polls `get-job` until `SUCCEED` rather than trusting the
   start call's exit code.

Override with env vars if needed: `STACK_NAME`, `AWS_REGION`, `APP_NAME`, `BRANCH`.

> **The Amplify app is not in `template.yaml`.** That is intentional — manual-deploy mode is
> what removes the OAuth and service-role setup. It does mean `describe-stacks` never mentions
> it and `sam delete` will not remove it. See Teardown.

### Local development against the deployed backend

```bash
cd frontend
npm install
VITE_WS_URL="$(aws cloudformation describe-stacks --stack-name hiveos \
  --query "Stacks[0].Outputs[?OutputKey=='WebSocketURL'].OutputValue" --output text)" \
  npm run dev
```

Each browser holds one identity in `localStorage['hiveos.identity']`, so two tabs of the same
origin share a name. Use separate browsers or profiles to act as different members.

---

## `AUTOMATED` — Verification

Never trust a zero exit code. Verify behaviour.

```bash
# Identity and stack
aws sts get-caller-identity
aws cloudformation describe-stacks --stack-name hiveos --query 'Stacks[0].StackStatus'

# DynamoDB round trip
aws dynamodb get-item --table-name hiveos-state \
  --key '{"PK":{"S":"TEAM#alpha"},"SK":{"S":"METADATA"}}'

# WebSocket — the real check. Two clients, fan-out, GoneException cleanup,
# and DynamoDB assertions, all against deployed AWS.
pip install websockets
python3 scripts/ws_smoke.py

# Queue depth
aws sqs get-queue-attributes --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages
```

`scripts/ws_smoke.py` resolves the endpoint from the stack output itself, so there is no URL to
keep in sync. Run it after every backend deploy: it is the regression check for the whole system,
and a clean run is **113/113**. It counts only the connections it opens itself, so other people
being on the public URL does not affect the score.

For poking by hand instead:

```bash
npx wscat -c "$(aws cloudformation describe-stacks --stack-name hiveos \
  --query "Stacks[0].Outputs[?OutputKey=='WebSocketURL'].OutputValue" \
  --output text)?user_id=alice"
> {"action":"hello"}
```

---

## Operational runbook: Dead-Letter Queue (DLQ) inspection and recovery

When tasks fail repeatedly in the Agent Runner (e.g. Lambda timeouts, unhandled exceptions, or transient infrastructure faults), SQS moves them to the Dead-Letter Queue (`TaskDLQ`).

### Deployment prerequisite
SAM / CloudFormation deployment (`sam deploy`) must be completed before DLQ tools can rely on stack-injected endpoints:
- `template.yaml` injects `DLQ_URL: !Ref TaskDLQ` into `AgentRunnerFunction`.
- `template.yaml` exports `DeadLetterQueueUrl` (`${AWS::StackName}-DeadLetterQueueUrl`) and `QueueUrl` (`${AWS::StackName}-QueueUrl`).

### Operational commands
Use `scripts/recover_dlq.py` to inspect, redrive, or purge dead-lettered messages:

```bash
# 1. Passive inspection (peeks at messages without modifying or removing them)
python3 scripts/recover_dlq.py --inspect

# 2. Safe atomic redrive (clears idempotency markers and replays tasks to main queue)
python3 scripts/recover_dlq.py --redrive-all

# 3. Purge/drain DLQ
python3 scripts/recover_dlq.py --purge

# Options: override URLs or stack name directly
python3 scripts/recover_dlq.py --inspect --dlq-url <DLQ_URL> --queue-url <QUEUE_URL>
```

### Safety and atomicity guarantees
- **Idempotency marker clearance**: When redriving, `state.clear_idempotency_marker()` removes the task's `IDEMPOTENCY#<task_id>#<hops>` marker so the Agent Runner does not treat the redriven task as a duplicate.
- **Atomic redrive claim**: `state.claim_dlq_redrive()` records a temporary claim with a 14-day TTL (matching `TaskDLQ` `MessageRetentionPeriod: 1209600`). If SQS message deletion fails after re-dispatch, subsequent recovery runs skip duplicate re-dispatch and safely finish DLQ message deletion.
- **Rollback on send failure**: If sending to the main queue fails, the redrive claim is released so the task can be retried.

### Before you redrive: check the desk is not back in use

A redrive deliberately clears the task's `IDEMPOTENCY#` marker, which is the
only thing that stops the runner executing it again — that is the whole point,
and it means a redriven task **calls the model again and charges the team
again**. It also means the replayed task ends the way any task ends: its
`finally` releases `slot_id` with `expected_holder=<its user_id>`.

That release names a *user*, not a task. If the same person has since claimed
the same desk for new work, the replayed task's release will free that desk out
from under them and clear their `ACTIVE#` admission — cutting a live task short.

So redrive is safe when the floor is quiet, and worth a look first when it is
not. `--inspect` prints the `slot_id` and `user_id` of every dead-lettered
message without touching the queue; compare them against the board before
running `--redrive-all`, and prefer redriving while nobody is working at those
desks.

---

## `AUTOMATED` — Logs

```bash
sam logs -n RouterFunction      --stack-name hiveos --tail
sam logs -n AgentRunnerFunction --stack-name hiveos --tail

aws logs tail /aws/lambda/hiveos-router --follow --since 10m
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `NoCredentials` on every call | Credentials not configured | Manual Action 1 |
| `AccessDeniedException` calling Bedrock | Account-wide Bedrock block — **expected, do not chase** | Nothing. Inference runs on Groq |
| Agent replies `[coder · offline]` | The model call failed; the fallback answered | `sam logs -n AgentRunnerFunction --stack-name hiveos` and grep `model call failed` — the reason is logged verbatim |
| `groq HTTP 403 ... error code: 1010` | Cloudflare rejected the User-Agent | Not a bad key. `shared/llm.py` must send an explicit `User-Agent` |
| `groq HTTP 404 model_not_found` | Groq retired the model name | List `GET https://api.groq.com/openai/v1/models`, update `samconfig.toml` |
| `sam build` fails on a compiled dependency | Built with local Python 3.14 | Use `sam build --use-container` |
| `sam build --use-container` cannot connect | Docker daemon down | Manual Action 3 |
| Broadcast fails with `403` | Missing `execute-api:ManageConnections` | Add to the Lambda IAM policy in `template.yaml` |
| Broadcast loop crashes mid-demo | GoneException unhandled | Implement the handler in `CONTRACT.md` — mandatory |
| Messages land in the DLQ | Agent Runner throwing | Read the DLQ body and CloudWatch logs; check the slot is released in `finally` |
| Slot stuck `BUSY` forever | Runner failed before release | Release must be in `try/finally`; reset with `scripts/reset-demo.py` |
| Stack stuck in `ROLLBACK_COMPLETE` | Failed first create | `aws cloudformation delete-stack --stack-name hiveos`, wait, redeploy |
| Frontend loads but never connects | Wrong `VITE_WS_URL` at build time | Rebuild with the current stack output |

---

## Cost control

| Guard | Where |
|---|---|
| Server-side token ceiling — refuses to call the model at 100% | Agent Runner (`ARCHITECTURE.md` decision 4) |
| Low `max_tokens` per call | `MAX_TOKENS_PER_CALL` env var |
| Fastest/cheapest model with access | `BEDROCK_MODEL_ID` in `CONTRACT.md` |
| AWS Budget alarm (~$20) | Manual Action 4 |
| Everything scales to zero | Lambda, DynamoDB on-demand, SQS |

Expected total for build and demo: a few dollars. The risk is a runaway loop, not baseline usage.

---

## Teardown

```bash
sam delete --stack-name hiveos
aws amplify delete-app --app-id dbavt8jr66qxx   # NOT covered by sam delete
```

Do **not** tear down before judging completes — the public URL must stay reachable.
