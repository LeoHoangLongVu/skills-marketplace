#!/usr/bin/env node
// check_template.js — verify a drop-in deck template honours the animated-deck contract.
//
//   node scripts/check_template.js assets/templates/mytheme.html
//
// A template is a single self-contained .html the deck is authored on: it must already carry
// the scaled canvas, the nav engine, the reveal system, and reduced-motion support, so that
// pouring slides into it "just works" and `scripts/shot.sh` can screenshot any slide. This
// does a STATIC check of that contract — it does not render. After it passes, still run
//   scripts/shot.sh <template>.html 1 <n>
// and look at the PNGs (a template can satisfy every check and still look wrong).
//
// Output mirrors check_diagram.js: FAIL = breaks the contract (non-zero exit), NOTE = worth
// a look but not fatal. A template with zero FAILs is good to build on.

const fs = require("fs");
const file = process.argv[2];
if (!file) { console.error("usage: check_template.js <template.html>"); process.exit(2); }
const html = fs.readFileSync(file, "utf8");

const fails = [], notes = [];
const has = re => re.test(html);
const count = re => (html.match(re) || []).length;

// 1. fixed 1280x720 canvas
if (!has(/#canvas\b[^}]*\bwidth\s*:\s*1280px/) || !has(/#canvas\b[^}]*\bheight\s*:\s*720px/))
  fails.push('CANVAS  : no `#canvas{width:1280px;height:720px}` — the deck is a fixed 1280x720 canvas.');

// 2. scale-to-fit engine (transform scale driven by viewport)
if (!has(/transform-origin/) || !has(/scale\(/) || !has(/innerWidth\s*\/\s*1280|1280\b[\s\S]{0,40}innerWidth/))
  notes.push('SCALE   : could not find the scale-to-fit logic (transform-origin + scale() from innerWidth/1280). Confirm the canvas scales to the viewport.');

// 3. shot.sh seed line — REQUIRED so screenshots can target a slide
if (!has(/var\s+n\s*=\s*slides\.length\s*,\s*i\s*=\s*0\s*;/))
  fails.push('SEED    : missing the exact token `var n=slides.length,i=0;`. shot.sh seeds the start slide by rewriting it; without it every screenshot shows slide 1. Collapse any spaces in that line.');
else if (!has(/var n=slides\.length,i=0;/))
  notes.push('SEED    : the seed line has spaces (`var n = slides.length, i = 0;`). It works in a browser but shot.sh will not seed it — collapse to `var n=slides.length,i=0;`.');

// 4. at least one slide + a nav engine
const nSlides = count(/<section[^>]*class="[^"]*\bslide\b/g);
if (nSlides < 1) fails.push('SLIDES  : no `<section class="slide">` found.');
if (!has(/querySelectorAll\(['"][^'"]*\.slide/)) fails.push('ENGINE  : no nav engine (nothing selects `.slide`). Templates ship the engine; do not hand-write it per deck.');

// 5. reveal system gated on .active (so it replays on revisit)
if (!has(/\.slide\.active/)) notes.push('ACTIVE  : no `.slide.active` rule — reveals/animations should be gated on the active slide so they replay on every visit.');
if (!has(/\.r\b/)) notes.push('REVEAL  : no `.r` reveal class seen — wrapping content in `.r` gives the staggered fade-in.');

// 6. reduced-motion (also what makes shot.sh / PDF capture the final frame)
if (!has(/prefers-reduced-motion/))
  notes.push('MOTION  : no `prefers-reduced-motion` block. Add one (reset `.slide` too) or shot.sh/PDF capture mid-fade and full-bleed slides render washed-out.');

// 7. slide roles (informational — full decks want a cover and an end)
const roles = {};
for (const m of html.matchAll(/data-role="([a-z]+)"/g)) roles[m[1]] = (roles[m[1]]||0)+1;
const roleStr = Object.keys(roles).length ? Object.entries(roles).map(([k,v])=>`${k}×${v}`).join(', ') : 'none';
if (!roles.cover || !roles.end)
  notes.push(`ROLES   : data-role tags = {${roleStr}}. A full deck is cover → slide… → end (five kinds: cover · agenda · divider · body · closing). Tag the opener "cover" and the closer "end" so they get full-bleed treatment.`);

// 8. portability — one self-contained file (font <link> is fine; external scripts are not)
if (has(/<script\b[^>]*\bsrc=/)) notes.push('PORTABLE: an external `<script src=…>` is referenced — a template should be one self-contained file (inline the engine).');

// report
const name = file.split("/").pop();
if (fails.length === 0 && notes.length === 0) {
  console.log(`${name}: OK — ${nSlides} slide(s), roles {${roleStr}}. Now render it: scripts/shot.sh ${file} 1 ${nSlides}`);
  process.exit(0);
}
console.log(`${name}: ${fails.length ? "ISSUES" : "OK (with notes)"} — ${nSlides} slide(s), roles {${roleStr}}`);
fails.forEach(f => console.log("  FAIL  " + f));
notes.forEach(n => console.log("  note  " + n));
if (fails.length) { console.log("\nFix the FAILs, then re-run. After it passes, screenshot and look: scripts/shot.sh " + file + " 1 " + nSlides); }
process.exit(fails.length ? 1 : 0);
