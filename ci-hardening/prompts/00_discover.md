# 00 — Discover orchestrator (CI Hardening)

> **Это Stage 0.** Цель — построить полный manifest.yml.

## Шаги

### 1. Project skeleton

```bash
cd "$PROJECT_PATH"

# Languages detection
[ -f package.json ] && langs+=(node)
[ -f pyproject.toml ] || [ -f requirements.txt ] && langs+=(python)
[ -f go.mod ] && langs+=(go)
[ -f Cargo.toml ] && langs+=(rust)
[ -f composer.json ] && langs+=(php)
[ -f Gemfile ] && langs+=(ruby)
[ -f pom.xml ] || [ -f build.gradle ] && langs+=(java)

# Git remote + repo
git remote get-url origin   # github.com:OWNER/REPO.git
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
```

Заполни `project.{root, name, type, languages, package_managers, git_head, git_branch}`.

### 2. GitHub repo metadata

```bash
gh auth status                       # is authenticated?
gh api repos/$OWNER/$REPO            # visibility, default_branch
gh api repos/$OWNER/$REPO --jq '.security_and_analysis'  # GHAS settings
```

Заполни `github.{owner, repo, default_branch, visibility, ghas_enabled, gh_cli_authenticated, api_access}`.

### 3. Workflow files

```bash
ls .github/workflows/*.{yml,yaml} 2>/dev/null
```

Заполни `paths.workflow_files`.

### 4. Sub-prompts

После skeleton — выполни:
- 00a — workflows audit
- 00b — third-party actions inventory
- 00c — secrets + OIDC opportunities
- 00d — branch protection (gh api)
- 00e — security features (Dependabot, scan)

### 5. Validate

```bash
python3 ci-hardening/validators/validate_manifest.py ci-hardening/manifest.yml --strict
```
