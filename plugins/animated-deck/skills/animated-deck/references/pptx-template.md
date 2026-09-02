# Themeing the deck from a PowerPoint template

When the user hands you a brand deck or template (`.pptx` / `.potx`), match the deck to it
instead of picking a preset. A PowerPoint file is a zip of OOXML; `scripts/pptx_theme.py`
reads the brand colour scheme, fonts, slide size and embedded images out of it and emits a
`:root{}` block that drops straight over the template's theme.

```bash
python3 scripts/pptx_theme.py BRAND.potx                 # report + :root block
python3 scripts/pptx_theme.py BRAND.potx --light         # light-background variant
python3 scripts/pptx_theme.py BRAND.potx --out theme.css # also write the block to a file
python3 scripts/pptx_theme.py BRAND.potx --logo logo.png # extract the largest image
```

## What it pulls, and where it goes

The script reads `ppt/theme/theme1.xml` (colours + fonts), `ppt/presentation.xml` (slide
size) and lists `ppt/media/*`. It maps the brand into the deck's variables:

| PowerPoint slot | Deck variable(s) | Notes |
|---|---|---|
| `accent1` | `--accent` | the dominant brand colour |
| most saturated, most opposite accent | `--accent2` | the secondary/contrast accent |
| `accent1…6` (by nearest hue) | `--blue --teal --green --amber --red --violet` | the diagram hue set; gaps fall back to the nearest accent |
| `dk2`/`dk1` (dark preset) or `lt1`/`lt2` (`--light`) | `--bg --bg2 --panel --panel2 --line --line2` | neutral surfaces, derived by tinting |
| `lt1`/`dk1` | `--ink --ink2 --ink3` | text tiers |
| `majorFont` / `minorFont` | `--font-head` / `--font-body` | brand faces + a web substitute |

## Steps to apply it

1. **Run the script and paste the `:root` block over the template's theme.** It replaces the
   NEON/AMBER `:root` in `assets/template.html`. The deck keeps working — every component
   reads these variables.
2. **Wire the fonts.** The block adds `--font-head` and `--font-body`, each listing the
   brand face first and a distinctive web substitute second (the exact Office font is rarely
   web-available, so the substitute is what actually renders unless the user supplies the
   font file). Add a Google Fonts `<link>` for the substitute, then point type at the vars:
   `h1,h2{font-family:var(--font-head)}` and `body,.lede,.note2{font-family:var(--font-body)}`.
   Keep `--mono` for code, captions and diagram text — monospace is what makes the diagrams
   read as precise. If the user provides the real `.ttf/.otf`, add an `@font-face` and the
   brand face renders exactly.
3. **Place the logo.** `--logo out.png` writes the largest embedded image (usually the mark).
   Drop it small in a title-slide corner and optionally a footer; never stretch it, and leave
   clear space around it. Inline it as a data URI if you want the deck to stay a single file.
4. **Light vs dark.** By default the script keeps the deck dark and recolours it with the
   brand accents (most brand decks read best this way and the deck's glow/grid suit dark).
   Use `--light` to match a light corporate template exactly — and when you do, tone the
   atmosphere down so it does not look muddy on a pale background: drop or lighten the
   `#canvas::before` glow and `#canvas::after` grid opacity, and remove the `text-shadow`
   glows on `.eyebrow`/`h1`/`.stat .v`. The structure is identical; only the atmosphere layer
   changes.
5. **Slide size.** The report prints the aspect and a recommended `#canvas` size (16:9 →
   `1280x720`, 4:3 → `960x720`). Set `#canvas{width;height}` accordingly; the scale-to-fit
   engine handles any size, and the diagram `viewBox`es are relative so they still fit.

## Stripping a whole deck to a blank template (pptx_chrome.py)

When the user wants to **reuse a deck's exact look but drop its content** — "remove the
content, leave the template, I'll add my own" — use `scripts/pptx_chrome.py`. The recurring
DESIGN of a deck is whatever appears unchanged slide after slide (logos, colour bands,
backgrounds, footers); the CONTENT is unique per slide. The script drives **LibreOffice via
UNO**: it opens the deck, removes every shape whose signature (position + size + text) does
not recur on at least a quarter of the slides, and exports the blanked deck to PDF — all
inside LibreOffice. It then rasterises the PDF, dedupes identical results, and emits a
self-contained HTML deck where each unique blank template is a slide with an empty `.content`
layer for new content. General — no per-template tuning.

**Why UNO and not a Python rewrite.** Re-packing a PowerPoint `.pptx` with Python
(`zipfile`, ElementTree, or python-pptx) makes LibreOffice mis-scale grouped vector logos and
text — an *anisotropic squash* (a wide SVG wordmark renders short, italic text renders
compressed) — even when the shape bytes are byte-identical and only the zip container was
rewritten. The pristine file renders perfectly; any Python repackage does not. Editing and
exporting through LibreOffice's own document model sidesteps this completely, so SVG logos
and text come out exactly as PowerPoint intends. (If you ever see logos/text vertically
squashed in the output, something reintroduced a Python zip round-trip — keep it on the UNO
path.)

The trade-off: genuinely one-off cover/section art (a unique full-bleed photo) does not
recur, so it is treated as content and dropped — the cover comes out blank. Recurring section
labels (an eyebrow that repeats on many slides) are kept as furniture; clear them by hand if
the user wants a truly empty header.

**Header SVG-logo repair.** Even via UNO, LibreOffice stretches an SVG logo that sits in a
non-uniformly-scaled PowerPoint group to its (wide) box, rendering the logo squashed vs
PowerPoint (its viewBox aspect is ignored). After rendering, the script detects a transparent
wide-aspect (~3:1) colour wordmark in `ppt/media`, knocks it out to white, and re-composites
it on every coloured-band content slide at `FPT_BOX` — the geometry PowerPoint uses, measured
from a reference screenshot of the master. If a deck's header logo lands wrong, compare a
PowerPoint screenshot and adjust `FPT_BOX`. (Verify against a real PowerPoint render: the
LibreOffice render is faithful to LibreOffice, which is not always faithful to PowerPoint for
grouped vector art — the HTML deck itself does not distort, confirmed via playwright.)

```bash
python3 scripts/pptx_chrome.py INPUT.pptx -o template.html       # any deck
python3 scripts/pptx_chrome.py INPUT.pptx -o out.html --keep-dupes
python3 scripts/pptx_chrome.py INPUT.pptx -o out.html --thr 0.4   # stricter "recurring" cutoff
# custom template: point the header-logo repair at the right place / asset
python3 scripts/pptx_chrome.py INPUT.pptx -o out.html \
    --logo-box 0.64,0.07,0.80,0.16 --logo-file white_logo.png
python3 scripts/pptx_chrome.py INPUT.pptx -o out.html --logo-fix off
```

Options for custom templates: `--thr` sets how often a shape must recur to count as chrome;
`--logo-box "x0,y0,x1,y1"` (slide fractions) places the repaired header logo; `--logo-file`
supplies a clean white logo PNG (otherwise one is auto-detected from the deck's media);
`--logo-fix off` disables the repair. The repair is a no-op unless the deck has a coloured top
band over a white body, so non-matching templates pass through untouched.

- Output is one `.html`; each `<section class="slide">` has the rendered layout as a
  full-bleed background `<img class="bg">` and an empty `<div class="content">` above it. Add
  your slide content inside `.content` (absolute-positioned over the template).
- Requires **libreoffice/soffice with the Python-UNO bridge** (`python3 -c "import uno"` must
  work), **pdftoppm** (poppler-utils) and Pillow. Fonts/effects are LibreOffice's
  interpretation of the deck — screenshot to confirm.
- The script launches a private headless LibreOffice instance on a socket and terminates it
  when done; it does not touch a running Office session.
- The background is a raster image of the blanked slide, so the chrome is pixel-faithful but
  not re-editable. That is the point: a backdrop to build on, not an editable master.
- The canvas aspect is taken from the actual rendered pixels (not the EMU slide size, which
  can disagree with LibreOffice's page) and backgrounds use `object-fit:contain`, so text is
  never squished vertically/horizontally — a mismatch letterboxes instead of distorting.
- Flat (non-photo) templates are stored as **lossless PNG** so header text stays crisp —
  JPEG rings around text on flat colour and reads as "compressed". Only photographic slides
  fall back to JPEG (`--quality`, default 92). Backgrounds are rendered/kept at ~2560px wide
  (≈2× the 1280 canvas) so the logo and chrome baked into the image stay sharp when the deck
  is shown fullscreen above 1280px — at 1600px the header logo visibly pixelates on a large
  screen. That makes the file larger; it is the right trade for a presentation deck.
- Tuning: the recurrence threshold is 25% of slides. If wanted chrome is dropped, lower it;
  if stray content survives, raise it (edit `thr` in the script).
- Use `pptx_theme.py` (colours/fonts) vs `pptx_chrome.py` (blank slides with chrome kept) per
  need; they are complementary.

## Building a real deck on the extracted template

`pptx_chrome.py` gives you blank backgrounds tagged `data-role="cover" | "slide" | "end"`. To
turn them into an actual presentation, **reuse those rendered backgrounds as each slide's
background image and overlay only your own text and diagrams** — never fabricate a cover or
closing (e.g. a flat blue panel). The template's real cover (usually a branded photo) and end
(a closing visual) are what make the deck look authentic; an invented solid-colour cover/end
reads as off-brand, which is the single most common mistake here.

- **Cover** = the template's `cover` background + your deck title overlaid in the zone the
  layout leaves clear (e.g. a colour band or photo strip). Match the text colour to that zone
  (dark on a light/yellow band, white on a dark/photo area).
- **Body slides** = the `slide` background (header band, logos, footer already baked in) +
  your slide title overlaid white in the band + your content/diagram in the white body. Do
  not redraw the band or re-add the logos — they are in the image.
- **End** = the template's `end` background + a one-line closing overlaid in its band.
- Pull the three backgrounds straight out of the pptx_chrome HTML — one `<img class="bg">`
  data URI per `data-role` — and reuse them verbatim. You add text and SVG diagrams on top;
  you never recreate the chrome.
- A deck is **one cover → a run of body slides → one end** (the three roles). For a multi-
  topic deck, repeat the `slide` background for each content slide.
- **Full-bleed cover/end gotcha:** in the `prefers-reduced-motion` block reset `.slide` too
  (`.slide{transition:none!important}`). Otherwise `shot.sh` and the PDF export capture the
  slide mid-fade and the cover/end background renders washed-out (a real-browser view is fine,
  so this is easy to miss).

### Body-slide layout grid (consistent across every slide)

A banded template wants the *same* skeleton on every body slide; that consistency is what
makes a 15-slide deck read as one deck and not fifteen. Three fixed zones:

1. **Section tag → in the header band, not the body.** Put a small running label
   (`NN · SECTION`, light tint on the dark band) absolutely positioned inside the rendered
   header band (e.g. `position:absolute; left:72px; top:48px`). This is the slide's section
   marker; do **not** also put a numbered eyebrow in the white body — one or the other, and
   the band is where the audience expects the running number (it is where the template's own
   `NN / Deck Name` footer sat).
2. **Title → pinned at a fixed top, identical on every slide.** Do **not** vertically centre
   the whole content block on a banded slide — when each slide centres independently the title
   floats to a different height every time, which is the most common "looks inconsistent"
   complaint. Pin the title just below the band (`.stage{top:<band+8>;…;justify-content:flex-
   start}`) so every title lands on the same line. If a slide needs a badge (e.g.
   "Recommended"), put it on the **title's baseline** (a flex row, `justify-content:space-
   between`) so the title's Y never moves.
3. **Content → centred in the area *below* the pinned title.** Give the body its own wrapper
   (`flex:1; display:flex; flex-direction:column; justify-content:center`) so cards / tables /
   diagrams sit centred in the open area under the title. Because the title is outside this
   wrapper, a tall table can no longer push the title up into the band (the failure you get if
   you centre the whole stage and the content overflows). For a table taller than the area,
   switch that wrapper to `flex-start` so it grows downward instead of overflowing both ways.

**Numbering must mirror the agenda exactly.** The band tag's `NN` and section name are the
same numbers and labels as the agenda lines, in the same order, and they must be contiguous
across the run (every slide of section 03 tagged `03`, then section 04, …). An off-by-one tag
(`02 · Objective` when Objective is agenda item 01) or a section that jumps `03 → 04 → 03`
reads as a mistake. Decide the agenda sections first, then tag each slide with its section.

## Scraping an HTML deck's chrome (deck_chrome.py)

When the template is another **HTML deck** — a previous deliverable, a drop-in template, or
"make one like our last deck" — the equivalent of pptx_chrome is `scripts/deck_chrome.py`:

```bash
python3 scripts/deck_chrome.py THEIRS.html -o starter.html          # scrape chrome
python3 scripts/deck_chrome.py THEIRS.html -o starter.html --body 3 # pick a specific body slide
node scripts/check_template.js starter.html && scripts/shot.sh starter.html 1 3
```

It expects a contract deck (`<section class="slide">`, data-role cover/slide/end) and emits a
**3-slide starter**: the cover and end slides verbatim, plus one body slide reduced to its
chrome — top-level children whose tag is `header` or whose class matches
band/logo/footer-style names are kept; everything else is dropped and replaced with an empty
`<div class="content">` layer. All CSS, icon `<defs>` and the nav engine carry over
untouched, so the starter passes `check_template.js` immediately.

Author the deck on the starter: copy the blank body slide once per content slide, retitle
its band per slide (the band's kicker/title text is per-slide content), and pour content
into `.content`. The same rules as the pptx path apply: **never invent a replacement cover
or closing, and never deliver a placeholder wordmark** — if the scraped chrome carries one
(e.g. corporate-light's ACME mark), swap in the real brand or remove it.

If LibreOffice is unavailable for the pptx path, this is also the fallback pattern: apply
`pptx_theme.py`'s palette/fonts/logo, rebuild the band/cover/end once against a screenshot
of the PowerPoint master, then scrape your own rebuild with `deck_chrome.py` so every later
deck on that brand starts from the same starter.

## Caveats

- Only the colour scheme, fonts and slide size are lifted. Gradient/effect styles
  (`fmtScheme`), slide-master background images, and per-layout placeholders are **not**
  reproduced — this themes the deck on-brand, it does not clone the template's layouts.
- Hue-mapped diagram colours (`--blue`…`--violet`) are a best-effort assignment; if two land
  on the same accent or a hue reads wrong in a diagram, swap that one variable by hand.
- The script is stdlib-only and never executes anything from the file. Still, **screenshot
  the result** (`scripts/shot.sh`) — a brand palette can blow contrast (e.g. a pale accent on
  the dark surface); nudge `--ink`/`--accent` if text or edges are hard to read.
