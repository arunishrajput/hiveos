import { useCallback, useEffect, useMemo, useState } from 'react'

import { useHive } from './useHive'
import Landing from './landing'
import AddAgentModal from './addagent'
import { AVATARS } from './sprites'
import {
  AgentFace,
  AppBar,
  CanvasPanel,
  LedgerPane,
  Mark,
  QuotaBar,
  MemberBar,
  RosterStrip,
  SpendPanel,
  StreamPane,
  ToastStack,
  agentStatus,
  formatEta,
} from './components'

const STORAGE_KEY = 'hiveos.identity'

/* Shown in the app bar. Hand-set rather than read from package.json: the
 * frontend is built by Amplify from a checkout, and a version that quietly
 * tracked a dependency file would drift from what the recording says. */
const VERSION = 'v1.0'

/* Mirrors `agents.MAX_AGENTS` server-side. Used only to disable the hire
 * button and say why — the refusal itself is the server's, and an error frame
 * is what a client that ignored this would get. */
const MAX_AGENTS = 4

// The Router truncates both of these server-side; matching the limits here
// keeps what you typed and what arrives the same thing.
const MAX_USER_ID = 40
// Mirrors state.TEAM_PATTERN server-side; a name outside it falls back to the
// default team rather than being rejected, so this is a hint, not a gate.
const MAX_TEAM = 31
const DEFAULT_TEAM = 'alpha'
const MAX_PROMPT = 2000
const MAX_TEXT = 500

/* One admin token per workspace, per browser, kept for as long as the browser
 * keeps anything. Generated with the platform CSPRNG rather than Math.random —
 * this is the only thing standing between a stranger and deleting a workspace.
 */
function adminTokenFor(teamId) {
  const key = `hiveos.admin.${teamId}`
  try {
    const existing = window.localStorage.getItem(key)
    if (existing) return existing
    const minted = crypto.randomUUID()
    window.localStorage.setItem(key, minted)
    return minted
  } catch {
    // A blocked localStorage means no admin rights rather than no entry.
    return null
  }
}

function loadIdentity() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    // `team` was added after the first release; anyone with a stored
    // identity from before it lands in the default workspace.
    return parsed?.userId ? { team: DEFAULT_TEAM, ...parsed } : null
  } catch {
    return null
  }
}

function saveIdentity(identity) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(identity))
  } catch {
    // A blocked localStorage is not worth failing entry over.
  }
}

/* --- Entry gate ----------------------------------------------------------- */

function Gate({ onEnter }) {
  const [name, setName] = useState('')
  const [team, setTeam] = useState(DEFAULT_TEAM)
  const [passphrase, setPassphrase] = useState('')
  const [avatar, setAvatar] = useState(AVATARS[0])

  const submit = (event) => {
    event.preventDefault()
    const userId = name.trim().slice(0, MAX_USER_ID)
    if (!userId) return
    // Lowercased to match the server: `Alpha` and `alpha` must be one room,
    // not two that look identical and cannot see each other.
    const teamId = team.trim().toLowerCase().slice(0, MAX_TEAM) || DEFAULT_TEAM
    // Minted here, kept here. If this workspace is new, the server stores a
    // hash of it and this browser becomes its administrator; if it already
    // exists, the token simply will not match and nothing is granted. Sharing
    // it with a teammate is what an invite is — there are no accounts to
    // invite anyone *to*.
    const adminToken = adminTokenFor(teamId)
    onEnter({ userId, avatar, team: teamId, passphrase, adminToken })
  }

  return (
    <main className="gate">
      <div className="gate__card">
        <div className="gate__head">
          <Mark className="gate__mark" />
          <h1 className="gate__title">HiveOS</h1>
          <p className="gate__blurb">
            A workspace is a floor of AI agents sharing one token budget. Pick
            a name and a workspace — everything you do is visible to everyone
            else on that floor, live.
          </p>
        </div>

        <form className="gate__form" onSubmit={submit}>
          <div>
            <label className="gate__legend" htmlFor="name">
              Your name
            </label>
            <input
              id="name"
              className="field"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={MAX_USER_ID}
              placeholder="alice"
              autoComplete="off"
              autoFocus
            />
          </div>

          <div>
            <label className="gate__legend" htmlFor="team">
              Workspace
            </label>
            <input
              id="team"
              className="field"
              value={team}
              onChange={(event) => setTeam(event.target.value)}
              maxLength={MAX_TEAM}
              placeholder={DEFAULT_TEAM}
              autoComplete="off"
              aria-describedby="team-hint"
            />
            <p className="gate__hint" id="team-hint">
              Separate workspaces have their own budget, agents, queue and
              memory — they cannot see each other.
            </p>
          </div>

          <div>
            <label className="gate__legend" htmlFor="passphrase">
              Passphrase <span className="gate__optional">optional</span>
            </label>
            <input
              id="passphrase"
              className="field"
              type="password"
              value={passphrase}
              onChange={(event) => setPassphrase(event.target.value)}
              maxLength={200}
              autoComplete="off"
              aria-describedby="pass-hint"
            />
            <p className="gate__hint" id="pass-hint">
              Set one when you create a workspace and it stays protected —
              everyone joining it afterwards needs the same passphrase. Leave
              blank for an open workspace.
            </p>
          </div>

          <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
            <legend className="gate__legend">Your marker</legend>
            <div className="chips">
              {AVATARS.map((option) => (
                <button
                  type="button"
                  key={option}
                  className={`chip ${option === avatar ? 'chip--on' : ''}`}
                  aria-pressed={option === avatar}
                  aria-label={`Marker ${option}`}
                  onClick={() => setAvatar(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>

          <button className="btn" type="submit" disabled={!name.trim()}>
            Join workspace
          </button>
        </form>
      </div>
    </main>
  )
}

/* --- Request panel -------------------------------------------------------- */

function hintFor({ connection, budgetExhausted, holding, queued, chosen }) {
  if (connection === 'refused') {
    return {
      text: 'This workspace is protected and the passphrase did not match. '
        + 'Reload to try again.',
      alarm: true,
    }
  }
  if (connection !== 'open') {
    return { text: 'Reconnecting. The board catches up on its own.', alarm: false }
  }
  if (budgetExhausted) {
    return {
      text: 'Team quota reached. HiveOS will not invoke the model.',
      alarm: true,
    }
  }
  if (holding) {
    return {
      text: `${holding.name || holding.slot_id} is running your task.`,
      alarm: false,
    }
  }
  if (queued) {
    return {
      text: `Position ${queued.queue_position} in the run queue · ${formatEta(
        queued.estimated_wait_seconds,
      )} away.`,
      alarm: false,
    }
  }
  // With an agent chosen, the useful thing to say is what that agent is for —
  // and, if they are busy, that choosing them is a preference rather than a
  // booking. Nobody waits behind an idle desk (CONTRACT.md).
  if (chosen) {
    return {
      text:
        chosen.status === 'BUSY'
          ? `${chosen.name || chosen.slot_id} is busy — the first free desk takes this.`
          : `${chosen.name || chosen.slot_id} — ${chosen.tagline || chosen.role}`,
      alarm: false,
    }
  }
  return {
    text: 'Whichever desk frees first takes it. If both are busy, your task joins the queue.',
    alarm: false,
  }
}

/* --- Inspector ------------------------------------------------------------
 *
 * One agent at a time, in depth: who they are, what they are doing, the stream
 * of what they have done, and the box that gives them work.
 *
 * The reference this is modelled on puts a live PTY here, attached to a CLI
 * running on the developer's own machine. HiveOS has no terminal to attach to
 * and will not pretend it does — so the four tabs are bound to the four things
 * this board genuinely knows: this agent's stream, this agent's ledger, the
 * room's chat, and the facts the floor has saved. Every tab has real data on a
 * cold load, because all four ride on `state_snapshot`.
 */

const TABS = [
  { id: 'stream', label: 'Stream' },
  { id: 'ledger', label: 'Ledger' },
  { id: 'msgs', label: 'Msgs' },
  { id: 'memory', label: 'Memory' },
  { id: 'spend', label: 'Spend' },
]

function Inspector({ hive, agent, me, note }) {
  const [tab, setTab] = useState('stream')
  const [prompt, setPrompt] = useState('')

  const { board, connection, budgetExhausted, holding, queued, working, activity } = hive

  if (!agent) {
    return (
      <aside className="inspect">
        <p className="empty">This floor has no agents yet.</p>
      </aside>
    )
  }

  const label = agent.name || agent.slot_id
  const busy = agent.status === 'BUSY'
  const mine = busy && agent.current_user === me
  const blocked = working || budgetExhausted || connection !== 'open'
  const hint = hintFor({ connection, budgetExhausted, holding, queued, chosen: agent })

  /* May this connection free this desk? The server decides it the same way —
   * the holder, or an administrator when nobody else can (see the release
   * guard merged in PR #1). The button only mirrors that rule; it does not
   * enforce it, and un-disabling it in devtools buys an error frame. */
  const canHalt = busy && (mine || board.is_admin)

  // A handoff belongs to both desks, hence the second match: the crossing
  // shows up in the sender's terminal and the receiver's.
  const stream = activity.filter(
    (entry) => entry.agent === agent.slot_id || entry.agentTo === agent.slot_id,
  )
  const ledger = board.history.filter((row) => row.agent_type === agent.slot_id)
  const chat = activity.filter((entry) => entry.kind === 'chat')

  const submit = (event) => {
    event.preventDefault()
    const text = prompt.trim().slice(0, MAX_PROMPT)
    if (!text || blocked) return
    // Only clear the box if the frame actually went out — otherwise the user
    // loses what they typed to a socket that was not open.
    if (hive.requestAgent(text, agent.slot_id)) setPrompt('')
  }

  return (
    <aside className="inspect" aria-label={`${label} — agent inspector`}>
      <header className="inspect__head">
        <AgentFace agent={agent} className="inspect__face" />
        <span className="inspect__id">
          <span className="inspect__name">{label}</span>
          <span className="inspect__role">{agent.role || agent.slot_id}</span>
        </span>
        <span className={`chip ${busy ? 'chip--busy' : 'chip--idle'}`}>
          <span className="chip__dot" aria-hidden="true" />
          {busy ? 'working' : 'idle'}
        </span>
      </header>

      <div className="inspect__control">
        <span className="inspect__ctrl">Control</span>
        <button
          type="button"
          className="btn btn--danger btn--sm"
          disabled={!canHalt}
          onClick={() => hive.releaseAgent(agent.slot_id)}
          title={
            !busy
              ? 'This desk is already free'
              : canHalt
                ? 'Free this desk now and dispatch the next waiting task'
                : `${agent.current_user} holds this desk`
          }
        >
          halt
        </button>

        {/* Dismissing is refused server-side while a desk is working, and for
            the last desk on a floor. Disabled here for the same two cases, so
            the button says what the server would rather than offering an
            action that comes back as an error frame. */}
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          disabled={busy || board.agents.length <= 1}
          onClick={() => hive.dismissAgent(agent.slot_id)}
          title={
            busy
              ? 'Halt this desk before dismissing it'
              : board.agents.length <= 1
                ? 'A floor needs at least one agent'
                : `Take ${label} off the floor`
          }
        >
          dismiss
        </button>
        {/* Only when there is something to say. The chip in the header already
            reports idle, and repeating it here is the panel talking to itself. */}
        {(busy || note) && (
          <span className="inspect__doing">{agentStatus(agent, note)}</span>
        )}
      </div>

      <div className="tabs" role="tablist" aria-label="Inspector view">
        {TABS.map((entry) => (
          <button
            type="button"
            key={entry.id}
            role="tab"
            aria-selected={tab === entry.id}
            className={`tab ${tab === entry.id ? 'tab--on' : ''}`}
            onClick={() => setTab(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </div>

      <div className="inspect__pane">
        {tab === 'stream' && (
          <StreamPane
            entries={stream}
            label={`live · ${agent.slot_id}@${board.team}`}
            empty={`Nothing yet. Give ${label} a task below.`}
          />
        )}

        {tab === 'ledger' && <LedgerPane rows={ledger} />}

        {tab === 'msgs' && (
          <StreamPane
            entries={chat}
            label={`team chat · ${board.team}`}
            empty="No messages yet."
          />
        )}

        {tab === 'memory' && (
          board.memory.length === 0 ? (
            <p className="stream__empty">
              Nothing saved yet. Ask an agent to remember something for the team.
            </p>
          ) : (
            <div className="memory">
              {board.memory.map((fact) => (
                <span className="fact" key={fact.key}>
                  <span className="fact__key">{fact.key}</span>
                  <span className="fact__val"> — {fact.val}</span>
                </span>
              ))}
            </div>
          )
        )}

        {/* Board-level, not agent-level, and deliberately so: the meter says
            the floor has spent 2,847 tokens and this says who spent them.
            Everyone on the board can open it — a governance panel only the
            owner could read would be the opposite of the product. */}
        {tab === 'spend' && (
          board.spend.length === 0 ? (
            <p className="stream__empty">Nothing spent yet on this floor.</p>
          ) : (
            <SpendPanel
              spend={board.spend}
              members={board.members}
              tokenBudget={board.token_budget}
            />
          )
        )}
      </div>

      <form className="compose" onSubmit={submit}>
        <span className="compose__label">Queue</span>

        <textarea
          className="field"
          rows={2}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          maxLength={MAX_PROMPT}
          placeholder={`Message ${label}`}
          aria-label={`Task for ${label}`}
        />

        <div className="compose__actions">
          <p className={`compose__hint ${hint.alarm ? 'compose__hint--alarm' : ''}`}>
            {hint.text}
          </p>
          <button className="btn" type="submit" disabled={blocked || !prompt.trim()}>
            send →
          </button>
        </div>
      </form>
    </aside>
  )
}

/* --- Team chat ------------------------------------------------------------ */

/* Plain human chat, not the agent. `send_message` has existed since Phase 1
 * and was broadcast to every client, but no UI ever sent one — the activity
 * log could render a `chat_message` that nothing could produce. */
function ChatComposer({ hive }) {
  const [text, setText] = useState('')
  const disabled = hive.connection !== 'open'

  const submit = (event) => {
    event.preventDefault()
    const message = text.trim().slice(0, MAX_TEXT)
    if (!message || disabled) return
    if (hive.sendMessage(message)) setText('')
  }

  return (
    <form className="chat" onSubmit={submit}>
      <input
        className="field"
        value={text}
        onChange={(event) => setText(event.target.value)}
        maxLength={MAX_TEXT}
        placeholder="Say something to the team"
        aria-label="Message the team"
        autoComplete="off"
      />
      <button className="btn btn--ghost" type="submit" disabled={disabled || !text.trim()}>
        Send
      </button>
    </form>
  )
}


/* --- Administration ------------------------------------------------------- */

/* Shown only to a connection the *server* admitted as an administrator.
 *
 * Hiding it is convenience, not the control: every action below is refused
 * server-side against the CONN# row unless this connection presented the
 * workspace's admin token at the handshake. A user who un-hid this panel in
 * devtools would get three error frames.
 */
function AdminPanel({ hive }) {
  const [budget, setBudget] = useState('')
  const [passphrase, setPassphrase] = useState('')
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  if (!hive.board.is_admin) return null

  const applyBudget = (event) => {
    event.preventDefault()
    const value = Number(budget)
    if (!Number.isFinite(value) || value < 0) return
    if (hive.setBudget(Math.round(value))) setBudget('')
  }

  return (
    <section className="panel panel--admin" aria-labelledby="admin-label">
      <div className="panel__head">
        <span className="panel__label" id="admin-label">
          Workspace admin
        </span>
        <span className="panel__aside">you own this</span>
      </div>

      <form className="admin__row" onSubmit={applyBudget}>
        <input
          className="field"
          value={budget}
          onChange={(event) => setBudget(event.target.value)}
          placeholder={`${hive.board.token_budget} tokens`}
          inputMode="numeric"
          aria-label="New token budget"
        />
        <button className="btn btn--ghost" type="submit" disabled={!budget.trim()}>
          Set budget
        </button>
      </form>

      <form
        className="admin__row"
        onSubmit={(event) => {
          event.preventDefault()
          if (hive.rotatePassphrase(passphrase)) setPassphrase('')
        }}
      >
        <input
          className="field"
          type="password"
          value={passphrase}
          onChange={(event) => setPassphrase(event.target.value)}
          placeholder="new passphrase"
          autoComplete="off"
          aria-label="New workspace passphrase"
        />
        <button className="btn btn--ghost" type="submit">
          {passphrase ? 'Set' : 'Remove'}
        </button>
      </form>

      <p className="admin__note">
        Rotating locks out the next person to join. Everyone already here stays.
      </p>

      {confirmingDelete ? (
        <div className="admin__row">
          <button
            className="btn btn--danger"
            type="button"
            onClick={() => hive.deleteWorkspace()}
          >
            Delete everything
          </button>
          <button
            className="btn btn--ghost"
            type="button"
            onClick={() => setConfirmingDelete(false)}
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          className="btn btn--ghost"
          type="button"
          onClick={() => setConfirmingDelete(true)}
        >
          Delete workspace…
        </button>
      )}
    </section>
  )
}

/* --- Workspace ------------------------------------------------------------ */

function Deleted() {
  return (
    <main className="gate">
      <div className="gate__card">
        <div className="gate__head">
          <Mark className="gate__mark" />
          <h1 className="gate__title">Workspace deleted</h1>
          <p className="gate__blurb">
            Its budget, slots, queue, memory and task history are gone. Reload
            to start a new workspace with the same name.
          </p>
        </div>
      </div>
    </main>
  )
}

/* How long a finished task keeps its afterglow over the desk that ran it. */
const NOTE_MS = 6000

/* Re-render once the newest note goes stale.
 *
 * Without this, `done · 549 tokens` sits over a desk for the rest of the
 * session — the board claiming something just happened when it happened four
 * minutes ago, which is the one failure this product cannot afford. One
 * timeout, armed only while a note is actually fresh, rather than an interval
 * running for the whole demo.
 */
function useNoteExpiry(activity) {
  const [, tick] = useState(0)
  const newest = activity[0]?.ts?.getTime() ?? 0

  useEffect(() => {
    if (!newest) return undefined
    const left = NOTE_MS - (Date.now() - newest)
    if (left <= 0) return undefined
    const timer = setTimeout(() => tick((n) => n + 1), left)
    return () => clearTimeout(timer)
  }, [newest])
}

function Workspace({ identity }) {
  const hive = useHive(identity)
  const { board } = hive

  /* Which desk the inspector is bound to. Held as an id rather than an object
   * so a re-synced snapshot — which replaces every agent object — does not
   * leave the panel pointing at a stale copy. */
  const [selected, setSelected] = useState(null)
  const [showAdmin, setShowAdmin] = useState(false)
  const [hiring, setHiring] = useState(false)

  useNoteExpiry(hive.activity)

  // Who is mid-task, so the floor can mark them working. Derived from the slot
  // table rather than tracked separately — the slots are the authority on who
  // holds an agent, and a second source would be one more thing to drift.
  const busyUsers = useMemo(
    () =>
      new Set(
        board.agents
          .filter((a) => a.status === 'BUSY' && a.current_user)
          .map((a) => a.current_user),
      ),
    [board.agents],
  )

  /* The afterglow line for one desk: what it just finished, for a few seconds.
   * `agentStatus` gives live BUSY state precedence over this, so a fresh note
   * can never sit over a desk that has already started something else. */
  const noteFor = useCallback(
    (agent) => {
      const entry = hive.activity.find((item) => item.agent === agent.slot_id)
      if (!entry || Date.now() - entry.ts.getTime() > NOTE_MS) return null
      if (entry.kind === 'response') {
        return entry.cost
          ? `done · ${entry.estimated ? '~' : ''}${entry.cost} tokens`
          : 'done'
      }
      if (entry.kind === 'handoff') return 'handed it on'
      return null
    },
    [hive.activity],
  )

  /* Falling back to the first desk rather than to nothing, so the inspector is
   * never blank: an agent dismissed while you were looking at it, or a cold
   * load before any click, both land on a real desk. */
  const agent =
    board.agents.find((item) => item.slot_id === selected) ?? board.agents[0] ?? null

  // Terminal state: there is no board left to draw and nothing to reconnect
  // to. Checked *after* the hooks above, never before — an early return ahead
  // of a `useMemo` changes the hook count between renders and React throws on
  // the very frame this is meant to handle gracefully.
  if (hive.deleted) return <Deleted />

  if (hive.configError) {
    return (
      <main className="gate">
        <div className="gate__card">
          <div className="gate__head">
            <h1 className="gate__title">Not configured</h1>
            <p className="gate__blurb">
              {hive.configError} Rebuild the frontend with the WebSocket URL
              from the stack output — see DEPLOYMENT.md.
            </p>
          </div>
        </div>
      </main>
    )
  }

  return (
    <div className="app">
      <AppBar
        team={board.team}
        members={board.members}
        agents={board.agents}
        connection={hive.connection}
        version={VERSION}
        onSettings={board.is_admin ? () => setShowAdmin((open) => !open) : null}
      />

      {/* The floor, and the two readouts that belong to the room rather than
          to any one desk: the quota above it and who is present below it. */}
      <main className="app__floor">
        <QuotaBar
          tokensUsed={board.tokens_used}
          tokenBudget={board.token_budget}
          pctUsed={board.pct_used}
          exhausted={hive.budgetExhausted}
          estimated={hive.usageEstimated}
        />

        <CanvasPanel
          members={board.members}
          me={identity.userId}
          busyUsers={busyUsers}
          agents={board.agents}
          queue={board.queue}
          onMove={hive.moveAvatar}
          handoff={hive.handoff}
          noteFor={noteFor}
        />

        <div className="app__foot">
          <span className="memchip">
            <span aria-hidden="true">🧠</span> memory ·{' '}
            {board.memory.length} {board.memory.length === 1 ? 'fact' : 'facts'}
          </span>

          <MemberBar
            members={board.members}
            me={identity.userId}
            busyUsers={busyUsers}
            queue={board.queue}
          />

          <ChatComposer hive={hive} />
        </div>
      </main>

      <Inspector
        hive={hive}
        agent={agent}
        me={identity.userId}
        note={agent ? noteFor(agent) : null}
      />

      <RosterStrip
        agents={board.agents}
        selected={agent?.slot_id ?? null}
        onSelect={setSelected}
        noteFor={noteFor}
        onAdd={() => setHiring(true)}
      />

      {hiring && (
        <AddAgentModal
          full={board.agents.length >= MAX_AGENTS}
          onSpawn={hive.spawnAgent}
          onClose={() => setHiring(false)}
        />
      )}

      {showAdmin && (
        <div className="drawer" role="dialog" aria-label="Workspace settings">
          <div className="drawer__panel">
            <AdminPanel hive={hive} />
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => setShowAdmin(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}

      <ToastStack toasts={hive.toasts} />
    </div>
  )
}

/* --- Routing --------------------------------------------------------------
 *
 * Two routes, one hash, no router library — the same reasoning that kept
 * Tailwind and a state library out of this frontend.
 *
 * The hash specifically, rather than a real path. Amplify serves this SPA with
 * a `404-200` rewrite, so a deep link like `/workspace` returns the right body
 * under an HTTP **404** (see PROGRESS.md — harmless, but real). A hash never
 * leaves `/`, so the workspace link a judge or a teammate is handed is a clean
 * 200 and is still bookmarkable and shareable.
 *
 * Anything that is not the workspace is the front door, including a stale or
 * mistyped hash — a landing page is the right thing to show someone who is
 * lost, and it is one click from where they meant to go.
 */
const WORKSPACE_ROUTE = '#/workspace'

function useIsWorkspace() {
  const read = () => window.location.hash === WORKSPACE_ROUTE
  const [isWorkspace, setIsWorkspace] = useState(read)

  useEffect(() => {
    const sync = () => setIsWorkspace(read())
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  // A hash link leaves the scroll position where it was, so arriving at the
  // workspace from halfway down the landing page would open the board
  // mid-scroll. Browsers restore scroll on back too, hence every change and
  // not just the entry.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [isWorkspace])

  return isWorkspace
}

export default function App() {
  const [identity, setIdentity] = useState(loadIdentity)
  const isWorkspace = useIsWorkspace()

  const enter = useCallback((next) => {
    saveIdentity(next)
    setIdentity(next)
  }, [])

  // `useHive` lives inside `Workspace`, so the landing route opens no socket
  // and writes no `CONN#` row. Reading the front page costs the backend
  // nothing and never appears in anyone's member list.
  if (!isWorkspace) return <Landing />
  if (!identity) return <Gate onEnter={enter} />
  return <Workspace identity={identity} />
}
