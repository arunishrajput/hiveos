"""Bootstrapping a workspace must not undo what its members did to the floor.

`ensure_team` runs on **every** `$connect` — it is what lets a team exist the
moment somebody types its name, with no seeding step. It also wrote the two
starting desks every time, conditional only on the row being absent, which is
precisely the state `dismiss_agent` leaves behind. So the next person to
connect put Iris back: no `agent_spawned` frame, nothing in the activity log, a
desk simply returning to a floor that had just been cleared of it. An automatic
reconnect after a network blip was enough to trigger it.

Reproduced against the deployed stack before the fix (`resurrect1`):

    1. fresh workspace roster : ['coder', 'researcher']
    2. after dismissing Iris  : ['coder']
    3. after a NEW connect    : ['coder', 'researcher']   <- the bug

Mocked rather than run against moto or deployed AWS, for the same reason as
`test_scheduler_slot_release.py`: the invariant is *which writes are issued*,
and that is exactly what a mock can see. `ws_smoke.py` checks the deployed
behaviour.
"""

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from shared import agents, state


TEAM = "alpha"


def _conditional_failure():
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "exists"}},
        "PutItem",
    )


def _agent_writes(table):
    """The `AGENT#` rows `ensure_team` tried to write, by slot id."""
    return [
        call.kwargs["Item"]["SK"]
        for call in table.put_item.call_args_list
        if call.kwargs.get("Item", {}).get("SK", "").startswith("AGENT#")
    ]


def _roster(*slot_ids):
    return [{"slot_id": slot_id, "status": "IDLE"} for slot_id in slot_ids]


class TestEnsureTeam:
    def test_a_brand_new_workspace_gets_the_starting_roster(self):
        """The METADATA write is what says this workspace is new. When it
        succeeds, the desks that come with a workspace are part of creating
        it."""
        table = MagicMock()
        with patch("shared.state.table", return_value=table), patch(
            "shared.state.roster"
        ) as roster:
            state.ensure_team(TEAM)

        assert _agent_writes(table) == [
            f"AGENT#{seed['id']}" for seed in agents.STARTING_ROSTER
        ]
        # A workspace we just created cannot have a roster worth reading.
        roster.assert_not_called()

    def test_joining_an_existing_workspace_writes_no_desks(self):
        """The regression. A dismissed desk is an absent row, so a re-seed on
        every connect is indistinguishable from an undo."""
        table = MagicMock()
        # METADATA already there: somebody else created this workspace.
        table.put_item.side_effect = _conditional_failure()
        with patch("shared.state.table", return_value=table), patch(
            "shared.state.roster", return_value=_roster("coder")
        ):
            state.ensure_team(TEAM)

        assert _agent_writes(table) == [], (
            "joining a workspace re-seeded its starting roster, which silently "
            "resurrects any starting desk that was dismissed"
        )

    def test_a_dismissed_desk_stays_dismissed_across_many_connects(self):
        """The shape the bug actually had: one dismissal, then traffic."""
        table = MagicMock()
        table.put_item.side_effect = _conditional_failure()
        floor = _roster("coder")  # Iris has been dismissed

        with patch("shared.state.table", return_value=table), patch(
            "shared.state.roster", return_value=floor
        ):
            for _ in range(5):
                state.ensure_team(TEAM)

        assert _agent_writes(table) == []

    def test_a_workspace_with_no_desks_at_all_is_repaired(self):
        """A floor with zero desks can never dispatch anything — every claim
        fails and the queue never drains, which is why `fire_agent` refuses to
        remove the last one. It is only reachable if a bootstrap died between
        the METADATA write and the desks, and leaving it permanently dead is
        the worse trade."""
        table = MagicMock()
        table.put_item.side_effect = _conditional_failure()
        with patch("shared.state.table", return_value=table), patch(
            "shared.state.roster", return_value=[]
        ):
            state.ensure_team(TEAM)

        assert _agent_writes(table) == [
            f"AGENT#{seed['id']}" for seed in agents.STARTING_ROSTER
        ]

    def test_the_desks_are_still_written_conditionally(self):
        """Belt and braces on the repair path: several people reaching a new
        workspace in the same second must not each reset it."""
        table = MagicMock()
        with patch("shared.state.table", return_value=table), patch(
            "shared.state.roster", return_value=[]
        ):
            state.ensure_team(TEAM)

        for call in table.put_item.call_args_list:
            assert call.kwargs.get("ConditionExpression") == (
                "attribute_not_exists(PK)"
            )
