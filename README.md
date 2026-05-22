# HoopsAI - NBA Win Percentage Predictor

> **Work in Progress** — This project is still actively being developed. Features, accuracy, and structure are subject to change.

A machine learning pipeline and web application that predicts NBA game outcomes. It scrapes live and historical data, engineers over 40 predictive features, and serves real-time win probability predictions through a React frontend powered by a Flask REST API.

**Current model accuracy: ~74.5% (forward validation on 2025 season)**

---

## How It Works

```
Basketball-Reference (scraping)
          ↓
  Raw game, player & team CSVs
          ↓
  features.py  (ELO, rolling averages, injury flags)
          ↓
  nba_games_features.csv
          ↓
  train.py  →  nba_model.pkl  (LightGBM)
          ↓
  live_predict.py  ←  ESPN API (today's schedule)
          ↓
  app.py  (Flask REST API)
          ↓
  frontend/  (React + Vite)
```

**Live predictions do not retrain the model.** The API loads a fixed `nba_model.pkl` and uses the latest row per team from `data/nba_games_features.csv` for rolling stats and ELO.
