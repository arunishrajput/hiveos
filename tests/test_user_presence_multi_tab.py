"""Regression tests for multi-tab and same-user presence (Bug H).

The backend tracks WebSocket connections by `connection_id` (CONN#<connection_id>),
while user presence and floor representation are keyed by `user_id`.

Multi-tab / same-user invariants:
1. Connecting a 2nd tab for an existing user inherits the user's current avatar
   and position, and does not broadcast a redundant `user_joined` event.
2. Disconnecting one tab does not broadcast `user_left` if another tab for the
   same user remains active.
3. Disconnecting the user's final tab broadcasts `user_left`.
4. Moving an avatar on any tab updates all active connection rows for that user
   so DynamoDB state stays unified.
5. `state_snapshot` deduplicates members by `user_id` so snapshots always reflect
   unique active users with consistent coordinates.
6. Graceful handling of disconnected/missing connection rows.
"""

from decimal import Decimal
import os
from unittest.mock import MagicMock, call, patch
import pytest

from router import app as router
from shared import broadcast, state


TEAM = "alpha"


class FakeTable:
    """In-memory table simulating DynamoDB operations on CONN# rows."""

    def __init__(self):
        self.items = {}

    def put_item(self, Item):
        pk = Item["PK"]
        sk = Item["SK"]
        self.items[(pk, sk)] = dict(Item)

    def delete_item(self, Key, ReturnValues="NONE"):
        pk = Key["PK"]
        sk = Key["SK"]
        old = self.items.pop((pk, sk), None)
        if ReturnValues == "ALL_OLD":
            return {"Attributes": old}
        return {}

    def get_item(self, Key, ProjectionExpression=None):
        pk = Key["PK"]
        sk = Key["SK"]
        item = self.items.get((pk, sk))
        if not item:
            return {}
        if ProjectionExpression == "user_id":
            return {"Item": {"user_id": item.get("user_id")}}
        if ProjectionExpression == "is_admin":
            return {"Item": {"is_admin": item.get("is_admin")}}
        return {"Item": dict(item)}

    def update_item(
        self,
        Key,
        UpdateExpression,
        ConditionExpression=None,
        ExpressionAttributeValues=None,
        ReturnValues="NONE",
    ):
        from botocore.exceptions import ClientError

        pk = Key["PK"]
        sk = Key["SK"]
        if (pk, sk) not in self.items and ConditionExpression == "attribute_exists(SK)":
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Conditional check failed"}},
                "UpdateItem",
            )
        item = self.items.get((pk, sk), {"PK": pk, "SK": sk})
        if ExpressionAttributeValues:
            if ":x" in ExpressionAttributeValues:
                item["x"] = ExpressionAttributeValues[":x"]
            if ":y" in ExpressionAttributeValues:
                item["y"] = ExpressionAttributeValues[":y"]
        self.items[(pk, sk)] = item
        if ReturnValues == "ALL_NEW":
            return {"Attributes": dict(item)}
        return {}

    def query(self, **kwargs):
        kce = kwargs.get("KeyConditionExpression")
        pk_val = None
        sk_prefix = None

        def extract(cond):
            nonlocal pk_val, sk_prefix
            if hasattr(cond, "_values"):
                v = cond._values
                if len(v) == 2 and hasattr(v[0], "name"):
                    if v[0].name == "PK":
                        pk_val = v[1]
                    elif v[0].name == "SK":
                        sk_prefix = v[1]
                else:
                    for sub in v:
                        extract(sub)

        extract(kce)
        results = []
        for (pk, sk), item in self.items.items():
            if pk == pk_val:
                if sk_prefix is None or sk.startswith(sk_prefix):
                    results.append(dict(item))
        return {"Items": results}


@pytest.fixture
def fake_table(monkeypatch):
    monkeypatch.setenv("WS_ENDPOINT", "https://ws.fake.local")
    monkeypatch.setenv("TABLE_NAME", "hiveos-state-test")
    tbl = FakeTable()
    with patch("shared.state.table", return_value=tbl), \
         patch("shared.state.bind_connection") as bind, \
         patch("shared.state.unbind_connection") as unbind, \
         patch("shared.broadcast.send_to_connection", return_value=True):
        yield tbl, bind, unbind


class TestUserPresenceMultiTab:

    def test_first_connection_broadcasts_user_joined(self, fake_table):
        tbl, bind, _ = fake_table

        with patch("shared.state.ensure_team"), \
             patch("shared.state.passphrase_ok", return_value=True), \
             patch("shared.state.admin_token_ok", return_value=False), \
             patch("shared.broadcast.broadcast_to_team") as bcast:

            event = {"queryStringParameters": {"team": TEAM, "user_id": "alice", "avatar": "🐝"}}
            res = router._on_connect(event, "conn-1")
            assert res["statusCode"] == 200

            bcast.assert_called_once()
            args, kwargs = bcast.call_args
            assert args[0] == TEAM
            assert args[1]["event"] == "user_joined"
            assert args[1]["user_id"] == "alice"
            assert args[1]["avatar"] == "🐝"
            assert kwargs["exclude"] == "conn-1"
            assert (f"TEAM#{TEAM}", "CONN#conn-1") in tbl.items

    def test_second_tab_same_user_inherits_position_and_does_not_broadcast_joined(self, fake_table):
        tbl, bind, _ = fake_table

        with patch("shared.state.ensure_team"), \
             patch("shared.state.passphrase_ok", return_value=True), \
             patch("shared.state.admin_token_ok", return_value=False), \
             patch("shared.broadcast.broadcast_to_team") as bcast:

            # First connection
            router._on_connect(
                {"queryStringParameters": {"team": TEAM, "user_id": "alice", "avatar": "🐝"}},
                "conn-1",
            )
            assert bcast.call_count == 1

            # Alice moves on first tab to (45, 60)
            state.move_connection(TEAM, "conn-1", 45, 60)

            # Second connection for Alice
            res = router._on_connect(
                {"queryStringParameters": {"team": TEAM, "user_id": "alice", "avatar": "🐝"}},
                "conn-2",
            )
            assert res["statusCode"] == 200

            # user_joined should NOT be broadcast again for the second tab
            assert bcast.call_count == 1

            # conn-2 row in DynamoDB must inherit the (45, 60) position from conn-1
            conn2_item = tbl.items[(f"TEAM#{TEAM}", "CONN#conn-2")]
            assert conn2_item["x"] == Decimal(45)
            assert conn2_item["y"] == Decimal(60)
            assert conn2_item["user_id"] == "alice"

    def test_closing_one_tab_does_not_broadcast_user_left_when_second_tab_open(self, fake_table):
        tbl, bind, _ = fake_table

        with patch("shared.state.ensure_team"), \
             patch("shared.state.passphrase_ok", return_value=True), \
             patch("shared.state.admin_token_ok", return_value=False), \
             patch("shared.broadcast.broadcast_to_team") as bcast, \
             patch("shared.state.connection_team", return_value=TEAM):

            # Connect tab 1 and tab 2
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice"}}, "conn-1")
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice"}}, "conn-2")
            bcast.reset_mock()

            # Disconnect tab 1
            res = router._on_disconnect("conn-1")
            assert res["statusCode"] == 200

            # user_left must NOT be broadcast because conn-2 is still active
            bcast.assert_not_called()
            assert (f"TEAM#{TEAM}", "CONN#conn-1") not in tbl.items
            assert (f"TEAM#{TEAM}", "CONN#conn-2") in tbl.items

    def test_closing_last_tab_broadcasts_user_left(self, fake_table):
        tbl, bind, _ = fake_table

        with patch("shared.state.ensure_team"), \
             patch("shared.state.passphrase_ok", return_value=True), \
             patch("shared.state.admin_token_ok", return_value=False), \
             patch("shared.broadcast.broadcast_to_team") as bcast, \
             patch("shared.state.connection_team", return_value=TEAM):

            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice"}}, "conn-1")
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice"}}, "conn-2")
            bcast.reset_mock()

            # Disconnect tab 1: no user_left
            router._on_disconnect("conn-1")
            bcast.assert_not_called()

            # Disconnect tab 2: final connection, user_left must be broadcast
            router._on_disconnect("conn-2")
            bcast.assert_called_once_with(TEAM, {"event": "user_left", "user_id": "alice"})
            assert (f"TEAM#{TEAM}", "CONN#conn-2") not in tbl.items

    def test_avatar_movement_syncs_across_all_active_connections_of_user(self, fake_table):
        tbl, bind, _ = fake_table

        with patch("shared.state.ensure_team"), \
             patch("shared.state.passphrase_ok", return_value=True), \
             patch("shared.state.admin_token_ok", return_value=False):

            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice"}}, "conn-1")
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice"}}, "conn-2")
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "bob"}}, "conn-bob")

            # Alice moves avatar on conn-1
            user = state.move_connection(TEAM, "conn-1", 72, 84)
            assert user == "alice"

            # Both conn-1 and conn-2 rows must reflect (72, 84)
            assert tbl.items[(f"TEAM#{TEAM}", "CONN#conn-1")]["x"] == Decimal(72)
            assert tbl.items[(f"TEAM#{TEAM}", "CONN#conn-1")]["y"] == Decimal(84)
            assert tbl.items[(f"TEAM#{TEAM}", "CONN#conn-2")]["x"] == Decimal(72)
            assert tbl.items[(f"TEAM#{TEAM}", "CONN#conn-2")]["y"] == Decimal(84)

            # Bob's connection must NOT have moved
            assert tbl.items[(f"TEAM#{TEAM}", "CONN#conn-bob")]["x"] != Decimal(72)

    def test_state_snapshot_deduplicates_members_by_user_id(self, fake_table):
        tbl, bind, _ = fake_table

        with patch("shared.state.ensure_team"), \
             patch("shared.state.passphrase_ok", return_value=True), \
             patch("shared.state.admin_token_ok", return_value=False):

            # Seed team metadata
            tbl.put_item({"PK": f"TEAM#{TEAM}", "SK": "METADATA", "tokens_used": 0, "token_budget": 100000})

            # Alice with 2 tabs, Bob with 1 tab
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice", "avatar": "🐝"}}, "conn-1")
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "alice", "avatar": "🐝"}}, "conn-2")
            router._on_connect({"queryStringParameters": {"team": TEAM, "user_id": "bob", "avatar": "🦊"}}, "conn-3")

            snapshot = state.state_snapshot(TEAM)
            members = snapshot["members"]

            # Snapshot must have exactly 2 distinct members: alice and bob
            assert len(members) == 2
            user_ids = [m["user_id"] for m in members]
            assert "alice" in user_ids
            assert "bob" in user_ids

    def test_move_connection_nonexistent_returns_none(self, fake_table):
        tbl, bind, _ = fake_table
        res = state.move_connection(TEAM, "nonexistent-conn", 10, 20)
        assert res is None

    def test_disconnect_nonexistent_connection_safe(self, fake_table):
        tbl, bind, _ = fake_table
        with patch("shared.state.connection_team", return_value=TEAM), \
             patch("shared.broadcast.broadcast_to_team") as bcast:
            res = router._on_disconnect("already-gone-conn")
            assert res["statusCode"] == 200
            bcast.assert_not_called()
