#!/usr/bin/env bash
# init.sh — Stage 0 of ci-hardening pipeline.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT=""
REFRESH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --refresh) REFRESH=1; shift ;;
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
    *) PROJECT_ROOT="$1"; shift ;;
  esac
done

PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
cd "$PROJECT_ROOT"

c_red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
c_green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }

echo "==> ci-hardening v2 — init"
echo "    project root: $PROJECT_ROOT"

# Pre-flight
need=()
for cmd in jq python3 git; do
  command -v "$cmd" >/dev/null 2>&1 || need+=("$cmd")
done
if (( ${#need[@]} )); then
  c_red "Missing required commands: ${need[*]}"
  exit 1
fi

python3 -c 'import yaml' 2>/dev/null || { c_red "PyYAML required: pip install pyyaml"; exit 1; }

# Pipeline files check
[[ -f "$SCRIPT_DIR/manifest.schema.yml" ]] || { c_red "Pipeline files missing"; exit 1; }

AUDIT_DIR="${AUDIT_DIR:-$SCRIPT_DIR/results}"
mkdir -p "$AUDIT_DIR" "$AUDIT_DIR/evidence" "$SCRIPT_DIR/_staging" .serena/memories 2>/dev/null || true
touch "$AUDIT_DIR/findings.jsonl"

# gh CLI auth check
GH_AUTH=false
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    GH_AUTH=true
  else
    c_yellow "gh CLI not authenticated. Run: gh auth login"
  fi
else
  c_yellow "gh CLI not installed. Branch protection / settings audit will be limited."
fi

# Detect repo
GIT_REMOTE=$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null || echo "")
OWNER=""
REPO=""
if [[ "$GIT_REMOTE" =~ github\.com[:/]([^/]+)/([^/.]+?)(\.git)?$ ]]; then
  OWNER="${BASH_REMATCH[1]}"
  REPO="${BASH_REMATCH[2]}"
fi

# Refresh mode
if [[ "$REFRESH" == "1" ]]; then
  if [[ ! -f "$SCRIPT_DIR/manifest.yml" ]]; then
    c_red "No existing manifest. Run init.sh without --refresh first."; exit 1
  fi
  PROMPT_FILE="$SCRIPT_DIR/_staging/refresh.md"
  cat > "$PROMPT_FILE" <<EOF
# Refresh CI Hardening Audit

Read prompts/refresh.md and update manifest.yml for changed workflows.

Project: $PROJECT_ROOT
Repo: $OWNER/$REPO
EOF
  c_green "Refresh staged in $PROMPT_FILE"
  exit 0
fi

# Already exists?
if [[ -f "$SCRIPT_DIR/manifest.yml" ]]; then
  c_yellow "Existing manifest at $SCRIPT_DIR/manifest.yml"
  echo "Options:"
  echo "  - Run phases:    bash ci-hardening/run.sh all"
  echo "  - Refresh:       bash ci-hardening/init.sh --refresh"
  echo "  - Reset:         bash ci-hardening/run.sh reset"
  exit 0
fi

# Stage AI prompt
PROMPT_FILE="$SCRIPT_DIR/_staging/init.md"
cat > "$PROMPT_FILE" <<EOF
# CI Hardening Audit — Init Phase

Read the master discover prompt and follow strictly:

**\`$SCRIPT_DIR/prompts/00_discover.md\`**

Sub-prompts (chunked):
- 00a — workflows audit
- 00b — third-party actions inventory
- 00c — secrets + OIDC
- 00d — branch protection (gh api)
- 00e — security features

## Project context

- PROJECT_PATH: \`$PROJECT_ROOT\`
- Git remote: \`$GIT_REMOTE\`
- Detected repo: \`$OWNER/$REPO\`
- gh CLI authenticated: \`$GH_AUTH\`

## Output

Produce **\`$SCRIPT_DIR/manifest.yml\`** conforming to:
- Schema:  \`$SCRIPT_DIR/manifest.schema.yml\`
- Example: \`$SCRIPT_DIR/manifest.example.yml\`

## Validation

Before reporting completion:

\`\`\`bash
python3 $SCRIPT_DIR/validators/validate_manifest.py $SCRIPT_DIR/manifest.yml --strict
\`\`\`

## After manifest

Stop and notify user. They invoke:

\`\`\`bash
bash ci-hardening/run.sh all
\`\`\`
EOF

c_green "Init staged."
echo
echo "Next:"
echo "  1. Open Claude Code in this directory"
echo "  2. Send: Прочитай ci-hardening/_staging/init.md и выполни discover-фазу. Создай ci-hardening/manifest.yml."
echo "  3. Review ci-hardening/manifest.yml"
echo "  4. Run: bash ci-hardening/run.sh all"
echo
echo "All audit artefacts will live in: ci-hardening/results/, ci-hardening/manifest.yml, ci-hardening/_staging/"
