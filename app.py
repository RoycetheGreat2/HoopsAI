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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

from week_epoch import (
    epoch_week_start,
    epoch_week_end,
    is_current_epoch_week,
    max_epoch_week_start,
    schedule_max_date,
)

SCHEDULE_AHEAD_DAYS = int(os.environ.get("SCHEDULE_AHEAD_DAYS", "30"))

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


def _game_date_from_rec(rec: dict, day_date: str) -> str | None:
    utc = rec.get("utc_time")
    if isinstance(utc, str) and len(utc) >= 10:
        gdate = utc[:10]
    else:
        gdate = day_date[:10]
    if not gdate or gdate < MIN_TRACK_DATE.isoformat():
        return None
    return gdate


def _iter_trackable_games_from_weekly(days_out: list[dict]):
    """Yield prediction records for all games on/after MIN_TRACK_DATE."""
    for day in days_out:
        day_date = (day.get("date") or "")[:10]
        for rec in day.get("games") or []:
            home = rec.get("home")
            away = rec.get("away")
            if not home or not away:
                continue
            gdate = _game_date_from_rec(rec, day_date)
            if not gdate:
                continue
            pred = rec.get("predicted_winner")
            status = rec.get("status") or "pre"
            actual = rec.get("actual_winner") if status == "post" else None
            if status == "post" and actual is None:
                continue
            correct = None
            if status == "post" and actual is not None:
                correct = bool(pred == actual)
            yield {
                "date": gdate,
                "home": home,
                "away": away,
                "predicted_winner": pred,
                "actual_winner": actual,
                "correct": correct,
                "status": status,
                "home_win_probability": rec.get("home_win_probability"),
                "away_win_probability": rec.get("away_win_probability"),
            }


def _sync_predictions_to_db(entries: list[dict]) -> None:
    from db import get_cursor

    with get_cursor() as cur:
        for e in entries:
            correct_val = e["correct"]
            if correct_val is None:
                correct_val = False
            cur.execute(
                """
                INSERT INTO predictions (
                    game_date, home, away, predicted_winner, actual_winner,
                    correct, home_win_probability, away_win_probability
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_date, home, away) DO UPDATE SET
                    predicted_winner = EXCLUDED.predicted_winner,
                    actual_winner = EXCLUDED.actual_winner,
                    correct = EXCLUDED.correct,
                    home_win_probability = EXCLUDED.home_win_probability,
                    away_win_probability = EXCLUDED.away_win_probability
                """,
                (
                    e["date"],
                    e["home"],
                    e["away"],
                    e["predicted_winner"],
                    e["actual_winner"],
                    correct_val,
                    e.get("home_win_probability"),
                    e.get("away_win_probability"),
                ),
            )


def _upsert_json_tracker_games(tracker: dict, entries: list[dict]) -> None:
    index: dict[tuple[str, str, str], int] = {
        (g["date"], g["home"], g["away"]): i
        for i, g in enumerate(tracker["games"])
    }
    for entry in entries:
        key = (entry["date"], entry["home"], entry["away"])
        row = {k: v for k, v in entry.items() if k != "status"}
        if key in index:
            existing = tracker["games"][index[key]]
            tracker["games"][index[key]] = {**existing, **row}
        else:
            index[key] = len(tracker["games"])
            tracker["games"].append(row)


def sync_prediction_tracker_from_weekly(days_out: list[dict]) -> None:
    entries = list(_iter_trackable_games_from_weekly(days_out))
    if not entries:
        return

    if _database_enabled():
        _sync_predictions_to_db(entries)
        return

    tracker = load_prediction_tracker()
    _upsert_json_tracker_games(tracker, entries)
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


def _prediction_storage_mode() -> str:
    if _database_enabled():
        return "postgres"
    try:
        PREDICTION_TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
        test = PREDICTION_TRACKER_PATH.parent / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return "json"
    except OSError:
        return "ephemeral"


def _database_health() -> dict:
    if not _database_enabled():
        return {"connected": False, "detail": "DATABASE_URL not configured"}
    try:
        from db import get_cursor

        with get_cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'predictions')"
            )
            has_table = bool(cur.fetchone()[0])
        return {"connected": True, "predictions_table": has_table}
    except Exception as e:
        return {"connected": False, "detail": str(e)}


@app.get("/api/health")
def health():
    try:
        _ensure_current_epoch_week_cached()
    except Exception as e:
        print(f"Warning: current-week cache warm failed ({e})")
    today = date.today()
    cur = epoch_week_start(today, MIN_TRACK_DATE)
    return jsonify(
        {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prediction_storage": _prediction_storage_mode(),
            "tracking_since": MIN_TRACK_DATE.isoformat(),
            "current_epoch_week": {
                "start": cur.isoformat(),
                "end": epoch_week_end(cur).isoformat(),
            },
            "database": _database_health(),
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


_WEEKLY_CACHE: dict[str, tuple[float, list[dict]]] = {}
_WEEKLY_PAYLOAD_CACHE: dict[str, tuple[float, dict]] = {}
_WEEKLY_CACHE_TTL_SEC = int(os.environ.get("WEEKLY_CACHE_TTL_SEC", "180"))
_CURRENT_WEEK_CACHE_TTL_SEC = int(
    os.environ.get("CURRENT_WEEK_CACHE_TTL_SEC", "86400")
)
_ACCURACY_CACHE: tuple[float, dict] | None = None
_ACCURACY_CACHE_TTL_SEC = int(os.environ.get("ACCURACY_CACHE_TTL_SEC", "90"))


def _parse_week_start_param(raw: str | None) -> date:
    today = date.today()
    if not raw:
        return epoch_week_start(today, MIN_TRACK_DATE)
    try:
        d = date.fromisoformat(str(raw)[:10])
    except ValueError:
        return epoch_week_start(today, MIN_TRACK_DATE)
    if d < MIN_TRACK_DATE:
        return MIN_TRACK_DATE
    return epoch_week_start(d, MIN_TRACK_DATE)


def _weekly_cache_ttl_sec(week_start: date) -> int:
    if is_current_epoch_week(week_start, date.today()):
        return _CURRENT_WEEK_CACHE_TTL_SEC
    return _WEEKLY_CACHE_TTL_SEC


def _ensure_current_epoch_week_cached() -> None:
    """Warm cache for the active epoch week (e.g. May 22–28, then May 29–Jun 4)."""
    start = epoch_week_start(date.today(), MIN_TRACK_DATE)
    cache_key = start.isoformat()
    now = time.time()
    cached = _WEEKLY_CACHE.get(cache_key)
    if cached and now - cached[0] < _weekly_cache_ttl_sec(start):
        return
    _fetch_week_days(start)


def _fetch_single_day(d: date) -> dict | None:
    if d < MIN_TRACK_DATE:
        return None
    ymd = d.strftime("%Y%m%d")
    try:
        resp = requests.get(
            ESPN_SCOREBOARD_URL,
            params={"dates": ymd},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Warning: ESPN fetch failed for {d.isoformat()}: {e}")
        return {"date": d.isoformat(), "games": []}

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
    return {"date": d.isoformat(), "games": day_games}


def _fetch_week_days(week_start: date) -> list[dict]:
    cache_key = week_start.isoformat()
    now = time.time()
    ttl = _weekly_cache_ttl_sec(week_start)
    cached = _WEEKLY_CACHE.get(cache_key)
    if cached and now - cached[0] < ttl:
        return cached[1]

    dates = [week_start + timedelta(days=i) for i in range(7)]
    days_out: list[dict] = []
    with ThreadPoolExecutor(max_workers=7) as pool:
        futures = {pool.submit(_fetch_single_day, d): d for d in dates}
        by_date: dict[str, dict] = {}
        for fut in as_completed(futures):
            row = fut.result()
            if row:
                by_date[row["date"]] = row
    for d in dates:
        if d.isoformat() in by_date:
            days_out.append(by_date[d.isoformat()])

    _WEEKLY_CACHE[cache_key] = (now, days_out)
    return days_out


def _schedule_bounds(today: date | None = None) -> dict:
    today = today or date.today()
    max_d = schedule_max_date(today, SCHEDULE_AHEAD_DAYS)
    max_epoch = max_epoch_week_start(today, MIN_TRACK_DATE, SCHEDULE_AHEAD_DAYS)
    return {
        "min_date": MIN_TRACK_DATE.isoformat(),
        "max_date": max_d.isoformat(),
        "max_epoch_week_start": max_epoch.isoformat(),
    }


def _weekly_payload_cache_get(week_start: date) -> dict | None:
    key = week_start.isoformat()
    now = time.time()
    cached = _WEEKLY_PAYLOAD_CACHE.get(key)
    if not cached:
        return None
    ttl = _weekly_cache_ttl_sec(week_start)
    if now - cached[0] >= ttl:
        return None
    return cached[1]


def _weekly_payload_cache_set(week_start: date, payload: dict) -> None:
    _WEEKLY_PAYLOAD_CACHE[week_start.isoformat()] = (time.time(), payload)


@app.get("/api/weekly-predictions")
def weekly_predictions():
    _ensure_current_epoch_week_cached()
    today = date.today()
    week_start = _parse_week_start_param(request.args.get("start"))
    max_epoch = max_epoch_week_start(today, MIN_TRACK_DATE, SCHEDULE_AHEAD_DAYS)
    if week_start > max_epoch:
        week_start = max_epoch

    cached_payload = _weekly_payload_cache_get(week_start)
    if cached_payload is not None:
        return jsonify(cached_payload)

    week_end = epoch_week_end(week_start)
    days_out = _fetch_week_days(week_start)

    try:
        sync_prediction_tracker_from_weekly(days_out)
        global _ACCURACY_CACHE
        _ACCURACY_CACHE = None
    except Exception as e:
        print(f"Warning: prediction sync failed ({e})")
    try:
        sync_playoff_tracker_from_weekly(days_out)
    except Exception as e:
        print(f"Warning: playoff sync failed ({e})")

    accuracy = _build_accuracy_payload()

    payload = {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "tracking_since": MIN_TRACK_DATE.isoformat(),
        "schedule": _schedule_bounds(today),
        "current_epoch_week_start": epoch_week_start(today, MIN_TRACK_DATE).isoformat(),
        "is_current_epoch_week": is_current_epoch_week(week_start, today),
        "days": days_out,
        "accuracy": accuracy,
    }
    _weekly_payload_cache_set(week_start, payload)
    return jsonify(payload)


def _accuracy_tally(start: date, end: date) -> dict:
    if _database_enabled():
        from db import get_cursor

        with get_cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::int AS total,
                    COALESCE(SUM(CASE WHEN correct THEN 1 ELSE 0 END), 0)::int AS correct
                FROM predictions
                WHERE game_date BETWEEN %s AND %s
                  AND actual_winner IS NOT NULL
                """,
                (start.isoformat(), end.isoformat()),
            )
            row = cur.fetchone()
            total = row[0] or 0
            correct = row[1] or 0
    else:
        tracker = load_prediction_tracker()
        subset = [
            g
            for g in (tracker.get("games") or [])
            if g.get("actual_winner")
            and start.isoformat() <= (g.get("date") or "") <= end.isoformat()
        ]
        total = len(subset)
        correct = sum(1 for g in subset if g.get("correct") is True)
    acc = (correct / total) if total else None
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "correct": correct,
        "total": total,
        "accuracy": acc,
    }


def _build_accuracy_payload() -> dict:
    global _ACCURACY_CACHE
    now = time.time()
    if _ACCURACY_CACHE and now - _ACCURACY_CACHE[0] < _ACCURACY_CACHE_TTL_SEC:
        return _ACCURACY_CACHE[1]

    today = date.today()
    week_start = today - timedelta(days=6)
    if week_start < MIN_TRACK_DATE:
        week_start = MIN_TRACK_DATE
    month_start = today - timedelta(days=29)
    if month_start < MIN_TRACK_DATE:
        month_start = MIN_TRACK_DATE

    payload = {
        "tracking_since": MIN_TRACK_DATE.isoformat(),
        "storage": "postgres" if _database_enabled() else "json",
        "week": _accuracy_tally(week_start, today),
        "month": _accuracy_tally(month_start, today),
    }
    _ACCURACY_CACHE = (now, payload)
    return payload


@app.get("/api/prediction-accuracy")
def prediction_accuracy():
    return jsonify(_build_accuracy_payload())


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
