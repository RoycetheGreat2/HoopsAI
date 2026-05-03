# HoopsAI - NBA Win Percentage Predictor

> ⚠️ **Work in Progress** — This project is still actively being developed. Features, accuracy, and structure are subject to change.

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

---

## File Reference

### Scripts — Data Pipeline
| File | What it does |
|------|-------------|
| `scripts/scraper.py` | Scrapes 2025 season game results → `nba_games_raw.csv` |
| `scripts/scrape_seasons.py` | Scrapes 2023–2024 historical results → `nba_games_historical.csv` |
| `scripts/scrape_team_stats.py` | Scrapes team Pace, TS%, 3PT rate → `nba_team_stats.csv` |
| `scripts/scrape_players.py` | Scrapes 2025 top-3 player stats per team → `nba_player_stats.csv` |
| `scripts/scrape_players_historical.py` | Scrapes & merges 2023–2025 player stats → `nba_player_stats_historical.csv` |
| `scripts/scrape_player_gamelogs.py` | Scrapes 2025 player game logs → `nba_player_gamelogs.csv` |
| `scripts/scrape_player_gamelogs_historical.py` | Scrapes & merges 2023–2025 gamelogs → `nba_player_gamelogs_all.csv` |
| `scripts/build_injury_features.py` | Flags star player absences per game → `nba_player_availability.csv` |
| `scripts/features.py` | Master ETL — merges all data, computes ELO + rolling features → `nba_games_features.csv` |
| `scripts/train.py` | Trains LightGBM classifier → `models/nba_model.pkl` |
| `scripts/live_predict.py` | Fetches ESPN schedule, runs model → `data/live_predictions_YYYY-MM-DD.json` |

### Data Files
| File | What it contains |
|------|----------------|
| `data/nba_games_raw.csv` | 2025 season game results |
| `data/nba_games_historical.csv` | 2023–2024 season game results |
| `data/nba_team_stats.csv` | Team-level advanced stats per season |
| `data/nba_player_stats.csv` | 2025 top player averages per team |
| `data/nba_player_stats_historical.csv` | 2023–2025 merged player stats |
| `data/nba_player_gamelogs.csv` | 2025 player game-by-game logs |
| `data/nba_player_gamelogs_all.csv` | 2023–2025 merged player gamelogs |
| `data/nba_player_availability.csv` | Star player absence flags |
| `data/nba_games_features.csv` | Final enriched feature matrix (model input) |
| `data/live_predictions_*.json` | Daily prediction output from live_predict.py |
| `data/playoff_tracker.json` | Model accuracy log for playoff games |

### Model
| File | What it contains |
|------|----------------|
| `models/nba_model.pkl` | Trained LightGBM classifier |
| `models/features.pkl` | Ordered list of 41 feature names |

### Application
| File | What it does |
|------|-------------|
| `app.py` | Flask REST API — serves predictions to the frontend |
| `frontend/src/App.jsx` | Main React app — fetches and renders the weekly schedule |
| `frontend/src/components/MatchupCard.jsx` | Game card with team logos and win probability bar |
| `frontend/src/components/ModelStatsPanel.jsx` | Displays model accuracy and top features |
| `frontend/src/components/PlayoffTrackerPanel.jsx` | Tracks model accuracy on playoff series |
| `frontend/src/components/HealthBanner.jsx` | API connection status indicator |

---

## Running the Project

### 1. Install dependencies
```bash
# Python backend
pip install flask flask-cors requests beautifulsoup4 lxml pandas numpy lightgbm scikit-learn joblib

# React frontend (only needed once)
cd frontend && npm install
```

### 2. Start the backend API
```bash
python app.py
# Running at http://127.0.0.1:5000
```

### 3. Start the frontend
```bash
cd frontend
npm run dev
# Running at http://localhost:5173
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | API connection check |
| `GET /api/predictions` | Latest pre-generated predictions |
| `GET /api/weekly-predictions` | Live 7-day predictions via ESPN |
| `GET /api/playoff-stats` | Playoff prediction accuracy tracker |
| `GET /api/model-stats` | Model accuracy, AUC-ROC, top features |

---

## Model Performance

| Metric | Value |
|--------|-------|
| Accuracy | ~74.5% |
| AUC-ROC | 0.818 |
| Brier Score | 0.1742 |
| Features | 41 |
| Training data | 2023 (H2) + full 2024 season |
| Test data | 2025 season (out-of-sample) |

---

## Tech Stack

- **Data:** Python, Pandas, BeautifulSoup, ESPN API
- **Model:** LightGBM, scikit-learn, joblib
- **Backend:** Flask, Flask-CORS
- **Frontend:** React, Vite, Axios
