/* The frame-to-terminal rules, and the handoff chain's last mile.
 *
 * The bug these exist for: an agent-to-agent handoff looked like it stopped at
 * the crossing. Ada said she had passed the task to Iris, the ADA → IRIS line
 * appeared, and then nothing — so the whole feature read as broken, and every
 * plausible backend cause (a leg never dispatched to SQS, a second leg eaten by
 * the `task_id` idempotency marker, a model that was never called) got blamed
 * for it in turn.
 *
 * None of those was it. The backend delivered: both legs ran, both billed to
 * one `task_id`, and Iris's `agent_response` reached the browser carrying the
 * real answer, the original `user_id` and `handoff_from: 'coder'`. What it did
 * not do was reach the *terminal the user was looking at*. The inspector shows
 * one desk at a time; the user had typed into Ada's, so Ada's is the one they
 * were watching, and the answer was filed under Iris's desk alone.
 *
 * The crossing itself was already dual-homed — `agent_handoff` sets `agentTo`
 * precisely so it does not vanish from one of the two terminals. The answer the
 * crossing produces was not. That asymmetry is the defect, and the tests below
 * pin both halves of it down.
 *
 * Run with `npm test` in `frontend/` (plain `node --test` — no test runner
 * dependency, which is also why `useHive.js` reads `import.meta.env?.`).
 */

import assert from 'node:assert/strict'
import { test, describe } from 'node:test'

import { activityFor, belongsToDesk } from './useHive.js'

const CODER = 'coder'
const RESEARCHER = 'researcher'
const TASK_ID = '8663c35448d5'

/** Ada's own reply: "I have passed this to Iris." An ordinary first leg. */
const HANDING_REPLY = {
  event: 'agent_response',
  user_id: 'alice',
  agent_type: CODER,
  agent_name: 'Ada',
  task_id: TASK_ID,
  handoff_from: null,
  handoff_from_name: null,
  text: 'I have handed your question to the researcher.',
  tokens_used_this_call: 320,
}

/** The crossing. Already dual-homed before this fix. */
const CROSSING = {
  event: 'agent_handoff',
  task_id: TASK_ID,
  user_id: 'alice',
  from_agent: CODER,
  from_name: 'Ada',
  to_agent: RESEARCHER,
  to_name: 'Iris',
  note: 'fact-finding, not engineering',
  queued: false,
}

/** Iris's answer — the second leg, and the one the user actually asked for.
 *  Shaped from a real frame captured off the deployed socket. */
const HANDED_OVER_ANSWER = {
  event: 'agent_response',
  user_id: 'alice',
  agent_type: RESEARCHER,
  agent_name: 'Iris',
  task_id: TASK_ID,
  handoff_from: CODER,
  handoff_from_name: 'Ada',
  text: 'AWS’s Mumbai region (ap-south-1) is the closest to the city.',
  tokens_used_this_call: 793,
}

/** An ordinary task nobody handed on. The control for every assertion below:
 *  without it, "the answer reaches both desks" could be satisfied by an entry
 *  that reaches every desk, which would put strangers' replies in your stream. */
const ORDINARY_ANSWER = {
  event: 'agent_response',
  user_id: 'bob',
  agent_type: RESEARCHER,
  agent_name: 'Iris',
  task_id: 'ffffffffffff',
  handoff_from: null,
  handoff_from_name: null,
  text: 'Here is the answer.',
  tokens_used_this_call: 210,
}

/** The inspector's stream for one desk, built exactly as `Inspector` builds it. */
const streamFor = (frames, slotId) =>
  frames.map(activityFor).filter((entry) => entry && belongsToDesk(entry, slotId))

describe('a handed-over answer reaches the desk that handed it on', () => {
  test('the second leg is filed under both desks', () => {
    const entry = activityFor(HANDED_OVER_ANSWER)
    assert.equal(entry.kind, 'response')
    // The desk that ran it...
    assert.equal(entry.agent, RESEARCHER)
    // ...and the desk that passed it on, which is the one the user typed into.
    assert.equal(entry.agentTo, CODER)
  })

  test('THE REGRESSION: the answer lands in the terminal the user was watching', () => {
    // The user prompted Ada, so Ada's inspector is what is on screen. Before
    // the fix this stream ended at the crossing and the question went visibly
    // unanswered.
    const adasTerminal = streamFor([HANDING_REPLY, CROSSING, HANDED_OVER_ANSWER], CODER)

    assert.deepEqual(
      adasTerminal.map((entry) => entry.kind),
      ['response', 'handoff', 'response'],
    )
    const last = adasTerminal.at(-1)
    assert.equal(last.text, HANDED_OVER_ANSWER.text)
    // And it says whose answer it is, so a reply from a desk the user never
    // chose is explained rather than merely appearing.
    assert.match(last.who, /^Iris → alice · handed over by Ada$/)
  })

  test('it still lands in the receiving desk’s own terminal', () => {
    const irisTerminal = streamFor([HANDING_REPLY, CROSSING, HANDED_OVER_ANSWER], RESEARCHER)
    assert.deepEqual(
      irisTerminal.map((entry) => entry.kind),
      ['handoff', 'response'],
    )
    assert.equal(irisTerminal.at(-1).text, HANDED_OVER_ANSWER.text)
  })

  test('one desk, one copy — the answer is not duplicated in either stream', () => {
    for (const desk of [CODER, RESEARCHER]) {
      const responses = streamFor([HANDED_OVER_ANSWER], desk)
      assert.equal(responses.length, 1)
    }
  })
})

describe('an ordinary reply still belongs to exactly one desk', () => {
  test('no handoff means no second desk', () => {
    assert.equal(activityFor(ORDINARY_ANSWER).agentTo, null)
    assert.equal(activityFor(HANDING_REPLY).agentTo, null)
  })

  test('it does not leak into another desk’s terminal', () => {
    assert.equal(streamFor([ORDINARY_ANSWER], CODER).length, 0)
    assert.equal(streamFor([ORDINARY_ANSWER], RESEARCHER).length, 1)
  })
})

describe('the crossing itself is unchanged', () => {
  test('a handoff still shows in both terminals', () => {
    const entry = activityFor(CROSSING)
    assert.equal(entry.kind, 'handoff')
    assert.equal(entry.agent, CODER)
    assert.equal(entry.agentTo, RESEARCHER)
    assert.ok(belongsToDesk(entry, CODER))
    assert.ok(belongsToDesk(entry, RESEARCHER))
  })

  test('a queued handoff says it is waiting rather than started', () => {
    const queued = activityFor({ ...CROSSING, queued: true })
    assert.match(queued.text, /Waiting for that desk/)
    assert.match(activityFor(CROSSING).text, /Picked up straight away/)
  })
})

describe('belongsToDesk', () => {
  test('matches on either desk and nothing else', () => {
    const entry = { agent: CODER, agentTo: RESEARCHER }
    assert.ok(belongsToDesk(entry, CODER))
    assert.ok(belongsToDesk(entry, RESEARCHER))
    assert.equal(belongsToDesk(entry, 'jim-a3f2'), false)
  })

  test('a null desk never matches a desk-less entry', () => {
    // Chat and memory entries carry no `agent` at all; a loose `==` or a
    // default of `null` on both sides would put every one of them in the
    // inspector of a desk whose id failed to resolve.
    assert.equal(belongsToDesk({ agent: null, agentTo: null }, null), true)
    assert.equal(belongsToDesk({ agent: null, agentTo: null }, CODER), false)
    assert.equal(belongsToDesk(activityFor({ event: 'chat_message' }), CODER), false)
  })
})
