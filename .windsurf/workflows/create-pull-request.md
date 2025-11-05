---
description: Create a pull request for code changes in the brandfetch-mcp repository
---

# Create Pull Request Workflow

This workflow guides you through creating a pull request (PR) for the brandfetch-mcp repository.

## Prerequisites

1. **Git repository set up** - Ensure you're working in a git repository
2. **GitHub CLI installed** - Required for PR creation (`gh --version`)
3. **Changes committed** - All changes should be committed to a feature branch
4. **Remote repository configured** - Ensure `origin` points to the GitHub repo

## Step-by-Step Process

### 1. Check Current Status

First, verify your current git status and branch:

```bash
git status
git branch -vv
```

This shows:
- What files have been modified
- Which branch you're on
- Whether your branch is ahead/behind remote

### 2. Stage and Commit Changes

If you have unstaged changes:

```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "feat: add new feature description

- What this change does
- Why it's needed
- Any breaking changes
- Testing considerations"
```

**Commit Message Guidelines:**
- Use prefixes: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`
- Keep first line under 50 characters
- Add detailed body for complex changes

### 3. Push Feature Branch

Push your feature branch to GitHub:

```bash
git push origin your-feature-branch-name
```

If this is your first push of the branch, you may need to set the upstream:

```bash
git push -u origin your-feature-branch-name
```

### 4. Create Pull Request

Use GitHub CLI to create the PR:

```bash
gh pr create \
  --base main \
  --head your-feature-branch-name \
  --title "feat: your feature title" \
  --body "## Summary

Brief description of what this PR does.

## Changes

### Code Changes
- List specific files/modules changed
- Describe the functionality added/modified

### Documentation Updates
- README.md, docs, comments updated
- API documentation changes

### Testing
- Unit tests added/updated
- Integration tests verified
- Manual testing completed

## Breaking Changes

List any breaking changes and migration steps for users.

## Testing

Describe how to test the changes:
1. Setup steps
2. Test commands
3. Expected results

## Related Issues

Closes #123, Fixes #456"
```

**PR Body Best Practices:**
- **Summary**: Clear, concise description
- **Changes**: Bullet points of what was modified
- **Breaking Changes**: Highlight any breaking changes
- **Testing**: How reviewers can test the changes
- **Related Issues**: Link to any related GitHub issues

### 5. Review and Iterate

1. **Wait for CI checks** to pass (if configured)
2. **Address review comments**:
   ```bash
   # Make requested changes
   git add .
   git commit -m "fix: address review feedback"
   git push origin your-feature-branch-name
   ```

3. **Re-request review** if needed:
   ```bash
   gh pr ready  # Mark as ready for review
   ```

### 6. Merge the PR

Once approved:

```bash
# Option 1: Merge via GitHub CLI
gh pr merge --merge

# Option 2: Merge via GitHub UI
# Click "Merge pull request" button

# Option 3: Squash and merge
gh pr merge --squash
```

### 7. Cleanup

After merging:

```bash
# Update local main branch
git checkout main
git pull origin main

# Delete feature branch locally
git branch -d your-feature-branch-name

# Delete remote branch (optional)
git push origin --delete your-feature-branch-name
```

## Branch Naming Conventions

Use descriptive, lowercase branch names:

- `feat/add-user-authentication`
- `fix/login-validation-bug`
- `docs/update-api-reference`
- `refactor/cleanup-old-code`
- `test/add-integration-tests`

## Common Issues and Solutions

### PR Creation Fails

**Error**: "A pull request for branch already exists"

**Solution**: Update existing PR or create new branch:
```bash
# Check existing PRs
gh pr list

# Update existing PR with new commits
git push origin your-branch-name
```

### Authentication Issues

**Error**: "Could not authenticate"

**Solution**: Set up GitHub CLI authentication:
```bash
gh auth login
```

### Merge Conflicts

**Resolution**:
```bash
# Update your branch with main
git checkout main
git pull origin main
git checkout your-feature-branch
git rebase main

# Resolve conflicts in editor
# Then continue rebase
git add resolved-files
git rebase --continue

# Force push updated branch
git push origin your-feature-branch-name --force-with-lease
```

## Automated Checks

Before creating PR, run these checks:

```bash
# Run tests
make test

# Check formatting
make lint

# Verify build
make build

# Check API keys (for this repo)
make verify
```

## Review Checklist

- [ ] **Code Quality**: Code follows project standards
- [ ] **Tests**: New functionality is tested
- [ ] **Documentation**: Docs updated for API changes
- [ ] **Breaking Changes**: Migration path documented
- [ ] **Security**: No sensitive data exposed
- [ ] **Performance**: No performance regressions
- [ ] **Dependencies**: New dependencies justified and secure
