# Deck templates — drop-in zone

A **template** is one self-contained `.html` the deck is authored on. It already carries the
scaled 1280×720 canvas, the nav engine, the `.r` reveal system, and reduced-motion support —
so building a deck is just pouring slides into a copy of it. Drop your own template files here
and they become selectable starting points alongside the built-ins.

## What's here

- `../template.html` — the canonical **NEON CYBER** base (and `../template-print.html` for
  PDF). This is the default; everything in the skill assumes its class names.
- `amber.html` — **AMBER** theme, five slide kinds wired up (cover · agenda · divider · body ·
  closing). Good starting point for a dark, terminal-flavoured deck.
- `corporate-light.html` — **CORPORATE NAVY** light theme, consulting-grade: navy header band,
  semantic red/green/blue/orange panels, icon-card / outcome-chip / takeaway-band components,
  an inline stroke-icon library, and three worked poster slides (staged argument · before/after
  contrast · architecture pipeline). Start here for business/enterprise audiences and dense
  one-pagers — genre guide in `references/diagrams/poster.md`.

## Add your own

1. Drop `mytheme.html` in this folder. Easiest sources: scrape an existing contract deck's
   chrome with `python scripts/deck_chrome.py theirs.html -o mytheme.html` (keeps its cover,
   header band and end; blanks the content), run `scripts/pptx_chrome.py` on a brand
   deck (gives you branded backgrounds), or copy an existing template and re-theme the `:root`
   block + fonts (see `references/themes.md` and `references/pptx-template.md`).
2. **Verify it honours the contract:**
   ```bash
   node scripts/check_template.js assets/templates/mytheme.html
   ```
   FAIL = breaks the contract (fix before building); note = worth a look. The check is static —
   after it passes, **render and look**:
   ```bash
   scripts/shot.sh assets/templates/mytheme.html 1 <n>
   ```

## The contract a template must honour

`check_template.js` enforces these so a poured-in deck "just works" and is screenshot-able:

- **Fixed canvas** — `#canvas{width:1280px;height:720px}`, scaled to the viewport with a
  `transform: scale(...)` driven by `innerWidth/1280` (never restyle to fluid layout).
- **Seedable engine** — the nav engine must contain the exact line `var n=slides.length,i=0;`
  (no spaces). `scripts/shot.sh` seeds the start slide by rewriting that token; spaces or a
  different shape mean every screenshot shows slide 1.
- **Inline engine** — one self-contained file; the engine selects `.slide` and handles
  keys/click/swipe/dots/counter. Do not hand-write it per deck.
- **Reveal gated on `.slide.active`** — so reveals and SVG draw-ins replay every time a slide
  is shown; wrap content in `.r` for the staggered fade.
- **`prefers-reduced-motion`** — reset `.slide` too, or `shot.sh`/PDF capture mid-fade and
  full-bleed cover/end slides render washed-out.
- **Slide roles** — tag the opener `data-role="cover"` and the closer `data-role="end"`
  (full-bleed); everything between is `data-role="slide"`. The five slide *kinds* a deck is
  built from — cover · agenda · divider · body · closing — all map onto those three roles
  (agenda/divider/body are `slide`). See SKILL.md "The five slide kinds, and the three roles".
