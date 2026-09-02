# Composition diagrams — pie/donut, pyramid, radial, table

Use for **proportions, hierarchy of size, and structured data** — a share-of-whole, a
tiered pyramid, a hub with satellites, or a comparison grid. These are *not* node-edge
graphs, so most of `geometry.md`'s connector rules do not apply, and `check_diagram.js`
does **not** validate them (it models boxes and arrows). Verify these by **screenshot**.
They are still hand-placed and illustrative: a single pie with a few slices, a 3–4 tier
pyramid, a small table — not data-bound, multi-series charts. For real charting (bar/line/
scatter/time-series with live data) use a plotting tool, not this skill.

## Pie / donut

Draw each slice as a full `<circle>` whose stroke is dashed to show only its arc, using
`pathLength="100"` so the dash array is in **percent** — no circumference maths:

```html
<!-- donut r=110 at (300,230); slices 45 / 30 / 25 % -->
<circle cx="300" cy="230" r="110" fill="none" stroke="#ffb02e" stroke-width="46"
        pathLength="100" stroke-dasharray="45 55" transform="rotate(-90 300 230)"></circle>
<circle cx="300" cy="230" r="110" fill="none" stroke="#4ec9b0" stroke-width="46"
        pathLength="100" stroke-dasharray="30 70" transform="rotate(72 300 230)"></circle>
<circle cx="300" cy="230" r="110" fill="none" stroke="#6aa6ff" stroke-width="46"
        pathLength="100" stroke-dasharray="25 75" transform="rotate(180 300 230)"></circle>
```

- Start angle: `rotate(-90 cx cy)` puts slice 1 at 12 o'clock. Each later slice rotates by
  the **cumulative** percent so far × 3.6° (slice 2 above starts at 45% → 162°, minus the
  90° start = 72°; slice 3 at 75% → 270° − 90° = 180°).
- Put a **legend** beside the pie: one small swatch (a filled `<rect>` in the slice colour)
  per slice with its label and percent. The legend, not labels-on-slices, keeps it readable.
- **Animate a slice by growing its arc from its own start edge — `stroke-dasharray` from
  `0 100` to `<seg> <100−seg>`, not `stroke-dashoffset`.** Offset-based draw makes the arc
  slide in from the gap region instead of growing from the slice's leading edge. Drive the
  target lengths with per-slice CSS vars and use `animation-fill-mode: both` so each slice
  stays *hidden* during its `animation-delay` — with `forwards` the slice shows its resting
  (full) state during the delay, so the whole pie flashes complete, then slices blink out
  and redraw. Keep the resting `stroke-dasharray="<seg> <100−seg>"` on the element as an
  attribute so reduced-motion (`animation:none`) still shows the full ring:

  ```css
  .pie{fill:none}
  .slide.active .pie{animation:sweep .9s ease both}
  @keyframes sweep{from{stroke-dasharray:0 100}to{stroke-dasharray:var(--seg) var(--rest)}}
  @media(prefers-reduced-motion:reduce){.pie{animation:none!important}}  /* keeps rotate() */
  ```
  ```html
  <circle class="pie" ... pathLength="100" stroke-dasharray="45 55"
          style="--seg:45;--rest:55;animation-delay:.4s" transform="rotate(-90 300 240)"/>
  ```
  Or, if you do not need the sweep, just let the whole `svg.graph.r` fade in. Keep slices
  to ~5; more becomes a chart.
- **The slice `rotate()` is positional, not animation — do not let `prefers-reduced-motion`
  reset it.** The template's reduced-motion block sets `transform:none!important`; if that
  selector also matches your pie slices it strips the rotation, every slice snaps back to
  3 o'clock and overlaps, and the pie renders as a broken partial ring — *including in
  `shot.sh` and the PDF export, which both force reduced-motion*. Give slices their own
  class (e.g. `.pie`) and in the reduced-motion block reset only their animation and
  `stroke-dashoffset`, never their `transform`.

## Pyramid

Stacked tiers that widen downward (or a TAM/SAM/SOM that narrows). Draw each tier as a
`<polygon>`: a small triangle at the apex, trapezoids below. For apex `(cx, topY)`, base
half-width `H` at `baseY`, the width at any `y` is `H·(y−topY)/(baseY−topY)`.

```html
<!-- 3 tiers, apex (560,80), base 300..820 at y=320 -->
<polygon points="560,80 473,160 647,160" fill="#13131b" stroke="#ffb02e"></polygon>
<polygon points="473,160 647,160 733,240 387,240" fill="#13131b" stroke="#4ec9b0"></polygon>
<polygon points="387,240 733,240 820,320 300,320" fill="#13131b" stroke="#6aa6ff"></polygon>
```

- Centre each tier's label on its vertical mid-band (`text-anchor="middle"`, x=cx). Put any
  value/explanation as a short note to the side, aligned to the tier.
- Keep tiers equal in height so the slope is constant; 3–4 tiers maximum.

## Radial (circle hub-and-spoke)

A central node with satellites evenly placed on a circle, spokes from the hub to each. This
is the one composition that uses connectors, and they are **radial (diagonal) by design** —
the right-angle rule does not apply, and the checker's `TIP`/diagonal rules will flag the
spokes, so verify by screenshot, not the checker. Place satellite *i* of *n* at angle
`θ = -90° + i·360/n`, centre `(cx + R·cosθ, cy + R·sinθ)`; keep R and the satellite boxes
equal so the ring is even. Spokes run hub-centre → satellite-centre. For concentric "impact
ring" diagrams instead, see the blast-radius pattern in `concept.md`.

## Table (comparison / feature matrix)

The simplest data diagram, and it is plain HTML — reuse the template's `table` component
rather than drawing SVG:

```html
<table>
  <thead><tr><th>Capability</th><th>Free</th><th>Pro</th><th>Enterprise</th></tr></thead>
  <tbody>
    <tr><td>Projects</td><td>3</td><td>Unlimited</td><td>Unlimited</td></tr>
    <tr><td>SSO</td><td>—</td><td>—</td><td>●</td></tr>
  </tbody>
</table>
```

- Respect the density ceiling: heading + **≤4 rows** + one note per slide; split a longer
  matrix across slides.
- For yes/no cells use `●` / `○` (or `Yes` / `—`), not emoji or `✓`/`✕`. Right-align numeric
  columns; left-align the row-label column.
- Colour only to encode meaning (the winning tier, a gap), not for decoration.

## Checklist

- Tables: rendered, ≤4 rows, columns aligned, professional cell content (`●`/`○`/`Yes`/`—`).
- Pie/pyramid/radial: screenshot and inspect — `check_diagram.js` does not validate these.
  Pie slices sum to 100% and start at 12 o'clock; pyramid tiers equal-height; radial ring
  even and spokes symmetric.
- Labels legible, professional register, values/identifiers verbatim.
