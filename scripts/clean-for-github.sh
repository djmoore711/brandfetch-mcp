#!/bin/bash

# Clean Project for GitHub
# This script removes development artifacts and sensitive files that shouldn't be tracked in git
# preparing the brandfetch_mcp project for a clean GitHub push

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}🚨 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_dry_run() {
    if [[ -n "$DRY_RUN" ]]; then
        echo -e "${BLUE}   [DRY RUN] $1${NC}"
    fi
}

# Function to safely remove files with dry-run support
safe_git_rm() {
    local file="$1"
    local desc="$2"
    
    if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        echo "Removing $desc from git tracking: $file"
        if [[ -z "${DRY_RUN:-}" ]]; then
            if git rm --cached "$file" 2>/dev/null; then
                return 0
            else
                echo "Failed to remove $file"
                return 1
            fi
        else
            print_dry_run "Would remove: $file"
            return 0
        fi
    else
        echo "$desc not tracked: $file"
        return 1  # Return 1 for not tracked
    fi
}

# Function to check gitignore patterns
check_gitignore_pattern() {
    local pattern="$1"
    
    # Escape special characters for pattern matching
    local escaped_pattern
    escaped_pattern=$(echo "$pattern" | sed 's/\*/\\*/g' | sed 's/\./\\./g')
    
    # Try different pattern matching approaches
    if grep -q "^$pattern" .gitignore 2>/dev/null || \
       grep -q "/$pattern" .gitignore 2>/dev/null || \
       grep -q "\*$pattern" .gitignore 2>/dev/null || \
       grep -q "$escaped_pattern" .gitignore 2>/dev/null; then
        return 0  # Pattern found
    else
        return 1  # Pattern not found
    fi
}

# Main script starts here
main() {
    print_status "Clean Project for GitHub - Starting"
    
    # Check if we're in a git repository
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        print_error "Not in a git repository!"
        exit 1
    fi
    
    # Check if we're in project root (look for pyproject.toml)
    if [[ ! -f "pyproject.toml" ]]; then
        print_error "pyproject.toml not found - run from project root directory!"
        exit 1
    fi
    
    # Pre-flight checks
    print_status "Pre-flight checks"
    
    # Initialize variables
    : "${DRY_RUN:=}"
    
    # Check for uncommitted changes
    if ! git diff --quiet || ! git diff --cached --quiet; then
        print_warning "You have uncommitted changes!"
        echo "   Please commit or stash changes before running this cleanup."
        echo "   Or set IGNORE_UNCOMMITTED=1 to proceed anyway."
        if [[ -z "${IGNORE_UNCOMMITTED:-}" ]]; then
            exit 1
        fi
    fi
    
    # Show current git status
    echo ""
    git status --porcelain
    
    echo ""
    if [[ -n "${DRY_RUN:-}" ]]; then
        print_status "DRY RUN MODE - Showing what would be removed without executing"
    fi
    
    # Check for sensitive files in git history
    print_status "Security check - scanning git history"
    
    if git log --all --full-history -- .env 2>/dev/null | grep -q "commit"; then
        print_error ".env found in git history!"
        echo "   API keys may be exposed. You MUST:"
        echo "   1. Rotate all Brandfetch API keys immediately"
        echo "   2. Remove from history: git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env' --prune-empty --tag-name-filter cat -- --all"
        echo "   3. Force push: git push --force-with-lease"
        echo "   ⚠️  Do NOT push to GitHub until keys are rotated!"
        
        if [[ -z "${SKIP_INTERACTIVE:-}" && -z "${DRY_RUN:-}" ]]; then
            echo ""
            read -r -p "Type 'understood' to continue: " && [[ $REPLY == "understood" ]] || exit 1
        elif [[ -n "${SKIP_INTERACTIVE:-}" ]]; then
            echo "SKIP_INTERACTIVE set - continuing without confirmation"
        fi
    else
        print_success ".env not found in git history"
    fi
    
    # Verify .gitignore patterns
    print_status "Verifying .gitignore patterns"
    
    required_patterns=(".env" ".coverage" "*.db" ".python-version" "uv.lock" ".pytest_cache" "__pycache__" ".shellcheckrc" ".snyk")
    patterns_added=0
    
    for pattern in "${required_patterns[@]}"; do
        if ! check_gitignore_pattern "$pattern"; then
            print_warning "Pattern '$pattern' missing from .gitignore - adding it"
            ((patterns_added++))  # Count regardless of dry-run mode
            if [[ -z "${DRY_RUN:-}" ]]; then
                echo "$pattern" >> .gitignore
            else
                print_dry_run "Would add: $pattern"
            fi
        fi
    done
    
    # Remove sensitive and development files
    print_status "Removing sensitive and development files from git tracking"
    
    files_removed=0
    # Remove sensitive files
    if safe_git_rm ".env" "API key file"; then ((files_removed++)); fi
    if safe_git_rm ".coverage" "coverage file"; then ((files_removed++)); fi
    if safe_git_rm "brand_api_usage.db" "database file"; then ((files_removed++)); fi
    if safe_git_rm ".python-version" "Python version file"; then ((files_removed++)); fi
    if safe_git_rm "uv.lock" "uv lock file"; then ((files_removed++)); fi
    
    # Remove development directories
    if git ls-files --error-unmatch ".pytest_cache" >/dev/null 2>&1; then
        echo "Removing pytest cache from git tracking"
        if [[ -z "${DRY_RUN:-}" ]]; then
            if git rm -r --cached .pytest_cache 2>/dev/null; then
                ((files_removed++))
            fi
        else
            print_dry_run "Would remove directory: .pytest_cache"
            ((files_removed++))
        fi
    else
        echo "pytest cache not tracked: .pytest_cache"
    fi
    
    # Remove other development files
    if safe_git_rm ".shellcheckrc" "shellcheck config"; then ((files_removed++)); fi
    if safe_git_rm ".snyk" "snyk config"; then ((files_removed++)); fi
    
    # Clean up empty/placeholder files
    print_status "Cleaning up empty/placeholder files"
    
    if grep -q "API_KEY_SETUP.md" README.md 2>/dev/null; then
        echo "API_KEY_SETUP.md is referenced in README.md - keeping with TODO"
        if [[ -z "${DRY_RUN:-}" ]]; then
            echo "# TODO: Add screenshots for API key setup" > API_KEY_SETUP.md
        else
            print_dry_run "Would update: API_KEY_SETUP.md with TODO content"
        fi
    else
        if git ls-files --error-unmatch "API_KEY_SETUP.md" >/dev/null 2>&1; then
            echo "Removing API_KEY_SETUP.md from git tracking"
            if [[ -z "${DRY_RUN:-}" ]]; then
                if git rm API_KEY_SETUP.md 2>/dev/null; then
                    ((files_removed++))
                fi
            else
                print_dry_run "Would remove: API_KEY_SETUP.md"
                ((files_removed++))
            fi
        fi
    fi
    
    if grep -q "manual_test.py" README.md 2>/dev/null; then
        echo "manual_test.py is referenced in README.md - keeping with TODO"
        if [[ -z "${DRY_RUN:-}" ]]; then
            echo "# TODO: Add manual test script" > manual_test.py
        else
            print_dry_run "Would update: manual_test.py with TODO content"
        fi
    else
        if git ls-files --error-unmatch "manual_test.py" >/dev/null 2>&1; then
            echo "Removing manual_test.py from git tracking"
            if [[ -z "${DRY_RUN:-}" ]]; then
                if git rm manual_test.py 2>/dev/null; then
                    ((files_removed++))
                fi
            else
                print_dry_run "Would remove: manual_test.py"
                ((files_removed++))
            fi
        fi
    fi
    
    # Clean Python cache directories
    print_status "Cleaning Python cache directories"
    
    if [[ -z "${DRY_RUN:-}" ]]; then
        # Safer cleanup that avoids recursion into deleted directories
        find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        find . -name "*.pyo" -delete 2>/dev/null || true
        echo "Python cache directories cleaned"
    else
        print_dry_run "Would clean Python cache directories (__pycache__, *.pyc, *.pyo)"
    fi
    
    # Remove IDE-specific directories
    print_status "Removing IDE-specific directories"
    
    if git ls-files --error-unmatch ".windsurf" >/dev/null 2>&1; then
        echo "Removing IDE-specific directory from git tracking"
        if [[ -z "${DRY_RUN:-}" ]]; then
            if git rm -r --cached .windsurf 2>/dev/null; then
                ((files_removed++))
            fi
        else
            print_dry_run "Would remove directory: .windsurf"
            ((files_removed++))
        fi
    else
        echo "IDE directory not tracked: .windsurf"
    fi
    
    # Final status check
    print_status "Final status check"
    git status --porcelain
    
    # Commit or show summary
    if [[ -n "${DRY_RUN:-}" ]]; then
        echo ""
        print_status "DRY RUN COMPLETE"
        echo "   No changes were made"
        echo "   Run without DRY_RUN=1 to execute the cleanup"
        echo ""
        echo "Summary of what would be done:"
        echo "   - Files to remove from git tracking: $files_removed"
        echo "   - Patterns to add to .gitignore: $patterns_added"
    else
        echo ""
        echo "Committing cleanup changes"
        
        # Stage .gitignore changes first if any were added
        if [[ $patterns_added -gt 0 ]]; then
            git add .gitignore
        fi
        
        # Only stage tracked file updates/deletions, not untracked files
        git add -u
        
        # Show what will be committed
        echo "Changes to be committed:"
        git diff --cached --name-status
        
        if git commit -m "chore: remove development artifacts from git tracking"; then
            print_success "Cleanup committed successfully"
            echo ""
            echo "Summary of changes:"
            echo "   - Files removed from git tracking: $files_removed"
            echo "   - Patterns added to .gitignore: $patterns_added"
        else
            print_error "Failed to commit changes!"
            echo "   You may need to resolve conflicts or check pre-commit hooks"
            echo "   Use 'git status' to see what went wrong"
            exit 1
        fi
    fi
    
    echo ""
    print_success "Clean Project for GitHub - Complete"
}

# Show help
show_help() {
    cat << EOF
Clean Project for GitHub

Usage: $0 [OPTIONS]

OPTIONS:
    -h, --help              Show this help message
    --dry-run               Preview changes without executing
    
ENVIRONMENT VARIABLES:
    DRY_RUN=1               Preview changes without executing
    SKIP_INTERACTIVE=1      Skip interactive prompts (for CI/CD)
    IGNORE_UNCOMMITTED=1    Ignore uncommitted changes warning

EXAMPLES:
    $0                      # Standard cleanup
    DRY_RUN=1 $0            # Preview changes first
    SKIP_INTERACTIVE=1 $0   # Skip prompts (CI/CD mode)
    IGNORE_UNCOMMITTED=1 $0 # Ignore uncommitted changes

This script removes development artifacts and sensitive files from git tracking,
preparing the brandfetch_mcp project for a clean GitHub push.

EOF
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    --dry-run)
        export DRY_RUN=1
        ;;
    "")
        # No argument, continue normally
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac

# Run main function
main "$@"
