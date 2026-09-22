"""The last-desk rule under concurrency.

`dismiss_agent` has always had two rules — never a `BUSY` desk, never the last
one — and both used to be decided by a read that happened before the delete:

    if len(roster(team)) <= 1:
        return "a floor needs at least one agent"
    table().delete_item(...)

Two frames arriving together each read a roster of two, each saw one to spare,
and each deleted. The floor ended up empty, which is the one state the
scheduler cannot work in: every claim fails, everything queues, and nothing
ever frees a slot to drain it. `ws_smoke.py` check 26 caught it on one run in
three — a race, not a regression.

`state.fire_agent` now decides both rules *in* the write. The last-desk rule is
a statement about other rows, which no single-item condition expression can
reach, so the write is a `TransactWriteItems`: delete the target, and in the
same transaction assert that some other desk — the *witness* — still exists.
After any transaction that commits, a desk remains: the witness was there at
the serialization point and the transaction did not remove it.

These tests evaluate the conditions against live fake state, the way
`test_budget_ceiling_race.py` does, so what they assert is the rule and not a
script. Every interleaving below is a genuine one: both invocations read a
roster of two before either has written anything.
"""

from unittest.mock import patch

import botocore.exceptions
import pytest

from shared import state

TEAM = "default"
PK = f"TEAM#{TEAM}"


def _slot(item):
    """The desk id out of a transaction item's key."""
    sk = item["Key"]["SK"]
    assert isinstance(sk, str), f"wire-format key in a document-client call: {sk!r}"
    return sk.split("#", 1)[1]


class FakeFloor:
    """The `AGENT#` rows of one workspace, with enough DynamoDB to be raced.

    It holds nothing but agent rows, so `query`'s SK-prefix narrowing is a
    no-op here and is not reimplemented. What *is* reimplemented faithfully is
    the transaction: conditions are evaluated against this object's live state
    at the moment of the write, and a cancelled transaction raises the same
    `ClientError` with the same positional `CancellationReasons` that DynamoDB
    returns. The expression strings are asserted rather than parsed, so the
    fake cannot quietly go on agreeing with a condition the code no longer
    sends.
    """

    DELETE_CONDITION = (
        "attribute_exists(PK) AND "
        "(attribute_not_exists(#status) OR #status <> :busy)"
    )
    WITNESS_CONDITION = "attribute_exists(PK)"

    def __init__(self, slot_ids, busy=()):
        self.rows = {
            slot_id: {
                "PK": PK,
                "SK": f"AGENT#{slot_id}",
                "slot_id": slot_id,
                "status": "BUSY" if slot_id in busy else "IDLE",
                "created_at": f"2026-09-22T09:00:{index:02d}.000000+00:00",
            }
            for index, slot_id in enumerate(slot_ids)
        }
        self.transactions = []
        self.name = "hiveos-state"
        # Fires once, during the next roster read, after that read has taken
        # its snapshot and before it returns. That is the TOCTOU window itself:
        # the caller has seen the floor as it was and has not yet written.
        #
        # It hangs off the *read* rather than off the write on purpose. Every
        # implementation of this rule reads the roster, so the interleavings
        # below can be run against the guard this fix replaced — which is how
        # they were shown to fail against it.
        self.before_next_roster_read = None
        self.meta = self._Meta(self)

    class _Meta:
        def __init__(self, floor):
            self.client = floor

    # --- what `agent_row` and `roster` read ---

    def get_item(self, Key):
        slot_id = Key["SK"].split("#", 1)[1]
        row = self.rows.get(slot_id)
        return {"Item": dict(row)} if row else {}

    def query(self, **kwargs):
        # Snapshot first, then let the competing dismissal run: what this read
        # returns is the floor as it stood *before* that write landed.
        snapshot = [dict(row) for row in self.rows.values()]
        hook, self.before_next_roster_read = self.before_next_roster_read, None
        if hook:
            hook()
        return {"Items": snapshot}

    # --- the write the rules now live in ---

    def transact_write_items(self, TransactItems):
        delete = TransactItems[0]["Delete"]
        witness = TransactItems[1]["ConditionCheck"]
        assert delete["ConditionExpression"] == self.DELETE_CONDITION
        assert witness["ConditionExpression"] == self.WITNESS_CONDITION
        assert delete["TableName"] == witness["TableName"] == self.name

        # Document format, the dialect `table().meta.client` speaks. Asserted
        # rather than tolerated: the first version of this fix passed
        # wire-format `{"S": ...}` here, the fake was written to match, and
        # every one of these tests passed while the deployed transaction was
        # cancelled as invalid on every call. A fake can agree with the code
        # and both be wrong about the service — so this one pins the format
        # that was measured against real DynamoDB.
        assert delete["Key"] == {"PK": PK, "SK": f"AGENT#{_slot(delete)}"}
        assert delete["ExpressionAttributeValues"] == {":busy": "BUSY"}
        target_id = _slot(delete)
        witness_id = _slot(witness)
        self.transactions.append((target_id, witness_id))

        target = self.rows.get(target_id)
        reasons = [
            {"Code": "None"} if target and target.get("status") != "BUSY"
            else {"Code": "ConditionalCheckFailed"},
            {"Code": "None"} if witness_id in self.rows
            else {"Code": "ConditionalCheckFailed"},
        ]
        if any(reason["Code"] != "None" for reason in reasons):
            raise botocore.exceptions.ClientError(
                {
                    "Error": {
                        "Code": "TransactionCanceledException",
                        "Message": "Transaction cancelled",
                    },
                    "CancellationReasons": reasons,
                },
                "TransactWriteItems",
            )

        del self.rows[target_id]
        return {}


@pytest.fixture
def running():
    """`fire_agent` against a fake floor, with nothing else stubbed."""

    def _run(floor):
        return patch("shared.state.table", return_value=floor)

    return _run


# --- The rules, uncontended -------------------------------------------------


class TestTheRules:
    def test_an_idle_desk_on_a_staffed_floor_is_dismissed(self, running):
        floor = FakeFloor(["desk-1", "desk-2", "desk-3"])

        with running(floor):
            assert state.fire_agent(TEAM, "desk-2") is None

        assert sorted(floor.rows) == ["desk-1", "desk-3"]
        # The witness is a desk that is not the target, chosen in roster order.
        assert floor.transactions == [("desk-2", "desk-1")]

    def test_the_last_desk_is_refused_without_a_write(self, running):
        floor = FakeFloor(["desk-1"])

        with running(floor):
            assert state.fire_agent(TEAM, "desk-1") == "a floor needs at least one agent"

        assert sorted(floor.rows) == ["desk-1"]
        # No witness exists, so there is nothing to attempt: the refusal costs
        # no write at all.
        assert floor.transactions == []

    def test_a_busy_desk_is_refused(self, running):
        floor = FakeFloor(["desk-1", "desk-2"], busy=["desk-2"])

        with running(floor):
            refused = state.fire_agent(TEAM, "desk-2")

        assert "working" in refused
        assert sorted(floor.rows) == ["desk-1", "desk-2"]

    def test_a_desk_that_does_not_exist_is_refused(self, running):
        floor = FakeFloor(["desk-1", "desk-2"])

        with running(floor):
            assert state.fire_agent(TEAM, "nonesuch") == "no such desk"

        assert floor.transactions == []

    def test_a_row_with_no_status_is_still_dismissable(self, running):
        """A workspace created before the roster became data.

        Those rows carry the runtime fields only. DynamoDB evaluates `<>`
        against a missing attribute as false, so a condition without the
        `attribute_not_exists` arm would refuse to dismiss exactly them.
        """
        floor = FakeFloor(["desk-1", "desk-2"])
        del floor.rows["desk-2"]["status"]

        with running(floor):
            assert state.fire_agent(TEAM, "desk-2") is None

        assert sorted(floor.rows) == ["desk-1"]


# --- The race ---------------------------------------------------------------


class TestTwoDismissalsAtOnce:
    def test_a_floor_of_two_cannot_be_emptied(self, running):
        """The reported bug, reproduced as the interleaving that caused it.

        Both invocations read a roster of two and neither has written: under
        the old guard both passed `len(roster) <= 1` and both deleted. Here the
        second write is tested against the first one's, and loses.
        """
        floor = FakeFloor(["desk-1", "desk-2"])
        also = []

        def dismiss_the_other():
            with running(floor):
                also.append(state.fire_agent(TEAM, "desk-2"))

        floor.before_next_roster_read = dismiss_the_other

        with running(floor):
            first = state.fire_agent(TEAM, "desk-1")

        # The invariant that outranks everything else in this file.
        assert len(floor.rows) == 1
        # One of the two was refused, and for the right reason.
        assert [first] + also == [
            "a floor needs at least one agent",
            None,
        ]

    def test_the_refusal_names_the_rule_the_smoke_suite_asserts(self, running):
        """`ws_smoke.py` check 26 matches on this wording."""
        floor = FakeFloor(["desk-1", "desk-2"])

        def dismiss_the_other():
            with running(floor):
                state.fire_agent(TEAM, "desk-2")

        floor.before_next_roster_read = dismiss_the_other

        with running(floor):
            refused = state.fire_agent(TEAM, "desk-1")

        assert "at least one agent" in refused

    def test_whichever_lands_first_wins_and_it_may_be_either(self, running):
        """Driven from both directions: the survivor is not a fixed desk.

        The smoke suite learned this the hard way — it hardcoded the survivor
        and failed on the run where the other one won. What is guaranteed is
        that *a* desk survives, not which.
        """
        for target, interloper in (("desk-1", "desk-2"), ("desk-2", "desk-1")):
            floor = FakeFloor(["desk-1", "desk-2"])

            def dismiss_the_other(slot_id=interloper):
                with running(floor):
                    state.fire_agent(TEAM, slot_id)

            floor.before_next_roster_read = dismiss_the_other

            with running(floor):
                refused = state.fire_agent(TEAM, target)

            assert list(floor.rows) == [target], target
            assert "at least one agent" in refused

    def test_a_staffed_floor_still_lets_both_dismissals_through(self, running):
        """The retry, and why it earns its place.

        On a floor of three, two dismissals of different desks are both legal.
        They pick each other as witness, so the second loses its condition
        check — but nothing about the floor refuses it, and a retry against a
        fresh roster finds another witness and commits. Without the retry this
        would be a refusal reading "a floor needs at least one agent" on a
        floor that still had two.
        """
        floor = FakeFloor(["desk-1", "desk-2", "desk-3"])
        also = []

        def dismiss_the_other():
            with running(floor):
                also.append(state.fire_agent(TEAM, "desk-1"))

        floor.before_next_roster_read = dismiss_the_other

        with running(floor):
            first = state.fire_agent(TEAM, "desk-2")

        assert (first, also) == (None, [None])
        assert list(floor.rows) == ["desk-3"]

    def test_a_desk_that_goes_busy_in_the_window_is_not_dismissed(self, running):
        """The smaller race, closed for free by folding BUSY into the write.

        A desk that starts a task between the read and the delete used to be
        removed out from under its runner.
        """
        floor = FakeFloor(["desk-1", "desk-2"])

        def it_starts_working():
            floor.rows["desk-2"]["status"] = "BUSY"

        floor.before_next_roster_read = it_starts_working

        with running(floor):
            refused = state.fire_agent(TEAM, "desk-2")

        assert "working" in refused
        assert sorted(floor.rows) == ["desk-1", "desk-2"]

    def test_a_desk_dismissed_twice_is_refused_the_second_time(self, running):
        """Two frames naming the *same* desk, not different ones."""
        floor = FakeFloor(["desk-1", "desk-2", "desk-3"])

        def somebody_else_got_there_first():
            del floor.rows["desk-2"]

        floor.before_next_roster_read = somebody_else_got_there_first

        with running(floor):
            assert state.fire_agent(TEAM, "desk-2") == "no such desk"

        assert sorted(floor.rows) == ["desk-1", "desk-3"]

    def test_a_floor_emptied_desk_by_desk_stops_at_the_last_one(self, running):
        """Five sequential dismissals, each reading after the last one wrote.

        No race here — this is the rule itself, driven to exhaustion, and it
        held before the fix too. It is in this file because it is the property
        the race broke, and it has to keep holding now that a different
        mechanism enforces it.
        """
        slot_ids = [f"desk-{n}" for n in range(1, 6)]
        floor = FakeFloor(slot_ids)
        outcomes = []

        with running(floor):
            for slot_id in slot_ids:
                outcomes.append(state.fire_agent(TEAM, slot_id))

        assert len(floor.rows) == 1
        assert outcomes == [None, None, None, None, "a floor needs at least one agent"]


# --- Failures that are not refusals ----------------------------------------


class TestInfrastructureIsNotARefusal:
    def test_throttling_raises_rather_than_refusing(self, running):
        """A busy table must not be reported to a room as a rule.

        The same reasoning as `reserve_budget`: a refusal invented out of an
        infrastructure error tells a team a desk could not be dismissed for a
        reason that was never true.
        """
        floor = FakeFloor(["desk-1", "desk-2"])

        def throttle(TransactItems):
            raise botocore.exceptions.ClientError(
                {"Error": {"Code": "ProvisionedThroughputExceededException",
                           "Message": "slow down"}},
                "TransactWriteItems",
            )

        floor.transact_write_items = throttle

        with running(floor):
            with pytest.raises(botocore.exceptions.ClientError) as caught:
                state.fire_agent(TEAM, "desk-2")

        assert caught.value.response["Error"]["Code"] == (
            "ProvisionedThroughputExceededException"
        )
        assert sorted(floor.rows) == ["desk-1", "desk-2"]

    def test_a_transaction_conflict_is_retried_rather_than_refused(self, running):
        """DynamoDB's own serialisation, not a rule about the floor."""
        floor = FakeFloor(["desk-1", "desk-2", "desk-3"])
        real = floor.transact_write_items
        conflicts = []

        def conflict_once(TransactItems):
            if not conflicts:
                conflicts.append(True)
                raise botocore.exceptions.ClientError(
                    {
                        "Error": {"Code": "TransactionCanceledException",
                                  "Message": "Transaction cancelled"},
                        "CancellationReasons": [
                            {"Code": "TransactionConflict"},
                            {"Code": "None"},
                        ],
                    },
                    "TransactWriteItems",
                )
            return real(TransactItems)

        floor.transact_write_items = conflict_once

        with running(floor):
            assert state.fire_agent(TEAM, "desk-2") is None

        assert sorted(floor.rows) == ["desk-1", "desk-3"]

    def test_a_floor_that_keeps_moving_gives_up_without_emptying(self, running):
        """The retry is bounded, and the bound is not a way to empty a floor."""
        floor = FakeFloor(["desk-1", "desk-2", "desk-3"])

        def always_conflict(TransactItems):
            raise botocore.exceptions.ClientError(
                {
                    "Error": {"Code": "TransactionCanceledException",
                              "Message": "Transaction cancelled"},
                    "CancellationReasons": [
                        {"Code": "TransactionConflict"},
                        {"Code": "None"},
                    ],
                },
                "TransactWriteItems",
            )

        floor.transact_write_items = always_conflict

        with running(floor):
            refused = state.fire_agent(TEAM, "desk-2")

        assert "try again" in refused
        assert len(floor.rows) == 3
