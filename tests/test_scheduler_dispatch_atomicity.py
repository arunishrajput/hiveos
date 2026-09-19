import pytest
import json
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError

TEAM       = "alpha"
SLOT_ID    = "coder"
USER_ID    = "user_A"
PROMPT     = "hello"
CONN_ID    = "conn-123"
AGENT_TYPE = "coder"

ORIGINAL_SK = "QUEUE#2024-01-01T00:00:00.000000#abcd1234"
ORIGINAL_TS = "2024-01-01T00:00:00.000000Z"

QUEUE_ITEM = {
    "PK": "TEAM#alpha",
    "SK": ORIGINAL_SK,
    "task_id": ORIGINAL_SK,
    "user_id": USER_ID,
    "agent_type": AGENT_TYPE,
    "prompt": PROMPT,
    "connection_id": CONN_ID,
    "enqueued_at": ORIGINAL_TS,
}

def _sqs_error():
    return ClientError(
        {"Error": {"Code": "SqsException", "Message": "SQS unavailable"}},
        "SendMessage",
    )


class TestEnqueue:

    def test_task_id_equals_sk(self):
        mock_table = MagicMock()
        mock_table.put_item.return_value = {}
        with patch("shared.state.table", return_value=mock_table), \
             patch("shared.state.team_pk", return_value="TEAM#alpha"), \
             patch("shared.state.now_iso", return_value=ORIGINAL_TS), \
             patch("shared.state.now_iso_micros",
                   return_value="2024-01-01T00:00:00.000000"):
            from shared import scheduler
            scheduler.enqueue(TEAM, USER_ID, AGENT_TYPE, PROMPT, CONN_ID)
            item = mock_table.put_item.call_args[1]["Item"]
            assert "task_id" in item
            assert item["task_id"] is not None
            assert item["task_id"] == item["SK"]


class TestDispatchNext:

    def _patches(self, sqs_side_effect=None):
        mock_sqs = MagicMock()
        if sqs_side_effect:
            mock_sqs.send_message.side_effect = sqs_side_effect
        else:
            mock_sqs.send_message.return_value = {"MessageId": "msg-1"}
        return {
            "queue_url":       patch.dict("os.environ", {"QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123/test"}),
            "idle_slots":      patch("shared.state.idle_slots",
                                     return_value=[SLOT_ID]),
            "take_next_task":  patch("shared.scheduler.take_next_task",
                                     return_value=QUEUE_ITEM),
            "claim_any":       patch("shared.scheduler.claim_any",
                                     return_value=SLOT_ID),
            "set_idle":        patch("shared.scheduler.set_idle"),
            "broadcast_slot":  patch("shared.scheduler.broadcast_slot"),
            "broadcast_queue": patch("shared.scheduler.broadcast_queue"),
            "requeue":         patch("shared.scheduler.requeue"),
            "sqs":             patch("shared.scheduler.sqs",
                                     return_value=mock_sqs),
        }, mock_sqs

    def test_task_id_in_sqs_payload(self):
        p, mock_sqs = self._patches()
        with p["queue_url"], p["idle_slots"], p["take_next_task"], p["claim_any"], \
             p["set_idle"], p["broadcast_slot"], p["broadcast_queue"], \
             p["requeue"], p["sqs"]:
            from shared import scheduler
            scheduler.dispatch_next(TEAM)
            _, kwargs = mock_sqs.send_message.call_args
            body = json.loads(kwargs["MessageBody"])
            assert body.get("task_id") == ORIGINAL_SK

    def test_task_requeued_when_sqs_fails(self):
        p, _ = self._patches(sqs_side_effect=_sqs_error())
        with p["queue_url"], p["idle_slots"], p["take_next_task"], p["claim_any"], \
             p["set_idle"], p["broadcast_slot"], p["broadcast_queue"], \
             p["requeue"] as mock_requeue, p["sqs"]:
            from shared import scheduler
            scheduler.dispatch_next(TEAM)
            mock_requeue.assert_called_once_with(TEAM, QUEUE_ITEM)

    def test_slot_released_when_sqs_fails(self):
        p, _ = self._patches(sqs_side_effect=_sqs_error())
        with p["queue_url"], p["idle_slots"], p["take_next_task"], p["claim_any"], \
             p["set_idle"] as mock_set_idle, p["broadcast_slot"], \
             p["broadcast_queue"], p["requeue"], p["sqs"]:
            from shared import scheduler
            scheduler.dispatch_next(TEAM)
            recovery = [
                c for c in mock_set_idle.call_args_list
                if SLOT_ID in str(c) and USER_ID in str(c)
            ]
            assert recovery

    def test_idle_broadcast_after_sqs_failure(self):
        p, _ = self._patches(sqs_side_effect=_sqs_error())
        with p["queue_url"], p["idle_slots"], p["take_next_task"], p["claim_any"], \
             p["set_idle"], p["broadcast_slot"] as mock_bs, \
             p["broadcast_queue"], p["requeue"], p["sqs"]:
            from shared import scheduler
            scheduler.dispatch_next(TEAM)
            assert any("IDLE" in str(c) for c in mock_bs.call_args_list)

    def test_no_requeue_on_success(self):
        p, _ = self._patches()
        with p["queue_url"], p["idle_slots"], p["take_next_task"], p["claim_any"], \
             p["set_idle"], p["broadcast_slot"], p["broadcast_queue"], \
             p["requeue"] as mock_requeue, p["sqs"]:
            from shared import scheduler
            scheduler.dispatch_next(TEAM)
            mock_requeue.assert_not_called()