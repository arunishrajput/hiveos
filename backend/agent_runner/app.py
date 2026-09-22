"""HiveOS Agent Runner — one SQS message is one agent task on one slot.

The agent is **real**: `shared/llm.py` calls a model and reports the token
usage the provider actually counted. Amazon Bedrock is blocked account-wide on
this AWS account (three regions, both first-party and Marketplace models — see
PROGRESS.md), so inference calls out to Groq. Every other component — the
queue, the scheduler, the state, the real-time layer, the hosting — is AWS.

Everything around the model is what the product actually claims:

  - team memory is loaded before the task runs, and saved facts broadcast
  - `tokens_used` is incremented atomically and broadcast to every client
  - the budget ceiling is **enforced** — the agent is not invoked at 100%,
    and the check that decides it is the same write that commits the spend, so
    two desks arriving at the ceiling together cannot both be let through

Four invariants live here:

1. **The slot is released even when the task fails.** A leaked slot deadlocks
   the workspace, and on a recording that is indistinguishable from the
   product being broken. Hence try/finally, always.
2. **A token count is only reported as real when a provider counted it.** If
   the model call fails we still answer, from `_stub_agent`, and that result
   sets `estimated` — which is sticky on the total (`state.add_tokens`), so a
   degraded call can never be laundered into a billed-looking meter.
3. **A task holds its slot for a visible minimum.** The scheduler is the
   product; a 400 ms call would make BUSY and a queue position illegible.
4. **A task is charged for once.** SQS is at-least-once, so a redelivery is a
   normal event, and running the model again would bill the team twice for one
   piece of work. `_already_delivered` is the gate — and it sits *inside* the
   try, because invariant 1 outranks it: a redelivery must still be able to
   free a desk the previous run died holding.
"""

import json
import time
import traceback
from collections import namedtuple

from botocore.exceptions import ClientError

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

# What one task provisionally takes off the meter before it is allowed to run.
#
# Not a prediction of the cost — the provider reports that afterwards and
# `state.add_tokens` settles the difference, so this number never decides what
# a team is charged. It decides one thing only: whether a second runner
# arriving in the same instant still finds room under the ceiling. Sized to a
# whole task so that it does, and derived rather than invented —
# `llm.MAX_TOKENS` is the most one call may emit and `llm.MAX_TOOL_ROUNDS`
# bounds how many calls a task makes, so their product is the completion side
# of the worst case. The prompt is added on top by `_refuse_over_budget`.
#
# It is an approximation of the worst case, not a proof of it: the system
# prompt, the team memory and a tool result are input tokens this does not
# count. It runs about twice a measured task (~800 tokens, CONTRACT.md), which
# is the margin that matters — a reservation at least the size of a real task
# is what keeps total spend inside `budget + one task`.
RESERVATION_CEILING = (llm.MAX_TOOL_ROUNDS + 1) * llm.MAX_TOKENS

# How long an `IDEMPOTENCY#` marker is kept. It only has to outlive the window
# in which SQS could still redeliver the task it guards: the queue retains a
# message for an hour (`template.yaml`), so a day is generous by a wide margin
# and DynamoDB's TTL sweep is best-effort anyway. Without it these rows would
# accumulate forever in a partition that `state_snapshot` reads whole.
MARKER_TTL_SECONDS = 86_400

AgentResult = namedtuple("AgentResult", "text tokens estimated")


def lambda_handler(event, context):
    for record in event.get("Records", []):
        # A body that will not parse cannot be acted on at all — let it raise
        # and land in the DLQ rather than pretending it succeeded.
        _handle(json.loads(record["body"]))
    return {"ok": True}


def _named(names, slot_id):
    """A display name for one desk, falling back to its id, then to None.

    `None` in means `None` out — `handoff_from` is null on an ordinary task and
    must stay null in the ledger, not become the string "None".
    """
    if not slot_id:
        return None
    return names.get(slot_id) or slot_id


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

    # The roster, read once for the whole task.
    #
    # It is per workspace now, so who Ada is depends on which board this is.
    # Everything downstream — the persona the model runs under, the handoff
    # targets, the name on the reply and the names written into the ledger —
    # comes from this one read rather than from four lookups against a module
    # that no longer knows the answer.
    desks = [agents.from_row(row) for row in state.roster(team)]
    names = {desk["slot_id"]: desk["name"] for desk in desks}

    handoff = None
    # What this task has provisionally taken off the meter. Held here, not on
    # the task, because `task` is an SQS message body that gets read back by
    # the ledger and the handoff — a local cannot leak into either.
    reserved = 0
    try:
        # Returning here still runs `finally`, so a duplicate or a refused task
        # releases its slot exactly like a completed one.
        if _already_delivered(team, task):
            return
        refused, reserved = _refuse_over_budget(team, task, names)
        if refused:
            return
        result, handoff = _run_agent(team, task, desks)
        _reply(team, task, result, names, reserved)
        # Settled by `_reply`, so there is nothing left for `finally` to give
        # back. Cleared *after* it returns: if the accounting write itself
        # fails, the reservation is still outstanding and must be released.
        reserved = 0
    except Exception:
        # The task failed, not the infrastructure. Tell the user, then fall
        # through to finally — swallowing it here is what stops SQS from
        # redelivering a task we have already accounted for.
        traceback.print_exc()
        try:
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
                agent_name=_named(names, slot_id),
                handoff_from_name=_named(names, task.get("handoff_from")),
            )
        except Exception:
            traceback.print_exc()
        _reply_error(task, "agent task failed")
    finally:
        # Before the slot release and fully swallowed, in that order and for
        # that reason: the release below is the invariant that outranks
        # everything here, so nothing ahead of it may raise. A reservation is
        # still outstanding on every path that did not reach `_reply` — a
        # refusal reserved nothing, a duplicate never asked, and a failure
        # already told the user it cost zero — so this is where the counter is
        # put back.
        _release_reservation(team, reserved)

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


# --- Exactly once ----------------------------------------------------------


def _already_delivered(team, task):
    """True if this task has run before and must not be charged for twice.

    SQS is at-least-once, so the same task can arrive more than once: either
    the delivery genuinely duplicated, or the previous run died holding its
    desk and the message came back after the visibility timeout. Running it
    again would call the model a second time and bill the team for it — and on
    a product whose headline number is the meter, a double charge is not a
    cosmetic bug.

    The gate is a conditional write, like every other exactly-once decision
    here: whoever wins the `IDEMPOTENCY#` put owns the task. A task with no
    `task_id` has nothing to key on and is let through — the alternative is
    dropping real work to guard against a duplicate that cannot be detected.

    **Keyed on the leg, not the chain.** `task_id` identifies the piece of
    work; `hops` identifies which delivery of it this is (`scheduler.dispatch`
    says so in as many words). Both legs of a handoff deliberately carry the
    same `task_id`, so keying on that alone made Iris's leg collide with Ada's
    marker: the receiving desk went BUSY, skipped its model call, and went
    IDLE again without ever answering. A redelivery repeats `hops`; a handoff
    increments it. That is exactly the distinction this gate needs.

    **Called from inside the try, so a duplicate still reaches the `finally`
    and still releases the desk.** That placement is the whole point. The
    previous run may have died *holding* its slot, and this redelivery is the
    only thing left that can free it (see the `finally` in `_handle`) — a gate
    that returned before the release would convert the one available recovery
    path into a permanent deadlock.
    """
    task_id = task.get("task_id")
    if not task_id:
        return False

    hops = int(task.get("hops", 0) or 0)
    try:
        state.table().put_item(
            Item={
                "PK": state.team_pk(team),
                "SK": f"IDEMPOTENCY#{task_id}#{hops}",
                "slot_id": task.get("slot_id"),
                "user_id": task.get("user_id"),
                "claimed_at": state.now_iso(),
                # Swept by DynamoDB rather than kept forever. Nothing reads
                # this row back — its existence *is* the value — so it has no
                # reason to outlive the redelivery window it guards.
                "expires_at": state.ttl_after(MARKER_TTL_SECONDS),
            },
            ConditionExpression="attribute_not_exists(SK)",
        )
    except ClientError as exc:
        # Only a lost race means "already delivered". Throttling must not be
        # laundered into a silent skip — that would drop the task outright.
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        print(
            f"[runner] duplicate delivery of task {task_id!r} hop {hops} "
            "— not running it again"
        )
        return True

    return False


# --- The budget ceiling ----------------------------------------------------


def _refuse_over_budget(team, task, names):
    """`(refused, reserved)` — whether the agent must not be invoked, and what
    running it has taken off the meter up front.

    This is the control the product is built around: a real refusal, not a
    gauge (PRD.md, ARCHITECTURE.md decision 4). It is also the spend guard —
    never disable it to make a demo work.

    Checked *here*, not at claim time, on purpose. A task can sit in the queue
    while the tasks ahead of it burn what was left, so the only honest moment
    to decide is immediately before the model would be called.

    The decision is `state.reserve_budget`, which both asks and commits in one
    conditional write. Asking and committing used to be separate — a read here
    and an `add_tokens` at the end of the task — and two runners arriving
    together could therefore both read the same remaining budget and both
    spend it. The threshold has not moved: a task runs if there was budget left
    when it asked. What moved is that the answer is now settled against
    committed state, so a second runner is tested against the first one's
    reservation instead of against the same stale read.

    The reservation is a placeholder that `_reply` settles and the runner's
    `finally` releases. It is never what the team is charged.
    """
    prompt = task.get("prompt", "")
    amount = RESERVATION_CEILING + _estimate_tokens(prompt)

    admitted, reserved, used, budget = state.reserve_budget(team, amount)
    if admitted:
        return False, reserved

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
        prompt=prompt,
        requested_agent=task.get("requested_agent"),
        task_id=task.get("task_id"),
        handoff_from=task.get("handoff_from"),
        agent_name=_named(names, task.get("slot_id")),
        handoff_from_name=_named(names, task.get("handoff_from")),
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
    return True, 0


def _release_reservation(team, reserved):
    """Give back a reservation the task never settled. Never raises.

    Swallowed on purpose, and the only thing in this file that is. It runs in
    `_handle`'s `finally` ahead of the slot release, and the slot release is
    the invariant that outranks every other consideration here: a leaked desk
    deadlocks the workspace, where a reservation that failed to come back is a
    meter reading high until `seed.sh` next rewrites the row. Of the two, only
    one of them is visible as the product being broken.
    """
    if not reserved:
        return
    try:
        state.refund_tokens(team, reserved)
    except Exception:
        traceback.print_exc()
        print(f"[runner] WARNING — {reserved} reserved tokens were not released")


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


def _run_agent(team, task, desks):
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
    requester = task.get("user_id", "unknown")
    started = time.monotonic()

    # `desks` is the workspace's roster, already resolved by `_handle`. Passed
    # in rather than read again: the persona, the handoff targets, the reply
    # and the ledger all have to agree about who is on this floor, and two
    # reads a second apart can disagree if somebody hires in between.
    agent = next((d for d in desks if d["slot_id"] == slot_id), None) or {
        "slot_id": slot_id,
        "name": slot_id,
        "role": "",
        "persona": "",
    }

    # Where this task may still be handed. Empty once the hop budget is spent,
    # and `llm.tools_for` then leaves the handoff tool out of the request
    # entirely — the loop guard is the absence of the tool, not an instruction
    # the model is trusted to follow.
    #
    # Derived from the live roster rather than a fixed "everyone except me"
    # list, so an agent hired five minutes ago is a legitimate target and one
    # that was fired is not offered as a desk that no longer exists.
    targets = (
        tuple(d for d in desks if d["slot_id"] != slot_id)
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
        result = _stub_agent(prompt, context, agent["name"], fact)
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
    by_id = {agent["slot_id"]: agent for agent in targets}
    if target == slot_id:
        return "You are already at that desk. Answer the task yourself."
    if target not in by_id:
        if not targets:
            return (
                "This task was already handed to you by another desk, so it "
                "cannot be passed on again. Answer it yourself."
            )
        offer = ", ".join(f"{a['slot_id']} ({a['name']}, {a['role']})" for a in targets)
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


def _reply(team, task, result, names, reserved):
    """Account for the spend, then tell the room.

    The `ADD` happens before either broadcast so no client is ever told about
    a response whose cost was not recorded. `token_update` goes first because
    it describes already-committed state and the meter is the headline number.

    `reserved` is what `_refuse_over_budget` already put on the counter to win
    this task its turn, so the write here is the difference between that
    placeholder and what the provider actually counted — usually a credit back.
    The broadcast still carries the settled total, read out of the same write,
    so the meter a user sees is the real number and never the placeholder.
    """
    usage = state.add_tokens(
        team,
        result.tokens,
        estimated=result.estimated,
        reserved=reserved,
    )

    # The desk it ran at, which is the agent that answered. Not the preference
    # on the request: those differ whenever the asked-for agent was busy, and
    # the whole point of naming the agents is that the difference is visible.
    slot_id = task["slot_id"]
    requested = task.get("requested_agent")
    substituted = requested if requested and requested != slot_id else None
    handed_from = task.get("handoff_from")

    # After the ADD, never before: the ledger must not be able to report a cost
    # that the team counter has not actually taken.
    try:
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
            # Written now, at the moment the work ran, rather than joined on when
            # the ledger is read. An agent can be fired, and a ledger that looked
            # its names up later would attribute this row to whoever holds that id
            # next — or to nobody.
            agent_name=_named(names, slot_id),
            handoff_from_name=_named(names, handed_from),
        )
    except Exception:
        # The ledger write failed permanently after its retries, so this task
        # is not in the ledger and the counter must not claim it is. Roll the
        # settlement above back so `tokens_used` never diverges from the TASK#
        # rows that `history.spend` and `state.fair_order` are read from.
        #
        # **Undo the settlement, do not zero the task.** What the `add_tokens`
        # above applied is `result.tokens - reserved`, so that is what comes
        # off here — which puts the counter back to still *holding this task's
        # reservation*, exactly where `_reply` found it. That is the state
        # `_handle` expects on this path: `reserved` is only cleared after
        # `_reply` returns, so its `finally` releases the hold. Subtracting
        # `result.tokens` alone would leave the hold released here and
        # released again there, and two releases of one placeholder drive the
        # meter below where the task found it.
        #
        # Tradeoff note: provider-side token usage cannot be reversed. This is
        # an internal consistency decision — the meter agreeing with the
        # ledger — not a claim that billing was reversed. CONTRACT.md says so
        # in as many words.
        state.add_tokens(team, reserved - result.tokens)
        raise

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
            "agent_name": _named(names, slot_id),
            # Null on an ordinary task. Set only when somebody asked for one
            # agent and a different one took the work, which is a thing the
            # room should say out loud rather than quietly substitute. The
            # name rides along for the same reason `agent_name` does: the
            # activity log renders a frame on its own, without a roster to
            # join against.
            "requested_agent": substituted,
            "requested_name": _named(names, substituted),
            # Null on an ordinary task; set on the receiving leg of a handoff.
            # The chain id rides along so a client can tie the two answers
            # together without holding the ledger.
            "task_id": task.get("task_id"),
            "handoff_from": handed_from,
            "handoff_from_name": _named(names, handed_from),
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
