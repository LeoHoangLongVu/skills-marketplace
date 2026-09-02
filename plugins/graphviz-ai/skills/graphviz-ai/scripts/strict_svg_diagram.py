#!/usr/bin/env python3
"""strict_svg_diagram.py — hand-routed architecture diagrams under HARD layout rules.

Use this when a diagram must satisfy the strict rule set that graphviz cannot
guarantee (probe-verified on graphviz 2.43: splines=ortho IGNORES ports — compass
AND html-cell — and stabs edges into node centers):

  R1  arrows are straight axis-parallel segments only (no curves, no diagonals)
  R2  arrows meet containers at right angles
  R3  nothing overlaps or passes through another element
  R4  only arrow-with-arrow crossings are allowed — and each such crossing is drawn
      as a HOP (a small semicircular bridge) so the two wires read as "no junction":
      the horizontal wire arcs over the vertical one (standard schematic line-jump).
      On by default; disable with "hops": false, size it with "hop_radius" (default 6).
  R5  arrows attach at the CENTER of a container side; a side with multiple
      arrows centers the GROUP on that side, arrows stay separated
  R6  parallel arrows keep clear corridor spacing
  R7  the final segment into the arrowhead is long enough that the last right-angle
      bend stays visually distinct from the tip (default >= 24px, spec key "min_tip_run")
  R8  no arrow ever sits ON (or hugs) a component border: a segment may not run parallel
      to — and overlap — a node OR cluster edge, or it merges into the box outline and
      reads as part of the frame. Clearance default 4px, spec key "border_clear".
      (Perpendicular attachment is unaffected — an endpoint on the border overlaps it by 0.)
  R9  minimum readable text: ALL text renders at >= "min_font" (default 14px) — smaller
      text is the standing review complaint (unreadable projected / pasted into docs).
      The audit flags any node whose lines don't FIT at that size (width estimate
      ~0.58em/char, 0.62 bold) or whose height can't hold its line count: the fix is
      a wider/taller node or shorter label, never a smaller font.
  R10 component borders never touch or crowd: every pair of components (node-node,
      node-cluster, cluster-cluster) keeps >= "component_clear" px (default 12)
      between borders. Containment is allowed, but the contained component's inner
      margins must respect the same clearance — a node glued to its cluster frame
      reads as part of the frame.

You author a spec (nodes/clusters/edges with explicit Manhattan waypoints);
this script renders the SVG and — the important part — AUDITS every rule and
prints violations with coordinates, so you iterate on numbers, not eyeballs.

ALIGNMENT (optional, so you stop hand-computing shared coordinates):
  "grid": 20            snap every un-pinned coordinate to a 20px lattice.
  "align": [            declare intent; the solver assigns exact coords:
    {"type":"row","nodes":["L1","L2","L3"],"at":300},          # share cy=300
    {"type":"col","nodes":["L1","VT1"]},                       # share cx (= their mean)
    {"type":"row","nodes":["L1","L2","L3"],"between":[150,450]},# + even cx spread
    {"type":"col","nodes":["A","B","C"],"gap":90,"start":120}   # + cx=120,210,300
  ]
  Edges then follow moved nodes via SYMBOLIC endpoints instead of raw pixels:
    "points": [ ["L1:e"], ["R1:w"] ]      # side CENTERS (e/w/n/s); auto-satisfy R5
    "points": [ ["VT1:s"], ["VT1:cx",300] ]  # waypoint borrows a node's cx/cy axis
  Multiple edges anchored to the SAME side auto-spread (port_spacing, default 14)
  so R5's "group centered, arrows separated" holds by construction.
  A spec with none of these keys renders byte-identical (fully backward compatible).

Spec JSON:
{
  "title": "...", "width": 2200, "height": 880,
  "clusters": [ {"x1":40,"y1":85,"x2":700,"y2":585,"fill":"#eef3fa",
                 "stroke":"#8ea9c9","label":"PEER PC","labelcolor":"#1f3864"} ],
  "nodes": { "id": {"cx":170,"cy":300,"w":240,"h":70,"fill":"#fff",
                    "stroke":"#1f3864","lines":["Title","subtitle"]} },
  "edges": [ {"from":"a","to":"b","points":[[290,300],[365,300]],
              "label":"does X","label_at":[327,262]} ],
  "min_sep": 12, "min_font": 14, "component_clear": 12,
  "hops": true, "hop_radius": 6,
  "grid": 0, "align": [], "port_spacing": 14
}

Usage:
  python3 strict_svg_diagram.py spec.json out.svg [--png out.png] [--scale 3]
    --scale N  raster the PNG at N x the spec's width/height (SVG is resolution-free)
Exit 0 = rendered + audit clean · exit 1 = rendered but violations printed.
Iterate until exit 0 — do not hand the user a diagram that fails its own audit.
"""
import json, sys, copy

# ---------------------------------------------------------------- geometry
def _rect(n):        # node dict -> (x1,y1,x2,y2)
    return (n["cx"]-n["w"]/2, n["cy"]-n["h"]/2, n["cx"]+n["w"]/2, n["cy"]+n["h"]/2)

def _chip_rect(text, cx, cy, fs=9.5):
    tw = int(len(text)*fs*0.57)+10
    hh = (fs+7)/2
    return (cx-tw/2, cy-hh, cx+tw/2, cy+hh)

def _fonts(spec):
    """Font sizes derived from min_font (default 14 — smaller text is a standing
    review complaint: unreadable when the diagram is projected or pasted into docs).
    Returns (node_fs, chip_fs, cluster_fs, line_pitch)."""
    f = spec.get("min_font", 14)
    return f, f, max(f+1, 14), round(f*1.3)

def _seg_axis(p, q):
    if p[0]==q[0]: return "v"
    if p[1]==q[1]: return "h"
    return None

def _seg_hits_rect(p, q, r, pad=0.0):
    """Axis-parallel segment strictly crossing a rect interior (pad shrinks rect)."""
    x1,y1,x2,y2 = r[0]+pad, r[1]+pad, r[2]-pad, r[3]-pad
    if x1>=x2 or y1>=y2: return False
    if p[0]==q[0]:                                   # vertical
        lo,hi = sorted((p[1],q[1]))
        return x1 < p[0] < x2 and lo < y2 and hi > y1
    lo,hi = sorted((p[0],q[0]))                      # horizontal
    return y1 < p[1] < y2 and lo < x2 and hi > x1

def _on_border(pt, r, tol=0.5):
    x,y = pt; x1,y1,x2,y2 = r
    if abs(x-x1)<tol or abs(x-x2)<tol: return y1-tol <= y <= y2+tol and ("w" if abs(x-x1)<tol else "e")
    if abs(y-y1)<tol or abs(y-y2)<tol: return x1-tol <= x <= x2+tol and ("n" if abs(y-y1)<tol else "s")
    return None

# ---------------------------------------------------------------- alignment
# resolve() turns an author-friendly spec (grid, align groups, symbolic edge
# anchors) into a pure-numeric spec that render()/audit() consume unchanged.
# Order matters: snap authored coords -> apply align (moves nodes) -> resolve
# edge anchors against the FINAL node positions (so edges follow moved nodes and
# multi-arrow sides auto-spread to satisfy R5). A spec with none of the new keys
# is returned byte-identical (backward compatible).
def _snap(v, g):
    return round(v/g)*g if g else v

def _is_ref(x):                      # "L1:e" / "VT1:cx" ...
    return isinstance(x, str) and ":" in x

def _resolve_align(spec):
    spec = copy.deepcopy(spec)
    g = spec.get("grid")
    nodes = spec["nodes"]
    # 1. grid-snap authored node centers
    if g:
        for n in nodes.values():
            n["cx"], n["cy"] = _snap(n["cx"], g), _snap(n["cy"], g)
    # 2. align constraints, in list order (a node in two groups: last wins)
    for c in spec.get("align", []):
        typ, ids = c.get("type"), c.get("nodes", [])
        if typ not in ("row", "col"):
            raise SystemExit(f"align: unknown type {typ!r} (use 'row' or 'col')")
        miss = [i for i in ids if i not in nodes]
        if miss:
            raise SystemExit(f"align {typ}: unknown node(s) {miss}")
        if not ids:
            continue
        shared = "cy" if typ == "row" else "cx"      # row shares cy, col shares cx
        other  = "cx" if typ == "row" else "cy"
        line = _snap(c["at"], g) if "at" in c else _snap(sum(nodes[i][shared] for i in ids)/len(ids), g)
        for i in ids:
            nodes[i][shared] = line
        # optional even distribution along the OTHER axis (folds in "distribute")
        coords = None
        if "between" in c and len(ids) > 1:
            lo, hi = c["between"]; step = (hi-lo)/(len(ids)-1)
            coords = [lo + step*k for k in range(len(ids))]
        elif "gap" in c:
            start = c.get("start", nodes[ids[0]][other])
            coords = [start + c["gap"]*k for k in range(len(ids))]
        if coords:
            for i, val in zip(ids, coords):
                nodes[i][other] = _snap(val, g)
    # 3a. count endpoint anchors per (node, side) so we can auto-spread a group
    spacing = spec.get("port_spacing", 14)
    users = {}                                       # (nid, side) -> [(edge_idx, end_pos)]
    for ei, e in enumerate(spec["edges"]):
        pts = e["points"]
        for pos in (0, len(pts)-1):
            p = pts[pos]
            if isinstance(p, list) and len(p) == 1 and _is_ref(p[0]):
                nid, side = p[0].split(":", 1)
                if side in ("e", "w", "n", "s"):
                    users.setdefault((nid, side), []).append((ei, pos))
    offset, off_ax = {}, {}                           # (edge,pos) -> px off center ; perpendicular axis idx
    for (nid, side), grp in users.items():
        k = len(grp)
        for idx, key in enumerate(grp):
            offset[key] = (idx - (k-1)/2) * spacing
            off_ax[key] = 1 if side in "ew" else 0    # e/w spread in y(1), n/s spread in x(0)
    # 3b. rewrite every point to numeric coords
    for ei, e in enumerate(spec["edges"]):
        pts = e["points"]
        out = [_resolve_point(p, nodes, g,
                              offset.get((ei, pi if pi == 0 else (len(pts)-1 if pi == len(pts)-1 else -999)), 0.0))
               for pi, p in enumerate(pts)]
        # keep the final segment perpendicular when a spread moved the port off-center:
        # drag the neighbouring waypoint onto the port's centered axis.
        for pos in (0, len(out)-1):
            key = (ei, pos)
            if offset.get(key) and len(out) >= 2:
                nb = 1 if pos == 0 else len(out)-2
                ai = off_ax[key]
                out[nb][ai] = out[pos][ai]
        e["points"] = out
    return spec

def _resolve_point(p, nodes, g, off):
    # side-center anchor: ["L1:e"]  (auto-spread by `off` for multi-arrow sides)
    if isinstance(p, list) and len(p) == 1 and _is_ref(p[0]):
        nid, side = p[0].split(":", 1)
        if nid not in nodes: raise SystemExit(f"edge anchor: unknown node {nid!r}")
        n = nodes[nid]; x1, y1, x2, y2 = _rect(n)
        base = {"e": (x2, n["cy"]), "w": (x1, n["cy"]),
                "n": (n["cx"], y1), "s": (n["cx"], y2)}.get(side)
        if base is None: raise SystemExit(f"edge anchor {nid}:{side} — side must be e/w/n/s")
        x, y = base                                  # side centers are grid-aligned via the node;
        return [x, y + off] if side in "ew" else [x + off, y]   # the small spread stays off-grid on purpose
    # axis-borrow / raw: [xspec, yspec] where a spec may be "id:cx"/"id:cy" or a number
    def ax(v, which):
        if _is_ref(v):
            nid, ref = v.split(":", 1)
            if nid not in nodes: raise SystemExit(f"edge waypoint: unknown node {nid!r}")
            if ref not in ("cx", "cy"): raise SystemExit(f"edge waypoint {v} — ref must be cx/cy")
            return nodes[nid][ref]
        return _snap(v, g)
    return [ax(p[0], "x"), ax(p[1], "y")]

# ---------------------------------------------------------------- audit
def audit(spec):
    V=[]
    nodes, edges = spec["nodes"], spec["edges"]
    min_sep = spec.get("min_sep", 12)
    node_fs, chip_fs, _, pitch = _fonts(spec)
    segs=[]                                          # (edge_idx, p, q)
    for i,e in enumerate(edges):
        pts=e["points"]
        for p,q in zip(pts,pts[1:]):
            if _seg_axis(p,q) is None:
                V.append(f"R1 edge#{i} segment {p}->{q} is diagonal")
            segs.append((i,tuple(p),tuple(q)))
    # R2+R5 endpoint on border, perpendicular, side-center / group-centered
    side_groups={}                                   # (node,side) -> [offset coords]
    for i,e in enumerate(edges):
        for which,nid,pt,nxt in (("from",e["from"],e["points"][0],e["points"][1]),
                                 ("to",e["to"],e["points"][-1],e["points"][-2])):
            if nid not in nodes: V.append(f"R2 edge#{i} unknown node '{nid}'"); continue
            r=_rect(nodes[nid]); side=_on_border(pt,r)
            if not side:
                V.append(f"R2 edge#{i} {which}={nid} endpoint {pt} not on node border")
                continue
            ax=_seg_axis(pt,nxt)
            if (side in "ew" and ax!="h") or (side in "ns" and ax!="v"):
                V.append(f"R2 edge#{i} {which}={nid} attaches to side '{side}' but segment is not perpendicular")
            side_groups.setdefault((nid,side),[]).append(pt[1] if side in "ew" else pt[0])
    for (nid,side),coords in side_groups.items():
        n=nodes[nid]; center = n["cy"] if side in "ew" else n["cx"]
        mean=sum(coords)/len(coords)
        if abs(mean-center) > 1.0:
            V.append(f"R5 {nid}:{side} group mean {mean:.1f} != side center {center} (ports {sorted(coords)})")
        cs=sorted(coords)
        for a,b in zip(cs,cs[1:]):
            if b-a < 8: V.append(f"R5 {nid}:{side} ports {a} and {b} too close (<8)")
    # R3 segments through nodes (attachment endpoints exempt on their own node)
    for i,p,q in segs:
        e=edges[i]
        for nid,n in nodes.items():
            r=_rect(n)
            if nid in (e["from"],e["to"]) and (_on_border(p,r) or _on_border(q,r)):
                continue
            if _seg_hits_rect(p,q,r):
                V.append(f"R3 edge#{i} segment {p}->{q} passes through node '{nid}'")
    # R3 foreign segments through label chips / chips over nodes
    for i,e in enumerate(edges):
        if not e.get("label"): continue
        c=_chip_rect(e["label"], *e.get("label_at",(0,0)), fs=chip_fs)
        for j,p,q in segs:
            if j==i: continue
            if _seg_hits_rect(p,q,c):
                V.append(f"R3 chip '{e['label']}' pierced by edge#{j} segment {p}->{q}")
        for nid,n in nodes.items():
            nr=_rect(n)
            if c[0]<nr[2] and c[2]>nr[0] and c[1]<nr[3] and c[3]>nr[1]:
                V.append(f"R3 chip '{e['label']}' overlaps node '{nid}'")
    # R3 chip-vs-chip (two labels drifting onto the same spot)
    chips=[(e["label"], _chip_rect(e["label"], *e.get("label_at",(0,0)), fs=chip_fs))
           for e in edges if e.get("label")]
    for a in range(len(chips)):
        for b in range(a+1, len(chips)):
            (la,ca),(lb,cb)=chips[a],chips[b]
            if ca[0]<cb[2] and cb[0]<ca[2] and ca[1]<cb[3] and cb[1]<ca[3]:
                V.append(f"R3 chip '{la}' overlaps chip '{lb}'")
    # R3 cluster labels vs nodes — the label is drawn at (x1+16, y1+10+fs) and a node
    # placed too close to the cluster's top-left corner covers it (found twice by eye,
    # never by the audit, on real diagrams: EXTERNAL under Jira, platform label under row 1).
    _, _, cl_fs, _ = _fonts(spec)
    for c in spec.get("clusters", []):
        if not c.get("label"): continue
        lw = len(c["label"]) * cl_fs * 0.62
        lr = (c["x1"]+16, c["y1"]+6, c["x1"]+16+lw, c["y1"]+14+cl_fs)
        for nid, n in nodes.items():
            nr = _rect(n)
            if lr[0] < nr[2] and lr[2] > nr[0] and lr[1] < nr[3] and lr[3] > nr[1]:
                V.append(f"R3 cluster label '{c['label']}' hidden under node '{nid}' — "
                         f"move the node or shrink/rename the label")
    # R9 text must fit its node at min_font — text below 14px is a standing review
    # complaint (unreadable projected/pasted), so the fix is a wider node, never a
    # smaller font. Width estimate: avg Helvetica char ~0.58em (0.62 bold).
    for nid,n in nodes.items():
        lines=n.get("lines",[nid])
        for i,t in enumerate(lines):
            est=len(t)*node_fs*(0.62 if i==0 else 0.58)
            if est > n["w"]-10:
                V.append(f"R9 node '{nid}' line '{t}' ~{est:.0f}px wide at font {node_fs} "
                         f"exceeds node width {n['w']} — widen the node, don't shrink text")
        need=len(lines)*pitch+10
        if need > n["h"]:
            V.append(f"R9 node '{nid}' needs h>={need} for {len(lines)} lines at font {node_fs} (h={n['h']})")
    # R7 final segment long enough that the last bend stays clear of the arrowhead
    tip_run = spec.get("min_tip_run", 24)
    for i,e in enumerate(edges):
        pts=e["points"]
        if len(pts) < 3: continue                    # straight edge — no bend to lose
        (x0,y0),(x1,y1) = pts[-2], pts[-1]
        L = abs(x1-x0)+abs(y1-y0)
        if L < tip_run:
            V.append(f"R7 edge#{i} final segment {pts[-2]}->{pts[-1]} only {L:.0f}px — bend too close to arrow tip (min {tip_run})")
    # R8 no arrow may sit ON (or hug) a component border line — a segment running parallel to,
    # and overlapping, a node/cluster edge merges visually into the box outline. Perpendicular
    # attachment is untouched: an endpoint ON the border has zero overlap along that border.
    clear = spec.get("border_clear", 4)
    rects = [(f"node '{nid}'", _rect(n)) for nid, n in nodes.items()] + \
            [(f"cluster '{c.get('label','?')}'", (c["x1"], c["y1"], c["x2"], c["y2"]))
             for c in spec.get("clusters", [])]
    for i, p, q in segs:
        ax = _seg_axis(p, q)
        for name, (x1, y1, x2, y2) in rects:
            if ax == "h":
                lo, hi = sorted((p[0], q[0]))
                if min(hi, x2) - max(lo, x1) > 0.5:          # real overlap along the border, not a corner touch
                    for by in (y1, y2):
                        if abs(p[1]-by) <= clear:
                            V.append(f"R8 edge#{i} segment {p}->{q} runs along {name} border y={by:.0f} "
                                     f"(clearance {abs(p[1]-by):.0f} <= {clear})")
            elif ax == "v":
                lo, hi = sorted((p[1], q[1]))
                if min(hi, y2) - max(lo, y1) > 0.5:
                    for bx in (x1, x2):
                        if abs(p[0]-bx) <= clear:
                            V.append(f"R8 edge#{i} segment {p}->{q} runs along {name} border x={bx:.0f} "
                                     f"(clearance {abs(p[0]-bx):.0f} <= {clear})")
    # R10 component borders never touch or crowd — every pair of components
    # (node-node, node-cluster, cluster-cluster) keeps >= component_clear px
    # between borders. Containment is fine (that is what clusters are for),
    # but the contained component's inner margins must respect the clearance
    # too, or it reads as glued to the container frame.
    comp_clear = spec.get("component_clear", 12)
    comps = [(f"node '{nid}'", _rect(n)) for nid, n in nodes.items()] + \
            [(f"cluster '{c.get('label','?')}'", (c["x1"], c["y1"], c["x2"], c["y2"]))
             for c in spec.get("clusters", [])]

    def _r10_inside(a, b):
        return a[0] >= b[0] and a[1] >= b[1] and a[2] <= b[2] and a[3] <= b[3]

    def _r10_gap(a, b):
        dx = max(b[0] - a[2], a[0] - b[2], 0)
        dy = max(b[1] - a[3], a[1] - b[3], 0)
        if dx == 0 and dy == 0:
            return -1.0                                  # intersect or touch
        if dx == 0 or dy == 0:
            return max(dx, dy)
        return (dx * dx + dy * dy) ** 0.5                # diagonal neighbours

    for x in range(len(comps)):
        for y in range(x + 1, len(comps)):
            (na, ra), (nb, rb) = comps[x], comps[y]
            if _r10_inside(ra, rb) or _r10_inside(rb, ra):
                inner, outer = (ra, rb) if _r10_inside(ra, rb) else (rb, ra)
                m = min(inner[0] - outer[0], inner[1] - outer[1],
                        outer[2] - inner[2], outer[3] - inner[3])
                if m < comp_clear:
                    V.append(f"R10 {na} and {nb}: inner margin {m:.0f}px < {comp_clear} "
                             f"— contained component hugs the container border")
            else:
                g = _r10_gap(ra, rb)
                if g < 0:
                    V.append(f"R10 {na} and {nb} overlap/touch — components need "
                             f">= {comp_clear}px padding")
                elif g < comp_clear:
                    V.append(f"R10 {na} and {nb}: gap {g:.0f}px < {comp_clear} "
                             f"— components need padding")
    # R6 corridor spacing: same-axis segments of DIFFERENT edges too close while overlapping in span.
    # d==0 (exactly collinear) is the WORST case, not exempt: two edges sharing a bend level often
    # leave a shared node side at nearly the same point (auto-spread only offsets them ~port_spacing/2
    # near the node) and can then run down the SAME line for their whole corridor before diverging —
    # the audit must catch that as "0px apart", not silently pass it as parallel-but-fine. This showed
    # up in practice as two arrows rendering as one merged line while R1-R10 reported clean (see the
    # sibling-vs-unrelated guidance in references/strict-layout-rules.md).
    for a in range(len(segs)):
        for b in range(a+1,len(segs)):
            i,p,q = segs[a]; j,r_,s_ = segs[b]
            if i==j: continue
            ax1,ax2=_seg_axis(p,q),_seg_axis(r_,s_)
            if ax1!=ax2 or ax1 is None: continue
            if ax1=="v":
                d=abs(p[0]-r_[0]); lo1,hi1=sorted((p[1],q[1])); lo2,hi2=sorted((r_[1],s_[1]))
            else:
                d=abs(p[1]-r_[1]); lo1,hi1=sorted((p[0],q[0])); lo2,hi2=sorted((r_[0],s_[0]))
            if d < min_sep and min(hi1,hi2)-max(lo1,lo2) > 4:
                tag = "COLLINEAR/OVERLAPPING" if d == 0 else f"parallel {d:.0f}px apart"
                V.append(f"R6 edge#{i} and edge#{j} {tag} (<{min_sep})")
    return V

# ---------------------------------------------------------------- render
def _esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _drawn_points(e):
    """edge point list as actually drawn — last vertex pulled back by the arrowhead."""
    pts=[tuple(p) for p in e["points"]]
    (x0,y0),(x1,y1)=pts[-2],pts[-1]; s=8
    head=(x1, y1-s if y1>y0 else y1+s) if x1==x0 else ((x1-s if x1>x0 else x1+s), y1)
    return pts[:-1]+[head]

def _vertical_segs(drawn):
    """all vertical segments as (edge_idx, x, ylo, yhi) — the bars a horizontal wire may hop."""
    vs=[]
    for i,pts2 in enumerate(drawn):
        for P,Q in zip(pts2,pts2[1:]):
            if P[0]==Q[0] and P[1]!=Q[1]:
                vs.append((i, P[0], min(P[1],Q[1]), max(P[1],Q[1])))
    return vs

def _shaft_path(i, pts2, vsegs, r):
    """Build an SVG path 'd' for edge i, arcing a hop where a horizontal segment
    crosses another edge's vertical segment. Returns (d_string, hop_count).
    Convention: the HORIZONTAL wire hops over the vertical one (standard schematic
    line-jump), so a crossing is drawn once and reads as 'no connection here'."""
    d=[f'M {pts2[0][0]} {pts2[0][1]}']; hops=0
    for P,Q in zip(pts2,pts2[1:]):
        if P[1]==Q[1] and P[0]!=Q[0]:                       # horizontal segment — may hop
            y=P[1]; direction=1 if Q[0]>P[0] else -1
            xs=sorted({vx for (j,vx,ylo,yhi) in vsegs
                       if j!=i and ylo < y < yhi and min(P[0],Q[0]) < vx < max(P[0],Q[0])},
                      reverse=(direction<0))
            for vx in xs:
                a=vx-direction*r; b=vx+direction*r
                sweep=1 if direction>0 else 0               # bulge away from the wire (up)
                d.append(f'L {a} {y}')
                d.append(f'A {r} {r} 0 0 {sweep} {b} {y}')
                hops+=1
            d.append(f'L {Q[0]} {Q[1]}')
        else:                                               # vertical (never hops) or head pull-back
            d.append(f'L {Q[0]} {Q[1]}')
    return " ".join(d), hops

def render(spec):
    W,H,FONT = spec.get("width",2200), spec.get("height",880), "Helvetica, Arial, sans-serif"
    node_fs, chip_fs, cluster_fs, pitch = _fonts(spec)
    title_fs = max(22, node_fs+8)
    o=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>']
    if spec.get("title"):
        o.append(f'<text x="{W//2}" y="38" text-anchor="middle" font-family="{FONT}" font-size="{title_fs}" fill="#111">{_esc(spec["title"])}</text>')
    for c in spec.get("clusters",[]):
        o.append(f'<rect x="{c["x1"]}" y="{c["y1"]}" width="{c["x2"]-c["x1"]}" height="{c["y2"]-c["y1"]}" rx="12" '
                 f'fill="{c.get("fill","#f5f5f5")}" stroke="{c.get("stroke","#999")}" stroke-width="1.4"/>')
        if c.get("label"):
            o.append(f'<text x="{c["x1"]+16}" y="{c["y1"]+10+cluster_fs}" font-family="{FONT}" font-size="{cluster_fs}" font-weight="bold" '
                     f'fill="{c.get("labelcolor","#333")}">{_esc(c["label"])}</text>')
    # hop bridges: precompute drawn geometry + the vertical bars, once, so every
    # horizontal wire can arc over crossings of OTHER edges (R4 crossings stay legal,
    # now they read as jumps instead of ambiguous "+" junctions).
    drawn=[_drawn_points(e) for e in spec["edges"]]
    hops_on = spec.get("hops", True)
    hop_r   = spec.get("hop_radius", 6)
    vsegs   = _vertical_segs(drawn) if hops_on else []
    total_hops=0
    for i,e in enumerate(spec["edges"]):                        # shafts (nodes drawn after, so they sit on top)
        pts2=drawn[i]
        if hops_on:
            dstr,hc=_shaft_path(i, pts2, vsegs, hop_r); total_hops+=hc
            o.append(f'<path d="{dstr}" fill="none" stroke="#1f3864" stroke-width="1.6"/>')
        else:
            poly=" ".join(f"{x},{y}" for x,y in pts2)
            o.append(f'<polyline points="{poly}" fill="none" stroke="#1f3864" stroke-width="1.6"/>')
        (x0,y0),(x1,y1)=e["points"][-2], e["points"][-1]; t=9   # arrowhead from the true endpoint
        if   x1==x0 and y1>y0: tri=[(x1,y1),(x1-4.5,y1-t),(x1+4.5,y1-t)]
        elif x1==x0:           tri=[(x1,y1),(x1-4.5,y1+t),(x1+4.5,y1+t)]
        elif y1>y0 or x1>x0:   tri=[(x1,y1),(x1-t,y1-4.5),(x1-t,y1+4.5)] if x1>x0 else [(x1,y1),(x1+t,y1-4.5),(x1+t,y1+4.5)]
        else:                  tri=[(x1,y1),(x1+t,y1-4.5),(x1+t,y1+4.5)]
        o.append('<polygon points="'+" ".join(f"{x},{y}" for x,y in tri)+'" fill="#1f3864"/>')
    for nid,n in spec["nodes"].items():
        x,y=n["cx"]-n["w"]/2, n["cy"]-n["h"]/2
        o.append(f'<rect x="{x}" y="{y}" width="{n["w"]}" height="{n["h"]}" rx="9" '
                 f'fill="{n.get("fill","#fff")}" stroke="{n.get("stroke","#1f3864")}" stroke-width="1.6"/>')
        lines=n.get("lines",[nid]); k=len(lines)
        for i,t in enumerate(lines):
            ty=n["cy"]+(i-(k-1)/2)*pitch+node_fs*0.35
            wt=' font-weight="bold"' if i==0 else ''
            o.append(f'<text x="{n["cx"]}" y="{ty}" text-anchor="middle" font-family="{FONT}" '
                     f'font-size="{node_fs}"{wt} fill="#111">{_esc(t)}</text>')
    for e in spec["edges"]:
        if not e.get("label"): continue
        cx,cy=e.get("label_at",(0,0)); r=_chip_rect(e["label"],cx,cy,chip_fs)
        o.append(f'<rect x="{r[0]}" y="{r[1]}" width="{r[2]-r[0]}" height="{r[3]-r[1]}" fill="#ffffff" fill-opacity="0.92"/>')
        o.append(f'<text x="{cx}" y="{cy+chip_fs*0.36}" text-anchor="middle" font-family="{FONT}" font-size="{chip_fs}" fill="#555">{_esc(e["label"])}</text>')
    o.append('</svg>')
    return "\n".join(o), total_hops

def main():
    if len(sys.argv)<3:
        sys.exit(__doc__.strip().splitlines()[-4].strip())
    spec=json.load(open(sys.argv[1]))
    spec=_resolve_align(spec)                        # grid + align groups + edge anchors -> numeric spec
    svg,hops=render(spec)
    open(sys.argv[2],"w").write(svg)
    print("wrote", sys.argv[2], f"({hops} hop{'s' if hops!=1 else ''})")
    if "--png" in sys.argv:
        out=sys.argv[sys.argv.index("--png")+1]
        scale=float(sys.argv[sys.argv.index("--scale")+1]) if "--scale" in sys.argv else 1.0
        w=int(spec.get("width",2200)*scale); h=int(spec.get("height",1400)*scale)
        try:
            import cairosvg; cairosvg.svg2png(url=sys.argv[2], write_to=out, output_width=w, output_height=h)
            print("wrote", out, f"({w}x{h}, {scale}x)")
        except Exception as ex:
            print("png skipped:", ex)
    v=audit(spec)
    if v:
        print(f"\nAUDIT: {len(v)} violation(s)")
        for x in v: print("  ✗", x)
        sys.exit(1)
    print("AUDIT: clean (R1-R10)")

if __name__=="__main__":
    main()
