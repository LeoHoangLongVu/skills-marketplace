# Animation Cookbook

Patterns for the SVG diagrams that make these decks feel alive. All are gated on
`.slide.active` so they replay on every visit. Copy the CSS that the template already
ships, then add the SVG markup below per slide.

Coordinates are in the SVG `viewBox` space (e.g. `viewBox="0 0 1000 360"`), independent of
the on-screen scale.

## Table of contents
1. Node-edge graph (base)
2. Edge draw (`pathLength`)
3. Node pop-in (and the fill-box trap)
4. Sequential traversal (light a path one step at a time)
5. Flow-dot travelling a path (SMIL)
6. Blast-radius rings (impact)
7. Dim-the-rest focus (onboarding/subgraph)
8. Marker (arrowhead) defs
9. Geometry checklist

---

## 1. Node-edge graph (base)

```html
<div class="gwrap">
  <svg class="graph" viewBox="0 0 1000 300">
    <defs>
      <marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">
        <path d="M0,0 L7,3 L0,6 Z" fill="var(--accent)"/></marker>
    </defs>
    <!-- draw EDGES first so nodes paint on top of them -->
    <line class="ge" x1="225" y1="150" x2="415" y2="150" pathLength="1"
          style="animation-delay:.5s" marker-end="url(#ar)"/>
    <!-- NODES: rect + two text lines; class a/b/c/d = colour -->
    <g class="gn a" style="animation-delay:.1s">
      <rect x="70" y="120" width="155" height="60" rx="10"/>
      <text class="t" x="147" y="146">node A</text>
      <text class="s" x="147" y="166">label</text>
    </g>
  </svg>
</div>
```

Node colour classes: `.gn.a` (cyan/accent), `.gn.b` (magenta), `.gn.c` (green), `.gn.d`
(amber). Edge colour: `.ge` (accent) or `.ge.m` (accent2).

## 2. Edge draw (`pathLength`)

Set `pathLength="1"` on any `<line>` or `<path>`. The CSS sets `stroke-dasharray:1;
stroke-dashoffset:1` and animates the offset to 0 — the stroke draws itself from start to
end. Because the path length is normalised to 1, you never measure real geometry. Stagger
multiple edges with `style="animation-delay:.Ns"`.

Curved edge:
```html
<path class="ge" d="M205,114 C300,104 380,92 453,90" pathLength="1"
      style="animation-delay:.6s" marker-end="url(#ar)"/>
```

## 3. Node pop-in (and the fill-box trap)

`.gn { opacity:0; transform-box:fill-box; transform-origin:center }` then
`@keyframes pop { from {opacity:0; transform:scale(.6)} to {opacity:1; transform:scale(1)} }`.

**The trap:** without `transform-box:fill-box`, an SVG `<g>`'s transform origin is the SVG
(0,0), so `scale(.6)` shrinks the node *toward the top-left corner* and it slides in
diagonally. `fill-box` makes the origin the node's own box → it scales in place. Always set
it on custom node groups.

## 4. Sequential traversal (light a path one step at a time)

Give the path nodes/edges increasing delays so the flow lights up in order. Use it for
"trace this control flow A→B→C→D".

```html
<g class="gn a" style="animation-delay:.1s">…A…</g>
<line class="ge" … style="animation-delay:.6s"/>   <!-- A→B draws after A pops -->
<g class="gn b" style="animation-delay:.7s">…B…</g>
<line class="ge" … style="animation-delay:1.2s"/>
<g class="gn c" style="animation-delay:1.3s">…C…</g>
```

Tune the cadence so each edge finishes drawing just as the next node appears.

## 5. Flow-dot travelling a path (SMIL)

A glowing dot that runs along the flow, re-triggered on each slide visit.

```html
<defs><path id="p7" d="M95,115 H965" fill="none"/></defs>
<circle class="dot" r="6">
  <animateMotion dur="2.6s" begin="indefinite" fill="freeze"><mpath href="#p7"/></animateMotion>
</circle>
```

CSS — the dot needs BOTH the SMIL motion AND an opacity keyframe (motion alone leaves it
invisible if `.dot{opacity:0}`):

```css
.dot{fill:var(--accent); filter:drop-shadow(0 0 9px var(--accent)); opacity:0;}
.slide.active .dot{animation:flowdot 2.6s linear forwards;}
@keyframes flowdot{0%{opacity:0;}8%{opacity:1;}92%{opacity:1;}100%{opacity:0;}}
```

The engine's `triggerMotion()` calls `beginElement()` on every `<animateMotion>` in the
active slide, so `begin="indefinite"` fires on each visit. Already wired in the template.

## 6. Blast-radius rings (impact)

Expanding rings around a focal node — "what does changing this affect?".

```html
<circle class="ring" cx="500" cy="180" r="95" style="animation-delay:.2s"/>
<circle class="ring" cx="500" cy="180" r="95" style="animation-delay:.9s"/>
<circle class="ring" cx="500" cy="180" r="95" style="animation-delay:1.6s"/>
```

`.ring` needs `transform-box:fill-box; transform-origin:center` so the scale grows from the
centre. Pair with a `.gn.pulse` focal node and edges to the affected nodes.

## 7. Dim-the-rest focus (onboarding/subgraph)

Show the whole system faintly, highlight one cluster. Use `.gn.dim` (opacity .22) and
`.ge.dim` for the background; full-colour nodes + a dashed ellipse for the focus.

```html
<ellipse cx="497" cy="178" rx="290" ry="72" fill="none" stroke="var(--accent)"
         stroke-width="1.6" stroke-dasharray="7 7" opacity=".5" class="gn" style="animation-delay:.6s"/>
```

Push the dimmed background nodes to the corners so they never overlap the focal cluster.

## 8. Marker (arrowhead) defs

One marker per colour, referenced by `marker-end`:

```html
<marker id="ar"  markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="var(--accent)"/></marker>
<marker id="arm" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="var(--accent2)"/></marker>
```

`refX="7"` puts the marker tip at the path endpoint, so the endpoint coordinate should sit
exactly on the target node's border.

## 9. Geometry checklist (verify by screenshot, not by reading source)

- Rect at `x,y,w,h`: right `x+w`, left `x`, top `y`, bottom `y+h`, centre `(x+w/2, y+h/2)`.
- Edge **start** on the source border, **end** on the target border. No floating gaps, no
  overshoot into the shape.
- For an orthogonal frame, give connected nodes the **same centre-x** (vertical link) or
  **same centre-y** (horizontal link) so the line is exactly perpendicular to the edge.
- Siblings equidistant from a hub → equal gaps.
- Background/dim layer must not overlap the focal layer.
- After building, run `scripts/shot.sh` and look. Fix in the render, not the source.
