#!/usr/bin/env python3
"""Standalone DOT diagram generator using Claude API.

Self-contained script — no graphviz_master package dependency required.
Resolves API key from: explicit arg > ANTHROPIC_API_KEY env > Claude Code OAuth.

Usage:
    python generate_dot.py "Login flow with 5 steps" --type process
    python generate_dot.py "Company org chart" --type hierarchy --style corporate
    python generate_dot.py "Data pipeline" --type process --output pipeline.dot
    python generate_dot.py "CI/CD stages" --type process --model claude-sonnet-4-6
"""

from __future__ import annotations

import argparse
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
#  Style guides & system prompt
# --------------------------------------------------------------------------- #

STYLE_GUIDES = {
    "modern": (
        "Use a clean, modern aesthetic with rounded rectangles, subtle gradients, "
        "a professional color palette (blues, teals, grays), and clear sans-serif "
        "fonts. Emphasize whitespace and visual breathing room."
    ),
    "corporate": (
        "Use a formal corporate style with sharp-cornered boxes, a conservative "
        "color palette (navy, dark gray, white), and clear hierarchy. Suitable "
        "for executive presentations and formal documents."
    ),
    "minimal": (
        "Use a minimalist design with simple shapes, thin lines, limited colors "
        "(black, white, one accent color), and generous spacing. Prioritize "
        "clarity and readability over decoration."
    ),
    "colorful": (
        "Use a vibrant, engaging design with distinct colors for each element, "
        "rounded shapes, and visual variety. Suitable for educational materials "
        "and creative presentations."
    ),
}

SYSTEM_PROMPT = """\
You are an expert Graphviz DOT language author. Generate ONLY valid DOT code.

Rules:
- Output ONLY the DOT code, no explanations or markdown fences.
- Use HTML-like labels (<...>) for rich text formatting when appropriate.
- Always set graph attributes: bgcolor, dpi, pad, nodesep, ranksep.
- Always set default node attributes: fontname, fontsize, shape, style, margin.
- Always set default edge attributes: fontname, fontsize, penwidth.
- Use "Segoe UI" as the primary font family.
- Ensure all node IDs are simple alphanumeric strings (no spaces or special chars).
- Use descriptive node IDs that reflect content (e.g., step1, ceo, q1).
- Place each node and edge on its own line for readability.
- End with a newline after the closing brace.
"""


# --------------------------------------------------------------------------- #
#  API call with retry
# --------------------------------------------------------------------------- #

def call_api(
    client,
    model: str,
    prompt: str,
    *,
    max_retries: int = 3,
) -> str:
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
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
#  Response cleaning
# --------------------------------------------------------------------------- #

def clean_dot_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end]).strip()

    if not (text.startswith("digraph") or text.startswith("graph")
            or text.startswith("strict")):
        for keyword in ["digraph ", "graph ", "strict "]:
            idx = text.find(keyword)
            if idx >= 0:
                text = text[idx:]
                break
    return text


# --------------------------------------------------------------------------- #
#  Prompt builder
# --------------------------------------------------------------------------- #

def build_prompt(layout_type: str, content: str, style: str) -> str:
    style_guide = STYLE_GUIDES.get(style, STYLE_GUIDES["modern"])
    return f"""\
Generate a professional Graphviz DOT diagram with the following specifications:

## Layout Type
{layout_type}

## Content
{content}

## Style
{style_guide}

## Requirements
- The diagram must be self-contained and render correctly with `dot -Tsvg`.
- Use the color palette and node shapes that are common for this layout type.
- Include a title if the content warrants one.
- Make the diagram visually balanced and professional.

Generate the complete DOT code now:
"""


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Graphviz DOT diagrams using Claude API"
    )
    parser.add_argument("content", help="Description of the diagram to generate")
    parser.add_argument(
        "--type", default="process",
        choices=["process", "hierarchy", "cycle", "list", "relation", "matrix", "pyramid"],
        help="Layout type (default: process)",
    )
    parser.add_argument(
        "--style", default="modern",
        choices=list(STYLE_GUIDES.keys()),
        help="Visual style (default: modern)",
    )
    parser.add_argument("--output", "-o", help="Output .dot file path")
    parser.add_argument("--model", default="claude-opus-4-6", help="Claude model ID")
    parser.add_argument("--api-key", help="Anthropic API key (overrides env/OAuth)")
    args = parser.parse_args()

    try:
        import anthropic
    except ImportError:
        print("Error: pip install anthropic>=0.39.0", file=sys.stderr)
        sys.exit(1)

    api_key = resolve_api_key(args.api_key)
    client = anthropic.Anthropic(api_key=api_key)

    print(f"  Generating {args.type} diagram (style={args.style})...", file=sys.stderr)
    prompt = build_prompt(args.type, args.content, args.style)
    raw = call_api(client, args.model, prompt)
    dot_code = clean_dot_response(raw)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(dot_code, encoding="utf-8")
        print(f"  Written to: {out}", file=sys.stderr)
    else:
        print(dot_code)


if __name__ == "__main__":
    main()
