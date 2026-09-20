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

/* What the pre-paint script in index.html needs before any stylesheet exists.
 *
 * `data-world` alone is not enough to stop a cold load flashing. The attribute
 * means nothing until the stylesheet that reads it arrives, and until then the
 * canvas is painted from the `<meta name="color-scheme">` in index.html, which
 * is Paper Office's literal `light`. A returning Night Watch visitor therefore
 * got a pale canvas for as long as the CSS took to land — which on a slow cold
 * load is the worst frame of the whole page and the one a recording catches.
 *
 * So the two values the browser needs *before* CSS are written here as well,
 * and index.html replays them. It is stored rather than derived because the
 * script is inline and pre-module: it cannot import this registry, and
 * hard-coding a list of dark worlds in the HTML would put the same fact in two
 * places and rot the moment world 20 lands. */
const PAINT_KEY = 'hiveos.world.paint'

export const DEFAULT_WORLD_ID = 'paper'

/* --- Night Watch's cast ----------------------------------------------------
 *
 * Hooded night-watch explorers. Same 9x10 grid, same five-letter alphabet,
 * same generator — a world supplies art, never machinery.
 *
 * What makes them not office workers in navy coats is the hood: it closes over
 * the head so the face is a slot rather than a whole face, and it carries a
 * headlamp on the `A` layer. That lamp is the one warm thing on a character in
 * this world, and it reports nothing — warmth decorates, cool reports.
 *
 *   H  the hood        --sp-hair    per-character, from the palette below
 *   F  skin            --sp-skin
 *   S  the coat        --sp-shirt
 *   A  the headlamp    --sp-accent  warm
 *   D  the eyes        --sp-detail
 *
 * Five rather than three, because `lookFor` mods by the table length and the
 * eight markers land on more of them — the office's three silhouettes differ
 * only above the eyes, and under a hood there is less room to differ. The last
 * row is legs and nothing else in every design, because `stepFrame` and
 * `seatedFrame` replace exactly that row.
 */
const NIGHT_WATCH = [
  // 0 — peaked hood, lamp across the brim
  [
    '....H....',
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHAAAHHH',
    '.HDFFFDH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — wide brim, broad lamp
  [
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHHHHHHHH',
    'HHAAAAAHH',
    '.HDFFFDH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — hood with an earpiece
  [
    '...HHH...',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHHHHHHHA',
    '.HHAAAHH.',
    '.HDFFFDH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — hood down, lamp on a headband
  [
    '...HHH...',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HAAAAAAAH',
    '.HFFFFFH.',
    '..DFFFD..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — tall crest, single lamp
  [
    '....H....',
    '....H....',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHAHHHH',
    '.HDFFFDH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* One hood colour per marker.
 *
 * The office's eight are pitched to sit *darker* than a cream floor; every one
 * of them disappears into a navy deck. These are the same eight identities
 * lifted to read against it, and kept just as desaturated for the same reason:
 * identity may carry hue, but none of it may be mistaken for the instrument
 * blue of a running agent or the jade, orange and coral of budget health.
 */
const NIGHT_HOODS = [
  '#9c82ad', // heather
  '#8494a8', // steel
  '#b08a68', // tan
  '#8fa583', // moss
  '#8089a8', // slate
  '#a89384', // clay
  '#a87f8d', // wine
  '#83a398', // sage
]

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
  {
    id: 'nightsky',
    label: 'Night Watch',
    blurb: 'A deck under a star field, lit by its instruments rather than by day.',
    colorScheme: 'dark',
    // `--cream` in worlds/nightsky.css. Literal for the same reason Paper
    // Office's is: the browser needs it before a stylesheet exists.
    themeColor: '#0b1020',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the bays at
    // y=14, so a world that raised its band would run the sky behind them.
    walkTop: 14,
    designs: NIGHT_WATCH,
    // The crew works this deck; the agents are crew too. A separate species
    // would say the agents are visitors, and the whole claim of the floor is
    // that they work here.
    agentDesigns: null,
    layers: DEFAULT_LAYERS,
    palette: NIGHT_HOODS,
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

/* The two values index.html's pre-paint script replays. See PAINT_KEY.
 *
 * Written from the provider's effect rather than from `setWorld`, so it is
 * also repaired for someone who chose a world before this key existed — their
 * next visit still flashes, and every visit after it does not. */
function savePaint(world) {
  try {
    window.localStorage.setItem(
      PAINT_KEY,
      JSON.stringify({ scheme: world.colorScheme, themeColor: world.themeColor }),
    )
  } catch {
    // Same reasoning as above: a browser with storage blocked simply gets the
    // literal light values in index.html, which is one repaint, not a failure.
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

    // Both of the above also have to be true *before* any of this runs on the
    // next cold load, or a dark world flashes pale while the CSS is in flight.
    savePaint(world)
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
