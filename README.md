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

---

## Running Locally

### Virtual environments (`venv` vs `.venv`)

Use **one** environment at the repo root — not both.

| Folder | Activate (PowerShell) |
|--------|------------------------|
| `venv` (recommended) | `.\venv\Scripts\activate` |
| `.venv` (also fine) | `.\.venv\Scripts\activate` |

If you accidentally created `.venv` and already have `venv`, delete the extra copy to save space (both are gitignored):

```powershell
# Only if you do NOT need .venv — keeps your original venv/
Remove-Item -Recurse -Force .venv
```

Then install deps **after** activating the environment you keep:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 1. Install dependencies

```bash
# Python backend (from repo root, venv activated)
pip install -r requirements.txt

# React frontend
cd frontend && npm install
```

Verify plan artifacts:

```bash
python scripts/verify_setup.py
```

### 2. Start the backend API

```bash
python app.py
# http://127.0.0.1:5000
```

### 3. Start the frontend (separate terminal)

```bash
cd frontend
npm run dev
# http://localhost:3000  (Vite proxies /api → Flask on port 5000)
```

If the UI shows "Could not reach the API", start step 2 first, then open http://127.0.0.1:5000/api/health — you should see `{"status":"ok",...}`.

### Production-style local API (Gunicorn)

```bash
gunicorn app:app --bind 0.0.0.0:5000 --timeout 120 --workers 1
```

---

## Deploy (hosting)

Use **two services**: a Python **web service** (API) and a **static site** (frontend). Vite’s dev proxy does not run in production; the built UI must know your API URL.

### Render Blueprint requires payment?

Render’s **Blueprint** flow often asks for a card or paid plan. You do **not** need Blueprint. Pick one of these instead:

| Option | Cost | Notes |
|--------|------|--------|
| **GitHub Pages + Fly.io** (recommended free) | $0 | Frontend: [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml). API: [`fly.toml`](fly.toml) + [`Dockerfile`](Dockerfile). |
| **Render — manual services** | Free tier limits | Create **Web Service** + **Static Site** by hand in the dashboard (no Blueprint). Same env vars as below. |
| **Railway** | Trial / usage-based | Uses [`Procfile`](Procfile); two services from GitHub repo. |

#### Free path: GitHub Pages (UI) + Fly.io (API)

**1. API on Fly.io**

```powershell
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
cd C:\Users\Cinnamoroll\nba-win-predictor
fly launch --no-deploy   # pick app name, region; do not deploy yet
fly secrets set CORS_ORIGINS=https://RoycetheGreat2.github.io/HoopsAI/
fly deploy
fly status   # note URL, e.g. https://hoopsai-api.fly.dev
```

**2. Frontend on GitHub Pages**

- Repo **Settings → Pages → Build and deployment**: Source = **GitHub Actions**.
- Run workflow **Deploy frontend (GitHub Pages)** with `api_url` = your Fly URL (or push to `main` after editing the default in the workflow).
- Site URL: `https://RoycetheGreat2.github.io/HoopsAI/` (repo name must match `VITE_BASE_PATH` in the workflow).

**3. Wire CORS**

Set `CORS_ORIGINS` on the API to your Pages URL (exact origin, no trailing path).

#### Render without Blueprint (manual)

1. **New → Web Service** → connect GitHub repo → root directory, build `pip install -r requirements.txt`, start `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`.
2. **New → Static Site** → `frontend/`, build `npm install && npm run build`, publish `dist`, set `VITE_API_URL`.
3. Set `CORS_ORIGINS` on the API to the static site URL.

---

## Deploy on Render or Railway (reference)

Use **two services**: a Python **web service** (API) and a **static site** (frontend).

### Files included for deploy

| File | Purpose |
|------|---------|
| [`requirements.txt`](requirements.txt) | Python dependencies |
| [`Procfile`](Procfile) | Railway start command |
| [`render.yaml`](render.yaml) | Optional Render Blueprint (API + static site) |
| [`frontend/.env.example`](frontend/.env.example) | `VITE_API_URL` template |

### Must be in Git (or uploaded to the host)

- `models/nba_model.pkl`, `models/features.pkl`
- `data/nba_games_features.csv` (loaded at API startup)
- `scripts/live_predict.py` (imported by `app.py`)
- Writable `data/` for `prediction_tracker.json` (accuracy since 2026-05-22)

### Service 1 — API (Render Web Service or Railway)

| Setting | Value |
|---------|--------|
| Root directory | repo root |
| Build | `pip install -r requirements.txt` |
| Start | `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1` |
| Health check | `/api/health` |

**Environment variables**

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | Auto | Set by Render/Railway |
| `CORS_ORIGINS` | Recommended | Comma-separated frontend URL(s), e.g. `https://hoopsai-web.onrender.com` |
| `FLASK_DEBUG` | Optional | Set to `0` in production |

**Smoke tests after deploy**

- `https://YOUR-API.onrender.com/api/health`
- `https://YOUR-API.onrender.com/api/weekly-predictions` (may take 30–60s)

### Service 2 — Frontend (Render Static Site or Railway static)

| Setting | Value |
|---------|--------|
| Root | `frontend` |
| Build | `npm install && npm run build` |
| Publish directory | `dist` |

**Build environment**

| Variable | Example |
|----------|---------|
| `VITE_API_URL` | `https://hoopsai-api.onrender.com` (no trailing slash) |

Redeploy the static site whenever the API URL changes.

### Wire services together

1. Deploy the API → copy its public URL.
2. Set `VITE_API_URL` on the static site → deploy frontend.
3. Set `CORS_ORIGINS` on the API to the static site URL → redeploy API.
4. Open the frontend URL; the hero should show "Live predictions active".

### Persistent accuracy data

`data/prediction_tracker.json` is updated when users load games. On free tiers, **disk is ephemeral** — the file resets on redeploy unless you attach a **persistent volume** (Render Disk / Railway Volume) mounted at `data/`.

### Railway quick start

1. New project from GitHub repo.
2. Add a service using the repo root; Railway detects [`Procfile`](Procfile).
3. Add a second static service from `frontend/` with build `npm install && npm run build`, output `dist`, and `VITE_API_URL`.

---

## Updating the Model and Data

There are three paths — do not confuse them.

### Path 1 — Live predictions (automatic)

**When:** Each visit / call to `/api/weekly-predictions`.

**What changes:** ESPN schedule + probabilities from the **existing** `nba_model.pkl` and latest team rows in `nba_games_features.csv`. Injury features are **0** live. Finished games are tracked since 2026-05-22 in **Postgres** (if `DATABASE_URL` is set) or `data/prediction_tracker.json`.

No scripts to run. **Retrain does not use ESPN** — training data comes from Basketball-Reference scrapers.

### Path 2 — Refresh team form (manual, no retrain)

**When:** Weekly, after new games finish — keeps rolling averages and ELO current without retraining.

```powershell
cd C:\Users\Cinnamoroll\nba-win-predictor
.\venv\Scripts\activate

python scripts/scraper.py
python scripts/scrape_players_historical.py
python scripts/scrape_player_gamelogs_historical.py
python scripts/build_injury_features.py
python scripts/features.py

# Restart API locally or redeploy so app.py reloads the CSV
```

**Season labels:** [`scripts/features.py`](scripts/features.py) assigns each raw game a B-Ref season end year from its date (e.g. Oct 2025 → season `2026`). [`scripts/scraper.py`](scripts/scraper.py) uses `BREF_SEASON=2026` for the current schedule URL.

### Path 3 — Full retrain (manual or monthly)

**When:** Monthly automation or after you have refreshed the feature matrix.

```powershell
# One command (scrape + features + train):
python scripts/monthly_pipeline.py

# Or only features + train if CSVs are already fresh:
$env:SKIP_SCRAPE="1"
python scripts/monthly_pipeline.py
```

[`scripts/train.py`](scripts/train.py):

- **Train:** 2023 H2 + full 2024 + full 2025 (weights: 2023=1×, 2024/2025=2×)
- **Test:** 2026 season (falls back to 2025 if no 2026 rows yet)
- **Saves** `models/nba_model.pkl` + `models/features.pkl` (best tuning variant, or baseline 41f)
- Writes `data/monthly_train_summary.json` for CI / `model_runs` logging

Restart or redeploy the API after new artifacts exist.

### Monthly automation (GitHub Actions)

Workflow: [`.github/workflows/monthly-retrain.yml`](.github/workflows/monthly-retrain.yml)

- Runs on the **1st of each month** (06:00 UTC) or manually via **workflow_dispatch**
- Runs `scripts/monthly_pipeline.py`
- Uploads `nba_games_features.csv`, model pickles, and summary as workflow artifacts
- Set GitHub secret `DATABASE_URL` to log runs into Supabase `model_runs`

Basketball-Reference may rate-limit; monthly cadence is appropriate.

### Recommended cadence

| Cadence | Action |
|---------|--------|
| Daily | Nothing; tracker updates via API |
| Weekly | Path 2 (`features.py` only) after updating `nba_games_raw.csv` |
| Monthly | `python scripts/monthly_pipeline.py` or GitHub Actions workflow |

---

## Supabase database (recommended for production)

Training still uses **CSV + pickle files**. Postgres stores **live prediction accuracy** and **monthly job history** so redeploys do not wipe stats.

### Setup

1. Create a free project at [supabase.com](https://supabase.com).
2. Copy the **Database URI** (Settings → Database).
3. Copy [`.env.example`](.env.example) to `.env` and set `DATABASE_URL=postgresql://...`
4. From repo root:

```powershell
pip install -r requirements.txt
python scripts/setup_database.py
```

Tables: `predictions`, `model_runs`, `playoff_tracker` (schema reserved).

Migrate existing JSON tracker into Postgres (optional, once):

```powershell
python scripts/migrate_json_to_db.py
```

### App behavior

| `DATABASE_URL` | Prediction tracking |
|----------------|---------------------|
| Set | [`app.py`](app.py) writes/reads `predictions` table |
| Not set | Falls back to `data/prediction_tracker.json` |

Set `DATABASE_URL` on **Render/Railway** for the API service and in **GitHub Actions secrets** for monthly logs.

Also set `CORS_ORIGINS` to your static site URL in production.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | API connection check |
| `GET /api/predictions` | Latest pre-generated predictions |
| `GET /api/weekly-predictions` | Live 7-day predictions via ESPN (`?start=YYYY-MM-DD` optional) |
| `GET /api/prediction-accuracy` | Correct picks for past 7 / 30 days (since 2026-05-22) |
| `GET /api/playoff-stats` | Playoff prediction accuracy tracker |
| `GET /api/model-stats` | Model validation metrics (legacy) |

---

## Model Performance

| Metric | Value |
|--------|-------|
| Accuracy | ~74.5% |
| AUC-ROC | 0.818 |
| Brier Score | 0.1742 |
| Features | 41 |
| Training data | 2023 (H2) + 2024 + 2025 |
| Test data | 2026 season (forward validation; falls back to 2025 if empty) |

---

## Tech Stack

- **Data:** Python, Pandas, ESPN API, Basketball-Reference scrapers
- **Model:** LightGBM, scikit-learn, joblib
- **Backend:** Flask, Flask-CORS, Gunicorn
- **Frontend:** React, Vite, TypeScript, Tailwind
