"""Tests for history recording, persistence failure handling, and scheduler fairness."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from shared import history, state


TEAM = "test-team"


def _client_error(code="ProvisionedThroughputExceededException", status=400):
    return ClientError(
        {
            "Error": {"Code": code, "Message": f"Mock {code}"},
            "ResponseMetadata": {"HTTPStatusCode": status},
        },
        "PutItem",
    )


class TestHistoryPersistence:
    @patch("shared.state.table")
    def test_record_persists_item_successfully(self, mock_table_fn):
        mock_table = MagicMock()
        mock_table_fn.return_value = mock_table

        item = history.record(
            team=TEAM,
            user_id="alice",
            agent_type="ada",
            tokens=450,
            estimated=False,
            status=history.DONE,
            prompt="Analyze this code",
            requested_agent="iris",
            task_id="task-100",
            handoff_from="coder",
            agent_name="Ada Lovelace",
            handoff_from_name="Coder Agent",
            retries=3,
        )

        assert mock_table.put_item.call_count == 1
        written = mock_table.put_item.call_args.kwargs["Item"]
        assert written["PK"] == state.team_pk(TEAM)
        assert written["SK"].startswith("TASK#")
        assert written["user_id"] == "alice"
        assert written["agent_type"] == "ada"
        assert written["agent_name"] == "Ada Lovelace"
        assert written["requested_agent"] == "iris"
        assert written["tokens"] == 450
        assert written["status"] == history.DONE
        assert written["prompt"] == "Analyze this code"
        assert item == written

    @patch("time.sleep")
    @patch("shared.state.table")
    def test_record_retries_transient_error_and_succeeds(self, mock_table_fn, mock_sleep):
        mock_table = MagicMock()
        # Fails first attempt with throttling, succeeds on second
        mock_table.put_item.side_effect = [
            _client_error("ProvisionedThroughputExceededException"),
            {},
        ]
        mock_table_fn.return_value = mock_table

        item = history.record(
            team=TEAM,
            user_id="bob",
            agent_type="iris",
            tokens=200,
            estimated=True,
            status=history.DONE,
            retries=3,
        )

        assert mock_table.put_item.call_count == 2
        assert mock_sleep.call_count == 1
        assert item["user_id"] == "bob"
        assert item["tokens"] == 200

    @patch("time.sleep")
    @patch("shared.state.table")
    def test_record_retries_botocore_endpoint_error_and_succeeds(self, mock_table_fn, mock_sleep):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = [
            EndpointConnectionError(endpoint_url="https://dynamodb.us-east-1.amazonaws.com"),
            {},
        ]
        mock_table_fn.return_value = mock_table

        item = history.record(
            team=TEAM,
            user_id="bob",
            agent_type="iris",
            tokens=150,
            estimated=False,
            status=history.DONE,
            retries=3,
        )

        assert mock_table.put_item.call_count == 2
        assert mock_sleep.call_count == 1
        assert item["user_id"] == "bob"

    @patch("time.sleep")
    @patch("shared.state.table")
    def test_record_does_not_retry_validation_error(self, mock_table_fn, mock_sleep):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = _client_error("ValidationException", status=400)
        mock_table_fn.return_value = mock_table

        with pytest.raises(ClientError) as exc_info:
            history.record(
                team=TEAM,
                user_id="alice",
                agent_type="ada",
                tokens=100,
                estimated=False,
                status=history.DONE,
                retries=3,
            )

        assert exc_info.value.response["Error"]["Code"] == "ValidationException"
        # Non-transient errors must NOT be retried:
        assert mock_table.put_item.call_count == 1
        assert mock_sleep.call_count == 0

    @patch("time.sleep")
    @patch("shared.state.table")
    def test_record_does_not_retry_programming_error(self, mock_table_fn, mock_sleep):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = TypeError("Mock programming error")
        mock_table_fn.return_value = mock_table

        with pytest.raises(TypeError):
            history.record(
                team=TEAM,
                user_id="alice",
                agent_type="ada",
                tokens=100,
                estimated=False,
                status=history.DONE,
                retries=3,
            )

        # Must fail immediately on programming bugs
        assert mock_table.put_item.call_count == 1
        assert mock_sleep.call_count == 0

    @patch("time.sleep")
    @patch("shared.state.table")
    def test_record_raises_on_persistent_failure(self, mock_table_fn, mock_sleep):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = _client_error("InternalServerError", status=500)
        mock_table_fn.return_value = mock_table

        with pytest.raises(ClientError) as exc_info:
            history.record(
                team=TEAM,
                user_id="alice",
                agent_type="ada",
                tokens=100,
                estimated=False,
                status=history.DONE,
                retries=3,
            )

        assert exc_info.value.response["Error"]["Code"] == "InternalServerError"
        assert mock_table.put_item.call_count == 3
        assert mock_sleep.call_count == 2


class TestFairnessAndAccountingImpact:
    def test_missing_task_record_corrupts_fair_order(self):
        """Demonstrates that an unwritten TASK# row inverts fair scheduling priority.

        Bob ran a task at T=100.
        Alice ran a task at T=200, but if Alice's TASK# write was swallowed/lost:
        - state._served_from() has Bob at T=100 and Alice as None ("").
        - fair_order() falsely sorts Alice (least recently served = "") BEFORE Bob!
        When Alice's TASK# write is persisted:
        - state._served_from() has Bob at T=100 and Alice at T=200.
        - fair_order() correctly prioritizes Bob over Alice.
        """
        bob_task_sk = "TASK#2026-09-22T10:00:00.000000#11111111"
        alice_task_sk = "TASK#2026-09-22T10:05:00.000000#22222222"

        # 1. Swallowed write: only Bob's task exists in DB
        corrupted_tasks = [
            {"SK": bob_task_sk, "user_id": "bob"},
        ]
        corrupted_served = state._served_from(corrupted_tasks)
        queue_items = [
            {"SK": "QUEUE#2026-09-22T10:10:00.000000#1", "user_id": "alice", "created_at": "2026-09-22T10:10:00Z"},
            {"SK": "QUEUE#2026-09-22T10:10:00.000000#2", "user_id": "bob", "created_at": "2026-09-22T10:10:00Z"},
        ]
        corrupted_order = state.fair_order(TEAM, queue_items, served=corrupted_served)
        # In corrupted state, Alice jumps the queue ahead of Bob because Alice appears never served
        assert corrupted_order[0]["user_id"] == "alice"

        # 2. Correctly persisted state: both Bob and Alice have TASK# rows
        persisted_tasks = [
            {"SK": bob_task_sk, "user_id": "bob"},
            {"SK": alice_task_sk, "user_id": "alice"},
        ]
        correct_served = state._served_from(persisted_tasks)
        correct_order = state.fair_order(TEAM, queue_items, served=correct_served)
        # In correct state, Bob (who waited longer since 10:00 vs 10:05) is served first
        assert correct_order[0]["user_id"] == "bob"

    def test_missing_task_record_causes_spend_divergence(self):
        """Demonstrates that an unwritten TASK# row causes per-user spend to diverge from total tokens."""
        # 3 tasks ran, but task 3 write failed
        recorded_tasks = [
            {"user_id": "alice", "tokens": 500, "SK": "TASK#1"},
            {"user_id": "bob", "tokens": 300, "SK": "TASK#2"},
            # Alice's second task (700 tokens) failed to write TASK#
        ]
        spend = history.spend(recorded_tasks)
        spend_map = {row["user_id"]: row["tokens"] for row in spend}

        # Spend only reflects recorded rows (500 tokens for Alice, 300 for Bob = 800 total)
        assert spend_map["alice"] == 500
        assert spend_map["bob"] == 300
        total_from_history = sum(row["tokens"] for row in spend)
        assert total_from_history == 800  # Missing 700 tokens!

        # When all tasks are recorded:
        full_tasks = recorded_tasks + [{"user_id": "alice", "tokens": 700, "SK": "TASK#3"}]
        full_spend = history.spend(full_tasks)
        full_spend_map = {row["user_id"]: row["tokens"] for row in full_spend}
        assert full_spend_map["alice"] == 1200
        assert full_spend_map["bob"] == 300
        assert sum(row["tokens"] for row in full_spend) == 1500


class TestRunnerHandlingOnRecordFailure:
    @patch("agent_runner.app.broadcast.broadcast_to_team")
    @patch("agent_runner.app.history.record")
    @patch("shared.state.add_tokens")
    def test_record_failure_in_reply_rolls_back_tokens_added(
        self, mock_add_tokens, mock_record, mock_broadcast
    ):
        """If history.record() raises in _reply(), the settlement is rolled back so METADATA does not diverge.

        The rollback undoes the settling write rather than zeroing the task:
        `_reply` settles `result.tokens - reserved`, so backing that same
        amount out returns the counter to still holding the reservation, which
        is what `_handle`'s `finally` then releases. See the note in `_reply`.
        """
        from agent_runner import app

        mock_add_tokens.side_effect = [
            {"tokens_used": 1500, "usage_estimated": False},  # settle: +500 -1200
            {"tokens_used": 2200, "usage_estimated": False},  # rollback: +1200 -500
        ]
        mock_record.side_effect = _client_error("InternalServerError", status=500)

        task = {
            "slot_id": "ada",
            "user_id": "alice",
            "task_id": "task-abc",
            "prompt": "Hello",
        }
        result = MagicMock(tokens=500, estimated=False)
        names = {"ada": "Ada"}
        reserved = 1200

        with pytest.raises(ClientError):
            app._reply(TEAM, task, result, names, reserved)

        assert mock_add_tokens.call_count == 2
        mock_add_tokens.assert_has_calls([
            call(TEAM, 500, estimated=False, reserved=1200),
            call(TEAM, 1200 - 500),
        ])
        # Broadcasts should NOT have gone out
        assert mock_broadcast.call_count == 0

    @patch("agent_runner.app.scheduler.release_and_dispatch")
    @patch("agent_runner.app._reply_error")
    @patch("agent_runner.app.history.record")
    @patch("agent_runner.app._run_agent")
    @patch("shared.state.budget_state", return_value=(0, 1_000_000))
    @patch("shared.state.roster", return_value=[{"id": "ada", "name": "Ada"}])
    @patch("shared.state.table")
    def test_record_failure_in_reply_still_releases_slot(
        self, mock_table, mock_roster, mock_budget, mock_run_agent, mock_record, mock_reply_error, mock_release
    ):
        """If history.record() raises in _reply(), _handle catches it, replies error, and releases slot."""
        from agent_runner import app

        mock_run_agent.return_value = (
            MagicMock(tokens=150, estimated=False),
            None,
        )
        # record raises on write failure
        mock_record.side_effect = _client_error("InternalServerError", status=500)

        task = {
            "team_id": TEAM,
            "slot_id": "ada",
            "user_id": "alice",
            "task_id": "task-abc",
            "prompt": "Hello",
        }

        # _handle should catch the error, reply error, and release the slot
        app._handle(task)

        assert mock_reply_error.call_count == 1
        mock_reply_error.assert_called_once_with(task, "agent task failed")
        assert mock_release.call_count == 1
        mock_release.assert_called_once_with(TEAM, "ada", expected_holder="alice")
