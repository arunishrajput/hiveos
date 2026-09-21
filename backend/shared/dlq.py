"""Dead-Letter Queue (DLQ) inspection, recovery, and replay mechanics for HiveOS.

When tasks repeatedly fail in the Agent Runner (e.g. Lambda timeouts, transient
outages, or unhandled exceptions), SQS moves them to the DLQ (`TaskDLQ`).

This module provides operational visibility and safe replay for dead-lettered tasks:
1. `inspect_dlq()`: Peek and inspect messages currently sitting in the DLQ.
2. `redrive_message()`: Safely re-dispatch a dead-lettered task to the main queue
   after clearing its `IDEMPOTENCY#` marker so it is not skipped as a duplicate,
   with atomic claim semantics to prevent duplicate re-dispatch if DLQ deletion fails.
3. `redrive_all()`: Batch recovery for all dead-lettered tasks in the DLQ.
4. `purge_dlq()`: Drain/clear the DLQ after operational review.
"""

import json
import os
import time
import boto3
from botocore.exceptions import ClientError

from . import history, scheduler, state

_sqs = None


def sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client("sqs")
    return _sqs


def get_dlq_url(override=None):
    if override:
        return override
    url = os.environ.get("DLQ_URL") or os.environ.get("DEAD_LETTER_QUEUE_URL")
    if url:
        return url
    try:
        res = sqs().get_queue_url(QueueName="hiveos-agent-tasks-dlq")
        return res.get("QueueUrl")
    except Exception:
        return None


def get_main_queue_url(override=None):
    if override:
        return override
    url = os.environ.get("QUEUE_URL")
    if url:
        return url
    try:
        res = sqs().get_queue_url(QueueName="hiveos-agent-tasks")
        return res.get("QueueUrl")
    except Exception:
        return None


def inspect_dlq(dlq_url=None, max_messages=10, visibility_timeout=0):
    """Inspect up to `max_messages` from the DLQ without removing them.

    By default, `visibility_timeout=0` is used for passive peeking so messages
    remain immediately visible to other tools/operators. Callers doing active
    batch recovery can specify `visibility_timeout > 0` to temporarily hold messages.

    Returns a list of message descriptors containing the raw SQS metadata and
    the parsed task payload.
    """
    url = get_dlq_url(dlq_url)
    if not url:
        raise ValueError("DLQ URL could not be determined. Set DLQ_URL or pass dlq_url.")

    items = []
    remaining = max(1, max_messages)

    while remaining > 0:
        batch_size = min(remaining, 10)
        resp = sqs().receive_message(
            QueueUrl=url,
            MaxNumberOfMessages=batch_size,
            AttributeNames=["All"],
            MessageAttributeNames=["All"],
            VisibilityTimeout=visibility_timeout,
        )
        msgs = resp.get("Messages", [])
        if not msgs:
            break

        for msg in msgs:
            raw_body = msg.get("Body", "")
            parsed_task = None
            parse_error = None
            try:
                parsed_task = json.loads(raw_body)
            except Exception as exc:
                parse_error = str(exc)

            items.append(
                {
                    "message_id": msg.get("MessageId"),
                    "receipt_handle": msg.get("ReceiptHandle"),
                    "attributes": msg.get("Attributes", {}),
                    "raw_body": raw_body,
                    "task": parsed_task,
                    "parse_error": parse_error,
                }
            )

        remaining -= len(msgs)
        # In passive inspection mode (visibility_timeout=0), prevent infinite loops over same messages
        if visibility_timeout == 0 or len(msgs) < batch_size:
            break

    return items


def redrive_message(
    receipt_handle,
    task_payload,
    dlq_url=None,
    target_queue_url=None,
    reset_idempotency=True,
):
    """Replay a dead-lettered task back to the main queue and remove it from DLQ.

    Safety semantics against partial failures:
    - Atomically claims the redrive in DynamoDB via `state.claim_dlq_redrive()`.
    - If step 2 (send to main queue) succeeds but step 3 (delete from DLQ) fails,
      the message remains in DLQ with the redrive claim recorded.
    - A subsequent recovery run detects the claim, skips duplicate re-dispatch
      and idempotency clearing, and directly retries DLQ message deletion.
    - If step 2 fails, the redrive claim is rolled back so it can be retried.
    - Upon verified DLQ deletion, the redrive claim is cleaned up.
    """
    target_url = get_main_queue_url(target_queue_url)
    if not target_url:
        raise ValueError(
            "Main Queue URL could not be determined. Set QUEUE_URL or pass target_queue_url."
        )

    source_dlq_url = get_dlq_url(dlq_url)
    if not source_dlq_url:
        raise ValueError("DLQ URL could not be determined. Set DLQ_URL or pass dlq_url.")

    team = state.clean_team(task_payload.get("team_id") or task_payload.get("team"))
    task_id = task_payload.get("task_id")
    hops = int(task_payload.get("hops", 0) or 0)

    already_dispatched = False
    new_message_id = None

    if task_id:
        is_first_claim = state.claim_dlq_redrive(team, task_id, hops=hops)
        if not is_first_claim:
            already_dispatched = True
            print(
                f"[dlq] task={task_id} hops={hops} was already dispatched in prior redrive; "
                f"skipping duplicate send and completing DLQ cleanup"
            )

    if not already_dispatched:
        # 1. Clear idempotency marker so runner will execute the replayed task
        if reset_idempotency and task_id:
            state.clear_idempotency_marker(team, task_id, hops=hops)
            print(f"[dlq] cleared idempotency marker for team={team} task={task_id} hops={hops}")

        # 2. Send task back to the main processing queue
        try:
            send_resp = sqs().send_message(
                QueueUrl=target_url,
                MessageBody=json.dumps(task_payload),
            )
            new_message_id = send_resp.get("MessageId")
            print(f"[dlq] redrove task={task_id} to {target_url} (new_msg_id={new_message_id})")
        except Exception:
            if task_id:
                state.release_dlq_redrive(team, task_id, hops=hops)
            raise

    # 3. Delete from DLQ with retry
    delete_succeeded = False
    last_delete_err = None
    for attempt in range(3):
        try:
            sqs().delete_message(
                QueueUrl=source_dlq_url,
                ReceiptHandle=receipt_handle,
            )
            delete_succeeded = True
            print(f"[dlq] deleted receipt={receipt_handle[:16]}... from DLQ")
            break
        except Exception as exc:
            last_delete_err = exc
            if attempt < 2:
                time.sleep(0.05 * (2**attempt))

    if not delete_succeeded:
        print(f"[dlq] failed to delete message from DLQ after retries: {last_delete_err}")
        raise last_delete_err

    # 4. Clean up redrive claim marker once DLQ deletion is complete
    if task_id:
        state.release_dlq_redrive(team, task_id, hops=hops)

    return {
        "success": True,
        "task_id": task_id,
        "new_message_id": new_message_id,
        "team_id": team,
        "already_dispatched": already_dispatched,
    }


def redrive_all(dlq_url=None, target_queue_url=None, reset_idempotency=True, max_messages=50):
    """Redrive all messages currently present in the DLQ up to `max_messages`."""
    source_dlq_url = get_dlq_url(dlq_url)
    target_url = get_main_queue_url(target_queue_url)

    redriven = 0
    failed = 0
    details = []

    while redriven + failed < max_messages:
        batch = inspect_dlq(
            dlq_url=source_dlq_url,
            max_messages=min(10, max_messages - (redriven + failed)),
            visibility_timeout=30,
        )
        if not batch:
            break

        for item in batch:
            if item.get("parse_error") or not item.get("task"):
                failed += 1
                details.append(
                    {
                        "message_id": item["message_id"],
                        "success": False,
                        "error": item.get("parse_error") or "Missing task payload",
                    }
                )
                continue

            try:
                res = redrive_message(
                    receipt_handle=item["receipt_handle"],
                    task_payload=item["task"],
                    dlq_url=source_dlq_url,
                    target_queue_url=target_url,
                    reset_idempotency=reset_idempotency,
                )
                redriven += 1
                details.append(res)
            except Exception as exc:
                failed += 1
                details.append(
                    {
                        "message_id": item["message_id"],
                        "success": False,
                        "error": str(exc),
                    }
                )

    return {
        "redriven": redriven,
        "failed": failed,
        "total": redriven + failed,
        "details": details,
    }


def purge_dlq(dlq_url=None):
    """Purge all messages from the DLQ."""
    url = get_dlq_url(dlq_url)
    if not url:
        raise ValueError("DLQ URL could not be determined.")
    try:
        sqs().purge_queue(QueueUrl=url)
        return {"ok": True, "method": "purge"}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        # PurgeQueue is rate-limited to once per 60 seconds per queue.
        # Fallback to manual drain if rate-limited or PurgeQueueInProgress.
        if code in ("PurgeQueueInProgress", "AWS.SimpleQueueService.PurgeQueueInProgress", "ThrottlingException"):
            drained = 0
            while True:
                msgs = sqs().receive_message(
                    QueueUrl=url,
                    MaxNumberOfMessages=10,
                    VisibilityTimeout=10,
                ).get("Messages", [])
                if not msgs:
                    break
                for m in msgs:
                    sqs().delete_message(QueueUrl=url, ReceiptHandle=m["ReceiptHandle"])
                    drained += 1
            return {"ok": True, "method": "drain", "drained": drained}
        raise
    except Exception as exc:
        # Generic drain fallback
        drained = 0
        while True:
            msgs = sqs().receive_message(
                QueueUrl=url,
                MaxNumberOfMessages=10,
                VisibilityTimeout=10,
            ).get("Messages", [])
            if not msgs:
                break
            for m in msgs:
                sqs().delete_message(QueueUrl=url, ReceiptHandle=m["ReceiptHandle"])
                drained += 1
        return {"ok": True, "method": "drain", "drained": drained}
