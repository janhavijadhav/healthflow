#!/bin/bash
# HealthFlow — GitHub setup script
# Double-click this file in Finder to run it in Terminal

set -e
cd "$(dirname "$0")"

echo ""
echo "============================================"
echo "  HealthFlow → GitHub Setup"
echo "============================================"
echo ""

# Clean up any partial git init (e.g. from sandbox attempt)
if [ -d .git ]; then
    echo "🗑  Removing existing .git folder..."
    rm -rf .git
fi

# Initialize fresh repo
echo "📁 Initialising git repo..."
git init -b main
git config user.email "janhavijadhav006@gmail.com"
git config user.name "Janhavi Jadhav"

# Stage all files (sensitive ones are in .gitignore)
echo "📦 Staging files..."
git add .

echo ""
echo "=== Files being committed ==="
git status --short
echo ""

# First commit
echo "✅ Creating initial commit..."
git commit -m "feat: initial commit — HealthFlow cloud-native healthcare claims pipeline

- 3-zone S3 data lakehouse (raw / processed / curated) via Terraform
- AWS Lambda event trigger + Glue schema catalog
- PySpark 3.5 batch transformation → Snappy Parquet
- dbt Core: 4 staging views + 2 mart tables (19/19 tests pass)
- Apache Airflow 3.x on Kubernetes (6-task daily DAG)
- FastAPI REST API with 7 BigQuery-backed endpoints
- GitHub Actions CI: lint, test, Terraform fmt check
- Synthea synthetic EHR data (14K+ records, 6 tables)"

echo ""
echo "============================================"
echo "  Pushing to GitHub..."
echo "============================================"
echo ""

# Try GitHub CLI first (fastest path)
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
    echo "🐙 GitHub CLI detected — creating repo and pushing..."
    gh repo create healthflow \
        --public \
        --description "Cloud-native healthcare claims analytics pipeline: AWS S3 + Glue + Lambda → PySpark → BigQuery → dbt → FastAPI, orchestrated with Airflow on Kubernetes" \
        --source=. \
        --remote=origin \
        --push
    REPO_URL=$(gh repo view healthflow --json url -q .url)
    echo ""
    echo "🎉 Done! Your repo is live at: $REPO_URL"
else
    echo "ℹ️  GitHub CLI not found or not authenticated."
    echo ""
    echo "Please do these two things:"
    echo ""
    echo "  1. Go to https://github.com/new"
    echo "     • Name: healthflow"
    echo "     • Visibility: Public"
    echo "     • Do NOT initialise with README (you already have one)"
    echo ""
    echo "  2. Come back here and run (replace YOUR_USERNAME):"
    echo ""
    echo "     git remote add origin https://github.com/YOUR_USERNAME/healthflow.git"
    echo "     git push -u origin main"
    echo ""
fi

echo ""
echo "Press Enter to close this window."
read
