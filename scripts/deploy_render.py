"""
Deploy HoopsAI to Render via Blueprint API (optional).

Requires RENDER_API_KEY (Dashboard → Account → API Keys).

Usage:
  set RENDER_API_KEY=rnd_...
  python scripts/deploy_render.py

Without the key, prints the one-click Blueprint URL for manual setup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
RENDER_YAML = ROOT / "render.yaml"
REPO = "https://github.com/RoycetheGreat2/HoopsAI"
BLUEPRINT_URL = f"https://dashboard.render.com/blueprint/new?repo={REPO}"


def validate_blueprint(api_key: str) -> bool:
    import json

    body = json.dumps({"blueprintFile": RENDER_YAML.read_text(encoding="utf-8")}).encode()
    req = urllib.request.Request(
        "https://api.render.com/v1/blueprints/validate",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            print("Blueprint validation:", resp.status)
            print(resp.read().decode()[:2000])
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print("Blueprint validation failed:", e.code, e.read().decode()[:2000])
        return False


def main() -> None:
    api_key = os.environ.get("RENDER_API_KEY", "").strip()
    if not RENDER_YAML.is_file():
        print("Missing render.yaml")
        sys.exit(1)

    if not api_key:
        print("RENDER_API_KEY not set.")
        print("\nManual deploy (recommended):")
        print(f"  1. Open: {BLUEPRINT_URL}")
        print("  2. Apply blueprint → deploy hoopsai-api first")
        print("  3. Set VITE_API_URL on hoopsai-web to the API URL → redeploy web")
        print("  4. Set CORS_ORIGINS on hoopsai-api to the static site URL → redeploy API")
        print("\nSee README.md — Deploy on Render or Railway")
        sys.exit(0)

    ok = validate_blueprint(api_key)
    if ok:
        print(f"\nBlueprint valid. Create/sync services in the dashboard:\n  {BLUEPRINT_URL}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
