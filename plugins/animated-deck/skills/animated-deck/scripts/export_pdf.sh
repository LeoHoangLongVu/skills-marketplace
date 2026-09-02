#!/usr/bin/env bash
# Export a deck to PDF — one slide per landscape page (1280×720 → 13.33"×7.5").
# The interactive deck is untouched; this builds a print variant and renders it.
#
# Usage:  export_pdf.sh deck.html [out.pdf]
# Output: deck.pdf (or the given name) + deck-print.html (the print source, kept)

set -euo pipefail
DECK="${1:?usage: export_pdf.sh deck.html [out.pdf]}"
OUT="${2:-${DECK%.html}.pdf}"
PRINT="${DECK%.html}-print.html"

CHROME="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser || true)"
[ -z "$CHROME" ] && { echo "No Chrome/Chromium found on PATH" >&2; exit 1; }

# Inject a print override before </head>: every slide becomes its own page-sized
# block (the interactive deck stacks them absolutely; print needs them in flow).
OVERRIDE='<style id="__print">
@page{ size:1280px 720px; margin:0; }
html,body{ height:auto; overflow:visible; background:#000; }
#stage{ position:static; display:block; inset:auto; }
#canvas{ position:static; width:1280px; height:auto; transform:none!important; margin:0 auto; border:none; background:transparent; overflow:visible; }
#canvas::before,#canvas::after{ display:none!important; }
.slide{ position:relative!important; inset:auto!important; opacity:1!important; visibility:visible!important; transform:none!important; width:1280px; height:720px; overflow:hidden; background:var(--bg); border:1px solid var(--line); break-after:page; page-break-after:always; }
.slide:last-child{ break-after:auto; page-break-after:auto; }
.slide .r{ opacity:1!important; transform:none!important; transition:none!important; }
.slide::before{ content:""; position:absolute; inset:0; z-index:0; pointer-events:none;
  background:radial-gradient(ellipse 50% 45% at 82% 12%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 60%),
             radial-gradient(ellipse 55% 50% at 12% 92%, color-mix(in srgb, var(--accent2) 10%, transparent), transparent 60%); }
#bar,#counter,#hint,#dots{ display:none!important; }
*{ -webkit-print-color-adjust:exact!important; print-color-adjust:exact!important; }
</style>'

# splice the override in just before </head>
awk -v ins="$OVERRIDE" '/<\/head>/{print ins} {print}' "$DECK" > "$PRINT"

ABS="$(cd "$(dirname "$PRINT")" && pwd)/$(basename "$PRINT")"
"$CHROME" --headless=new --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$ABS" >/dev/null 2>&1

echo "PDF written: $OUT"
echo "Print source kept: $PRINT  (re-run to regenerate after deck edits)"
