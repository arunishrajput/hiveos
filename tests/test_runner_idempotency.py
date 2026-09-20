"""Regression tests for Bug C: no idempotency guard in the SQS runner.

Before the fix, a duplicate SQS delivery caused:
  - the model to be called a second time
  - tokens to be charged a second time
  - a second history row to be written

After the fix, the runner writes an IDEMPOTENCY# marker on first delivery.
A duplicate finds the marker already exists, gets
ConditionalCheckFailedException, logs it, and returns without calling
the model or charging tokens.
"""
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

TEAM_ID    = "alpha"
SLOT_ID    = "coder"
USER_ID    = "user_A"
TASK_ID    = "QUEUE#2024-01-01T00:00:00.000000#abcd1234"
PROMPT     = "hello"
CONN_ID    = "conn-123"

TASK = {
    "team_id":         TEAM_ID,
    "slot_id":         SLOT_ID,
    "user_id":         USER_ID,
    "task_id":         TASK_ID,
    "prompt":          PROMPT,
    "connection_id":   CONN_ID,
    "requested_agent": "coder",
    "hops":            0,
    "handoff_from":    None,
}


def _cce():
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException",
                   "Message": "condition not met"}},
        "PutItem",
    )


def _make_result():
    r = MagicMock()
    r.text = "response"
    r.tokens = 10
    r.estimated = False
    return r


def _patches(put_item_raises=None):
    mock_table = MagicMock()
    if put_item_raises:
        mock_table.put_item.side_effect = put_item_raises
    else:
        mock_table.put_item.return_value = {}

    return mock_table, {
        "table":      patch("shared.state.table", return_value=mock_table),
        "team_pk":    patch("shared.state.team_pk", return_value="TEAM#alpha"),
        "now_iso":    patch("shared.state.now_iso",
                            return_value="2024-01-01T00:00:00Z"),
        "budget":     patch("shared.state.budget_state",
                            return_value=(0, 100000)),
        "release":    patch("shared.scheduler.release_and_dispatch"),
        "run_agent":  patch("agent_runner.app._run_agent",
                            return_value=(_make_result(), None)),
        "reply":      patch("agent_runner.app._reply"),
    }


class TestRunnerIdempotency:

    def test_idempotency_marker_written_on_first_delivery(self):
        """First delivery must write an IDEMPOTENCY# row to DynamoDB."""
        mock_table, p = _patches()
        with p["table"], p["team_pk"], p["now_iso"], \
             p["budget"], p["release"], p["run_agent"], p["reply"]:
            from agent_runner import app
            app._handle(TASK)
            idempotency_puts = [
                c for c in mock_table.put_item.call_args_list
                if f"IDEMPOTENCY#{TASK_ID}" in str(c)
            ]
            assert idempotency_puts, \
                "First delivery must write an IDEMPOTENCY# marker to DynamoDB"

    def test_duplicate_delivery_does_not_call_model(self):
        """Second delivery must return early without calling the model."""
        _, p = _patches(put_item_raises=_cce())
        with p["table"], p["team_pk"], p["now_iso"], \
             p["budget"], p["release"], p["run_agent"] as mock_run, p["reply"]:
            from agent_runner import app
            app._handle(TASK)
            mock_run.assert_not_called()

    def test_duplicate_delivery_does_not_charge_tokens(self):
        """Second delivery must not call add_tokens."""
        _, p = _patches(put_item_raises=_cce())
        with p["table"], p["team_pk"], p["now_iso"], \
             p["budget"], p["release"], p["run_agent"], p["reply"], \
             patch("shared.state.add_tokens") as mock_tokens:
            from agent_runner import app
            app._handle(TASK)
            mock_tokens.assert_not_called()

    def test_task_without_task_id_still_runs(self):
        """Tasks with no task_id must not be blocked by the gate."""
        task_no_id = {**TASK, "task_id": None}
        _, p = _patches()
        with p["table"], p["team_pk"], p["now_iso"], \
             p["budget"], p["release"], p["run_agent"] as mock_run, p["reply"]:
            from agent_runner import app
            app._handle(task_no_id)
            mock_run.assert_called_once()

    def test_non_idempotency_dynamodb_error_propagates(self):
        """A real DynamoDB error must not be silently swallowed."""
        real_error = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException",
                       "Message": "throttled"}},
            "PutItem",
        )
        _, p = _patches(put_item_raises=real_error)
        with p["table"], p["team_pk"], p["now_iso"], \
             p["budget"], p["release"], p["run_agent"], p["reply"]:
            from agent_runner import app
            with pytest.raises(ClientError) as exc_info:
                app._handle(TASK)
            assert exc_info.value.response["Error"]["Code"] == \
                "ProvisionedThroughputExceededException"