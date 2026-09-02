# Poster slides — dense consulting-style one-pagers

Use when one slide must carry the **whole argument spatially** — current pain → mechanism →
capabilities → outcomes — the way enterprise consulting and SI workshop decks do: numbered
stage panels, icon cards, semantic red/green colouring, outcome chips, a takeaway band. The
audience *studies* this slide (workshop, steering committee, reference architecture); it is
not a glance-and-move-on story beat. Read `references/diagrams/geometry.md` first for any
embedded node-edge cluster; this file owns the poster's layout system.

**Relationship to the density rules:** the poster is the deliberate exception to "one idea
per slide" — but it is not a licence to cram. Density is earned through *hierarchy and
repetition* (a few panel shapes, one card shape repeated, one chip shape repeated), and the
font floors still apply without exception: 14px is still the hard minimum for every label.
A deck is usually mostly normal slides with **1–3 posters at its heart**; do not turn every
slide into a poster.

## Build rule #1 — HTML owns layout, SVG owns relationships

A poster has 20–30 small components. Build the macro layout in **HTML (CSS grid/flex)**:
panels, cards, chips, badges, bands. HTML wraps text, stretches heights, and keeps font
sizes honest. Reach for SVG only where HTML cannot express the relationship:

- **Gap arrows** — a small inline chevron/arrow glyph between two columns or rows.
- **A connector underlay** — one absolutely-positioned `<svg>` behind a group of
  absolutely-pinned cards, when arrows must genuinely cross space (converge, fan, scatter).
- **An embedded cluster** — a true node-edge diagram (hub-and-spoke, mesh) living *inside
  one panel*, sized to that panel.

Never draw the entire slide as one big SVG. You lose text wrapping, the 14px floor slips
unnoticed as you shrink labels to fit, and `check_diagram.js` cannot police a poster it
cannot model. `assets/templates/corporate-light.html` is the worked implementation of
everything below — copy it rather than rebuilding these parts.

## The layout grammar

- **Columns are argument stages.** 3–5 macro columns, read left→right as the story:
  *challenge → mechanism → capabilities → outcomes*. Give stage panels a **circled number
  badge** (1, 2, 3…) so the reading order is explicit even at a glance.
- **The panel is the macro unit.** Rounded container (10–14px radius), tinted ~6–8% in its
  semantic tone, 1.5px border in the tone, headed by badge + bold title + optional one-line
  sub. Panels in one row stretch to **equal height** (CSS grid does this for free).
- **Between columns: one chevron arrow** at the vertical centre of the gap — a single glyph,
  not a drawn line. It says "then", not "data flows here".
- **Optional right rail: outcome chips.** A narrow column of compact cards, each a green
  check badge + a 2–4 word outcome. End the rail with one solid-fill card for the headline
  payoff if there is one.
- **Optional full-width bottom band** — either a *progression* (pain → mechanism → payoff,
  coloured red → blue → green with arrows) or a *KEY TAKEAWAY* strip (icon + one sentence).
  One band maximum, ~56–72px tall, and it must restate the slide, not add a new idea.
- **Title band on top** (see `references/pptx-template.md`): kicker `NN | SECTION NAME`,
  large white title in the band, logo right, and **one coloured framing sentence** centred
  directly under the band. The framing line is the thesis; the poster below proves it.

## Semantic colour — the consulting code

Colour encodes *meaning*, never decoration:

| Tone | Means | Typical use |
|---|---|---|
| red | current state, pain, risk | challenge panel, "without X" panel, warnings |
| green | target state, outcome, benefit | solution panel, outcome chips, takeaway |
| blue | process, mechanism, brand-neutral | the platform/core panel, step chips, framing line |
| orange | secondary system, ingestion, tooling | a supporting subsystem panel |

One tone per panel; cards and chips inside inherit it. Tint fills with
`color-mix(in srgb, <tone> 7%, #fff)` and keep card text dark ink on white — the tone lives
in borders, badges, icons and headings. A slide where every card is a different colour
reads as amateur; a slide where colour tracks the argument reads as engineered.

## Component vocabulary

The corporate-light template ships all of these as classes; snippets here show the shape.

**Numbered stage panel**

```html
<div class="panel t-red">
  <div class="phead"><span class="nbadge">1</span>
    <div><b>Current Challenge</b><i>why today's approach stalls</i></div></div>
  <!-- cards… -->
</div>
```

**Icon card** — the atomic unit: icon chip + bold term + one muted line.

```html
<div class="icard"><span class="ic"><svg><use href="#i-doc"/></svg></span>
  <div><b>Fragmented context</b><span>code, docs and tickets live apart</span></div></div>
```

**Outcome chip** — check badge + short claim; stack 4–6 in the rail.

```html
<div class="ocard"><span class="ock"><svg><use href="#i-check"/></svg></span>
  <div><b>Faster resolution</b><span>hours, not days</span></div></div>
```

**Chip flow** — a mini pipeline *inside* a panel (e.g. an evidence chain).

```html
<div class="chipflow">
  <span class="chip"><svg><use href="#i-edit"/></svg>Change</span><span class="carrow">→</span>
  <span class="chip"><svg><use href="#i-net"/></svg>Impacted</span><span class="carrow">→</span>
  <span class="chip"><svg><use href="#i-doc"/></svg>Evidence</span></div>
```

(The `→` here is a styled glyph inside a component, which is fine — the "no decorative
markers" rule is about prose.)

**Vertical mini-chain** — a sub-process as icon+label steps with small down-arrows
(`.vchain` / `.vstep`), for "A does: step → step → step" inside an architecture column.

**Progression band** — bottom strip: three `.tcell`s (label + one-line sub) coloured
red / blue / green, joined by arrow glyphs.

## Icons — one `<symbol>` set, no emoji

Icons are what make cards read as designed rather than listed. Define a single hidden
`<svg><defs>` of `<symbol viewBox="0 0 24 24">` line icons once, then instantiate with
`<use href="#i-name">`. Draw them as **stroke icons**: leave fill/stroke off the symbol
paths and style from outside — inherited properties cross the `<use>` boundary:

```css
.ic svg{width:20px;height:20px;fill:none;stroke:currentColor;
        stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
```

The icon chip (`.ic`) is a small rounded square tinted in the panel's tone with the icon in
the tone colour. Keep every icon on the same 24-grid and stroke width — mixed icon weights
are instantly visible. The template ships ~18 (doc, db, code, gear, search, person, team,
bug, shield, clipboard, target, network, chip, chart, cycle, check, warn, layers); draw a
missing one from the same primitives (2–4 strokes) rather than importing art or emoji.

## Embedded clusters — recipes

Read `geometry.md`'s **"Connector styles carry meaning"** first: every recipe below leans on
it. Radial spokes and mesh links are diagonal *by design* — the checker would flag them, so
give these SVGs a non-`graph` class and verify by **screenshot** (same doctrine as
`composition.md`'s radial). A cluster that IS orthogonal rects-and-arrows can still use
`svg.graph` and get `check_diagram.js` coverage — prefer that when it fits. Working
implementations of all of these live in `assets/templates/corporate-light.html` (slides 3–5).

**Hub-and-spoke (source map).** Centre emblem = filled tone circle Ø 48–56 with a white
glyph, caption in caps beneath it. Satellites are icon chips whose **centres sit ON a dashed
orbit ring** (the ellipse passes through them — chips floating off the ring read as
misplaced), at `θ = −90° + i·360/n`, first chip at 12 o'clock; size the ring so the widest
chip clears the panel edge by ≥12px. Spokes are **dotted hub→chip with no arrowheads**
(traceability, not flow), drawn *before* emblem and chips so both ends hide cleanly under
them. Add 4–8 **accent dots** (r 2–3, satellite tones, ~70% opacity) sitting on the ring in
the gaps between chips — they whisper "more members exist" without claiming any. Animate:
ring draws → spokes draw → hub pops → chips pop clockwise from 12 o'clock, 60–90ms apart.

**Knowledge mesh.** Three visual layers in strict contrast order: **labelled entity chips**
(the information — full contrast, ≥14px) over **small tone-coloured dots** (scale texture,
r≈2, ~40–60% opacity) over **hairline grey links** (connectivity, lowest contrast). Centre
emblem dominant; 5–7 chips ringed around it; links centre↔chip plus a few chip↔chip; dots
scattered between chips, roughly annular, never touching text. Optionally annotate **one**
emblematic link with a small-caps caption pair (e.g. `LINKS_TO` / `LINKED_FROM` on a dashed
two-way pair) — one, not every link, or the mesh becomes a schema diagram. Animate: links
fade → chips pop → dots fade in last.

**Chaos scatter (the "without" panel).** Cards in a plain orthogonal grid (2+1+2 works) —
chaos never lives in the card layout, only in the links (see geometry.md). Pin the cards
with absolute positions inside a fixed-size `position:relative` zone and draw one `<svg>`
underlay (`position:absolute; inset:0`) behind them: **dashed links with arrowheads at both
ends** that deliberately cross, plus a red `?` at 2–3 crossing midpoints. Route each link so
its arrowheads land in *visible* gaps between cards (a marker hidden under a card is wasted).
5–7 links maximum — past that it reads as scribble, not chaos.

**Converge – hub – fan (the "with" panel).** Source chips in one grid row; a **solid tone
arrow drops from each chip** — reuse the same `grid-template-columns` for the arrow row so
every arrow sits exactly under its chip — into a full-width hub bar (emblem + name + a
sub-caption of 3–4 middot-separated qualities); a second aligned arrow row fans out to the
consumer chips. Every arrow solid, one-way, tone-coloured: the deliberate stylistic opposite
of the chaos panel across the slide.

**Vertical track chains.** One sub-panel per track, its header (`A · Document track`) in the
track tone; steps are icon + 14px label rows with short (8–12px) down-arrows in the track
tone between them; 3–5 steps per track. Two tracks side by side or stacked read as "parallel
understanding" — give them different tones (e.g. orange docs, blue code) so the parallel is
visible at a glance.

**Transition glyphs between stage panels.** Pick ONE glyph per slide — fat filled block
arrows or outline chevrons — and repeat it in every gap; mixing both reads as indecision.
When a transition moves the argument between tones, gradient-fill the fat arrow source-tone
→ target-tone (see geometry.md); the progression band's red→blue→green arrows should always
use those gradients.

## Poster ceilings (replace the per-slide table, floors still apply)

- ≤ **5 macro zones** (columns + rail), plus at most one bottom band.
- ≤ **5 cards per panel**; card description ≤ 2 lines at 14px; card title ≤ 3 words bold.
- ≤ **~30 atoms** total (cards + chips + cluster nodes). Past that, split into two posters.
- Gaps consistent everywhere (12–16px); panel padding 12–16px; nothing within 20px of the
  canvas bottom.
- Typography scale inside the poster: panel title 18–20px/800, card title 15–16px/700,
  descriptions and chips 14px, kicker 13–14px caps. **Nothing below 14px, ever** — if it
  does not fit, remove a card or shorten a description; never shrink.

## Animation — reveal the argument, not confetti

Reveal in **argument order**: panel 1, its cards (staggered ~60–80ms), gap arrow, panel 2…
then the rail, then the bottom band. Put `.r` on the macro zones for the global stagger and
drive inner-card delays with a per-card `transition-delay` var. An embedded cluster
animates on slide activation like any diagram (`.gn` pop / `.ge` draw, or its orbit
classes). Keep the full sequence under ~2.5s — a workshop slide is revisited; slow reveals
grate on the second pass.

## Verify — a poster hides its own failures

- `scripts/shot.sh deck.html <n>` — **mandatory for every poster slide.** Wrapped labels,
  an overflowing rail, a card pushed past the canvas bottom are invisible in source. The
  canvas hard-clips at 720px, so overflow does not scroll — it silently disappears.
- `node scripts/check_diagram.js deck.html` still validates any `svg.graph` you embedded.
- Check the screenshot against the ceilings: equal panel heights, aligned card rows,
  consistent gaps, one tone per panel, no label below 14px.

## Common mistakes

- Building the whole slide as one giant SVG (see build rule #1).
- Rainbow cards — colour must track the argument, one tone per panel.
- Emoji or mixed-weight icon art instead of the single stroke-icon set.
- A bottom band that introduces a *new* idea instead of restating the slide.
- Shrinking text below 14px to make a fifth card fit — cut the card instead.
- Equal-height panels broken by one overstuffed column (move a card, or thin the content).
- Skipping the screenshot because the HTML "looks right" — posters fail in render, not in
  source.
