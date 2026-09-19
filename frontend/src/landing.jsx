/* The front door.
 *
 * Everything a judge needs in the first five seconds, at `/`, with the
 * workspace one click away at `#/workspace`. It opens no socket and reads no
 * board — the landing page costs the backend nothing, which is the point of
 * keeping `useHive` inside `Workspace` rather than at the app root.
 *
 * Two rules from the theme govern the whole page, and both come straight from
 * the top of styles.css: brand amber is a fill and never carries a word, and
 * the one place the retired graphite console is allowed back is the terminal
 * card in the architecture band.
 */

import { CanvasPanel, QuotaBar, Mark } from './components'

const REPO = 'https://github.com/arunishrajput/hiveos'
const WORKSPACE = '#/workspace'

/* --- The board preview ----------------------------------------------------
 *
 * Canned state rendered through the *real* components, so the picture on the
 * front page cannot drift from the product behind it — if the room changes,
 * this changes with it.
 *
 * It deliberately does not connect. A preview socket would write a `CONN#`
 * row, so every visitor to the landing page would appear as a phantom member
 * on the default board, inflate the count on camera during a take, and trip
 * `ws_smoke.py`'s connection-leak checks. There is no read-only observer in
 * the protocol and inventing one for a marketing page is the wrong trade.
 *
 * The numbers are chosen to show the product doing its job in one frame: both
 * slots working, someone holding a real queue position, and the meter in its
 * middle band — 56.9% is above the 50% threshold, so the quota strip renders
 * ochre rather than jade and the colour itself reports something.
 */
const PREVIEW_MEMBERS = [
  { user_id: 'alice', avatar: '🐝', x: 24, y: 58 },
  { user_id: 'bob', avatar: '🦊', x: 70, y: 58 },
  { user_id: 'charlie', avatar: '🦉', x: 50, y: 74 },
]

/* The roster, as the snapshot would deliver it. Duplicated from
 * `backend/shared/agents.py` because this page has no socket to ask — the one
 * place in the frontend that knows an agent's name without being told. If the
 * roster changes, this is the line that has to change with it; nothing else
 * in the app hardcodes a name.
 */
const PREVIEW_AGENTS = [
  { slot_id: 'coder', name: 'Ada', role: 'Engineer', status: 'BUSY', current_user: 'alice' },
  { slot_id: 'researcher', name: 'Iris', role: 'Researcher', status: 'BUSY', current_user: 'bob' },
]

const PREVIEW_QUEUE = [{ user_id: 'charlie', queue_position: 1 }]
const PREVIEW_BUSY = new Set(['alice', 'bob'])

function BoardPreview() {
  return (
    <figure className="lp-preview">
      <div className="lp-preview__frame">
        <div className="lp-preview__chrome">
          <Mark className="lp-preview__mark" />
          <span className="lp-preview__title">HiveOS</span>
          <span className="lp-preview__team">alpha</span>
        </div>

        <QuotaBar
          tokensUsed={2847}
          tokenBudget={5000}
          pctUsed={56.9}
          exhausted={false}
          estimated={false}
        />

        {/* No `onMove`: nothing here is connected to a socket, so the floor
            drops its click target and its tab stop rather than offering an
            interaction that silently does nothing. */}
        <CanvasPanel
          members={PREVIEW_MEMBERS}
          me={null}
          busyUsers={PREVIEW_BUSY}
          agents={PREVIEW_AGENTS}
          queue={PREVIEW_QUEUE}
        />
      </div>

      <figcaption className="lp-preview__caption">
        Ada and Iris at their desks, both working, with the people who asked
        standing beside them — one more waiting, and 2,847 of 5,000 tokens
        spent. Every member sees this same frame at the same instant.
      </figcaption>
    </figure>
  )
}

/* --- Evidence -------------------------------------------------------------
 *
 * The figures are the ones in SUBMISSION.md, with their sources attached.
 * A statistic without its source on a page that argues for accountability
 * would be a poor look.
 */
const EVIDENCE = [
  {
    figure: '4 months',
    claim:
      'Uber burned its entire 2026 AI coding budget in four months. One '
      + 'internal demo cost $1,200 in two hours.',
    source: 'Fortune / The Information, May 2026',
  },
  {
    figure: '79%',
    claim: 'of enterprises had AI cost overruns in the past twelve months.',
    source: 'DoiT / Sapio Research, Feb 2026',
  },
  {
    figure: '36%',
    claim: 'of organisations have any token or usage controls at all.',
    source: 'PointFive Research, Jul 2026',
  },
]

const STEPS = [
  {
    n: '01',
    title: 'Staff the floor',
    body:
      'A workspace opens with Ada, who takes engineering work, and Iris, who '
      + 'researches. Hire more: a name, a character, a briefing, and a desk '
      + 'appears on every teammate’s floor without anyone reloading. '
      + 'Hiring is free — running an agent is what spends the budget.',
  },
  {
    n: '02',
    title: 'Ask one, or take a number',
    body:
      'Claiming a desk is a single atomic conditional write in DynamoDB, so '
      + 'two people clicking in the same moment cannot both win it. Every desk '
      + 'busy? You stand in the waiting area with a real queue position. '
      + 'Dispatch is least-recently-served first, not arrival order — one '
      + 'heavy user cannot camp at the front of the line.',
  },
  {
    n: '03',
    title: 'Watch the budget move',
    body:
      "Each task's cost is the model provider's own token count, added with an "
      + 'atomic counter and pushed to every open socket. Three screens, one '
      + 'figure, no divergence.',
  },
  {
    n: '04',
    title: 'Hit the ceiling and stop',
    body:
      'At 100% the server refuses to invoke the model at all. A refused task '
      + 'records zero tokens — the ceiling is a control, not a gauge.',
  },
]

const SERVICES = [
  ['API Gateway', 'WebSocket'],
  ['Lambda', 'Router + Agent Runner'],
  ['DynamoDB', 'single table'],
  ['SQS', '+ DLQ'],
  ['Amplify', 'hosting'],
  ['SSM', 'SecureString'],
  ['CloudFormation', 'SAM'],
  ['Budgets', 'spend backstop'],
]

/* Column-aligned by hand, and worth checking if any label here is ever edited:
 * the `│` drops from the centre of *Router Lambda* to `SQS`, and the `▲` rises
 * from the centre of *Runner* to *DynamoDB*. Change a word and the arrows point
 * at whatever now happens to sit in that column, which looks like a diagram and
 * says something false. */
const PIPELINE = `Browser ──wss──► API Gateway WebSocket ──► Router Lambda ──► DynamoDB
                                                 │              ▲
                                                 ▼              │
                                                SQS ──► Agent Runner Lambda`

/* --- The page ------------------------------------------------------------- */

export default function Landing() {
  return (
    <div className="lp">
      <header className="lp-nav">
        <a className="lp-nav__brand" href="#/">
          <Mark className="lp-nav__mark" />
          <span className="lp-nav__name">HiveOS</span>
        </a>
        <span className="lp-nav__spacer" />
        <a
          className="lp-nav__link"
          href={REPO}
          target="_blank"
          rel="noreferrer"
        >
          Source
        </a>
        <a className="btn" href={WORKSPACE}>
          Enter the workspace
        </a>
      </header>

      <main>
        {/* Hero — cream */}
        <section className="lp-band lp-band--cream">
          <div className="lp-wrap lp-hero">
            <div className="lp-hero__copy">
              <p className="lp-eyebrow">
                First Commit · WeMakeDevs × AWS · Ship It
              </p>
              <h1 className="lp-hero__title">
                An office of AI agents your whole team can walk into.
              </h1>
              <p className="lp-hero__sub">
                Hire an agent, give it a name and a briefing, and watch it take
                a desk on a floor everyone can see. Your teammates watch it
                work in real time — and every desk on that floor draws from one
                shared token budget, behind a ceiling the server actually
                enforces.
              </p>

              <div className="lp-hero__actions">
                <a className="btn" href={WORKSPACE}>
                  Enter the workspace
                </a>
                <a
                  className="btn btn--ghost"
                  href={REPO}
                  target="_blank"
                  rel="noreferrer"
                >
                  Read the source
                </a>
              </div>

              <p className="lp-hero__note">
                No sign-in, no setup. Pick a name and you are on the floor.
              </p>
            </div>

            <BoardPreview />
          </div>
        </section>

        {/* Evidence — sand */}
        <section className="lp-band lp-band--sand" aria-labelledby="why">
          <div className="lp-wrap">
            <p className="lp-eyebrow" id="why">
              Why this exists
            </p>
            <h2 className="lp-h2">
              Teams are handing AI agents a shared budget and no way to govern
              it.
            </h2>

            <ul className="lp-stats">
              {EVIDENCE.map((item) => (
                <li className="lp-stat" key={item.figure}>
                  <p className="lp-stat__figure">{item.figure}</p>
                  <p className="lp-stat__claim">{item.claim}</p>
                  <p className="lp-stat__source">{item.source}</p>
                </li>
              ))}
            </ul>

            <p className="lp-lede">
              The gap is not dashboards — those report yesterday. The gap is
              real-time, shared, <em>enforced</em> governance: who is using the
              agents right now, what it is costing, whose turn is next, and what
              happens when the budget runs out. Operating systems solved exactly
              this for CPU fifty years ago.
            </p>
          </div>
        </section>

        {/* How it works — cream */}
        <section className="lp-band lp-band--cream" aria-labelledby="how">
          <div className="lp-wrap">
            <p className="lp-eyebrow" id="how">
              How it works
            </p>
            <h2 className="lp-h2">Scheduling, quotas, fair queueing.</h2>

            <ol className="lp-steps">
              {STEPS.map((step) => (
                <li className="lp-step" key={step.n}>
                  <span className="lp-step__n">{step.n}</span>
                  <h3 className="lp-step__title">{step.title}</h3>
                  <p className="lp-step__body">{step.body}</p>
                </li>
              ))}
            </ol>

            <ul className="lp-measures">
              <li>
                <span className="lp-measures__n">282 ms</span>
                for a claim to reach a second browser
              </li>
              <li>
                <span className="lp-measures__n">187 ms</span>
                for auto-dispatch to show after a slot frees
              </li>
              <li>
                <span className="lp-measures__n">79/79</span>
                end-to-end checks against deployed AWS
              </li>
            </ul>
            <p className="lp-measures__note">
              Click-to-paint across two separate browsers, measured against the
              deployed system — not a server-side round trip.
            </p>
          </div>
        </section>

        {/* Architecture — sand, and the one ink-dark card on the page */}
        <section className="lp-band lp-band--sand" aria-labelledby="aws">
          <div className="lp-wrap">
            <p className="lp-eyebrow" id="aws">
              Built on AWS
            </p>
            <h2 className="lp-h2">
              Serverless end to end, all of it in one template.
            </h2>

            <div className="lp-terminal">
              <div className="lp-terminal__head">
                <span className="lp-terminal__dot" />
                <span className="lp-terminal__dot" />
                <span className="lp-terminal__dot" />
                <span className="lp-terminal__path">hiveos · us-east-1</span>
              </div>
              {/* Scrolls inside itself on a narrow screen rather than pushing
                  the page sideways — a diagram made of box-drawing characters
                  cannot reflow. */}
              <pre className="lp-terminal__body">{PIPELINE}</pre>
            </div>

            <ul className="lp-services">
              {SERVICES.map(([name, role]) => (
                <li className="lp-service" key={name}>
                  <span className="lp-service__name">{name}</span>
                  <span className="lp-service__role">{role}</span>
                </li>
              ))}
            </ul>

            <div className="lp-honest">
              <p className="lp-honest__label">One honest caveat</p>
              <p className="lp-honest__body">
                Model inference calls out to Groq. Amazon Bedrock is blocked
                account-wide on this AWS account — 42 of 43 per-day token quotas
                sit at zero and are marked non-adjustable, including first-party
                Amazon Nova, which needs no Marketplace subscription. That is an
                AWS Support matter, not a config fix. Everything else is AWS;
                one outbound HTTPS call is the whole difference.
              </p>
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-foot">
        <div className="lp-wrap lp-foot__inner">
          <div className="lp-foot__brand">
            <Mark className="lp-foot__mark" />
            <span className="lp-foot__name">HiveOS</span>
            <span className="lp-foot__tag">
              Queue management for AI agents, visible to everyone in real time.
            </span>
          </div>

          <nav className="lp-foot__links" aria-label="Footer">
            <a href={WORKSPACE}>Enter the workspace</a>
            <a href={REPO} target="_blank" rel="noreferrer">
              GitHub
            </a>
          </nav>

          <p className="lp-foot__credit">
            Built by Arunish Rajput for First Commit (WeMakeDevs × AWS), Ship It
            track.
          </p>
        </div>
      </footer>
    </div>
  )
}
