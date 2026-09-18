/* Presentational pieces of the operator console.
 *
 * All of them are pure functions of board state, so what a browser shows is
 * exactly what the last snapshot said — which is the property the demo turns
 * on: three windows, one board, no divergence.
 */

import { useEffect, useRef, useState } from 'react'

import { lookFor } from './sprites'

const NUM = new Intl.NumberFormat('en-US')

/** BUILD_PLAN.md: green <50%, amber 50-80%, red >80%. */
export function toneFor(pct) {
  if (pct < 50) return 'safe'
  if (pct <= 80) return 'warn'
  return 'alarm'
}

export function formatEta(seconds) {
  if (seconds == null) return '—'
  if (seconds < 90) return `~${Math.round(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return rest ? `~${minutes}m ${rest}s` : `~${minutes}m`
}

function formatClock(date) {
  return date.toLocaleTimeString('en-GB', { hour12: false })
}

/* The hive cell.
 *
 * Amber and blue swapped roles when the theme did. The hexagon used to be
 * stroked amber because amber was the brightest thing available on graphite;
 * on cream a #f0a714 hairline is barely there, and the outline is the part
 * that has to survive at 18px. So the cell is drawn in ink and amber moves to
 * the fill — which is also the rule the rest of the system follows.
 */
export function Mark({ className }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <path
        d="M16 5.5l8 4.6v9.2l-8 4.6-8-4.6V10.1z"
        fill="#ffca54"
        stroke="#1a1320"
        strokeWidth="2.6"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="14.7" r="2.8" fill="#1a1320" />
    </svg>
  )
}

const LAMP_TEXT = {
  idle: 'offline',
  connecting: 'connecting',
  open: 'live',
  reconnecting: 'reconnecting',
  refused: 'locked',
  closed: 'offline',
}

export function Lamp({ connection }) {
  return (
    <span className={`lamp lamp--${connection}`}>
      <span className="lamp__dot" />
      {LAMP_TEXT[connection] ?? connection}
    </span>
  )
}

export function StatusRail({ team, members, connection }) {
  const avatars = members
    .map((m) => m.avatar)
    .filter(Boolean)
    .slice(0, 5)
    .join('')

  return (
    <header className="rail">
      <Mark className="rail__mark" />
      <span className="rail__name">HiveOS</span>
      <span className="rail__team">{team}</span>
      <span className="rail__spacer" />
      <span className="rail__members">
        {avatars} {members.length} online
      </span>
      <Lamp connection={connection} />
    </header>
  )
}

export function QuotaPanel({ tokensUsed, tokenBudget, pctUsed, exhausted, estimated }) {
  const pct = Math.max(0, Math.min(100, pctUsed ?? 0))
  const tone = toneFor(pct)
  const remaining = Math.max(0, (tokenBudget ?? 0) - (tokensUsed ?? 0))

  return (
    <section className="panel" aria-labelledby="quota-label">
      <div className="panel__head">
        <span className="panel__label" id="quota-label">
          Team token quota
        </span>
      </div>

      <div className="quota__figures">
        <span className="quota__used">{NUM.format(tokensUsed ?? 0)}</span>
        <span className="quota__budget">/ {NUM.format(tokenBudget ?? 0)}</span>
        <span className={`quota__pct tone--${tone}`}>{pct.toFixed(1)}%</span>
      </div>

      <div
        className="strip"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Team token quota used"
      >
        <div
          className={`strip__fill tone--${tone}`}
          style={{ clipPath: `inset(0 ${100 - pct}% 0 0)` }}
        />
      </div>

      {exhausted ? (
        <p className="quota__note quota__note--alarm">
          Quota reached. HiveOS stops invoking the agent until the budget is raised.
        </p>
      ) : (
        <p className="quota__note">
          {NUM.format(remaining)} tokens left, shared by the whole team
          {/* Normally absent: counts are the usage the provider reported. This
              appears only when some spend on this board was charged from the
              fallback heuristic because the model was unreachable — said next
              to the number rather than trusting a narrator to remember. */}
          {estimated ? ' · partly estimated — the model was unreachable' : ''}
        </p>
      )}
    </section>
  )
}

/* The quota, as chrome rather than a panel.
 *
 * Same numbers, same semantic tones, same tick geometry as QuotaPanel — this
 * is a re-layout, not a second implementation, and it deliberately keeps the
 * strip because a segment snapping on is what survives video compression.
 * Costs ~70px where the panel cost 148, which is most of what putting the room
 * first had to pay for.
 */
export function QuotaBar({ tokensUsed, tokenBudget, pctUsed, exhausted, estimated }) {
  const pct = Math.max(0, Math.min(100, pctUsed ?? 0))
  const tone = toneFor(pct)
  const remaining = Math.max(0, (tokenBudget ?? 0) - (tokensUsed ?? 0))

  return (
    <section className="quotabar" aria-label="Team token quota">
      <div className="quotabar__row">
        <span className="quotabar__label">Team quota</span>
        <span className="quotabar__used">{NUM.format(tokensUsed ?? 0)}</span>
        <span className="quotabar__budget">/ {NUM.format(tokenBudget ?? 0)}</span>
        <span className={`quotabar__pct tone--${tone}`}>{pct.toFixed(1)}%</span>
      </div>

      <div
        className="strip"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Team token quota used"
      >
        <div
          className={`strip__fill tone--${tone}`}
          style={{ clipPath: `inset(0 ${100 - pct}% 0 0)` }}
        />
      </div>

      <p className={`quotabar__note ${exhausted ? 'quotabar__note--alarm' : ''}`}>
        {exhausted
          ? 'Quota reached — HiveOS stops invoking the agent.'
          : `${NUM.format(remaining)} tokens left, shared by the whole team`}
        {!exhausted && estimated ? ' · partly estimated' : ''}
      </p>
    </section>
  )
}

/* Who is in the room and what they are doing, along the bottom.
 *
 * The same three states the floor shows, in a form that survives someone
 * standing behind a desk or two people overlapping — the room is the nicer
 * read, this is the reliable one.
 */
export function MemberBar({ members, me, busyUsers, queue }) {
  const queuedBy = new Map(queue.map((entry) => [entry.user_id, entry.queue_position]))

  return (
    <section className="memberbar" aria-label="Who is here">
      {members.map((member) => {
        const busy = busyUsers.has(member.user_id)
        const position = queuedBy.get(member.user_id)
        const state = busy ? 'busy' : position ? 'queued' : 'idle'
        const look = lookFor(member.avatar, member.user_id)
        return (
          <div key={member.user_id} className={`member member--${state}`}>
            <span
              className="member__face"
              style={{ '--art': look.art, '--sp-hair': look.hair }}
              aria-hidden="true"
            />
            <span className="member__name">
              {member.user_id === me ? `${member.user_id} (you)` : member.user_id}
            </span>
            <span className="member__state">
              {busy ? 'working' : position ? `queued #${position}` : 'idle'}
            </span>
          </div>
        )
      })}
    </section>
  )
}


/* Where the budget actually went.
 *
 * The meter says the team has spent 2,214 tokens; this says who spent them.
 * That difference is the product — a gauge tells you the tank is low, a ledger
 * tells you who is driving. Derived server-side from TASK# rows and carried on
 * `state_snapshot`, so a browser opening the URL cold sees the whole history
 * rather than an empty panel that fills in only if something happens next.
 */
export function SpendPanel({ spend, members, tokenBudget }) {
  if (!spend.length) return null

  // Share of the *budget*, not of the largest spender: the question this panel
  // answers is "how much of what we have has this person used", and scaling to
  // the top spender would make one person's small spend look like all of it.
  const budget = tokenBudget || 0
  const avatarOf = new Map(members.map((m) => [m.user_id, m.avatar]))
  const totalTasks = spend.reduce((sum, row) => sum + row.tasks, 0)

  return (
    <section className="panel panel--spend" aria-labelledby="spend-label">
      <div className="panel__head">
        <span className="panel__label" id="spend-label">
          Where it went
        </span>
        <span className="panel__aside">
          {totalTasks} {totalTasks === 1 ? 'task' : 'tasks'}
        </span>
      </div>

      <div className="spend">
        {spend.map((row) => {
          const look = lookFor(avatarOf.get(row.user_id), row.user_id)
          const share = budget ? Math.min(100, (row.tokens / budget) * 100) : 0
          return (
            <div className="spend__row" key={row.user_id}>
              <span className="spend__who">{row.user_id}</span>
              <span className="spend__figures">
                <span className="spend__tokens">{NUM.format(row.tokens)}</span>
                <span className="spend__tasks">
                  {row.tasks} {row.tasks === 1 ? 'task' : 'tasks'}
                </span>
              </span>
              {/* Their own colour from the floor, so the ledger and the room
                  are visibly about the same people. */}
              <span className="spend__track">
                <span
                  className="spend__fill"
                  style={{ '--share': share / 100, background: look.hair }}
                />
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

/* Which agent to ask for.
 *
 * A preference, not a reservation, and the copy has to say so: picking a busy
 * agent does not queue you behind them — the first free desk takes the work
 * (CONTRACT.md). Advertising it as a booking would be the one promise this
 * scheduler deliberately does not make.
 *
 * Rendered from `state_snapshot.agents[]`, so the roster, the desks on the
 * floor and this list are the same list.
 */
export function AgentPicker({ agents, value, onChange, disabled }) {
  if (!agents.length) return null

  const option = (key, label, sub, selected, on, busy) => (
    <button
      type="button"
      key={key}
      role="radio"
      aria-checked={selected}
      disabled={disabled}
      onClick={on}
      className={`pick ${selected ? 'pick--on' : ''} ${busy ? 'pick--busy' : ''}`}
    >
      <span className="pick__name">{label}</span>
      <span className="pick__role">{sub}</span>
    </button>
  )

  return (
    <div className="picker" role="radiogroup" aria-label="Which agent takes this task">
      {agents.map((agent) => {
        const busy = agent.status === 'BUSY'
        return option(
          agent.slot_id,
          agent.name || agent.slot_id,
          busy ? 'busy' : agent.role || agent.slot_id,
          value === agent.slot_id,
          () => onChange(agent.slot_id),
          busy,
        )
      })}
      {option('any', 'Either', 'first free', value === null, () => onChange(null), false)}
    </div>
  )
}

export function SlotsPanel({ agents, me }) {
  const running = agents.filter((a) => a.status === 'BUSY').length

  return (
    <section className="panel" aria-labelledby="slots-label">
      <div className="panel__head">
        <span className="panel__label" id="slots-label">
          Agent slots
        </span>
        <span className="panel__aside">
          {running} of {agents.length || 2} running
        </span>
      </div>

      <div className="slots">
        {agents.map((agent) => {
          const busy = agent.status === 'BUSY'
          const mine = busy && agent.current_user === me
          return (
            <article
              key={agent.slot_id}
              className={`slot ${busy ? 'slot--busy' : 'slot--idle'}`}
            >
              <span className="slot__id">{agent.name || agent.slot_id}</span>
              <span className="slot__status">
                <span className="slot__dot" />
                {busy ? 'busy' : 'idle'}
              </span>
              {busy ? (
                <p className={`slot__holder ${mine ? 'slot__mine' : ''}`}>
                  {mine ? 'held by you' : `held by ${agent.current_user}`}
                </p>
              ) : (
                <p className="slot__holder slot__holder--empty">Available</p>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}

export function QueuePanel({ queue, me }) {
  return (
    <section className="panel" aria-labelledby="queue-label">
      <div className="panel__head">
        <span className="panel__label" id="queue-label">
          Run queue
        </span>
        <span className="panel__aside">
          {queue.length} waiting
        </span>
      </div>

      {queue.length === 0 ? (
        <p className="empty">No tasks waiting.</p>
      ) : (
        <div className="queue">
          {queue.map((entry) => {
            const mine = entry.user_id === me
            return (
              <div
                key={`${entry.user_id}-${entry.queue_position}`}
                className={`queue__row ${mine ? 'queue__row--mine' : ''}`}
              >
                <span className="queue__pos">{entry.queue_position}</span>
                <span className="queue__user">{entry.user_id}</span>
                {mine && <span className="queue__tag">you</span>}
                <span className="queue__eta">
                  {formatEta(entry.estimated_wait_seconds)}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

/** How far one arrow-key press moves you, in canvas percent. */
const STEP = 4

/* The back wall occupies the top of the floor, so the walkable ground starts
 * below it. Coordinates stay exactly what CONTRACT.md says they are — 0-100
 * over the whole board, unchanged server-side — and only the *rendering* maps
 * that range onto the floor strip. Without this, one spawn in five puts
 * somebody inside the wall.
 *
 * The click handler applies the inverse, so clicking a spot still puts you on
 * that spot. Both directions use this one constant; they cannot drift apart.
 *
 * Lowered from 22 to 14 with the room plan: the wall band got thinner because
 * the project rooms now stand against it and were eating the band's height
 * twice. Safe to change precisely because both directions read this constant —
 * the only visible effect is that a stored coordinate renders slightly higher.
 */
const WALK_TOP = 14

/* How long a walk takes, whatever the distance. Must match the `left`/`top`
 * transition in styles.css: the class drives the leg animation and the
 * transition drives the travel, and if they disagree someone arrives and keeps
 * striding, or stops stepping halfway across the room.
 *
 * Fixed rather than proportional to distance on purpose — a real walking speed
 * would make a cross-room move take several seconds, and this is a board, not
 * a game. */
const WALK_MS = 700

/* Tracks who is mid-walk, so the sprite can run its leg cycle only while
 * actually travelling.
 *
 * Diffs the *rendered* position rather than the stored one, because those are
 * no longer the same thing: taking a slot seats you at a desk without changing
 * the coordinate the server holds for you. Diffing stored coordinates would
 * leave people sliding to their desk with no gait, and sliding back with none
 * either.
 *
 * Derived here rather than sent by the server: movement is already broadcast
 * as a new position, and "is walking" is a property of the *rendering* of that
 * change, not a fact about the board. Putting it in the protocol would mean a
 * client that reconnected mid-walk had to be told about an animation.
 */
function useWalking(placed) {
  const [walking, setWalking] = useState(() => new Set())
  const previous = useRef(new Map())
  const timers = useRef(new Map())

  useEffect(() => {
    const moved = []
    placed.forEach(({ id, left, top }) => {
      const was = previous.current.get(id)
      if (was && (was.left !== left || was.top !== top)) moved.push(id)
      previous.current.set(id, { left, top })
    })
    if (!moved.length) return

    setWalking((current) => new Set([...current, ...moved]))

    // Per-user timers. A single shared timer would let one person's move cut
    // short another's walk that started 200ms earlier.
    const handles = timers.current
    moved.forEach((id) => {
      clearTimeout(handles.get(id))
      handles.set(
        id,
        setTimeout(() => {
          handles.delete(id)
          setWalking((current) => {
            const next = new Set(current)
            next.delete(id)
            return next
          })
        }, WALK_MS),
      )
    })
  }, [placed])

  // Unmount only: clearing on every change would cancel walks in flight.
  useEffect(() => {
    const handles = timers.current
    return () => handles.forEach(clearTimeout)
  }, [])

  return walking
}

const toFloor = (y) => WALK_TOP + (y * (100 - WALK_TOP)) / 100
const fromFloor = (v) => ((v - WALK_TOP) * 100) / (100 - WALK_TOP)

const ARROWS = {
  ArrowUp: [0, -STEP],
  ArrowDown: [0, STEP],
  ArrowLeft: [-STEP, 0],
  ArrowRight: [STEP, 0],
}

/* The floor plan, in the same 0-100 percentage space as the avatars.
 *
 * Percentages, not pixels, for exactly the reason CONTRACT.md gives for avatar
 * coordinates: three browsers at different widths have to agree on where
 * things are. A pixel room would sit under a different person's feet on a
 * narrower window, which is the one thing this board is supposed to be
 * incapable of. Every number in this section is a percentage of the floor box,
 * so the whole plan scales with it and nothing here needs a media query.
 *
 * The office reads in three bands, top to bottom:
 *
 *   0-14    back wall — window, whiteboard. Not walkable (WALK_TOP).
 *   14-62   two project rooms, standing against that wall, one per agent slot,
 *           with a corridor between them.
 *   62-100  the open floor — waiting area in the middle, hot desks on the
 *           left, cooler and plants at the edges.
 *
 * `x`/`y` are the room's top-left corner, not its centre, because a room is
 * placed by its edges and the wall it shares with the corridor is the thing
 * that has to line up.
 *
 * The rooms are narrower than the space would allow, and the 20% left between
 * them is the reason. The floor is a wide, short box — 606x250 at the demo
 * window — and two rooms filling it edge to edge left a 76px desk adrift in a
 * 267px room and no way to read the plan except as "two boxes". A corridor
 * running from the whiteboard down to the waiting area gives the office
 * circulation, and gives each room a size its furniture can fill.
 *
 * Positions only. *Who* works in each room comes from `state_snapshot.agents[]`,
 * which carries the roster — so renaming an agent is a backend edit and the
 * floor follows, rather than two lists that have to be kept in step.
 */
const ROOMS = [
  { slot_id: 'coder', x: 6, y: 14, w: 34, h: 48 },
  { slot_id: 'researcher', x: 60, y: 14, w: 34, h: 48 },
]

/* How far down its room a desk sits, as a fraction of the room's height.
 *
 * Above centre on purpose: the desk stack is drawn from its own centre, and
 * the person seated at it hangs SEAT_DROP below that, carrying two lines of
 * label under them. At 0.42 in a 46-tall room the occupant's "working" line
 * fell across the bottom wall — measured on the deployed floor height, not
 * guessed. 0.38 in a 48-tall room lands the whole stack inside. */
const DESK_IN_ROOM = 0.38

/* The rooms to draw, each joined to the live slot behind it.
 *
 * Driven by the plan rather than by the agent list, so an agent with no room is
 * simply not drawn — better than a desk stacked at (0, 0) on top of another
 * one. The join itself is unchanged from the two-spot version it replaces; only
 * the geometry either side of it is new.
 */
function roomsFrom(agents) {
  const bySlot = new Map(agents.map((agent) => [agent.slot_id, agent]))
  return ROOMS.map((room) => {
    const agent = bySlot.get(room.slot_id)
    return {
      ...room,
      agent,
      name: agent?.name || room.slot_id,
      role: agent?.role || '',
      busy: agent?.status === 'BUSY',
      /* The desk's centre in *floor* percent, kept alongside the room's own
       * corner rather than replacing it. The desk is drawn room-locally, but
       * the person seated at it is a pawn on the floor like any other, so the
       * one coordinate that has to exist in floor space is this one. Deriving
       * it back out of the corner at each use site is how the two drift. */
      deskX: room.x + room.w / 2,
      deskY: room.y + room.h * DESK_IN_ROOM,
    }
  })
}

/* The waiting area, and where people stand in it.
 *
 * This is the half of the phase that makes the queue a place rather than a
 * label. A queued member is drawn on a numbered spot, in queue order, exactly
 * the way a slot holder is drawn at their desk — same mechanism, same promise:
 * the coordinate the server holds for them is never touched, so leaving the
 * queue walks them back to wherever they were actually standing.
 *
 * The line runs left to right at the mouth of the rooms, so when a slot frees
 * and the front of the queue is dispatched, the walk from the waiting spot to
 * the desk crosses the room in full view. That walk is the scheduler, visible.
 */
/* WAIT_X0 is 38 rather than the area's own left edge because the first spot at
 * 30 put somebody 5px under the "WAITING AREA" caption, and the two read as one
 * smudge at recording size. Measured against the rendered boxes at 640px, not
 * eyeballed. The caption then moved to the top *right* — the far end of the
 * line — which is the half of the fix that holds at every floor width; see
 * `.waiting__label` in styles.css. */
const WAIT_X0 = 38
const WAIT_DX = 9
const WAIT_Y0 = 80
const WAIT_PER_ROW = 5
/* Overflow rows stack *upward*, towards the rooms. Downward would put the
 * sixth person's name label through the bottom edge of the floor. */
const WAIT_DY = -12

function waitSpot(position) {
  const i = Math.max(0, position - 1)
  const row = Math.floor(i / WAIT_PER_ROW)
  const col = i % WAIT_PER_ROW
  return { x: WAIT_X0 + col * WAIT_DX, y: WAIT_Y0 + row * WAIT_DY }
}

/* Hot desks for the humans, along the left edge of the open floor.
 *
 * Furniture, not state: nobody is assigned one and nothing lights up. They earn
 * their place by answering "why is this person standing here" — without them
 * the lower half is an empty field with a rug in it, and the two rooms read as
 * the only places in the office anyone could possibly be.
 */
const HOT_DESKS = [
  { x: 9, y: 72 },
  { x: 9, y: 91 },
]

/* How far below a desk's own centre its chair sits, in floor percent. The desk
 * stack is label, monitor, surface, chair from the top, all centred on the
 * desk coordinate, so the seat is roughly a third of that stack below it. */
const SEAT_DROP = 13

/* Fixed decor. Percentages for the same reason. Re-placed for the room plan:
 * the old positions sat where the project rooms now stand, and a potted plant
 * inside somebody's office is a different claim than one in the corridor. */
const PLANTS = [
  { x: 92, y: 91 },
  { x: 16, y: 66 },
]

/* The shared workspace floor.
 *
 * Absolutely positioned elements inside a box, moved with CSS transitions — no
 * canvas element, no game engine, no animation loop (ARCHITECTURE.md rules a
 * game engine out, and nothing here needs one). Everything is positioned in
 * percentages, so the same room renders identically at any window width, which
 * is the property the multi-browser demo depends on.
 *
 * The desks are not decoration: each one is bound to a scheduler slot and
 * lights up while that slot is BUSY, so "both agents are working and a third
 * person is waiting" is legible from the room itself.
 */
export function CanvasPanel({ members, me, busyUsers, agents = [], queue = [], onMove }) {
  const rooms = roomsFrom(agents)
  const queuedBy = new Map(queue.map((entry) => [entry.user_id, entry.queue_position]))

  /* Who is sitting where. A slot holder is drawn at that slot's desk rather
   * than at their own coordinate — and crucially the coordinate itself is left
   * alone, so releasing the slot walks them back to wherever they were
   * standing. Writing the seat into their position instead would strand them
   * at the desk afterwards, and would mean the room quietly editing state the
   * server owns. */
  const seatOf = new Map()
  rooms.forEach((room) => {
    const holder = room.busy ? room.agent?.current_user : null
    if (holder) seatOf.set(holder, room)
  })

  /* Three places a person can be, in this order of precedence: at an agent's
   * desk because they hold that slot, on a waiting spot because they are in
   * the queue, or wherever they last walked to. The first two are the board
   * showing scheduler state; only the third is the coordinate the server
   * keeps. Somebody dispatched off the front of the queue moves from the
   * second to the first, which is the walk the room exists to show. */
  const placed = members.map((member, index) => {
    const desk = seatOf.get(member.user_id)
    const position = desk ? null : queuedBy.get(member.user_id)
    const waiting = position ? waitSpot(position) : null
    return {
      id: member.user_id,
      member,
      index,
      desk,
      waiting: Boolean(waiting),
      left: desk
        ? desk.deskX
        : waiting
          ? waiting.x
          : Math.max(0, Math.min(100, Number(member.x) || 0)),
      top: desk
        ? desk.deskY + SEAT_DROP
        : waiting
          ? waiting.y
          : toFloor(Math.max(0, Math.min(100, Number(member.y) || 0))),
    }
  })

  const walking = useWalking(placed)

  /* The landing page renders this same room from canned state, with no socket
   * behind it. Without an `onMove` there is nothing to move, so the floor drops
   * its click target, its tab stop and its "click to move" affordance rather
   * than advertising an interaction that silently does nothing — and becomes an
   * image for a screen reader instead of an application. */
  const interactive = Boolean(onMove)

  const move = (event) => {
    const box = event.currentTarget.getBoundingClientRect()
    if (!box.width || !box.height) return
    onMove(
      ((event.clientX - box.left) / box.width) * 100,
      fromFloor(((event.clientY - box.top) / box.height) * 100),
    )
  }

  const nudge = (event) => {
    const delta = ARROWS[event.key]
    if (!delta) return
    event.preventDefault()
    const self = members.find((m) => m.user_id === me)
    onMove((Number(self?.x) || 0) + delta[0], (Number(self?.y) || 0) + delta[1])
  }

  return (
    <section className="panel panel--floor" aria-labelledby="floor-label">
      <div className="panel__head">
        <span className="panel__label" id="floor-label">
          Workspace floor
        </span>
        {interactive && (
          <span className="panel__aside">click or use arrow keys to move</span>
        )}
      </div>

      <div
        className={`floor ${interactive ? '' : 'floor--still'}`}
        onClick={interactive ? move : undefined}
        onKeyDown={interactive ? nudge : undefined}
        tabIndex={interactive ? 0 : undefined}
        role={interactive ? 'application' : 'img'}
        aria-label={
          `Shared workspace floor. ${members.length} ` +
          `${members.length === 1 ? 'person' : 'people'} present` +
          (interactive
            ? '. Click or use the arrow keys to move your marker.'
            : `, ${busyUsers.size} at an agent desk.`)
        }
      >
        {/* Wall fixtures sit in the back band of the room, above everything
            else, so the floor has an "up" and reads as enclosed rather than as
            a field seen from above. */}
        <div className="fixture fixture--board" aria-hidden="true">
          <span className="board__scribble" />
          <span className="board__scribble board__scribble--short" />
        </div>

        <div className="fixture fixture--window" aria-hidden="true" />
        <div className="fixture fixture--daylight" aria-hidden="true" />

        <div className="fixture fixture--cooler" aria-hidden="true">
          <span className="cooler__bottle" />
          <span className="cooler__body" />
        </div>

        {/* The waiting area: a rug and a caption, with no state of its own —
            the state is *who is standing on it*. Drawn before the rooms so a
            room's wall reads as being in front of the corridor floor rather
            than behind it. */}
        <div className="waiting" aria-hidden="true">
          <span className="waiting__label">Waiting area</span>
        </div>

        {/* Hot desks. Furniture — see HOT_DESKS. */}
        {HOT_DESKS.map((spot, i) => (
          <div
            key={i}
            className="hotdesk"
            style={{ left: `${spot.x}%`, top: `${spot.y}%` }}
            aria-hidden="true"
          >
            <span className="hotdesk__surface" />
            <span className="hotdesk__chair" />
          </div>
        ))}

        {/* The project rooms, each bound to a scheduler slot: walls, a doorway
            onto the corridor, and the agent's desk inside. Before the pawns so
            someone standing at a desk is in front of it, not behind it. */}
        {rooms.map((room) => (
          <div
            key={room.slot_id}
            className={`room ${room.busy ? 'room--busy' : ''}`}
            style={{
              left: `${room.x}%`,
              top: `${room.y}%`,
              width: `${room.w}%`,
              height: `${room.h}%`,
            }}
            aria-hidden="true"
          >
            {/* A gap punched in the wall that faces the corridor. Without it
                the rooms are two boxes; with it they are rooms somebody could
                have walked into, which is most of what sells a plan view. */}
            <span className="room__door" />

            <div
              className={`desk ${room.busy ? 'desk--busy' : ''}`}
              style={{ top: `${DESK_IN_ROOM * 100}%` }}
            >
              {/* Nameplate above the desk, not below it. People approach a desk
                  from the chair side, so a label under the chair is guaranteed
                  to end up behind somebody's head. The name reads as a person
                  and the role as a job, which is the whole difference between
                  a desk and a slot. */}
              <span className="desk__label">{room.name}</span>
              {room.role && <span className="desk__role">{room.role}</span>}
              <span className="desk__monitor" />
              <span className="desk__surface">
                <span className="desk__keyboard" />
              </span>
              <span className="desk__chair" />
            </div>
          </div>
        ))}

        {PLANTS.map((plant, i) => (
          <div
            key={i}
            className="decor decor--plant"
            style={{ left: `${plant.x}%`, top: `${plant.y}%` }}
            aria-hidden="true"
          >
            <span className="decor__leaves" />
            <span className="decor__pot" />
          </div>
        ))}

        {placed.map(({ id, member, index, desk, waiting, left, top }) => {
          const mine = id === me
          const busy = busyUsers.has(id)
          const position = queuedBy.get(id)
          const isWalking = walking.has(id)
          const look = lookFor(member.avatar, id)
          // Seated only once they have actually arrived. Tucking the legs away
          // at the moment the slot is claimed would have them glide to the
          // desk with nothing to walk on.
          const seated = Boolean(desk) && !isWalking
          return (
            <div
              key={id}
              className={
                `pawn ${mine ? 'pawn--mine' : ''} ${busy ? 'pawn--busy' : ''} ` +
                `${isWalking ? 'pawn--walking' : ''} ${seated ? 'pawn--seated' : ''} ` +
                `${waiting && !isWalking ? 'pawn--waiting' : ''}`
              }
              style={{ left: `${left}%`, top: `${top}%` }}
            >
              {/* Three sprite designs, assigned by position in the deduped
                  member list so everyone looks distinct without the server
                  having to carry an appearance field. */}
              <span
                className="sprite"
                style={{
                  '--art': seated ? look.seat : look.art,
                  '--art-step': look.step,
                  '--sp-hair': look.hair,
                }}
                aria-hidden="true"
              />
              <span className="pawn__name">
                {mine ? 'you' : id}
              </span>
              <span className="pawn__state">
                {busy ? 'working' : position ? `queued #${position}` : 'idle'}
              </span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

/* Team-level events you would otherwise miss because you were looking at a
 * different panel. Deliberately only two kinds — a toast for everything turns
 * into noise nobody reads, and on a recording it covers the board. */
export function ToastStack({ toasts }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <article className={`toast toast--${toast.kind}`} key={toast.id}>
          <p className="toast__title">{toast.title}</p>
          <p className="toast__text">{toast.text}</p>
          {toast.who && <p className="toast__who">saved by {toast.who}</p>}
        </article>
      ))}
    </div>
  )
}

export function MemoryPanel({ memory }) {
  return (
    <section className="panel panel--memory" aria-labelledby="memory-label">
      <div className="panel__head">
        <span className="panel__label" id="memory-label">
          Team memory
        </span>
        <span className="panel__aside">
          {memory.length} {memory.length === 1 ? 'fact' : 'facts'}
        </span>
      </div>
      <div className="memory">
        {memory.map((fact) => (
          <span className="fact" key={fact.key}>
            <span className="fact__key">{fact.key}</span>
            <span className="fact__val"> — {fact.val}</span>
          </span>
        ))}
      </div>
    </section>
  )
}

export function ActivityPanel({ activity, children }) {
  return (
    <section className="panel panel--grow panel--activity" aria-labelledby="activity-label">
      <div className="panel__head">
        <span className="panel__label" id="activity-label">
          Activity
        </span>
      </div>

      {activity.length === 0 ? (
        <p className="empty">Nothing yet. Request an agent to start.</p>
      ) : (
        <div className="activity">
          {activity.map((entry, index) => (
            <article
              className={`entry entry--${entry.kind}`}
              key={`${entry.ts.getTime()}-${index}`}
            >
              <time className="entry__ts">{formatClock(entry.ts)}</time>
              <div className="entry__body">
                <span className="entry__who">
                  {entry.who}
                  {entry.cost ? (
                    <span className="entry__cost">
                      {entry.estimated ? '~' : ''}
                      {NUM.format(entry.cost)} tokens
                    </span>
                  ) : null}
                </span>
                <p className="entry__text">{entry.text}</p>
              </div>
            </article>
          ))}
        </div>
      )}

      {children}
    </section>
  )
}
