#!/usr/bin/env python3
"""deck_chrome.py - scrape the chrome (cover / header band / end) out of an
animated-deck HTML file and emit a blank branded starter template.

Usage:
    python deck_chrome.py THEIRS.html -o starter.html [--body N]

Given any deck built on the animated-deck engine contract (fixed #canvas,
<section class="slide"> slides, data-role cover/slide/end), the output keeps:

  - the whole <head>, all CSS, hidden icon <defs> and the nav engine VERBATIM
  - the cover slide VERBATIM
  - ONE body slide reduced to its chrome (header band / logo / footer kept,
    content replaced by an empty  <div class="content">  layer)
  - the end slide VERBATIM

so you get a blank 3-slide starter that still passes check_template.js.
Author the new deck by copying the blank body slide once per content slide.

Why this exists: a supplied template's cover, header band and closing page are
brand assets. A generated deck must inherit them exactly - not approximate
them, and never ship placeholder branding. Same doctrine as pptx_chrome.py,
for HTML templates.

Options:
  --body N   use the Nth body slide (1-indexed) as the blank chrome carrier
             (default: the first body slide that has a chrome child, else the
             first body slide)

Limits: expects contract decks (sections are not nested). For arbitrary
non-contract HTML, scrape by hand. Verify the output like any template:
  node scripts/check_template.js starter.html && scripts/shot.sh starter.html 1 3
"""
import argparse
import re
import sys
from pathlib import Path

VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input",
             "link", "meta", "source", "track", "wbr"}
# One tag or comment; the attr part tolerates quoted '>' characters.
TOKEN = re.compile(
    r'<!--[\s\S]*?-->|<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)>')
SECTION = re.compile(r'<section\b((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)>([\s\S]*?)</section>')
CHROME_CLASS = re.compile(r'\b(band|topbar|banner|chrome|blogo|logo|wordmark|footer|slidefoot)\b')


def top_level_children(inner: str):
    """Split a section's inner HTML into its top-level element/comment chunks.
    Bare top-level text is dropped (it is content, not chrome)."""
    chunks, depth, start = [], 0, None
    for m in TOKEN.finditer(inner):
        if m.group(0).startswith('<!--'):
            continue  # drop comments
        closing = m.group(1) == '/'
        name = m.group(2).lower()
        self_close = (m.group(3) or '').rstrip().endswith('/')
        if not closing and (name in VOID_TAGS or self_close):
            if depth == 0:
                chunks.append(inner[m.start():m.end()])
            continue
        if not closing:
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0 and start is not None:
                chunks.append(inner[start:m.end()])
                start = None
            if depth < 0:  # tolerate a stray closer
                depth = 0
    return chunks


def open_tag_info(chunk: str):
    m = re.match(r'<([a-zA-Z][a-zA-Z0-9-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)>', chunk)
    if not m:
        return "", ""
    attrs = m.group(2) or ""
    cm = re.search(r'class="([^"]*)"', attrs) or re.search(r"class='([^']*)'", attrs)
    return m.group(1).lower(), (cm.group(1) if cm else "")


def is_chrome(chunk: str) -> bool:
    tag, cls = open_tag_info(chunk)
    return tag == "header" or bool(CHROME_CLASS.search(cls))


def main():
    ap = argparse.ArgumentParser(description="Scrape cover/band/end chrome from a deck html")
    ap.add_argument("deck")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--body", type=int, default=0, help="1-indexed body slide to use as chrome carrier")
    args = ap.parse_args()

    html = Path(args.deck).read_text(encoding="utf-8", errors="replace")
    secs = []
    for m in SECTION.finditer(html):
        attrs = m.group(1) or ""
        if not re.search(r'class="[^"]*\bslide\b', attrs) and not re.search(r"class='[^']*\bslide\b", attrs):
            continue
        role_m = re.search(r'data-role="([a-zA-Z]+)"', attrs)
        secs.append({
            "start": m.start(), "end": m.end(), "html": m.group(0),
            "attrs": attrs, "inner": m.group(2),
            "role": role_m.group(1) if role_m else None,
        })
    if len(secs) < 2:
        sys.exit(f"Found only {len(secs)} <section class=\"slide\"> block(s) - not a contract deck.")

    cover = next((s for s in secs if s["role"] == "cover"), secs[0])
    end = next((s for s in secs if s["role"] == "end"), secs[-1])
    bodies = [s for s in secs if s is not cover and s is not end]
    if not bodies:
        sys.exit("No body slide between cover and end - nothing to blank.")

    if args.body:
        if not (1 <= args.body <= len(bodies)):
            sys.exit(f"--body {args.body} out of range (1..{len(bodies)})")
        body = bodies[args.body - 1]
    else:
        body = next((b for b in bodies if any(is_chrome(c) for c in top_level_children(b["inner"]))),
                    bodies[0])

    kept, dropped = [], []
    for chunk in top_level_children(body["inner"]):
        (kept if is_chrome(chunk) else dropped).append(chunk)
    blank_inner = "\n      " + "\n      ".join(kept) if kept else ""
    blank_inner += '\n      <div class="content"><!-- pour this slide\'s content here --></div>\n    '
    blank_body = f'<section{body["attrs"]}>{blank_inner}</section>'

    out_html = (html[:secs[0]["start"]]
                + cover["html"] + "\n\n    " + blank_body + "\n\n    " + end["html"]
                + html[secs[-1]["end"]:])
    Path(args.out).write_text(out_html, encoding="utf-8")

    kept_desc = [f"<{open_tag_info(c)[0]} class=\"{open_tag_info(c)[1]}\">" for c in kept] or ["(none - template has bare body slides)"]
    print(f"Scraped {Path(args.deck).name}: {len(secs)} slides -> 3-slide starter {args.out}")
    print(f"  cover : {'data-role=cover' if cover['role'] == 'cover' else 'first slide (no role tag)'} kept verbatim")
    print(f"  body  : slide {secs.index(body) + 1} blanked; chrome kept: {', '.join(kept_desc)}; {len(dropped)} content block(s) dropped")
    print(f"  end   : {'data-role=end' if end['role'] == 'end' else 'last slide (no role tag)'} kept verbatim")
    print("Next: node scripts/check_template.js OUT && scripts/shot.sh OUT 1 3 - then copy the blank")
    print("body slide once per content slide. Replace any placeholder wordmark with the real brand.")


if __name__ == "__main__":
    main()
