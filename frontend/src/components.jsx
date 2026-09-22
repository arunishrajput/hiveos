/* Presentational pieces of the operator console.
 *
 * All of them are pure functions of board state, so what a browser shows is
 * exactly what the last snapshot said — which is the property the demo turns
 * on: three windows, one board, no divergence.
 */

import { useEffect, useRef, useState } from 'react'

import { lookFor } from './sprites'
import { useWorld } from './worlds'

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

/* The application chrome, along the top of the shell.
 *
 * `auto mode on` is a readout, not a switch. The scheduler has dispatched off
 * the front of the queue by itself since Phase 2, so the line is simply true —
 * and a toggle here would be a control with nothing behind it, which is the
 * one thing a board about honest state cannot ship.
 *
 * `StatusRail` is what this replaces and is still exported: the landing page's
 * canned preview uses it, and it is the right shape for a panel stack.
 */
export function AppBar({ team, connection, members, agents, version, onSettings, onWorlds }) {
  const working = agents.filter((a) => a.status === 'BUSY').length

  return (
    <header className="appbar">
      <Mark className="appbar__mark" />
      <span className="appbar__name">HiveOS</span>
      <span className="appbar__version">{version}</span>
      <span className="appbar__mode">auto mode on</span>

      <span className="appbar__spacer" />

      <span className="appbar__stat">
        {working}/{agents.length} working
      </span>
      <span className="appbar__team">{team}</span>
      <span className="appbar__stat">
        {members.length} {members.length === 1 ? 'person' : 'people'}
      </span>
      <Lamp connection={connection} />

      {/* Everyone gets this one, unlike the gear beside it. Choosing a world
          is a preference about your own screen — it is stored in your browser,
          changes no board state and is broadcast to nobody, so there is
          nothing here for the server to refuse and no reason to gate it on
          being an administrator. */}
      {onWorlds && (
        <button
          type="button"
          className="appbar__gear"
          onClick={onWorlds}
          aria-label="Change world"
        >
          <span aria-hidden="true">◑</span>
        </button>
      )}

      {/* Only an administrator gets the gear, because it opens the only panel
          whose actions the server would accept from them. Hiding it from
          everyone else is convenience — the refusal is server-side. */}
      {onSettings && (
        <button
          type="button"
          className="appbar__gear"
          onClick={onSettings}
          aria-label="Workspace settings"
        >
          <span aria-hidden="true">⚙</span>
        </button>
      )}
    </header>
  )
}

/* One agent's portrait, from the same sprite system as the people.
 *
 * `character` is undefined until an agent can be hired with one, and `lookFor`
 * already falls back to hashing the second argument — so every desk gets a
 * stable, distinct face today and the field simply starts being honoured the
 * moment the backend carries it.
 */
export function AgentFace({ agent, className = '' }) {
  const { world } = useWorld()
  const look = lookFor(agent.character, agent.slot_id, world, true)
  return (
    <span
      className={`agentface ${className}`}
      style={{ '--art': look.art, '--sp-hair': look.hair }}
      aria-hidden="true"
    />
  )
}

/* What an agent is doing right now, in a few words.
 *
 * One function, three consumers — the speech bubble over the desk, the roster
 * card along the bottom, and the inspector header. Phase 8's fairness bug was
 * exactly this shape: the same state derived independently in two places and
 * allowed to disagree on camera.
 */
export function agentStatus(agent, note, short = false) {
  // Busy wins over the note, always. A note is the afterglow of the *last*
  // thing this desk finished, and letting it outrank live state would put
  // "done · 549 tokens" over a desk that is mid-task for somebody else.
  if (agent.status === 'BUSY') {
    if (!agent.current_user) return 'working'
    // `short` is for the speech bubble, which has a room's width to live in
    // and shares it with whoever is standing at the desk. Same fact, fewer
    // words — still one function, so the bubble and the roster card can never
    // end up reporting different things.
    return short
      ? `for ${agent.current_user}`
      : `working for ${agent.current_user}`
  }
  return note || 'idle'
}

/* The roster along the bottom: every desk on this floor, at a glance.
 *
 * Selecting a card is what the inspector on the right is bound to, so this is
 * navigation as well as status. The progress bar is deliberately indeterminate
 * — the server knows a task is running but not how far through it is, and a bar
 * that implied otherwise would be inventing a number.
 */
export function RosterStrip({ agents, selected, onSelect, onAdd, noteFor }) {
  return (
    <section className="roster" aria-label="Agents on this floor">
      <div className="roster__cards">
        {agents.map((agent) => {
          const busy = agent.status === 'BUSY'
          const on = selected === agent.slot_id
          const note = noteFor?.(agent)
          return (
            <button
              type="button"
              key={agent.slot_id}
              onClick={() => onSelect(agent.slot_id)}
              aria-pressed={on}
              className={
                `agentcard ${on ? 'agentcard--on' : ''} ` +
                `${busy ? 'agentcard--busy' : ''}`
              }
            >
              <AgentFace agent={agent} className="agentcard__face" />

              <span className="agentcard__head">
                <span className="agentcard__name">{agent.name || agent.slot_id}</span>
                <span className={`chip ${busy ? 'chip--busy' : 'chip--idle'}`}>
                  <span className="chip__dot" aria-hidden="true" />
                  {busy ? 'working' : 'idle'}
                </span>
              </span>

              {/* The chip beside the name already says "idle", so an idle card
                  spends its second line on what this desk is *for* instead of
                  saying it twice. The moment there is something to report —
                  running, or just finished — the live line takes over. */}
              <span className="agentcard__sub">
                {busy || note
                  ? agentStatus(agent, note)
                  : agent.role || agent.slot_id}
              </span>

              <span className="agentcard__track" aria-hidden="true">
                <span className="agentcard__fill" />
              </span>
            </button>
          )
        })}
      </div>

      {onAdd && (
        <button type="button" className="roster__add" onClick={onAdd}>
          + add agent
        </button>
      )}
    </section>
  )
}

/* One agent's terminal.
 *
 * Styled as a live PTY because that is the thing it stands in for, but it is
 * not pretending to be a shell: every line is an event this board actually
 * broadcast, and the glyph names the kind rather than decorating it. Newest at
 * the bottom, scrolled to, the way a terminal behaves.
 */
const STREAM_MARK = {
  response: '✓',
  handoff: '→',
  memory: '★',
  chat: '·',
  hire: '+',
  error: '!',
}

export function StreamPane({ entries, label, empty }) {
  const ref = useRef(null)

  // Pinned to the bottom on every new line. The pane is short and the newest
  // answer is the one being read, so following the tail is right here — unlike
  // the old activity panel, which was the whole board's log and was read by
  // scrolling back.
  useEffect(() => {
    const node = ref.current
    if (node) node.scrollTop = node.scrollHeight
  }, [entries.length])

  return (
    <div className="stream">
      <div className="stream__head">
        <span className="stream__live" aria-hidden="true" />
        <span className="stream__label">{label}</span>
      </div>

      <div className="stream__body" ref={ref} role="log" aria-live="polite">
        {entries.length === 0 ? (
          <p className="stream__empty">{empty}</p>
        ) : (
          // `activity` is newest-first everywhere else in the app; a terminal
          // reads the other way, so it is reversed here rather than stored
          // twice. `slice()` because `reverse()` mutates.
          entries
            .slice()
            .reverse()
            .map((entry, index) => (
              <div
                className={`streamline streamline--${entry.kind}`}
                key={`${entry.ts.getTime()}-${index}`}
              >
                <span className="streamline__mark" aria-hidden="true">
                  {STREAM_MARK[entry.kind] ?? '>'}
                </span>
                <span className="streamline__body">
                  <span className="streamline__who">
                    {entry.who}
                    {entry.cost ? (
                      <span className="streamline__cost">
                        {entry.estimated ? '~' : ''}
                        {NUM.format(entry.cost)} tokens
                      </span>
                    ) : null}
                  </span>
                  <span className="streamline__text">{entry.text}</span>
                </span>
              </div>
            ))
        )}
      </div>
    </div>
  )
}

/* What one agent has actually done, and what each task cost.
 *
 * This is the product's evidence rather than a log: a **refused** task records
 * zero tokens, which is the clearest thing in the whole app that the ceiling is
 * a control and not a gauge. Filtered to one desk here; the board-wide version
 * rides on `state_snapshot` and feeds `SpendPanel`.
 */
const LEDGER_STATE = {
  done: 'done',
  refused: 'refused at the ceiling',
  failed: 'failed',
}

export function LedgerPane({ rows }) {
  if (!rows.length) {
    return <p className="stream__empty">No tasks yet at this desk.</p>
  }

  return (
    <div className="ledger">
      {rows.map((row, index) => {
        const status = row.status || 'done'
        return (
          <article
            className={`ledrow ledrow--${status}`}
            key={`${row.task_id ?? 'row'}-${index}`}
          >
            <span className="ledrow__top">
              <span className="ledrow__who">{row.user_id}</span>
              <span className="ledrow__state">{LEDGER_STATE[status] ?? status}</span>
              <span className="ledrow__cost">
                {row.estimated ? '~' : ''}
                {NUM.format(row.tokens ?? 0)}
              </span>
            </span>

            {row.prompt && <p className="ledrow__prompt">{row.prompt}</p>}

            {row.handoff_from_name && (
              <span className="ledrow__tag">
                handed over by {row.handoff_from_name}
              </span>
            )}
          </article>
        )
      })}
    </div>
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
  const { world } = useWorld()
  const queuedBy = new Map(queue.map((entry) => [entry.user_id, entry.queue_position]))

  return (
    <section className="memberbar" aria-label="Who is here">
      {members.map((member) => {
        const busy = busyUsers.has(member.user_id)
        const position = queuedBy.get(member.user_id)
        const state = busy ? 'busy' : position ? 'queued' : 'idle'
        const look = lookFor(member.avatar, member.user_id, world)
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
          const look = lookFor(avatarOf.get(row.user_id), row.user_id, world)
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
 * that spot. Both directions take the same `walkTop`; they cannot drift apart.
 *
 * Lowered from 22 to 14 with the room plan: the wall band got thinner because
 * the project rooms now stand against it and were eating the band's height
 * twice. Safe to change precisely because both directions read one number —
 * the only visible effect is that a stored coordinate renders slightly higher.
 *
 * That number was the module constant `WALK_TOP = 14` until Phase 18, and the
 * stylesheet had its own copy as `100% 14%`. It now comes from the world
 * registry, which stamps `--walk-top` for the stylesheet and hands the same
 * value to the walk math — one source, two consumers, because a world that
 * raises its wall band has to move the paint and the walkable area together.
 */

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

const toFloor = (y, walkTop) => walkTop + (y * (100 - walkTop)) / 100
const fromFloor = (v, walkTop) => ((v - walkTop) * 100) / (100 - walkTop)

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
 *   0-14    back wall — window, whiteboard. Not walkable (`walkTop`).
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
  { x: 6, y: 14, w: 34, h: 48 },
  { x: 60, y: 14, w: 34, h: 48 },
]

/* Where desks three to six go.
 *
 * The two project rooms are the floor's architecture and they stay exactly as
 * Phase 15 measured them. Everything hired after that sits at an open-plan
 * desk along the left edge and across the bottom — which is where `HOT_DESKS`
 * already drew furniture, so the room was always composed for people to be
 * there. Those two coordinates are now the first two open desks rather than
 * props, which is why the constant is gone: a desk that somebody works at and
 * a desk that is scenery cannot be the same thing on a board whose whole claim
 * is that it shows real state.
 *
 * Open desks are not rooms. They get no walls and no doorway — an office does
 * not give every hire a private office, and walled rooms for everyone in a
 * floor this short would read as a spreadsheet.
 *
 * **Two, and the floor caps at four. That number is measured, not chosen.**
 * The lower band is 38% of the floor tall (62 to 100) with the waiting-area
 * rug across the middle, so the only free places are the left and right
 * margins. Two rows per side was the first attempt and does not fit: at the
 * 0.72 scale in styles.css a desk stack is ~19% and its seated agent hangs
 * `OPEN_SEAT_DROP` below that, so row one's character lands on row two's
 * nameplate, and row two's character falls off the bottom of the floor.
 * Shrinking further makes a nameplate unreadable at recording size.
 *
 * So the floor holds four desks and `agents.MAX_AGENTS` says four. A cap that
 * matches the room is better than one that promises a desk with nowhere to put
 * it — the roster strip would list an agent the floor could not show.
 */
const OPEN_DESKS = [
  { x: 8, y: 78 },
  { x: 91, y: 78 },
]

/* How far down its room a desk sits, as a fraction of the room's height.
 *
 * Above centre on purpose: the desk stack is drawn from its own centre, and
 * the person seated at it hangs SEAT_DROP below that, carrying two lines of
 * label under them. At 0.42 in a 46-tall room the occupant's "working" line
 * fell across the bottom wall — measured on the deployed floor height, not
 * guessed. 0.38 in a 48-tall room lands the whole stack inside. */
const DESK_IN_ROOM = 0.38

/* The desks to draw, each joined to the live agent sitting at it. */
function roomsFrom(agents) {
  /* Driven by the *agent list* now, not by a fixed plan keyed on slot id.
   *
   * It had to invert: the plan used to name `coder` and `researcher`, which
   * only worked while those were the only two desks that could ever exist.
   * The floor now lays out whatever roster it is given, in roster order — the
   * first two into the project rooms, the rest at open desks — so a hire
   * appears at the next free place and a dismissal leaves no hole.
   *
   * An agent past the last open desk is simply not drawn. The server caps a
   * floor at six, which is exactly how many places this plan has, so that is
   * belt and braces rather than an expected state — and a desk stacked on top
   * of another one would be worse than one that is missing.
   */
  return agents.slice(0, ROOMS.length + OPEN_DESKS.length).map((agent, index) => {
    const room = ROOMS[index]
    const open = room ? null : OPEN_DESKS[index - ROOMS.length]
    return {
      ...(room ?? { x: open.x - 8, y: open.y - 8, w: 0, h: 0 }),
      slot_id: agent.slot_id,
      walled: Boolean(room),
      agent,
      name: agent?.name || agent.slot_id,
      role: agent?.role || '',
      busy: agent?.status === 'BUSY',
      /* The desk's centre in *floor* percent, kept alongside the room's own
       * corner rather than replacing it. The desk is drawn room-locally, but
       * the person seated at it is a pawn on the floor like any other, so the
       * one coordinate that has to exist in floor space is this one. Deriving
       * it back out of the corner at each use site is how the two drift.
       *
       * An open desk has no room to be local to, so it is its own centre. */
      deskX: room ? room.x + room.w / 2 : open.x,
      deskY: room ? room.y + room.h * DESK_IN_ROOM : open.y,
      // How far below the desk its occupant sits. An open desk is drawn at
      // 0.72, so its chair is closer to its own centre than a room desk's is.
      seatDrop: room ? SEAT_DROP : OPEN_SEAT_DROP,
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
/* The line is one row, and it grows by tightening rather than by wrapping.
 *
 * It used to wrap: `WAIT_PER_ROW` 5, with `WAIT_DY` −12 stacking the overflow
 * upward. That could not work at any framing, which measuring the rendered
 * boxes made plain. At the 540 demo framing the floor is 516×260 and a pawn —
 * sprite, name, state caption — is **75px tall, 29% of the floor**. The
 * waiting rug is 32% tall. One row fills it. The second row landed 30px above
 * the first, so the sixth person's `queued #6` sat across the first person's
 * head: **1.00:1 on Paper Office**, occlusion rather than colour. And there
 * was nowhere for a real second row to go — clearing a 29%-tall pawn would put
 * it at 51–65%, and the rooms end at 61.6%.
 *
 * So: no second row, and the line tightens as it grows.
 *
 * **The spacing is in pixels, and that is the whole point.** Everything that
 * can collide here is a fixed pixel size: the sprite is `9 * --px-n` px wide,
 * and both captions are 9px type. None of it tracks the floor, which is
 * **366px wide on a 390 phone, 516px at the 540 framing, and 995px at 1440**
 * — while the caption stays 53px at every one of them and the sprite grows
 * only 36px → 45px. A pitch expressed as a percentage of that box is
 * therefore a different clearance at each width: the old 9% was 46px at 540,
 * under the 53px `queued #N` it had to clear — captions overlapped from
 * *three* queued there, well before the row ever wrapped — and a roomy 90px
 * at 1440. Percentages are right for the room plan, which is a composition;
 * they are wrong for clearances between glyphs, which are not.
 *
 * Past the point where `queued #N` no longer fits, the caption goes compact —
 * `#6` — rather than the line wrapping. `waitLayout` decides the pitch and the
 * caption together, from the same measurement, so the copy can never be wider
 * than the space allotted to it. The word `queued` is what the compact form
 * gives up; it is still spelled out on the member bar, and the ochre and the
 * rug both still say waiting.
 */
/* Floor percent — the line's preferred width, centred on WAIT_MID. 28%–72%,
 * inside the rug's 21%–79% with room for the end captions to hang over. */
const WAIT_SPAN = 44
const WAIT_MID = 50
const WAIT_Y0 = 80
/* How much of the floor's own width the person at each end of the line keeps
 * clear, in pixels — half the widest thing a pawn draws, plus air. The line
 * stops widening here and starts overlapping instead, which is the milder of
 * the two failures: a crowded line is still legible, a person drawn past the
 * edge of the floor box is clipped.
 *
 * In pixels and not a percentage of the span for the reason the whole of this
 * section is: a pawn is the same size on a 358px floor as on a 928px one, so
 * a percentage margin is a different clearance at each. A 92% span looked
 * right and put two people off the left edge of a 390px phone at ten queued —
 * their *centres* were inside the floor and their sprites were not. */
const WAIT_EDGE_PX = 32

/* Pixels, measured on the rendered boxes at both demo framings.
 * `queued #12` is 53px; `#12` is 20px; the sprite is 36px at `--px-n` 4 and
 * grows with it. `WAIT_GAP_PX` is the air between two of them. */
const WAIT_CAPTION_PX = 53
const WAIT_COMPACT_PX = 20
const WAIT_GAP_PX = 5

/* The sprite's rendered width. `--px-n` is the one number that scales the
 * character (see `.sprite` in styles.css, which sizes it `9 * --px-n`), so
 * reading it is how this stays true when a wider layout grows the cast. */
function spriteWidth(el) {
  const n = Number(getComputedStyle(el).getPropertyValue('--px-n')) || 4
  return 9 * n
}

/* How far apart the waiting spots stand, and whether the long caption fits.
 *
 * Returns pixels. One function for both answers on purpose: the caption's
 * length is a function of the space, so deciding them apart is how they would
 * come to disagree.
 */
function waitLayout(total, floorWidth, sprite) {
  const longPitch = WAIT_CAPTION_PX + WAIT_GAP_PX
  const compactPitch = Math.max(sprite, WAIT_COMPACT_PX) + WAIT_GAP_PX
  if (total <= 1 || !floorWidth) return { pitch: longPitch, compact: false }

  // What the preferred span would give this many people, and what the hard
  // span would — the second only matters once the first is already too tight.
  const wanted = (floorWidth * (WAIT_SPAN / 100)) / (total - 1)
  const mostItMaySpread =
    Math.max(0, floorWidth - WAIT_EDGE_PX * 2) / (total - 1)

  const pitch = Math.max(
    Math.min(longPitch, wanted),
    Math.min(compactPitch, mostItMaySpread),
  )
  return { pitch, compact: pitch < longPitch }
}

/* One spot on the line, as a floor percentage — because that is the
 * coordinate space every pawn is positioned in and the walk animates through.
 * The pitch that produced it was pixels; this is the last step. */
function waitSpot(position, total, pitch, floorWidth) {
  const i = Math.max(0, position - 1)
  if (!floorWidth) return { x: WAIT_MID, y: WAIT_Y0 }
  const fromCentre = i - (Math.max(1, total) - 1) / 2
  return { x: WAIT_MID + ((fromCentre * pitch) / floorWidth) * 100, y: WAIT_Y0 }
}

/* `HOT_DESKS` was here, and is now `OPEN_DESKS` above.
 *
 * It was furniture — two desks nobody was assigned and nothing lit up, there
 * to answer "why is this person standing here". They are real desks now,
 * because agents three and four sit at them. That is the better outcome: the
 * lower half of the floor stopped being an empty field with a rug in it by
 * acquiring people rather than by acquiring props.
 */

/* How far below a desk's own centre its chair sits, in floor percent. The desk
 * stack is label, monitor, surface, chair from the top, all centred on the
 * desk coordinate, so the seat is roughly a third of that stack below it. */
const SEAT_DROP = 13

/* How far to the side of a desk the person who asked for the work stands.
 *
 * This is the floor catching up with what the product now is. The chair
 * belongs to the *agent* — it is their desk, they are the one working — so the
 * human who requested the task stands beside it and watches, rather than
 * sitting in it. Before hireable agents the two were the same thing and the
 * holder took the seat; drawing both there now would stack two characters on
 * one coordinate.
 *
 * 11 rather than something roomier: a room is 34% wide, so the desk's centre
 * has 17% of clearance either side, and the name label under a pawn needs the
 * rest of it.
 */
const VISITOR_DX = 11

/* The seat drop for an open desk.
 *
 * `SEAT_DROP` is in floor percent, and the agent seated at a desk is a pawn on
 * the floor rather than a child of the desk — so the 0.72 scale on `.opendesk`
 * shrinks the furniture and leaves the character sitting 13% below it, well
 * clear of the chair. Scaled by the same factor here, which is the whole
 * reason the two numbers have to move together.
 */
const OPEN_SEAT_DROP = Math.round(SEAT_DROP * 0.72)

/* How long the envelope takes to cross the floor. Must match the `left`/`top`
 * transition on `.envelope` in styles.css, for the same reason WALK_MS must
 * match the pawn's — and it is deliberately slower than a walk, because the
 * crossing is the thing being read rather than a side effect of somebody
 * moving. `HANDOFF_MS` in useHive.js is what decides how long it stays after
 * arriving, and must stay comfortably larger than this. */
const ENVELOPE_MS = 1100

/* One handoff, drawn as an envelope travelling from the desk that passed the
 * work to the desk that takes it.
 *
 * Mounted at the sender's desk and moved on the *second* animation frame. A
 * single rAF is not enough: React can batch the state change into the same
 * paint as the mount, and an element whose position is set before it has ever
 * been painted simply appears at the destination with no transition to run.
 *
 * Remounted per handoff by its key in `CanvasPanel`, so a second handoff
 * between the same two desks replays the crossing instead of React reusing an
 * element that is already sitting at the target.
 */
function Envelope({ from, to, label }) {
  const [at, setAt] = useState(from)

  useEffect(() => {
    let inner = 0
    const outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => setAt(to))
    })
    return () => {
      cancelAnimationFrame(outer)
      cancelAnimationFrame(inner)
    }
  }, [to])

  return (
    <div
      className="envelope"
      style={{ left: `${at.x}%`, top: `${at.y}%` }}
      /* Announced rather than hidden: the crossing is a real scheduling event,
         and the activity log entry it pairs with scrolls away. One short,
         polite line is what a screen reader should get out of an animation. */
      role="status"
      aria-live="polite"
    >
      <span className="envelope__flap" aria-hidden="true" />
      <span className="visually-hidden">{label}</span>
    </div>
  )
}

/* Fixed decor. Percentages for the same reason. Re-placed for the room plan:
 * the old positions sat where the project rooms now stand, and a potted plant
 * inside somebody's office is a different claim than one in the corridor. */
/* Fixed decor. Percentages for the same reason. The right-hand plant moved off
 * the bottom-right corner when that corner became the second open desk — it
 * was rendering as a brown box under Pam's chair. Now beside Iris's room, in
 * the right margin, which nothing else uses. */
const PLANTS = [
  { x: 97, y: 55 },
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
export function CanvasPanel({
  members,
  me,
  busyUsers,
  agents = [],
  queue = [],
  onMove,
  handoff = null,
  noteFor,
}) {
  /* The world supplies the cast and the height of the back wall. Everything
   * else about this floor — the room plan, the desks, the waiting spots — is
   * percentages and is the same in every world by design: keeping the
   * composition fixed is what lets nine worlds inherit the responsive
   * behaviour this floor earned over Phases 7, 15 and 17. */
  const { world } = useWorld()
  const walkTop = world.walkTop

  const rooms = roomsFrom(agents)
  const queuedBy = new Map(queue.map((entry) => [entry.user_id, entry.queue_position]))

  /* The waiting line is spaced in pixels (see `waitLayout`), so it needs the
   * floor's real width rather than its percentage one. Observed rather than
   * read once: the floor is fluid — 366px on a phone, 995px at 1440 — and it
   * resizes without this component remounting. */
  const floorRef = useRef(null)
  const [floorBox, setFloorBox] = useState({ width: 0, sprite: 36 })
  useEffect(() => {
    const el = floorRef.current
    if (!el) return undefined
    const read = () =>
      setFloorBox({ width: el.getBoundingClientRect().width, sprite: spriteWidth(el) })
    read()
    if (typeof ResizeObserver === 'undefined') return undefined
    const observer = new ResizeObserver(read)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const line = waitLayout(queue.length, floorBox.width, floorBox.sprite)
  const compactQueue = line.compact

  /* The envelope, if one is in flight. Resolved against the *room plan* rather
   * than the agent list, so a handoff naming a desk this floor does not draw —
   * a third agent with no room yet — simply shows nothing instead of flying an
   * envelope to (0, 0). */
  const byRoom = new Map(rooms.map((room) => [room.slot_id, room]))
  const crossing =
    handoff && byRoom.has(handoff.from) && byRoom.has(handoff.to)
      ? {
          key: handoff.id,
          from: byRoom.get(handoff.from),
          to: byRoom.get(handoff.to),
          label:
            `${handoff.fromName} passed this task to ${handoff.toName}` +
            (handoff.queued ? ', who is busy — it is waiting in the queue.' : '.'),
        }
      : null

  /* Who is standing where. Whoever asked for the running task is drawn beside
   * that agent's desk rather than at their own coordinate — and crucially the
   * coordinate itself is left alone, so the task ending walks them back to
   * wherever they were standing. Writing the spot into their position instead
   * would strand them at the desk afterwards, and would mean the room quietly
   * editing state the server owns. */
  const seatOf = new Map()
  rooms.forEach((room) => {
    const holder = room.busy ? room.agent?.current_user : null
    if (holder) seatOf.set(holder, room)
  })

  /* Three places a person can be, in this order of precedence: beside an
   * agent's desk because that agent is running their task, on a waiting spot
   * because they are in the queue, or wherever they last walked to. The first
   * two are the board showing scheduler state; only the third is the
   * coordinate the server keeps. Somebody dispatched off the front of the
   * queue moves from the second to the first, which is the walk the room
   * exists to show. */
  const placed = members.map((member, index) => {
    const desk = seatOf.get(member.user_id)
    const position = desk ? null : queuedBy.get(member.user_id)
    const waiting = position
      ? waitSpot(position, queue.length, line.pitch, floorBox.width)
      : null
    return {
      id: member.user_id,
      member,
      index,
      desk,
      waiting: Boolean(waiting),
      left: desk
        ? desk.deskX + VISITOR_DX
        : waiting
          ? waiting.x
          : Math.max(0, Math.min(100, Number(member.x) || 0)),
      top: desk
        ? desk.deskY + desk.seatDrop
        : waiting
          ? waiting.y
          : toFloor(Math.max(0, Math.min(100, Number(member.y) || 0)), walkTop),
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
      fromFloor(((event.clientY - box.top) / box.height) * 100, walkTop),
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
        ref={floorRef}
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
        {/* The two lower decoration slots. Empty in Paper Office — the office
            is the floor's own background and needs no backdrop — and filled by
            each world with art that does not exist here.

            Stacking is DOM order, not z-index: sky is the backdrop behind
            every object (a star field, a forest canopy, a water column) and
            ground is the plane marked on top of it (a path, caustics, a pool
            of light), both beneath the furniture and the rooms so a world can
            paint the ground without painting over the desks. */}
        <div className="worldlayer worldlayer--sky" aria-hidden="true" />
        <div className="worldlayer worldlayer--ground" aria-hidden="true" />

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

        {/* Every desk on this floor, drawn from the roster.

            The first two get walls and a doorway onto the corridor — those are
            the project rooms, and the doorway is most of what sells a plan
            view. Everything hired after that is an open-plan desk: the same
            desk, the same nameplate, the same monitor that lights when it is
            working, without a private office. Before the pawns, so someone
            standing at a desk is in front of it rather than behind it. */}
        {rooms.map((room) =>
          room.walled ? (
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
              <span className="room__door" />

              <div
                className={`desk ${room.busy ? 'desk--busy' : ''}`}
                style={{ top: `${DESK_IN_ROOM * 100}%` }}
              >
                {/* Nameplate above the desk, not below it. People approach a
                    desk from the chair side, so a label under the chair is
                    guaranteed to end up behind somebody's head. The name reads
                    as a person and the role as a job, which is the whole
                    difference between a desk and a slot. */}
                <span className="desk__label">{room.name}</span>
                {room.role && <span className="desk__role">{room.role}</span>}
                <span className="desk__monitor" />
                <span className="desk__surface">
                  <span className="desk__keyboard" />
                </span>
                <span className="desk__chair" />
              </div>
            </div>
          ) : (
            <div
              key={room.slot_id}
              className={`opendesk ${room.busy ? 'opendesk--busy' : ''}`}
              style={{ left: `${room.deskX}%`, top: `${room.deskY}%` }}
              aria-hidden="true"
            >
              <div className={`desk ${room.busy ? 'desk--busy' : ''}`}>
                <span className="desk__label">{room.name}</span>
                {room.role && <span className="desk__role">{room.role}</span>}
                <span className="desk__monitor" />
                <span className="desk__surface">
                  <span className="desk__keyboard" />
                </span>
                <span className="desk__chair" />
              </div>
            </div>
          ),
        )}

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

        {/* The agents themselves, seated at their own desks with a bubble over
            each saying what they are doing.

            This is the half of the floor that makes the office an office. A lit
            monitor already said "this desk is BUSY"; a character sitting at it
            saying "working for alice" says *who* is doing it and for whom,
            which is the thing a stranger watching a 3-minute video has to pick
            up without narration. Drawn before the people so somebody walking up
            to a desk passes in front of its occupant. */}
        {rooms.map((room) => {
          if (!room.agent) return null
          const look = lookFor(room.agent.character, room.slot_id, world, true)
          return (
            <div
              key={`agent-${room.slot_id}`}
              className={`pawn pawn--agent pawn--seated ${room.busy ? 'pawn--busy' : ''}`}
              style={{ left: `${room.deskX}%`, top: `${room.deskY + room.seatDrop}%` }}
            >
              <span className="bubble">
                {agentStatus(room.agent, noteFor?.(room.agent), true)}
              </span>
              <span
                className="sprite"
                style={{
                  '--art': look.seat,
                  '--art-step': look.step,
                  '--sp-hair': look.hair,
                }}
                aria-hidden="true"
              />
            </div>
          )
        })}

        {placed.map(({ id, member, index, desk, waiting, left, top }) => {
          const mine = id === me
          const busy = busyUsers.has(id)
          const position = queuedBy.get(id)
          // Compact past the pitch the long form needs — see `waitSpot`.
          const compact = compactQueue && Boolean(position)
          const isWalking = walking.has(id)
          const look = lookFor(member.avatar, id, world)
          // Standing, not seated — the chair belongs to the agent. A visitor
          // keeps their legs, which is also what distinguishes them from the
          // seated character at the same desk.
          const visiting = Boolean(desk) && !isWalking
          return (
            <div
              key={id}
              className={
                `pawn ${mine ? 'pawn--mine' : ''} ${busy ? 'pawn--busy' : ''} ` +
                `${isWalking ? 'pawn--walking' : ''} ${visiting ? 'pawn--visiting' : ''} ` +
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
                  '--art': look.art,
                  '--art-step': look.step,
                  '--sp-hair': look.hair,
                }}
                aria-hidden="true"
              />
              <span className="pawn__name">
                {mine ? 'you' : id}
              </span>
              <span className="pawn__state">
                {busy
                  ? 'working'
                  : position
                    ? compact
                      ? `#${position}`
                      : `queued #${position}`
                    : 'idle'}
              </span>
            </div>
          )
        })}

        {/* The third slot: whatever drifts over the top of the room — snow,
            embers, plankton, dust in the light. Above the pawns, so it passes
            in front of people rather than behind them, and `pointer-events:
            none` so it never eats a click meant for the floor. */}
        <div className="worldlayer worldlayer--air" aria-hidden="true" />

        {/* Last, so the envelope passes in front of the rooms and whoever is
            standing in the corridor rather than sliding behind a wall. */}
        {crossing && (
          <Envelope
            key={crossing.key}
            from={{ x: crossing.from.deskX, y: crossing.from.deskY }}
            to={{ x: crossing.to.deskX, y: crossing.to.deskY }}
            label={crossing.label}
          />
        )}
      </div>
    </section>
  )
}

/* Which world the board wears.
 *
 * A radiogroup rather than a list of buttons, and the same `.modal` backdrop
 * and click-away as hiring — a world is one choice out of a set, which is
 * exactly what a radiogroup is, and reusing the dialog means keyboard and
 * screen-reader behaviour that is already right.
 *
 * Applying immediately, with no confirm step, is the whole interaction: the
 * board is right there behind the dialog, and seeing it change is how you
 * decide. A picker that needed an OK would hide the only information you are
 * choosing on.
 */
export function WorldModal({ onClose }) {
  const { world, worlds, setWorld, surprise } = useWorld()
  const cards = useRef([])
  const index = worlds.findIndex((entry) => entry.id === world.id)

  /* The radiogroup keyboard contract, which the cards did not honour before
   * Phase 27: a group of radios is ONE tab stop, and the arrows move within
   * it. Nine buttons each taking a tab stop meant nine presses to get past
   * the picker, and the arrow keys — which is what a keyboard user reaches
   * for in a radiogroup — did nothing at all.
   *
   * Selection follows focus, as it does in every native radio group, and
   * selection here applies the world. So arrowing along the row flips the
   * board from one world to the next, which is the mouse interaction's own
   * argument ("seeing it change is how you decide") with a keyboard on it.
   * The cross-fade is built to be retargeted mid-flight for exactly this. */
  const move = (to) => {
    const next = worlds[(to + worlds.length) % worlds.length]
    setWorld(next.id)
    cards.current[worlds.indexOf(next)]?.focus()
  }

  const onKeyDown = (event) => {
    const { key } = event
    if (key === 'ArrowRight' || key === 'ArrowDown') move(index + 1)
    else if (key === 'ArrowLeft' || key === 'ArrowUp') move(index - 1)
    else if (key === 'Home') move(0)
    else if (key === 'End') move(worlds.length - 1)
    else return
    // Only once we know we handled it: arrowing must not also scroll the grid.
    event.preventDefault()
  }

  return (
    <div
      className="modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="worlds-title"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
      /* Escape closes. The dialog is a costume rack — there is nothing to
       * lose by leaving it, and the world you chose is already applied. */
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose()
      }}
    >
      <div className="worlds">
        <header className="worlds__head">
          <h2 className="worlds__title" id="worlds-title">
            World
          </h2>
          <p className="worlds__blurb">
            The same floor, the same agents, the same budget — somewhere else.
            Yours only: this is stored in your browser and changes nothing
            anyone else sees.
          </p>
        </header>

        <div className="worldgrid" role="radiogroup" aria-label="World" onKeyDown={onKeyDown}>
          {worlds.map((entry, i) => (
            <button
              type="button"
              key={entry.id}
              role="radio"
              aria-checked={entry.id === world.id}
              // One tab stop for the whole group; the arrows do the rest.
              tabIndex={entry.id === world.id ? 0 : -1}
              ref={(node) => {
                cards.current[i] = node
              }}
              // Opening the rack with the current world already focused is
              // what makes the arrows usable without hunting for them first.
              autoFocus={entry.id === world.id}
              onClick={() => setWorld(entry.id)}
              className={`worldcard ${entry.id === world.id ? 'worldcard--on' : ''}`}
            >
              <span className="worldcard__name">{entry.label}</span>
              <span className="worldcard__blurb">{entry.blurb}</span>
            </button>
          ))}
        </div>

        {/* Outside the radiogroup on purpose — see `.worldcard--random`. It
            picks one of the other eight and leaves that world selected, so a
            reload comes back to where it landed rather than rolling again. */}
        <button
          type="button"
          className="worldcard worldcard--random"
          onClick={surprise}
        >
          <span className="worldcard__name">Surprise me</span>
          <span className="worldcard__blurb">
            Somewhere else — any world but the one you are in.
          </span>
        </button>

        <footer className="worlds__foot">
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            done
          </button>
        </footer>
      </div>
    </div>
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
