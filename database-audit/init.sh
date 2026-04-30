#!/usr/bin/env bash
# init.sh — Stage 0 of database-audit v2.
# Single entry point. Bootstraps environment and primes the AI to discover the project.
#
# Usage:
#   bash database-audit/init.sh [--project-root <path>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(pwd)}"
[[ "${1:-}" == "--project-root" ]] && PROJECT_ROOT="$2"

cd "$PROJECT_ROOT"

c_red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
c_green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }

echo "==> database-audit v2 — init"
echo "    project root: $PROJECT_ROOT"
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

# Optional but recommended
command -v yq >/dev/null 2>&1 || c_yellow "yq not installed — manifest YAML edits will need manual care (recommended: install yq)"
python3 -c 'import yaml' 2>/dev/null || { c_red "PyYAML required: pip install pyyaml"; exit 1; }
python3 -c 'import jsonschema' 2>/dev/null || { c_yellow "jsonschema not installed — manifest validation will be weaker (recommended: pip install jsonschema)"; }

# Locate pipeline files
if [[ ! -f "$SCRIPT_DIR/manifest.schema.yml" ]]; then
  c_red "Pipeline files missing. Re-clone or copy database-audit/ to project root."
  exit 1
fi

# Ensure audit dir
AUDIT_DIR="${AUDIT_DIR:-audit}"
mkdir -p "$AUDIT_DIR" "$AUDIT_DIR/evidence" .serena/memories
touch "$AUDIT_DIR/findings.jsonl"

# Already ran?
if [[ -f "database-audit.manifest.yml" ]]; then
  c_yellow "Existing manifest detected at database-audit.manifest.yml"
  echo "Options:"
  echo "  - Keep and run phases:    bash database-audit/run.sh all"
  echo "  - Re-discover (refresh):  bash database-audit/init.sh --refresh"
  echo "  - Edit manifest manually, then run phases"
  exit 0
fi

# Stage the AI prompt
PROMPT_FILE=".audit-init.md"
{
  echo "# Database Audit — Init Phase"
  echo
  echo "Read the master discover prompt and execute it strictly:"
  echo
  echo "**\`$SCRIPT_DIR/prompts/00_discover.md\`**"
  echo
  echo "Project root: \`$PROJECT_ROOT\`"
  echo "Audit dir:    \`$AUDIT_DIR\`"
  echo
  echo "## Output contract"
  echo
  echo "Produce **\`database-audit.manifest.yml\`** at project root, conforming to:"
  echo "- Schema: \`$SCRIPT_DIR/manifest.schema.yml\`"
  echo "- Example: \`$SCRIPT_DIR/manifest.example.yml\`"
  echo
  echo "## Validation"
  echo
  echo "Before reporting completion, run:"
  echo
  echo '```bash'
  echo "python3 $SCRIPT_DIR/validators/validate_manifest.py database-audit.manifest.yml"
  echo '```'
  echo
  echo "exit 0 = manifest is valid. exit ≠ 0 = fix and retry."
  echo
  echo "## After manifest"
  echo
  echo "Once manifest is valid, **stop and report to the user**. Do NOT run phases yet."
  echo "User reviews manifest, then explicitly invokes:"
  echo
  echo '```bash'
  echo "bash database-audit/run.sh all"
  echo '```'
} > "$PROMPT_FILE"

c_green "Init staged."
echo
echo "Next step:"
echo
echo "  1. Open Claude Code in this directory."
echo "  2. Send command:"
echo
echo "     Прочитай $PROMPT_FILE и выполни discover-фазу. Создай database-audit.manifest.yml."
echo
echo "  3. Review the produced database-audit.manifest.yml."
echo "  4. When ready, run: bash database-audit/run.sh all"
echo
