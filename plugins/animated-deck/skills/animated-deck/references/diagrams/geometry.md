# Diagram geometry — universal rules

Every diagram family (flow, interaction, concept) obeys these. They are where a diagram
reads as *polished* vs *amateur*. The source can look fine and still render wrong, so after
laying any diagram out, **run the checker and look at a screenshot** — do not eyeball:

```bash
node scripts/check_diagram.js deck.html     # PADDING / VCENTER / OVERLAP / TIP / LABEL
scripts/shot.sh deck.html <n>                # render slide n to PNG and inspect
```

The checker is the contract for everything below. If it reports `OK` for a slide and the
PNG looks right, the geometry is sound.

## Mechanics (wired into the template CSS)

- **Nodes** `.gn` pop in (`scale .6→1`) using `transform-box:fill-box` so they scale *in
  place*; without it an SVG `<g>` scales from the origin and flies in from the corner.
  Stagger reveals with inline `style="animation-delay:.Ns"`.
- **Edges** `.ge` draw themselves: put `pathLength="1"` on the `<line>`/`<path>`; the CSS
  animates `stroke-dashoffset` 1→0, so you never compute real path lengths.
- Everything is gated on `.slide.active`, so the animation **replays** on every visit.
  Animate on activation, never on page-load.

## Boxes

- **Equal padding on all four sides.** Text has the same gap to top, bottom, left and right
  — never crammed against one side. Use one consistent line-height across boxes and
  vertically centre the text block. Remember a text `y` is the *baseline* (~0.7·font-size
  below the visual top), so naive centring drifts low. Keep ≥14px horizontal padding. The
  checker flags `PADDING` (<14px) and `VCENTER` (top/bottom gap differ >10px).
- **Equal spacing between siblings.** Three boxes in a row → equal gaps between them and to
  the frame. Two siblings at distance D from a hub → the third at D too.
- **Equalise the GAPS, not the pitch — especially when boxes differ in width.** A chain of
  boxes with different widths (e.g. a 200-wide source, a 210 gateway, a 260 core, a 190 db)
  laid out by eye ends up with uneven edge-to-edge gaps (80px here, 30px there), which reads
  as sloppy even though each box looks fine. Compute it: with the row spanning `x0..x1`, the
  gap is `g = (x1 - x0 - Σ box widths) / (N - 1)`; place box *i* at
  `x0 + Σ(previous widths) + i·g`. Then every gap is identical and the arrows between boxes
  are the same length. Verify by checking consecutive `rightEdge → nextLeftEdge` distances are
  equal.
- **Don't overlap.** Two node boxes must not intersect (`OVERLAP`). A container that
  *encloses* children is not an overlap — that is intentional nesting and the checker
  allows it.

## Connectors

- **Endpoints land exactly on the *target box's* border.** A rect `x,y,w,h` has right-edge
  `x+w`, left-edge `x`, vertical-centre `y+h/2`. The arrowhead marker tip sits at the
  endpoint (`refX=7` on a 9-wide marker), so put the endpoint *on* the border. Compute it
  from the box you are actually pointing at — a recurring bug is an endpoint left from an
  earlier layout (a removed wrapper, a resized box) so the tip floats 10–20px short. The
  checker's `TIP` rule catches every floating arrowhead; fix until all land within ~1px.
- **Enter a box well inside its edge, not at the corner.** For a vertical arrow into a
  horizontal edge, land ~25–40px in from the box's left/right corner (past the corner
  radius), not 2–5px where it looks like it is slipping off. Size boxes large enough that
  their connection points are comfortably interior.
- **Prefer right angles.** A horizontal line into a vertical edge (or vice-versa) reads as
  structure; a slightly-off diagonal reads as a mistake. Align the two boxes' centres, or
  pick a shared y for a row / shared x for a column, so the line is *truly* H or V.
- **Use an elbow to reach an inner box at a different height.** When the target's centre
  does not line up with the source, route an orthogonal elbow `<path d="M.. H.. V.. H..">`
  (all right-angle legs) onto its border, rather than a diagonal or an arrow that stops at a
  wrapper edge. Set `fill="none" pathLength="1"` so it still draws itself.
- **When a true right angle is impossible** (a hub fanning to targets at different heights
  without room to elbow), make the diagonal clearly intentional and symmetric, not
  nearly-straight.

## Fans, joins, and wrappers (this is where information gets lost)

- **One arrow per *pair*, but never drop a real relationship.** Collapse only *duplicate*
  parallel arrows between the same two boxes. A genuine fan-out (one source → N distinct
  targets) or fan-in (N sources → one target) carries real information — each edge is a
  different relationship and must survive. Do not delete edges to chase a "one inbound
  arrow" ideal; that silently erases meaning.
- **Draw a fan as an orthogonal comb (bus), not a diagonal spray.** Run one shared **trunk**
  line in the gap beside the target group; connect the hub to it with a short right-angle
  **feeder**; branch off equal-length, equally-spaced **stubs**, one arrowhead per target.
  Fan-in is the mirror (stubs merge into the trunk, one arrowhead into the target).
- **Several inputs converging on one box → merge them into a bus, do not draw a separate
  crooked elbow per input.** When two or more sources feed a single (often narrow) target —
  e.g. an Artifacts box *and* a Key Vault box both feeding one CI stage — two independent
  doglegs look kinked (one jogs far sideways, the other barely). Instead: drop a short
  **feeder** straight down from each source, join them with one horizontal **bus** line, and
  send a *single* arrow from the **bus midpoint** into the target. Centre the whole thing on
  the target: place the sources symmetrically about the target's centre-x so the feeders'
  midpoint, the bus midpoint, and the drop arrow all sit on the target centre (e.g. sources
  at x=504 and x=674 → midpoint 589 → drop at 589 = the target's centre). The bus reads as
  "these inputs feed this stage", uses only right angles, and the lone arrowhead lands dead
  centre on the target border.
- **The feeder must meet the trunk at the trunk's *midpoint*, collinear with the hub's
  centre.** If the hub's centre-line enters the trunk above or below its middle, the comb
  looks lopsided even though every stub is correct. Arrange the targets *symmetrically about
  the hub's centre* so the middle stub (for an odd count) sits exactly on the hub centre-line
  and the trunk is centred on it — e.g. for a hub at cy=210 fanning to three targets, place
  them at 120 / 210 / 300, not 126 / 216 / 306. Then feeder, trunk-centre and middle stub
  are one straight line. (For an even count, centre the trunk on the gap between the two
  middle stubs so the feeder still meets it at the midpoint.)
- **Prefer standalone boxes with their own arrows over a big wrapper rectangle.** Wrapping a
  group in one rounded rect and pointing a single arrow at the wrapper hides *which* inner
  box connects and erases the real edges. Draw sub-nodes as separate boxes, point a separate
  arrow at each, and use a light **text lane-label** (not an enclosing rectangle) to name
  the stage. Reserve a wrapper only when the group is genuinely addressed as one unit.

## Connector styles carry meaning

Beyond geometry, the *style* of a connector is a semantic channel — professional decks use
it deliberately, and mixing styles at random reads as noise. The grammar:

| Style | Means | Typical use |
|---|---|---|
| solid line, single arrowhead | managed, directional flow | data/control moving between stages |
| dashed line, single arrowhead | out-of-band / asynchronous | feedback loops, monitoring, background generation |
| dashed or dotted, **no** arrowhead | membership / traceability | hub spokes, "belongs to", metadata links |
| dashed, arrowheads **both ends**, "?" at the midpoint | unmanaged mutual dependency | the "before/chaos" side of a contrast slide |
| hairline, low contrast, no arrowhead | atmosphere / connectivity texture | mesh backgrounds behind labelled chips |

Two corollaries. First, a contrast slide argues through line style: the "without" panel's
dashed bidirectional tangle against the "with" panel's solid one-way arrows carries the
argument before a single label is read — keep the two vocabularies strictly apart, never a
solid arrow on the chaos side or a dashed tangle on the ordered side. Second, **chaos lives
only in the connectors**: the cards under a chaotic tangle stay orthogonally aligned and
evenly spaced. Misaligned boxes read as sloppy authorship; crossing dashed links read as the
system's problem — which is exactly the intended message.

A transition between adjacent stages that also changes tone (a red stage handing off to a
blue one) may use a short fat arrow filled with a **linear gradient from the source tone to
the target tone** — define one gradient per gap in `<defs>`. Used in a bottom progression
band, the gradient arrows make it read as one continuous transformation rather than three
unrelated cells.

## Labels

- **Label arrows where it adds meaning, and keep the caption clear of *both* the line and
  every box.** A caption ("delegate query", "returns ~1k") names what flows. It must sit in
  empty space — not on the stroke, not on the arrowhead, not over a node box (including ones
  it passes near). The checker's `LABEL` rule catches all three. Three failure modes:
  - **Into a box.** A caption centred on a connector entering a box is wider than the gap and
    bleeds in. Estimate width (≈0.6·font-size per char), keep its whole extent inside the
    open gap, place it on the *source* side; if it does not fit, shorten it. If even a short
    caption cannot clear a tight gap, drop it — the box names carry the meaning.
  - **On a diagonal.** Offset perpendicular to the stroke by ≥14px to one side.
  - **On an elbow.** An elbow has 2–3 legs; the caption must clear *every* leg (≥8–10px),
    not just the one it sits above. The safe spot is the open quadrant on the far side of the
    first leg from the bend.

## Language inside diagrams

Professional register, same as slide prose: no emoji or decorative markers (`▶ ✓ ✕ →`) in
captions or node text. Keep code, identifiers, file paths, product names, and domain terms
verbatim (`Apache Kafka`, `bge-m3`, `spec_rag.sh`, `項目名`) — translate prose, never tokens.
