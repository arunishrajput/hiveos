"""The model call. One provider, one function, no SDK.

Amazon Bedrock is blocked account-wide on this AWS account — not by anything
here, and not by a fixable setting. Three regions (`us-east-1`, `us-west-2`,
`ap-south-1`), both first-party and Marketplace models, all refuse:
`INVALID_PAYMENT_INSTRUMENT` for Anthropic/AI21, and a hard zero per-day token
quota (`adjustable=False`) for Amazon's own Nova. See ARCHITECTURE.md,
decision 7. Inference therefore calls out to Groq; **every other component stays on AWS.**

That split is worth stating plainly rather than hiding: a governance layer that
only works with one vendor's models is a worse governance layer. The scheduler
does not care where a token was spent, only that it was counted.

Deliberately built on `urllib` from the standard library:

  - no new dependency, so `sam build` has nothing extra to package
  - no wheel to resolve, which matters because local Python is 3.14 and any
    compiled dependency built off-container would be the wrong platform
  - the whole client is one POST and one JSON parse

The API key lives in SSM Parameter Store as a SecureString, never in
`template.yaml`, `samconfig.toml`, an environment variable, or this repository.
It is fetched once per cold start and cached for the life of the container.
"""

import json
import os
import urllib.error
import urllib.request

import boto3

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Name of the SSM SecureString holding the key. The *name* is not a secret.
KEY_PARAM_NAME = os.environ.get("GROQ_KEY_PARAM", "/hiveos/groq-api-key")

# Groq retires model names periodically — the Llama 3.3 name this was first
# written against was already gone by the time it was deployed. If this starts
# returning 404 `model_not_found`, list the current ids with
# `GET https://api.groq.com/openai/v1/models`; it is a one-variable change.
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# Per-call output cap — the same spend guard the Bedrock plan specified.
#
# **This model's reasoning tokens are charged against it.** `gpt-oss-120b`
# thinks before it answers, and that thinking counts as completion tokens, so a
# cap set to the length of the *answer* can be spent entirely on reasoning and
# return empty content. That surfaces here as "no usable completion" and to the
# user as a stubbed reply — having paid full price for the call. Size this for
# reasoning plus the answer, never for the answer alone.
MAX_TOKENS = int(os.environ.get("MAX_TOKENS_PER_CALL", "900"))

# Shorter than the Lambda's 60s timeout and the queue's visibility window, so a
# hung provider surfaces as a fallback rather than as a redelivered task.
TIMEOUT_SECONDS = 20

# Identifies this client to the provider's edge. See the note in `complete`:
# the stdlib default is blocked by Cloudflare, so this is load-bearing.
USER_AGENT = "HiveOS/1.0 (+https://github.com/arunishrajput/hiveos)"

# Low but not zero: the demo asks the same question across takes and a wildly
# different answer each time reads as instability on camera.
TEMPERATURE = 0.3

# Brevity is a product constraint, not a style preference: every token spent
# here comes out of a quota the whole team shares, and the response renders in
# a narrow panel beside three other people's. Stated in the imperative and
# repeated, because a single polite "be brief" is reliably ignored the moment a
# prompt looks like it wants code.
#
# Split from the rules below so a named agent can replace it. Everything after
# it — the tools, the brevity rules — is identical whoever is at the desk;
# only the identity changes.
SHARED_ROLE = (
    "You are a shared team agent running inside HiveOS, a workspace where an "
    "entire team draws on one pooled AI token budget."
)

SYSTEM_PROMPT = (
    "You have tools. Use set_team_memory whenever someone asks you to "
    "remember, note or record something for the team — it is shared, so every "
    "teammate's later tasks will know it. Use get_task_context for questions "
    "about what the team has been doing or where the budget went.\n"
    "Rules, in order of importance:\n"
    "1. Answer in at most three short sentences. Never exceed this.\n"
    "2. Do not include code blocks, bullet lists, or headings. Prose only.\n"
    "3. If a question invites a long answer, give the shortest useful one and "
    "stop.\n"
    "Every token you spend is drawn from the team's shared quota, so brevity "
    "is the job, not a preference."
)

_key_cache = None


def _api_key():
    """The Groq key from SSM, fetched once per container.

    Cached at module scope: a warm Lambda serves many tasks and re-reading the
    parameter on every one would add a round trip to each task for nothing.
    """
    global _key_cache
    if _key_cache is None:
        _key_cache = boto3.client("ssm").get_parameter(
            Name=KEY_PARAM_NAME,
            WithDecryption=True,
        )["Parameter"]["Value"]
    return _key_cache


def _identity(agent):
    """Who is answering. The roster entry's persona, or the generic agent.

    Falls back rather than raising: a task queued before an agent was removed
    from the roster still has to run, and running it as the generic shared
    agent is a better outcome than failing a task someone is waiting on.
    """
    if not agent:
        return SHARED_ROLE
    # A hired agent may have been given no briefing at all — the form allows
    # it, because "Jim, the Editor" is already a useful instruction. Joined on
    # the non-empty parts so an empty persona leaves a clean sentence rather
    # than a trailing space.
    role = f", the {agent['role']}" if agent.get("role") else ""
    return " ".join(
        part
        for part in (
            f"You are {agent['name']}{role} at one of HiveOS's agent desks — "
            "a workspace where an entire team draws on one pooled AI token "
            "budget.",
            agent.get("persona") or "",
        )
        if part
    )


def build_system_prompt(context, agent=None):
    """The system prompt: who this agent is, then the rules, then what the
    team already knows.

    `agent` is a roster entry from `shared.agents` — the desk this task is
    running at. Identity first and rules second on purpose: the rules are
    absolute and shared, so they are stated after the persona rather than
    before it, where a persona could read as qualifying them.

    `context` is the team's shared memory. Loading it *before* the call is the
    product claim — a queued user's agent knows the team's facts the moment its
    turn starts, without anyone repeating them.

    It no longer takes a saved fact. That argument existed to tell the model
    about a save the *runner* had already performed by regex; the model now
    makes that decision itself and hears the outcome as a tool result, which is
    where it belongs.
    """
    parts = [_identity(agent), SYSTEM_PROMPT]
    if context:
        parts.append(context)
    return "\n\n".join(parts)


# --- Tools -----------------------------------------------------------------

# What the agent may decide to do, as opposed to what is done *for* it.
#
# `get_team_memory` is deliberately absent. The team's facts are loaded into
# the system prompt before the call, because "a queued user's agent already
# knows the team's facts the moment its turn starts" is a product claim
# (CONTRACT.md) — making it a tool would make it conditional on the model
# choosing to ask, and a model that forgot to ask would silently break the
# demo's strongest beat.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "set_team_memory",
            "description": (
                "Save a fact for the whole team. Everyone's future agent tasks "
                "will load it automatically. Use this whenever the user asks "
                "you to remember, note or record something for the team."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Short name for the fact, e.g. 'deploy window'.",
                    },
                    "value": {
                        "type": "string",
                        "description": "The fact itself, e.g. 'Friday 16:00 UTC'.",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_task_context",
            "description": (
                "Look at what the team has recently asked agents to do, and "
                "what each task cost. Use this for questions about what the "
                "team has been working on or where the token budget went."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

# One round of tools, not a loop until the model is satisfied. Each round is a
# full round trip inside a Lambda that holds an agent slot the whole time, and
# an unbounded loop is an unbounded bill. One round is enough for "save this
# and tell me you did".
MAX_TOOL_ROUNDS = 1


def handoff_tool(targets):
    """The tool that passes a task to another desk, or None if there is none.

    Built from the roster entries the caller says are reachable, so the enum
    can only ever name a desk that exists — and so a task that has already been
    handed once is simply not offered the tool. The hop limit is therefore
    structural rather than a rule the model is asked to respect: there is
    nothing to call.

    The descriptions carry each target's role verbatim from the roster. A bare
    list of ids ("coder", "researcher") tells a model nothing about which desk a
    piece of work belongs at, and picking the wrong one is worse than not
    handing over at all — it spends a second leg to arrive at the same place.
    """
    if not targets:
        return None

    roles = "; ".join(
        f"{agent['slot_id']} is {agent['name']}, the {agent['role']}"
        f" — {agent['tagline']}"
        for agent in targets
    )
    return {
        "type": "function",
        "function": {
            "name": "handoff_to_agent",
            "description": (
                "Pass this task to a different agent desk when the work plainly "
                "belongs to them rather than to you. They pick it up at their "
                "own desk, under the same team budget, and answer the user "
                "next. Use it only for a genuine mismatch of expertise — the "
                f"handover costs the team a second agent run. Desks: {roles}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {
                        "type": "string",
                        "enum": [agent["slot_id"] for agent in targets],
                        "description": "Which desk takes it from here.",
                    },
                    "note": {
                        "type": "string",
                        "description": (
                            "One sentence for the agent picking this up: what "
                            "you understood the task to be and why it is theirs."
                        ),
                    },
                },
                "required": ["agent", "note"],
            },
        },
    }


def tools_for(handoff_targets=()):
    """The tool list for one task. The base tools, plus a handoff if allowed."""
    handoff = handoff_tool(handoff_targets)
    return TOOLS + [handoff] if handoff else list(TOOLS)


def _post(payload):
    """One POST to the provider. Returns the decoded body."""
    request = urllib.request.Request(
        GROQ_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            # Not decoration. The endpoint sits behind Cloudflare, which bans
            # urllib's default `Python-urllib/3.13` signature outright and
            # answers HTTP 403 `error code: 1010` — which looks exactly like a
            # bad API key and is not one. Any honest UA gets through.
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        # The body carries the actual reason (bad model name, revoked key,
        # rate limit). Surfacing it is the difference between a five-minute fix
        # and an hour of guessing — and it never contains the key, which rides
        # in the request headers only.
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"groq HTTP {exc.code}: {detail}") from exc


def _usage(payload):
    return int((payload.get("usage") or {}).get("total_tokens") or 0)


def _no_completion(payload):
    """Why an answer came back empty, said in a way a log reader can act on.

    Worth the extra lines because the interesting case is indistinguishable
    from a generic provider failure in a bare usage dump, and it cost this
    project a confused half hour: the model spent its entire output cap on
    reasoning and had nothing left to say. That is a `MAX_TOKENS_PER_CALL`
    problem, not a provider problem, and the two want opposite responses.
    """
    usage = payload.get("usage") or {}
    reasoning = int(
        (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    )
    completion = int(usage.get("completion_tokens") or 0)
    if reasoning and completion >= MAX_TOKENS * 0.9:
        return (
            f"groq spent the whole {MAX_TOKENS}-token output cap on reasoning "
            f"({reasoning} reasoning of {completion} completion tokens) and "
            "returned no answer — raise MAX_TOKENS_PER_CALL"
        )
    return f"groq returned no usable completion: {usage}"


def complete(prompt, system, run_tool=None, tools=None):
    """Call the model, letting it use tools. Returns (text, tokens, called).

    `run_tool(name, args) -> str` executes one tool and returns what the model
    should be told about it. `called` is the list of tool names the model
    actually chose, which the caller needs because a fact saved by the *model*
    and a fact saved by a regex are different claims and only one of them is
    "the agent decided to".

    `tools` is the schema list to offer, defaulting to `TOOLS`. It is a
    parameter rather than a constant because what an agent may do depends on
    the task: a task that has already been handed over once is not offered the
    handoff tool, which is how the hop limit is enforced.

    **Tokens are the sum across every round.** A tool call costs two requests,
    and charging the team for one of them would under-report spend on the one
    product whose entire subject is spend.

    Raises on any failure — transport, HTTP status, or a response missing the
    fields we need. The caller owns the fallback, because only the caller knows
    what a degraded answer should say.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    request = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "messages": messages,
    }
    if run_tool:
        request["tools"] = TOOLS if tools is None else tools
        request["tool_choice"] = "auto"

    tokens = 0
    called = []

    for _ in range(MAX_TOOL_ROUNDS + 1):
        payload = _post({**request, "messages": messages})
        tokens += _usage(payload)
        choice = payload["choices"][0]["message"]
        calls = choice.get("tool_calls") or []

        if not calls or not run_tool:
            text = (choice.get("content") or "").strip()
            if not text or tokens <= 0:
                raise RuntimeError(_no_completion(payload))
            return text, tokens, called

        # The assistant turn that *requested* the tools has to go back verbatim,
        # or the tool results below have nothing to attach to.
        messages.append(choice)
        for call in calls:
            name = call.get("function", {}).get("name", "")
            try:
                args = json.loads(call.get("function", {}).get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"[llm] model called {name}({args})")
            called.append(name)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": run_tool(name, args),
                }
            )

        # Second round answers in prose; offering the tools again would invite
        # it to call them forever.
        request.pop("tools", None)
        request.pop("tool_choice", None)

    raise RuntimeError("groq kept asking for tools past the round limit")
