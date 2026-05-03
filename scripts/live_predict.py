"""
Live NBA win-probability predictions using the trained LightGBM model.
Run from project root: python scripts/live_predict.py
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_CSV = ROOT / "data" / "nba_games_features.csv"
FEATURES_PKL = ROOT / "models" / "features.pkl"
MODEL_PKL = ROOT / "models" / "nba_model.pkl"
SCOREBOARD_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
)

# ESPN / common API abbreviations -> Basketball-Reference style used in feature CSV
ESPN_TO_MATRIX = {
    "BKN": "BRK",
    "CHA": "CHO",
    "PHX": "PHO",
    "NO": "NOP",
    "UTAH": "UTA",
    "SA": "SAS",
    "WSH": "WAS",  # ESPN uses WSH; matrix uses WAS
    "GS": "GSW",
    "NY": "NYK",
}


def matrix_abbrev(espn_abbrev: str) -> str:
    a = (espn_abbrev or "").strip().upper()
    return ESPN_TO_MATRIX.get(a, a)


def print_data_inventory() -> tuple[list[str], list[str]]:
    """Print CSV columns and saved feature list (authoritative for the model)."""
    df_head = pd.read_csv(DATA_CSV, nrows=0)
    csv_columns = list(df_head.columns)
    print("=== nba_games_features.csv columns ===")
    print(f"({len(csv_columns)} columns)")
    for name in csv_columns:
        print(name)

    feature_list: list[str] = list(joblib.load(FEATURES_PKL))
    print()
    print("=== models/features.pkl (model input order) ===")
    print(f"({len(feature_list)} features)")
    for name in feature_list:
        print(name)

    return csv_columns, feature_list


def latest_team_row(features_df: pd.DataFrame, team: str) -> pd.Series | None:
    sub = features_df[features_df["team"] == team]
    if sub.empty:
        return None
    sub = sub.sort_values("date", ascending=False)
    return sub.iloc[0]


def build_feature_vector(home: pd.Series, away: pd.Series) -> dict[str, float]:
    """
    Build model features for home-team perspective: home = 'team' stats,
    away = source for all opp_* components. Recompute all *_diff columns.
    Injury flags set to 0 via explicit keys at end.
    """
    h = home
    a = away

    def num(series: pd.Series, col: str) -> float:
        v = series.get(col, float("nan"))
        if pd.isna(v):
            return 0.0
        return float(v)

    win_pct_h = num(h, "win_pct")
    win_pct_a = num(a, "win_pct")
    pd5_h = num(h, "point_diff_last5")
    pd5_a = num(a, "point_diff_last5")
    pd10_h = num(h, "point_diff_last10")
    pd10_a = num(a, "point_diff_last10")
    ap5_h = num(h, "avg_pts_last5")
    ap5_a = num(a, "avg_pts_last5")
    ap10_h = num(h, "avg_pts_last10")
    ap10_a = num(a, "avg_pts_last10")
    apa5_h = num(h, "avg_pts_allowed_last5")
    apa5_a = num(a, "avg_pts_allowed_last5")
    apa10_h = num(h, "avg_pts_allowed_last10")
    apa10_a = num(a, "avg_pts_allowed_last10")
    wr10_h = num(h, "win_rate_last10")
    wr10_a = num(a, "win_rate_last10")
    streak_h = num(h, "streak_entering_game")
    streak_a = num(a, "streak_entering_game")
    s1p_h = num(h, "star1_PTS")
    s1p_a = num(a, "star1_PTS")
    top_pts_h = num(h, "top_combined_pts")
    top_pts_a = num(a, "top_combined_pts")
    top_ast_h = num(h, "top_combined_ast")
    top_ast_a = num(a, "top_combined_ast")
    top_reb_h = num(h, "top_combined_reb")
    top_reb_a = num(a, "top_combined_reb")
    s1ast_h = num(h, "star1_AST")
    s1ast_a = num(a, "star1_AST")
    elo_h = num(h, "elo")
    elo_a = num(a, "elo")
    nr_h = num(h, "net_rating")
    nr_a = num(a, "net_rating")

    return {
        "win_pct": win_pct_h,
        "opp_win_pct": win_pct_a,
        "win_pct_diff": win_pct_h - win_pct_a,
        "point_diff_last5": pd5_h,
        "opp_point_diff_last5": pd5_a,
        "pts_diff_diff": pd5_h - pd5_a,
        "point_diff_last10": pd10_h,
        "opp_point_diff_last10": pd10_a,
        "pts_diff_diff10": pd10_h - pd10_a,
        "avg_pts_last5": ap5_h,
        "opp_avg_pts_last5": ap5_a,
        "avg_pts_last10": ap10_h,
        "opp_avg_pts_last10": ap10_a,
        "avg_pts_allowed_last5": apa5_h,
        "opp_avg_pts_allowed_last5": apa5_a,
        "avg_pts_allowed_last10": apa10_h,
        "opp_avg_pts_allowed_last10": apa10_a,
        "win_rate_last10": wr10_h,
        "opp_win_rate_last10": wr10_a,
        "win_rate_diff10": wr10_h - wr10_a,
        "streak_diff": streak_h - streak_a,
        "star1_pts_diff": s1p_h - s1p_a,
        "top_pts_diff": top_pts_h - top_pts_a,
        "top_ast_diff": top_ast_h - top_ast_a,
        "top_reb_diff": top_reb_h - top_reb_a,
        "star1_AST": s1ast_h,
        "opp_star1_AST": s1ast_a,
        "elo": elo_h,
        "opp_elo": elo_a,
        "elo_diff": elo_h - elo_a,
        "avg_pts_last5_diff": ap5_h - ap5_a,
        "avg_pts_last10_diff": ap10_h - ap10_a,
        "avg_pts_allowed_last5_diff": apa5_h - apa5_a,
        "avg_pts_allowed_last10_diff": apa10_h - apa10_a,
        "net_rating": nr_h,
        "net_rating_diff": nr_h - nr_a,
        "star1_absent": 0.0,
        "star2_absent": 0.0,
        "opp_star1_absent": 0.0,
        "opp_star2_absent": 0.0,
        "star_advantage": 0.0,
    }


def dataframe_for_model(
    feature_dict: dict[str, float], expected: list[str]
) -> tuple[pd.DataFrame, list[str]]:
    missing: list[str] = []
    row: dict[str, float] = {}
    for name in expected:
        if name not in feature_dict:
            missing.append(name)
            row[name] = 0.0
        else:
            row[name] = float(feature_dict[name])
    return pd.DataFrame([row], columns=expected), missing


def _logo_url(team: dict) -> str | None:
    logo = team.get("logo")
    if logo is None:
        return None
    if isinstance(logo, str):
        return logo
    if isinstance(logo, dict):
        href = logo.get("href")
        return str(href) if href else None
    return None


def _parse_competitor_score(raw) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _season_type_from_event(event: dict) -> int:
    """ESPN season.type: 2 = regular, 3 = playoffs; else treat as regular (2)."""
    raw = (event.get("season") or {}).get("type")
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return 2
    if v == 3:
        return 3
    return 2


def parse_scoreboard_games(
    payload: dict,
) -> list[
    tuple[
        str,
        str,
        str | None,
        str | None,
        str,
        int,
        int,
        str | None,
        int,
    ]
]:
    """Return per event: away, home, logos, status, scores, actual_winner, season_type."""
    games: list[
        tuple[str, str, str | None, str | None, str, int, int, str | None, int]
    ] = []
    for event in payload.get("events") or []:
        comps = event.get("competitions") or []
        if not comps:
            continue
        comp = comps[0]
        status_type = (comp.get("status") or {}).get("type") or {}
        state = status_type.get("state") or "pre"
        season_type = _season_type_from_event(event)
        competitors = comp.get("competitors") or []
        away_abbr = None
        home_abbr = None
        away_logo: str | None = None
        home_logo: str | None = None
        away_score = 0
        home_score = 0
        for c in competitors:
            team_obj = c.get("team") or {}
            team = team_obj.get("abbreviation")
            ha = c.get("homeAway")
            sc = _parse_competitor_score(c.get("score"))
            if ha == "home":
                home_abbr = matrix_abbrev(team)
                home_logo = _logo_url(team_obj)
                home_score = sc
            elif ha == "away":
                away_abbr = matrix_abbrev(team)
                away_logo = _logo_url(team_obj)
                away_score = sc
        if away_abbr and home_abbr:
            actual: str | None = None
            if state == "post":
                if away_score > home_score:
                    actual = away_abbr
                elif home_score > away_score:
                    actual = home_abbr
                else:
                    actual = None
            games.append(
                (
                    away_abbr,
                    home_abbr,
                    away_logo,
                    home_logo,
                    state,
                    away_score,
                    home_score,
                    actual,
                    season_type,
                )
            )
    return games


def main() -> int:
    csv_columns, feature_list = print_data_inventory()
    _ = csv_columns  # inspected at runtime; ensures CSV exists

    features_df = pd.read_csv(DATA_CSV)
    features_df["date"] = pd.to_datetime(features_df["date"])

    try:
        resp = requests.get(SCOREBOARD_URL, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"\nCould not fetch NBA scoreboard: {e}")
        return 1

    games = parse_scoreboard_games(data)
    if not games:
        print("\nNo games found on the scoreboard response. Exiting.")
        return 0

    model = joblib.load(MODEL_PKL)

    today = date.today().isoformat()
    out_records: list[dict] = []

    print()
    print("=== Live predictions ===")

    for (
        away_abbr,
        home_abbr,
        away_logo,
        home_logo,
        status_state,
        away_score,
        home_score,
        actual_winner,
        season_type,
    ) in games:
        home_row = latest_team_row(features_df, home_abbr)
        away_row = latest_team_row(features_df, away_abbr)
        if home_row is None:
            print(f"Warning: no feature-matrix history for home team {home_abbr}; skipping.")
            continue
        if away_row is None:
            print(f"Warning: no feature-matrix history for away team {away_abbr}; skipping.")
            continue

        feat_dict = build_feature_vector(home_row, away_row)
        X_df, missing_feats = dataframe_for_model(feat_dict, feature_list)
        if missing_feats:
            print(
                "Warning: missing features (filled with 0): "
                + ", ".join(missing_feats)
            )

        p_home = float(model.predict_proba(X_df)[0, 1])
        p_away = 1.0 - p_home
        winner = home_abbr if p_home >= 0.5 else away_abbr

        print(
            f"{away_abbr} @ {home_abbr}  |  "
            f"Away {p_away * 100:.1f}%  Home {p_home * 100:.1f}%  |  "
            f"Pick: {winner}"
        )

        out_records.append(
            {
                "away": away_abbr,
                "home": home_abbr,
                "away_logo": away_logo,
                "home_logo": home_logo,
                "away_win_probability": round(p_away, 4),
                "home_win_probability": round(p_home, 4),
                "predicted_winner": winner,
                "status": status_state,
                "home_score": home_score,
                "away_score": away_score,
                "actual_winner": actual_winner,
                "season_type": int(season_type),
            }
        )

    payload = {
        "date": today,
        "predictions": out_records,
    }
    out_path = ROOT / "data" / f"live_predictions_{today}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    raise SystemExit(main())
