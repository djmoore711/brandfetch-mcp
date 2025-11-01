---
description: Clean development artifacts and prepare project for GitHub push
---

# Clean Project for GitHub

This workflow removes development artifacts and sensitive files that shouldn't be tracked in git, preparing the brandfetch_mcp project for a clean GitHub push.

## Prerequisites

- Run from project root directory
- Ensure all important work is committed or stashed
- Have git available
- **Optional**: Set DRY_RUN=1 to preview changes without executing

## Steps

### 1. Pre-flight checks
```bash
# Check for uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "⚠️  You have uncommitted changes!"
    echo "   Please commit or stash changes before running this cleanup."
    echo "   Or set IGNORE_UNCOMMITTED=1 to proceed anyway."
    [[ -n "$IGNORE_UNCOMMITTED" ]] || exit 1
fi

# Check current git status
echo "=== Current git status ==="
git status

echo ""
if [[ -n "$DRY_RUN" ]]; then
    echo "🔍 DRY RUN MODE: Showing what would be removed without executing"
fi
```

### 2. Check for sensitive files in git history (CRITICAL)
```bash
# Check if .env was ever committed - if so, API keys are in git history!
if git log --all --full-history -- .env 2>/dev/null | grep -q "commit"; then
    echo "🚨 SECURITY ALERT: .env found in git history!"
    echo "   API keys may be exposed. You MUST:"
    echo "   1. Rotate all Brandfetch API keys immediately"
    echo "   2. Remove from history: git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all"
    echo "   3. Force push: git push --force-with-lease"
    echo "   ⚠️  Do NOT push to GitHub until keys are rotated!"
    
    if [[ -z "$SKIP_INTERACTIVE" ]]; then
        read -p "Type 'understood' to continue: " && [[ $REPLY == "understood" ]] || exit 1
    else
        echo "SKIP_INTERACTIVE set - continuing without confirmation"
    fi
else
    echo "✅ .env not found in git history"
fi
```

### 3. Verify .gitignore patterns before cleanup
```bash
echo "Checking .gitignore has necessary patterns..."
required_patterns=(".env" ".coverage" "*.db" ".python-version" "uv.lock" ".pytest_cache" "__pycache__" ".shellcheckrc" ".snyk")

for pattern in "${required_patterns[@]}"; do
    if ! grep -q "^$pattern" .gitignore && ! grep -q "/$pattern" .gitignore && ! grep -q "\*$pattern" .gitignore; then
        echo "⚠️  Pattern '$pattern' missing from .gitignore - adding it"
        if [[ -z "$DRY_RUN" ]]; then
            echo "$pattern" >> .gitignore
        else
            echo "   [DRY RUN] Would add: $pattern"
        fi
    fi
done
```

### 4. Remove sensitive and development files from git tracking
```bash
# Function to safely remove files with dry-run support
safe_git_rm() {
    local file="$1"
    local desc="$2"
    
    if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        echo "Removing $desc from git tracking: $file"
        if [[ -z "$DRY_RUN" ]]; then
            git rm --cached "$file" 2>/dev/null || echo "Failed to remove $file"
        else
            echo "   [DRY RUN] Would remove: $file"
        fi
    else
        echo "$desc not tracked: $file"
    fi
}

# Remove sensitive files
safe_git_rm ".env" "API key file"
safe_git_rm ".coverage" "coverage file"
safe_git_rm "brand_api_usage.db" "database file"
safe_git_rm ".python-version" "Python version file"
safe_git_rm "uv.lock" "uv lock file"

# Remove development directories
if git ls-files --error-unmatch ".pytest_cache" >/dev/null 2>&1; then
    echo "Removing pytest cache from git tracking"
    if [[ -z "$DRY_RUN" ]]; then
        git rm -r --cached .pytest_cache 2>/dev/null || echo ".pytest_cache not tracked"
    else
        echo "   [DRY RUN] Would remove directory: .pytest_cache"
    fi
else
    echo "pytest cache not tracked: .pytest_cache"
fi

# Remove other development files
safe_git_rm ".shellcheckrc" "shellcheck config"
safe_git_rm ".snyk" "snyk config"
```

### 5. Clean up empty/placeholder files
```bash
# Check if API_KEY_SETUP.md is referenced before removing
if grep -q "API_KEY_SETUP.md" README.md; then
    echo "API_KEY_SETUP.md is referenced in README.md - keeping with TODO"
    echo "# TODO: Add screenshots for API key setup" > API_KEY_SETUP.md
else
    git rm API_KEY_SETUP.md 2>/dev/null || echo "API_KEY_SETUP.md not tracked"
fi

# Check if manual_test.py is referenced before removing  
if grep -q "manual_test.py" README.md; then
    echo "manual_test.py is referenced in README.md - keeping with TODO"
    echo "# TODO: Add manual test script" > manual_test.py
else
    git rm manual_test.py 2>/dev/null || echo "manual_test.py not tracked"
fi
```

### 6. Clean Python cache directories
```bash
# Safer cleanup that avoids recursion into deleted directories
find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
```

### 7. Remove IDE-specific directories
```bash
if git ls-files --error-unmatch ".windsurf" >/dev/null 2>&1; then
    echo "Removing IDE-specific directory from git tracking"
    if [[ -z "$DRY_RUN" ]]; then
        git rm -r --cached .windsurf 2>/dev/null || echo ".windsurf not tracked"
    else
        echo "   [DRY RUN] Would remove directory: .windsurf"
    fi
else
    echo "IDE directory not tracked: .windsurf"
fi
```

### 8. Final status check
```bash
echo "=== Final git status ==="
git status
echo ""
echo "=== Files ready to commit ==="
git status --porcelain | grep "^.D" || echo "No files staged for deletion"
```

### 9. Commit the cleanup
```bash
if [[ -n "$DRY_RUN" ]]; then
    echo "🔍 DRY RUN COMPLETE: No changes made"
    echo "   Run without DRY_RUN=1 to execute the cleanup"
else
    echo "Committing cleanup changes..."
    # Only stage tracked file updates/deletions, not untracked files
    git add -u
    
    # Show what will be committed
    echo "Changes to be committed:"
    git diff --cached --name-status
    
    git commit -m "chore: remove development artifacts from git tracking"
    echo "✅ Cleanup committed successfully"
fi
```

## Usage Examples

```bash
# Standard cleanup
./scripts/clean-for-github.sh

# Preview changes first
DRY_RUN=1 ./scripts/clean-for-github.sh

# Skip interactive prompts (CI/CD)
SKIP_INTERACTIVE=1 ./scripts/clean-for-github.sh

# Ignore uncommitted changes
IGNORE_UNCOMMITTED=1 ./scripts/clean-for-github.sh
```

## Security Notes

- **CRITICAL**: If `.env` was tracked, API keys are in git history. The workflow above detects this and provides remediation steps. Do NOT push to GitHub until keys are rotated and history cleaned.
- **Non-interactive mode**: Step 2 includes interactive prompts. In CI/CD, set SKIP_INTERACTIVE=1 to bypass prompts.

### 10. Optional: Use existing git readiness checker
```bash
# Alternative: run the existing script if preferred (run before committing)
# Note: This workflow provides more comprehensive security checks
if [[ -f "git_readiness_checker.sh" && -z "$DRY_RUN" ]]; then
    echo "\n=== Alternative: existing git readiness checker ==="
    echo "Note: This workflow provides additional security checks for .env history"
    echo "Run this before step 9 if you want to use it instead"
    # ./git_readiness_checker.sh  # Uncomment to use
fi
```

## Rollback Instructions

If something goes wrong before step 9:
```bash
# Unstage all changes
git reset HEAD

# Restore accidentally removed files (if needed)
git checkout HEAD -- .env .coverage etc
```

## Idempotency

This workflow is safe to run multiple times:
- Files already untracked will be skipped
- .gitignore patterns already present won't be duplicated
- Dry-run mode lets you preview before executing

## Verification

After cleanup, verify the project is ready:

```bash
# Test installation still works
uv pip install -e ".[dev]"

# Run tests to ensure nothing broken
pytest tests/ -v

# Verify git status is clean
git status
```

## What This Preserves

- Source code in `src/`
- Tests in `tests/` 
- Documentation files
- Configuration files (pyproject.toml, requirements.txt)
- Examples and examples data
- Docker files
- Build scripts (Makefile, run.sh)

## What This Removes

- API keys and environment files
- Python cache files
- Coverage reports
- Local databases
- IDE-specific files
- Development lock files
- Temporary build artifacts
