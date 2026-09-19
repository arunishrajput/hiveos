"""The agent roster — who sits at each desk, and who may be hired.

Until Phase 17 this module *was* the roster: one tuple, fixed at deploy time,
identical in every workspace, two desks forever. A floor you staff cannot work
that way, so the roster moved into DynamoDB — one `AGENT#` row per agent,
carrying its identity alongside the `status` and `current_user` that row
already held.

What stays here is the part that genuinely belongs in code:

  * ``STARTING_ROSTER`` — who a brand-new workspace opens with.
  * ``CHARACTERS`` — the faces the hire form offers.
  * the limits every hired field is truncated to.

**`from_row` falls back to `STARTING_ROSTER` by slot id, and that fallback is
load-bearing rather than defensive.** `ensure_team` writes slot rows
*conditionally*, so it never updates a row that already exists — which means
every workspace created before this phase still holds an `AGENT#coder` row with
no name on it. Reading identity through this function gives all of them Ada and
Iris exactly as before, with no migration, no backfill, and no one-off script
run against a live table. The alternative was a scan-and-update over every
partition, to add data that can be derived.

The two original ids stay `coder` and `researcher`. They are in deployed rows,
in `seed.sh`, in `ws_smoke.py` and in every queued task, and renaming them
would buy nothing that hiring a third agent does not already give.
"""

import re
import secrets

# How many desks one workspace may hold.
#
# A floor limit, not a cost limit — the ceiling is what governs spend, and it
# is per workspace no matter how many agents share it. This is the room: six
# desks is what the plan in `components.jsx` has places for, and a seventh
# agent would be hired into a floor with nowhere to sit.
MAX_AGENTS = 6

# What a hired agent may carry. Truncated server-side, like `user_id` already
# is — a client that sends more gets a shorter agent, not an error.
MAX_NAME = 24
MAX_ROLE = 24
MAX_TAGLINE = 120
MAX_PERSONA = 600
MAX_PROJECT = 40

# The faces the hire form offers.
#
# Deliberately the same eight markers the entry gate uses for people, and in
# the same order: `sprites.js` derives a look from this string, so an agent and
# a person picking the same marker genuinely look alike. Keeping one list means
# the art, the gate and the hire form cannot drift into three different rosters
# of faces.
#
# **This tuple must stay in step with `AVATARS` in `frontend/src/sprites.js`.**
# A value not in that list still works — `lookFor` hashes anything it does not
# recognise — so the failure mode is a face you did not pick, not a crash.
CHARACTERS = ("🐝", "🦊", "🐙", "🦉", "🐺", "🦋", "🐢", "🦜")

# Who a new workspace opens with.
#
# Two, not zero. An empty floor is a worse first impression than a staffed one
# and would make the very first thing a visitor has to do a form — and two is
# what every existing workspace already has, so the fallback below and a fresh
# board describe the same office.
STARTING_ROSTER = (
    {
        "id": "coder",
        "name": "Ada",
        "role": "Engineer",
        "character": "🦊",
        "project": "platform",
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
        "character": "🦉",
        "project": "platform",
        "tagline": "Finding, checking, summarising. Says what it is unsure of.",
        "persona": (
            "You take work that needs finding, checking and summarising. Give "
            "the short answer first, then the one detail that matters most, "
            "and name what you are unsure of instead of smoothing over it."
        ),
    },
)

_SEED_BY_ID = {agent["id"]: agent for agent in STARTING_ROSTER}

# What a slot id may contain. Slugged from the agent's name and suffixed, so it
# is readable in a log line and in a queued task rather than being a bare uuid.
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def new_slot_id(name):
    """A fresh slot id for a hired agent: `jim-a3f2`.

    Suffixed rather than deduplicated by lookup. Two people hiring a "Jim" at
    the same moment is a real race on a shared board, and four random hex
    characters settle it without a read, a lock or a retry. The slug is only
    there so `[scheduler] claimed slot=jim-a3f2` is readable — the suffix is
    what makes it unique.

    A name with nothing sluggable in it (emoji, or a script this regex does not
    cover) still yields a valid id, because the suffix alone is one.
    """
    slug = _SLUG_STRIP.sub("-", (name or "").lower()).strip("-")[:16]
    suffix = secrets.token_hex(2)
    return f"{slug}-{suffix}" if slug else f"agent-{suffix}"


def clean(value, limit, fallback=""):
    """One hired field: a string, trimmed, truncated, never None."""
    text = (value or "").strip()
    return text[:limit] if text else fallback


def seed_for(slot_id):
    """The starting-roster entry for an id, or None. Used by the fallback."""
    return _SEED_BY_ID.get(slot_id)


def from_row(item):
    """The identity of one agent, from its `AGENT#` row.

    Falls back field by field rather than wholesale, so a row written before
    this phase — which has a `slot_id` and nothing else — still reports Ada's
    name, role, tagline and persona, while a row that carries its own name uses
    every value it was hired with.

    An unknown id with no stored name is not an error: it can only come from a
    row whose roster entry was removed, and answering with the id is better
    than raising inside a task that has already run.
    """
    slot_id = item.get("slot_id")
    seed = _SEED_BY_ID.get(slot_id) or {}
    return {
        "slot_id": slot_id,
        "name": item.get("name") or seed.get("name") or slot_id or "agent",
        "role": item.get("role") or seed.get("role") or "",
        "tagline": item.get("tagline") or seed.get("tagline") or "",
        "persona": item.get("persona") or seed.get("persona") or "",
        "character": item.get("character") or seed.get("character") or "",
        "project": item.get("project") or seed.get("project") or "",
    }


def public(item):
    """What a client is told about an agent: everything except the prompt.

    `persona` is deliberately withheld. It is the model's instruction, not
    board state, and shipping it to every browser on every snapshot would make
    editing a briefing a frontend concern — and would hand anyone on a public
    URL the exact text steering the agents.
    """
    identity = from_row(item)
    identity.pop("persona", None)
    return identity


def name_of(item):
    """A display name for a row. `None` in means a neutral label out."""
    return from_row(item)["name"] if item else "agent"
