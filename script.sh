#!/usr/bin/env bash
set -euo pipefail

# Run this from /Users/dj/Code/brandfetch_mcp
echo "Starting safe .env restore & .gitignore fix..."

# 1) Restore .env from quarantine if present
QDIR="cleanup-quarantine"
if [ -f "$QDIR/.env" ]; then
  if [ -f .env ]; then
    echo "Local .env already exists; will back it up to cleanup-quarantine/.env.bak before restoring."
    mv .env "$QDIR/.env.bak.$(date +%s)"
  fi
  mv "$QDIR/.env" ./
  echo "Restored $QDIR/.env -> ./ .env"
else
  echo "No $QDIR/.env found — nothing to restore."
fi

# 2) Ensure .gitignore exists
if [ ! -f .gitignore ]; then
  echo "Creating .gitignore"
  touch .gitignore
fi

# 3) Ensure env ignore lines exist
# Add canonical ignore patterns if missing
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
grep -qxF ".env.*" .gitignore || echo ".env.*" >> .gitignore
grep -qxF ".env.local" .gitignore || echo ".env.local" >> .gitignore
grep -qxF "cleanup-quarantine/" .gitignore || echo "cleanup-quarantine/" >> .gitignore

# 4) Ensure the negation for .env.example is present (append if missing)
# Using grouped echo with single redirect for:
# 1. Atomic file operation
# 2. Better performance
# 3. ShellCheck compliance
# Requires bash 3.2+ (2006)
if ! grep -qxF "!/.env.example" .gitignore; then
  {
    echo ""
    echo "# Allow the example env template to be tracked"
    echo "!/.env.example"
  } >> .gitignore || {
    echo "Failed to update .gitignore" >&2
    exit 1
  }
  echo "Appended !/.env.example to .gitignore (ensures .env.example can be tracked)."
else
  echo "Negation for .env.example already present in .gitignore."
fi

# 5) If .env is tracked, remove it from index but keep the file locally
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    git rm --cached .env
    echo ".env removed from index (kept local)."
  else
    echo ".env not tracked by git index (or already removed)."
  fi
else
  echo "Not a git repo (skipping git index cleanup and commits)."
fi

# 6) Create .env.example from .env (if present)
if [ -f .env ]; then
  # Keep comments and keys, strip values: turns KEY=VALUE -> KEY=
  awk '/^[[:space:]]*#/ { print; next } /^[[:space:]]*$/ { next } /^[A-Za-z_][A-Za-z0-9_]*=/ { split($0,a,"="); print a[1]"="; next } { print }' .env > .env.example
  chmod 644 .env.example || true
  echo ".env.example created from .env (values stripped)."
else
  echo "No .env file present — skipping .env.example creation."
fi

# 7) Tighten local permissions on .env if it exists
if [ -f .env ]; then
  chmod 600 .env || true
  echo "Set permissions of .env -> 600 (owner read/write)."
fi

# 8) Stage and commit changes safely if this is a git repo
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  # Only add & commit if there are changes
  git add .gitignore 2>/dev/null || true
  git add .env.example 2>/dev/null || true
  if git diff --cached --quiet; then
    echo "No staged changes to commit (or nothing to commit)."
  else
    git commit -m "chore: ensure .env ignored; allow .env.example; restore local .env (if any)"
    echo "Committed .gitignore and .env.example changes on branch $(git branch --show-current 2>/dev/null || echo 'unknown')."
  fi
else
  echo "Not inside a git repo — skipped staging and committing."
fi

# 9) Diagnostics: show relevant status and checks
echo
echo "==== DIAGNOSTICS ===="
echo "git ignore check for .env.example:"
git check-ignore -v .env.example || echo ".env.example not ignored now"

echo
echo "Is .env tracked?"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    echo "WARNING: .env still tracked in git history/index"
  else
    echo ".env is not tracked by index — correct"
  fi
else
  echo "Not a git repo"
fi

echo
echo "List quarantine dir (if exists):"
ls -la "$QDIR" || echo "No $QDIR directory"
echo "Done."