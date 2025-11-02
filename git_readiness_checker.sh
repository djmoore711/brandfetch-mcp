#!/usr/bin/env bash
set -e

echo "=== 1) Check git status for .env and .env.example ==="
if git ls-files --error-unmatch .env > /dev/null 2>&1; then
  echo "ERROR: .env is tracked by git! Remove it before pushing."
  git ls-files --error-unmatch .env || true
  exit 1
else
  echo ".env not tracked — good."
fi

if git ls-files --error-unmatch .env.example > /dev/null 2>&1; then
  echo ".env.example is tracked — good."
else
  echo "WARNING: .env.example not found in index. Make sure .env.example exists and is committed."
fi

echo
echo "=== 2) Create & activate venv, install deps ==="
python -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "=== 3) Run Snyk test ==="
if command -v snyk > /dev/null 2>&1; then
  snyk test --file=requirements.txt
else
  echo "snyk not installed; skipping Snyk test. Install with: npm i -g snyk (or brew install snyk)"
fi

echo
echo "=== 4) Run unit tests (if any) ==="
if command -v pytest > /dev/null 2>&1; then
  pytest -q || { echo 'Tests failed'; exit 1; }
else
  echo "pytest not installed. If you have tests, install pytest or run your test command manually."
fi

echo
echo "=== 5) Smoke run the app (server.py) for 5 seconds ==="
# Try common server runner approaches. Adjust if your entrypoint is different.
SMOKE_OK=0

# 1) try python server.py in background
python server.py &
PID=$!
sleep 5
# check still running
if ps -p $PID > /dev/null 2>&1; then
  echo "server.py started (PID $PID). Killing it now."
  kill $PID || true
  SMOKE_OK=1
else
  echo "server.py did not stay up. Trying common frameworks..."
fi

# 2) try Flask
if [[ $SMOKE_OK -eq 0 ]]; then
  if python -c "import importlib.util; exit(0 if importlib.util.find_spec('flask') else 1)" &>/dev/null; then
    echo "Attempting Flask run (FLASK_APP=server.py) for 5s..."
    FLASK_APP=server.py flask run --port 5001 >/dev/null 2>&1 &
    PID=$!
    sleep 5
    if ps -p $PID > /dev/null 2>&1; then
      kill $PID || true
      SMOKE_OK=1
      echo "Flask server started and stopped cleanly."
    else
      echo "Flask attempt failed."
    fi
  fi
fi

# 3) try uvicorn (fastapi)
if [[ $SMOKE_OK -eq 0 ]] && command -v uvicorn > /dev/null 2>&1 ; then
  echo "Attempting uvicorn server: uvicorn server:app --port 5002 for 5s..."
  uvicorn server:app --port 5002 >/dev/null 2>&1 &
  PID=$!
  sleep 5
  if ps -p $PID > /dev/null 2>&1; then
    kill $PID || true
    SMOKE_OK=1
    echo "uvicorn server started and stopped cleanly."
  else
    echo "uvicorn attempt failed."
  fi
fi

if [[ $SMOKE_OK -eq 0 ]]; then
  echo "WARNING: smoke-run didn't detect a common entry. If your entry is different, run it manually (e.g. python server.py or uvicorn server:app)."
else
  echo "Smoke run looks OK."
fi

echo
echo "=== 6) Pre-commit (optional) ==="
if command -v pre-commit > /dev/null 2>&1; then
  pre-commit run --all-files || echo "pre-commit had failures. Fix or skip intentionally."
else
  echo "pre-commit not installed; skipping."
fi

echo
echo "=== Pre-upload checks complete ==="
echo "If everything above succeeded, create a branch and push:"
echo "  git checkout -b prepare-for-github"
echo "  git add ."
echo "  git commit -m 'chore: prepare repo for GitHub (env example, gitignore, requirements)'"
echo "  git push -u origin prepare-for-github"
echo "Then open a PR for review before merging to main."