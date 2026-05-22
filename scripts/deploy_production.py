"""
Deploy HoopsAI to Render + Supabase (plan: Simple Render Deploy).

Requires in .env or environment:
  DATABASE_URL   — real Supabase Postgres URI (not .env.example placeholder)
  RENDER_API_KEY — from https://dashboard.render.com/u/settings?add-api-key

Usage (repo root):
  python scripts/deploy_production.py
  python scripts/deploy_production.py --skip-render   # Supabase setup only
  python scripts/deploy_production.py --skip-supabase # Render only
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/RoycetheGreat2/HoopsAI"
API_NAME = "hoopsai-api"
WEB_NAME = "hoopsai-web"
RENDER_API = "https://api.render.com/v1"
PLACEHOLDER_MARKERS = ("YOUR_PROJECT", "YOUR_PASSWORD", "your-api.onrender.com")


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: Set {name} in .env or the environment.")
        sys.exit(1)
    if any(m in value for m in PLACEHOLDER_MARKERS):
        print(f"ERROR: {name} still contains placeholder text. Use a real value.")
        sys.exit(1)
    return value


def render_request(
    method: str,
    path: str,
    api_key: str,
    body: dict | None = None,
) -> dict | list:
    url = f"{RENDER_API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:2000]
        print(f"Render API {method} {path} failed: {e.code}\n{detail}")
        sys.exit(1)


def get_owner_id(api_key: str) -> str:
    owners = render_request("GET", "/owners?limit=20", api_key)
    if not owners:
        print("ERROR: No Render workspaces found for this API key.")
        sys.exit(1)
    owner = owners[0]
    oid = owner.get("owner", owner).get("id") or owner.get("id")
    name = owner.get("owner", owner).get("name") or owner.get("name") or oid
    print(f"Using Render workspace: {name} ({oid})")
    return oid


def find_service(api_key: str, name: str) -> dict | None:
    services = render_request("GET", f"/services?name={name}&limit=20", api_key)
    for item in services or []:
        svc = item.get("service", item)
        if svc.get("name") == name:
            return svc
    return None


def service_url(svc: dict) -> str:
    host = (svc.get("serviceDetails") or {}).get("url") or svc.get("url")
    if host:
        return host if host.startswith("http") else f"https://{host}"
    slug = svc.get("slug") or svc.get("name", "").replace("_", "-")
    return f"https://{slug}.onrender.com"


def create_or_get_api(api_key: str, owner_id: str, database_url: str) -> dict:
    existing = find_service(api_key, API_NAME)
    if existing:
        print(f"API service exists: {service_url(existing)}")
        return existing

    body = {
        "type": "web_service",
        "name": API_NAME,
        "ownerId": owner_id,
        "repo": REPO,
        "branch": "main",
        "autoDeploy": "yes",
        "envVars": [
            {"key": "DATABASE_URL", "value": database_url},
            {"key": "FLASK_DEBUG", "value": "0"},
        ],
        "serviceDetails": {
            "runtime": "python",
            "plan": "free",
            "healthCheckPath": "/api/health",
            "envSpecificDetails": {
                "buildCommand": "pip install -r requirements.txt",
                "startCommand": (
                    "gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1"
                ),
            },
        },
    }
    print("Creating Render API service...")
    result = render_request("POST", "/services", api_key, body)
    svc = result.get("service", result)
    print(f"API service created: {service_url(svc)}")
    return svc


def create_or_get_web(api_key: str, owner_id: str, api_url: str) -> dict:
    existing = find_service(api_key, WEB_NAME)
    if existing:
        print(f"Static site exists: {service_url(existing)}")
        return existing

    body = {
        "type": "static_site",
        "name": WEB_NAME,
        "ownerId": owner_id,
        "repo": REPO,
        "branch": "main",
        "rootDir": "frontend",
        "autoDeploy": "yes",
        "envVars": [{"key": "VITE_API_URL", "value": api_url.rstrip("/")}],
        "serviceDetails": {
            "buildCommand": "npm install && npm run build",
            "publishPath": "dist",
        },
    }
    print("Creating Render static site...")
    result = render_request("POST", "/services", api_key, body)
    svc = result.get("service", result)
    print(f"Static site created: {service_url(svc)}")
    return svc


def update_cors(api_key: str, service_id: str, web_origin: str) -> None:
    """Set CORS_ORIGINS on the API service (PUT replaces all env vars)."""
    path = f"/services/{service_id}/env-vars"
    existing = render_request("GET", path, api_key)
    env_map: dict[str, str] = {}
    if isinstance(existing, list):
        for item in existing:
            ev = item.get("envVar", item)
            key = ev.get("key")
            if key:
                env_map[key] = ev.get("value", "")
    env_map["CORS_ORIGINS"] = web_origin.rstrip("/")
    env_list = [{"key": k, "value": v} for k, v in env_map.items()]
    render_request("PUT", path, api_key, env_list)
    print(f"CORS_ORIGINS set to {web_origin}")
    render_request(
        "POST",
        f"/services/{service_id}/deploys",
        api_key,
        {"clearCache": "do_not_clear"},
    )


def setup_supabase() -> None:
    print("\n=== Supabase setup ===")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "setup_database.py")],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "migrate_json_to_db.py")],
        cwd=ROOT,
        check=True,
    )
    print("Supabase tables ready.")


def set_github_secret(database_url: str) -> None:
    try:
        subprocess.run(
            [
                "gh",
                "secret",
                "set",
                "DATABASE_URL",
                "--body",
                database_url,
                "-R",
                "RoycetheGreat2/HoopsAI",
            ],
            check=True,
            capture_output=True,
        )
        print("GitHub secret DATABASE_URL updated.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: could not set GitHub secret: {e}")


def wait_for_health(api_url: str, timeout: int = 300) -> bool:
    health = f"{api_url.rstrip('/')}/api/health"
    print(f"Waiting for {health} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(health, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    print("Health check OK.")
                    return True
        except Exception:
            pass
        time.sleep(15)
    print("Health check timed out (cold start may need more time).")
    return False


def smoke_test(api_url: str, web_url: str) -> None:
    print("\n=== Smoke tests ===")
    wait_for_health(api_url)
    weekly = f"{api_url.rstrip('/')}/api/weekly-predictions"
    try:
        with urllib.request.urlopen(weekly, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            n = len(data) if isinstance(data, list) else len(data.get("games", data.get("predictions", [])))
            print(f"weekly-predictions: OK ({n} items)")
    except Exception as e:
        print(f"weekly-predictions: {e}")

    try:
        req = urllib.request.Request(web_url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Frontend: HTTP {resp.status}")
    except Exception as e:
        print(f"Frontend: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy HoopsAI (Render + Supabase)")
    parser.add_argument("--skip-supabase", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--skip-github-secret", action="store_true")
    args = parser.parse_args()

    load_dotenv()

    if not args.skip_supabase:
        db_url = require_env("DATABASE_URL")
        setup_supabase()
        if not args.skip_github_secret:
            set_github_secret(db_url)
    else:
        db_url = os.environ.get("DATABASE_URL", "").strip()

    if args.skip_render:
        print("Render deploy skipped.")
        return

    api_key = require_env("RENDER_API_KEY")
    if not db_url:
        db_url = require_env("DATABASE_URL")

    owner_id = get_owner_id(api_key)
    api_svc = create_or_get_api(api_key, owner_id, db_url)
    api_url = service_url(api_svc)
    web_svc = create_or_get_web(api_key, owner_id, api_url)
    web_url = service_url(web_svc)

    api_id = api_svc.get("id")
    if api_id:
        update_cors(api_key, api_id, web_url)

    print("\n=== Deploy URLs ===")
    print(f"API:      {api_url}")
    print(f"Frontend: {web_url}")
    smoke_test(api_url, web_url)


if __name__ == "__main__":
    main()
