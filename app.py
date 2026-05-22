"""
Flask API for NBA win predictor: health, latest live predictions JSON, model stats.

Local dev:  python app.py  →  http://127.0.0.1:5000
Production: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1
"""
import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import joblib
import pandas as pd
import requests
from collections import defaultdict
from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DATA_DIR = ROOT / "data"
MODEL_PATH = ROOT / "models" / "nba_model.pkl"
FEATURES_PATH = ROOT / "models" / "features.pkl"
FEATURES_CSV = ROOT / "data" / "nba_games_features.csv"
LIVE_PREDICT_PATH = ROOT / "scripts" / "live_predict.py"
PLAYOFF_TRACKER_PATH = DATA_DIR / "playoff_tracker.json"
PREDICTION_TRACKER_PATH = DATA_DIR / "prediction_tracker.json"
# Live tracking for deployed app — games before this date are excluded.
MIN_TRACK_DATE = date(2026, 5, 22)

PREDICTIONS_FILE_RE = re.compile(
    r"^live_predictions_(\d{4}-\d{2}-\d{2})\.json$"
)

ESPN_SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
)

_spec = importlib.util.spec_from_file_location(
    "nba_live_predict_bridge",
    LIVE_PREDICT_PATH,
)
_lp = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_lp)

app = Flask(__name__)

_cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
if _cors_raw and _cors_raw != "*":
    CORS(app, origins=[o.strip() for o in _cors_raw.split(",") if o.strip()])
else:
    CORS(app)

MODEL = joblib.load(MODEL_PATH)
FEATURE_NAMES: list[str] = list(joblib.load(FEATURES_PATH))

FEATURES_DF = pd.read_csv(FEATURES_CSV)
FEATURES_DF["date"] = pd.to_datetime(FEATURES_DF["date"])

_importances = MODEL.feature_importances_
_ranked = sorted(
    zip(FEATURE_NAMES, _importances),
    key=lambda x: float(x[1]),
    reverse=True,
)
TOP_5_FEATURES = [
    {
        "rank": i + 1,
        "feature": name,
        "importance": float(imp),
    }
    for i, (name, imp) in enumerate(_ranked[:5])
]


def current_nba_season_label(now: date | None = None) -> str:
    d = now or date.today()
    y = d.year
    if d.month >= 10:
        return f"{y}-{str(y + 1)[-2:]}"
    return f"{y - 1}-{str(y)[-2:]}"


def _series_key(home: str, away: str) -> str:
    return "_".join(sorted([home, away]))


def load_playoff_tracker() -> dict:
    try:
        if not PLAYOFF_TRACKER_PATH.is_file():
            return {"season": current_nba_season_label(), "games": []}
        text = PLAYOFF_TRACKER_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("root must be an object")
        data.setdefault("season", current_nba_season_label())
        g = data.get("games")
        if not isinstance(g, list):
            data["games"] = []
        return data
    except Exception as e:
        print(f"Warning: playoff tracker read failed ({e}); using empty tracker.")
        return {"season": current_nba_season_label(), "games": []}


def save_playoff_tracker(data: dict) -> None:
    PLAYOFF_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAYOFF_TRACKER_PATH.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def load_prediction_tracker() -> dict:
    try:
        if not PREDICTION_TRACKER_PATH.is_file():
            return {"tracking_since": MIN_TRACK_DATE.isoformat(), "games": []}
        data = json.loads(PREDICTION_TRACKER_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("root must be an object")
        data.setdefault("tracking_since", MIN_TRACK_DATE.isoformat())
        if not isinstance(data.get("games"), list):
            data["games"] = []
        return data
    except Exception as e:
        print(f"Warning: prediction tracker read failed ({e}); using empty tracker.")
        return {"tracking_since": MIN_TRACK_DATE.isoformat(), "games": []}


def save_prediction_tracker(data: dict) -> None:
    PREDICTION_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREDICTION_TRACKER_PATH.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )


def _database_enabled() -> bool:
    try:
        from db import database_enabled

        return database_enabled()
    except Exception:
        return False


def _iter_finished_games_from_weekly(days_out: list[dict]):
    """Yield finished game records eligible for tracking."""
    for day in days_out:
        day_date = (day.get("date") or "")[:10]
        for rec in day.get("games") or []:
            if rec.get("status") != "post":
                continue
            actual = rec.get("actual_winner")
            if actual is None:
                continue
            home = rec.get("home")
            away = rec.get("away")
            if not home or not away:
                continue
            utc = rec.get("utc_time")
            if isinstance(utc, str) and len(utc) >= 10:
                gdate = utc[:10]
            else:
                gdate = day_date
            if gdate < MIN_TRACK_DATE.isoformat():
                continue
            pred = rec.get("predicted_winner")
            yield {
                "date": gdate,
                "home": home,
                "away": away,
                "predicted_winner": pred,
                "actual_winner": actual,
                "correct": bool(pred == actual),
                "home_win_probability": rec.get("home_win_probability"),
                "away_win_probability": rec.get("away_win_probability"),
            }


def _sync_predictions_to_db(entries: list[dict]) -> None:
    from db import get_cursor

    with get_cursor() as cur:
        for e in entries:
            cur.execute(
                """
                INSERT INTO predictions (
                    game_date, home, away, predicted_winner, actual_winner,
                    correct, home_win_probability, away_win_probability
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_date, home, away) DO NOTHING
                """,
                (
                    e["date"],
                    e["home"],
                    e["away"],
                    e["predicted_winner"],
                    e["actual_winner"],
                    e["correct"],
                    e.get("home_win_probability"),
                    e.get("away_win_probability"),
                ),
            )


def sync_prediction_tracker_from_weekly(days_out: list[dict]) -> None:
    new_entries: list[dict] = []
    if _database_enabled():
        from db import get_cursor

        with get_cursor() as cur:
            cur.execute(
                """
                SELECT game_date::text, home, away
                FROM predictions
                WHERE game_date >= %s
                """,
                (MIN_TRACK_DATE.isoformat(),),
            )
            seen = {(r[0], r[1], r[2]) for r in cur.fetchall()}
        for entry in _iter_finished_games_from_weekly(days_out):
            key = (entry["date"], entry["home"], entry["away"])
            if key in seen:
                continue
            new_entries.append(entry)
            seen.add(key)
        if new_entries:
            _sync_predictions_to_db(new_entries)
        return

    tracker = load_prediction_tracker()
    seen = {(x["date"], x["home"], x["away"]) for x in tracker["games"]}
    for entry in _iter_finished_games_from_weekly(days_out):
        key = (entry["date"], entry["home"], entry["away"])
        if key in seen:
            continue
        tracker["games"].append(entry)
        seen.add(key)
    save_prediction_tracker(tracker)


def sync_playoff_tracker_from_weekly(days_out: list[dict]) -> None:
    tracker = load_playoff_tracker()
    seen = {(x["date"], x["home"], x["away"]) for x in tracker["games"]}
    for day in days_out:
        day_date = (day.get("date") or "")[:10]
        for rec in day.get("games") or []:
            if rec.get("season_type") != 3:
                continue
            if rec.get("status") != "post":
                continue
            actual = rec.get("actual_winner")
            if actual is None:
                continue
            home = rec.get("home")
            away = rec.get("away")
            if not home or not away:
                continue
            utc = rec.get("utc_time")
            if isinstance(utc, str) and len(utc) >= 10:
                gdate = utc[:10]
            else:
                gdate = day_date
            key = (gdate, home, away)
            if key in seen:
                continue
            pred = rec.get("predicted_winner")
            entry = {
                "date": gdate,
                "home": home,
                "away": away,
                "predicted_winner": pred,
                "actual_winner": actual,
                "correct": bool(pred == actual),
                "home_win_probability": rec.get("home_win_probability"),
                "away_win_probability": rec.get("away_win_probability"),
                "series": _series_key(home, away),
            }
            tracker["games"].append(entry)
            seen.add(key)
    if not tracker.get("season"):
        tracker["season"] = current_nba_season_label()
    save_playoff_tracker(tracker)


def _prediction_record_from_tuple(
    tuple_game: tuple,
) -> dict:
    (
        away_abbr,
        home_abbr,
        away_logo,
        home_logo,
        status_state,
        away_score,
        home_score,
        actual_winner,
        season_type,
    ) = tuple_game
    home_row = _lp.latest_team_row(FEATURES_DF, home_abbr)
    away_row = _lp.latest_team_row(FEATURES_DF, away_abbr)
    if home_row is None:
        raise ValueError(f"no feature-matrix history for home team {home_abbr}")
    if away_row is None:
        raise ValueError(f"no feature-matrix history for away team {away_abbr}")
    feat_dict = _lp.build_feature_vector(home_row, away_row)
    X_df, missing_feats = _lp.dataframe_for_model(feat_dict, FEATURE_NAMES)
    if missing_feats:
        print(
            "Warning: missing features (filled with 0): "
            + ", ".join(missing_feats)
        )
    p_home = float(MODEL.predict_proba(X_df)[0, 1])
    p_away = 1.0 - p_home
    winner = home_abbr if p_home >= 0.5 else away_abbr
    return {
        "away": away_abbr,
        "home": home_abbr,
        "away_logo": away_logo,
        "home_logo": home_logo,
        "away_win_probability": round(p_away, 4),
        "home_win_probability": round(p_home, 4),
        "predicted_winner": winner,
        "status": status_state,
        "home_score": int(home_score),
        "away_score": int(away_score),
        "actual_winner": actual_winner,
        "season_type": int(season_type),
    }


def latest_predictions_file() -> Path | None:
    """Newest live_predictions_YYYY-MM-DD.json by embedded date (not mtime)."""
    candidates: list[tuple[str, Path]] = []
    if not DATA_DIR.is_dir():
        return None
    for path in DATA_DIR.glob("live_predictions_*.json"):
        m = PREDICTIONS_FILE_RE.match(path.name)
        if m:
            candidates.append((m.group(1), path))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/api/predictions")
def predictions():
    path = latest_predictions_file()
    if path is None:
        return jsonify(
            {
                "error": "No predictions file found.",
                "detail": "Expected data/live_predictions_YYYY-MM-DD.json from live_predict.py.",
            }
        ), 404
    try:
        text = path.read_text(encoding="utf-8")
        payload = json.loads(text)
    except json.JSONDecodeError as e:
        return jsonify(
            {
                "error": "Predictions file is not valid JSON.",
                "detail": str(e),
                "path": str(path),
            }
        ), 500
    except OSError as e:
        return jsonify(
            {
                "error": "Could not read predictions file.",
                "detail": str(e),
                "path": str(path),
            }
        ), 500
    return jsonify(payload)


def _parse_week_start_param(raw: str | None) -> date:
    today = date.today()
    if not raw:
        return today
    try:
        d = date.fromisoformat(str(raw)[:10])
    except ValueError:
        return today
    if d < MIN_TRACK_DATE:
        return MIN_TRACK_DATE
    return d


def _fetch_week_days(week_start: date) -> list[dict]:
    days_out: list[dict] = []
    for offset in range(7):
        d = week_start + timedelta(days=offset)
        if d < MIN_TRACK_DATE:
            continue
        ymd = d.strftime("%Y%m%d")
        try:
            resp = requests.get(
                ESPN_SCOREBOARD_URL,
                params={"dates": ymd},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            continue

        day_games: list[dict] = []
        for event in data.get("events") or []:
            utc_raw = event.get("date")
            utc_time = utc_raw if isinstance(utc_raw, str) else None
            games = _lp.parse_scoreboard_games({"events": [event]})
            for g in games:
                try:
                    rec = _prediction_record_from_tuple(g)
                    rec["utc_time"] = utc_time
                    day_games.append(rec)
                except Exception as e:
                    print(
                        f"Warning: skipping game {g[0]} @ {g[1]} on {d.isoformat()}: {e}"
                    )
                    continue

        days_out.append({"date": d.isoformat(), "games": day_games})
    return days_out


@app.get("/api/weekly-predictions")
def weekly_predictions():
    week_start = _parse_week_start_param(request.args.get("start"))
    week_end = week_start + timedelta(days=6)
    days_out = _fetch_week_days(week_start)

    sync_prediction_tracker_from_weekly(days_out)
    sync_playoff_tracker_from_weekly(days_out)

    return jsonify(
        {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "tracking_since": MIN_TRACK_DATE.isoformat(),
            "days": days_out,
        }
    )


@app.get("/api/prediction-accuracy")
def prediction_accuracy():
    today = date.today()
    week_start = today - timedelta(days=6)
    if week_start < MIN_TRACK_DATE:
        week_start = MIN_TRACK_DATE
    month_start = today - timedelta(days=29)
    if month_start < MIN_TRACK_DATE:
        month_start = MIN_TRACK_DATE

    def tally(start: date, end: date) -> dict:
        if _database_enabled():
            from db import get_cursor

            with get_cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)::int AS total,
                        COALESCE(SUM(CASE WHEN correct THEN 1 ELSE 0 END), 0)::int AS correct
                    FROM predictions
                    WHERE game_date >= %s
                      AND game_date BETWEEN %s AND %s
                    """,
                    (MIN_TRACK_DATE.isoformat(), start.isoformat(), end.isoformat()),
                )
                row = cur.fetchone()
                total = row[0] or 0
                correct = row[1] or 0
        else:
            tracker = load_prediction_tracker()
            games = [
                g
                for g in (tracker.get("games") or [])
                if (g.get("date") or "") >= MIN_TRACK_DATE.isoformat()
            ]
            subset = [
                g
                for g in games
                if start.isoformat() <= (g.get("date") or "") <= end.isoformat()
            ]
            total = len(subset)
            correct = sum(1 for g in subset if g.get("correct"))
        acc = (correct / total) if total else None
        return {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "correct": correct,
            "total": total,
            "accuracy": acc,
        }

    return jsonify(
        {
            "tracking_since": MIN_TRACK_DATE.isoformat(),
            "storage": "postgres" if _database_enabled() else "json",
            "week": tally(week_start, today),
            "month": tally(month_start, today),
        }
    )


@app.get("/api/playoff-stats")
def playoff_stats():
    tracker = load_playoff_tracker()
    games = tracker.get("games") or []
    season = tracker.get("season") or current_nba_season_label()
    total_games = len(games)
    correct_n = sum(1 for g in games if g.get("correct"))
    accuracy = (correct_n / total_games) if total_games else None
    is_active = total_games > 0

    by_series_map: dict[str, list] = defaultdict(list)
    for g in games:
        sk = g.get("series") or _series_key(g.get("home"), g.get("away"))
        by_series_map[sk].append(g)

    by_series: list[dict] = []
    for sk in sorted(by_series_map.keys()):
        sg = by_series_map[sk]
        parts = sk.split("_") if sk else []
        team_a, team_b = (parts[0], parts[1]) if len(parts) >= 2 else ("", "")
        played = len(sg)
        gc = sum(1 for x in sg if x.get("correct"))
        acc_s = (gc / played) if played else None
        sg_sorted = sorted(sg, key=lambda z: (z.get("date") or "", z.get("home")))
        game_log = [
            {
                "date": x.get("date"),
                "predicted_winner": x.get("predicted_winner"),
                "actual_winner": x.get("actual_winner"),
                "home_win_probability": x.get("home_win_probability"),
                "away_win_probability": x.get("away_win_probability"),
                "correct": bool(x.get("correct")),
            }
            for x in sg_sorted
        ]
        by_series.append(
            {
                "series": sk,
                "team_a": team_a,
                "team_b": team_b,
                "games_played": played,
                "games_correct": gc,
                "accuracy": acc_s,
                "games": game_log,
            }
        )

    return jsonify(
        {
            "season": season,
            "total_games": total_games,
            "correct": correct_n,
            "accuracy": accuracy,
            "by_series": by_series,
            "is_active": is_active,
        }
    )


@app.get("/api/model-stats")
def model_stats():
    return jsonify(
        {
            "accuracy": 0.745,
            "forward_validation_accuracy_pct": 74.5,
            "auc_roc": 0.818,
            "brier_score": 0.1742,
            "num_features": 41,
            "top_features": TOP_5_FEATURES,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=port, debug=debug)
