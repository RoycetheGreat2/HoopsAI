# One-time: paste real credentials, then run deploy.
# Usage (repo root):
#   notepad deploy.credentials.ps1   # fill in values, save
#   .\scripts\setup_deploy_credentials.ps1
#   python scripts/deploy_production.py

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$CredFile = Join-Path $Root "deploy.credentials.ps1"

if (-not (Test-Path $CredFile)) {
    @"
# Copy to deploy.credentials.ps1 (gitignored) and fill in real values.
# `$DATABASE_URL = "postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres"
# `$RENDER_API_KEY = "rnd_..."
"@ | Set-Content (Join-Path $Root "deploy.credentials.ps1.example") -Encoding UTF8
    Write-Host "Created deploy.credentials.ps1.example"
    Write-Host "Copy it to deploy.credentials.ps1, add your Supabase URI and Render API key, then re-run this script."
    exit 1
}

. $CredFile
if (-not $DATABASE_URL -or $DATABASE_URL -match "YOUR_PROJECT") {
    Write-Error "Set a real DATABASE_URL in deploy.credentials.ps1"
}
if (-not $RENDER_API_KEY) {
    Write-Error "Set RENDER_API_KEY in deploy.credentials.ps1"
}

$envPath = Join-Path $Root ".env"
$lines = @()
if (Test-Path $envPath) {
    $lines = Get-Content $envPath | Where-Object { $_ -notmatch "^DATABASE_URL=" }
}
$lines += "DATABASE_URL=$DATABASE_URL"
$lines | Set-Content $envPath -Encoding UTF8
Write-Host "Updated .env with DATABASE_URL"

gh secret set DATABASE_URL --body $DATABASE_URL -R RoycetheGreat2/HoopsAI
gh secret set RENDER_API_KEY --body $RENDER_API_KEY -R RoycetheGreat2/HoopsAI
Write-Host "GitHub secrets DATABASE_URL and RENDER_API_KEY set."

Write-Host "Run: python scripts/deploy_production.py"
