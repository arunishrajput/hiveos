"""The agent roster — who sits at each desk.

Until now a slot was a number with a name on it: `coder` and `researcher` were
two interchangeable workers whose only difference was the string in the URL.
Every claim fell back to whichever was free and the ledger recorded whichever
had been *asked for*, so the two labels were decoration.

Here each desk holds a named agent with a role and a system prompt of its own,
and the ledger records the one that actually ran the task.

**The roster lives in code, not in DynamoDB.** The `AGENT#` row keeps only what
varies at runtime — `status` and `current_user` — and the snapshot joins the
two. The alternative was tempting and wrong: `ensure_team` writes slot rows
conditionally, so every workspace that already exists would have kept rows
without the new attributes and needed a backfill, and a persona editable per
workspace is a feature nobody asked for. One tuple, one place to edit, no
migration.

The ids are unchanged (`coder`, `researcher`). They are in deployed DynamoDB
rows, in `seed.sh`, in `ws_smoke.py` and in every queued task, and renaming
them would buy nothing that adding a name to them does not.
"""

# Order matters twice: it is the fallback order for a claim (CONTRACT.md), and
# it is the left-to-right order of the desks on the floor.
AGENTS = (
    {
        "id": "coder",
        "name": "Ada",
        "role": "Engineer",
        "tagline": "Code, debugging, design. Answers with the next concrete step.",
        "persona": (
            "You take engineering work: code, debugging, design and "
            "implementation questions. Answer with the concrete next step "
            "someone can act on, and say plainly when something needs to be "
            "checked rather than guessing at it."
        ),
    },
    {
        "id": "researcher",
        "name": "Iris",
        "role": "Researcher",
        "tagline": "Finding, checking, summarising. Says what it is unsure of.",
        "persona": (
            "You take work that needs finding, checking and summarising. Give "
            "the short answer first, then the one detail that matters most, "
            "and name what you are unsure of instead of smoothing over it."
        ),
    },
)

IDS = tuple(agent["id"] for agent in AGENTS)

_BY_ID = {agent["id"]: agent for agent in AGENTS}


def get(agent_id):
    """One agent by id, or None. `None` in means `None` out — a task with no
    preference is a normal thing, not a lookup failure."""
    return _BY_ID.get(agent_id)


def name_of(agent_id):
    """A display name for an id, falling back to the id itself.

    Used on every wire frame and log line that names an agent. Falling back
    rather than raising: an id that is not in the roster can only come from an
    older queued task or a hand-written frame, and neither is worth failing a
    task that has already run.
    """
    agent = get(agent_id)
    return agent["name"] if agent else (agent_id or "agent")


def public(agent_id):
    """What a client is told about an agent: everything except the prompt.

    The persona is deliberately not sent. It is the model's instruction, not
    board state, and shipping it to every browser on every snapshot would make
    a prompt edit a frontend concern.
    """
    agent = get(agent_id)
    if not agent:
        return {"name": agent_id, "role": "", "tagline": ""}
    return {
        "name": agent["name"],
        "role": agent["role"],
        "tagline": agent["tagline"],
    }
