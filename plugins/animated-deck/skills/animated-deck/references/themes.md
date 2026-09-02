# Themes

A theme is just the `:root` block in the template. Swap it and the whole deck restyles —
every component reads from these CSS variables. Two presets ship inside `template.html`;
more below. Pick one fully; do not mix palettes.

## How the variables are used

- `--bg / --bg2 / --panel / --panel2` — backgrounds, darkest → lightest.
- `--line / --line2` — borders (subtle → visible).
- `--ink / --ink2 / --ink3` — text (primary → muted → faint).
- `--accent / --accent2` — the two signature colours (titles, edges, glows). Point these at
  whichever named colours the theme wants to lead with.
- Named colours `--cyan --mag --blue --green --amber --red --violet` — used by stat values,
  diagram node classes (`.gn.a/b/c/d`), calc cells, etc. Keep all seven defined even in a
  monochrome theme (point unused ones at near-neighbours) so components never break.

## Preset: NEON CYBER (default)

Dark navy, cyan + magenta, glow. Futuristic / technical. Already active in the template.

```
--bg:#080b1c; --bg2:#0e1430; --panel:#161d40; --panel2:#1e2752;
--line:#2a3360; --line2:#3c4888;
--ink:#f1f4ff; --ink2:#b4bdec; --ink3:#8089bd;
--cyan:#1ff0e6; --mag:#ff45e0; --blue:#5b8cff; --green:#52ffa8; --amber:#ffd24d; --red:#ff5e86; --violet:#b98cff;
--accent:var(--cyan); --accent2:var(--mag);
```

## Preset: TERMINAL AMBER

Near-black, amber + teal, mono grid. Restrained / engineering. (Commented in the template.)

```
--bg:#09090c; --bg2:#0d0d12; --panel:#13131b; --panel2:#181821;
--line:#26262f; --line2:#34343f;
--ink:#eceae2; --ink2:#a6a4af; --ink3:#6a6874;
--cyan:#4ec9b0; --mag:#c77dba; --blue:#6aa6ff; --green:#7ee787; --amber:#ffb02e; --red:#ff6b6b; --violet:#c77dba;
--accent:var(--amber); --accent2:var(--cyan);
```

## Preset: CLEAN LIGHT

For a corporate / print-friendly look. Lighten backgrounds, darken ink, keep one accent.
Reduce glow (the `text-shadow` and `drop-shadow` blurs read as noise on light backgrounds —
trim them in the `.eyebrow`/`h1`/`.ge` rules if using a light theme).

```
--bg:#f6f7fb; --bg2:#eef1f7; --panel:#ffffff; --panel2:#eef1f7;
--line:#dce1ec; --line2:#c3cbdb;
--ink:#10131c; --ink2:#3b4360; --ink3:#727b96;
--cyan:#0a8f86; --mag:#b03a8f; --blue:#2f5bd0; --green:#1f9d57; --amber:#c98a00; --red:#cc3355; --violet:#7a52c0;
--accent:var(--blue); --accent2:var(--cyan);
```

## Preset: CORPORATE NAVY (light)

The consulting / enterprise look — white canvas, navy header band, colour used *semantically*
(red = current pain, green = outcome, blue = process, orange = supporting system; see
`references/diagrams/poster.md`). Shipped ready to use as
`assets/templates/corporate-light.html` with the icon library and poster components wired in —
copy that template rather than re-theming the NEON base. Its tokens:

```
--bg:#ffffff; --bg2:#f3f5fa; --panel:#ffffff; --panel2:#f7f9fc;
--line:#dbe1ec; --line2:#c2cbdc;
--ink:#182238; --ink2:#3d4763; --ink3:#6f7994;
--navy:#141f52; --navy2:#25379b;
--blue:#2456c4; --green:#1d8a4b; --red:#c22f3d; --amber:#d9720f; --violet:#5f46b4; --cyan:#0f7f96;
--accent:var(--blue); --accent2:var(--green);
```

Fonts default to the system grotesque stack (`Segoe UI` / Helvetica) — the correct register
for corporate decks, and it keeps the file offline-safe. Swap in the brand face via
`--font-head` / `--font-body` when one is supplied (`pptx_theme.py --light` emits both).

## Making a new theme

1. Choose two signature colours → `--accent`, `--accent2`.
2. Build a 4-step background ramp (`--bg` darkest) and a 3-step ink ramp.
3. Keep contrast high: `--ink` on `--bg` should be very legible; `--ink3` is for captions only.
4. Define all seven named colours so diagram/stat components keep working.
5. On light themes, cut the neon glows (shadow blur) or they look muddy.

## Fonts

The template uses a monospace stack (`JetBrains Mono` → system mono). For a non-technical
deck, swap `--mono` for a display + body pairing loaded via one `@import` at the top of the
`<style>` (e.g. a geometric sans for headings). Keep to two families. If the deck must work
fully offline, stay with the system stack — `@import` needs network at view time.
