#!/usr/bin/env python3
"""Extract Claude Code OAuth access token from ~/.claude/.credentials.json.

Usage:
    python get_oauth_token.py          # Print access token
    python get_oauth_token.py --check  # Check token validity and print info
    python get_oauth_token.py --export # Print export command for shell

Examples:
    # Set as env var
    export ANTHROPIC_API_KEY=$(python get_oauth_token.py)

    # Check before using
    python get_oauth_token.py --check
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"


def load_credentials() -> dict:
    """Load and return the credentials JSON."""
    if not CREDENTIALS_PATH.exists():
        print(
            f"Error: {CREDENTIALS_PATH} not found. "
            "Is Claude Code installed and authenticated?",
            file=sys.stderr,
        )
        sys.exit(1)

    return json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))


def get_oauth_token() -> str:
    """Extract the OAuth access token."""
    creds = load_credentials()
    oauth = creds.get("claudeAiOauth", {})
    token = oauth.get("accessToken", "")
    if not token:
        print("Error: No OAuth access token found in credentials.", file=sys.stderr)
        sys.exit(1)
    return token


def check_token() -> None:
    """Print token status information."""
    creds = load_credentials()
    oauth = creds.get("claudeAiOauth", {})

    token = oauth.get("accessToken", "")
    expires_at = oauth.get("expiresAt", 0)
    scopes = oauth.get("scopes", [])
    sub_type = oauth.get("subscriptionType", "unknown")
    rate_tier = oauth.get("rateLimitTier", "unknown")

    now_ms = int(time.time() * 1000)
    expired = now_ms > expires_at if expires_at else True
    remaining_s = (expires_at - now_ms) / 1000 if expires_at else 0

    print(f"Token prefix:    {token[:20]}..." if token else "Token: MISSING")
    print(f"Expired:         {'YES' if expired else 'no'}")
    if remaining_s > 0:
        hours = remaining_s / 3600
        print(f"Expires in:      {hours:.1f} hours")
    print(f"Scopes:          {', '.join(scopes)}")
    print(f"Subscription:    {sub_type}")
    print(f"Rate limit tier: {rate_tier}")
    print(f"Has inference:   {'yes' if 'user:inference' in scopes else 'NO'}")


def main() -> None:
    if "--check" in sys.argv:
        check_token()
    elif "--export" in sys.argv:
        token = get_oauth_token()
        print(f'export ANTHROPIC_API_KEY="{token}"')
    else:
        print(get_oauth_token())


if __name__ == "__main__":
    main()
