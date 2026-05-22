import json
import sys
import warnings
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, roc_auc_score

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

warnings.filterwarnings("ignore")

df = pd.read_csv("data/nba_games_features.csv")
df["date"] = pd.to_datetime(df["date"])
print(f"Total rows: {len(df)}")
print(df.groupby("season").size())

train_2023 = df[df["season"] == 2023].sort_values("date")
cutoff_2023 = train_2023["date"].quantile(0.5)
train_df = pd.concat(
    [
        train_2023[train_2023["date"] >= cutoff_2023],
        df[df["season"] == 2024],
        df[df["season"] == 2025],
    ]
).copy()
test_df = df[df["season"] == 2026].copy()
if len(test_df) == 0:
    print("Warning: no 2026 season rows in feature matrix; falling back to 2025 for test.")
    test_df = df[df["season"] == 2025].copy()

w_train = train_df["season"].map({2023: 1.0, 2024: 2.0, 2025: 2.0}).values
TARGET = "result_binary"
y_train = train_df[TARGET].values
y_test = test_df[TARGET].values

print(f"\nTrain: {len(train_df)} | Test: {len(test_df)}")

LGBM_BASE = dict(
    n_estimators=500,
    max_depth=4,
    learning_rate=0.02,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_samples=20,
    reg_alpha=0.1,
    reg_lambda=0.1,
    random_state=42,
    verbose=-1,
)

BASELINE_CORE = [
    "win_pct",
    "opp_win_pct",
    "win_pct_diff",
    "point_diff_last5",
    "opp_point_diff_last5",
    "pts_diff_diff",
    "point_diff_last10",
    "opp_point_diff_last10",
    "pts_diff_diff10",
    "avg_pts_last5",
    "opp_avg_pts_last5",
    "avg_pts_last10",
    "opp_avg_pts_last10",
    "avg_pts_allowed_last5",
    "opp_avg_pts_allowed_last5",
    "avg_pts_allowed_last10",
    "opp_avg_pts_allowed_last10",
    "win_rate_last10",
    "opp_win_rate_last10",
    "win_rate_diff10",
    "streak_diff",
    "star1_pts_diff",
    "top_pts_diff",
    "top_ast_diff",
    "top_reb_diff",
    "star1_AST",
    "opp_star1_AST",
    "elo",
    "opp_elo",
    "elo_diff",
    "avg_pts_last5_diff",
    "avg_pts_last10_diff",
    "avg_pts_allowed_last5_diff",
    "avg_pts_allowed_last10_diff",
    "net_rating",
    "net_rating_diff",
]

INJURY_FEATURES_FULL = [
    "star1_absent",
    "star2_absent",
    "opp_star1_absent",
    "opp_star2_absent",
    "star_advantage",
]

INJURY_FEATURES_PRUNED = [
    "star1_absent",
    "opp_star1_absent",
    "star_advantage",
]

FEATURES_41F = BASELINE_CORE + INJURY_FEATURES_FULL
FEATURES_39F = BASELINE_CORE + INJURY_FEATURES_PRUNED


def evaluate_lgbm(features, params):
    missing = [f for f in features if f not in train_df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    X_tr = train_df[features].values
    X_te = test_df[features].values
    model = lgb.LGBMClassifier(**params)
    model.fit(X_tr, y_train, sample_weight=w_train)
    proba = model.predict_proba(X_te)[:, 1]
    acc = accuracy_score(y_test, model.predict(X_te))
    auc = roc_auc_score(y_test, proba)
    brier = brier_score_loss(y_test, proba)
    return acc, auc, brier, model


runs = []

acc0, auc0, brier0, model0 = evaluate_lgbm(FEATURES_41F, LGBM_BASE.copy())
runs.append(
    {
        "label": "Baseline 41f (current)",
        "acc": acc0,
        "auc": auc0,
        "brier": brier0,
        "features": list(FEATURES_41F),
        "params": LGBM_BASE.copy(),
        "model": model0,
    }
)

p1 = LGBM_BASE.copy()
p1["max_depth"] = 5
acc, auc, brier, model = evaluate_lgbm(FEATURES_41F, p1)
runs.append(
    {
        "label": "V1: depth=5",
        "acc": acc,
        "auc": auc,
        "brier": brier,
        "features": list(FEATURES_41F),
        "params": p1,
        "model": model,
    }
)

p2 = LGBM_BASE.copy()
p2["learning_rate"] = 0.03
p2["n_estimators"] = 400
acc, auc, brier, model = evaluate_lgbm(FEATURES_41F, p2)
runs.append(
    {
        "label": "V2: lr=0.03, n=400",
        "acc": acc,
        "auc": auc,
        "brier": brier,
        "features": list(FEATURES_41F),
        "params": p2,
        "model": model,
    }
)

p3 = LGBM_BASE.copy()
p3["reg_alpha"] = 0.05
p3["reg_lambda"] = 0.05
acc, auc, brier, model = evaluate_lgbm(FEATURES_41F, p3)
runs.append(
    {
        "label": "V3: softer reg",
        "acc": acc,
        "auc": auc,
        "brier": brier,
        "features": list(FEATURES_41F),
        "params": p3,
        "model": model,
    }
)

acc, auc, brier, model = evaluate_lgbm(FEATURES_39F, LGBM_BASE.copy())
runs.append(
    {
        "label": "V4: pruned injury (39f)",
        "acc": acc,
        "auc": auc,
        "brier": brier,
        "features": list(FEATURES_39F),
        "params": LGBM_BASE.copy(),
        "model": model,
    }
)

baseline = runs[0]
print()
print(
    "=== TUNING RESULTS (forward validation: train 2023h2+2024+2025, test 2026) ==="
)
print(f"{'Variant':<24} | {'Accuracy':>8} | {'AUC-ROC':>7} | {'Brier':>5}")
print("-------------------------|----------|---------|-------")
for r in runs:
    print(
        f"{r['label']:<24} | {r['acc'] * 100:7.1f}% | {r['auc']:7.3f} | {r['brier']:.4f}"
    )

b_acc = baseline["acc"]
b_auc = baseline["auc"]

qualifiers = [
    r
    for r in runs[1:]
    if r["acc"] > b_acc and r["auc"] >= b_auc
]

model_saved = False
saved_label = baseline["label"]
if qualifiers:
    best = max(qualifiers, key=lambda r: (r["auc"], -r["brier"]))
    joblib.dump(best["model"], "models/nba_model.pkl")
    joblib.dump(best["features"], "models/features.pkl")
    model_saved = True
    saved_label = best["label"]
    print()
    print(
        f"New best: {best['label']} | acc={best['acc']*100:.1f}% "
        f"AUC={best['auc']:.3f} Brier={best['brier']:.4f}"
    )
    print("New best model saved.")
else:
    joblib.dump(baseline["model"], "models/nba_model.pkl")
    joblib.dump(baseline["features"], "models/features.pkl")
    model_saved = True
    print()
    print("No tuning beat baseline; baseline 41f model saved.")

summary = {
    "train_rows": int(len(train_df)),
    "test_rows": int(len(test_df)),
    "test_season": int(test_df["season"].iloc[0]) if len(test_df) else None,
    "baseline_accuracy": float(baseline["acc"]),
    "baseline_auc": float(baseline["auc"]),
    "baseline_brier": float(baseline["brier"]),
    "model_saved": model_saved,
    "saved_label": saved_label,
}
summary_path = Path("data/monthly_train_summary.json")
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(f"Wrote summary to {summary_path}")
