#!/usr/bin/env python3
"""Standalone diagram image analyzer using Claude Vision API.

Self-contained script — no graphviz_master package dependency required.
Resolves API key from: explicit arg > ANTHROPIC_API_KEY env > Claude Code OAuth.

Usage:
    python analyze_image.py diagram.png
    python analyze_image.py diagram.png --output results.json
    python analyze_image.py img1.png img2.png img3.png --batch
    python analyze_image.py diagram.png --model claude-sonnet-4-6
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
#  Auth: 3-tier API key resolution
# --------------------------------------------------------------------------- #

_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"


def _load_oauth_token() -> str | None:
    if not _CREDENTIALS_PATH.exists():
        return None
    try:
        creds = json.loads(_CREDENTIALS_PATH.read_text(encoding="utf-8"))
        oauth = creds.get("claudeAiOauth", {})
        token = oauth.get("accessToken", "")
        if not token:
            return None
        expires_at = oauth.get("expiresAt", 0)
        if expires_at and int(time.time() * 1000) > expires_at:
            return None
        scopes = oauth.get("scopes", [])
        if "user:inference" not in scopes:
            return None
        return token
    except (json.JSONDecodeError, OSError):
        return None


def resolve_api_key(explicit_key: str | None = None) -> str:
    if explicit_key:
        return explicit_key
    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        return env_key
    oauth_token = _load_oauth_token()
    if oauth_token:
        return oauth_token
    raise ValueError(
        "Anthropic API key required. Provide one via:\n"
        "  1. --api-key argument\n"
        "  2. ANTHROPIC_API_KEY environment variable\n"
        "  3. Claude Code OAuth (login with 'claude' CLI)"
    )


# --------------------------------------------------------------------------- #
#  Image encoding
# --------------------------------------------------------------------------- #

def encode_image(image_path: Path) -> tuple[str, str]:
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    ext = image_path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")
    return data, media_type


# --------------------------------------------------------------------------- #
#  Analysis prompt
# --------------------------------------------------------------------------- #

ANALYSIS_PROMPT = """Analyze this diagram image and extract LAYOUT and ALIGNMENT properties.
Respond ONLY with a valid JSON object (no markdown, no explanation).

{
  "flow_direction": "TB|BT|LR|RL|radial|grid|unknown",
  "rank_count": "<integer, number of distinct ranks/levels>",
  "nodes_per_rank": ["<int>", "<int>"],
  "rank_separation": "<float, vertical gap between ranks / avg node height>",
  "node_separation": "<float, horizontal gap between sibling nodes / avg node width>",
  "rank_balance": "centered|left-heavy|right-heavy|staggered",
  "node_count": "<integer>",
  "node_shape": "rectangle|rounded|circle|diamond|hexagon|other",
  "nodes_equal_width": "<true|false>",
  "nodes_equal_height": "<true|false>",
  "avg_node_width_ratio": "<0.0-1.0, avg node width / diagram content width>",
  "avg_node_height_ratio": "<0.0-1.0, avg node height / diagram content height>",
  "node_text_alignment": "left|center|right",
  "node_internal_padding": "tight|medium|generous",
  "diagram_margin": "none|small|medium|large",
  "has_edges": "<true|false>",
  "edge_style": "straight|ortho|curved|spline|polyline|none",
  "edge_arrows": "forward|back|both|none",
  "edge_labels_present": "<true|false>",
  "has_clusters": "<true|false>",
  "cluster_count": "<integer>",
  "cluster_style": "boxed|colored_bg|dashed_border|swimlane|",
  "nesting_depth": "<integer, 1=flat, 2=one level of groups>",
  "columns": "<integer, 0 if not grid-based>",
  "rows": "<integer, 0 if not grid-based>",
  "title_present": "<true|false>",
  "has_legend": "<true|false>"
}

Focus ONLY on layout structure — spacing, alignment, edge routing, grouping."""


# --------------------------------------------------------------------------- #
#  API call with retry
# --------------------------------------------------------------------------- #

def analyze_image(
    client,
    model: str,
    image_path: Path,
    *,
    max_retries: int = 3,
) -> dict:
    image_data, media_type = encode_image(image_path)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": ANALYSIS_PROMPT,
                },
            ],
        }
    ]

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                messages=messages,
            )
            text = response.content[0].text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [line for line in lines if not line.strip().startswith("```")]
                text = "\n".join(lines)
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_response": text, "error": "non_json_response"}
        except Exception as e:
            err_str = str(e).lower()
            if "rate" in err_str or "429" in err_str or "overloaded" in err_str:
                wait = 2 ** (attempt + 1)
                print(f"  [!] Rate limited, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise

    raise RuntimeError(f"Failed after {max_retries} retries")


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze diagram images using Claude Vision API"
    )
    parser.add_argument("images", nargs="+", help="Image file(s) to analyze")
    parser.add_argument("--output", "-o", help="Output JSON file path")
    parser.add_argument("--model", default="claude-opus-4-6", help="Claude model ID")
    parser.add_argument("--api-key", help="Anthropic API key (overrides env/OAuth)")
    parser.add_argument(
        "--batch", action="store_true",
        help="Batch mode: analyze multiple images with 1s delay between calls",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Seconds between batch API calls (default: 1.0)",
    )
    args = parser.parse_args()

    try:
        import anthropic
    except ImportError:
        print("Error: pip install anthropic>=0.39.0", file=sys.stderr)
        sys.exit(1)

    api_key = resolve_api_key(args.api_key)
    client = anthropic.Anthropic(api_key=api_key)

    results = {}
    image_paths = [Path(p) for p in args.images]

    for i, img in enumerate(image_paths):
        if not img.exists():
            print(f"  [!] File not found: {img}", file=sys.stderr)
            results[str(img)] = {"error": "file_not_found"}
            continue

        print(f"  [{i + 1}/{len(image_paths)}] Analyzing {img.name}...", file=sys.stderr)
        try:
            result = analyze_image(client, args.model, img)
            results[str(img)] = result
        except Exception as e:
            print(f"  [!] Error: {e}", file=sys.stderr)
            results[str(img)] = {"error": str(e)}

        if args.batch and i < len(image_paths) - 1:
            time.sleep(args.delay)

    output = json.dumps(results, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(output, encoding="utf-8")
        print(f"  Written to: {out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
