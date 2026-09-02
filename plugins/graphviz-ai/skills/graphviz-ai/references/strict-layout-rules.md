# Strict Layout Rules — hard-constraint diagrams

The user's standing rule set for architecture diagrams (first stated 2026-07 for the
KM3 bug-stack diagram; treat as the default whenever they ask for "the rules"):

| # | Rule |
|---|------|
| R1 | Arrows are straight axis-parallel segments only — no curves, no diagonals |
| R2 | Arrows meet containers at right angles |
| R3 | Nothing overlaps or passes through another element (nodes, labels, clusters) |
| R4 | The ONLY allowed crossings are arrow-with-arrow — and each is drawn as a HOP (a small semicircular bridge where the horizontal wire arcs over the vertical one), so a crossing never reads as a junction. The hand-routed generator does this automatically; on by default (`"hops": true`, `"hop_radius": 6`) |
| R5 | Arrows attach at the CENTER of a container side; a side with multiple arrows centers the GROUP on that side, arrows stay separated |
| R6 | Parallel arrows keep clear corridor spacing (≥12px between parallel runs) — **and 0px apart (exactly collinear) is the worst case of this, not an exemption**: two edges that run the same line for any real stretch render as one merged arrow. See "Same bend level, different destinations" below for the authoring pitfall this actually comes from |
| R7 | The final segment into the arrowhead is long enough (≥24px) that the last right-angle bend stays visually distinct from the tip — a bend hugging the head reads as a diagonal |
| R8 | An arrow never sits ON (or hugs) a component border — no segment may run parallel to, and overlap, a **node or cluster** edge, or it merges into the box outline and reads as part of the frame. Clearance ≥4px (`border_clear`). Perpendicular attachment is unaffected (an endpoint on the border overlaps it by zero) |
| R9 | Minimum readable text: every label renders at ≥ `min_font` px (default **14**) — smaller text is the standing review complaint (unreadable when projected or pasted into a doc). The audit flags any node whose lines don't FIT at that size (width ≈0.58em/char, 0.62 bold; height = lines×1.3em+10) — the fix is a wider/taller node or a shorter label, **never a smaller font**. Chip and port spacing scale from the same knob. Legacy specs authored pre-R9 may pin `"min_font": 10` explicitly. **To make text LOOK bigger: hold the canvas and raise `min_font`** (bigger text on the same paper → R9 tells you which nodes must widen → re-layout). Scaling the page together with the font is a visual no-op — proportions are unchanged, only the nominal number moves. **On a single slide, nominal pt is a DENSITY property**: ≈ slide_pt_width ÷ (canvas_px/min_font_px) — lowering min_font shrinks the canvas with it and lands at the SAME nominal. A wall-chart spec (~2500px) reads ~6pt on one slide no matter what; slide-readable (≥10pt) needs a separate CONDENSED variant spec: 2-line nodes, 1-2-word chips, merge node groups (e.g. 4 engines → one list node), aspect ≈ 16:9 (~1500×840px @ min_font 16 → ~10pt). Keep both specs |
| R10 | Component borders never touch or crowd (added 2026-08-11): every pair of components — node↔node, node↔cluster, cluster↔cluster — keeps ≥ `component_clear` px (default **12**) between borders. Containment is allowed (that's what clusters are for), but the contained component's **inner margins** must respect the same clearance; a node glued to its cluster frame reads as part of the frame. Grid tip: with 70px-tall nodes on a 5px grid, a 20px inner margin means cluster borders land on ×5 coordinates — budget cluster boxes 20px outside their outermost nodes |

## Decision tree — which tool can honor which rules

- **R1, R2, R4, R6 only** (no center-port rule): graphviz `splines=ortho` works.
  Required attrs: `splines=ortho, esep="+14", nodesep≥0.65, ranksep≥0.7, overlap=false,
  compound=true, newrank=true`. BUT edge labels are broken under ortho (see below).
  **Caveat: graphviz cannot draw the R4 HOP bridges** — it renders crossings as plain
  "+" junctions. If the user wants hops (line-jumps) at crossings, ortho can't do it;
  use the hand-routed SVG generator (`scripts/strict_svg_diagram.py`, hops on by default).
- **R5 present** (center / group-centered ports): **graphviz cannot do it — at all.**
  Probe-verified on graphviz 2.43: with `splines=ortho`, compass ports (`a:e -> b:w`)
  AND html-cell ports (`x:p1:e`) are silently ignored; worse, edges clip INTO the node
  and terminate at its center (arrowhead on top of the label). There is no dot-engine
  path to R5. Go straight to the hand-routed SVG generator:
  `scripts/strict_svg_diagram.py`.

## Ortho mode facts (when staying in graphviz)

- **Edge labels overlap nodes under ortho** — `xlabel` placement is naive. Robust
  pattern = **mid label nodes**: replace `a -> b [label="X"]` with
  `a -> m [dir=none]; m -> b;` where `m` is a borderless white-filled box
  (`fontsize=8.5, penwidth=0, margin="0.04,0.02"`), pinned into its own
  `{rank=same;...}` column between the endpoint columns. Short xlabels survive only
  on short same-rank vertical edges.
- The graphviz_master validator regenerates a `_fixed` copy with house defaults that
  will strip your mandatory graph attrs — ignore the `_fixed` file, ship your own.
  Its ratio gate is w/h ≤ 3.0; tune `nodesep`/`ranksep` to pass, never `ratio=`.

## Hand-routed SVG workflow (the R5 path)

1. **Node placement**: run the LayoutPlanner (deterministic, no API) or reuse its
   columnar plan mentally — nodes in rank columns, clusters as background rects.
   **Budget spacing, don't inflate it** — readers read big gaps as sloppy. The gap
   between two rows only needs: 22px chip clearance above a wire + 15px per corridor
   lane running between the rows + 24px tip run (R7). That's ~90–130px between node
   borders for a 2-lane gap, not 200+. Same for canvas margins: trim dead strips
   (audit exit 0 is unaffected by compaction — re-run it after).
2. **Author a spec JSON** (schema in the script docstring): nodes with center+size,
   edges as explicit Manhattan waypoint lists with `from`/`to` ids, one optional
   label chip per edge with an explicit `label_at`.
3. **Port math** (R5): a side with one arrow attaches at the side's exact center.
   A side with k arrows uses offsets symmetric about the center (e.g. ±12, or
   {−22, 0, +22}); when a straight run to the peer's center port forces an
   off-center port, move the NODE's center (shift cy/cx) so the group mean lands
   back on the side center — re-center the node, don't bend the arrow.
4. **Corridors** (R6+R7): give every long vertical/horizontal run its own lane
   coordinate, ≥12–15px from any parallel neighbor. Budget lanes up front
   (x=320, 335, 350… / y-lanes between rank rows). Keep the LAST lane ≥24px away
   from the target's border so the final run into the arrowhead stays long (R7) —
   when several corridors fan into one port group, put the innermost corridor
   ≥24px out and step outward from there.
5. **Render + audit**: `python3 scripts/strict_svg_diagram.py spec.json out.svg
   --png out.png`. The audit checks all nine rules with coordinates and exits 1 on
   violations. **Iterate until exit 0** — the eyeball misses 2–3px chip/node
   overlaps and forgotten corridor crossings; the audit does not (it caught 3
   violations a careful manual pass missed on the first real diagram).
6. **When a chip has no clean home** (verticals slice every candidate x-range):
   re-topology beats squeezing — route that edge on the other side of its column,
   convert the side to a port group, and re-center the node (step 3). Moving one
   edge usually frees a whole label zone.
7. **Other output formats** (same spec, no re-authoring):
   - High-res PNG: `--png out.png --scale 3` rasters at 3× the spec's width/height
     (the SVG itself is resolution-free — prefer it where SVG is accepted).
   - PowerPoint: `python3 scripts/spec_to_pptx.py spec.json out.pptx` emits NATIVE
     editable shapes — rounded rects with real text frames, one open freeform per
     edge (hop bridges approximated as 8-segment polyline arcs), filled arrowhead
     triangles, white chip text boxes. DEFAULT slide = PowerPoint's own 13.333×7.5 in
     16:9 (12192000×6858000 EMU; 914400 EMU/in; vector, so "resolution" ≈96 dpi only
     at raster export), diagram fitted + centered → copy-paste into another deck
     arrives at deck-native size. `--slide native` = wall-chart mode (slide sized 1:1
     to the spec, 12pt nominal floor `MIN_PT`; ceiling 56 in) for plotter/PDF use.
     Wanting bigger text relative to boxes is a SPEC change: raise `min_font`,
     re-layout on the held canvas — page+font scaling together is a visual no-op.
     Needs `python-pptx`
     (often only under system python3, not a project venv). Pitfall encoded in
     the script: text boxes must set `auto_size = NONE` — python-pptx's default
     `spAutoFit` + `wrap="none"` re-centers the shrunk box and silently defeats
     left/right paragraph alignment.

8. **Slide edition — deck-readable variant** (when the ask is "readable on one
   PowerPoint slide", nominal >= ~10pt): do NOT touch min_font or the converter —
   author a SECOND, condensed spec next to the wall-chart one (keep both):
   - Budget first: nominal pt ≈ 936pt / (canvas_w_px / min_font_px). At min_font 16
     that means canvas ≤ ~1500×840px for ~10pt on a 13.33×7.5in slide.
   - Get under the budget by cutting WIDTH, not font: 2-line nodes (title + one
     detail), 1–2-word edge chips, merge homogeneous node groups into one list node
     (e.g. 4 engine boxes → "Engines — MCP ×5" with one line each — also deletes the
     fan corridor), aspect ≈ 16:9 so no dimension is wasted.
   - Same audit loop; expect cluster-label collisions on the first pass (tight
     top-left corners) — the R3 cluster-label check flags them.
   - Worked example pair: ims.ai repo `.claude/docs/kmi-suite-architecture.spec.json`
     (wall-chart, 2560×1080, 18 nodes) vs `kmi-suite-architecture-slide.spec.json`
     (slide edition, 1500×840, 15 nodes, 9.8pt nominal) — same system, both audit-clean.

## Same bend level, different destinations — a real bend-sharing pitfall

Symbolic anchors (`["node:side"]`) auto-spread when several edges share one side — that's
what makes fan-out/fan-in read as centered and separated (R5) with zero manual port math.
But the auto-spread only nudges each edge ~`port_spacing`/2 (a few px) at the point it
*leaves* the shared node. If two edges on that side then both bend at the **same**
coordinate before heading toward *different, unrelated* destinations, their corridor
between the node and that bend can be exactly collinear — 0px apart — for its whole length.
The two arrows render as one merged line while every rule still reports clean, because the
audit's own corridor-spacing check historically treated 0px as "not close, not measured"
instead of "as close as two lines can get" (fixed in `strict_svg_diagram.py`'s R6 and
mirrored in `check_svg_rules.py`'s `no_collinear_edge_overlap` — both now flag this; if
you're on an older copy of either script, this is the fix to port over first).

**The rule that actually matters, so you don't just chase the audit number:**

- **True siblings** — one node fanning out to several, or several merging into one — belong
  on the **same** bend level. That's the whole point of the shared-level pattern: the
  divergence happens because the destinations are in *different columns*, so the corridor
  splits apart almost immediately after leaving the shared point, into a symmetric V or
  merge shape. Don't "fix" a false alarm here by giving siblings different levels — that
  breaks the visual symmetry the pattern exists to create; if a sibling pair ever DOES
  trip the collinear check, the fix is spacing the destination columns further apart, not
  un-sharing the bend level.
- **Unrelated edges that happen to leave the same side** — e.g. the main trunk continuing
  down one row, and an unrelated side-feed from a different node also passing through that
  row gap — are not siblings just because they're both edges in that gap. Give the
  non-trunk one its **own** bend level, offset by ~20–40px from the shared one. They'll
  still read as "both crossing this row gap," just as two distinct corridors instead of one
  smudged line.

The tell, when authoring by hand: if two `vedge`/`hedge`-style calls pass the identical
bend coordinate AND their destinations are on the *same side* of the shared origin (both
well left, or both well right — not a symmetric left/right pair), they're very likely two
unrelated routes about to collide, not a sibling pair.

## Alignment helpers — automate steps 1 & 3 (declare intent, not pixels)

Rather than hand-computing shared coordinates and port offsets, declare them and let
`resolve()` assign exact numbers (runs before render+audit; a spec without these keys
is unchanged):

- `"grid": N` — snap every un-pinned coordinate to an N-px lattice (kills 2–3px drift
  globally, one number).
- `"align": [{"type":"row","nodes":[…],"at":Y}, {"type":"col","nodes":[…]}]` — **step 1
  node placement**: `row` shares `cy`, `col` shares `cx` (omit `at` → group mean). Add
  `"between":[lo,hi]` or `"gap"+"start"` for even distribution on the other axis.
- **Symbolic edge endpoints** `["id:e"|"id:w"|"id:n"|"id:s"]` → the side **center**,
  resolved *after* nodes move (edges follow alignment). Waypoints may borrow an axis:
  `["id:cx", y]`. **This is step 3 done for you**: k edges into one side auto-spread
  symmetrically about the center (`port_spacing`, default 14), so the R5 group-centering
  and the perpendicular final segment hold by construction — no manual ±offset math.

Use these first; drop to raw pixels only where you need a bespoke route. The audit still
judges the resolved geometry, so a mis-declared alignment that causes an overlap is still
caught.

## Worked example

`docs/bug-stack-architecture.{spec.json,gen.py,svg,png}` in the ims.ai repo
(AI-Support/src/ims.ai.repository-main) is a 13-node / 16-edge / 3-cluster diagram
that passes the audit clean — use its spec as the reference for scale, corridor
budgeting, and port-group layout.

## API/auth notes for the AI-generation half

- Claude Code OAuth tokens (`sk-ant-oat…`) must be passed as
  `anthropic.Anthropic(auth_token=…, default_headers={"anthropic-beta":
  "oauth-2025-04-20"})` — `api_key=` sends x-api-key and 401s. (Fixed in
  dot_generator `_create_client` 2026-07-02.)
- While a Claude Code session is active, the same Max-subscription key usually
  429s on every model — the AI-generation stage is unavailable from inside a
  session. The working pattern: LayoutPlanner (local) for the plan, author the
  DOT/spec yourself, validate/audit locally. Nothing in the strict-rules path
  needs the API.

## Independent SVG grader

`scripts/check_svg_rules.py <file.svg>` audits ANY svg (hand-routed or graphviz output)
geometrically — no spec needed: axis-parallel-only (graphviz collinear-control beziers
count as straight; `strict_svg_diagram.py`'s own R4 hop bridges — circular arcs with a
horizontal, exactly-2×radius chord — are recognized as decoration too, not a curve
violation), segment-through-node, side-center/group-centered ports, R7 tip-run length, and
`no_collinear_edge_overlap` (the R6 same-bend-level pitfall above, run against the
*rendered* geometry rather than the authored spec — useful as a second opinion, or for
grading a diagram you didn't author). Use it to verify third-party or graphviz-produced
diagrams against the rules; use the spec-based audit in `strict_svg_diagram.py` while
authoring — it catches the same collinear-overlap case, plus everything upstream of
rendering (R2, R8–R10) that a pure-geometry grader can't see without the spec. Exit 0 =
clean on both.
