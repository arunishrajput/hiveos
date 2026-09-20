/* The world registry.
 *
 * HiveOS renders one board. A *world* is the costume that board wears: the
 * same sockets, the same scheduler, the same rows in DynamoDB, drawn as a
 * night observation deck or a reef station instead of a paper office.
 *
 * Two rules govern everything in this file, and a world that breaks either one
 * is wrong however good it looks:
 *
 *   A WORLD IS NOT A COLOUR SCHEME. The floor has rooms, desks, a waiting
 *   area, pixel characters, a handoff animation, plants and state-driven
 *   monitor lighting. A world transforms those *objects*. If the only thing
 *   that changed is the value of `--floor`, nothing has been built.
 *
 *   A WORLD MAY NEVER CHANGE WHAT ANYTHING MEANS. The busy blue, the queued
 *   ochre, the budget jade and the over-budget red carry the whole governance
 *   story, which is the product. They are re-tuned for each world's surfaces
 *   and they are never reassigned. A judge who has watched the paper office
 *   must be able to read the reef station on first sight.
 *
 * The one place that bends, and it bends the same way for every world: several
 * worlds want a busy desk to be a warm pool of light — a campfire, a lit
 * cabin, a lantern. Warm is `--honey`, and `--honey` already means *queued,
 * 50-80% of budget spent*. So: ambient warmth is the world's resting
 * character and means nothing; the cool instrument glow is the state and
 * *joins* it when the agent goes BUSY. Warmth decorates and never reports.
 *
 * ---
 *
 * The mechanism is `data-world="<id>"` on `document.documentElement`. Bare
 * `:root` keeps Paper Office; a world adds `:root[data-world="<id>"] { … }` in
 * its own file under `worlds/`, which outranks bare `:root` on specificity —
 * so load order never matters and nothing needs `!important`. An id that
 * matches no stylesheet therefore renders as Paper Office, which is what makes
 * an unknown stored value harmless rather than a blank board.
 */

import { createContext, createElement, useContext, useEffect, useMemo, useState } from 'react'

import { DESIGNS, DEFAULT_LAYERS, HAIR_COLOURS, compileSheets } from './sprites'

const STORAGE_KEY = 'hiveos.world'

export const DEFAULT_WORLD_ID = 'paper'

/* One entry per world.
 *
 * | field         | what it is                                              |
 * |---------------|---------------------------------------------------------|
 * | id            | the `data-world` value, and the CSS filename            |
 * | label         | what the picker calls it                                 |
 * | blurb         | one line in the picker; say what the place IS           |
 * | colorScheme   | `light` or `dark` — drives the UA's own form widgets    |
 * | themeColor    | the mobile browser chrome, matched to the page ground   |
 * | walkTop       | the back-wall band, as a percentage. Not walkable.      |
 * | designs       | the sprite design table — the cast of this world        |
 * | agentDesigns  | a second table, when agents are a different species     |
 * | layers        | letter -> CSS custom property, if not the default five  |
 * | palette       | eight identity colours, one per marker                  |
 *
 * `walkTop` lives here rather than in CSS because both halves need it: the
 * stylesheet paints the wall from `--walk-top` and the walk math converts
 * coordinates with the same number. They cannot be allowed to drift, so the
 * registry owns it and the provider stamps the custom property. A world
 * stylesheet must never set `--walk-top` — the JS would not see it.
 */
const REGISTRY = [
  {
    id: DEFAULT_WORLD_ID,
    label: 'Paper Office',
    blurb: 'Warm daylight, cream tiles, a whiteboard and a water cooler.',
    colorScheme: 'light',
    // `--cream`. Kept in step with the token by hand, because the browser
    // needs this before any stylesheet has been parsed.
    themeColor: '#fff8e7',
    walkTop: 14,
    designs: DESIGNS,
    agentDesigns: null,
    layers: DEFAULT_LAYERS,
    palette: HAIR_COLOURS,
  },
]

/* Compiled once, at import. Each entry carries its own finished sprite sheets
 * so nothing has to recompile art while the picker is open. */
export const WORLDS = REGISTRY.map((world) => ({
  ...world,
  sprites: compileSheets(world.designs, world.layers),
  agentSprites: world.agentDesigns
    ? compileSheets(world.agentDesigns, world.layers)
    : null,
}))

export const PAPER_OFFICE = WORLDS.find((w) => w.id === DEFAULT_WORLD_ID)

/** The world for an id, or Paper Office for anything unrecognised. */
export function worldFor(id) {
  return WORLDS.find((world) => world.id === id) ?? PAPER_OFFICE
}

/* Persistence, in the shape `App.jsx` already uses for identity: a lazy
 * initialiser, try/catch on both sides, and an unknown value treated as
 * absent. A browser with localStorage blocked gets Paper Office and a picker
 * that works for the session — never a refusal to render. */
function loadWorldId() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return WORLDS.some((world) => world.id === raw) ? raw : DEFAULT_WORLD_ID
  } catch {
    return DEFAULT_WORLD_ID
  }
}

function saveWorldId(id) {
  try {
    window.localStorage.setItem(STORAGE_KEY, id)
  } catch {
    // Not worth failing a render over. The choice lasts the session.
  }
}

const WorldContext = createContext(null)

/** The active world, plus the setter the picker calls. */
export function useWorld() {
  return useContext(WorldContext) ?? { world: PAPER_OFFICE, worlds: WORLDS, setWorld: () => {} }
}

export function WorldProvider({ children }) {
  const [worldId, setWorldId] = useState(loadWorldId)
  const world = worldFor(worldId)

  useEffect(() => {
    const root = document.documentElement

    // Always stamped, including for Paper Office — no `:root[data-world=
    // "paper"]` block exists, so bare `:root` still wins and the attribute is
    // simply how you inspect which world is live. This also corrects an
    // unknown id left by the pre-paint script in index.html.
    root.dataset.world = world.id

    // The number CSS paints the wall band from. See `walkTop` above.
    root.style.setProperty('--walk-top', `${world.walkTop}%`)

    // `color-scheme` is set in CSS as well, because the stylesheet lands
    // before first paint and this effect does not. Setting it here too keeps
    // the two honest when a world is chosen at runtime rather than at load.
    root.style.colorScheme = world.colorScheme

    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', world.themeColor)
  }, [world])

  const value = useMemo(
    () => ({
      world,
      worlds: WORLDS,
      setWorld: (id) => {
        const next = worldFor(id)
        saveWorldId(next.id)
        setWorldId(next.id)
      },
    }),
    [world],
  )

  return createElement(WorldContext.Provider, { value }, children)
}
