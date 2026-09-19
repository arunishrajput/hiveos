"""HiveOS Agent Runner — one SQS message is one agent task on one slot.

The agent is **real**: `shared/llm.py` calls a model and reports the token
usage the provider actually counted. Amazon Bedrock is blocked account-wide on
this AWS account (three regions, both first-party and Marketplace models — see
PROGRESS.md), so inference calls out to Groq. Every other component — the
queue, the scheduler, the state, the real-time layer, the hosting — is AWS.

Everything around the model is what the product actually claims:

  - team memory is loaded before the task runs, and saved facts broadcast
  - `tokens_used` is incremented atomically and broadcast to every client
  - the budget ceiling is **enforced** — the agent is not invoked at 100%

Three invariants live here:

1. **The slot is released even when the task fails.** A leaked slot deadlocks
   the workspace, and on a recording that is indistinguishable from the
   product being broken. Hence try/finally, always.
2. **A token count is only reported as real when a provider counted it.** If
   the model call fails we still answer, from `_stub_agent`, and that result
   sets `estimated` — which is sticky on the total (`state.add_tokens`), so a
   degraded call can never be laundered into a billed-looking meter.
3. **A task holds its slot for a visible minimum.** The scheduler is the
   product; a 400 ms call would make BUSY and a queue position illegible.
"""

import json
import time
import traceback
from collections import namedtuple

from shared import agents, broadcast, history, llm, memory, scheduler, state

# The floor on how long a task occupies its slot. This pads the *slot*, not the
# model: the queue mechanic is the thing being demonstrated, and a sub-second
# response would flash BUSY and free again before either was readable. Sized so
# a three-deep queue still drains well inside a 3-minute demo.
MIN_SLOT_SECONDS = 4.0

# Fault injection for the smoke test's no-slot-leak check. The release
# invariant is the one thing that must never silently regress, so it stays
# verifiable against deployed AWS rather than only in a local test.
FAIL_SENTINEL = "__hiveos_fail__"

# The standard rough heuristic for English. Used *only* on the fallback path,
# where no provider counted anything; a real response reports usage directly
# and `estimated` becomes False.
CHARS_PER_TOKEN = 4

AgentResult = namedtuple("AgentResult", "text tokens estimated")


def lambda_handler(event, context):
    for record in event.get("Records", []):
        # A body that will not parse cannot be acted on at all — let it raise
        # and land in the DLQ rather than pretending it succeeded.
        _handle(json.loads(record["body"]))
    return {"ok": True}


def _handle(task):
    slot_id = task["slot_id"]
    user_id = task.get("user_id", "unknown")
    # Carried on the message because the runner has no connection to resolve
    # from — by the time a queued task runs, the requester may have gone.
    team = state.clean_team(task.get("team_id"))
    print(
        f"[runner] start team={team} slot={slot_id} user={user_id} "
        f"task={task.get('task_id')} hops={task.get('hops', 0)} "
        f"conn={task.get('connection_id')}"
    )

    handoff = None
    try:
        # Returning here still runs `finally`, so a refused task releases its
        # slot exactly like a completed one.
        if _refuse_over_budget(team, task):
            return
        result, handoff = _run_agent(team, task)
        _reply(team, task, result)
    except Exception:
        # The task failed, not the infrastructure. Tell the user, then fall
        # through to finally — swallowing it here is what stops SQS from
        # redelivering a task we have already accounted for.
        traceback.print_exc()
        history.record(
            team,
            task.get("user_id"),
            slot_id,
            tokens=0,
            estimated=False,
            status=history.FAILED,
            prompt=task.get("prompt", ""),
            requested_agent=task.get("requested_agent"),
            task_id=task.get("task_id"),
            handoff_from=task.get("handoff_from"),
        )
        _reply_error(task, "agent task failed")
    finally:
        # Still deliberately not wrapped: if the release fails the slot is
        # leaked, and an SQS redelivery is the only thing that can still fix
        # it. Better a duplicate response than a deadlocked workspace.
        #
        # What it is no longer allowed to do is free somebody *else's* desk.
        # This task is the one SQS may redeliver, and a redelivery can arrive
        # after the original release already handed the desk to the next
        # person in the queue. Naming the holder we expect makes the write
        # conditional, so a stale runner returns False and changes nothing
        # rather than ending a stranger's task.
        scheduler.release_and_dispatch(team, slot_id, expected_holder=user_id)

        # After the release, never before. A handoff is a scheduling request,
        # so it has to compete for a desk on the same terms as everyone in the
        # queue — dispatching it while this task still held a slot would let one
        # chain occupy both desks at once, which is the monopoly the product
        # exists to prevent.
        #
        # Reached from the failure path too, and deliberately: if the model
        # genuinely decided to hand the work on and the reply then failed, the
        # answer the user is waiting for is the *second* leg's.
        if handoff:
            scheduler.hand_off(team, task, handoff["target"], handoff["note"])

    print(f"[runner] done slot={slot_id} user={user_id}")


# --- The budget ceiling ----------------------------------------------------


def _refuse_over_budget(team, task):
    """True if the quota is spent and the agent must not be invoked.

    This is the control the product is built around: a real refusal, not a
    gauge (PRD.md, ARCHITECTURE.md decision 4). It is also the spend guard —
    never disable it to make a demo work.

    Checked *here*, not at claim time, on purpose. A task can sit in the queue
    while the tasks ahead of it burn what was left, so the only honest moment
    to decide is immediately before the model would be called.
    """
    used, budget = state.budget_state(team)
    if not budget or used < budget:
        return False

    print(f"[runner] REFUSED — over budget used={used} budget={budget}")
    # A refusal is part of the record, and the most telling part: it is what
    # proves the ceiling is a control rather than a gauge. Zero tokens, and
    # the ledger says so.
    history.record(
        team,
        task.get("user_id"),
        task.get("slot_id"),
        tokens=0,
        estimated=False,
        status=history.REFUSED,
        prompt=task.get("prompt", ""),
        requested_agent=task.get("requested_agent"),
        task_id=task.get("task_id"),
        handoff_from=task.get("handoff_from"),
    )
    broadcast.broadcast_to_team(
        team,
        {
            "event": "budget_exhausted",
            "tokens_used": used,
            "token_budget": budget,
        }
    )
    _reply_error(task, "team token quota reached — the agent was not invoked")
    return True


# --- The agent -------------------------------------------------------------


def _estimate_tokens(*texts):
    """A truthful estimate of what these strings would cost a model.

    **Not** a Bedrock usage figure — there is no model call. It is
    `len(text) / 4` over the real prompt, the real memory context and the real
    response, which is the standard rough heuristic. Every frame that carries
    it sets `estimated: true`.
    """
    total = sum(len(text or "") for text in texts)
    return max(1, total // CHARS_PER_TOKEN)


def _remember_from_prompt(team, prompt, requester):
    """The `remember: k = v` convention, kept as a safety net.

    Saving a fact is now the *model's* decision — it has a `set_team_memory`
    tool and normally calls it. This runs only when it did not: either the
    model declined, or the call failed outright and there was no model in the
    loop at all.

    Worth keeping rather than deleting. The memory beat is the strongest thing
    the product does, a tool call is a probabilistic act where a regex is not,
    and this costs one match on a string already in hand.
    """
    directive = memory.directive(prompt)
    if not directive:
        return None
    fact = memory.remember(team, directive[0], directive[1], requester)
    if fact:
        print(f"[runner] fell back to the remember: convention for {fact['key']!r}")
    return fact


def _run_agent(team, task):
    """Run one task. Returns `(result, handoff)`; `handoff` is usually None.

    The model call is the only part that can fail in a way the user should
    still get an answer from, so it is the only part wrapped. Everything around
    it — the memory write, the broadcast, the accounting — is the real
    mechanism and runs whether or not the provider is reachable.

    A handoff is *recorded here and acted on by the caller*, after this task's
    slot is released. The tool cannot dispatch it itself: doing so from inside a
    task that still holds a desk would put one chain on both desks at once.
    """
    prompt = task.get("prompt", "")

    if FAIL_SENTINEL in prompt:
        raise RuntimeError(f"fault injection via {FAIL_SENTINEL}")

    # Who answers is the desk this ran at, never the preference on the request.
    # They are usually the same; when they are not, the substitution is what
    # `_reply` reports and what the ledger records.
    slot_id = task["slot_id"]
    agent = agents.get(slot_id)
    requester = task.get("user_id", "unknown")
    started = time.monotonic()

    # Where this task may still be handed. Empty once the hop budget is spent,
    # and `llm.tools_for` then leaves the handoff tool out of the request
    # entirely — the loop guard is the absence of the tool, not an instruction
    # the model is trusted to follow.
    targets = (
        agents.others(slot_id)
        if int(task.get("hops", 0) or 0) < scheduler.MAX_HANDOFF_HOPS
        else ()
    )

    # Before the work, not during it: a queued user's agent must already know
    # the team's facts the moment its turn starts (CONTRACT.md). Deliberately
    # not a tool — a model that forgot to ask would break that guarantee.
    context = memory.as_context(team)

    saved = []
    handoff = {}

    def run_tool(name, args):
        """Execute one tool the model chose to call.

        Returns what the model should be *told*, which is not always what
        happened — a refused save has to come back as prose it can relay,
        because raising here would abandon a task that has already run.
        """
        if name == "set_team_memory":
            fact = memory.remember(team, args.get("key"), args.get("value"), requester)
            if not fact:
                return "Not saved — a team fact needs both a key and a value."
            saved.append(fact)
            return (
                f"Saved for the team: {fact['key']} = {fact['val']}. "
                "Every future agent task loads this automatically."
            )
        if name == "get_task_context":
            return history.as_context(team)
        if name == "handoff_to_agent":
            return _accept_handoff(handoff, targets, slot_id, args)
        return f"There is no tool called {name}."

    try:
        text, tokens, called = llm.complete(
            prompt,
            llm.build_system_prompt(context, agent),
            run_tool,
            tools=llm.tools_for(targets),
        )
        result = AgentResult(text=text, tokens=tokens, estimated=False)
        if called:
            print(f"[runner] model used tools: {called}")
    except Exception as exc:
        # Answer anyway. A demo that shows an error because a third-party API
        # blipped is worse than one that answers from composed text and says
        # so — and `estimated=True` keeps the meter honest about it.
        print(f"[runner] model call failed ({type(exc).__name__}: {exc}) — composing fallback")
        fact = _remember_from_prompt(team, prompt, requester)
        result = _stub_agent(prompt, context, agents.name_of(slot_id), fact)
        # A handoff the model asked for before the call fell over is not acted
        # on: `_stub_agent` has already answered the user from this desk, and
        # dispatching a second leg would spend the team's budget answering a
        # question that has a reply on screen.
        handoff = {}
    else:
        # The model answered but chose not to save, and the prompt plainly
        # asked. Save it regardless: the fact is what the user asked for, and
        # the row, the broadcast and the next task's context all follow from it.
        if not saved:
            _remember_from_prompt(team, prompt, requester)

    _hold_slot(started)
    return result, (handoff or None)


def _accept_handoff(handoff, targets, slot_id, args):
    """Record the model's decision to pass this task on. Never dispatches.

    Returns prose, including when it refuses — a tool that raised would abandon
    a task that has already run and already cost the team tokens, and the model
    can relay "there is no such desk" to the user perfectly well.
    """
    if handoff.get("target"):
        return (
            "This task has already been handed on. Tell the user who has it "
            "and stop."
        )

    target = args.get("agent")
    by_id = {agent["id"]: agent for agent in targets}
    if target == slot_id:
        return "You are already at that desk. Answer the task yourself."
    if target not in by_id:
        if not targets:
            return (
                "This task was already handed to you by another desk, so it "
                "cannot be passed on again. Answer it yourself."
            )
        offer = ", ".join(f"{a['id']} ({a['name']}, {a['role']})" for a in targets)
        return f"There is no desk called {target!r}. Available: {offer}."

    handoff["target"] = target
    handoff["note"] = (args.get("note") or "").strip()
    taker = by_id[target]
    return (
        f"Handed to {taker['name']}, the {taker['role']}. They pick it up at "
        "their own desk and answer next, under the same team budget. Tell the "
        "user in one sentence that you have passed it on, and why."
    )


def _hold_slot(started):
    """Keep the slot BUSY long enough to be legible on a recording.

    Padding the slot rather than the model: the queue mechanic is what is being
    demonstrated, and the scheduler's behaviour is identical either way.
    """
    remaining = MIN_SLOT_SECONDS - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)


def _stub_agent(prompt, context, agent_name, fact):
    """Composed answer for when the model is unreachable. Always `estimated`.

    This is the fallback ladder's bottom rung (PRD.md) kept live in code rather
    than as a plan: the workspace degrades to text it composes itself instead
    of surfacing a provider outage as a broken product.

    Still signed by the agent whose desk the task ran at. The name is the only
    part of that agent this path can honour — the persona goes to a model that
    is not answering — but a reply from "Ada · offline" is at least the same
    board the room is showing.
    """
    if fact:
        text = (
            f"[{agent_name} · offline] Saved for the team: "
            f"{fact['key']} — {fact['val']}. Every agent task from now on "
            "loads this before it starts."
        )
    elif context:
        text = (
            f"[{agent_name} · offline] Task accepted: {prompt!r}.\n{context}\n"
            "Those facts were loaded before this task began — nobody had to "
            "repeat them. The model itself is unreachable right now, so this "
            "reply is composed and its token count is an estimate."
        )
    else:
        text = (
            f"[{agent_name} · offline] Task accepted: {prompt!r}. The model is "
            "unreachable right now, so this reply is composed; the scheduler, "
            "queue, quota and shared memory around it are live either way."
        )

    return AgentResult(
        text=text,
        tokens=_estimate_tokens(prompt, context, text),
        estimated=True,
    )


# --- Replies ---------------------------------------------------------------


def _reply(team, task, result):
    """Account for the spend, then tell the room.

    The `ADD` happens before either broadcast so no client is ever told about
    a response whose cost was not recorded. `token_update` goes first because
    it describes already-committed state and the meter is the headline number.
    """
    usage = state.add_tokens(team, result.tokens, estimated=result.estimated)

    # The desk it ran at, which is the agent that answered. Not the preference
    # on the request: those differ whenever the asked-for agent was busy, and
    # the whole point of naming the agents is that the difference is visible.
    slot_id = task["slot_id"]
    requested = task.get("requested_agent")
    substituted = requested if requested and requested != slot_id else None
    handed_from = task.get("handoff_from")

    # After the ADD, never before: the ledger must not be able to report a cost
    # that the team counter has not actually taken.
    history.record(
        team,
        task.get("user_id"),
        slot_id,
        tokens=result.tokens,
        estimated=result.estimated,
        status=history.DONE,
        prompt=task.get("prompt", ""),
        requested_agent=requested,
        # Both legs of a handed-over task carry the same chain id, so the
        # ledger can say the work cost the team N tokens rather than showing
        # two unrelated tasks that happen to sit next to each other.
        task_id=task.get("task_id"),
        handoff_from=handed_from,
    )

    # `usage` already carries `estimated`, read back from the row, so the
    # broadcast reports the provenance of the whole total rather than of this
    # one call.
    broadcast.broadcast_to_team(team, {"event": "token_update", **usage})
    broadcast.broadcast_to_team(
        team,
        {
            "event": "agent_response",
            "user_id": task.get("user_id"),
            "agent_type": slot_id,
            "agent_name": agents.name_of(slot_id),
            # Null on an ordinary task. Set only when somebody asked for one
            # agent and a different one took the work, which is a thing the
            # room should say out loud rather than quietly substitute. The
            # name rides along for the same reason `agent_name` does: the
            # activity log renders a frame on its own, without a roster to
            # join against.
            "requested_agent": substituted,
            "requested_name": agents.name_of(substituted) if substituted else None,
            # Null on an ordinary task; set on the receiving leg of a handoff.
            # The chain id rides along so a client can tie the two answers
            # together without holding the ledger.
            "task_id": task.get("task_id"),
            "handoff_from": handed_from,
            "handoff_from_name": agents.name_of(handed_from) if handed_from else None,
            "text": result.text,
            "tokens_used_this_call": result.tokens,
            "estimated": result.estimated,
        }
    )


def _reply_error(task, message):
    """Directed at the requester — a failed task is their problem, not the room's.

    The connection may already be gone; send_to_connection handles that and
    cleans up the row, so no special case is needed here.
    """
    connection_id = task.get("connection_id")
    if not connection_id:
        print("[runner] no connection_id on the task — cannot report the failure")
        return
    delivered = broadcast.send_to_connection(
        connection_id,
        {"event": "error", "message": message},
    )
    print(f"[runner] error reply to {connection_id} delivered={delivered}")
