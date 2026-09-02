#!/usr/bin/env python3
r"""Render a Graphviz graph to a slide-ready SVG, themed and fitted to the deck.

The animated-deck diagrams are hand-placed (≲15 boxes) and checked by check_diagram.js.
For a genuinely dense / many-to-many / auto-laid-out graph that cannot be hand-placed, this
wraps Graphviz: it injects the deck's visual theme, runs the chosen layout engine, scales the
result to fit a slide's content box, and reports the *effective* on-canvas font size so you
can tell whether it is still legible. It does NOT reimplement layout — Graphviz owns that.

Use it only as an escape hatch. A hairball on a slide communicates nothing: prefer to
aggregate, show the relevant subgraph, or split across slides first. If you must show the
whole graph, this makes it look like the rest of the deck.

Usage:
  python3 graphviz_embed.py graph.dot -o graph.svg            # default: dot, fit a content box
  python3 graphviz_embed.py graph.dot -o g.svg --engine sfdp  # force-directed (dense mesh)
  python3 graphviz_embed.py graph.dot -o g.svg --box 1180x560 # plain (no-chrome) slide box
  cat graph.dot | python3 graphviz_embed.py - -o g.svg

Then drop the SVG inside a `.r` container in the slide's content area. The wrapper prints the
effective minimum font size on the 1280x720 canvas; if it is below 14px the graph is too
dense to read at slide size — simplify it (see references/diagrams/graphviz.md).

Requires Graphviz (`dot`).
"""
import argparse, re, subprocess, sys

# deck theme injected as graph/node/edge defaults (explicit attrs in the .dot still win).
# splines/overlap/sep/esep make edges route around boxes and meet node borders cleanly on
# the force engines (neato/fdp/sfdp); dot ignores them harmlessly. esep<sep is deliberate:
# sep spaces the nodes for legibility while esep="+1" lets edges reach the real border instead
# of stopping a full sep-margin short (the gap you otherwise see). arrowsize is small (0.6) so
# the head reads as touching the border — a big head overlaps the rounded corner and looks like
# it overshoots inside. (Graphviz clips edges to the node's bounding RECTANGLE, so a tip landing
# at a rounded corner sits slightly inside the visible curve; that residual overshoot is an
# inherent Graphviz limitation, minimised but not eliminated by the small head.)
THEME = (
    'graph[bgcolor="transparent",rankdir=LR,fontname="Lato",fontsize=14,'
    'nodesep=0.35,ranksep=0.55,pad=0.1,splines=true,overlap=false,sep="+6",esep="+1"];'
    'node[shape=box,style="rounded,filled",fillcolor="#ffffff",color="#1b2a6b",'
    'penwidth=1.4,fontname="JetBrains Mono",fontsize=14,fontcolor="#1f2733",margin="0.20,0.11"];'
    'edge[color="#1b2a6b",penwidth=1.3,fontname="Lato",fontsize=14,fontcolor="#5a6472",arrowsize=0.6];'
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dot", help="path to .dot file, or - for stdin")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--engine", default="dot",
                    choices=["dot", "neato", "fdp", "sfdp", "circo", "twopi"],
                    help="layout engine (dot=hierarchical/DAG; sfdp/fdp/neato=force, for meshes)")
    ap.add_argument("--box", default="1136x470",
                    help='content box WxH px to fit (default 1136x470 for a chrome content '
                         'slide; use 1180x560 for a plain slide)')
    ap.add_argument("--no-theme", action="store_true", help="do not inject the deck theme")
    args = ap.parse_args()

    src = sys.stdin.read() if args.dot == "-" else open(args.dot).read()
    if not args.no_theme:
        # inject theme defaults right after the first opening brace of the graph
        m = re.search(r"\b(strict\s+)?(di)?graph\b[^{]*\{", src)
        if not m:
            sys.exit("not a valid .dot graph (no 'digraph/graph {' found)")
        i = m.end()
        src = src[:i] + "\n  " + THEME + "\n" + src[i:]

    try:
        svg = subprocess.run(["dot", "-K" + args.engine, "-Tsvg"], input=src,
                             capture_output=True, text=True, check=True).stdout
    except FileNotFoundError:
        sys.exit("Graphviz 'dot' not found")
    except subprocess.CalledProcessError as e:
        sys.exit("dot failed:\n" + e.stderr)

    m = re.search(r'<svg width="([\d.]+)pt" height="([\d.]+)pt"', svg)
    if not m:
        sys.exit("unexpected dot SVG output")
    W, H = float(m.group(1)), float(m.group(2))
    bw, bh = (int(v) for v in args.box.lower().split("x"))
    scale = min(bw / W, bh / H)                       # fit inside the box (may up- or down-scale)
    fonts = [float(x) for x in re.findall(r'font-size="([\d.]+)"', svg)]
    minf = min(fonts) if fonts else 14.0
    eff = minf * scale                               # effective px on the 1280x720 canvas

    # size the root <svg> to the fitted box and let it scale by viewBox; keep it centred
    svg = re.sub(r'<svg width="[\d.]+pt" height="[\d.]+pt"',
                 '<svg class="gv" width="%d" height="%d" preserveAspectRatio="xMidYMid meet"'
                 % (round(W * scale), round(H * scale)), svg, count=1)
    with open(args.out, "w") as f:
        f.write(svg)

    flag = "" if eff >= 14 else "  <-- BELOW 14px: too dense, simplify (see graphviz.md)"
    print(f"{args.engine}: graph {W:.0f}x{H:.0f}pt -> fit {round(W*scale)}x{round(H*scale)}px "
          f"in {bw}x{bh} box (scale {scale:.2f})")
    print(f"effective min font: {eff:.1f}px{flag}")
    print(f"wrote {args.out} — embed inside a .r container in the slide body")

if __name__ == "__main__":
    main()
