"""The release path: a desk can only be freed by whoever is sitting at it.

Two holes, both closed here, both of which the demo would have shown as the
product being broken rather than as a bug:

  - `set_idle` wrote unconditionally. SQS redelivers, so a task can finish and
    reach the release long after its desk was handed to the next person in the
    queue. That write ended a stranger's task and then broadcast IDLE for a
    desk that was genuinely working.
  - `release_agent` checked nothing. Any connected client could name any desk
    and free it.

These assert the fixed behaviour, so they fail if either guard is removed.
Mocked rather than run against moto or deployed AWS: the invariant is which
arguments reach DynamoDB and which calls are skipped, and that is exactly what
a mock can see. `ws_smoke.py` is where the deployed behaviour is checked.
"""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from shared import scheduler


TEAM = "alpha"
SLOT = "coder"


def _client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "UpdateItem")


def _conditional_failure():
    return _client_error("ConditionalCheckFailedException")


# --- set_idle: the conditional write ---------------------------------------


class TestSetIdle:
    def _table(self, side_effect=None):
        table = MagicMock()
        table.update_item.side_effect = side_effect
        return table

    def test_names_the_expected_holder_in_the_condition(self):
        """Without a ConditionExpression bound to the holder, the write is a
        blind clear and a stale runner can take somebody else's desk."""
        table = self._table()
        with patch("shared.state.table", return_value=table):
            scheduler.set_idle(TEAM, SLOT, expected_holder="ada-user")

        kwargs = table.update_item.call_args.kwargs
        assert "ConditionExpression" in kwargs
        assert "ada-user" in kwargs["ExpressionAttributeValues"].values()
        # The condition has to test the holder, not merely mention one.
        condition = kwargs["ConditionExpression"]
        holder_alias = next(
            alias
            for alias, name in kwargs["ExpressionAttributeNames"].items()
            if name == "current_user"
        )
        assert holder_alias in condition

    def test_returns_true_when_the_desk_was_ours(self):
        table = self._table()
        with patch("shared.state.table", return_value=table):
            assert scheduler.set_idle(TEAM, SLOT, expected_holder="ada-user") is True

    def test_returns_false_when_the_desk_moved_on(self):
        """The stale-runner case: DynamoDB refuses, and that is not an error
        worth raising — it is the guard doing its job."""
        table = self._table(side_effect=_conditional_failure())
        with patch("shared.state.table", return_value=table):
            assert scheduler.set_idle(TEAM, SLOT, expected_holder="ada-user") is False

        assert table.update_item.call_count == 1, "a refused release must not retry"

    def test_a_real_failure_still_raises(self):
        """Only the conditional failure is absorbed. Throttling or a missing
        table must not be laundered into 'somebody else holds it'."""
        table = self._table(side_effect=_client_error("ProvisionedThroughputExceeded"))
        with patch("shared.state.table", return_value=table):
            with pytest.raises(ClientError):
                scheduler.set_idle(TEAM, SLOT, expected_holder="ada-user")


# --- release_and_dispatch: what a refusal must not do ----------------------


class TestReleaseAndDispatch:
    def test_a_refused_release_broadcasts_nothing_and_dispatches_nothing(self):
        """The regression that matters on camera.

        If the desk was reassigned while this task was in flight, announcing
        IDLE puts every client's board in a state the scheduler is not in, and
        dispatching again would hand out a desk somebody is already using.
        """
        with patch.object(scheduler, "set_idle", return_value=False), \
             patch.object(scheduler, "broadcast_slot") as broadcast_slot, \
             patch.object(scheduler, "dispatch_next") as dispatch_next:

            result = scheduler.release_and_dispatch(
                TEAM, SLOT, expected_holder="ada-user"
            )

        assert result is None
        broadcast_slot.assert_not_called()
        dispatch_next.assert_not_called()

    def test_a_real_release_announces_idle_then_dispatches(self):
        with patch.object(scheduler, "set_idle", return_value=True), \
             patch.object(scheduler, "broadcast_slot") as broadcast_slot, \
             patch.object(scheduler, "dispatch_next", return_value="researcher"):

            result = scheduler.release_and_dispatch(
                TEAM, SLOT, expected_holder="ada-user"
            )

        assert result == "researcher"
        broadcast_slot.assert_called_once_with(TEAM, SLOT, "IDLE", None)

    def test_the_holder_is_passed_through_to_the_write(self):
        """`release_and_dispatch` must not invent its own expectation."""
        with patch.object(scheduler, "set_idle", return_value=False) as set_idle:
            scheduler.release_and_dispatch(TEAM, SLOT, expected_holder="ada-user")

        set_idle.assert_called_once_with(TEAM, SLOT, "ada-user")


# --- release_agent: who is allowed to free a desk --------------------------


class TestReleaseAgentRoute:
    """The router route. Patched at `shared.*` because `conftest.py` puts
    `backend/` on the path, so the test and `router/app.py` import the same
    module objects — the same arrangement `sam build` produces."""

    def _run(self, holder, requester, is_admin=False, body=None):
        from router import app as router

        with patch("shared.state.slot_holder", return_value=holder), \
             patch("shared.state.connection_user", return_value=requester), \
             patch("shared.state.connection_is_admin", return_value=is_admin), \
             patch("shared.broadcast.send_to_connection") as send, \
             patch("shared.scheduler.release_and_dispatch") as release, \
             patch("shared.scheduler.dispatch_next") as dispatch_next:

            router._release_agent(
                TEAM, "conn-1", body or {"agent_type": SLOT}
            )
            return send, release, dispatch_next

    def test_a_bystander_cannot_free_someone_elses_desk(self):
        send, release, _ = self._run(holder="ada-user", requester="bystander")

        release.assert_not_called()
        assert send.call_count == 1
        assert send.call_args.args[1]["event"] == "error"

    def test_the_holder_can_free_their_own_desk(self):
        _, release, _ = self._run(holder="ada-user", requester="ada-user")

        release.assert_called_once()
        assert release.call_args.kwargs["expected_holder"] == "ada-user"

    def test_an_admin_can_free_a_wedged_desk(self):
        """The case the button was written for: the runner died holding the
        desk and the person it belonged to has closed the tab."""
        _, release, _ = self._run(
            holder="ada-user", requester="operator", is_admin=True
        )

        release.assert_called_once()
        # The write expects whoever is actually sitting there, not the admin.
        assert release.call_args.kwargs["expected_holder"] == "ada-user"

    def test_authorisation_ignores_the_user_id_on_the_frame(self):
        """`user_id` in the body is client-supplied. Trusting it here would
        make the whole check decorative."""
        send, release, _ = self._run(
            holder="ada-user",
            requester="bystander",
            body={"agent_type": SLOT, "user_id": "ada-user"},
        )

        release.assert_not_called()
        assert send.call_args.args[1]["event"] == "error"

    def test_an_idle_desk_is_a_dispatch_poke_not_a_release(self):
        """Nobody to authorise against and nothing to free — but the queue may
        still have a pinned handoff waiting for a desk that is now free.
        `ws_smoke.py` section 25 depends on this."""
        send, release, dispatch_next = self._run(holder=None, requester="anyone")

        release.assert_not_called()
        send.assert_not_called()  # not an error
        dispatch_next.assert_called_once_with(TEAM)

    def test_an_unknown_desk_is_still_rejected(self):
        send, release, _ = self._run(
            holder=None, requester="anyone", body={"agent_type": "nonesuch"}
        )

        release.assert_not_called()
        assert send.call_args.args[1]["event"] == "error"


# --- The runner's finally block --------------------------------------------


class TestRunnerRelease:
    def test_the_runner_releases_under_its_own_task_user(self):
        """The task's own user is the expectation. This is the argument that
        makes a redelivered task harmless instead of destructive."""
        from agent_runner import app as runner

        task = {
            "slot_id": SLOT,
            "user_id": "ada-user",
            "team_id": TEAM,
            "prompt": "anything",
        }

        # Refusing on budget returns early and still runs `finally`, which is
        # the block under test, without reaching a model call.
        with patch.object(runner, "_refuse_over_budget", return_value=True), \
             patch("shared.scheduler.release_and_dispatch") as release:
            runner._handle(task)

        release.assert_called_once()
        assert release.call_args.kwargs["expected_holder"] == "ada-user"
