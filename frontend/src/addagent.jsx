/* Hiring an agent.
 *
 * Its own file because `components.jsx` was already a thousand lines, and
 * because this is one self-contained thing: a four-step form that ends in a
 * `spawn_agent` frame.
 *
 * The four steps are the reference's, and they are steps rather than one long
 * form for the reason the reference has them — hiring is meant to feel like
 * staffing a floor, not like filling in a dialog. Nothing is sent until
 * `spawn` is pressed; the rail is navigation, not a wizard that commits as it
 * goes, so every field stays editable from every step.
 */

import { useState } from 'react'

import { AVATARS, lookFor } from './sprites'

/* Mirrors the server-side truncation in `backend/shared/agents.py`. Matching
 * the limits here keeps what you typed and what arrives the same thing — the
 * same reasoning as MAX_USER_ID at the entry gate. The server still truncates;
 * this only stops the surprise. */
const MAX_NAME = 24
const MAX_ROLE = 24
const MAX_TAGLINE = 120
const MAX_PERSONA = 600
const MAX_PROJECT = 40

const STEPS = [
  { id: 1, title: 'Identity', sub: 'name · character' },
  { id: 2, title: 'Workspace', sub: 'project' },
  { id: 3, title: 'Engine', sub: 'provider · model' },
  { id: 4, title: 'Briefing', sub: 'description · goal' },
]

/* A few roles worth one click, because an empty form is a worse first
 * impression than a form with an obvious next move. Each one fills the fields
 * a hire actually needs — everything stays editable afterwards. */
const PRESETS = [
  {
    name: 'Jim',
    role: 'Editor',
    project: 'newsletter',
    tagline: 'Tightens prose. Cuts what does not earn its place.',
    persona:
      'You edit text. Cut hedges and filler, keep the author’s voice, and '
      + 'say plainly what you changed and why.',
  },
  {
    name: 'Pam',
    role: 'Designer',
    project: 'product',
    tagline: 'Layout, hierarchy, and what to remove.',
    persona:
      'You take design questions. Lead with the single change that would '
      + 'help most, and say what you would remove before what you would add.',
  },
  {
    name: 'Oscar',
    role: 'Analyst',
    project: 'finance',
    tagline: 'Numbers, and what they do not say.',
    persona:
      'You take questions about numbers and cost. Give the figure first, '
      + 'then the assumption it rests on, and name what would change it.',
  },
]

export default function AddAgentModal({ onSpawn, onClose, full }) {
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [project, setProject] = useState('')
  const [tagline, setTagline] = useState('')
  const [persona, setPersona] = useState('')
  const [character, setCharacter] = useState(AVATARS[2])

  const apply = (preset) => {
    setName(preset.name)
    setRole(preset.role)
    setProject(preset.project)
    setTagline(preset.tagline)
    setPersona(preset.persona)
  }

  const submit = (event) => {
    event.preventDefault()
    if (!name.trim() || full) return
    onSpawn({
      name: name.trim().slice(0, MAX_NAME),
      role: role.trim().slice(0, MAX_ROLE),
      project: project.trim().slice(0, MAX_PROJECT),
      tagline: tagline.trim().slice(0, MAX_TAGLINE),
      persona: persona.trim().slice(0, MAX_PERSONA),
      character,
    })
    onClose()
  }

  return (
    <div
      className="modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="hire-title"
      // Click-away closes, but only on the backdrop itself — a click that
      // started inside the panel and drifted out must not throw the form away.
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <form className="hire" onSubmit={submit}>
        <header className="hire__head">
          <h2 className="hire__title" id="hire-title">
            Add agent
          </h2>
        </header>

        <div className="hire__body">
          <nav className="hire__rail" aria-label="Hire steps">
            {STEPS.map((entry) => (
              <button
                type="button"
                key={entry.id}
                className={`railstep ${step === entry.id ? 'railstep--on' : ''}`}
                aria-current={step === entry.id}
                onClick={() => setStep(entry.id)}
              >
                <span className="railstep__n">{entry.id}</span>
                <span className="railstep__title">{entry.title}</span>
                <span className="railstep__sub">{entry.sub}</span>
              </button>
            ))}
          </nav>

          <div className="hire__pane">
            {step === 1 && (
              <>
                <label className="hire__legend" htmlFor="hire-name">
                  Name
                </label>
                <input
                  id="hire-name"
                  className="field"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  maxLength={MAX_NAME}
                  placeholder="Jim"
                  autoComplete="off"
                  autoFocus
                />

                <label className="hire__legend" htmlFor="hire-role">
                  Role
                </label>
                <input
                  id="hire-role"
                  className="field"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  maxLength={MAX_ROLE}
                  placeholder="Editor"
                  autoComplete="off"
                />

                <span className="hire__legend">Character</span>
                <div className="faces" role="radiogroup" aria-label="Character">
                  {AVATARS.map((option) => {
                    const look = lookFor(option, option)
                    return (
                      <button
                        type="button"
                        key={option}
                        role="radio"
                        aria-checked={character === option}
                        aria-label={`Character ${option}`}
                        onClick={() => setCharacter(option)}
                        className={`face ${character === option ? 'face--on' : ''}`}
                      >
                        <span
                          className="agentface"
                          style={{ '--art': look.art, '--sp-hair': look.hair }}
                          aria-hidden="true"
                        />
                      </button>
                    )
                  })}
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <label className="hire__legend" htmlFor="hire-project">
                  Project
                </label>
                <input
                  id="hire-project"
                  className="field"
                  value={project}
                  onChange={(event) => setProject(event.target.value)}
                  maxLength={MAX_PROJECT}
                  placeholder="newsletter"
                  autoComplete="off"
                  aria-describedby="hire-project-hint"
                />
                <p className="hire__hint" id="hire-project-hint">
                  A label for what this agent works on. It appears on their
                  desk card. Every agent on this floor shares the same team
                  memory and the same budget — a project is what they are
                  <em> for</em>, not a wall between them.
                </p>
              </>
            )}

            {step === 3 && (
              <>
                <span className="hire__legend">Provider</span>
                <p className="hire__readout">Groq · openai/gpt-oss-120b</p>
                <p className="hire__hint">
                  Every desk on this floor runs the same model. The budget is
                  shared, so the engine is too — a per-agent model picker would
                  let one hire quietly change what the team spends per call.
                  It is one deployment-wide setting, and this is it.
                </p>
              </>
            )}

            {step === 4 && (
              <>
                <label className="hire__legend" htmlFor="hire-tagline">
                  Description
                </label>
                <input
                  id="hire-tagline"
                  className="field"
                  value={tagline}
                  onChange={(event) => setTagline(event.target.value)}
                  maxLength={MAX_TAGLINE}
                  placeholder="Tightens prose. Cuts what does not earn its place."
                  autoComplete="off"
                  aria-describedby="hire-tagline-hint"
                />
                <p className="hire__hint" id="hire-tagline-hint">
                  One line, shown to the team — and to the other agents, who
                  read it when deciding whether a task belongs at this desk.
                </p>

                <label className="hire__legend" htmlFor="hire-persona">
                  Goal
                </label>
                <textarea
                  id="hire-persona"
                  className="field"
                  rows={4}
                  value={persona}
                  onChange={(event) => setPersona(event.target.value)}
                  maxLength={MAX_PERSONA}
                  placeholder="You edit text. Cut hedges and filler, keep the author's voice…"
                  aria-describedby="hire-persona-hint"
                />
                <p className="hire__hint" id="hire-persona-hint">
                  This becomes the agent's standing instruction. It never
                  leaves the server — it is the model's brief, not board state,
                  so it is not on the snapshot every browser holds.
                </p>
              </>
            )}
          </div>
        </div>

        <div className="hire__presets">
          <span className="hire__legend">Start from</span>
          <div className="hire__presetrow">
            {PRESETS.map((preset) => (
              <button
                type="button"
                key={preset.name}
                className="btn btn--ghost btn--sm"
                onClick={() => apply(preset)}
              >
                {preset.name} · {preset.role}
              </button>
            ))}
          </div>
        </div>

        <footer className="hire__foot">
          {full && (
            <p className="hire__full">
              This floor is full. Dismiss an idle agent to make room.
            </p>
          )}
          <span className="hire__spacer" />
          <button type="button" className="btn btn--ghost" onClick={onClose}>
            cancel
          </button>
          <button
            type="submit"
            className="btn btn--ink"
            disabled={!name.trim() || full}
          >
            spawn
          </button>
        </footer>
      </form>
    </div>
  )
}
