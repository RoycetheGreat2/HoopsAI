"""
Create Postgres tables for HoopsAI (Supabase).

Usage (from project root, DATABASE_URL in .env or environment):
  python scripts/setup_database.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import get_cursor, database_enabled

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    game_date DATE NOT NULL,
    home VARCHAR(8) NOT NULL,
    away VARCHAR(8) NOT NULL,
    predicted_winner VARCHAR(8),
    actual_winner VARCHAR(8),
    correct BOOLEAN NOT NULL DEFAULT FALSE,
    home_win_probability DOUBLE PRECISION,
    away_win_probability DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (game_date, home, away)
);

CREATE TABLE IF NOT EXISTS model_runs (
    id SERIAL PRIMARY KEY,
    run_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    train_rows INTEGER,
    test_rows INTEGER,
    test_season INTEGER,
    baseline_accuracy DOUBLE PRECISION,
    baseline_auc DOUBLE PRECISION,
    baseline_brier DOUBLE PRECISION,
    model_saved BOOLEAN,
    saved_label TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS playoff_tracker (
    id SERIAL PRIMARY KEY,
    game_date DATE NOT NULL,
    home VARCHAR(8) NOT NULL,
    away VARCHAR(8) NOT NULL,
    predicted_winner VARCHAR(8),
    actual_winner VARCHAR(8),
    correct BOOLEAN NOT NULL DEFAULT FALSE,
    home_win_probability DOUBLE PRECISION,
    away_win_probability DOUBLE PRECISION,
    series_key VARCHAR(32),
    season_label VARCHAR(16),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (game_date, home, away)
);

CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions (game_date);
CREATE INDEX IF NOT EXISTS idx_playoff_date ON playoff_tracker (game_date);
"""


def main() -> None:
    if not database_enabled():
        print("ERROR: Set DATABASE_URL in .env (Supabase connection string).")
        sys.exit(1)

    with get_cursor() as cur:
        cur.execute(SCHEMA_SQL)

    print("Database tables ready: predictions, model_runs, playoff_tracker")


if __name__ == "__main__":
    main()
