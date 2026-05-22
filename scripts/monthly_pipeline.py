"""
Monthly retrain pipeline: Basketball-Reference scrapers -> features -> train.

Run from project root:
  python scripts/monthly_pipeline.py

Optional env:
  BREF_SEASON=2026   passed to scraper.py
  DATABASE_URL       if set, logs run to Postgres model_runs table
  SKIP_SCRAPE=1      skip scrapers (only features + train)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA = ROOT / "data"


def run_step(name: str, script: str, extra_env: dict | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, str(SCRIPTS / script)]
    print(f"\n=== {name} ===")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT), env=env)
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {name} (exit {result.returncode})")


def log_model_run(summary: dict) -> None:
    if not os.environ.get("DATABASE_URL"):
        return
    try:
        sys.path.insert(0, str(SCRIPTS))
        from db import get_cursor

        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_runs (
                    run_at, train_rows, test_rows, test_season,
                    baseline_accuracy, baseline_auc, baseline_brier,
                    model_saved, saved_label, notes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    datetime.now(timezone.utc),
                    summary.get("train_rows"),
                    summary.get("test_rows"),
                    summary.get("test_season"),
                    summary.get("baseline_accuracy"),
                    summary.get("baseline_auc"),
                    summary.get("baseline_brier"),
                    summary.get("model_saved"),
                    summary.get("saved_label"),
                    "monthly_pipeline",
                ),
            )
        print("Logged run to model_runs table.")
    except Exception as e:
        print(f"Warning: could not log to database ({e})")


def main() -> None:
    os.chdir(ROOT)
    print(f"Monthly pipeline started at {datetime.now(timezone.utc).isoformat()}")
    print(f"Project root: {ROOT}")

    if os.environ.get("SKIP_SCRAPE", "").lower() not in ("1", "true", "yes"):
        bref = os.environ.get("BREF_SEASON", "2026")
        run_step("Scrape current season games", "scraper.py", {"BREF_SEASON": bref})
        run_step("Scrape player stats (historical)", "scrape_players_historical.py")
        run_step(
            "Scrape player gamelogs (historical)",
            "scrape_player_gamelogs_historical.py",
        )
        run_step("Build injury features", "build_injury_features.py")
    else:
        print("SKIP_SCRAPE set — skipping scrapers.")

    run_step("Build feature matrix", "features.py")
    run_step("Train model", "train.py")

    summary_path = DATA / "monthly_train_summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        log_model_run(summary)
    else:
        print("Warning: monthly_train_summary.json not found after train.")

    print("\nMonthly pipeline completed successfully.")
    print("Restart or redeploy the API to load new models and features CSV.")


if __name__ == "__main__":
    main()
