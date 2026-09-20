/* Top-down pixel sprites, drawn with `box-shadow`.
 *
 * Top-down rather than isometric on purpose: the floor is a plan view, and an
 * isometric character standing on a flat grid reads as a mistake rather than a
 * style. From above you mostly see hair and shoulders, which is why the three
 * designs differ by silhouette at the top — that is the only part with enough
 * pixels to carry identity at this size.
 *
 * The art lives here as ASCII because a 90-cell grid hand-written as
 * `box-shadow` offsets is unreviewable and silently wrong the first time a
 * comma moves. The geometry is generated; the *palette* stays in CSS as
 * per-character custom properties, so recolouring a character never touches
 * this file.
 *
 * The alphabet is five letters, and what each one *means* is the world's
 * business rather than this file's — the slot is "primary", and whether that
 * primary is hair, a shell, a carapace or a hull is decided by the design
 * table that uses it. Phase 18 widened it from three; `A` and `D` are what
 * make a non-human character possible, because a beak and an eye are exactly
 * the two things a recoloured office worker cannot have.
 *
 *   H  primary   var(--sp-hair)     hair / shell / carapace / hull
 *   F  face      var(--sp-skin)     skin / scales / fur / plating
 *   S  torso     var(--sp-shirt)    shirt / body / fuselage
 *   A  accent    var(--sp-accent)   beak, fin, antenna, visor
 *   D  detail    var(--sp-detail)   eye, outline, dark marking
 *   .  transparent
 */

export const DEFAULT_LAYERS = {
  H: 'var(--sp-hair)',
  F: 'var(--sp-skin)',
  S: 'var(--sp-shirt)',
  A: 'var(--sp-accent)',
  D: 'var(--sp-detail)',
}

/* 9 wide x 10 tall. Odd width so the sprite has a true centre column, which is
 * what lets `translate(-50%, -50%)` land it exactly on its coordinate. */
export const DESIGNS = [
  // 0 — long hair
  [
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHFFFFFHH',
    '.HFFFFFH.',
    '..FFFFF..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — cropped
  [
    '...HHH...',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHFFFFFHH',
    '.HFFFFFH.',
    '..FFFFF..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — topknot
  [
    '....H....',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHFFFFFHH',
    '.HFFFFFH.',
    '..FFFFF..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* One CSS pixel of the sprite, in real pixels. 4 puts a 9x10 design at 36x40:
 * big enough to have presence in the room at the width a demo browser is
 * recorded at, which is the whole reason not to judge these at desktop zoom.
 * 3 was tried first and the characters read as smudges. */
export const SCALE = 4

/* The walk frame.
 *
 * Only the legs move. At nine pixels wide there is no room for a readable arm
 * swing, and from directly above you would barely see one anyway — feet
 * together alternating with feet apart is what reads as walking, and it reads
 * at 4x on a compressed video, which is the only test that matters here.
 *
 * Derived rather than written out a second time: the walk frame must differ
 * from the rest frame in exactly one row, and three hand-copied 10-row designs
 * would let the other nine drift apart silently.
 */
const LEGS_APART = '.S.....S.'

function stepFrame(design) {
  const rows = [...design]
  rows[rows.length - 1] = LEGS_APART
  return rows
}

/* The seated frame: legs gone, because they are under the desk.
 *
 * From directly above, sitting down is almost entirely about where you are —
 * at the chair rather than beside it. The only part that actually changes
 * shape is the legs disappearing beneath the desk, and that one row is enough
 * to sell it once the character is in the right place.
 */
const LEGS_TUCKED = '.........'

function seatedFrame(design) {
  const rows = [...design]
  rows[rows.length - 1] = LEGS_TUCKED
  return rows
}

/** Build the `box-shadow` value for one design. */
export function shadowFor(design, layers = DEFAULT_LAYERS) {
  const cells = []
  design.forEach((row, y) => {
    ;[...row].forEach((cell, x) => {
      const colour = layers[cell]
      if (colour) cells.push(`${x * SCALE}px ${y * SCALE}px 0 0 ${colour}`)
    })
  })
  return cells.join(', ')
}

/* Compile one world's design table into the three frames every pawn needs.
 *
 * Done once per world at module load rather than per render: these never
 * change at runtime, and rebuilding ~60 shadow entries for every pawn on every
 * frame would be work done for nothing. Nine worlds of three frames is still
 * nothing — the cost is paid once, at import.
 */
export function compileSheets(designs, layers = DEFAULT_LAYERS) {
  return {
    art: designs.map((design) => shadowFor(design, layers)),
    step: designs.map((design) => shadowFor(stepFrame(design), layers)),
    seat: designs.map((design) => shadowFor(seatedFrame(design), layers)),
  }
}

/* Paper Office's own sheets, and the fallback for any caller that has no world
 * in hand. Defined here rather than imported from `worlds.js` on purpose: that
 * import would be a cycle, since the registry is what imports *this* file. */
export const DEFAULT_SHEETS = compileSheets(DESIGNS)

export const SPRITE_WIDTH = DESIGNS[0][0].length * SCALE
export const SPRITE_HEIGHT = DESIGNS[0].length * SCALE

/* The markers offered at the entry gate.
 *
 * This list lives here, next to the art, because it is what decides how a
 * person looks on the floor. It used to live in App.jsx as picker options
 * only, and the floor ignored it entirely — see `lookFor`.
 */
export const AVATARS = ['🐝', '🦊', '🐙', '🦉', '🐺', '🦋', '🐢', '🦜']

/* One hair colour per marker, so all eight are telling apart at a glance even
 * though there are only three silhouettes.
 *
 * Identity, not status — which is why these may carry hue at all when the rest
 * of the room may not. Kept desaturated so none of them can be mistaken for
 * the jade/amber/coral of budget health or the instrument blue of a running
 * agent.
 */
const HAIR = [
  '#7a4b6b', // plum
  '#3f5f6b', // steel
  '#8a5a3c', // rust
  '#5b6b45', // moss
  '#4a5570', // slate
  '#6e5a48', // clay
  '#6b3f4f', // wine
  '#52705f', // sage
]

export const HAIR_COLOURS = HAIR

/** Stable small hash, for people who arrived without a marker. */
function hashOf(text) {
  let h = 0
  for (let i = 0; i < (text || '').length; i += 1) {
    h = (h * 31 + text.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

/* How one person looks. Derived from their *marker*, which is theirs and does
 * not change — never from their position in the member list.
 *
 * The list-position version was a real bug: `index % 3` meant two people in a
 * room of four were identical, and because the member list is deduped and
 * re-synced, an index could shift under someone and change their character
 * while they were standing still. A board whose whole claim is that everyone
 * sees the same thing cannot have people swapping faces.
 *
 * The world is the third argument rather than a module-level lookup so this
 * stays a pure function of its inputs — the character picker draws every
 * option at once and the floor draws a mix of people and agents, and both have
 * to be able to say *which* world's cast they mean. A world that ships its own
 * agent table gets it here too, via `agents`.
 *
 * Three silhouettes is the floor and eight is the ceiling: the key is a marker
 * index, and the mod means a world offering five designs simply repeats after
 * five rather than rendering nothing for markers 5-7.
 */
export function lookFor(avatar, userId, world, agents = false) {
  const picked = AVATARS.indexOf(avatar)
  const key = picked >= 0 ? picked : hashOf(userId) % AVATARS.length
  const sheets =
    (agents ? world?.agentSprites : null) ?? world?.sprites ?? DEFAULT_SHEETS
  const palette = world?.palette ?? HAIR
  return {
    art: sheets.art[key % sheets.art.length],
    step: sheets.step[key % sheets.step.length],
    seat: sheets.seat[key % sheets.seat.length],
    hair: palette[key % palette.length],
  }
}
