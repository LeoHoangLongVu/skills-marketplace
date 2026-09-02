# Timeline & roadmap diagrams — phases, milestones, plans

Use for **events or phases ordered along an axis**: a project roadmap, a release timeline, a
phased rollout, a "how we got here" history. The defining feature is a single axis (usually
horizontal = time) with markers placed along it. Read `references/diagrams/geometry.md`
first; timelines mostly use markers and ticks rather than arrowheads, so the box rules
matter more than the connector rules.

## Layout

- **One axis line** spanning the slide width at a fixed `y` (e.g. y=300 on a 1120×500
  viewBox). Draw it as a plain `.ge` line (it self-draws); no arrowhead unless the timeline
  is explicitly open-ended.
- **Markers** sit on the axis: a small dot (`<circle>`) or tick at each event's x. Position
  x **proportionally to the date** when the spacing is meaningful, or evenly when the phases
  are just ordered. Equal spacing reads as "phases"; proportional spacing reads as "dates".
- **Labels alternate above and below the axis** so adjacent ones never collide: odd markers
  get a box above with a short vertical tick down to the axis, even markers a box below with
  a tick up. Each label box is a normal `.gn` node (date + title), so the padding rules
  apply.
- **Phase bands** (optional): translucent full-height rectangles behind a span of the axis
  to group milestones into phases, with a phase name on top. A band that *encloses* its
  markers is a container (the checker allows the nesting).

## Connector idioms

- **Ticks, not arrows.** The line from a marker to its label is a plain vertical `.ge` line
  with no `marker-end` — it is a leader, not a flow. This also keeps the checker's TIP rule
  out of it (no arrowheads to align).
- If you do show progression *through* phases, one horizontal arrow along the axis is enough;
  do not arrow every gap.
- Keep every tick truly vertical (label box centred over its marker x).

## Worked skeleton (4 phases, alternating labels)

```
        [Q1 · Research]        [Q3 · Beta]
            |                      |
  ──────────●──────────●──────────●──────────●─────────▶  (axis)
                       |                      |
                  [Q2 · Build]          [Q4 · GA]
```

- Axis = one horizontal line; 4 dots evenly spaced on it.
- Labels alternate above/below; each connected by a short vertical tick.
- Markers equally spaced (gaps match) per the geometry guide.

## Checklist

- `node scripts/check_diagram.js deck.html` → `OK` (label boxes pass padding; no floating
  tips because ticks have no arrowheads).
- Markers equally spaced (or proportional and clearly so); ticks vertical and centred.
- Labels alternate sides; no two label boxes overlap; phase bands enclose their markers.
- Dates/version tags verbatim; professional register.
