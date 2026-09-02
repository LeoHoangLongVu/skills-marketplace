# Dense / auto-laid-out graphs — wrapping Graphviz

The hand-placed diagrams in the other family guides cover directed flows and small DAGs
(≲15 boxes), verified by `check_diagram.js`. When a graph is genuinely **dense, many-to-many,
or needs automatic layout** (you cannot place the nodes by hand), do not try to hand-place it
and do not reimplement layout — that is exactly what Graphviz is for. Wrap it instead with
`scripts/graphviz_embed.py`, which lays the graph out with Graphviz, themes it to match the
deck, fits it to a slide, and reports whether the text is still legible.

```bash
python3 scripts/graphviz_embed.py graph.dot -o graph.svg              # dot (hierarchical/DAG)
python3 scripts/graphviz_embed.py graph.dot -o graph.svg --engine sfdp # force-directed mesh
python3 scripts/graphviz_embed.py graph.dot -o graph.svg --box 1180x560 # plain (no-chrome) slide
```
Then paste the produced `<svg class="gv">` inside a `.r` container in the slide's content area
(centred). The script prints the **effective minimum font size on the 1280×720 canvas** — read
it every time.

## Rules so it looks native to the deck

1. **Simplify before you reach for it.** A hairball on a slide communicates nothing. First try
   to aggregate clusters into one node, show only the relevant subgraph, or split across
   slides. Graphviz is the escape hatch for when the whole dense graph genuinely must appear,
   not the default for "many boxes".
2. **Effective font must stay ≥ 14px — that caps you at roughly 8–10 nodes.** The wrapper
   scales the graph to fit the content box; the more nodes (and the wider their labels), the
   smaller everything renders. It prints the effective min font and flags anything `< 14px`. In
   practice a force-directed mesh fits a slide body at ≥14px only up to ~8–10 nodes; past that,
   or with long labels, the layout grows and the text drops below 14. Two levers, in order:
   **shorten the labels** (a long word like `Validated` widens its node, which pushes the whole
   layout out and shrinks every label — `Valid` reads the same and keeps the graph compact),
   then **drop nodes**. Force engines (`neato`/`fdp`) pack tighter than `circo`/`twopi`, so they
   hold a higher font at the same node count. Never ship a sub-14 graph just because it fit.
3. **Keep the injected theme — it is also what makes edges read cleanly.** The wrapper sets
   white rounded nodes, navy `#1b2a6b` strokes, mono labels and a transparent background so it
   matches the hand-drawn diagrams; it *also* injects `splines=true` + `overlap=false` (edges
   curve **around** boxes instead of cutting across them) and `sep="+6"`/`esep="+1"` (nodes get
   breathing room while edges still reach the real border — drop `esep` and every arrow stops a
   visible gap short of its node). The arrowhead is small (`arrowsize=0.6`) on purpose: a big
   head overlaps the rounded corner and looks like it stabs inside the box. Explicit attributes
   in your `.dot` still win for an accent (e.g. a terminal node
   `[fillcolor="#2E9E45",fontcolor="#fff"]`), but do not strip the routing defaults or
   re-introduce Graphviz's light-blue/black look.
4. **Pick the layout for the shape, and prefer wide.** `rankdir=LR` is the default (slides are
   wide); use `rankdir=TB` only for a tall hierarchy. Engines: `dot` = hierarchical/DAG,
   `sfdp`/`fdp`/`neato` = force-directed (meshes), `circo`/`twopi` = cyclic/radial.
5. **One graph per slide; title goes in the slide, not the graph.** Let the slide's eyebrow +
   title name it; keep node labels short (wrap long ones with `\n`). Add a one-line caption
   below if needed.
6. **It is a still structural image — no per-node animation.** Auto-layout has no authored
   reveal order, so do not try to pop/draw individual nodes; let the slide's `.r` fade carry
   it in. (That is the trade for letting Graphviz place things.)
7. **Place it in a container *below* the slide title, not spanning the whole slide.** The
   produced `<svg class="gv">` centres itself; if its `.r` wrapper is `inset:0` the top nodes
   ride up under the eyebrow/heading. Give the wrapper a `top` clear of the title band (e.g.
   `top:208px;bottom:52px`) so the graph lives in the body only.
8. **Arrow tips may still sit a hair inside a node — accept it.** Graphviz clips edges to each
   node's bounding **rectangle**, but the visible node is a **rounded** rectangle, so a tip
   arriving near a corner lands inside the rounded curve. The injected small arrowhead minimises
   this, but a residual overshoot at some corners is an inherent Graphviz limitation, not a bug
   to keep chasing. (If a specific graph's contact really matters, nudge that edge's target with
   a port like `-> n:w`, or hand-place it with `flow.md` instead.)
9. **`check_diagram.js` does not validate it** — the output is not `.gn`/`.ge`, so the geometry
   checker skips it. Your checks are the wrapper's font report and a `shot.sh` screenshot.

## When NOT to use this
- ≲15 nodes you can place meaningfully by hand → use `flow.md` / `concept.md` (animated,
  checked, authored reveal order). Hand-placed almost always reads better on a slide.
- Quantitative data (bar/line/scatter) → that is a chart, not a graph; this skill does not do
  data charts (use a real plotting tool, or `composition.md`'s pie for shares of a whole).
