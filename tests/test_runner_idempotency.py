"""Exactly-once in the runner: a redelivered task must not be charged twice.

SQS is at-least-once. A task can arrive again either because the delivery
genuinely duplicated or because the previous run died holding its desk and the
message came back after the visibility timeout. Before the gate, the second
arrival called the model again and billed the team for the same piece of work
— on a product whose headline number is the meter, that is not cosmetic.

The gate is a conditional `IDEMPOTENCY#` write: whoever wins the put owns the
task. What these tests pin down is not only that a duplicate stops, but
*where* it stops — inside the try, so it still reaches the `finally`. The
runner's invariant 1 (a desk is released even when the task fails) outranks
this one: a redelivery is the only thing that can free a desk the previous run
died holding, so a gate placed before the try would turn the single recovery
path into a permanent deadlock. `test_duplicate_still_releases_the_desk` is
the test that says so, and it is the most important one here.

`_reply` is deliberately *not* stubbed — its dependencies are. Stubbing the
whole reply would make "a duplicate does not charge the team" vacuously true,
since `state.add_tokens` is reached through it.

Mocked rather than run against moto or deployed AWS, like the rest of `tests/`:
the invariant is which arguments reach DynamoDB and which calls are skipped,
and that is exactly what a mock can see.
"""

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError


TEAM = "alpha"
SLOT = "coder"
USER = "user_A"
TASK_ID = "a1b2c3d4e5f6"

TASK = {
    "team_id": TEAM,
    "slot_id": SLOT,
    "user_id": USER,
    "task_id": TASK_ID,
    "prompt": "hello",
    "connection_id": "conn-123",
    "requested_agent": SLOT,
    "hops": 0,
    "handoff_from": None,
}

# One desk, enough for `agents.from_row` to name it. `_handle` reads the roster
# before it does anything else, so a test that leaves this unpatched hangs
# rather than fails: `state.query_team` paginates until `LastEvaluatedKey` is
# falsy, and a bare MagicMock returns a truthy one forever.
ROSTER = [{"slot_id": SLOT, "name": "Ada", "role": "Engineer"}]

MARKER_SK = f"IDEMPOTENCY#{TASK_ID}"


def _client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "PutItem")


def _result():
    result = MagicMock()
    result.text = "response"
    result.tokens = 10
    result.estimated = False
    return result


class _Harness:
    """Everything `_handle` reaches past the gate, stubbed at the boundary.

    `marker_raises` fails only the `IDEMPOTENCY#` put, not every write — a
    throttled marker must not also break the ledger row written on the way out.
    """

    def __init__(self, marker_raises=None):
        self.marker_raises = marker_raises
        self.table = MagicMock()
        self.table.put_item.side_effect = self._put_item

    def _put_item(self, **kwargs):
        if self.marker_raises and kwargs.get("Item", {}).get("SK") == MARKER_SK:
            raise self.marker_raises
        return {}

    def __enter__(self):
        self._patches = {
            "table": patch("shared.state.table", return_value=self.table),
            "roster": patch("shared.state.roster", return_value=ROSTER),
            "budget": patch("shared.state.budget_state", return_value=(0, 1_000_000)),
            "add_tokens": patch("shared.state.add_tokens", return_value={}),
            "record": patch("shared.history.record"),
            "broadcast": patch("shared.broadcast.broadcast_to_team"),
            "release": patch("shared.scheduler.release_and_dispatch"),
            "run_agent": patch(
                "agent_runner.app._run_agent", return_value=(_result(), None)
            ),
            "reply_error": patch("agent_runner.app._reply_error"),
        }
        self.mocks = {name: p.start() for name, p in self._patches.items()}
        return self

    def __exit__(self, *exc):
        for p in self._patches.values():
            p.stop()
        return False

    def __getattr__(self, name):
        try:
            return self.__dict__["mocks"][name]
        except KeyError:
            raise AttributeError(name) from None

    def markers(self):
        """Every `IDEMPOTENCY#` put the runner attempted."""
        return [
            call.kwargs
            for call in self.table.put_item.call_args_list
            if call.kwargs.get("Item", {}).get("SK", "").startswith("IDEMPOTENCY#")
        ]


def _run(task=TASK, marker_raises=None):
    from agent_runner import app

    with _Harness(marker_raises) as harness:
        app._handle(task)
        return harness


def _duplicate():
    return _run(marker_raises=_client_error("ConditionalCheckFailedException"))


# --- The marker ------------------------------------------------------------


class TestMarker:
    def test_first_delivery_writes_a_marker(self):
        markers = _run().markers()
        assert len(markers) == 1
        assert markers[0]["Item"]["PK"] == f"TEAM#{TEAM}"
        assert markers[0]["Item"]["SK"] == MARKER_SK

    def test_the_marker_is_written_conditionally(self):
        """A plain put would overwrite the marker and defeat the whole gate."""
        assert _run().markers()[0]["ConditionExpression"] == "attribute_not_exists(SK)"

    def test_the_marker_expires(self):
        """Nothing reads these rows back, so they must not accumulate forever."""
        expires_at = _run().markers()[0]["Item"]["expires_at"]
        assert isinstance(expires_at, int) and expires_at > 0

    def test_a_first_delivery_runs_and_charges(self):
        """The control. Without this the duplicate assertions prove nothing."""
        harness = _run()
        harness.run_agent.assert_called_once()
        harness.add_tokens.assert_called_once()


# --- A duplicate delivery --------------------------------------------------


class TestDuplicate:
    def test_duplicate_does_not_call_the_model(self):
        _duplicate().run_agent.assert_not_called()

    def test_duplicate_does_not_charge_the_team(self):
        _duplicate().add_tokens.assert_not_called()

    def test_duplicate_writes_no_ledger_row(self):
        """The work was already recorded by the delivery that actually ran."""
        _duplicate().record.assert_not_called()

    def test_duplicate_still_releases_the_desk(self):
        """The one that matters. A duplicate must not deadlock the workspace.

        The previous run may have died *holding* this desk — a Lambda timeout,
        or a release that itself failed — and the redelivery is the only thing
        left that can free it. If the gate returns before the `finally`, that
        desk stays BUSY forever and every task queued behind it stops.

        Fails if `_already_delivered` is moved back out of the try block.
        """
        _duplicate().release.assert_called_once_with(TEAM, SLOT, expected_holder=USER)


# --- Errors that are not duplicates ----------------------------------------


class TestRealErrors:
    def test_a_throttle_is_not_read_as_a_duplicate(self):
        """Only a lost race means "already ran".

        A non-conditional error is treated like any other mid-task failure:
        the ledger records it, the requester is told, the desk is freed. What
        it must never do is return quietly — that would drop the task while
        looking like a successful skip. The adjacent `_refuse_over_budget`
        gate already handles a throttled read exactly this way.
        """
        from shared import history

        harness = _run(
            marker_raises=_client_error("ProvisionedThroughputExceededException")
        )
        harness.run_agent.assert_not_called()
        harness.record.assert_called_once()
        assert harness.record.call_args.kwargs["status"] == history.FAILED
        harness.reply_error.assert_called_once()
        harness.release.assert_called_once_with(TEAM, SLOT, expected_holder=USER)


# --- Tasks with nothing to key on ------------------------------------------


class TestNoTaskId:
    def test_a_task_without_an_id_still_runs(self):
        """Dropping real work to guard an undetectable duplicate is worse."""
        _run({**TASK, "task_id": None}).run_agent.assert_called_once()

    def test_a_task_without_an_id_writes_no_marker(self):
        assert _run({**TASK, "task_id": None}).markers() == []
