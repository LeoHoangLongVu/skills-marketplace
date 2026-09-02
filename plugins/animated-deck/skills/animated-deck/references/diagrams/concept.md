# Concept diagrams — before/after, blast-radius, state transitions, shallow trees

Use for **comparisons and relationships that are not a left-to-right flow**: a before/after
contrast, a blast-radius (what a change touches), a small state machine, or a shallow
hierarchy/tree. Read `references/diagrams/geometry.md` first.

## Before / after

Two panels side by side, equal size, one shared baseline. Left = current/old, right =
new/improved; give each a coloured top accent (e.g. red vs green) and a short header. Put
the contrast metric between or below them (a 3-cell `calc` strip works well: old → saved →
new). No arrows are needed; the side-by-side *is* the comparison. If you do connect them,
one horizontal arrow between the panels labelled with the transformation.

- Keep both panels identical in width, height and inner padding so the eye compares content,
  not box sizes.

## Blast-radius (impact rings)

A focal node in the centre; concentric rings (or tiers of boxes) outward show first-order,
second-order, … impact. Draw rings as `<circle>` with increasing radius and decreasing
opacity, or as columns of boxes at increasing distance with arrows from the focus outward.
Animate rings expanding (scale or radius) on slide activation. Keep the focus visually
dominant; dimmed outer nodes must not overlap the focus (push them to the edges).

## State transitions

Boxes are states; arrows are transitions, each **labelled with the trigger** ("on submit",
"timeout"). A self-loop is a small rounded arrow returning to the same box (label above it).
Lay states left→right for a linear lifecycle, or around a ring for a cycle. Because
transitions can go both directions between two states, use the request/response idiom (two
separate arrows at different `y`) rather than one double-headed line.

## Shallow trees / hierarchy

A root at the top (or left), children below, one level or two. Parent → child is a single
arrow; siblings are equally spaced under the parent (a comb works: trunk under the parent,
equal stubs down to each child). Keep it shallow — deep trees do not fit 1280×720; if it is
deep, show the top two levels and summarise the rest in a caption. Do not wrap a parent's
children in one box; draw each child standalone with its own arrow.

## Decision tree

A tree whose internal nodes are **tests** and whose branches are **answers** — "Exact field?
→ yes/no". Two things distinguish it from a plain hierarchy: diamond decision nodes and a
label on every branch.

- **Decision nodes are diamonds** (`<polygon points="cx,cy-h cx+w,cy cx,cy+h cx-w,cy">`),
  outcomes are rounded rects. A diamond is not a rect, so `check_diagram.js` cannot validate
  it as a node or as an arrow target — keep it inside a `.gn` group for the pop-in and verify
  its text fit and tip landings by screenshot.
- **Keep arrowheads off edges that end on a diamond.** Because the checker flags any
  arrowhead that does not land on a rect, route decision→decision edges as plain elbows into
  the diamond (no marker) and reserve arrowheads for edges into outcome rects. This keeps the
  slide checker-green *and* reads correctly — the flow is obvious from the cascade.
- **Label both branches** ("yes"/"no", or the value range) and clear the label of every leg
  per `geometry.md`'s label rule. A binary cascade lays out cleanly as a staircase: each
  test's "yes" goes sideways to an outcome, its "no" steps down to the next test, and the
  final test's "no" is the fallback outcome. Colour answers consistently (e.g. yes-edges and
  their outcomes green) so the eye follows one verdict at a time.

## Matrix / 2×2 quadrant

Two axes crossing at the centre (effort × impact, reach × difficulty). Draw the two axes as
plain lines (no arrowheads, or a single arrowhead at each far end) with an axis label at
each end. Place items as small boxes or dots in the quadrant their values dictate; add a
faint quadrant caption in each corner ("quick wins", "money pit"). No connectors between
items. Keep the cross centred and the four quadrants equal in size.

## Funnel

Stages that narrow (visitors → signups → trials → paid). Draw each stage as a horizontal bar
**centred on the same x**, each narrower than the one above, top→bottom, with the stage name
and its value/percentage inside. A single vertical arrow between bars (or none — the
narrowing is the message). Keep the centre-line and the vertical step between bars constant.

## Venn / set overlap

Two or three translucent circles (`<circle>` with `fill-opacity`), overlapping where sets
share members. Label each circle's unique region and the intersection. No arrows. The
checker does not model circles, so verify text fit by screenshot; keep labels inside their
region and the intersection label centred on the overlap.

## Connector idioms

- before/after: usually none (side-by-side); at most one labelled transform arrow.
- blast-radius: arrows radiate from the focus; or rings with no arrows.
- state machine: one arrow per transition, each trigger-labelled; bidirectional → two arrows.
- tree: parent→children as a comb (equal stubs), each child a standalone box.

## Checklist

- `node scripts/check_diagram.js deck.html` → `OK`.
- Before/after panels equal in size and padding; comparison metric present.
- Rings/children equally spaced; focus dominant and unobscured.
- Every transition/edge labelled where it adds meaning; tips on borders; professional register.
