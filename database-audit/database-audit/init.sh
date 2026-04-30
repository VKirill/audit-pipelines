#!/usr/bin/env bash
# init.sh — Stage 0 of database-audit v3.
#
# Usage:
#   bash database-audit/init.sh                          # fresh discover
#   bash database-audit/init.sh --refresh                # update existing manifest
#   bash database-audit/init.sh --project-root <path>    # explicit root

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

echo "==> database-audit v3 — init"
echo "    project root: $PROJECT_ROOT"
[[ "$REFRESH" == "1" ]] && echo "    mode: refresh"
echo

# Pre-flight: required tools
need=()
for cmd in jq python3 rg find git; do
  command -v "$cmd" >/dev/null 2>&1 || need+=("$cmd")
done
if (( ${#need[@]} )); then
  c_red "Missing required commands: ${need[*]}"
  echo "Install: apt install jq python3 ripgrep git"
  exit 1
fi

python3 -c 'import yaml' 2>/dev/null || { c_red "PyYAML required: pip install pyyaml"; exit 1; }
python3 -c 'import jsonschema' 2>/dev/null || c_yellow "jsonschema not installed (recommended: pip install jsonschema)"

[[ -f "$SCRIPT_DIR/manifest.schema.yml" ]] || { c_red "Pipeline files missing"; exit 1; }

AUDIT_DIR="${AUDIT_DIR:-audit}"
mkdir -p "$AUDIT_DIR" "$AUDIT_DIR/evidence" .serena/memories
touch "$AUDIT_DIR/findings.jsonl"

# Refresh mode
if [[ "$REFRESH" == "1" ]]; then
  if [[ ! -f "database-audit.manifest.yml" ]]; then
    c_red "No existing manifest to refresh. Run init without --refresh first."
    exit 1
  fi
  PROMPT_FILE=".audit-refresh.md"
  {
    echo "# Database Audit — Refresh"
    echo
    echo "Read **\`$SCRIPT_DIR/prompts/refresh.md\`** and execute the refresh protocol."
    echo
    echo "Existing manifest: \`database-audit.manifest.yml\`"
    echo "Project root: \`$PROJECT_ROOT\`"
    echo
    echo "Output: updated manifest with refresh_state populated."
    echo
    echo "Validate when done:"
    echo '  python3 '"$SCRIPT_DIR"'/validators/validate_manifest.py database-audit.manifest.yml --strict'
  } > "$PROMPT_FILE"
  c_green "Refresh staged in $PROMPT_FILE"
  exit 0
fi

# Already exists?
if [[ -f "database-audit.manifest.yml" ]]; then
  c_yellow "Existing manifest detected at database-audit.manifest.yml"
  echo "Options:"
  echo "  - Keep and run phases:    bash database-audit/run.sh all"
  echo "  - Refresh:                bash database-audit/init.sh --refresh"
  echo "  - Edit manually then run"
  exit 0
fi

# Stage AI prompt
PROMPT_FILE=".audit-init.md"
{
  echo "# Database Audit — Init Phase (v3)"
  echo
  echo "Read the master discover prompt and follow it strictly:"
  echo
  echo "**\`$SCRIPT_DIR/prompts/00_discover.md\`**"
  echo
  echo "It uses chunked sub-prompts (\`00a..00e\`) for deep analysis of:"
  echo "- Money columns + endpoints (00a)"
  echo "- Transactions + race candidates (00b)"
  echo "- PII + secrets (00c)"
  echo "- N+1 candidates (00d)"
  echo "- Migrations + dangerous DDL (00e)"
  echo
  echo "Project root: \`$PROJECT_ROOT\`"
  echo "Audit dir:    \`$AUDIT_DIR\`"
  echo
  echo "## Output contract"
  echo
  echo "Produce **\`database-audit.manifest.yml\`** at project root, conforming to:"
  echo "- Schema:  \`$SCRIPT_DIR/manifest.schema.yml\`"
  echo "- Example: \`$SCRIPT_DIR/manifest.example.yml\`"
  echo
  echo "## Validation gate"
  echo
  echo "Before reporting completion, follow \`prompts/00z_validate_manifest.md\` —"
  echo "it includes the strict validator + coverage checks."
  echo
  echo "## After manifest"
  echo
  echo "Once manifest is valid, **stop and report to the user**. Do NOT run phases."
  echo
  echo "User reviews manifest, then explicitly runs:"
  echo
  echo '  bash database-audit/run.sh all'
} > "$PROMPT_FILE"

c_green "Init staged."
echo
echo "Next:"
echo "  1. Open Claude Code in this directory"
echo "  2. Send: Прочитай $PROMPT_FILE и выполни discover-фазу. Создай database-audit.manifest.yml."
echo "  3. Review database-audit.manifest.yml"
echo "  4. Run: bash database-audit/run.sh all"
