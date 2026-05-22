"""
Verify monthly-retrain + deploy artifacts are present.

  python scripts/verify_setup.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "requirements.txt",
    "Procfile",
    "render.yaml",
    ".env.example",
    "app.py",
    "scripts/monthly_pipeline.py",
    "scripts/setup_database.py",
    "scripts/db.py",
    "scripts/season_utils.py",
    "scripts/migrate_json_to_db.py",
    ".github/workflows/monthly-retrain.yml",
    "frontend/.env.example",
    "frontend/src/hooks/useApi.ts",
    "data/prediction_tracker.json",
]

REQUIRED_RUNTIME = [
    "models/nba_model.pkl",
    "models/features.pkl",
    "data/nba_games_features.csv",
]


def main() -> int:
    ok = True
    print(f"Checking project root: {ROOT}\n")

    for rel in REQUIRED_FILES:
        p = ROOT / rel
        status = "OK" if p.is_file() else "MISSING"
        if status == "MISSING":
            ok = False
        print(f"  [{status}] {rel}")

    print()
    for rel in REQUIRED_RUNTIME:
        p = ROOT / rel
        status = "OK" if p.is_file() else "WARN (needed to run API/train)"
        print(f"  [{status}] {rel}")

    venv = ROOT / "venv"
    dotvenv = ROOT / ".venv"
    print()
    if venv.is_dir():
        print("  [OK] venv/ exists (recommended)")
    if dotvenv.is_dir():
        print("  [NOTE] .venv/ exists — pick ONE venv; see README Virtual environments")
    if not venv.is_dir() and not dotvenv.is_dir():
        print("  [WARN] No venv/ or .venv/ — create one: python -m venv venv")

    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from db import database_enabled

        db = database_enabled()
        print(f"\n  DATABASE_URL configured: {db}")
    except Exception as e:
        print(f"\n  DATABASE_URL check skipped: {e}")

    print()
    if ok:
        print("Setup files: all present.")
        return 0
    print("Setup files: some missing — re-run plan implementation.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
