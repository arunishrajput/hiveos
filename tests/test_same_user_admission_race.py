"""Deterministic tests for Bug E — Same-user admission control race condition.

Proves and verifies:
1. Two concurrent `claim_agent` requests from the same user cannot both claim
   different idle slots or both enter the queue.
2. Admission is atomic: the first request succeeds and claims or enqueues; the second
   request receives `{"event": "error", "message": "you already have an agent running or queued"}`.
3. Multiple distinct users can claim idle slots concurrently without interference.
4. User admission lifecycle: freed on slot release, preserved across handoffs, and cleaned
   up if dispatch fails.
"""

import os
import threading
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from shared import state, scheduler, broadcast
from router import app as router


TEAM = "test-team"
SLOTS = ["ada", "iris"]


class InMemoryDynamoDBTable:
    """Thread-safe in-memory replica of DynamoDB table for race simulation."""

    def __init__(self):
        self._lock = threading.Lock()
        self.items = {}

    def _key(self, key_dict):
        return (key_dict.get("PK"), key_dict.get("SK"))

    def put_item(self, Item, ConditionExpression=None, **kwargs):
        with self._lock:
            k = self._key(Item)
            if ConditionExpression == "attribute_not_exists(SK)":
                if k in self.items:
                    error_response = {
                        "Error": {
                            "Code": "ConditionalCheckFailedException",
                            "Message": "The conditional request failed",
                        }
                    }
                    raise ClientError(error_response, "PutItem")
            self.items[k] = dict(Item)
            return {}

    def get_item(self, Key, **kwargs):
        with self._lock:
            k = self._key(Key)
            item = self.items.get(k)
            return {"Item": dict(item)} if item else {}

    def delete_item(self, Key, ConditionExpression=None, **kwargs):
        with self._lock:
            k = self._key(Key)
            if ConditionExpression == "attribute_exists(SK)":
                if k not in self.items:
                    error_response = {
                        "Error": {
                            "Code": "ConditionalCheckFailedException",
                            "Message": "The conditional request failed",
                        }
                    }
                    raise ClientError(error_response, "DeleteItem")
            self.items.pop(k, None)
            return {}

    def update_item(self, Key, UpdateExpression, ConditionExpression=None,
                    ExpressionAttributeNames=None, ExpressionAttributeValues=None, **kwargs):
        with self._lock:
            k = self._key(Key)
            item = dict(self.items.get(k, {}))
            names = ExpressionAttributeNames or {}
            values = ExpressionAttributeValues or {}

            # Condition check for slot claim: #s = :idle
            if ConditionExpression == "#s = :idle":
                status_attr = names.get("#s", "status")
                idle_val = values.get(":idle", "IDLE")
                if item.get(status_attr) != idle_val:
                    error_response = {
                        "Error": {
                            "Code": "ConditionalCheckFailedException",
                            "Message": "The conditional request failed",
                        }
                    }
                    raise ClientError(error_response, "UpdateItem")

            # Condition check for slot release: #u = :holder
            if ConditionExpression == "#u = :holder":
                user_attr = names.get("#u", "current_user")
                holder_val = values.get(":holder")
                if item.get(user_attr) != holder_val:
                    error_response = {
                        "Error": {
                            "Code": "ConditionalCheckFailedException",
                            "Message": "The conditional request failed",
                        }
                    }
                    raise ClientError(error_response, "UpdateItem")

            # Apply updates
            if "SET #s = :busy, #u = :user, claimed_at = :now" in UpdateExpression:
                item["status"] = values.get(":busy")
                item["current_user"] = values.get(":user")
                item["claimed_at"] = values.get(":now")
            elif "SET #s = :idle, #u = :null REMOVE claimed_at" in UpdateExpression:
                item["status"] = values.get(":idle")
                item["current_user"] = None
                item.pop("claimed_at", None)

            self.items[k] = item
            return {"Attributes": dict(item)}

    def query(self, KeyConditionExpression=None, **kwargs):
        with self._lock:
            results = []
            pk_val = f"TEAM#{state.clean_team(TEAM)}"
            sk_prefix = None
            if KeyConditionExpression is not None:
                if hasattr(KeyConditionExpression, "_values"):
                    for item_cond in KeyConditionExpression._values:
                        if type(item_cond).__name__ == "BeginsWith" or getattr(item_cond, "expression_operator", "") == "begins_with":
                            sk_prefix = item_cond._values[1]

            for (pk, sk), item in self.items.items():
                if pk == pk_val:
                    if sk_prefix is None or sk.startswith(sk_prefix):
                        results.append(dict(item))
            return {"Items": results}


@pytest.fixture
def mock_db(monkeypatch):
    db = InMemoryDynamoDBTable()
    monkeypatch.setattr(state, "table", lambda: db)
    # Seed team metadata and slots
    db.items[(f"TEAM#{TEAM}", "METADATA")] = {
        "PK": f"TEAM#{TEAM}",
        "SK": "METADATA",
        "token_budget": 500000,
        "tokens_used": 0,
    }
    for slot in SLOTS:
        db.items[(f"TEAM#{TEAM}", f"AGENT#{slot}")] = {
            "PK": f"TEAM#{TEAM}",
            "SK": f"AGENT#{slot}",
            "slot_id": slot,
            "status": "IDLE",
            "current_user": None,
        }
    monkeypatch.setenv("QUEUE_URL", "https://sqs.mock/queue")
    return db


class TestSameUserAdmissionAtomicity:
    """Unit checks on atomic user admission helpers."""

    def test_acquire_user_admission_succeeds_for_idle_user(self, mock_db):
        task_id = "task-1"
        assert state.acquire_user_admission(TEAM, "alice", task_id) is True
        assert state.is_user_active(TEAM, "alice") is True

    def test_acquire_user_admission_fails_when_already_active(self, mock_db):
        task_id_1 = "task-1"
        task_id_2 = "task-2"
        assert state.acquire_user_admission(TEAM, "alice", task_id_1) is True
        # Second call fails due to conditional check
        assert state.acquire_user_admission(TEAM, "alice", task_id_2) is False

    def test_distinct_users_can_acquire_concurrently(self, mock_db):
        assert state.acquire_user_admission(TEAM, "alice", "task-1") is True
        assert state.acquire_user_admission(TEAM, "bob", "task-2") is True
        assert state.is_user_active(TEAM, "alice") is True
        assert state.is_user_active(TEAM, "bob") is True

    def test_release_user_admission_frees_user(self, mock_db):
        assert state.acquire_user_admission(TEAM, "alice", "task-1") is True
        state.release_user_admission(TEAM, "alice")
        assert state.is_user_active(TEAM, "alice") is False
        # Can acquire again after release
        assert state.acquire_user_admission(TEAM, "alice", "task-2") is True


class TestClaimAgentConcurrencyRace:
    """Simulate concurrent claim_agent requests from the same user."""

    def test_concurrent_claim_agent_prevents_same_user_holding_two_slots(self, mock_db):
        """When both Ada and Iris are IDLE, two concurrent requests from Alice
        must result in exactly ONE slot claimed by Alice and ONE error returned.
        """
        sent_messages = []

        def mock_send(conn_id, payload):
            sent_messages.append((conn_id, payload))

        dispatched = []

        def mock_dispatch(team, slot_id, user_id, requested, prompt, connection_id, task_id=None, **kwargs):
            dispatched.append({"slot_id": slot_id, "user_id": user_id, "task_id": task_id})

        with patch("shared.broadcast.send_to_connection", side_effect=mock_send), \
             patch("shared.scheduler.dispatch", side_effect=mock_dispatch), \
             patch("shared.state.connection_user", return_value="alice"):

            # Request 1 from tab 1
            res1 = router._claim_agent(
                TEAM, "conn-1", {"agent_type": "ada", "prompt": "Write python code", "user_id": "alice"}
            )
            # Request 2 from tab 2 (or double click)
            res2 = router._claim_agent(
                TEAM, "conn-2", {"agent_type": "iris", "prompt": "Review architecture", "user_id": "alice"}
            )

        assert res1 == {"statusCode": 200}
        assert res2 == {"statusCode": 200}

        # Alice should only be dispatched ONCE
        assert len(dispatched) == 1
        assert dispatched[0]["user_id"] == "alice"
        assert dispatched[0]["slot_id"] == "ada"

        # Tab 2 must have received an error
        errors = [p for c, p in sent_messages if p.get("event") == "error"]
        assert len(errors) == 1
        assert "you already have an agent running or queued" in errors[0]["message"]

        # Only one desk is BUSY; the other is still IDLE
        ada_row = mock_db.items[(f"TEAM#{TEAM}", "AGENT#ada")]
        iris_row = mock_db.items[(f"TEAM#{TEAM}", "AGENT#iris")]
        assert ada_row["status"] == "BUSY"
        assert ada_row["current_user"] == "alice"
        assert iris_row["status"] == "IDLE"
        assert iris_row["current_user"] is None

    def test_concurrent_claim_agent_prevents_duplicate_enqueue(self, mock_db):
        """When all slots are BUSY, two concurrent requests from Alice must
        result in only ONE queued task and ONE error response.
        """
        # Set all slots to BUSY with other users
        mock_db.items[(f"TEAM#{TEAM}", "AGENT#ada")]["status"] = "BUSY"
        mock_db.items[(f"TEAM#{TEAM}", "AGENT#ada")]["current_user"] = "bob"
        mock_db.items[(f"TEAM#{TEAM}", "AGENT#iris")]["status"] = "BUSY"
        mock_db.items[(f"TEAM#{TEAM}", "AGENT#iris")]["current_user"] = "charlie"

        sent_messages = []

        def mock_send(conn_id, payload):
            sent_messages.append((conn_id, payload))

        with patch("shared.broadcast.send_to_connection", side_effect=mock_send), \
             patch("shared.state.connection_user", return_value="alice"):

            res1 = router._claim_agent(
                TEAM, "conn-1", {"prompt": "Queued task 1", "user_id": "alice"}
            )
            res2 = router._claim_agent(
                TEAM, "conn-2", {"prompt": "Queued task 2", "user_id": "alice"}
            )

        assert res1 == {"statusCode": 200}
        assert res2 == {"statusCode": 200}

        # Exactly ONE queue row exists for Alice
        queue_rows = [item for k, item in mock_db.items.items() if k[1].startswith("QUEUE#")]
        assert len(queue_rows) == 1
        assert queue_rows[0]["user_id"] == "alice"

        # Tab 2 received the admission error
        errors = [p for c, p in sent_messages if p.get("event") == "error"]
        assert len(errors) == 1
        assert "you already have an agent running or queued" in errors[0]["message"]

    def test_multithreaded_concurrent_claims_same_user(self, mock_db):
        """Run 10 simultaneous threads trying to claim agents for 'alice'."""
        sent_messages = []
        lock = threading.Lock()

        def mock_send(conn_id, payload):
            with lock:
                sent_messages.append((conn_id, payload))

        dispatched = []

        def mock_dispatch(team, slot_id, user_id, requested, prompt, connection_id, task_id=None, **kwargs):
            with lock:
                dispatched.append(slot_id)

        with patch("shared.broadcast.send_to_connection", side_effect=mock_send), \
             patch("shared.scheduler.dispatch", side_effect=mock_dispatch), \
             patch("shared.state.connection_user", return_value="alice"):

            threads = []
            for i in range(10):
                t = threading.Thread(
                    target=router._claim_agent,
                    args=(TEAM, f"conn-{i}", {"prompt": f"Task {i}", "user_id": "alice"}),
                )
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Exactly ONE thread must have succeeded in claiming a slot
        assert len(dispatched) == 1
        # Exactly 9 threads must have been refused with error
        errors = [p for c, p in sent_messages if p.get("event") == "error"]
        assert len(errors) == 9
        for err in errors:
            assert "you already have an agent running or queued" in err["message"]


class TestUserAdmissionLifecycle:
    """Test release, handoff, and failure recovery."""

    def test_slot_release_frees_user_admission(self, mock_db):
        task_id = "task-1"
        assert state.acquire_user_admission(TEAM, "alice", task_id) is True
        scheduler.try_claim(TEAM, "ada", "alice")

        # Slot is freed
        freed = scheduler.set_idle(TEAM, "ada", expected_holder="alice")
        assert freed is True
        assert state.is_user_active(TEAM, "alice") is False

        # User is free to claim again
        assert state.acquire_user_admission(TEAM, "alice", "task-2") is True

    def test_dispatch_failure_rolls_back_admission(self, mock_db):
        sent_messages = []

        def mock_send(conn_id, payload):
            sent_messages.append((conn_id, payload))

        def failing_dispatch(*args, **kwargs):
            raise RuntimeError("SQS unavailable")

        with patch("shared.broadcast.send_to_connection", side_effect=mock_send), \
             patch("shared.scheduler.dispatch", side_effect=failing_dispatch), \
             patch("shared.state.connection_user", return_value="alice"):

            with pytest.raises(RuntimeError, match="SQS unavailable"):
                router._claim_agent(
                    TEAM, "conn-1", {"agent_type": "ada", "prompt": "Failing task", "user_id": "alice"}
                )

        # Slot and user admission must be rolled back
        assert mock_db.items[(f"TEAM#{TEAM}", "AGENT#ada")]["status"] == "IDLE"
        assert state.is_user_active(TEAM, "alice") is False

    def test_handoff_retains_user_admission(self, mock_db):
        task = {
            "slot_id": "ada",
            "user_id": "alice",
            "task_id": "job-123",
            "prompt": "Initial prompt",
            "hops": 0,
            "connection_id": "conn-1",
        }
        state.set_user_admission(TEAM, "alice", "job-123")

        dispatched = []

        def mock_dispatch(team, slot_id, user_id, requested, prompt, connection_id, task_id=None, **kwargs):
            dispatched.append(slot_id)

        with patch("shared.scheduler.dispatch", side_effect=mock_dispatch):
            # Target slot iris is idle
            claimed = scheduler.hand_off(TEAM, task, "iris", "Passing to iris")

        assert claimed == "iris"
        assert len(dispatched) == 1
        assert state.is_user_active(TEAM, "alice") is True
