"""
One-time migration: data/prediction_tracker.json -> Postgres predictions table.

Requires DATABASE_URL in .env and tables created via setup_database.py.

  python scripts/migrate_json_to_db.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import database_enabled, get_cursor

TRACKER = ROOT / "data" / "prediction_tracker.json"
MIN_DATE = "2026-05-22"


def main() -> None:
    if not database_enabled():
        print("ERROR: Set DATABASE_URL in .env first.")
        sys.exit(1)
    if not TRACKER.is_file():
        print(f"No file at {TRACKER}; nothing to migrate.")
        return

    data = json.loads(TRACKER.read_text(encoding="utf-8"))
    games = data.get("games") or []
    inserted = 0
    with get_cursor() as cur:
        for g in games:
            d = (g.get("date") or "")[:10]
            if d < MIN_DATE:
                continue
            cur.execute(
                """
                INSERT INTO predictions (
                    game_date, home, away, predicted_winner, actual_winner,
                    correct, home_win_probability, away_win_probability
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_date, home, away) DO NOTHING
                """,
                (
                    d,
                    g.get("home"),
                    g.get("away"),
                    g.get("predicted_winner"),
                    g.get("actual_winner"),
                    bool(g.get("correct")),
                    g.get("home_win_probability"),
                    g.get("away_win_probability"),
                ),
            )
            if cur.rowcount:
                inserted += 1
    print(f"Migrated {inserted} new rows from {TRACKER.name} ({len(games)} in file).")


if __name__ == "__main__":
    main()
