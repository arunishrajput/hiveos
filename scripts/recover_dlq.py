#!/usr/bin/env python3
"""CLI utility to inspect, redrive, or purge dead-lettered tasks from the DLQ.

Usage:
  python3 scripts/recover_dlq.py --inspect
  python3 scripts/recover_dlq.py --redrive-all
  python3 scripts/recover_dlq.py --purge
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure backend modules are importable
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import boto3
from shared import dlq, state


def resolve_urls_from_cloudformation(stack_name="hiveos", region="us-east-1"):
    cf = boto3.client("cloudformation", region_name=region)
    try:
        stacks = cf.describe_stacks(StackName=stack_name).get("Stacks", [])
        if not stacks:
            return None, None
        outputs = {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}
        return outputs.get("QueueUrl"), outputs.get("DeadLetterQueueUrl")
    except Exception as exc:
        print(f"[warn] CloudFormation describe-stacks failed: {exc}", file=sys.stderr)
        return None, None


def main():
    parser = argparse.ArgumentParser(description="HiveOS DLQ Inspection and Recovery Utility")
    parser.add_argument("--inspect", action="store_true", help="Inspect messages in DLQ")
    parser.add_argument("--redrive-all", action="store_true", help="Redrive all DLQ messages to main queue")
    parser.add_argument("--purge", action="store_true", help="Purge DLQ messages")
    parser.add_argument("--max-messages", type=int, default=20, help="Maximum messages to inspect/redrive")
    parser.add_argument("--dlq-url", default=None, help="Explicit DLQ URL override")
    parser.add_argument("--queue-url", default=None, help="Explicit main Queue URL override")
    parser.add_argument("--stack-name", default=os.environ.get("STACK_NAME", "hiveos"), help="CloudFormation stack name")
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"), help="AWS Region")

    args = parser.parse_args()

    # Discover URLs if not explicitly configured in environment
    if not os.environ.get("DLQ_URL") and not args.dlq_url:
        q_url, dlq_url = resolve_urls_from_cloudformation(args.stack_name, args.region)
        if q_url and not os.environ.get("QUEUE_URL"):
            os.environ["QUEUE_URL"] = q_url
        if dlq_url:
            os.environ["DLQ_URL"] = dlq_url

    if args.queue_url:
        os.environ["QUEUE_URL"] = args.queue_url
    if args.dlq_url:
        os.environ["DLQ_URL"] = args.dlq_url

    # Validate that required infrastructure endpoints are resolved
    resolved_dlq = dlq.get_dlq_url()
    if not resolved_dlq:
        print(
            "ERROR: DLQ_URL could not be resolved from environment or CloudFormation stack.\n"
            "Prerequisite: SAM / CloudFormation deployment ('sam deploy') must be completed\n"
            "so the 'DeadLetterQueueUrl' stack output exists, or provide --dlq-url explicitly.",
            file=sys.stderr,
        )
        return 1

    if args.redrive_all:
        resolved_queue = dlq.get_main_queue_url()
        if not resolved_queue:
            print(
                "ERROR: QUEUE_URL could not be resolved from environment or CloudFormation stack.\n"
                "Prerequisite: SAM / CloudFormation deployment ('sam deploy') must be completed\n"
                "so the 'QueueUrl' stack output exists, or provide --queue-url explicitly.",
                file=sys.stderr,
            )
            return 1

    if not args.inspect and not args.redrive_all and not args.purge:
        # Default action: inspect
        args.inspect = True

    if args.inspect:
        print("== Inspecting HiveOS Task DLQ ==")
        items = dlq.inspect_dlq(max_messages=args.max_messages)
        if not items:
            print("DLQ is empty. No dead-lettered tasks found.")
            return 0
        print(f"Found {len(items)} dead-lettered message(s):")
        for idx, item in enumerate(items, 1):
            print(f"\n[{idx}] MessageId: {item['message_id']}")
            print(f"    Attributes: {json.dumps(item['attributes'])}")
            if item.get("parse_error"):
                print(f"    Parse Error: {item['parse_error']}")
                print(f"    Raw Body: {item['raw_body']}")
            else:
                task = item.get("task", {})
                print(f"    Task ID: {task.get('task_id')}")
                print(f"    User:    {task.get('user_id')}")
                print(f"    Slot:    {task.get('slot_id')} (requested: {task.get('requested_agent')})")
                print(f"    Prompt:  {task.get('prompt')}")
        return 0

    if args.redrive_all:
        print("== Redriving HiveOS Task DLQ Messages ==")
        summary = dlq.redrive_all(max_messages=args.max_messages)
        print(f"Redrive complete: {summary['redriven']} succeeded, {summary['failed']} failed (total: {summary['total']})")
        for detail in summary["details"]:
            print(f"  - {detail}")
        return 0 if summary["failed"] == 0 else 1

    if args.purge:
        print("== Purging HiveOS Task DLQ ==")
        res = dlq.purge_dlq()
        print(f"DLQ purge result: {res}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
