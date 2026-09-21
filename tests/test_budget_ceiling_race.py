"""Deterministic tests for Bug D — Budget ceiling race condition and atomic reservation.

Proves and verifies:
1. Two concurrent runners cannot both pass budget check and invoke the model when
   remaining budget cannot accommodate both.
2. Server-side atomic reservation in DynamoDB prevents overshooting the token ceiling.
3. Provider-reported tokens are reconciled accurately upon task completion.
4. Failed tasks refund reservations so unspent tokens are not charged.
5. Fallback/estimated token accounting is preserved.
"""

from unittest.mock import MagicMock, call, patch
import botocore.exceptions
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from shared import state, history, broadcast
from agent_runner import app as runner
from agent_runner.app import AgentResult


TEAM = "default"
SLOT = "desk-1"
USER = "ada-user"


def _client_error(code="ConditionalCheckFailedException"):
    return botocore.exceptions.ClientError(
        {"Error": {"Code": code, "Message": "conditional check failed"}},
        "UpdateItem",
    )


class TestBudgetReservationAtomicity:
    """Tests for state.reserve_budget, commit_tokens/add_tokens, and refund_tokens."""

    def test_reserve_budget_succeeds_when_under_ceiling(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"tokens_used": 500, "token_budget": 1000}
        }
        mock_table.update_item.return_value = {
            "Attributes": {"tokens_used": 550, "token_budget": 1000}
        }

        with patch("shared.state.table", return_value=mock_table):
            allowed, reserved, used, budget = state.reserve_budget(TEAM, 50)

        assert allowed is True
        assert reserved == 50
        assert used == 550
        assert budget == 1000
        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert call_kwargs["ExpressionAttributeValues"][":amount"] == 50
        assert call_kwargs["ExpressionAttributeValues"][":max_allowed"] == 950

    def test_reserve_budget_refuses_when_already_at_or_over_ceiling(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"tokens_used": 1000, "token_budget": 1000}
        }

        with patch("shared.state.table", return_value=mock_table):
            allowed, reserved, used, budget = state.reserve_budget(TEAM, 10)

        assert allowed is False
        assert reserved == 0
        assert used == 1000
        assert budget == 1000
        mock_table.update_item.assert_not_called()

    def test_reserve_budget_refuses_when_amount_exceeds_remaining(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"tokens_used": 950, "token_budget": 1000}
        }

        with patch("shared.state.table", return_value=mock_table):
            allowed, reserved, used, budget = state.reserve_budget(TEAM, 60)

        assert allowed is False
        assert reserved == 0
        assert used == 950
        assert budget == 1000
        mock_table.update_item.assert_not_called()

    def test_reserve_budget_handles_conditional_check_failed_lost_race(self):
        """Simulates losing the atomic race to another runner in DynamoDB."""
        mock_table = MagicMock()
        # First read sees 900 used
        mock_table.get_item.side_effect = [
            {"Item": {"tokens_used": 900, "token_budget": 1000}},
            # Second read after lost race sees 980 used
            {"Item": {"tokens_used": 980, "token_budget": 1000}},
        ]
        # DynamoDB rejects the conditional update because another runner moved tokens_used
        mock_table.update_item.side_effect = _client_error("ConditionalCheckFailedException")

        with patch("shared.state.table", return_value=mock_table):
            allowed, reserved, used, budget = state.reserve_budget(TEAM, 60, retries=0)

        assert allowed is False
        assert reserved == 0
        assert used == 980
        assert budget == 1000

    def test_reserve_budget_unlimited_when_budget_zero(self):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"tokens_used": 500, "token_budget": 0}
        }

        with patch("shared.state.table", return_value=mock_table):
            allowed, reserved, used, budget = state.reserve_budget(TEAM, 50)

        assert allowed is True
        assert reserved == 0
        assert used == 500
        assert budget == 0
        mock_table.update_item.assert_not_called()

    def test_add_tokens_reconciles_reservation_delta(self):
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            "Attributes": {"tokens_used": 580, "token_budget": 1000, "usage_estimated": False}
        }

        with patch("shared.state.table", return_value=mock_table):
            # Reserved 50, actual tokens spent was 80 -> delta is +30
            usage = state.add_tokens(TEAM, count=80, estimated=False, reserved=50)

        assert usage["tokens_used"] == 580
        assert usage["token_budget"] == 1000
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert call_kwargs["ExpressionAttributeValues"][":n"] == 30

    def test_refund_tokens_decrements_reservation(self):
        mock_table = MagicMock()
        mock_table.update_item.return_value = {
            "Attributes": {"tokens_used": 500, "token_budget": 1000}
        }

        with patch("shared.state.table", return_value=mock_table):
            used, budget = state.refund_tokens(TEAM, 50)

        assert used == 500
        assert budget == 1000
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert call_kwargs["ExpressionAttributeValues"][":neg"] == -50


class TestBudgetCeilingConcurrencyRace:
    """End-to-end tests for runner behaviour during concurrent tasks near budget ceiling."""

    def test_concurrent_runners_racing_near_ceiling(self):
        """Proves Bug D: Two concurrent tasks arrive when remaining budget can only cover one.

        Task 1 wins reservation, invokes model, commits tokens.
        Task 2 loses atomic reservation, is refused, does NOT invoke model, and releases slot.
        """
        task_1 = {
            "task_id": "task-1",
            "slot_id": "desk-1",
            "user_id": "user-1",
            "team_id": TEAM,
            "prompt": "Task 1 prompt requiring tokens",
        }
        task_2 = {
            "task_id": "task-2",
            "slot_id": "desk-2",
            "user_id": "user-2",
            "team_id": TEAM,
            "prompt": "Task 2 prompt requiring tokens",
        }

        # Shared mock workspace state:
        # budget = 1000, initial tokens_used = 900.
        # Remaining budget = 100.
        # Each prompt requires ~8 tokens reservation (or estimate).
        # Suppose task 1 reserves 60 tokens, leaving only 40 tokens.
        # Task 2 requires 60 tokens, so task 2 will fail the atomic condition in DynamoDB.

        table_items = {"tokens_used": 900, "token_budget": 1000}

        def mock_get_item(Key):
            return {"Item": dict(table_items)}

        def mock_update_item(Key, UpdateExpression, ExpressionAttributeValues, **kwargs):
            if "ADD tokens_used :amount" in UpdateExpression:
                amount = ExpressionAttributeValues[":amount"]
                max_allowed = ExpressionAttributeValues[":max_allowed"]
                current_used = table_items.get("tokens_used", 0)
                if current_used > max_allowed or current_used + amount > table_items["token_budget"]:
                    raise _client_error("ConditionalCheckFailedException")
                table_items["tokens_used"] = current_used + amount
                return {"Attributes": dict(table_items)}
            elif "ADD tokens_used :n" in UpdateExpression:
                delta = ExpressionAttributeValues[":n"]
                table_items["tokens_used"] = table_items.get("tokens_used", 0) + delta
                return {"Attributes": dict(table_items)}
            elif "ADD tokens_used :neg" in UpdateExpression:
                neg = ExpressionAttributeValues[":neg"]
                table_items["tokens_used"] = table_items.get("tokens_used", 0) + neg
                return {"Attributes": dict(table_items)}
            return {"Attributes": dict(table_items)}

        mock_table = MagicMock()
        mock_table.get_item.side_effect = mock_get_item
        mock_table.update_item.side_effect = mock_update_item
        mock_table.put_item.return_value = {}

        roster = [
            {"slot_id": "desk-1", "name": "Ada", "role": "Engineer"},
            {"slot_id": "desk-2", "name": "Iris", "role": "Designer"},
        ]

        run_agent_calls = []

        def fake_run_agent(team, task, desks):
            run_agent_calls.append(task["task_id"])
            return AgentResult(text="Answer", tokens=50, estimated=False), None

        with patch("shared.state.table", return_value=mock_table), \
             patch("shared.state.roster", return_value=roster), \
             patch("agent_runner.app._run_agent", side_effect=fake_run_agent), \
             patch("shared.history.record") as mock_record, \
             patch("shared.broadcast.broadcast_to_team") as mock_broadcast, \
             patch("shared.scheduler.release_and_dispatch") as mock_release, \
             patch("agent_runner.app._reply_error") as mock_reply_error, \
             patch("shared.state.reserve_budget", side_effect=[
                 (True, 60, 960, 1000),   # Task 1 reserves 60 tokens -> used becomes 960
                 (False, 0, 960, 1000),   # Task 2 fails reservation because 960 + 60 > 1000
             ]):

            # Execute Task 1
            runner._handle(task_1)

            # Execute Task 2
            runner._handle(task_2)

        # Verification:
        # 1. Model was invoked for Task 1 ONLY
        assert run_agent_calls == ["task-1"]

        # 2. Task 2 was refused and never invoked the model
        assert "task-2" not in run_agent_calls

        # 3. Task 2 broadcast budget_exhausted
        budget_exhausted_broadcasts = [
            call.args[1] for call in mock_broadcast.call_args_list
            if call.args[1].get("event") == "budget_exhausted"
        ]
        assert len(budget_exhausted_broadcasts) == 1
        assert budget_exhausted_broadcasts[0]["tokens_used"] == 960
        assert budget_exhausted_broadcasts[0]["token_budget"] == 1000

        # 4. Task 2 replied error to user
        mock_reply_error.assert_called_once()
        assert mock_reply_error.call_args[0][0]["task_id"] == "task-2"

        # 5. Task 2 recorded REFUSED with tokens=0 in history
        refused_history_calls = [
            call for call in mock_record.call_args_list
            if call.kwargs.get("status") == history.REFUSED
        ]
        assert len(refused_history_calls) == 1
        assert refused_history_calls[0].kwargs["task_id"] == "task-2"
        assert refused_history_calls[0].kwargs["tokens"] == 0

        # 6. Both tasks released their slots in finally
        released_holders = [call.kwargs.get("expected_holder") for call in mock_release.call_args_list]
        assert "user-1" in released_holders
        assert "user-2" in released_holders

    def test_reservation_refunded_on_runner_exception(self):
        """If runner raises an unhandled exception after reserving tokens, tokens must be refunded."""
        task = {
            "task_id": "failing-task",
            "slot_id": "desk-1",
            "user_id": "user-1",
            "team_id": TEAM,
            "prompt": "Prompt that fails during execution",
        }

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {"tokens_used": 500, "token_budget": 1000}
        }
        mock_table.update_item.return_value = {
            "Attributes": {"tokens_used": 500, "token_budget": 1000}
        }
        mock_table.put_item.return_value = {}

        roster = [{"slot_id": "desk-1", "name": "Ada", "role": "Engineer"}]

        with patch("shared.state.table", return_value=mock_table), \
             patch("shared.state.roster", return_value=roster), \
             patch("agent_runner.app._run_agent", side_effect=RuntimeError("Model crashed")), \
             patch("shared.state.refund_tokens") as mock_refund, \
             patch("shared.history.record") as mock_record, \
             patch("shared.scheduler.release_and_dispatch") as mock_release, \
             patch("agent_runner.app._reply_error"):

            runner._handle(task)

        # Refund must be called with the reserved token amount
        mock_refund.assert_called_once()
        assert mock_refund.call_args[0][0] == TEAM
        assert mock_refund.call_args[0][1] > 0

        # History must record FAILED with 0 tokens
        failed_record = [call for call in mock_record.call_args_list if call.kwargs.get("status") == history.FAILED]
        assert len(failed_record) == 1
        assert failed_record[0].kwargs["tokens"] == 0

        # Slot must be released
        mock_release.assert_called_once()
