# skills-marketplace

Personal Claude Code plugin marketplace.

## Install

```
/plugin marketplace add LeoHoangLongVu/skills-marketplace
/plugin install project-scaffold@skills-marketplace
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

## Requirements

- Python 3.10+ on PATH (the bundled scripts are stdlib-only).
