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

# Python deps with minimum-version checks
python3 -c "import yaml; assert tuple(int(x) for x in yaml.__version__.split('.')[:2]) >= (6,0), yaml.__version__" 2>/dev/null     || { c_red "PyYAML >= 6.0 required (current: $(python3 -c 'import yaml; print(yaml.__version__)' 2>/dev/null || echo 'not installed')). Install: pip install -r database-audit/requirements.txt"; exit 1; }

python3 -c "
import sys
try:
    from importlib.metadata import version
    v = version('jsonschema')
except Exception:
    import jsonschema
    v = jsonschema.__version__
maj, mn, *_ = (int(x) for x in v.split('.')[:2] + [0]*2)
if (maj, mn) < (4, 23):
    print(f'WARN: jsonschema {v} < 4.23 (CVE-2023-22102). Upgrade: pip install --upgrade -r database-audit/requirements.txt', file=sys.stderr)
    sys.exit(2)
" 2>/dev/null
case $? in
    0) ;;  # ok
    1) c_yellow "jsonschema not installed (validator will skip schema check). Install: pip install -r database-audit/requirements.txt" ;;
    2) c_yellow "jsonschema below 4.23 — security CVE present. Recommended: pip install --upgrade -r database-audit/requirements.txt" ;;
esac

# CLI tool version check (warn-only)
ripgrep_version=$(rg --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
if [[ -n "$ripgrep_version" ]] && [[ $(echo "$ripgrep_version 13.0" | awk '{print ($1 < $2)}') == "1" ]]; then
    c_yellow "ripgrep $ripgrep_version < 13.0 — some glob patterns may not work. Recommended: 14.1+"
fi

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
