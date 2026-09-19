"""Slot scheduling — the OS mechanic that HiveOS actually is.

Two agent slots are the CPU cores. A claim is a conditional DynamoDB update, so
two people clicking at the same instant can never both win the same slot. If
every slot is taken the task becomes a QUEUE# row and gets a real position,
because a queue you cannot see your place in is not a queue.

Both Lambdas use this module: the Router claims on demand, the Agent Runner
releases and dispatches the next waiting task. Keeping one implementation is
what stops the two paths from drifting into different state machines.

Ordering rules that matter (ARCHITECTURE.md decision 1):
  - SQS carries tasks that are RUNNING. Waiting tasks live in DynamoDB.
  - The QUEUE# delete is the exactly-once gate. Whoever wins the delete owns
    the task, so two runners finishing together cannot dispatch it twice.

An agent may also hand its work to another desk (`hand_off`). That is a
scheduling request like any other — it claims or queues, it is bounded by
`MAX_HANDOFF_HOPS`, and its second leg meets the budget ceiling on its own
account. The one thing it does differently is that its queue row is *pinned*:
falling back to another desk would hand the work straight back to the agent
that decided it was not theirs.
"""

import json
import os
import uuid

import boto3
from botocore.exceptions import ClientError

from . import agents, broadcast, state

# Slot order is also the fallback order for a claim. CONTRACT.md. Taken from
# the roster so the desks, the fallback order and the slot rows cannot disagree
# about which agents exist.
SLOTS = agents.IDS

# Rough per-task duration used for the queue's estimated wait. A heuristic,
# shown as such — the stub agent takes ~2.5s, a Bedrock call will take longer.
# Phase 3 should retune this once real latency is known.
ESTIMATED_TASK_SECONDS = 8

# How many times one piece of work may be passed between desks. One.
#
# This is the loop guard, and it is structural rather than advisory: the runner
# only offers the handoff tool to a task whose hop count is below this, so a
# task that arrived by handoff has nothing to call. Ada → Iris → Ada would
# otherwise be a legal chain, and each leg is a real model call against the
# team's real budget.
MAX_HANDOFF_HOPS = 1

# How much of an agent's handover note is carried. Long enough for "this is a
# research question, not an engineering one"; short enough that it cannot
# become a second copy of the prompt riding on every frame.
MAX_HANDOFF_NOTE = 400

_sqs = None


def sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs")
    return _sqs


def _is_conditional_failure(error):
    return (
        error.response.get("Error", {}).get("Code")
        == "ConditionalCheckFailedException"
    )


# --- Slots -----------------------------------------------------------------


def try_claim(team, slot_id, user_id):
    """Atomically take one slot. False means somebody else already had it.

    The ConditionExpression is the whole point: this is the only correct way
    to claim, and a read-then-write here would hand both users the same slot
    under exactly the load the demo creates.
    """
    try:
        state.table().update_item(
            Key={"PK": state.team_pk(team), "SK": f"AGENT#{slot_id}"},
            UpdateExpression="SET #s = :busy, #u = :user, claimed_at = :now",
            ConditionExpression="#s = :idle",
            ExpressionAttributeNames={"#s": "status", "#u": "current_user"},
            ExpressionAttributeValues={
                ":busy": "BUSY",
                ":idle": "IDLE",
                ":user": user_id,
                ":now": state.now_iso(),
            },
        )
        return True
    except ClientError as error:
        if _is_conditional_failure(error):
            return False
        raise


def claim_any(team, preferred, user_id):
    """Claim the requested slot, else any other. None if all are busy."""
    order = list(SLOTS)
    if preferred in order:
        order.remove(preferred)
        order.insert(0, preferred)

    for slot_id in order:
        if try_claim(team, slot_id, user_id):
            print(f"[scheduler] claimed slot={slot_id} user={user_id}")
            return slot_id

    print(f"[scheduler] all slots busy — user={user_id} must queue")
    return None


def set_idle(team, slot_id):
    state.table().update_item(
        Key={"PK": state.team_pk(team), "SK": f"AGENT#{slot_id}"},
        UpdateExpression="SET #s = :idle, #u = :null REMOVE claimed_at",
        ExpressionAttributeNames={"#s": "status", "#u": "current_user"},
        ExpressionAttributeValues={":idle": "IDLE", ":null": None},
    )
    print(f"[scheduler] released slot={slot_id}")


# --- Queue -----------------------------------------------------------------


def new_task_id():
    """An id for one piece of work, which may run as more than one agent task.

    Minted where the work is *requested*, not where it runs, and carried
    unchanged across a handoff. Both legs of a handed-over task therefore bill
    to the same id, which is the difference between a ledger that shows two
    unrelated 700-token tasks and one that shows a single 1,400-token job that
    crossed two desks.
    """
    return uuid.uuid4().hex[:12]


def enqueue(team, user_id, agent_type, prompt, connection_id, task_id=None,
            pinned_slot=None, hops=0, handoff_from=None):
    """Park a task in DynamoDB and return its SK.

    `pinned_slot` makes a queue row dispatchable at exactly one desk. Only a
    handoff sets it: `agent_type` is a *preference* and the scheduler is right
    to fall back off it, but falling back on a handoff would hand the work
    straight back to the agent that just decided it was not theirs.
    """
    sk = f"QUEUE#{state.now_iso_micros()}#{uuid.uuid4().hex[:8]}"
    state.table().put_item(
        Item={
            "PK": state.team_pk(team),
            "SK": sk,
            "user_id": user_id,
            "agent_type": agent_type,
            "prompt": prompt,
            "connection_id": connection_id,
            "task_id": task_id,
            "pinned_slot": pinned_slot,
            "hops": int(hops),
            "handoff_from": handoff_from,
            "enqueued_at": state.now_iso(),
        }
    )
    print(f"[scheduler] enqueued user={user_id} sk={sk} pinned={pinned_slot}")
    return sk


def take_next_task(team, idle):
    """Claim ownership of the next dispatchable waiting task, or None.

    "Next" is `state.fair_order` — least-recently-served first, arrival only as
    the tie-break — not simply the oldest. The same function orders the queue
    the clients are shown, so position 1 on the board is genuinely whoever this
    will pick.

    `idle` is the set of desks free right now. A row pinned to a desk that is
    not in it is **skipped, not taken**: a handoff waiting for Iris stays in the
    queue when Ada frees up, because Ada is the desk that passed it on. An
    unpinned row is dispatchable at any free desk, as it always was.

    The conditional delete is the exactly-once gate. Two Agent Runners
    finishing at the same moment both see the same head-of-queue item; only
    one can delete it, and the loser simply moves to the next one.
    """
    for item in state.queue_items(team):
        pin = item.get("pinned_slot")
        if pin and pin not in idle:
            continue
        try:
            state.table().delete_item(
                Key={"PK": state.team_pk(team), "SK": item["SK"]},
                ConditionExpression="attribute_exists(SK)",
            )
            return item
        except ClientError as error:
            if _is_conditional_failure(error):
                print(f"[scheduler] lost race for {item['SK']} — trying next")
                continue
            raise
    return None


def requeue(team, item):
    """Put a task back at its original position.

    Only used when we won a task but then lost the slot race. Re-writing the
    same SK preserves FIFO — the user does not get punished by going to the
    back of the line for losing a race they never saw.
    """
    state.table().put_item(Item=item)
    print(f"[scheduler] requeued {item['SK']} — no slot was free after all")


# --- Dispatch --------------------------------------------------------------


def dispatch(team, slot_id, user_id, requested_agent, prompt, connection_id,
             task_id=None, hops=0, handoff_from=None):
    """Hand a running task to SQS. Format is CONTRACT.md's.

    `slot_id` is the agent that will actually run this — the desk whose row we
    just won — and `requested_agent` is the one the user asked for, which may
    be neither it nor anything at all. The message used to carry a single
    `agent_type` holding the *preference*, which the runner then recorded in
    the ledger as the agent that ran the task. With interchangeable slots that
    was a harmless label; with named agents it is the ledger saying Ada did
    work that Iris did.

    `task_id` identifies the piece of work rather than this leg of it, `hops`
    counts how many times it has been handed on, and `handoff_from` names the
    desk that handed it. All three are absent on an ordinary task, and a
    message still in flight across a deploy simply reads as hop zero.
    """
    sqs().send_message(
        QueueUrl=os.environ["QUEUE_URL"],
        MessageBody=json.dumps(
            {
                "team_id": state.clean_team(team),
                "slot_id": slot_id,
                "user_id": user_id,
                "requested_agent": requested_agent,
                "prompt": prompt,
                "connection_id": connection_id,
                "task_id": task_id,
                "hops": int(hops),
                "handoff_from": handoff_from,
                "enqueued_at": state.now_iso(),
            }
        ),
    )
    print(
        f"[scheduler] dispatched slot={slot_id} user={user_id} "
        f"requested={requested_agent} task={task_id} hops={hops}"
    )


# --- Broadcasts ------------------------------------------------------------


def broadcast_slot(team, slot_id, status, current_user):
    broadcast.broadcast_to_team(
        team,
        {
            "event": "agent_state_update",
            "agent_type": slot_id,
            "slot_id": slot_id,
            "status": status,
            "current_user": current_user,
        }
    )


def broadcast_queue(team):
    """Tell every waiting user where they now stand.

    Sent to the whole team rather than directed at one connection: a user can
    have several tabs open, and the frontend filters on user_id anyway.
    """
    for entry in state.queue_view(team):
        broadcast.broadcast_to_team(
            team,
            {
                "event": "queue_update",
                "user_id": entry["user_id"],
                "queue_position": entry["queue_position"],
                "estimated_wait_seconds": entry["queue_position"]
                * ESTIMATED_TASK_SECONDS,
            }
        )


# --- The release path ------------------------------------------------------


def release_and_dispatch(team, slot_id):
    """Free a slot, then start the next waiting task. Returns the slot used.

    This runs in the Agent Runner's finally block, so it must work even when
    the task it follows blew up. A slot that leaks here deadlocks the demo.
    """
    set_idle(team, slot_id)
    broadcast_slot(team, slot_id, "IDLE", None)
    return dispatch_next(team)


def dispatch_next(team):
    """Start the next waiting task that has a desk free for it, if any.

    Split out of `release_and_dispatch` because a release is no longer the only
    thing that can make the queue movable: enqueuing a handoff can too, when the
    desk it is pinned to freed in the window between the failed claim and the
    row existing. Both paths must make the same decision, so there is one
    function that makes it.
    """
    idle = state.idle_slots(team)
    if not idle:
        return None

    task = take_next_task(team, idle)
    if task is None:
        return None

    pin = task.get("pinned_slot")
    if pin:
        # A handoff runs at the desk it was handed to or it waits. Falling back
        # would return the work to whoever passed it on.
        claimed = pin if try_claim(team, pin, task["user_id"]) else None
    else:
        # The QUEUE# row's `agent_type` is what this person asked for when they
        # joined the line — a preference, which is why waiting behind a busy
        # agent never happens.
        claimed = claim_any(team, task.get("agent_type"), task["user_id"])

    if claimed is None:
        # Someone claimed the slot we just freed in the gap between the two
        # operations. Put the task back where it was and let whoever finishes
        # next pick it up.
        requeue(team, task)
        broadcast_queue(team)
        return None

    # Same ordering rule as claim_agent: the BUSY frame must reach clients
    # before the task that could complete and release the slot.
    broadcast_slot(team, claimed, "BUSY", task["user_id"])
    dispatch(
        team,
        claimed,
        task["user_id"],
        task.get("agent_type"),
        task.get("prompt", ""),
        task.get("connection_id"),
        task_id=task.get("task_id"),
        hops=int(task.get("hops", 0) or 0),
        handoff_from=task.get("handoff_from"),
    )
    broadcast_queue(team)
    return claimed


# --- Agent-to-agent handoff ------------------------------------------------


def handoff_prompt(task, from_slot, note):
    """What the receiving agent is actually asked.

    Composed once, here, and carried as the leg's ordinary `prompt` rather than
    as separate fields the runner would have to reassemble. The receiving agent
    is a normal task in every other respect — same ceiling check, same memory
    load, same accounting — and the fewer special cases it has, the fewer ways
    the second leg can behave unlike the first.

    The last line restates the hop limit the tool list already enforces. Belt
    and braces: the structural guard is that the tool is not offered, and this
    is what the model reads if it ever is.
    """
    sender = agents.get(from_slot)
    who = (
        f"{sender['name']}, the {sender['role']}," if sender else f"{from_slot},"
    )
    lines = [
        f"This task was passed to you by {who} who judged it a better fit for "
        "your desk.",
    ]
    if note:
        lines.append(f"Their note: {note}")
    lines.append(
        f"The original request, from {task.get('user_id', 'a teammate')}: "
        f"{task.get('prompt', '')}"
    )
    lines.append("Answer it directly. Do not hand it on again.")
    return "\n".join(lines)


def hand_off(team, task, target_slot, note):
    """Pass one task's work to another desk. Returns the slot it landed on.

    Called *after* the handing agent's own slot has been released, so the
    handoff competes for a desk on exactly the same terms as anybody in the
    queue — it is a scheduling request, not a private channel between agents.
    None means it is waiting in the queue, pinned to its target.

    The ceiling is not re-checked here. It is checked by the receiving leg
    immediately before its model call, which is the same place it is checked for
    every other task and the only honest moment: a handoff may sit in the queue
    while the tasks ahead of it spend what was left. A chain can therefore
    overspend by at most one leg, exactly like a single task, and never by one
    leg at a time indefinitely — `MAX_HANDOFF_HOPS` is what bounds the chain.
    """
    from_slot = task["slot_id"]
    user_id = task.get("user_id", "unknown")
    task_id = task.get("task_id")
    hops = int(task.get("hops", 0) or 0) + 1
    note = (note or "").strip()[:MAX_HANDOFF_NOTE]
    prompt = handoff_prompt(task, from_slot, note)

    claimed = try_claim(team, target_slot, user_id)

    # Broadcast either way, and say which it was. The envelope crossing the
    # floor is the same event whether the receiving desk takes it immediately or
    # it has to wait — and a handoff that vanished from the board because the
    # target happened to be busy would be the board lying about the scheduler.
    broadcast.broadcast_to_team(
        team,
        {
            "event": "agent_handoff",
            "task_id": task_id,
            "user_id": user_id,
            "from_agent": from_slot,
            "from_name": agents.name_of(from_slot),
            "to_agent": target_slot,
            "to_name": agents.name_of(target_slot),
            "note": note,
            "queued": not claimed,
        },
    )

    if claimed:
        broadcast_slot(team, target_slot, "BUSY", user_id)
        dispatch(
            team,
            target_slot,
            user_id,
            # Requested and ran are the same desk here, so nothing is reported
            # as a substitution — the handoff is the story, not a fallback.
            target_slot,
            prompt,
            task.get("connection_id"),
            task_id=task_id,
            hops=hops,
            handoff_from=from_slot,
        )
        print(f"[scheduler] handoff {from_slot} -> {target_slot} ran immediately")
        return target_slot

    enqueue(
        team,
        user_id,
        target_slot,
        prompt,
        task.get("connection_id"),
        task_id=task_id,
        pinned_slot=target_slot,
        hops=hops,
        handoff_from=from_slot,
    )
    broadcast_queue(team)
    print(f"[scheduler] handoff {from_slot} -> {target_slot} queued")

    # Closes the one race this path has: the target desk could have released in
    # the window between the failed claim above and the row existing, and its
    # own release found nothing to dispatch. Without this the handoff waits for
    # the *next* release, which on a two-desk board may never come.
    dispatch_next(team)
    return None
