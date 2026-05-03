# NBA Win Predictor — frontend

## Run the stack

**1. Flask API** (from the project root, with the virtual environment active):

```bash
python app.py
```

**2. Vite dev server** (from this `frontend` folder):

```bash
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). API requests to `/api/*` are proxied to the Flask app on `127.0.0.1:5000` via `vite.config.js`.
