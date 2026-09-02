# Flow diagrams — pipelines, dataflow, architecture

Use for **directed flow through stages**: a processing pipeline, a data platform, a system
architecture (e.g. an ingest → store → serve flow). Each stage is one or more standalone
boxes; edges show what moves between them. Read `references/diagrams/geometry.md` first —
this file only adds the layout patterns specific to flows.

Scope check: this works for a hand-curated DAG of up to ~15 boxes. For a dense mesh,
many-to-many graph, or anything needing automatic layout, generate it with Graphviz
(`dot`) and embed the result instead — manual SVG placement does not scale past that.

## Layout patterns

**1. Single row (≤5 stages).** Boxes left→right at one shared `y`; straight horizontal
arrows between adjacent stages. The cleanest option — use it whenever the stages fit the
1120-wide canvas (~180–220px per box + gaps).

**2. Snake / boustrophedon (6+ stages).** When a single row overflows, wrap: top row flows
left→right, bottom row flows right→left, joined by one vertical connector on the side where
they meet. Lay each stage's boxes so cross-row connectors stay orthogonal (a single vertical
arrow, or an elbow onto a specific inner box). Keep stage **lane-labels** (plain text, no
enclosing rectangle) above each group.

**3. Two parallel bands (Lambda / speed + batch).** A spine of shared stages down the
middle, a real-time band along the top and a batch band along the bottom, both fed from the
same hub and merging downstream. Place the speed box and batch box at mirrored `y` so the
fork from the hub is two symmetric elbows and the two bands never cross. (This is the Uber
data-flow pattern: `Kafka → {Flink, Spark} → {Pinot, Hive}`, both → `Feature store →
Michelangelo → products`.)

## Connector idioms

- **Stage → stage:** straight horizontal arrow on the shared row `y`, tip on the next box's
  left border.
- **Fork (one source → several stores/branches):** separate arrows, one per target, each
  landing on its own box. If the targets stack vertically, use a comb (trunk + equal stubs)
  per `geometry.md`. Do not wrap the targets in one box and point a single arrow at it.
- **Join (several sources → one box):** separate arrows entering the target on *different*
  points of its border (e.g. two arrows into the top edge at well-separated x), so the
  arrowheads do not collide.
- **Cross-row / different-height target:** orthogonal elbow `<path>` onto the inner box.
- **Backbone into a multi-box stage:** point the arrow at the stage's *entry* box (its first
  node), not at a wrapper — elbow up/down to reach it if needed.

## Worked skeleton (single row, fork + join)

```
ingest ──parse──▶ build-index ──▶ chunks ──embed──▶ [BM25]
                                     │                  └──┐
                                     └──derive──▶ props    ├─▶ hybrid ──▶ search
                                                  [dense]──┘
```

- All stage→stage arrows horizontal on the row centre-line.
- `chunks → BM25` and `chunks → dense` is a fork: two arrows to two standalone boxes.
- `BM25 → hybrid` and `dense → hybrid` is a join: two arrows onto `hybrid`'s top edge at two
  separated x positions.
- Label only where it adds meaning and the gap allows ("embed", "derive"); leave obvious
  internal forks unlabelled rather than cramming a caption.

## More flow patterns

**Layered stack** (tech stack, OSI-style, architecture tiers). Full-width horizontal bands
stacked top→bottom, one per layer, each labelled; the topmost is the entry/UI layer, the
bottom the foundation. Keep all bands the same height and inner padding. Show dependency
with a single vertical arrow down the side ("calls" / "depends on") rather than an arrow per
band. Place sub-components as standalone boxes *inside* a band (the band then reads as a
container — the checker allows the nesting).

**Cycle / feedback loop** (PDCA, retrain loop, control loop). Place the stages at the
corners of a rectangle and run each arrow *along a side*, so the loop is built entirely from
horizontal and vertical segments: top edge left→right, right edge top→bottom, bottom edge
right→left, left edge bottom→top. This keeps a cyclic process fully orthogonal — no arcs, no
diagonals. Label each transition on its side. (Three stages → an equilateral layout needs
diagonals; prefer four, or accept clearly-symmetric diagonals per the geometry guide.)

**Cloud / system architecture with nested groups** (a vendor reference architecture: a
CI/CD pipeline feeding grouped deployment targets, with a monitoring/insight group and a
feedback loop). This is the most container-heavy flow; it is in scope as long as you keep
it orthogonal and let the checker police the nesting.

- **Nested labelled containers.** A group box may hold sub-group boxes which hold service
  boxes (e.g. `DEPLOYMENT` ▸ `PRODUCTION` / `STAGING` ▸ `App Services` / `VMs`). Put each
  group's name as a small caption at its top-left, inset from the corner. Keep a consistent
  inner padding at every nesting level (~16–20px) so the levels read as deliberate. The
  checker treats *any* box that encloses another as a container — it skips overlap and
  vertical-centring for it — so nesting is free; just make sure inner boxes never touch the
  container edge (they would look cramped and may trip `PADDING` on their own text).
- **Point arrows at the right granularity.** An arrow for "deploy to the whole environment"
  lands on the *outer container's* border; an arrow to one specific service lands on that
  service box. Do not point at a container when you mean one inner box, and vice-versa.
- **Side inputs.** Secondary sources that feed one stage (a key vault, an artifact feed) sit
  above the spine and drop in with a short vertical or elbow arrow onto *that stage's* top
  edge — not onto the whole pipeline. Space their landing points apart so the arrowheads do
  not collide.
- **Feedback / monitoring loops.** A return edge (operator/monitoring → developer) is drawn
  with `stroke-dasharray` to read as "asynchronous / out-of-band", and routed as an
  orthogonal elbow along the slide's bottom (or top) margin so it never crosses the spine.
  It still lands its arrowhead on a real box border like any other edge.
- **Icons are optional and never brand art.** The node is a labelled box. If you want a
  visual hint, draw a small monochrome geometric glyph (rounded square, circle, triangle)
  in the node's top-left from SVG primitives, or embed a supplied inline icon `<svg>` inside
  the node `<g>`. Do not paste copyrighted vendor logos and do not use emoji; the product
  name as text is enough and stays professional.

**Swimlanes** (a process that crosses actors/systems). Stack horizontal lanes, one per
actor, with the actor name in a left-hand label column; the process flows left→right and an
arrow crosses into another lane (vertical segment) when the actor handchanges. Keep step
boxes aligned on a shared row inside each lane, and the lane dividers as faint full-width
lines.

## Checklist (run before delivering)

- `node scripts/check_diagram.js deck.html` → `OK` for the diagram slide.
- Every box: equal 4-side padding, equal sibling gaps.
- Every arrowhead lands on a box border (no floating tips), right-angle or clean elbow.
- Fans/joins drawn as separate arrows / combs — no wrapper hiding edges, no diagonal spray.
- Captions clear of lines, elbows and boxes. Professional register; product names verbatim.
