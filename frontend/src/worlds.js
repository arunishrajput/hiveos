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
 *   and they are never reassigned. Someone who has learned to read the paper
 *   office must be able to read the reef station on first sight.
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

import {
  createContext,
  createElement,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

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

/* --- The Enchanted Forest's cast --------------------------------------------
 *
 * Woodland animals working the clearing. The first cast in the ten worlds that
 * is not bipedal-humanoid-shaped at all, and the first where the `A` and `D`
 * layers Phase 18 added are actually load-bearing: an ear, a beak and an eye
 * are exactly the three things a recoloured office worker cannot have.
 *
 *   H  head fur        --sp-hair    per-character, from the palette below
 *   F  muzzle / blaze  --sp-skin    the pale fur of a snout or a facial disc
 *   S  the body        --sp-shirt
 *   A  ears / beak     --sp-accent  warm
 *   D  the eyes        --sp-detail
 *
 * From directly above you see the top of a head, so the silhouette above the
 * eyes is the whole of identity at this size — which is lucky, because ears are
 * the one part of an animal that reads instantly from above. Five designs, and
 * every one of them is a different pair of ears: pricked, tufted, none at all,
 * long, and antlered. The badger has no ears worth drawing from above and is
 * identified by its blaze instead, which is the only design here that carries
 * its identity in a marking rather than in an outline.
 *
 * The last row is legs and nothing else in every design, because `stepFrame`
 * and `seatedFrame` replace exactly that row.
 */
const WOODLAND = [
  // 0 — fox: pricked ears, a narrow pale snout
  [
    '.A.....A.',
    '.AHHHHHA.',
    '.HHHHHHH.',
    'HHDHHHDHH',
    '.HHFFFHH.',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — owl: ear tufts, a broad facial disc, a beak between the eyes
  [
    '..H...H..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HFFFFFFFH',
    'HFDFAFDFH',
    '.HFFFFFH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — badger: no ears from above, and the blaze instead
  [
    '...HFH...',
    '.HHHFHHH.',
    'HHHHFHHHH',
    'HHDHFHDHH',
    '.HHHFHHH.',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — hare: the ears are most of the character
  [
    '..A...A..',
    '..A...A..',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHDHHHDHH',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — stag: branching antlers, which is the widest silhouette in the set
  [
    'A.A...A.A',
    '.AA...AA.',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHDHHHDHH',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* One coat colour per marker.
 *
 * Pitched to read against moss — all eight clear 4.5:1 on the clearing floor,
 * inside a hollow and on the dirt path — and spread across the hue circle
 * rather than kept inside the world's greens, because eight greens are one
 * green at sprite size.
 *
 * Every one is desaturated to 0.04-0.44 where the four state hues run
 * 0.57-0.64. That gap is the whole safety argument and it matters more here
 * than in either dark world before it: this is a green world whose budget-jade
 * has to stay legible, so an identity that wandered into a saturated green or a
 * saturated cyan would be competing with the two hues the board reports with.
 * The fox is the closest call — 26.7deg is honey's hue — and it is held at 0.44
 * against honey's 0.60, on the same guarantee that separates honey from the
 * brand amber: honey is only ever a word, and a fox is never one.
 */
const FOREST_COATS = [
  '#bd8f6a', // fox
  '#bda87c', // tawny
  '#aeb6b4', // badger
  '#a8b487', // hare
  '#b39a86', // hazel
  '#c2a0bc', // dusk
  '#c69a9a', // finch
  '#8fb2be', // kingfisher
]

/* --- The Reef Station's cast ------------------------------------------------
 *
 * The animals that live on the reef the station was built into. Fish, ray,
 * turtle, octopus and crab.
 *
 *   H  scales / shell  --sp-hair    per-character, from the palette below
 *   F  pale markings   --sp-skin    a bleached stripe, a head, a carapace band
 *   S  the hind body   --sp-shirt
 *   A  fins and claws  --sp-accent  the thin parts, where the light goes through
 *   D  the eyes        --sp-detail
 *
 * IDENTITY LIVES IN THE FIRST TWO ROWS, AND THIS CAST WAS DRAWN TWICE TO FIND
 * THAT OUT. The first attempt reasoned that a sea creature seen from directly
 * above shows you its whole body plan — that is the view every field guide
 * uses — so the five were given genuinely different outlines top to bottom: a
 * narrow dart, a wide diamond, an oval between four flippers, a dome trailing
 * arms, a flat shell. Rendered at 12x they were five coloured blobs with two
 * eyes each, and no better at 4x.
 *
 * The reason is structural rather than artistic. Rows 6-9 are not available —
 * they are the walk machinery, and `stepFrame` and `seatedFrame` both rewrite
 * the last one, so every design has to share that torso. Rows 2-5 are
 * dominated by the eyes, and any two things with two eyes at 9px apart read as
 * the same thing. That leaves rows 0 and 1, which is exactly where Night
 * Watch put its hoods and the Forest put its ears — arrived at there by
 * drawing heads from above, and true here for a different reason.
 *
 * So each of these five is identified by what sticks out at the FRONT: a
 * pointed snout, a wing to each edge, a small head between two flippers, a
 * rounded mantle, and a pair of claws held up. The `A` layer is those
 * extremities in every design, which is what the brief asks for.
 *
 * The last row is the tail rather than legs, which turns out to be a gift:
 * `..S...S..` is a closed caudal fin and `.S.....S.` is a spread one, so the
 * walk cycle the office uses for feet is a tail beat here for free.
 */
const REEF = [
  // 0 — fish: a pointed snout, and pectoral fins out at the midline
  [
    '....H....',
    '...HHH...',
    '..HHHHH..',
    '.HDHHHDH.',
    'AAHHHHHAA',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — ray: a wing to each edge, and the widest front on the floor
  [
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHDHHHDHH',
    'AHHHHHHHA',
    'AAHHHHHAA',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — turtle: a small head out front, between two front flippers
  [
    '....F....',
    '.AHHHHHA.',
    'AAHHHHHAA',
    '.HDHHHDH.',
    '.HHHHHHH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — octopus: a tall rounded mantle, and arms out at the shoulders
  [
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHDHHHDHH',
    'A.HFFFH.A',
    'ASSSSSSSA',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — crab: two claws held up, over a wide flat carapace
  [
    'AA.....AA',
    '.AA...AA.',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHDHHHDHH',
    'HHFFFFFHH',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* One scale colour per marker.
 *
 * Measured against the three grounds a creature is ever seen on — the seabed,
 * a dome's deck and the settled plating — and every one clears 4.0:1 on all
 * three, worst case 4.06.
 *
 * Held between 0.13 and 0.39 saturation, where the four state hues run
 * 0.48-0.74. That gap does more work here than in any world before it: this is
 * the world whose ambient hue IS its busy hue, so `--cool` cannot separate
 * itself from the water by hue and separates by saturation and value instead.
 * An identity that wandered into a saturated cyan would be taking away the one
 * argument the whole world rests on. The steel at 211deg is the closest any of
 * them comes to the busy cyan at 190deg, and it is held at 0.24 saturation
 * against `--cool`'s 0.74.
 *
 * Spread across the hue circle rather than kept inside the reef's blues, for
 * the reason the Forest's coats are not all green: eight blues are one blue at
 * sprite size.
 */
const REEF_SCALES = [
  '#d29b81', // clownfish
  '#c9b47a', // wrasse
  '#a9c47f', // parrot
  '#b0a3cd', // urchin
  '#cc9dbc', // orchid
  '#9db5cf', // steel
  '#c7ad95', // driftwood
  '#a7c0b8', // pearl
]

/* --- The Alien Colony's cast ------------------------------------------------
 *
 * The first world to use `agentDesigns`, and the first where the two casts are
 * different species: the people are colonists, the agents are the service
 * robots working the stations. That is a claim the office could not make and
 * this world can — an agent at a desk is *visibly* not one of the people
 * watching it, which is the whole shape of the product in one silhouette.
 *
 * It is also the only place in the ten worlds where the distinction is honest.
 * Night Watch deliberately gave agents the same cast, because the claim there
 * is that the crew works the deck together. A colony has machines in it.
 *
 *   H  the cranium     --sp-hair    per-colonist, from the palette below
 *   F  the face        --sp-skin
 *   S  the suit        --sp-shirt
 *   A  antenna/visor   --sp-accent  the world's ambient violet
 *   D  the eyes        --sp-detail
 *
 * The silhouette is the point, not the palette: a wide domed cranium over a
 * narrow torso is the opposite proportion to an office worker, whose shoulders
 * are the widest thing about them. Recolouring would not have got there.
 */
const COLONISTS = [
  // 0 — domed cranium, twin antennae
  [
    '..A...A..',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HDFFFFFDH',
    '.HFFFFFH.',
    '..SSSSS..',
    '.SSSSSSS.',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — elongated crown, one tall antenna
  [
    '....A....',
    '....A....',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HDFFFFFDH',
    '..SSSSS..',
    '.SSSSSSS.',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — broad flat head, side sensors
  [
    '...HHH...',
    '.HHHHHHH.',
    'AHHHHHHHA',
    'HHHHHHHHH',
    'HDFFFFFDH',
    '.HFFFFFH.',
    '..SSSSS..',
    '.SSSSSSS.',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — a visor band where the eyes would be
  [
    '....A....',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HAAAAAAAH',
    '.HFFFFFH.',
    '..SSSSS..',
    '.SSSSSSS.',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — eyes on stalks
  [
    '..D...D..',
    '..A...A..',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    '.HFFFFFH.',
    '..SSSSS..',
    '.SSSSSSS.',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* The agents. Small service robots: a hull, a sensor band instead of a face,
 * and manipulator arms on the row where a colonist has hands.
 *
 * No `F` layer anywhere in the four designs, which is the tell — a robot has
 * no skin, so the layer simply goes unused and `shadowFor` emits nothing for
 * it. The dark optic on `D` is what gives a faceless box a front.
 */
const SERVICE_ROBOTS = [
  // 0 — drum chassis, optic band, mast antenna
  [
    '....A....',
    '..HHHHH..',
    '.HHHHHHH.',
    '.HDDDDDH.',
    '.HHHHHHH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 1 — flat-top chassis, twin optics, stub antennae
  [
    '.A.....A.',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HDHHHHHDH',
    'HHHHHHHHH',
    '.HHHHHHH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 2 — dish head on a neck
  [
    '..AAAAA..',
    '...A.A...',
    '..HHHHH..',
    '.HDDDDDH.',
    '..HHHHH..',
    '...SSS...',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 3 — low hauler, one recessed optic
  [
    '...HHH...',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHH.D.HHH',
    'HHHHHHHHH',
    '.HHHHHHH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
]

/* --- Arctic Base's cast -----------------------------------------------------
 *
 * The station's people are the research team, in hooded parkas. Its agents are
 * the penguins, who were here first and work the survey stations. The third
 * world to use `agentDesigns`, for the colony's and the harbour's reason: an
 * agent at a desk has to be visibly not one of the people watching it, and a
 * silhouette says that faster than a hue does on a compressed recording.
 *
 *   H  hood / plumage  --sp-hair    per-character, from the palette below
 *   F  the face        --sp-skin    people only
 *   S  parka / body    --sp-shirt
 *   A  ruff, mittens, bill          --sp-accent
 *   D  goggles, eye    --sp-detail
 *
 * WHAT MAKES THESE NOT NIGHT WATCH'S HOODS, which is the risk a fourth hooded
 * cast runs: the night deck's `A` is a headlamp lying ACROSS the brim, one bar
 * at the top of the head. A parka's tell is the fur ruff, which RINGS the face
 * opening — `A` down both sides of the face and under the chin, which is a
 * shape the night watch never makes. The mittens are the same layer at the
 * ends of row 8, where every other world in the set has bare hands; an arctic
 * team with bare hands was the first thing that looked wrong.
 *
 * THE PENGUINS HAVE NO `F` LAYER, and the reason is the honest one rather than
 * the convenient one. A penguin's white front is the first thing anybody draws
 * and IT IS NOT VISIBLE FROM ABOVE — from directly overhead a penguin is a
 * dark back, a bill, and two flipper edges, which is also exactly the number of
 * marks a 9x10 grid can hold. So `shadowFor` simply emits nothing for `F` here,
 * the same tell the colony's robots and the harbour's drones carry, and the
 * skin token stays unambiguously human.
 *
 * Identity lives in rows 0 and 1 in both tables — Phase 21's lesson, taken as
 * given. The last row is legs and nothing else in every design, because
 * `stepFrame` and `seatedFrame` replace exactly that row; a penguin's feet are
 * therefore `S` and not `A`, or the walk cycle would change their colour
 * halfway through a stride.
 */
const PARKA_TEAM = [
  // 0 — hood drawn tight, deep fur ruff right around the face
  [
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    '.HAAAAAH.',
    '.ADFFFDA.',
    '..AFFFA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 1 — wide storm hood, shallow ruff
  [
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHHAAAHHH',
    '.HDFFFDH.',
    '..AFFFA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 2 — peaked hood with the storm flap out to both shoulders
  [
    '....H....',
    '..HHHHH..',
    '.HHHHHHH.',
    '.HAAAAAH.',
    'HHDFFFDHH',
    '..AFFFA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 3 — drawcords flying loose, so row 0 is split rather than solid
  [
    '.A.....A.',
    '.AHHHHHA.',
    '..HHHHH..',
    '.HAAAAAH.',
    '.HDFFFDH.',
    '..AFFFA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 4 — the widest ruff in the set, and the one pair of goggles pulled DOWN
  [
    '..HHHHH..',
    'AHHHHHHHA',
    'AAHHHHHAA',
    '.AAAAAAA.',
    '.HDDDDDH.',
    '..AFFFA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
]

/* The agents. Penguins, seen from directly above.
 *
 * Four rather than five: `lookFor` mods by the table length, so the eight
 * markers land on more of a short table, and there are only so many ways a
 * top-down penguin can differ above the eyes.
 *
 * The bill is `--sp-accent` and IT IS NOT ORANGE. This is the fourth world
 * running where the prop with the obvious real-world colour was a state hue
 * wearing a costume — the reef's aqua fin, the harbour's brass fitting and its
 * orange windsock, and now a gentoo's bill. An orange mark riding on every
 * agent on a board whose `--honey` means "queued" is the same defect each
 * time. Plenty of real penguins have dark or pale bills; these have pale ones,
 * in the same oat the parka ruffs are, which also lets one accent token serve
 * both casts.
 */
const PENGUINS = [
  // 0 — Adélie: small round head, short bill, eyes wide apart
  [
    '....A....',
    '...HHH...',
    '..HHHHH..',
    '.HDHHHDH.',
    '.HHHHHHH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 1 — emperor: tall head, long bill, the two ear-patch flashes low
  [
    '....A....',
    '....A....',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHDHHHDHH',
    '.AHHHHHA.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 2 — chinstrap: narrow bill, and the strap as a line across the throat
  [
    '....A....',
    '...HHH...',
    '..HHHHH..',
    '.HDHHHDH.',
    '.HHHHHHH.',
    '.AAAAAAA.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'SSSSSSSSS',
    '..S...S..',
  ],
  // 3 — crested: plumes out to each side of row 0, bill below them
  [
    '.A.....A.',
    '.AAHHHAA.',
    '...HAH...',
    '..HHHHH..',
    '.HDHHHDH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
]

/* One parka shell per marker, shared by the team and the penguins.
 *
 * Shared for the reason the colony and the harbour share theirs: the palette is
 * *identity*, and the person who picked the fox is the fox whichever body the
 * world gives them. On a penguin it reads as the oily sheen a penguin's back
 * actually has, which photographs blue, green or violet depending on the light.
 *
 * MEASURED AGAINST THREE VALUE REGISTERS, WHICH IS WHAT MAKES THIS THE
 * TIGHTEST PALETTE IN THE SET. The harbour's jackets only ever had to clear
 * near-white; these have to clear near-white snow AND the cabin deck, which is
 * a third of the way down the value range, AND a lit cabin deck below that.
 * Every one clears 4.0:1 on all five surfaces a pawn can stand on — packed
 * snow, bare blue ice, the swept path, a cabin deck and a lit cabin deck —
 * worst case 4.60:1 against the lit deck, which is the binding one every time.
 *
 * Held between 0.23 and 0.45 saturation where this world's four state hues run
 * 0.83-0.96. That gap is the whole guarantee: on a bright world a state hue
 * has to be both deep and saturated to carry a word, and deep is exactly what
 * an identity has to be as well — so saturation is the only axis left to
 * separate them on, and it is held at 2.0x or better everywhere.
 */
const PARKA_SHELLS = [
  '#644c71', // aubergine
  '#3e5670', // deep petrol
  '#695241', // umber
  '#3c5c49', // pine
  '#4e5079', // indigo
  '#575636', // olive
  '#6b3e52', // wine
  '#48595d', // storm
]

/* --- Cloud City's cast ------------------------------------------------------
 *
 * The sky harbour's people are pilots: flying helmets, goggles, high-collared
 * jackets. Its agents are the courier drones that work the control desks. The
 * second world to use `agentDesigns`, and honest here for the colony's reason —
 * a harbour is a place machines work and people arrive at, so an agent at a
 * desk is visibly not one of the people watching it.
 *
 *   H  helmet / cap    --sp-hair    per-pilot, from the palette below
 *   F  the face        --sp-skin
 *   S  flight jacket   --sp-shirt
 *   A  goggles, straps --sp-accent  weathered leather
 *   D  the eyes        --sp-detail
 *
 * Identity lives in rows 0 and 1 — Phase 21's lesson, taken as given rather
 * than rediscovered — but this cast gets a second register the animals did not
 * have. A pilot's most identifying feature is at the FRONT of the head, where
 * rows 2-5 are "dominated by the eyes"; goggles are worn exactly there, so the
 * `A` layer can replace the eye row outright. Two of these five have their
 * goggles down over the eyes and three have them pushed up, which doubles the
 * silhouette work rows 0 and 1 are doing.
 *
 * The last row is legs and nothing else in every design, because `stepFrame`
 * and `seatedFrame` replace exactly that row.
 */
const PILOTS = [
  // 0 — leather flying helmet, goggles DOWN over the eyes
  [
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHHHHHHHH',
    'HAAAAAAAH',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — peaked harbour cap, goggles pushed up onto the brim
  [
    '...HHH...',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HAAAAAAAH',
    '.HDFFFDH.',
    '..FFFFF..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — helmet with the earflaps out, which is the widest row 1 in the set
  [
    '...HHH...',
    'AHHHHHHHA',
    'HHHHHHHHH',
    'HHHHHHHHH',
    '.HDFFFDH.',
    '..FFFFF..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — chin straps flying loose behind, so row 0 is split rather than solid
  [
    '.A.....A.',
    '.AHHHHHA.',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHDHHHDHH',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — crested helmet, visor band DOWN
  [
    '....H....',
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHAAAAAHH',
    '..HFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* The agents. Small courier drones working the harbour's control desks.
 *
 * No `F` layer in any of the four, which is the same tell the colony's robots
 * carry: a drone has no skin, so `shadowFor` simply emits nothing for it. The
 * dark optic on `D` is what gives a hovering box a front.
 *
 * The last row is landing skids rather than legs, which turns out to be the
 * same gift the reef's tails were: `..S...S..` is a pair of skids together and
 * `.S.....S.` is the same pair spread, so the walk cycle the office uses for
 * feet reads here as a hover settling and lifting.
 *
 * Their rotors are the `A` layer, in the pilots' leather rather than in
 * anything bright. A drone with a lit nose would be a small cyan mark moving
 * about a floor whose whole argument is that only a working desk is cyan —
 * the same trap the reef's ROV would have walked into.
 */
const SKY_DRONES = [
  // 0 — quadrotor, discs at the corners
  [
    'A.......A',
    '.AHHHHHA.',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHDDDDDHH',
    '.HHHHHHH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 1 — single main rotor over a narrow hull
  [
    '....A....',
    '...AAA...',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHDDDHHH',
    '.HHHHHHH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 2 — fixed-wing glider, a wing out to each edge.
  //
  // Its optic row is the wide band twice over, which is deliberate: a single
  // recessed dot was drawn first and the two gaps around it read as a PAIR OF
  // EYES, which is the one thing a machine on this floor may not have. Sharing
  // an optic with design 0 costs nothing, because identity lives in rows 0 and
  // 1 and these two do not share those.
  [
    '..HHHHH..',
    'AAHHHHHAA',
    '.HHHHHHH.',
    'HHHHHHHHH',
    'HHDDDDDHH',
    '.HHHHHHH.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
  // 3 — twin stacked rotors, the tallest pair in the set
  [
    '.AA...AA.',
    '.AA...AA.',
    '..HHHHH..',
    '..HHHHH..',
    '.HDDDDDH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSSA',
    '..S...S..',
  ],
]

/* One jacket colour per marker, shared by the pilots and their drones.
 *
 * Shared for the colony's reason: the palette is *identity*, and the person who
 * picked the fox is the fox whichever body the world gives them. Silhouette is
 * what separates a person from an agent here, and it survives a compressed
 * recording better than hue does.
 *
 * MEASURED AGAINST A BRIGHT WORLD, WHICH INVERTS THE PROBLEM. The office's
 * eight are pitched to sit darker than a cream floor and the three dark worlds
 * lifted theirs to read against navy, moss and water. Cloud City is brighter
 * than the office, so these come *down* again and further: every one clears
 * 4.0:1 on the platform stone, a pavilion deck, a busy pavilion deck and the
 * cloud seen through a gap in the deck, worst case 4.05.
 *
 * Held between 0.15 and 0.61 saturation where this world's four state hues run
 * 0.81-0.95 — the widest saturation floor any world has needed, because a
 * bright world's state hues have to be deep and saturated to carry a word, and
 * deep saturated marks are exactly what an identity must not be mistaken for.
 * The harbour blue at 214deg is the closest call and is held at 0.26 against
 * `--cool`'s 0.91.
 */
const PILOT_JACKETS = [
  '#6b5586', // aubergine
  '#3f6285', // deep harbour
  '#7d5a31', // tan
  '#4f7350', // olive
  '#7a5566', // mulberry
  '#5f6289', // iris
  '#8a5a52', // terracotta
  '#5d6b7d', // slate
]

/* One hull colour per marker, shared by the colonists and their robots.
 *
 * Shared on purpose: the palette is *identity*, and the person who picked the
 * fox is the fox whichever body the world gives them. What separates a person
 * from an agent here is the silhouette, which is a stronger signal than hue
 * and survives a compressed recording.
 *
 * Pitched to read against purple regolith — all eight clear 5:1 on the module
 * deck — and deliberately spread across the hue circle rather than kept inside
 * the world's violet family, because eight violets are one violet at sprite
 * size. Every one is desaturated to 0.16-0.34 where the four state hues run
 * 0.57-1.00: identity may carry hue, but a dusty clay hull can never be
 * mistaken for the honey of a queue label.
 */
const COLONY_HULLS = [
  '#a88fc8', // amethyst
  '#8f9ec6', // periwinkle
  '#c294b0', // orchid
  '#96b3a8', // verdigris
  '#8b8fb8', // iris
  '#bfa08f', // clay
  '#c08fa0', // rose
  '#9db08f', // lichen
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
/* --- Desert Outpost's cast --------------------------------------------------
 *
 * The outpost's people are travellers in head wraps; its agents are the animals
 * that already lived in the dunes. The fourth world to use `agentDesigns`, and
 * the argument is Arctic Base's rather than the colony's: the survey team are
 * visitors and the fennec was here first, so an agent at a field station is
 * visibly not one of the people watching it.
 *
 *   H  wrap / pelt / scales  --sp-hair    per-character, from the palette below
 *   F  the face              --sp-skin    people only
 *   S  robe / body           --sp-shirt
 *   A  wrap tail, ears, tail --sp-accent
 *   D  eyes                  --sp-detail
 *
 * WHAT MAKES THESE NOT THE NIGHT WATCH'S HOODS AND NOT THE ICE TEAM'S PARKAS,
 * which is the risk a THIRD hooded cast runs and the one Phase 24 wrote down.
 * The night deck's `A` is a headlamp lying ACROSS the brim: one bar, centred,
 * at the top of the head. A parka's `A` RINGS the face opening and repeats at
 * the ends of row 8 as mittens: symmetrical, on both sides, every time. A
 * desert head wrap does neither — its tell is the loose end of the cloth, which
 * hangs down ONE shoulder and nothing else. Every traveller here is
 * asymmetric, and neither of the other two casts ever is. That is a difference
 * the eye gets at 9x10 without being told.
 *
 * THE ANIMALS HAVE NO `F` LAYER, the same tell the colony's robots, the
 * harbour's drones and the ice's penguins carry: a fennec seen from directly
 * above is ears, a back and two eyes, and `--sp-skin` stays unambiguously
 * human. Identity lives in rows 0 and 1 in both tables — Phase 21's lesson,
 * taken as given and now holding for a seventh cast. The last row is legs and
 * nothing else in every design, because `stepFrame` and `seatedFrame` replace
 * exactly that row.
 *
 * WHICH IS ALSO WHY A TAIL CANNOT BE DRAWN WHERE A TAIL GOES. Seen from above a
 * quadruped's tail trails off the back of it, and the back of a sprite is row
 * 9 — the one row the walk cycle rewrites, so anything put there changes colour
 * halfway through a stride. It is curled to one side at row 8 instead, which is
 * what a resting fennec actually does with it and which makes the animals
 * asymmetric too.
 */
const CARAVAN = [
  // 0 — wrap drawn close, the loose end down the left shoulder
  [
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    '.HHHHHHH.',
    'AHDFFFDH.',
    'A.HFFFH..',
    'ASSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — a wide brow band, and the end thrown over the right shoulder
  [
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    '.AAAAAAA.',
    '.HDFFFDHA',
    '..HFFFH.A',
    '.SSSSSSSA',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — the wrap piled high on the crown, short end to the left
  [
    '....H....',
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    'AHDFFFDH.',
    '.AHFFFH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — hood thrown back, the cloth round the neck only
  [
    '..HHHHH..',
    '.HHHHHHH.',
    '.HFFFFFH.',
    '..FFFFF..',
    '..DFFFD..',
    '.AAAAAAA.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — veiled against the sand, so row 4 is an eye slot rather than a face
  [
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    'HHHHHHHHH',
    '.HDDDDDH.',
    '.HHHHHHHA',
    '.SSSSSSSA',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
]

/* The agents. The dune's own residents, seen from directly above.
 *
 * Four rather than five: `lookFor` mods by the table length, so the eight
 * markers land on more of a short table. Two with ears and two without, and the
 * two of each differ from each other in row 0 rather than anywhere lower —
 * enormous round ears against tall narrow ones, a narrow snout against a wide
 * flat skull.
 *
 * THE EARS ARE `--sp-accent` AND THAT COLOUR IS MADDER ROSE, NOT SAND. A
 * fennec's ears are the first thing anybody draws and the obvious colour for
 * them is the pale gold of the animal itself — which is this world's floor, so
 * the ears would vanish into the ground the character is standing on. It is the
 * sixth world running where the prop with the obvious real-world colour had to
 * go somewhere else, and the first where the reason was legibility rather than
 * a state collision. The rose reads as the ear lining, which on a real fennec
 * is exactly what is pink.
 */
const DESERT_FAUNA = [
  // 0 — fennec: ears filling both top corners, which is the whole animal
  [
    'AA.....AA',
    'AAA...AAA',
    '.AAHHHAA.',
    '..HHHHH..',
    '.HDHHHDH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSS.',
    '..S...S..',
  ],
  // 1 — jerboa: two tall narrow ears rising from the centre
  [
    '..A...A..',
    '..A...A..',
    '..AHHHA..',
    '..HHHHH..',
    '.HDHHHDH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    '.SSSSSSSA',
    '..S...S..',
  ],
  // 2 — agama: no ears at all, a narrow snout widening into the skull
  [
    '...HHH...',
    '..HHHHH..',
    '.HHHHHHH.',
    'HDHHHHHDH',
    '.HHHHHHH.',
    '..HHHHH..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'ASSSSSSS.',
    '..S...S..',
  ],
  // 3 — gecko: a wide flat skull with the eyes right at the front of it
  [
    '.HHHHHHH.',
    'HDHHHHHDH',
    'HHHHHHHHH',
    '.HHHHHHH.',
    '..HHHHH..',
    '..AHHHA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    '.SSSSSSSA',
    '..S...S..',
  ],
]

/* One dyed cloth per marker, shared by the travellers and the animals.
 *
 * Shared for the reason the colony, the harbour and the ice share theirs: the
 * palette is *identity*, and the person who picked the fox is the fox whichever
 * body the world gives them. On an animal it reads as the coat, which in real
 * desert fauna genuinely runs from slate to olive to rust.
 *
 * NOT ONE OF THESE IS IN THE OCHRE WEDGE, AND THAT IS THE POINT. Every other
 * world could spend a hue anywhere it liked as long as it stayed clear of four
 * narrow bands. This world's entire ground is one of those bands, so the whole
 * region from roughly 10deg to 50deg is unavailable twice over — a warm brown
 * identity would be both the colour of the sand it stands on and the colour of
 * the word hanging under it while it waits. Seven of the eight are therefore
 * cool, green or violet, and the one warm-neutral is held at 0.26 saturation
 * against `--honey`'s 0.98, a 3.8x gap.
 *
 * MEASURED AGAINST TWO VALUE REGISTERS. Every one clears 4.0:1 on all five
 * surfaces a pawn can stand on — open sand, scoured pan, the caravan track, an
 * outpost deck and a lit outpost deck — worst case 4.13:1 against the lit deck,
 * which is the binding one every time. Held between 0.14 and 0.48 saturation
 * where this world's four state hues run 0.86-0.98.
 */
const CARAVAN_CLOTH = [
  '#364365', // indigo
  '#35504f', // verdigris
  '#43533c', // desert sage
  '#4b4d31', // dry olive
  '#4d3757', // aubergine
  '#663546', // madder
  '#464951', // basalt
  '#4e443a', // dust
]

/* --- Ancient Ruins' cast ----------------------------------------------------
 *
 * The temple's people are an expedition of archaeologists; its agents are the
 * stone sentinels that were carved here long before anybody arrived with a
 * trowel. The fifth world to use `agentDesigns`, and the argument is the
 * colony's rather than Arctic Base's: a temple is a place its guardians work
 * and its excavators visit, so an agent at a worktable is visibly not one of
 * the people watching it.
 *
 *   H  hat / stone        --sp-hair    per-character, from the palette below
 *   F  the face           --sp-skin    people only
 *   S  jacket / torso     --sp-shirt
 *   A  band, peak, strap  --sp-accent  bone canvas
 *   D  eyes / eye slits   --sp-detail
 *
 * WHAT MAKES THESE NOT THE NIGHT WATCH'S HOODS, THE ICE TEAM'S PARKAS OR THE
 * CARAVAN'S HEAD WRAPS — the risk a FOURTH covered-head cast runs. A hood
 * closes over the head and carries a lamp ACROSS the brim; a parka RINGS the
 * face opening; a head wrap's tell is one loose end down one shoulder. A hat
 * is none of those: seen from above it is a brim, which is WIDER than the head
 * under it, with a band ringing the crown inside the brim's edge. Three of the
 * five here are hats of different widths, and the other two are what an
 * archaeologist wears when the hat is off — a knotted bandana and a headband
 * — both of which show the whole crown, which no hooded or wrapped cast ever
 * does. The pack straps and the satchel strap are the other tell: kit worn
 * over the jacket, which the night deck, the ice and the caravan never carry.
 *
 * THE SENTINELS HAVE NO `F` LAYER, the same tell the colony's robots, the
 * harbour's drones, the ice's penguins and the dune's animals carry: a carved
 * guardian is stone all the way through, and `--sp-skin` stays unambiguously
 * human. And their hands are `H` rather than `F` — stone fists in the same
 * stone as the head — which is what makes a sentinel read as one carved
 * object rather than as a person in a mask. Identity lives in rows 0 and 1 in
 * both tables: Phase 21's lesson, taken as given and now holding for an
 * eighth cast. The last row is legs and nothing else in every design, because
 * `stepFrame` and `seatedFrame` replace exactly that row.
 */
const EXPEDITION = [
  // 0 — slouch hat: a brim turned up on one side, a band round the crown
  [
    '..HHHHH..',
    '.HHHHHHHH',
    'HHAAAHHHH',
    '.HHHHHHH.',
    '..HFFFH..',
    '..DFFFD..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 1 — pith helmet: a dome with a pale rim all the way round
  [
    '...AAA...',
    '..AHHHA..',
    '.AHHHHHA.',
    '.AHHHHHA.',
    '..AFFFA..',
    '..DFFFD..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 2 — bandana knotted at the back, pack straps over both shoulders
  [
    '...HH..H.',
    '..HHHHHH.',
    '.HHHHHHH.',
    '.HHHHHHH.',
    '..FFFFF..',
    '..DFFFD..',
    '.SASSSAS.',
    'SSASSSASS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 3 — the wide flat brim: the whole width of the grid, band inside it
  [
    '.HHHHHHH.',
    'HHHAAAHHH',
    'HHAHHHAHH',
    'HHHAAAHHH',
    '.HHFFFHH.',
    '..DFFFD..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'FSSSSSSSF',
    '..S...S..',
  ],
  // 4 — hat off: cropped hair under a headband, one satchel strap across
  [
    '...HHH...',
    '..HHHHH..',
    '.HAAAAAH.',
    '.HHHHHHH.',
    '..FFFFF..',
    '..DFFFD..',
    '.SSSSSAS.',
    'SSSSSASSS',
    'FSSSSASSF',
    '..S...S..',
  ],
]

/* The stone sentinels. Four carved heads, every one of them a shape no living
 * head has: a square block, a crown of points, a flat slab with a brow across
 * it, and a rounded head with lappets hanging either side of it. The eye
 * slits are `D` and are dark — a guardian whose eyes glowed would be a second
 * status light walking about the floor, and this world's argument is that
 * there is exactly one. The collar and the brow are the pale `A`, which is
 * the same bone canvas as a hat band: dressed stone and bleached cloth are
 * close enough in colour that one token honestly serves both. */
const SENTINELS = [
  // 0 — the block: a square head, wide eye slits, a collar
  [
    '.HHHHHHH.',
    '.HHHHHHH.',
    '.HDDHDDH.',
    '.HHHHHHH.',
    '.HHHHHHH.',
    '..AAAAA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'HSSSSSSSH',
    '..S...S..',
  ],
  // 1 — the crowned: a row of points along the top of the head
  [
    'H.H.H.H.H',
    'HHHHHHHHH',
    '.HHHHHHH.',
    '.HDHHHDH.',
    '.HHHHHHH.',
    '..AAAAA..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'HSSSSSSSH',
    '..S...S..',
  ],
  // 2 — the slab: a flat head the full width of the grid, a pale brow across it
  [
    'HHHHHHHHH',
    'HAAAAAAAH',
    'HHDHHHDHH',
    'HHHHHHHHH',
    '.HHHHHHH.',
    '..SSSSS..',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'HSSSSSSSH',
    '..S...S..',
  ],
  // 3 — the lappets: a rounded head with the headdress hanging down both sides
  [
    '..HHHHH..',
    '.HHHHHHH.',
    'AHHHHHHHA',
    'AHDHHHDHA',
    'AHHHHHHHA',
    '.A.....A.',
    '.SSSSSSS.',
    'SSSSSSSSS',
    'HSSSSSSSH',
    '..S...S..',
  ],
]

/* One hat per marker, shared by the expedition and the sentinels.
 *
 * Shared for the reason every world with two casts shares its palette: the
 * palette is *identity*, and the person who picked the fox is the fox
 * whichever body the world gives them. On a sentinel it reads as the stone
 * the guardian was carved from — and temple statuary genuinely runs from
 * slate to serpentine to rose granite.
 *
 * PALE, because the floor is dark, and every one of them is lighter than the
 * jacket so identity still reads from the top down. Held between 0.08 and
 * 0.20 saturation where this world's four state hues run 0.53-0.61, and the
 * wedges are avoided by hue as well: nothing here is within 25deg of `--cool`
 * at 198deg or `--honey` at 25deg, the one green is a grey-green at 164deg
 * and 0.14 saturation against the jade's 151deg and 0.61, and the one warm
 * neutral is held at 0.15 saturation against honey's 0.59, a 3.9x gap.
 *
 * MEASURED AGAINST THREE VALUE REGISTERS. Every one clears 4.0:1 on all five
 * surfaces a pawn can stand on — the flags, the mosaic runner, a chamber
 * floor, a lit chamber floor and the stylobate — worst case 4.34:1 against
 * the runner, which is the lightest of the eight and the binding one every
 * time in this world.
 */
const EXPEDITION_HATS = [
  '#a293b8', // heather
  '#8fa0b2', // slate
  '#aca68c', // limestone
  '#96a892', // sage
  '#b0929f', // mauve
  '#93aaa4', // verdigris
  '#a2a2b0', // ash
  '#ab9c92', // dust
]

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
  {
    id: 'forest',
    label: 'Enchanted Forest',
    blurb: 'A clearing of hollow stumps and carved benches, under a dappled canopy.',
    colorScheme: 'dark',
    // `--cream` in worlds/forest.css. Literal for the same reason the others
    // are: the browser needs it before a stylesheet exists.
    themeColor: '#0e1710',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the hollows at
    // y=14, so a world that raised its band would run the treeline behind
    // them.
    walkTop: 14,
    designs: WOODLAND,
    // One cast, deliberately, and the reasoning is Night Watch's rather than
    // the colony's. A clearing where the animals work the benches together is
    // the same claim the night deck makes: the agents live here. The obvious
    // second species would be will-o'-wisps — and that is exactly the one this
    // world may not have, because the wisp is already spoken for. It is what a
    // working slab lights up as, and a floor with wisps walking around on it
    // could not also use a wisp to mean BUSY.
    agentDesigns: null,
    layers: DEFAULT_LAYERS,
    palette: FOREST_COATS,
  },
  {
    id: 'underwater',
    label: 'Reef Station',
    blurb: 'Research domes on the seabed, under caustics from a surface far above.',
    colorScheme: 'dark',
    // `--cream` in worlds/underwater.css. Literal for the same reason the
    // others are: the browser needs it before a stylesheet exists.
    themeColor: '#071a24',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the domes at
    // y=14, so a world that raised its band would run the water column behind
    // them.
    walkTop: 14,
    designs: REEF,
    // One cast, and this world has a reason of its own on top of Night Watch's
    // and the Forest's. The obvious second species is a machine — an ROV, a
    // crawler, a manipulator unit — and every machine anybody draws underwater
    // has a lamp on the front of it. A small bright lamp walking about the
    // floor is precisely what this world may not have: the whole of Reef
    // Station's argument is that the only lit things down here are the desks
    // that are spending the budget. So the reef keeps one cast, and the agents
    // are the animals that live here.
    agentDesigns: null,
    layers: DEFAULT_LAYERS,
    palette: REEF_SCALES,
  },
  {
    id: 'alien',
    label: 'Alien Colony',
    blurb: 'Command modules on landing pads, under two moons and a ringed planet.',
    colorScheme: 'dark',
    // `--cream` in worlds/alien.css. Literal for the same reason the other
    // two are: the browser needs it before a stylesheet exists.
    themeColor: '#120b1f',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the modules
    // at y=14, so a world that raised its band would run the horizon behind
    // them.
    walkTop: 14,
    designs: COLONISTS,
    // The one world so far where the agents are a different species. See
    // SERVICE_ROBOTS above for why this is honest here and was not on the
    // night deck.
    agentDesigns: SERVICE_ROBOTS,
    layers: DEFAULT_LAYERS,
    palette: COLONY_HULLS,
  },
  {
    id: 'cloudcity',
    label: 'Cloud City',
    blurb: 'A sky harbour of platforms and pavilions, above the cloud line.',
    // THE FIRST WORLD SINCE PAPER OFFICE THAT IS LIGHT, and the only one of
    // the nine brighter than it. Which means the three overrides every dark
    // world needs — the two scrims, the chair's under-edge — are not needed
    // here at all: `--ink` still means "the mark on the page" AND still means
    // "a dark colour", because the page is pale. Phase 19's finding 2 is a
    // *dark*-world finding, and this is the world that proves it.
    colorScheme: 'light',
    // `--cream` in worlds/cloudcity.css. Literal for the same reason all the
    // others are: the browser needs it before a stylesheet exists.
    themeColor: '#e9f2fb',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the pavilions
    // at y=14, so a world that raised its band would run the sky behind them.
    walkTop: 14,
    designs: PILOTS,
    // The second world whose agents are a different species, and the reasoning
    // is the colony's rather than the night deck's: a harbour is a place
    // machines work and people arrive at. See SKY_DRONES above.
    agentDesigns: SKY_DRONES,
    layers: DEFAULT_LAYERS,
    palette: PILOT_JACKETS,
  },
  {
    id: 'arctic',
    label: 'Arctic Base',
    blurb: 'Cabins and antenna masts on packed snow, under a winter aurora.',
    // THE FIRST WORLD SPLIT DOWN THE MIDDLE. Cloud City is bright everywhere
    // and the three before it are dark everywhere; this one is a near-white
    // floor under a night sky, and the line between the two regimes is
    // `--walk-top`. It registers as light because the eight surfaces a word
    // can land on are all in the bright half — the band carries no word and is
    // not walkable. So `--ink` still means "the mark on the page" AND "a dark
    // colour" at once, and the three overrides every dark world needs (the two
    // scrims, the chair's under-edge) are not needed here, exactly as they
    // were not needed in the harbour.
    colorScheme: 'light',
    // `--cream` in worlds/arctic.css. Literal for the same reason all the
    // others are: the browser needs it before a stylesheet exists.
    themeColor: '#eef3f8',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the cabins at
    // y=14, so a world that raised its band would run the aurora behind them.
    walkTop: 14,
    designs: PARKA_TEAM,
    // The third world whose agents are a different species, and the argument
    // is the colony's rather than the night deck's: the research team are
    // visitors and the penguins live here, so an agent at a survey station is
    // visibly not one of the people watching it. See PENGUINS above.
    agentDesigns: PENGUINS,
    layers: DEFAULT_LAYERS,
    palette: PARKA_SHELLS,
  },
  {
    id: 'desert',
    label: 'Desert Outpost',
    blurb: 'Adobe outposts under shade canopies, on open sand at low sun.',
    // THE SECOND WORLD SPLIT AT `--walk-top`, and the split is Arctic Base's
    // with the reason changed: the ice is bright below and dark above because
    // it is night up there, and this is bright below and dark above because the
    // sun is BEHIND the dunes along the back of the floor. It registers as
    // light for exactly the reason the ice does — the eight surfaces a word can
    // land on are all in the bright half, the band carries no word and is not
    // walkable. So `--ink` still means "the mark on the page" AND "a dark
    // colour" at once, and the three overrides every dark world needs (the two
    // scrims, the chair's under-edge) are not needed here.
    colorScheme: 'light',
    // `--cream` in worlds/desert.css. Literal for the same reason all the
    // others are: the browser needs it before a stylesheet exists.
    themeColor: '#f8eddc',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the outposts at
    // y=14, so a world that raised its band would run the dunes behind them.
    walkTop: 14,
    designs: CARAVAN,
    // The fourth world whose agents are a different species, on Arctic Base's
    // argument rather than the colony's: the survey team are visitors and the
    // dune's animals live here. See DESERT_FAUNA above.
    agentDesigns: DESERT_FAUNA,
    layers: DEFAULT_LAYERS,
    palette: CARAVAN_CLOTH,
  },
  {
    id: 'ruins',
    label: 'Ancient Ruins',
    blurb: 'Pillared stone chambers under a carved frieze, lit by torches and by glyphs.',
    // THE FIRST DARK WORLD SINCE REEF STATION, and it is dark everywhere:
    // stone above the walk line and stone below it, with the only light
    // coming from the torches and — when something is happening — from the
    // glyphs. So `--ink` inverts and the five overrides every dark world
    // needs come back: the two scrims, the chair's under-edge, a world-local
    // `--sheet`, and the sprite rim held down to a lit edge. Phase 19's
    // finding 2, applied for the fifth time.
    colorScheme: 'dark',
    // `--cream` in worlds/ruins.css. Literal for the same reason all the
    // others are: the browser needs it before a stylesheet exists.
    themeColor: '#16130f',
    // Unchanged, and it has to be: ROOMS in components.jsx puts the chambers
    // at y=14, so a world that raised its band would run the carved wall
    // behind them.
    walkTop: 14,
    designs: EXPEDITION,
    // The fifth world whose agents are a different species, on the colony's
    // argument: a temple is a place its guardians work and its excavators
    // visit. See SENTINELS above.
    agentDesigns: SENTINELS,
    layers: DEFAULT_LAYERS,
    palette: EXPEDITION_HATS,
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

/* Half of a world change, in milliseconds.
 *
 * MUST match `--swap-ms` in styles.css. This decides when `data-world`
 * actually changes; that decides how long the veil takes to become opaque,
 * and a disagreement means the board changes in front of the viewer instead
 * of behind the fade. Same contract as WALK_MS/`.pawn` and
 * ENVELOPE_MS/`.envelope` in components.jsx. */
const SWAP_MS = 200

/* Whether the change should be faded or cut.
 *
 * Read at the moment of the swap rather than cached, because the preference
 * can be turned on while the page is open and the next swap has to honour it.
 * A browser without `matchMedia` gets the fade, which is the same answer it
 * gets for every other animation in the product. */
function prefersMotion() {
  try {
    return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return true
  }
}

/* Pick a world at random that is not the one already showing.
 *
 * Drawn from the other eight rather than from all nine and retried, because
 * "surprise me" that leaves you where you are is not a surprise, it is a
 * broken button — and a retry loop has no upper bound on how many times it
 * can draw the current world. */
export function randomWorldId(currentId) {
  const others = WORLDS.filter((entry) => entry.id !== currentId)
  if (!others.length) return currentId
  return others[Math.floor(Math.random() * others.length)].id
}

const WorldContext = createContext(null)

/** The active world, plus the setters the picker calls. */
export function useWorld() {
  return (
    useContext(WorldContext) ?? {
      world: PAPER_OFFICE,
      worlds: WORLDS,
      setWorld: () => {},
      surprise: () => {},
    }
  )
}

export function WorldProvider({ children }) {
  const [worldId, setWorldId] = useState(loadWorldId)
  /* Which half of the cross-fade is running: `out` is the veil rising over
   * the world you are leaving, `in` is it falling over the one you arrived
   * in, `null` is a settled board. */
  const [phase, setPhase] = useState(null)
  /* Where the fade is heading. A ref rather than state on purpose: clicking a
   * second world while the first swap is still running has to retarget the
   * *running* timer rather than start a competing one, and a ref is read at
   * the moment the timer fires. That is what makes arrowing through the
   * picker feel like flipping through worlds instead of queueing them. */
  const bound = useRef(null)
  /* `phase` again, readable from an event handler.
   *
   * `value` below is memoised on the world alone, deliberately: putting the
   * phase in its dependencies would hand every consumer a new context object
   * twice per swap and re-render the whole board mid-fade, which is exactly
   * the work a fade exists to hide. So the one thing `setWorld` needs to know
   * about the phase is mirrored into a ref instead. */
  const phaseRef = useRef(null)
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

  /* The veil reads this, and nothing else does. Kept off the React tree and
   * on `documentElement` for the same reason `data-world` is: the fade covers
   * the whole page, including the parts a route is not rendering. */
  useEffect(() => {
    const root = document.documentElement
    phaseRef.current = phase
    if (phase) root.dataset.swap = phase
    else delete root.dataset.swap
  }, [phase])

  /* The swap machine. Two ticks of SWAP_MS: the first ends by changing the
   * world under an opaque veil, the second by putting the veil away.
   *
   * The cleanup matters. Choosing a third world during the second tick sets
   * the phase back to `out`, which re-runs this effect, cancels the timer
   * that was about to settle the board and restarts the fade — so a run of
   * fast choices is one continuous dissolve rather than a stutter of them. */
  useEffect(() => {
    if (!phase) return undefined
    const timer = window.setTimeout(() => {
      if (phase === 'out') {
        setWorldId(bound.current ?? DEFAULT_WORLD_ID)
        setPhase('in')
      } else {
        setPhase(null)
      }
    }, SWAP_MS)
    return () => window.clearTimeout(timer)
  }, [phase])

  const value = useMemo(() => {
    const setWorld = (id) => {
      const next = worldFor(id)
      /* Picking the world already showing is a no-op, not a 400ms dissolve
       * back to where you started. Guarded only on a settled board: choosing
       * the current world *during* a fade to a different one is a genuine
       * change of mind and has to turn the fade around. */
      if (next.id === world.id && !phaseRef.current) return
      /* Persist the world we are heading for, not the fact that we are
       * fading towards it. A reload mid-fade lands on the new world with no
       * fade, which is right: the choice is made, the animation is only how
       * it was shown. */
      saveWorldId(next.id)
      if (!prefersMotion()) {
        bound.current = null
        setPhase(null)
        setWorldId(next.id)
        return
      }
      bound.current = next.id
      setPhase('out')
    }
    return {
      world,
      worlds: WORLDS,
      setWorld,
      /* Somewhere else, and never here. `world.id` rather than `bound.current`
       * so a second press during a fade is still measured against what is on
       * screen — pressing it twice quickly must not be able to land you back
       * where you started. */
      surprise: () => setWorld(randomWorldId(world.id)),
    }
  }, [world])

  return createElement(
    WorldContext.Provider,
    { value },
    children,
    /* Rendered here rather than in a route so it exists on the landing page
     * and behind the entry gate too — the world applies to all three, so the
     * fade has to as well. */
    createElement('div', { className: 'worldveil', key: 'veil', 'aria-hidden': 'true' }),
  )
}
