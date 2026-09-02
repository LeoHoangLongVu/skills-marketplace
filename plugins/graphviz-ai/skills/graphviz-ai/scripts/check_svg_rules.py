#!/usr/bin/env python3
"""check_svg_rules.py <file.svg> — geometric grader for the strict-rule assertions.

Tolerant parser for arbitrary agent-produced SVGs (hand-routed or graphviz):
- node boxes  = <rect>/axis-aligned <polygon> (4-5 pts) big enough to be a box;
                a rect containing >=2 other boxes is a CLUSTER (excluded)
- arrows      = <polyline>/<line>/<path>; bezier C segments whose control points are
                collinear on one axis count as STRAIGHT (graphviz emits these), other
                C/Q/A = curved. Segments lying fully inside one node = decoration, skipped.
Checks: R1 axis-parallel, R3 segment-through-node, R5 endpoint at side center / centered group,
R6 no two DIFFERENT edges run same-axis within 12px while their spans overlap — includes the
d==0 (exactly collinear) case, which is the actual failure mode seen in practice: two edges
sharing a bend coordinate can render as one merged line while everything else about them looks
fine, R7 final segment of a bent chain long enough that the last right-angle bend stays visually
distinct from the arrowhead (threshold 15px on the DRAWN shaft — renderers trim ~8px for the
head, so a 24px authored run leaves ~16px of shaft).
Exit 0 = all pass.
"""
import re, sys
from xml.dom import minidom

doc = minidom.parse(sys.argv[1])
svg = doc.getElementsByTagName("svg")[0]
def _f(v):
    try: return float(re.sub(r"[a-z%]+$","",(v or "0").strip()))
    except Exception: return 0.0
W = _f(svg.getAttribute("width")) or 2000
H = _f(svg.getAttribute("height")) or 1000

boxes=[]
for r in doc.getElementsByTagName("rect"):
    x,y,w,h=_f(r.getAttribute("x")),_f(r.getAttribute("y")),_f(r.getAttribute("width")),_f(r.getAttribute("height"))
    if w>=60 and h>=28 and w*h < 0.75*W*H and (r.getAttribute("fill") or "").lower()!="none":
        boxes.append((x,y,x+w,y+h))
for pg in doc.getElementsByTagName("polygon"):
    try: pts=[(float(a),float(b)) for a,b in (q.split(",") for q in pg.getAttribute("points").split() if "," in q)]
    except Exception: continue
    if not (4<=len(pts)<=5): continue
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    w,h=max(xs)-min(xs),max(ys)-min(ys)
    axis_aligned=all(any(abs(p[0]-q[0])<0.6 or abs(p[1]-q[1])<0.6 for q in pts if q!=p) for p in pts)
    if w>=60 and h>=28 and axis_aligned and w*h<0.75*W*H:
        boxes.append((min(xs),min(ys),max(xs),max(ys)))

def _contains(a,b):
    return a[0]<=b[0]+1 and a[1]<=b[1]+1 and a[2]>=b[2]-1 and a[3]>=b[3]-1 and a!=b
nodes=[b for b in boxes if not any(_contains(b,o) for o in boxes)]        # containers (hold any box) = clusters, excluded

segs=[]; chains=[]; curved=0; diag=0
_elem_id=[-1]                                          # one id per <polyline>/<line>/<path> DOM element,
                                                        # i.e. per rendered edge — NOT per M-triggered
                                                        # subpath, so an edge's own shaft + decoration
                                                        # never trip the cross-edge overlap check below
def add_chain(pts):
    if len(pts) < 2: return
    for r in nodes:                                    # decoration: whole chain inside one node box
        if all(r[0]-1<=p[0]<=r[2]+1 and r[1]-1<=p[1]<=r[3]+1 for p in pts):
            return
    chains.append(pts)
def add_seg(p,q):
    global diag
    for r in nodes:                                    # decoration: fully inside one node box
        if min(p[0],q[0])>=r[0]-1 and max(p[0],q[0])<=r[2]+1 and min(p[1],q[1])>=r[1]-1 and max(p[1],q[1])<=r[3]+1:
            return
    if abs(p[0]-q[0])>0.8 and abs(p[1]-q[1])>0.8: diag+=1
    segs.append((_elem_id[0],p,q))

for pl in list(doc.getElementsByTagName("polyline"))+list(doc.getElementsByTagName("line")):
    _elem_id[0]+=1
    if pl.tagName=="line":
        pts=[(_f(pl.getAttribute("x1")),_f(pl.getAttribute("y1"))),(_f(pl.getAttribute("x2")),_f(pl.getAttribute("y2")))]
    else:
        pts=[tuple(map(float,p.split(","))) for p in pl.getAttribute("points").split() if "," in p]
    add_chain(pts)
    for p,q in zip(pts,pts[1:]): add_seg(p,q)

for pa in doc.getElementsByTagName("path"):
    _elem_id[0]+=1
    d=pa.getAttribute("d") or ""
    cur=None; start=None; pchain=[]
    for cmd,arg in re.findall(r"([MLHVCQASTZmlhvcqastz])([^MLHVCQASTZmlhvcqastz]*)", d):
        vals=[float(v) for v in re.split(r"[ ,]+", arg.strip()) if v]
        i=0
        if cmd in "Zz" and start is not None: cur=start; continue
        while i<len(vals) or cmd in "Zz":
            if cmd in "Mm" and i+1<len(vals):
                cur=(vals[i],vals[i+1]) if cmd=="M" or cur is None else (cur[0]+vals[i],cur[1]+vals[i+1])
                add_chain(pchain); pchain=[cur]
                start=cur; i+=2; cmd="L" if cmd=="M" else "l"; continue
            if cmd in "Ll" and i+1<len(vals):
                nxt=(vals[i],vals[i+1]) if cmd=="L" else (cur[0]+vals[i],cur[1]+vals[i+1]); i+=2
            elif cmd in "Hh" and i<len(vals):
                nxt=((vals[i] if cmd=="H" else cur[0]+vals[i]), cur[1]); i+=1
            elif cmd in "Vv" and i<len(vals):
                nxt=(cur[0],(vals[i] if cmd=="V" else cur[1]+vals[i])); i+=1
            elif cmd in "Cc" and i+5<len(vals):
                pts6=vals[i:i+6]; i+=6
                if cmd=="c": pts6=[pts6[0]+cur[0],pts6[1]+cur[1],pts6[2]+cur[0],pts6[3]+cur[1],pts6[4]+cur[0],pts6[5]+cur[1]]
                xs=[cur[0],pts6[0],pts6[2],pts6[4]]; ys=[cur[1],pts6[1],pts6[3],pts6[5]]
                nxt=(pts6[4],pts6[5])
                if max(xs)-min(xs)<0.8 or max(ys)-min(ys)<0.8:
                    pass                                            # collinear-axis bezier = straight
                else:
                    curved+=1; cur=nxt; continue
            elif cmd in "Aa" and i+6<len(vals):
                # R4 hop bridges (strict_svg_diagram.py) are `A r r 0 0 <sweep> x y` — a circular
                # arc (rx==ry) whose chord is horizontal and exactly 2r long, since it always jumps
                # a straight wire over another. That's the ONLY arc shape our own generator emits,
                # so treat exactly that shape as decoration (not a curve, not a Manhattan segment)
                # and keep parsing the rest of the path from its true endpoint. Anything else with
                # rx!=ry, a non-horizontal chord, or a chord length that isn't ~2r is a genuine
                # curve — falls through to the generic R1 violation below.
                rx,ry=vals[i],vals[i+1]; ex,ey=vals[i+5],vals[i+6]; i+=7
                if cmd=="a": ex,ey=cur[0]+ex,cur[1]+ey
                if abs(rx-ry)<0.5 and abs(ey-cur[1])<0.8 and abs(abs(ex-cur[0])-2*rx)<1.5:
                    cur=(ex,ey); pchain.append(cur); continue
                curved+=1; break
            elif cmd in "QqAaSsTt":
                curved+=1; break
            else: break
            if cur is not None: add_seg(cur,nxt)
            cur=nxt; pchain.append(nxt)
    add_chain(pchain)

def through(p,q,r,pad=1.0):
    x1,y1,x2,y2=r[0]+pad,r[1]+pad,r[2]-pad,r[3]-pad
    if abs(p[0]-q[0])<=0.8:
        lo,hi=sorted((p[1],q[1])); return x1<p[0]<x2 and lo<y2-2 and hi>y1+2
    if abs(p[1]-q[1])<=0.8:
        lo,hi=sorted((p[0],q[0])); return y1<p[1]<y2 and lo<x2-2 and hi>x1+2
    return False

pierce=0; pierce_ex=[]
for _eid,p,q in segs:
    for r in nodes:
        onb=lambda pt: (abs(pt[0]-r[0])<2.5 or abs(pt[0]-r[2])<2.5) and r[1]-2.5<=pt[1]<=r[3]+2.5 \
                    or (abs(pt[1]-r[1])<2.5 or abs(pt[1]-r[3])<2.5) and r[0]-2.5<=pt[0]<=r[2]+2.5
        if onb(p) or onb(q): continue
        if through(p,q,r):
            pierce+=1; pierce_ex.append(f"{p}->{q} through {tuple(round(v) for v in r)}"); break

# R6 corridor spacing / collinear-overlap: same-axis segments from DIFFERENT edges too close
# while their spans overlap. d==0 (exactly collinear) is the WORST case — two edges sharing a
# bend level (or a graphviz layout coincidence) can render as one merged line while every other
# rule stays clean; that gap is exactly what this check exists to close (see
# strict-layout-rules.md for the authoring-side fix once you find one of these).
MIN_SEP=12.0
overlap=[]
for a in range(len(segs)):
    for b in range(a+1,len(segs)):
        i,p,q = segs[a]; j,r_,s_ = segs[b]
        if i==j: continue
        h1,h2 = abs(p[1]-q[1])<=0.8, abs(r_[1]-s_[1])<=0.8      # horizontal?
        v1,v2 = abs(p[0]-q[0])<=0.8, abs(r_[0]-s_[0])<=0.8      # vertical?
        if h1 and h2:
            d=abs(p[1]-r_[1]); lo1,hi1=sorted((p[0],q[0])); lo2,hi2=sorted((r_[0],s_[0]))
        elif v1 and v2:
            d=abs(p[0]-r_[0]); lo1,hi1=sorted((p[1],q[1])); lo2,hi2=sorted((r_[1],s_[1]))
        else:
            continue
        if d < MIN_SEP and min(hi1,hi2)-max(lo1,lo2) > 4:
            tag = "collinear/overlapping" if d==0 else f"{d:.0f}px apart"
            overlap.append(f"edge~{i} and edge~{j} {tag}: {p}->{q} vs {r_}->{s_}")

# Attachment points come from CHAIN ENDPOINTS only (waypoints never attach). Tolerance 9.5px:
# renderers trim ~8px of shaft for the arrowhead, so an incoming tip stops short of the border —
# without the slack, sides that mix one outgoing (on-border) and one incoming (trimmed) port
# would register only the outgoing one and read as off-center.
groups={}
ATT=9.5
for c in chains:
    for pt in (c[0], c[-1]):
        for i,r in enumerate(nodes):
            side=None
            if   abs(pt[0]-r[0])<ATT and r[1]-ATT<=pt[1]<=r[3]+ATT: side="w"
            elif abs(pt[0]-r[2])<ATT and r[1]-ATT<=pt[1]<=r[3]+ATT: side="e"
            elif abs(pt[1]-r[1])<ATT and r[0]-ATT<=pt[0]<=r[2]+ATT: side="n"
            elif abs(pt[1]-r[3])<ATT and r[0]-ATT<=pt[0]<=r[2]+ATT: side="s"
            if side: groups.setdefault((i,side),set()).add(round(pt[1] if side in "we" else pt[0],1)); break
offc=[]
for (i,side),coords in groups.items():
    r=nodes[i]; center=(r[1]+r[3])/2 if side in "we" else (r[0]+r[2])/2
    m=sum(coords)/len(coords)
    if abs(m-center)>2.5:
        offc.append(f"node{i}{tuple(round(v) for v in r)}:{side} mean {m:.0f} vs center {center:.0f}")

# R7: a chain that bends (>=3 pts) must keep its drawn final segment >=15px so the last
# right-angle bend stays visually distinct from the arrowhead
TIP=15.0
tips=[]
for c in chains:
    if len(c) < 3: continue
    (x0,y0),(x1,y1)=c[-2],c[-1]
    L=abs(x1-x0)+abs(y1-y0)
    if 0 < L < TIP: tips.append(f"{c[-2]}->{c[-1]} shaft {L:.0f}px")

res=[("axis_parallel_only", diag==0 and curved==0, f"diagonal_segments={diag} curved_paths={curved}"),
     ("no_segment_through_node", pierce==0, f"pierced={pierce} " + ("; ".join(pierce_ex[:4]) if pierce_ex else f"(nodes={len(nodes)}, segs={len(segs)})")),
     ("ports_centered", not offc, "; ".join(offc[:6]) or f"all {len(groups)} side-groups centered ±2.5px"),
     ("bend_clear_of_arrow_tip", not tips, "; ".join(tips[:5]) or f"all {sum(1 for c in chains if len(c)>=3)} bent chains keep final run ≥{TIP:.0f}px"),
     ("no_collinear_edge_overlap", not overlap, "; ".join(overlap[:5]) or f"no two edges run the same line within {MIN_SEP:.0f}px")]
ok=True
for name,passed,detail in res:
    print(("PASS" if passed else "FAIL"), name, "—", detail); ok = ok and passed
sys.exit(0 if ok else 1)
