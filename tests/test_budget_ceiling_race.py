"""The budget ceiling under concurrency — the reservation and its settlement.

The ceiling has always been checked immediately before the model call, which
is the only honest moment: a task can sit in the queue while the tasks ahead
of it spend what was left. What it used to do at that moment was *read* the
counter and decide, and commit the spend at the end of the task. Two runners
finishing their reads in the same instant therefore both saw room and both
invoked the model, and the overshoot grew with the number of desks rather than
staying at the one task's worth CONTRACT.md promises.

`state.reserve_budget` closes that window by asking and committing in one
conditional write, whose condition — `tokens_used < token_budget` — is
evaluated by DynamoDB against the committed row rather than against a number
this Lambda read a moment ago. The threshold is unchanged; what changed is
that the second runner is tested against the first one's reservation.

The reservation is a placeholder, not a bill. `state.add_tokens` settles it
against what the provider actually counted, and `_release_reservation` gives
it back on every path that never reached a reply. These tests are mostly about
that arithmetic: a placeholder that is not reconciled is a meter that lies,
which is the one failure this product cannot have.
"""

from unittest.mock import MagicMock, patch

import botocore.exceptions

from shared import state
from shared import history
from agent_runner import app as runner
from agent_runner.app import AgentResult

TEAM = "default"

# What a real task costs with tools, measured on the deployed build and
# recorded in CONTRACT.md. The reservation has to clear it; see the note on
# `RESERVATION_CEILING`.
MEASURED_TASK_TOKENS = 800

ROSTER = [
    {"slot_id": "desk-1", "name": "Ada", "role": "Engineer"},
    {"slot_id": "desk-2", "name": "Iris", "role": "Designer"},
]

TASK_1 = {
    "task_id": "task-1",
    "slot_id": "desk-1",
    "user_id": "user-1",
    "team_id": TEAM,
    "prompt": "summarise the quarter",
}
TASK_2 = {
    "task_id": "task-2",
    "slot_id": "desk-2",
    "user_id": "user-2",
    "team_id": TEAM,
    "prompt": "and draft the email",
}


def _client_error(code="ConditionalCheckFailedException"):
    return botocore.exceptions.ClientError(
        {"Error": {"Code": code, "Message": code}}, "UpdateItem"
    )


class FakeMetadata:
    """The METADATA row with just enough DynamoDB in it to be raced against.

    The condition is evaluated here, against this object's live state, which is
    the whole reason the race tests below mean anything: a test that stubbed
    `reserve_budget` out and handed it a scripted answer would be asserting its
    own script. The expression string is asserted rather than parsed, so the
    fake cannot quietly go on agreeing with a condition the code no longer
    sends.
    """

    RESERVE_CONDITION = (
        "attribute_exists(token_budget) AND "
        "(attribute_not_exists(tokens_used) OR tokens_used < token_budget)"
    )

    def __init__(self, tokens_used=0, token_budget=1000):
        self.row = {"tokens_used": tokens_used, "token_budget": token_budget}
        self.writes = []

    # --- the two calls the ceiling makes ---

    def get_item(self, Key):
        return {"Item": dict(self.row)}

    def put_item(self, **kwargs):
        return {}

    def update_item(
        self,
        Key,
        UpdateExpression,
        ExpressionAttributeValues,
        ConditionExpression=None,
        ReturnValues=None,
    ):
        assert UpdateExpression.startswith("ADD tokens_used :n")
        if ConditionExpression is not None:
            assert ConditionExpression == self.RESERVE_CONDITION
            budget = self.row.get("token_budget")
            if not budget or self.row.get("tokens_used", 0) >= budget:
                raise _client_error()
        self.writes.append(ExpressionAttributeValues[":n"])
        self.row["tokens_used"] = (
            self.row.get("tokens_used", 0) + ExpressionAttributeValues[":n"]
        )
        if ":e" in ExpressionAttributeValues:
            self.row["usage_estimated"] = ExpressionAttributeValues[":e"]
        return {"Attributes": dict(self.row)}


def _harness(table, run_agent):
    """Everything around the runner that is not the ceiling."""
    return [
        patch("shared.state.table", return_value=table),
        patch("shared.state.roster", return_value=ROSTER),
        patch("agent_runner.app._run_agent", side_effect=run_agent),
        patch("shared.history.record"),
        patch("shared.broadcast.broadcast_to_team"),
        patch("shared.scheduler.release_and_dispatch"),
        patch("agent_runner.app._reply_error"),
    ]


class _Running:
    def __init__(self, table, run_agent):
        self._patches = _harness(table, run_agent)

    def __enter__(self):
        self.mocks = [p.start() for p in self._patches]
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()
        return False

    @property
    def broadcasts(self):
        return [c.args[1] for c in self.mocks[4].call_args_list]

    @property
    def records(self):
        return [c.kwargs for c in self.mocks[3].call_args_list]

    @property
    def releases(self):
        return self.mocks[5]


# --- The reservation itself -------------------------------------------------


class TestReserveBudget:
    def test_a_task_with_room_is_admitted_and_the_counter_moves_first(self):
        """The commit is what admission *is* now, not a separate step later."""
        table = FakeMetadata(tokens_used=500, token_budget=1000)

        with patch("shared.state.table", return_value=table):
            admitted, reserved, used, budget = state.reserve_budget(TEAM, 120)

        assert admitted is True
        assert reserved == 120
        assert (used, budget) == (620, 1000)
        assert table.row["tokens_used"] == 620

    def test_a_spent_budget_refuses_and_reserves_nothing(self):
        table = FakeMetadata(tokens_used=1000, token_budget=1000)

        with patch("shared.state.table", return_value=table):
            admitted, reserved, used, budget = state.reserve_budget(TEAM, 120)

        assert admitted is False
        assert reserved == 0
        # The numbers the refusal reports are the ones that caused it, and the
        # counter is untouched — a refused task costs zero, which is the
        # clearest evidence the ceiling is a control and not a gauge.
        assert (used, budget) == (1000, 1000)
        assert table.row["tokens_used"] == 1000

    def test_the_last_token_still_buys_a_turn_and_the_hold_is_clamped_to_it(self):
        """The threshold did not move: budget left means the task runs.

        What is held back is clamped to what is there. A placeholder that
        pushed the counter past the ceiling would raise "Quota reached" on every
        client that loaded while the task ran — `state_snapshot` and
        `token_update` both latch on `tokens_used >= token_budget` — on a board
        that had not actually spent anything.
        """
        table = FakeMetadata(tokens_used=999, token_budget=1000)

        with patch("shared.state.table", return_value=table):
            admitted, reserved, _, _ = state.reserve_budget(TEAM, 1800)

        assert admitted is True
        assert reserved == 1
        # Parked exactly on the ceiling: high enough to refuse everybody else,
        # never higher than the meter can honestly show.
        assert table.row["tokens_used"] == 1000

    def test_a_reservation_never_reads_as_a_spent_quota(self):
        """The clamp, driven across every position under a small ceiling."""
        for used in range(0, 1000, 97):
            table = FakeMetadata(tokens_used=used, token_budget=1000)
            with patch("shared.state.table", return_value=table):
                state.reserve_budget(TEAM, 1800)
            assert table.row["tokens_used"] <= 1000, used

    def test_a_workspace_with_no_ceiling_reserves_nothing(self):
        table = FakeMetadata(tokens_used=500, token_budget=0)

        with patch("shared.state.table", return_value=table):
            admitted, reserved, used, budget = state.reserve_budget(TEAM, 120)

        assert admitted is True
        assert reserved == 0
        assert (used, budget) == (500, 0)
        # Nothing to enforce, so nothing is written at all.
        assert table.writes == []

    def test_throttling_is_not_laundered_into_a_refusal(self):
        """A busy table must not be reported to a team as a spent quota."""
        table = FakeMetadata(tokens_used=0, token_budget=1000)
        table.update_item = MagicMock(
            side_effect=_client_error("ProvisionedThroughputExceededException")
        )

        with patch("shared.state.table", return_value=table):
            try:
                state.reserve_budget(TEAM, 120)
            except botocore.exceptions.ClientError as exc:
                assert exc.response["Error"]["Code"] == "ProvisionedThroughputExceededException"
            else:
                raise AssertionError("a throttled write must raise, not refuse")


# --- Settling it ------------------------------------------------------------


class TestSettlement:
    def test_a_task_that_cost_less_than_it_reserved_gives_the_rest_back(self):
        table = FakeMetadata(tokens_used=1806, token_budget=10_000)

        with patch("shared.state.table", return_value=table):
            usage = state.add_tokens(TEAM, 800, estimated=False, reserved=1806)

        # 1,806 held, 800 actually spent: the write is the difference.
        assert table.writes == [-1006]
        assert usage["tokens_used"] == 800
        assert table.row["tokens_used"] == 800

    def test_a_task_that_overran_its_reservation_is_charged_the_difference(self):
        table = FakeMetadata(tokens_used=1806, token_budget=10_000)

        with patch("shared.state.table", return_value=table):
            state.add_tokens(TEAM, 2000, estimated=False, reserved=1806)

        assert table.writes == [194]
        assert table.row["tokens_used"] == 2000

    def test_without_a_reservation_it_adds_the_whole_cost(self):
        """The unlimited-workspace path, unchanged from before reservations."""
        table = FakeMetadata(tokens_used=0, token_budget=0)

        with patch("shared.state.table", return_value=table):
            state.add_tokens(TEAM, 800)

        assert table.writes == [800]

    def test_estimated_spend_is_still_sticky_through_the_settlement(self):
        table = FakeMetadata(tokens_used=1806, token_budget=10_000)

        with patch("shared.state.table", return_value=table):
            usage = state.add_tokens(TEAM, 300, estimated=True, reserved=1806)

        assert usage["estimated"] is True
        assert table.row["usage_estimated"] is True

    def test_a_refund_removes_exactly_the_placeholder(self):
        table = FakeMetadata(tokens_used=1806, token_budget=10_000)

        with patch("shared.state.table", return_value=table):
            used, budget = state.refund_tokens(TEAM, 1806)

        assert table.writes == [-1806]
        assert (used, budget) == (0, 10_000)

    def test_refunding_nothing_touches_nothing(self):
        table = FakeMetadata(tokens_used=500, token_budget=1000)

        with patch("shared.state.table", return_value=table):
            assert state.refund_tokens(TEAM, 0) == (500, 1000)

        assert table.writes == []


# --- The race ---------------------------------------------------------------


class TestTwoRunnersAtTheCeiling:
    def test_only_one_of_two_runners_is_admitted_on_the_last_token(self):
        """Both ask before either settles. That is the whole bug.

        With one token of room the old check said yes to both, because both
        read `used < budget` before either had written anything back.
        """
        table = FakeMetadata(tokens_used=999, token_budget=1000)

        with patch("shared.state.table", return_value=table):
            first = state.reserve_budget(TEAM, 1800)
            second = state.reserve_budget(TEAM, 1800)

        assert first[0] is True
        assert second[0] is False
        assert second[1] == 0

    def test_a_whole_floor_asking_at_once_cannot_all_be_admitted(self):
        """Why the reservation is sized to a task and not to the prompt.

        Four desks ask before any of them settles. A placeholder the size of a
        prompt — a dozen tokens — leaves the counter essentially where it was,
        so every one of them reads room and the floor spends four tasks against
        a budget with one left in it. A placeholder the size of a task does not.
        """
        table = FakeMetadata(tokens_used=0, token_budget=1000)

        with patch("shared.state.table", return_value=table):
            outcomes = [state.reserve_budget(TEAM, 1800)[0] for _ in range(4)]

        assert outcomes == [True, False, False, False]

    def test_spend_stays_inside_the_budget_plus_one_task(self):
        """The bound the ceiling actually promises, driven to exhaustion.

        Tasks are admitted and settled until the workspace refuses, with the
        reservation an honest over-estimate of what each one costs. The counter
        may cross the ceiling — by one task, which is the documented allowance —
        and it may not cross it twice.
        """
        table = FakeMetadata(tokens_used=0, token_budget=1000)
        cost = 800
        spent = 0

        with patch("shared.state.table", return_value=table):
            for _ in range(20):
                admitted, reserved, _, _ = state.reserve_budget(TEAM, 1800)
                if not admitted:
                    break
                spent += cost
                state.add_tokens(TEAM, cost, reserved=reserved)

        assert table.row["tokens_used"] == spent
        assert spent <= 1000 + cost

    def test_the_reservation_is_at_least_what_a_task_costs(self):
        """The constant, pinned to the number it is sized from.

        A task measures around 800 tokens with tools (CONTRACT.md). A
        placeholder smaller than that lets a floor of desks through the ceiling
        one prompt at a time, because each one leaves the counter near enough
        to where it found it that the next still reads room.
        """
        assert runner.RESERVATION_CEILING >= MEASURED_TASK_TOKENS

    def test_the_second_runner_never_calls_the_model(self):
        """End to end, with task 2 arriving while task 1 is at the model.

        The budget starts untouched and holds one task, so nothing but task
        1's own reservation can be what refuses task 2.
        """
        table = FakeMetadata(tokens_used=0, token_budget=1000)
        called = []

        def run(team, task, desks):
            called.append(task["task_id"])
            if task["task_id"] == "task-1":
                # The window the old read-then-check lost: task 1 is spending
                # and has not settled, and task 2 asks for its turn.
                runner._handle(dict(TASK_2))
            return AgentResult(text="answered", tokens=800, estimated=False), None

        with _Running(table, run) as running:
            runner._handle(dict(TASK_1))

        assert called == ["task-1"]
        refusals = [b for b in running.broadcasts if b["event"] == "budget_exhausted"]
        assert len(refusals) == 1
        # The refusal reports the counter that caused it, reservation included.
        assert refusals[0]["token_budget"] == 1000

        # Both desks still came back, which is the invariant that outranks
        # everything else in this file.
        assert running.releases.call_count == 2

    def test_the_counter_lands_on_what_was_actually_spent(self):
        """The placeholder must leave no trace once the provider has reported."""
        table = FakeMetadata(tokens_used=0, token_budget=10_000)

        def run(team, task, desks):
            return AgentResult(text="answered", tokens=800, estimated=False), None

        with _Running(table, run):
            runner._handle(dict(TASK_1))

        assert table.row["tokens_used"] == 800


# --- Releasing it -----------------------------------------------------------


class TestReleaseOnEveryPath:
    def test_a_failed_task_gives_its_reservation_back(self):
        table = FakeMetadata(tokens_used=0, token_budget=10_000)

        def run(team, task, desks):
            raise RuntimeError("the model crashed")

        with _Running(table, run) as running:
            runner._handle(dict(TASK_1))

        # A failed task costs the team nothing, and the ledger says so.
        assert table.row["tokens_used"] == 0
        failed = [r for r in running.records if r.get("status") == history.FAILED]
        assert len(failed) == 1 and failed[0]["tokens"] == 0

    def test_a_reservation_survives_a_failed_settlement(self):
        """If the accounting write itself fails, the hold is still outstanding."""
        table = FakeMetadata(tokens_used=0, token_budget=10_000)

        def run(team, task, desks):
            return AgentResult(text="answered", tokens=800, estimated=False), None

        with _Running(table, run):
            with patch("shared.state.add_tokens", side_effect=RuntimeError("boom")):
                runner._handle(dict(TASK_1))

        assert table.row["tokens_used"] == 0

    def test_a_failed_ledger_write_gives_the_hold_back_exactly_once(self):
        """The rollback in `_reply` and the refund in `finally` are one release.

        `history.record` raises now rather than swallowing (Bug F), so `_reply`
        can fail *after* `add_tokens` has already settled the reservation. The
        rollback there has to undo that settlement and nothing more — leaving
        the hold outstanding for `finally` to release — or the two paths both
        give the same placeholder back and the meter ends up below where the
        task found it.
        """
        table = FakeMetadata(tokens_used=0, token_budget=10_000)

        def run(team, task, desks):
            return AgentResult(text="answered", tokens=800, estimated=False), None

        with _Running(table, run) as running:
            running.mocks[3].side_effect = RuntimeError("dynamo is down")
            runner._handle(dict(TASK_1))

        # Back exactly where it started: the work is not in the ledger, so the
        # team is not charged for it, and the hold was released once.
        assert table.row["tokens_used"] == 0

    def test_a_release_that_fails_does_not_cost_the_desk(self):
        """The slot release outranks the refund and must still happen."""
        table = FakeMetadata(tokens_used=0, token_budget=10_000)

        def run(team, task, desks):
            raise RuntimeError("the model crashed")

        with _Running(table, run) as running:
            with patch("shared.state.refund_tokens", side_effect=RuntimeError("boom")):
                runner._handle(dict(TASK_1))

        running.releases.assert_called_once()

    def test_a_refused_task_reserves_nothing_and_still_frees_its_desk(self):
        table = FakeMetadata(tokens_used=10_000, token_budget=10_000)
        called = []

        def run(team, task, desks):
            called.append(task["task_id"])
            return AgentResult(text="", tokens=0, estimated=False), None

        with _Running(table, run) as running:
            runner._handle(dict(TASK_1))

        assert called == []
        assert table.row["tokens_used"] == 10_000
        running.releases.assert_called_once()

    def test_the_reservation_never_rides_on_the_task(self):
        """`task` is an SQS body the ledger and the handoff read back.

        The hold is a local in `_handle` precisely so it cannot end up on the
        wire, and this is the assertion that keeps it there.
        """
        table = FakeMetadata(tokens_used=0, token_budget=10_000)
        task = dict(TASK_1)

        def run(team, task, desks):
            return AgentResult(text="answered", tokens=800, estimated=False), None

        with _Running(table, run):
            runner._handle(task)

        assert task == TASK_1
