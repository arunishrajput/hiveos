"""Task history — who ran what, what it cost, and whether it ran at all.

This is the entity a governance product is actually for. Until now HiveOS
could tell you the team had spent 2,214 tokens and absolutely nothing about
*where they went*: no per-person spend, no record of a refusal, no way to
answer "who used the budget up". A meter without a ledger is a gauge, which is
the exact criticism the product levels at everything else.

It is also why `get_task_context` was never built (CONTRACT.md): there was no
task history to return.

Rows are `TASK#<microsecond timestamp>#<short uuid>`, so they sort newest-last
lexicographically by SK for free. **Microsecond precision, not `now_iso()`** —
at second granularity two tasks finishing in the same second tie and fall back
to UUID order, i.e. random. The queue learned this the hard way in Phase 2.
"""

import time
import uuid

from botocore.exceptions import BotoCoreError, ClientError

from . import agents, state

# How much of the prompt to keep. Enough to recognise a task in a list, not so
# much that the history rows become a second copy of everything ever asked.
MAX_PROMPT = 120

# What a snapshot carries. The frame has to stay small — every client parses it
# on connect — and nobody reads the 40th most recent task off a board.
SNAPSHOT_LIMIT = 12

DONE = "done"
FAILED = "failed"
REFUSED = "refused"


MAX_RETRIES = 3
INITIAL_BACKOFF = 0.05

TRANSIENT_CLIENT_ERROR_CODES = {
    "ProvisionedThroughputExceededException",
    "ThrottlingException",
    "RequestLimitExceeded",
    "InternalServerError",
    "ServiceUnavailable",
    "TransactionConflictException",
    "TransactionInProgressException",
}

TRANSIENT_BOTOCORE_EXCEPTIONS = (
    "EndpointConnectionError",
    "ConnectTimeoutError",
    "ReadTimeoutError",
    "ConnectionClosedError",
    "HTTPClientError",
    "IncompleteReadError",
)


def is_transient_error(exc):
    """Determine if an exception is a transient failure worthy of retrying."""
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        if code in TRANSIENT_CLIENT_ERROR_CODES:
            return True
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        if 500 <= status_code < 600:
            return True
        return False

    if isinstance(exc, BotoCoreError):
        return exc.__class__.__name__ in TRANSIENT_BOTOCORE_EXCEPTIONS

    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True

    return False


def record(team, user_id, agent_type, tokens, estimated, status, prompt="",
           requested_agent=None, task_id=None, handoff_from=None,
           agent_name=None, handoff_from_name=None, retries=MAX_RETRIES):
    """Write one task to the ledger.

    `agent_type` is the agent that **ran** the task — the desk it ran at, not
    the one the requester asked for. `requested_agent` records the preference,
    and only when it differed: a ledger that repeated the same id in both
    columns on every row would make the one case that matters invisible.

    **The names are written here, at the moment the work ran, rather than
    joined on when the ledger is read.** They used to be looked up from a
    roster that was the same in every workspace and never changed; an agent can
    now be hired and fired, so a late join would report a dismissed agent's
    past work as `jim-a3f2` — or, worse, attribute it to whoever was hired into
    that id next. A ledger is a record of what happened, and who did it is part
    of what happened. It also drops N lookups from every snapshot.

    `task_id` is the *chain*, not the row. A handoff runs as two agent tasks
    and writes two rows, and they carry the same `task_id` — that is what makes
    "this piece of work cost the team 1,400 tokens across two desks" a question
    the ledger can answer at all. `handoff_from` is set on the second row only,
    and names the desk that passed it on.

    TASK# rows are the authoritative source for scheduler fairness
    (`state.last_served` / `fair_order`) and per-person spend breakdowns
    (`history.spend`). Writes are retried against transient persistence
    failures with backoff, and failures raise to prevent silent corruption
    of fairness and spend state.
    """
    substituted = requested_agent if requested_agent and requested_agent != agent_type else None
    item = {
        "PK": state.team_pk(team),
        "SK": f"TASK#{state.now_iso_micros()}#{uuid.uuid4().hex[:8]}",
        "user_id": user_id or "unknown",
        "agent_type": agent_type or "",
        "agent_name": agent_name or agent_type or "",
        "requested_agent": substituted,
        "task_id": task_id,
        "handoff_from": handoff_from,
        "handoff_from_name": handoff_from_name,
        "tokens": int(tokens or 0),
        "estimated": bool(estimated),
        "status": status,
        "prompt": (prompt or "")[:MAX_PROMPT],
        "created_at": state.now_iso(),
    }

    backoff = INITIAL_BACKOFF
    last_exc = None
    for attempt in range(max(1, retries)):
        try:
            state.table().put_item(Item=item)
            return item
        except Exception as exc:
            last_exc = exc
            if not is_transient_error(exc):
                # Non-transient error (validation, permissions, programming bug) — do not retry
                print(
                    f"[history] permanent write error ({type(exc).__name__}: {exc})"
                )
                raise
            print(
                f"[history] transient write attempt {attempt + 1}/{retries} failed "
                f"({type(exc).__name__}: {exc})"
            )
            if attempt < retries - 1:
                time.sleep(backoff)
                backoff *= 2

    if last_exc is not None:
        raise last_exc
    return item


def view(rows):
    """Shape `TASK#` items for the wire, newest first."""
    ordered = sorted(rows, key=lambda item: item["SK"], reverse=True)
    return [
        {
            "user_id": item.get("user_id"),
            "agent_type": item.get("agent_type"),
            # Read straight off the row. Rows written before this phase have no
            # `agent_name`, so they fall back to the id — which for those rows
            # is `coder` or `researcher`, the only two ids that existed then.
            "agent_name": item.get("agent_name") or item.get("agent_type"),
            # Present only when somebody got a different agent than they asked
            # for. Null on every ordinary row.
            "requested_agent": item.get("requested_agent"),
            # The chain this row belongs to. Two rows share one `task_id` when
            # an agent handed the work on, and `handoff_from` names the desk it
            # came from — null on a row that nobody handed over.
            "task_id": item.get("task_id"),
            "handoff_from": item.get("handoff_from"),
            "handoff_from_name": (
                item.get("handoff_from_name") or item.get("handoff_from") or None
            ),
            "tokens": int(item.get("tokens", 0)),
            "estimated": bool(item.get("estimated", False)),
            "status": item.get("status"),
            "prompt": item.get("prompt", ""),
            "at": item.get("created_at"),
        }
        for item in ordered[:SNAPSHOT_LIMIT]
    ]


def as_context(team, limit=8):
    """Recent tasks as a block a model can read. "" when nothing has run.

    This is what `get_task_context` returns, and the reason CONTRACT.md could
    finally stop calling that tool unbuildable: it was specified to return
    prior task history, and until the ledger existed there was none.

    Reads the table itself rather than taking rows, because its caller is a
    tool invocation deep inside a model round trip and has none to hand.
    """
    rows = sorted(state.query_team(team, "TASK#"), key=lambda item: item["SK"], reverse=True)
    if not rows:
        return "The team has not run any agent tasks yet."

    lines = [
        f"- {item.get('user_id')} asked"
        f" {item.get('agent_name') or item.get('agent_type')}:"
        f" {item.get('prompt') or '(no prompt)'}"
        f" [{item.get('status')}, {int(item.get('tokens', 0))} tokens"
        # Named here too, so an agent asked where the budget went can say that
        # two of these rows were one piece of work rather than two requests.
        + (f", handed over by "
           f"{item.get('handoff_from_name') or item.get('handoff_from')}"
           if item.get("handoff_from") else "")
        + "]"
        for item in rows[:limit]
    ]
    return "Recent agent tasks, newest first:\n" + "\n".join(lines)


def spend(rows):
    """Per-person spend, biggest first.

    Aggregated over *every* task row rather than the snapshot slice — the whole
    point is the total, and a breakdown of only the last twelve tasks would be
    a different and much less useful number.

    Counts refusals and failures as tasks but not as spend, because that is
    what they are: a refused task costs nothing, and saying so is the clearest
    possible demonstration that the ceiling is a control rather than a gauge.
    """
    totals = {}
    for item in rows:
        user = item.get("user_id") or "unknown"
        bucket = totals.setdefault(user, {"user_id": user, "tokens": 0, "tasks": 0})
        bucket["tokens"] += int(item.get("tokens", 0))
        bucket["tasks"] += 1

    return sorted(totals.values(), key=lambda row: (-row["tokens"], row["user_id"]))
