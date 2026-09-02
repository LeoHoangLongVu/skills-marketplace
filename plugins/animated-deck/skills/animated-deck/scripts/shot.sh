#!/usr/bin/env bash
# Screenshot specific slide(s) of a deck for visual verification.
# Geometry/overflow bugs are invisible in source — always render and look.
#
# Usage:
#   shot.sh deck.html 3          # screenshot slide 3 (1-indexed)
#   shot.sh deck.html 1 16       # screenshot slides 1..16
#   shot.sh deck.html            # screenshot slide 1
#
# Output: /tmp/shot_<deck>_<pid>_<n>.png  (unique per run so parallel invocations
# never overwrite each other; the exact paths are printed at the end — open/Read them)
#
# Uses --force-prefers-reduced-motion so reveals render at their FINAL state
# instantly. Animated captures under headless virtual-time are flaky (a slide
# can come out blank though it is fine in a real browser); reduced-motion makes
# the capture deterministic. To preview the animation itself, open in a real browser.

set -euo pipefail
DECK="${1:?usage: shot.sh deck.html [from] [to]}"
FROM="${2:-1}"
TO="${3:-$FROM}"

CHROME="$(command -v google-chrome || command -v google-chrome-stable || command -v chromium || command -v chromium-browser || true)"
if [ -z "$CHROME" ]; then  # Windows (git-bash): fall back to installed Chrome/Edge
  for c in "/c/Program Files/Google/Chrome/Application/chrome.exe" \
           "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
           "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe" \
           "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"; do
    [ -f "$c" ] && CHROME="$c" && break
  done
fi
[ -z "$CHROME" ] && { echo "No Chrome/Chromium found on PATH" >&2; exit 1; }

# On Windows, Chrome needs Windows-style paths for file:// URLs and --screenshot
W(){ if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }

ABS="$(cd "$(dirname "$DECK")" && pwd)/$(basename "$DECK")"
OUT=()
PROFILE="/tmp/shot_profile_$$"   # isolated profile: never clash with a running desktop Chrome
NAME="$(basename "$DECK" .html)"
for ((S=FROM; S<=TO; S++)); do
  TMP="/tmp/shot_src_${NAME}_$$_$S.html"
  # start the deck on slide S by seeding the engine's index
  sed "s/var n=slides.length,i=0;/var n=slides.length,i=$((S-1));/" "$ABS" > "$TMP"
  PNG="/tmp/shot_${NAME}_$$_$S.png"
  "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
    --user-data-dir="$(W "$PROFILE")" \
    --force-prefers-reduced-motion --window-size=1280,720 \
    --screenshot="$(W "$PNG")" "file://$(W "$TMP")" >/dev/null 2>&1 || true
  rm -f "$TMP"
  [ -f "$PNG" ] && OUT+=("$PNG")
done
rm -rf "$PROFILE"

echo "Rendered ${#OUT[@]} slide(s):"
printf '  %s\n' "${OUT[@]}"
echo "Open or Read these PNGs to inspect geometry, overlap, and overflow."
