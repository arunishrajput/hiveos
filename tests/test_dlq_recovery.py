"""Tests for DLQ inspection, recovery, replay, and idempotency clearing mechanics (Bug G)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from botocore.exceptions import ClientError

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from shared import dlq, state
from agent_runner import app as runner_app

TEAM = "test-team"
MAIN_QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/hiveos-agent-tasks"
DLQ_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/hiveos-agent-tasks-dlq"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("QUEUE_URL", MAIN_QUEUE_URL)
    monkeypatch.setenv("DLQ_URL", DLQ_URL)
    monkeypatch.setenv("TABLE_NAME", "hiveos-state")


class TestDLQInspection:
    @patch("shared.dlq.sqs")
    def test_inspect_dlq_empty(self, mock_sqs_fn):
        mock_sqs = MagicMock()
        mock_sqs.receive_message.return_value = {"Messages": []}
        mock_sqs_fn.return_value = mock_sqs

        items = dlq.inspect_dlq(dlq_url=DLQ_URL)
        assert items == []
        mock_sqs.receive_message.assert_called_once()

    @patch("shared.dlq.sqs")
    def test_inspect_dlq_with_messages(self, mock_sqs_fn):
        mock_sqs = MagicMock()
        valid_task = {
            "team_id": TEAM,
            "slot_id": "ada",
            "user_id": "alice",
            "task_id": "task-001",
            "hops": 0,
            "prompt": "Test prompt",
        }
        mock_sqs.receive_message.return_value = {
            "Messages": [
                {
                    "MessageId": "msg-1",
                    "ReceiptHandle": "rcpt-1",
                    "Body": json.dumps(valid_task),
                    "Attributes": {"ApproximateReceiveCount": "5"},
                },
                {
                    "MessageId": "msg-2",
                    "ReceiptHandle": "rcpt-2",
                    "Body": "invalid-non-json",
                    "Attributes": {"ApproximateReceiveCount": "5"},
                },
            ]
        }
        mock_sqs_fn.return_value = mock_sqs

        items = dlq.inspect_dlq(dlq_url=DLQ_URL)
        assert len(items) == 2
        assert items[0]["message_id"] == "msg-1"
        assert items[0]["task"] == valid_task
        assert items[0]["parse_error"] is None

        assert items[1]["message_id"] == "msg-2"
        assert items[1]["task"] is None
        assert items[1]["parse_error"] is not None


class TestDLQRecoveryAndReplay:
    @patch("shared.state.table")
    def test_clear_idempotency_marker(self, mock_table_fn):
        mock_table = MagicMock()
        mock_table_fn.return_value = mock_table

        state.clear_idempotency_marker(TEAM, "task-999", hops=0)

        mock_table.delete_item.assert_called_once_with(
            Key={
                "PK": state.team_pk(TEAM),
                "SK": "IDEMPOTENCY#task-999#0",
            }
        )

    @patch("shared.state.clear_idempotency_marker")
    @patch("shared.dlq.sqs")
    def test_redrive_message_clears_idempotency_and_sends_to_main_queue(
        self, mock_sqs_fn, mock_clear_marker
    ):
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {"MessageId": "new-msg-123"}
        mock_sqs_fn.return_value = mock_sqs

        task_payload = {
            "team_id": TEAM,
            "slot_id": "ada",
            "user_id": "alice",
            "task_id": "task-abc",
            "hops": 0,
            "prompt": "Fix the build",
        }

        result = dlq.redrive_message(
            receipt_handle="handle-123",
            task_payload=task_payload,
            dlq_url=DLQ_URL,
            target_queue_url=MAIN_QUEUE_URL,
            reset_idempotency=True,
        )

        assert result["success"] is True
        assert result["new_message_id"] == "new-msg-123"
        assert result["task_id"] == "task-abc"

        # 1. Cleared idempotency marker
        mock_clear_marker.assert_called_once_with(TEAM, "task-abc", hops=0)

        # 2. Sent to main queue
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl=MAIN_QUEUE_URL,
            MessageBody=json.dumps(task_payload),
        )

        # 3. Deleted from DLQ
        mock_sqs.delete_message.assert_called_once_with(
            QueueUrl=DLQ_URL,
            ReceiptHandle="handle-123",
        )

    @patch("shared.dlq.redrive_message")
    @patch("shared.dlq.inspect_dlq")
    def test_redrive_all(self, mock_inspect, mock_redrive_msg):
        task_1 = {"team_id": TEAM, "task_id": "t1", "prompt": "p1"}
        task_2 = {"team_id": TEAM, "task_id": "t2", "prompt": "p2"}

        mock_inspect.side_effect = [
            [
                {"message_id": "m1", "receipt_handle": "r1", "task": task_1},
                {"message_id": "m2", "receipt_handle": "r2", "task": task_2},
                {"message_id": "m3", "receipt_handle": "r3", "task": None, "parse_error": "JSON error"},
            ],
            [],  # Second batch is empty
        ]
        mock_redrive_msg.return_value = {"success": True}

        summary = dlq.redrive_all(dlq_url=DLQ_URL, target_queue_url=MAIN_QUEUE_URL)

        assert summary["redriven"] == 2
        assert summary["failed"] == 1
        assert summary["total"] == 3
        assert mock_redrive_msg.call_count == 2

    @patch("shared.dlq.sqs")
    def test_purge_dlq(self, mock_sqs_fn):
        mock_sqs = MagicMock()
        mock_sqs_fn.return_value = mock_sqs

        res = dlq.purge_dlq(dlq_url=DLQ_URL)
        assert res["ok"] is True
        mock_sqs.purge_queue.assert_called_once_with(QueueUrl=DLQ_URL)


class TestRunnerReplayWithIdempotencyClear:
    @patch("agent_runner.app.state.table")
    def test_replayed_task_executes_when_marker_cleared(self, mock_table_fn):
        """Proves that clearing the idempotency marker enables a redriven task to execute."""
        mock_table = MagicMock()
        mock_table_fn.return_value = mock_table

        task = {
            "team_id": TEAM,
            "slot_id": "ada",
            "user_id": "alice",
            "task_id": "task-retry-01",
            "hops": 0,
        }

        # 1. Normal run succeeds in claiming marker
        assert runner_app._already_delivered(TEAM, task) is False
        mock_table.put_item.assert_called_once()

        # 2. If marker was left in DB (old state), delivery is rejected as duplicate
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}},
            "PutItem",
        )
        assert runner_app._already_delivered(TEAM, task) is True

        # 3. DLQ recovery clears the marker:
        state.clear_idempotency_marker(TEAM, "task-retry-01", hops=0)
        mock_table.delete_item.assert_called_once_with(
            Key={
                "PK": state.team_pk(TEAM),
                "SK": "IDEMPOTENCY#task-retry-01#0",
            }
        )

        # 4. Subsequent redrive run succeeds in claiming marker again:
        mock_table.put_item.side_effect = None
        assert runner_app._already_delivered(TEAM, task) is False
