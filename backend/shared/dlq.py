"""Dead-Letter Queue (DLQ) inspection, recovery, and replay mechanics for HiveOS.

When tasks repeatedly fail in the Agent Runner (e.g. Lambda timeouts, transient
outages, or unhandled exceptions), SQS moves them to the DLQ (`TaskDLQ`).

This module provides operational visibility and safe replay for dead-lettered tasks:
1. `inspect_dlq()`: Peek and inspect messages currently sitting in the DLQ.
2. `redrive_message()`: Safely re-dispatch a dead-lettered task to the main queue
   after clearing its `IDEMPOTENCY#` marker so it is not skipped as a duplicate.
3. `redrive_all()`: Batch recovery for all dead-lettered tasks in the DLQ.
4. `purge_dlq()`: Drain/clear the DLQ after operational review.
"""

import json
import os
import boto3

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


def inspect_dlq(dlq_url=None, max_messages=10, visibility_timeout=10):
    """Inspect up to `max_messages` from the DLQ without deleting them.

    Returns a list of message descriptors containing the raw SQS metadata and
    the parsed task payload.
    """
    url = get_dlq_url(dlq_url)
    if not url:
        raise ValueError("DLQ URL could not be determined. Set DLQ_URL or pass dlq_url.")

    resp = sqs().receive_message(
        QueueUrl=url,
        MaxNumberOfMessages=min(max(1, max_messages), 10),
        AttributeNames=["All"],
        MessageAttributeNames=["All"],
        VisibilityTimeout=visibility_timeout,
    )

    items = []
    for msg in resp.get("Messages", []):
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
    return items


def redrive_message(
    receipt_handle,
    task_payload,
    dlq_url=None,
    target_queue_url=None,
    reset_idempotency=True,
):
    """Replay a dead-lettered task back to the main queue and remove it from DLQ.

    If `reset_idempotency` is True, any existing `IDEMPOTENCY#<task_id>#<hops>`
    marker in DynamoDB is cleared so the runner will execute the replayed task
    rather than dropping it as a duplicate.
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

    # 1. Clear idempotency marker so the runner will execute the replayed task
    if reset_idempotency and task_id:
        state.clear_idempotency_marker(team, task_id, hops=hops)
        print(f"[dlq] cleared idempotency marker for team={team} task={task_id} hops={hops}")

    # 2. Send task back to the main processing queue
    send_resp = sqs().send_message(
        QueueUrl=target_url,
        MessageBody=json.dumps(task_payload),
    )
    new_message_id = send_resp.get("MessageId")
    print(f"[dlq] redrove task={task_id} to {target_url} (new_msg_id={new_message_id})")

    # 3. Delete from DLQ
    sqs().delete_message(
        QueueUrl=source_dlq_url,
        ReceiptHandle=receipt_handle,
    )
    print(f"[dlq] deleted receipt={receipt_handle[:16]}... from DLQ")

    return {
        "success": True,
        "task_id": task_id,
        "new_message_id": new_message_id,
        "team_id": team,
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
    except Exception as exc:
        # PurgeQueue is rate-limited to once per 60 seconds per queue.
        # Fallback to manual drain if rate-limited.
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
