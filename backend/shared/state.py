"""DynamoDB access for the HiveOS single table.

Schema authority is CONTRACT.md. Everything for a team lives under one
partition key and is separated by SK prefix, so the whole world state is one
Query away — which is exactly what `state_snapshot` needs.
"""

import hashlib
import hmac
import json
import secrets
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from . import agents

# The team a client lands in when it does not name one. Teams are no longer
# hardcoded — every row is partitioned by team and every function takes one —
# but a bare connection still has to go somewhere, and that somewhere is the
# team the demo uses.
DEFAULT_TEAM = os.environ.get("TEAM_ID", "alpha")

# Team names arrive from a query string, so they are untrusted input that ends
# up inside a partition key. Anything outside this set could collide two teams
# into one partition, or forge a `TEAM#` prefix of its own.
TEAM_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,30}$")

# What a team starts with the first time anyone joins it. Teams bootstrap
# themselves — requiring a seeding script before a name works would make
# isolation a deployment step rather than a property of the product.
DEFAULT_TEAM_BUDGET = int(os.environ.get("TOKEN_BUDGET", "1000000"))

# `SLOT_IDS` is gone. The roster is no longer a constant this module can hold —
# it is per workspace and lives in the `AGENT#` rows, because a floor you staff
# has a different set of desks in every room. Read it with `roster(team)`.


def clean_team(name):
    """Normalise an untrusted team name, falling back to the default.

    Lowercased so `Alpha` and `alpha` are the same room rather than two rooms
    that look identical in the UI — a team whose members silently cannot see
    each other is worse than one that rejects the name outright.
    """
    candidate = (name or "").strip().lower()
    return candidate if TEAM_PATTERN.match(candidate) else DEFAULT_TEAM


def team_pk(team):
    return f"TEAM#{clean_team(team)}"

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ttl_after(seconds):
    """A DynamoDB TTL value — Unix epoch seconds, `seconds` from now.

    Epoch integers rather than the ISO strings everything else in this schema
    uses, because TTL is the one field DynamoDB itself reads and that is the
    only format it accepts.

    Only `IDEMPOTENCY#` rows carry this. Every other row in the table is state
    somebody can still read, so nothing else should ever expire.
    """
    return int(datetime.now(timezone.utc).timestamp()) + int(seconds)


def clear_idempotency_marker(team, task_id, hops=0):
    """Delete the idempotency gate for a task/hop so it can be safely replayed.

    Used by DLQ recovery to permit a dead-lettered message to be redriven without
    being falsely dropped as a duplicate by `_already_delivered`.
    """
    if not task_id:
        return
    table().delete_item(
        Key={
            "PK": team_pk(team),
            "SK": f"IDEMPOTENCY#{task_id}#{int(hops or 0)}",
        }
    )


def claim_dlq_redrive(team, task_id, hops=0, message_id=None):
    """Atomically claim redrive execution for a dead-lettered task.

    Returns True if this is the first redrive claim (safe to dispatch).
    Returns False if already claimed by a prior redrive attempt that failed
    at the DLQ deletion step (meaning the message was already sent to the main
    queue and must NOT be sent again).
    """
    if not task_id:
        return True
    try:
        table().put_item(
            Item={
                "PK": team_pk(team),
                "SK": f"DLQ_REDRIVE#{task_id}#{int(hops or 0)}",
                "task_id": task_id,
                "hops": int(hops or 0),
                "message_id": message_id,
                "claimed_at": now_iso(),
                "expires_at": ttl_after(3600),  # 1 hour safety TTL
            },
            ConditionExpression="attribute_not_exists(SK)",
        )
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise


def release_dlq_redrive(team, task_id, hops=0):
    """Release or clear the DLQ redrive marker."""
    if not task_id:
        return
    table().delete_item(
        Key={
            "PK": team_pk(team),
            "SK": f"DLQ_REDRIVE#{task_id}#{int(hops or 0)}",
        }
    )


def is_dlq_redriven(team, task_id, hops=0):
    """Check if a DLQ redrive claim exists."""
    if not task_id:
        return False
    item = table().get_item(
        Key={
            "PK": team_pk(team),
            "SK": f"DLQ_REDRIVE#{task_id}#{int(hops or 0)}",
        }
    ).get("Item")
    return item is not None


def now_iso_micros():
    """Microsecond-precision timestamp, used only for QUEUE# sort keys.

    QUEUE# items are ordered by SK, so the timestamp is what makes the queue
    FIFO. At second granularity two people clicking in the same second tie and
    fall back to UUID order — i.e. random. Microseconds keep the order the one
    thing the queue must never get wrong: actual arrival.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# --- JSON ------------------------------------------------------------------
# DynamoDB hands back Decimal for every number and json.dumps refuses it.
# Every frame that leaves this backend goes through dumps().


def _plain(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def dumps(payload):
    return json.dumps(_plain(payload))


# --- Queries ---------------------------------------------------------------


def query_team(team, sk_prefix=None):
    """Every item for the team, optionally narrowed to one SK prefix."""
    condition = Key("PK").eq(team_pk(team))
    if sk_prefix:
        condition = condition & Key("SK").begins_with(sk_prefix)

    items = []
    kwargs = {"KeyConditionExpression": condition}
    while True:
        response = table().query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


# --- Connections -----------------------------------------------------------


def connection_ids(team):
    return [item["SK"].split("#", 1)[1] for item in query_team(team, "CONN#")]


def spawn_point(connection_id):
    """A scattered starting position, derived from the connection ID.

    Everyone used to spawn at (0, 0), which stacked every avatar in one corner
    of the canvas — on a three-browser demo that reads as "the workspace is
    broken", not "nobody has moved yet". Derived from the ID rather than
    randomised so a client and the server agree without another round trip, and
    so a reconnect does not teleport someone across the room.

    Kept to the middle 60% of each axis: the corners are where the avatar
    collides with the canvas caption and the edge labels.
    """
    digest = hashlib.sha1(connection_id.encode()).digest()
    return {
        "x": Decimal(20 + digest[0] * 60 // 255),
        "y": Decimal(20 + digest[1] * 60 // 255),
    }


def add_connection(team, connection_id, user_id, avatar, is_admin=False):
    member = {
        "user_id": user_id,
        "avatar": avatar,
        **spawn_point(connection_id),
    }
    table().put_item(
        Item={
            "PK": team_pk(team),
            "SK": f"CONN#{connection_id}",
            "connected_at": now_iso(),
            # Settled at the handshake, like the team itself. Every later
            # admin action reads it from here rather than re-checking a token.
            "is_admin": is_admin,
            **member,
        }
    )
    # Written together: a member row without its index is a connection nothing
    # can route a later frame to.
    bind_connection(connection_id, team)
    return member


def move_connection(team, connection_id, x, y):
    """Move one avatar. Returns the mover's `user_id`, or None if the row is gone.

    Conditional on the row existing so a frame that races `$disconnect` cannot
    resurrect a dead connection as a half-populated row — `state_snapshot`
    reads every CONN# row as a live member, so that ghost would show up in the
    member count on every screen.
    """
    try:
        response = table().update_item(
            Key={"PK": team_pk(team), "SK": f"CONN#{connection_id}"},
            UpdateExpression="SET x = :x, y = :y",
            ConditionExpression="attribute_exists(SK)",
            # `Decimal(str(x))`, never `Decimal(x)`. Building a Decimal from a
            # float carries the full binary expansion — Decimal(24.92) is
            # 24.9200000000000017053..., and boto3's DYNAMODB_CONTEXT raises
            # decimal.Inexact rather than silently rounding it.
            ExpressionAttributeValues={":x": Decimal(str(x)), ":y": Decimal(str(y))},
            ReturnValues="ALL_NEW",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return None
        raise
    return (response.get("Attributes") or {}).get("user_id")


def remove_connection(team, connection_id):
    """Delete a CONN# row and return what was there, or None if it was gone."""
    response = table().delete_item(
        Key={"PK": team_pk(team), "SK": f"CONN#{connection_id}"},
        ReturnValues="ALL_OLD",
    )
    unbind_connection(connection_id)
    return response.get("Attributes")


def connection_user(team, connection_id):
    response = table().get_item(
        Key={"PK": team_pk(team), "SK": f"CONN#{connection_id}"},
        ProjectionExpression="user_id",
    )
    return (response.get("Item") or {}).get("user_id")



# --- Workspace passphrases -------------------------------------------------

# PBKDF2-HMAC-SHA256. Not the strongest KDF available, but it is in the
# standard library — Lambda has no argon2 or bcrypt without a layer, and a
# layer for one function is more moving parts than this is worth.
#
# 100k iterations costs roughly 50ms per connect. That is paid once per
# WebSocket handshake, never per frame, so it does not touch the latency the
# demo is measured on.
KDF_ITERATIONS = 100_000


def _derive(passphrase, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", (passphrase or "").encode(), bytes.fromhex(salt), KDF_ITERATIONS
    ).hex()


def _team_secret(team):
    """The stored salt and hash for a team, or (None, None) if it is open."""
    response = table().get_item(
        Key={"PK": team_pk(team), "SK": "METADATA"},
        ProjectionExpression="pass_salt, pass_hash",
    )
    item = response.get("Item") or {}
    return item.get("pass_salt"), item.get("pass_hash")


def passphrase_ok(team, passphrase):
    """May this passphrase join this workspace?

    An open workspace admits anyone — that is what keeps the public URL
    something a stranger can open cold onto a live board, which is the whole
    reason this is per-workspace rather than a login wall in front of the app.

    A protected one is compared in constant time. `compare_digest` rather than
    `==` because a plain comparison returns early on the first differing byte,
    which leaks the length of the matching prefix to anyone willing to time it.
    """
    salt, stored = _team_secret(team)
    if not stored:
        return True
    if not passphrase:
        return False
    return hmac.compare_digest(_derive(passphrase, salt), stored)



# --- Workspace administration ----------------------------------------------

# There are no accounts, so there is no "who". Administration is therefore
# keyed on a *secret the creator holds*, not on a name anyone could type at the
# gate — an owner identified by display name would be enforceable only in the
# UI, which is to say not enforceable.
#
# Sharing that secret is what an invite is here. Deliberate: it is the honest
# mechanism available without identity, and pretending otherwise would be
# worse than saying so.


def _team_admin_hash(team):
    response = table().get_item(
        Key={"PK": team_pk(team), "SK": "METADATA"},
        ProjectionExpression="admin_salt, admin_hash",
    )
    item = response.get("Item") or {}
    return item.get("admin_salt"), item.get("admin_hash")


def admin_token_ok(team, token):
    """Does this token hold administrative rights over this workspace?

    False for a workspace that has no admin hash at all. A workspace created
    before this existed — or seeded by `seed.sh` — simply has no administrator,
    which is safer than treating "no owner recorded" as "everyone is owner".
    """
    salt, stored = _team_admin_hash(team)
    if not stored or not token:
        return False
    return hmac.compare_digest(_derive(token, salt), stored)


def set_budget(team, budget):
    """Set a workspace's ceiling. Returns the new (used, budget)."""
    item = table().update_item(
        Key={"PK": team_pk(team), "SK": "METADATA"},
        UpdateExpression="SET token_budget = :b",
        ExpressionAttributeValues={":b": int(budget)},
        ReturnValues="ALL_NEW",
    )["Attributes"]
    return int(item.get("tokens_used", 0)), int(item.get("token_budget", 0))


def rotate_passphrase(team, passphrase):
    """Replace a workspace's passphrase, or remove it if given nothing.

    Removing is a real operation, not an oversight: a workspace that was
    protected for a demo should be able to become open again without being
    deleted and recreated.
    """
    if passphrase:
        salt = secrets.token_hex(16)
        table().update_item(
            Key={"PK": team_pk(team), "SK": "METADATA"},
            UpdateExpression="SET pass_salt = :s, pass_hash = :h",
            ExpressionAttributeValues={":s": salt, ":h": _derive(passphrase, salt)},
        )
    else:
        table().update_item(
            Key={"PK": team_pk(team), "SK": "METADATA"},
            UpdateExpression="REMOVE pass_salt, pass_hash",
        )


def delete_team(team):
    """Remove every row a workspace owns. Returns how many were deleted.

    Includes the CONN#/TEAM index rows for its live members, which live outside
    the partition — missing those would leave connections pointing at a
    workspace that no longer exists.
    """
    pk = team_pk(team)
    rows = query_team(team)
    with table().batch_writer() as batch:
        for item in rows:
            batch.delete_item(Key={"PK": pk, "SK": item["SK"]})
            if item["SK"].startswith("CONN#"):
                batch.delete_item(
                    Key={"PK": f"CONN#{item['SK'].split('#', 1)[1]}", "SK": "TEAM"}
                )
    return len(rows)


def connection_is_admin(team, connection_id):
    """Was this connection admitted as an administrator?

    Decided once, at the handshake, and stored on the CONN# row — the same
    shape as every other thing the server trusts about a connection. An admin
    action that re-presented the token per frame would be a token travelling
    over the wire repeatedly for no gain.
    """
    response = table().get_item(
        Key={"PK": team_pk(team), "SK": f"CONN#{connection_id}"},
        ProjectionExpression="is_admin",
    )
    return bool((response.get("Item") or {}).get("is_admin"))


# --- Connection ownership --------------------------------------------------


def ensure_team(team, passphrase=None, admin_token=None):
    """Create a team's METADATA and slot rows if this is its first member.

    Teams bootstrap themselves. Requiring `seed.sh` before a name worked would
    make isolation a deployment step rather than a property of the product —
    and the whole point is that two people typing different team names get
    different workspaces without anyone provisioning anything.

    Every write is conditional on the row being absent, so several people
    joining a brand-new team in the same second cannot each reset it to empty.
    """
    pk = team_pk(team)

    # A passphrase is set by whoever creates the workspace and never changed
    # here. The conditional write below is what makes that safe: if two people
    # reach a brand-new name in the same second with different passphrases,
    # exactly one creation wins and the other is then checked against it like
    # any other joiner.
    secret = {}
    if passphrase:
        salt = secrets.token_hex(16)
        secret = {"pass_salt": salt, "pass_hash": _derive(passphrase, salt)}
    if admin_token:
        admin_salt = secrets.token_hex(16)
        secret["admin_salt"] = admin_salt
        secret["admin_hash"] = _derive(admin_token, admin_salt)

    created = False
    try:
        table().put_item(
            Item={
                "PK": pk,
                "SK": "METADATA",
                "name": clean_team(team),
                "token_budget": DEFAULT_TEAM_BUDGET,
                "tokens_used": 0,
                "created_at": now_iso(),
                **secret,
            },
            ConditionExpression="attribute_not_exists(PK)",
        )
        created = True
        print(f"[state] bootstrapped new team {clean_team(team)!r}")
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

    # The starting roster belongs to *creating* a workspace, not to joining
    # one — and this runs on every `$connect`.
    #
    # Writing it unconditionally silently undid `dismiss_agent`. The seed rows
    # below are conditional on the item being absent, which is exactly what a
    # dismissal makes them, so the next person to connect put Iris back: no
    # `agent_spawned` frame, no trace in the log, a desk simply returning to a
    # floor somebody had just cleared it from. A reconnect after a network blip
    # was enough to do it.
    #
    # The second clause is a repair rather than a re-seed. A floor with no
    # desks at all can never dispatch anything — every claim fails and the
    # queue never drains — which is why `fire_agent` refuses to remove the last
    # one. It is only reachable if a bootstrap died between the two writes
    # above, and leaving such a workspace permanently dead would be the worse
    # trade. One query, on the handshake path only, and only for a floor that
    # is already broken.
    if not created and roster(team):
        return

    # The seeded desks, written with their identity on the row.
    #
    # Still conditional, so a workspace that already exists is never rewritten
    # — which is why `agents.from_row` falls back by slot id. Every board
    # created before this phase keeps a bare `AGENT#coder` row and still reads
    # as Ada, without a backfill.
    #
    # `created_at` is spaced by index rather than taken from one clock read:
    # desks are ordered by it, and two rows written in the same millisecond
    # would order by the id tiebreak instead, putting Iris before Ada.
    for index, seed in enumerate(agents.STARTING_ROSTER):
        try:
            table().put_item(
                Item={
                    "PK": pk,
                    "SK": f"AGENT#{seed['id']}",
                    "slot_id": seed["id"],
                    "status": "IDLE",
                    "current_user": None,
                    "name": seed["name"],
                    "role": seed["role"],
                    "tagline": seed["tagline"],
                    "persona": seed["persona"],
                    "character": seed["character"],
                    "project": seed["project"],
                    "created_at": f"{now_iso()}#{index:03d}",
                },
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise


def bind_connection(connection_id, team):
    """Record which team a connection belongs to.

    This row lives *outside* every team partition, keyed `CONN#<id>` / `TEAM`,
    and it exists because of an awkward asymmetry in API Gateway: the team
    arrives in the query string, which is only readable on `$connect`. Every
    frame after that carries a connection ID and nothing else — so without an
    index, finding a connection's team would mean scanning every team.

    The alternative was to have the client send its team on each frame. That is
    rejected for the same reason `CONTRACT.md` resolves the *sender* from the
    stored row rather than the frame: a value the client supplies is a value
    the client can forge, and here forging it would mean reading another
    team's board.
    """
    table().put_item(
        Item={
            "PK": f"CONN#{connection_id}",
            "SK": "TEAM",
            "team": clean_team(team),
            "connected_at": now_iso(),
        }
    )


def connection_team(connection_id):
    """Which team this connection is in. `DEFAULT_TEAM` if the row is gone.

    Falling back rather than raising: a missing index row means the connection
    is already being torn down, and answering into the default team is
    harmless, where an exception in the router is a dropped frame.
    """
    response = table().get_item(
        Key={"PK": f"CONN#{connection_id}", "SK": "TEAM"},
        ProjectionExpression="team",
    )
    return (response.get("Item") or {}).get("team") or DEFAULT_TEAM


def unbind_connection(connection_id):
    table().delete_item(Key={"PK": f"CONN#{connection_id}", "SK": "TEAM"})


# --- Queue -----------------------------------------------------------------


def _served_from(task_rows):
    """When each person's most recent task finished, from rows already in hand.

    The SK leads with a microsecond timestamp, so the largest SK for a user
    *is* their most recent task. People with no tasks are simply absent, and
    `fair_order` reads absent as "has waited forever" — which is what it means.
    """
    served = {}
    for item in task_rows:
        user = item.get("user_id")
        if not user:
            continue
        if item["SK"] > served.get(user, ""):
            served[user] = item["SK"]
    return served


def last_served(team):
    """`_served_from` over a fresh read of the `TASK#` ledger.

    Read off the ledger rather than tracked separately: it already records who
    ran what and when, and a second counter maintained alongside it is one more
    thing that can disagree with it.

    Accurate at dispatch time because the runner records a task before its
    `finally` releases the slot — the job that just finished is already in the
    ledger when the next one is chosen.
    """
    return _served_from(query_team(team, "TASK#"))


def fair_order(team, items, served=None):
    """The queue order: fair queueing, not first-come-first-served.

    Sorted by how long each person has gone without a turn, and only then by
    arrival. Someone who has never run outranks someone who just did, so one
    person queueing three tasks cannot drain the whole queue while another
    waits — they interleave.

    **This is the single definition of queue order.** Display and dispatch both
    go through it. If the board said "position 1" by arrival while the runner
    picked by fairness, the number on screen would simply be wrong about who
    goes next — and this repository has been bitten twice by two orderings that
    had to agree and eventually did not.

    FIFO remains the tie-break, so among people who have waited equally long
    the earlier request still wins. With one task each — the common case, and
    the demo case — this is indistinguishable from FIFO.
    """
    served = last_served(team) if served is None else served
    return sorted(items, key=lambda item: (served.get(item.get("user_id"), ""), item["SK"]))


def queue_items(team, served=None):
    """Waiting tasks in the order they will actually be dispatched."""
    return fair_order(team, query_team(team, "QUEUE#"), served)


def idle_slots(team):
    """Which desks are free right now, as a set of slot ids.

    Read on the dispatch path because a *pinned* queue row — a handoff, which
    may only run at the desk it was handed to — is dispatchable exactly when
    that one desk is idle. Without this the scheduler would have to delete the
    row to find out, then put it back, and a task would churn through the queue
    every time any other desk released.
    """
    return {
        item.get("slot_id")
        for item in query_team(team, "AGENT#")
        if item.get("status") == "IDLE"
    }


def roster(team):
    """Every desk in one workspace, in the order they sit on the floor.

    This replaces the `SLOT_IDS` constant that used to answer "which agents
    exist". It is a per-workspace question now, so it is a read rather than a
    module attribute, and every caller that used to iterate the constant
    iterates this instead.

    Ordered by `created_at`, so the desks, the claim fallback order and the
    floor plan all agree — and a newly hired agent appears at the end rather
    than shuffling the room. A row written before this phase has no
    `created_at` at all and sorts first, which is correct: those are the two
    the workspace opened with.
    """
    return sorted(
        query_team(team, "AGENT#"),
        key=lambda item: (item.get("created_at") or "", item.get("slot_id") or ""),
    )


def agent_row(team, slot_id):
    """One desk's row, or None. For the runner, which needs the persona."""
    response = table().get_item(
        Key={"PK": team_pk(team), "SK": f"AGENT#{slot_id}"}
    )
    return response.get("Item")


def hire_agent(team, fields):
    """Put a new desk on the floor. Returns its row, or None if the floor is full.

    Hiring is free and deliberately open to any member, not just the owner.
    Spawning an agent costs nothing — *running* one is what spends the budget,
    and the ceiling already governs that no matter how many desks share it. A
    governance product that made you an administrator to add a colleague would
    be governing the wrong thing.

    The cap is checked with a read and is therefore racy: two simultaneous
    hires can both see five desks and both write, leaving seven. That is the
    right trade here — the alternative is a counter on the METADATA row updated
    conditionally, which buys strict enforcement of a *cosmetic* limit at the
    cost of a second write on every hire. The floor draws what it has room for
    and the ceiling is unaffected either way.
    """
    existing = roster(team)
    if len(existing) >= agents.MAX_AGENTS:
        print(f"[state] hire refused — {clean_team(team)} already has "
              f"{len(existing)} desks")
        return None

    name = agents.clean(fields.get("name"), agents.MAX_NAME, "Agent")
    slot_id = agents.new_slot_id(name)
    item = {
        "PK": team_pk(team),
        "SK": f"AGENT#{slot_id}",
        "slot_id": slot_id,
        "status": "IDLE",
        "current_user": None,
        "name": name,
        "role": agents.clean(fields.get("role"), agents.MAX_ROLE, "Generalist"),
        "tagline": agents.clean(fields.get("tagline"), agents.MAX_TAGLINE),
        "persona": agents.clean(fields.get("persona"), agents.MAX_PERSONA),
        "character": (
            fields.get("character")
            if fields.get("character") in agents.CHARACTERS
            else agents.CHARACTERS[len(existing) % len(agents.CHARACTERS)]
        ),
        "project": agents.clean(fields.get("project"), agents.MAX_PROJECT),
        # Microseconds, for the same reason `QUEUE#` sort keys use them: this
        # value orders the floor, and `now_iso()` is second-granularity. Two
        # people hiring in the same second tied and fell through to the
        # `slot_id` tiebreak in `_desk_rank` — which is derived from the name,
        # so the desks would come back in alphabetical order rather than in the
        # order they were hired. That is the room reshuffling itself, which is
        # exactly what ordering by `created_at` exists to prevent.
        "created_at": now_iso_micros(),
    }

    # Conditional on the id being free. The suffix in `new_slot_id` makes a
    # collision vanishingly unlikely; this is what makes it impossible.
    table().put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
    print(f"[state] hired {name!r} as slot={slot_id} in {clean_team(team)}")
    return item


def fire_agent(team, slot_id):
    """Take a desk off the floor. Returns the reason it could not, or None.

    Two rules, both of which exist because the scheduler reads this roster:

    * **Only while idle.** Deleting a row mid-task leaves the runner holding a
      desk that no longer exists; its release would then write a row back with
      `set_idle`'s update, resurrecting a fired agent as a ghost with no name.
    * **Never the last one.** A floor with no desks accepts tasks it can never
      dispatch — every claim fails, everything queues, and nothing ever frees a
      slot to drain it.
    """
    row = agent_row(team, slot_id)
    if not row:
        return "no such desk"
    if row.get("status") == "BUSY":
        return "that desk is working — halt it first"
    if len(roster(team)) <= 1:
        return "a floor needs at least one agent"

    table().delete_item(Key={"PK": team_pk(team), "SK": f"AGENT#{slot_id}"})
    print(f"[state] fired slot={slot_id} from {clean_team(team)}")
    return None


# `slot_holder` was here and is now `agent_row` above.
#
# It was added in PR #1 so the release route would not read the table directly,
# and it projected `current_user` alone because that was the only thing the
# route needed. The route now needs one more thing — whether the desk exists at
# all, which used to be answerable for free against a module constant and is a
# read since the roster became per-workspace data. `agent_row` answers both
# from the same GetItem, so keeping a second function that answers half of it
# would be one more thing to keep in step. The rule it was written to protect
# is intact: `router/app.py` still contains no raw table access.


def queue_view(team, items=None):
    """The queue as clients see it: 1-based positions, next up first."""
    items = queue_items(team) if items is None else items
    return [
        {
            "user_id": item.get("user_id"),
            "agent_type": item.get("agent_type"),
            "queue_position": position,
        }
        for position, item in enumerate(items, start=1)
    ]


# --- Token accounting ------------------------------------------------------


def pct_used(used, budget):
    """One definition of the percentage, shared by the snapshot and every
    `token_update`. Two copies would eventually disagree by a rounding step
    and the meter would flicker between them."""
    if not budget:
        return 0
    return round(float(used) / float(budget) * 100, 1)


def budget_state(team):
    """`(tokens_used, token_budget)` straight from METADATA.

    METADATA is the single source of truth for the ceiling — deliberately not
    the `TOKEN_BUDGET` env var. It is the same row the counter increments and
    the same number `state_snapshot` hands a client, so the guard can never
    disagree with the meter a user is looking at. `TOKEN_BUDGET` only supplies
    the default `seed.sh` writes.
    """
    item = table().get_item(Key={"PK": team_pk(team), "SK": "METADATA"}).get("Item") or {}
    return int(item.get("tokens_used", 0)), int(item.get("token_budget", 0))


def add_tokens(team, count, estimated=False):
    """Atomically add to `tokens_used`; returns a ready `token_update` payload.

    `ADD` rather than read-then-write because two agent runs finishing
    together would otherwise lose one of the two increments — and an
    undercounted meter is exactly the failure the product claims to prevent.

    `ALL_NEW` so the budget comes back in the same round trip that moved the
    counter. Reading it separately would let the broadcast describe a state
    that no longer matches the row it came from.

    `estimated` sets a sticky `usage_estimated` flag on the row. It is sticky
    and never cleared here on purpose: once any estimated spend is folded into
    the total, the *total* is partly estimated for as long as it stands, and a
    client loading cold has no other way to learn that. Only `seed.sh` clears
    it, by rewriting METADATA from scratch.
    """
    expression = "ADD tokens_used :n"
    values = {":n": count}
    if estimated:
        expression += " SET usage_estimated = :e"
        values[":e"] = True

    item = table().update_item(
        Key={"PK": team_pk(team), "SK": "METADATA"},
        UpdateExpression=expression,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )["Attributes"]

    used = int(item.get("tokens_used", 0))
    budget = int(item.get("token_budget", 0))
    return {
        "tokens_used": used,
        "token_budget": budget,
        "pct_used": pct_used(used, budget),
        "estimated": bool(item.get("usage_estimated", False)),
    }


# --- Snapshot --------------------------------------------------------------


def _desk_rank(desk):
    """Where a desk sits on the floor: when it was hired, then its id.

    This used to be a position in the `agents.py` tuple, which stopped meaning
    anything the moment the roster became per-workspace data. Ordering by
    `created_at` keeps the two desks a board opened with at the front and puts
    every hire after them, so hiring never reshuffles the room somebody is
    watching. The two seeded rows carry an index suffix on their timestamp for
    exactly that reason — see `ensure_team`.

    A row written before this phase has no `created_at` and sorts first, which
    is where those desks belong.
    """
    return (desk.get("created_at") or "", desk.get("slot_id") or "")


def state_snapshot(team, is_admin=False):
    """One frame a cold client can render the entire workspace from.

    Load-bearing per CONTRACT.md: a browser joining mid-demo must not have to
    wait for the next incremental event to show correct state.
    """
    # Imported here, not at module scope: `history` needs `state` for its
    # writes, so a top-level import either way is a cycle. Only the two pure
    # shaping functions are used below, and this is their one caller.
    from . import history

    # `desks`, not `agents` — the module of that name is the roster, and the
    # two would shadow each other in the loop below.
    metadata, desks, members, memory, waiting, tasks = {}, [], [], [], [], []

    for item in query_team(team):
        sk = item["SK"]
        if sk == "METADATA":
            metadata = item
        elif sk.startswith("QUEUE#"):
            waiting.append(item)
        elif sk.startswith("AGENT#"):
            # The row now carries its own identity as well as its runtime
            # state. `public` reads it back with the starting-roster fallback
            # and drops the persona, so the board renders every desk from this
            # frame alone (CONTRACT.md) and no browser is ever handed the text
            # that steers an agent.
            desks.append(
                {
                    "agent_type": item.get("slot_id"),
                    "status": item.get("status"),
                    "current_user": item.get("current_user"),
                    "created_at": item.get("created_at"),
                    **agents.public(item),
                }
            )
        elif sk.startswith("CONN#"):
            members.append(
                {
                    "user_id": item.get("user_id"),
                    "avatar": item.get("avatar"),
                    "x": item.get("x", 0),
                    "y": item.get("y", 0),
                }
            )
        elif sk.startswith("TASK#"):
            tasks.append(item)
        elif sk.startswith("MEMORY#"):
            memory.append(
                {
                    "key": item.get("key"),
                    "val": item.get("val"),
                    "updated_by": item.get("updated_by"),
                }
            )

    budget = metadata.get("token_budget", 0)
    used = metadata.get("tokens_used", 0)

    return {
        "event": "state_snapshot",
        "team": clean_team(team),
        # Roster order, not alphabetical: it is the order the desks sit in on
        # the floor and the order a claim falls back through, and a client that
        # renders them in a different order is showing a different room.
        "agents": sorted(desks, key=_desk_rank),
        "tokens_used": used,
        "token_budget": budget,
        "pct_used": pct_used(used, budget),
        # Whether any of that total is an estimate rather than billed model
        # usage. Carried on the snapshot so a client loading cold — the most
        # likely way anyone sees this board — is told too, not just clients
        # that happened to be watching when the spend happened.
        "usage_estimated": bool(metadata.get("usage_estimated", False)),
        # Whether a passphrase is *needed*, never the salt or the hash. The
        # METADATA row is read wholesale above, so this is the one place that
        # could leak them and it names the fields it sends instead.
        "protected": bool(metadata.get("pass_hash")),
        # Whether this workspace has an owner at all. Never the hash.
        "owned": bool(metadata.get("admin_hash")),
        # Whether the connection asking holds those rights. Decided at the
        # handshake and passed in — the snapshot does not re-verify a token.
        "is_admin": bool(is_admin),
        "members": members,
        "memory": memory,
        # Without this a client that joins or reconnects while queued cannot
        # render its own position until someone else's action happens to move
        # the queue. The snapshot has to stand alone (CONTRACT.md).
        # Ordered by the same function the runner dispatches with, and from
        # the task rows already in hand rather than a second query. Sorting by
        # SK here — as this did — would have the snapshot disagree with the
        # live queue about who is next the moment fairness reorders anything.
        "queue": queue_view(team, fair_order(team, waiting, _served_from(tasks))),
        # The ledger. On the snapshot rather than only on a live event for the
        # same reason as everything else here: the client most likely to want
        # "who spent what" is the one that just opened the URL.
        "history": history.view(tasks),
        "spend": history.spend(tasks),
    }
