"""Dispatch is two steps, and this is what happens when the second one fails.

`take_next_task` deletes the QUEUE# row first — that delete *is* the
exactly-once gate, so it cannot come second — and `dispatch` then hands the task
to SQS. In between, the task exists nowhere but in memory, and the desk has
already been claimed and already been announced BUSY.

If the send raises, both halves of that are lost:

  - the task is gone from DynamoDB and never reached SQS, so there is no DLQ
    message to redrive and no record of it anywhere;
  - the desk stays BUSY with nothing running in it, deadlocking that agent for
    the whole workspace until someone releases it by hand.

The quieter half is what it did to the Agent Runner. `dispatch_next` is called
from the runner's `finally`, so the exception failed the invocation of a task
that had **already completed and already charged the team**. SQS redelivered
that task and the model ran a second time — a real second charge against the
ceiling the entire product is built around.

Mocked rather than run against moto or deployed AWS: the invariant is which
calls are made, with which arguments, when the send fails — which is exactly
what a mock can see. `ws_smoke.py` is where deployed behaviour is checked.
"""

import json
from collections import namedtuple
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from shared import scheduler


TEAM = "alpha"
SLOT = "coder"
USER = "ada-user"

# A queue row exactly as `take_next_task` returns it: the whole DynamoDB item,
# because `requeue` writes it back verbatim and the SK is what holds the user's
# place in line.
QUEUE_ITEM = {
    "PK": f"TEAM#{TEAM}",
    "SK": "QUEUE#2026-09-19T10:00:00.000000#abcd1234",
    "user_id": USER,
    "agent_type": SLOT,
    "prompt": "summarise the incident",
    "connection_id": "conn-1",
    "task_id": "a1b2c3d4e5f6",
    "hops": 0,
    "handoff_from": None,
    "enqueued_at": "2026-09-19T10:00:00Z",
}

Run = namedtuple("Run", "result sqs set_idle requeue broadcast_slot")


def _sqs_failure():
    """A send that genuinely did not happen — not a conditional check."""
    return ClientError(
        {"Error": {"Code": "ServiceUnavailable", "Message": "SQS unavailable"}},
        "SendMessage",
    )


def _run(send_effect=None, released=True):
    """Drive `dispatch_next` with one task waiting and one desk free.

    Patched at `shared.*` because `conftest.py` puts `backend/` on the path, so
    the test and the Lambdas import the same module objects — the arrangement
    `sam build` produces.
    """
    sqs = MagicMock()
    sqs.send_message.side_effect = send_effect

    with patch.dict("os.environ", {"QUEUE_URL": "https://sqs.test/q"}), \
         patch("shared.state.idle_slots", return_value=[SLOT]), \
         patch.object(scheduler, "take_next_task", return_value=dict(QUEUE_ITEM)), \
         patch.object(scheduler, "claim_any", return_value=SLOT), \
         patch.object(scheduler, "set_idle", return_value=released) as set_idle, \
         patch.object(scheduler, "requeue") as requeue, \
         patch.object(scheduler, "broadcast_slot") as broadcast_slot, \
         patch.object(scheduler, "broadcast_queue"), \
         patch.object(scheduler, "sqs", return_value=sqs):

        result = scheduler.dispatch_next(TEAM)

    return Run(result, sqs, set_idle, requeue, broadcast_slot)


# --- The send fails --------------------------------------------------------


class TestDispatchFailureRecovery:
    def test_the_failure_does_not_reach_the_caller(self):
        """The regression that costs real money.

        `dispatch_next` runs inside the Agent Runner's `finally`. Raising out of
        it fails the invocation of a task that has already run and already been
        billed; SQS redelivers it and the model is called a second time. The
        release half above is deliberately left unwrapped for the opposite
        reason — a leaked desk is worth a redelivery — but a failed dispatch is
        not, because this path frees the desk itself.
        """
        assert _run(send_effect=_sqs_failure()).result is None

    def test_the_task_goes_back_at_its_original_position(self):
        """Written back verbatim, SK included. Losing a race nobody saw must not
        also send that person to the back of the line."""
        _run(send_effect=_sqs_failure()).requeue.assert_called_once_with(
            TEAM, QUEUE_ITEM
        )

    def test_the_desk_is_freed_under_the_holder_it_was_claimed_for(self):
        """Conditional, like every other release. The claim above set
        `current_user` to the task's user, so that is the only holder this write
        may name."""
        _run(send_effect=_sqs_failure()).set_idle.assert_called_once_with(
            TEAM, SLOT, expected_holder=USER
        )

    def test_idle_corrects_the_busy_frame_already_sent(self):
        """Clients were told BUSY before the send was attempted. Without the
        correction every board shows a desk working on a task that no longer
        exists anywhere."""
        frames = _run(send_effect=_sqs_failure()).broadcast_slot.call_args_list

        assert frames[0].args == (TEAM, SLOT, "BUSY", USER)
        assert frames[-1].args == (TEAM, SLOT, "IDLE", None)

    def test_a_refused_release_announces_nothing(self):
        """The same guard `release_and_dispatch` has. If the desk was not ours
        to free, IDLE describes a state the scheduler is not in — and the board
        lying about the scheduler is the one thing this product cannot do."""
        frames = _run(
            send_effect=_sqs_failure(), released=False
        ).broadcast_slot.call_args_list

        assert not [frame for frame in frames if "IDLE" in frame.args]

    def test_recovery_is_not_specific_to_botocore(self):
        """Anything that stops the message reaching SQS leaves the same hole —
        a bad endpoint, a serialisation error, a missing QUEUE_URL."""
        run = _run(send_effect=RuntimeError("boom"))

        assert run.result is None
        run.requeue.assert_called_once()


# --- The send succeeds -----------------------------------------------------


class TestDispatchSuccessPath:
    def test_nothing_is_requeued_or_released(self):
        """The recovery must be reachable only by failing, or a working dispatch
        quietly hands its desk back while the task runs."""
        run = _run()

        assert run.result == SLOT
        run.requeue.assert_not_called()
        run.set_idle.assert_not_called()

    def test_the_queued_task_keeps_its_identity_through_the_queue(self):
        """`task_id` is the chain id minted when the work was requested, and the
        ledger joins a handoff's two rows on it. A queued leg that invented a new
        one would split one job into two unrelated ones."""
        body = json.loads(_run().sqs.send_message.call_args.kwargs["MessageBody"])

        assert body["task_id"] == QUEUE_ITEM["task_id"]
        assert body["slot_id"] == SLOT
        assert body["user_id"] == USER
