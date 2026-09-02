# skills-marketplace

Personal Claude Code plugin marketplace.

## Install

```
/plugin marketplace add LeoHoangLongVu/skills-marketplace
/plugin install project-scaffold@skills-marketplace
/plugin install animated-deck@skills-marketplace
/plugin install graphviz-ai@skills-marketplace
```

## Plugins

### project-scaffold `v1.0.0`

Scaffolds a new project governed by a strict engineering directory contract — a
`CLAUDE.md` directory map (~70 folders across requirements, architecture,
design, src, tests, ops, …), path-scoped rule files, ten ID registers
(`REQ-*`, `ADR`, `DEC`, `RISK`, `ISS`, `CR`) and a requirements traceability
matrix — then keeps every file that enters such a project in the one folder the
map assigns.

What it brings:

- `scripts/scaffold.py` — creates the 20-file project root (contract files +
  seeded registers, no empty directories; the map is the contract). Supports
  `--dry-run`, Python/.NET/other stacks, and `--enforce-hook`.
- `scripts/check_path.py` — validates any path against the map: wrong folders,
  wrong ID prefixes, ID collisions, naming rules, secrets. Modes: `check`,
  `--audit`, `--next-id PREFIX`, `--hook` (PreToolUse guard that blocks illegal
  writes with the reason and the correct location).
- `references/placement.md` — the decision procedure for the hard cases (the
  four homes for "interfaces", ADR vs DEC, the five homes for data artifacts).
- `assets/doc-templates/` — eight document skeletons (ADR, requirement,
  decision, risk, issue, change request, component design, report) with correct
  frontmatter.

Benchmarked with skill-creator: scaffolding conformance 10/10 with the skill vs
1/10 baseline, at ~10× less wall-clock and ~2.4× fewer tokens.

### animated-deck `v1.0.0`

Builds self-contained, animated single-file HTML presentation decks — scale to
any screen, keyboard/click/swipe navigation, animated content and SVG node-edge
diagrams that draw themselves, PDF export, and on-brand theming extracted from a
corporate `.pptx`/`.potx` template. Also does consulting-grade "poster"
one-pagers (numbered stage panels, icon cards, outcome chips, architecture
pipelines).

Bundles three deck templates, a print template, eight diagram-genre references
(flow, timeline, poster, composition, …), an animation cookbook, i18n tooling,
and Chrome-driven PDF/PPTX export scripts.

### graphviz-ai `v1.0.0`

Guide and tooling for the graphviz_master AI integration plus a strict-layout
diagram mode: DotGenerator, LayoutPlanner, VisionClient, a validation pipeline,
and a hand-routed SVG generator (straight/orthogonal arrows, no overlaps,
centered ports, hop bridges at crossings) with an R1–R9 rule audit including a
14px readable-text floor. Exports high-resolution PNG (`--scale`) and
native-shape PowerPoint (`spec_to_pptx.py`).

## Requirements

- Python 3.10+ on PATH.
- `project-scaffold` scripts are stdlib-only.
- `animated-deck` PDF/screenshot export uses a local Chrome/Chromium;
  `.pptx` theming uses `python-pptx`.
- `graphviz-ai` uses Graphviz (`dot`) and, for AI generation/vision analysis,
  an Anthropic API key or Claude Code OAuth token read locally at runtime
  (nothing is stored in the repo).
