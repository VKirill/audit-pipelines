#!/usr/bin/env bash
# Common helpers for audit_pipeline v3 scripts.
# Sourced by validate_phase.sh, finalize.sh, etc.
# Usage: source "$(dirname "$0")/lib/common.sh"
#
# Convention:
#   - All scripts run from project root (where audit/ lives).
#   - AUDIT_DIR overridable via env (default: ./audit).
#   - Exit 0 = ok, exit 1 = hard fail, exit 2 = misuse.

set -euo pipefail

AUDIT_DIR="${AUDIT_DIR:-audit}"
FINDINGS="${AUDIT_DIR}/findings.jsonl"
EVIDENCE_DIR="${AUDIT_DIR}/evidence"

c_red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
c_green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }
c_dim()    { printf '\033[2m%s\033[0m\n' "$*" >&2; }

die()  { c_red "FAIL: $*"; exit 1; }
warn() { c_yellow "WARN: $*"; }
ok()   { c_green "OK:   $*"; }
info() { c_dim   "      $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

require_audit_dir() {
  [[ -d "$AUDIT_DIR" ]] || die "$AUDIT_DIR/ not found. Run from project root."
}

# Phase quotas for size M (10k-100k LOC). Scaled in validate_phase.sh by SIZE.
phase_min_findings_M() {
  case "$1" in
    00) echo 0 ;;
    01) echo 0 ;;
    02|02b) echo 5 ;;
    03) echo 3 ;;
    04) echo 8 ;;
    05) echo 5 ;;
    06|06b) echo 5 ;;
    07) echo 3 ;;
    08) echo 3 ;;
    09) echo 3 ;;
    10|10a) echo 0 ;;
    11) echo 0 ;;
    *) echo 0 ;;
  esac
}

# Required evidence files per phase. Whitespace-separated names within evidence/<NN>_*/.
phase_required_evidence() {
  case "$1" in
    02)  echo "cluster_matrix.md cluster_graph.mmd central_symbols.md" ;;
    02b) echo "trust_map.md sources_sinks.md" ;;
    03)  echo "dep_audit.txt manifest_summary.md" ;;
    04)  echo "large_functions.md todo_grep.txt" ;;
    05)  echo "catch_blocks.txt external_calls_timeouts.md" ;;
    06)  echo "owasp_checklist.md auth_coverage.md secret_scan.txt" ;;
    06b) echo "money_invariants.md state_mutations.md" ;;
    07)  echo "test_inventory.md central_symbols_coverage.md" ;;
    08)  echo "ci_workflows.txt logging_analysis.md health_endpoints.md" ;;
    09)  echo "hotpath_analysis.md n_plus_one_suspects.md" ;;
    10)  echo "epic_dag.mmd findings_by_severity.md" ;;
    *)   echo "" ;;
  esac
}

# Mandatory h2 sections in audit/NN_*.md (TEMPLATES.md §2).
required_sections() {
  cat <<'EOF'
## 1. Цель фазы
## 2. Что проверено
## 3. Ключевые наблюдения
## 4. Находки
## 5. Неполные проверки
## 6. Контрольные вопросы
## 7. Следующая фаза
EOF
}

# Resolve the report markdown file for a phase (audit/NN_*.md).
phase_report_file() {
  local n="$1"
  shopt -s nullglob
  local matches=("$AUDIT_DIR"/"${n}"_*.md)
  shopt -u nullglob
  if (( ${#matches[@]} == 0 )); then
    echo ""
  else
    echo "${matches[0]}"
  fi
}

# Resolve the evidence directory for a phase (audit/evidence/NN_*/).
phase_evidence_dir() {
  local n="$1"
  shopt -s nullglob
  local matches=("$EVIDENCE_DIR"/"${n}"_*)
  shopt -u nullglob
  if (( ${#matches[@]} == 0 )); then
    echo ""
  else
    echo "${matches[0]}"
  fi
}

# Project size from .serena/memories/audit_phase_00 if available, else "M".
project_size() {
  local mem=".serena/memories/audit_phase_00.md"
  [[ -f "$mem" ]] || mem=".serena/memories/audit_phase_00"
  if [[ -f "$mem" ]]; then
    local sz
    sz=$(grep -E '^\s*-\s*size:\s*' "$mem" 2>/dev/null | head -1 | sed -E 's/.*size:\s*([A-Z]+).*/\1/' | tr -d '[:space:]')
    case "$sz" in XS|S|M|L|XL) echo "$sz"; return ;; esac
  fi
  echo "M"
}

# Scale a baseline-M quota by project size.
scale_quota_by_size() {
  local base="$1" size="$2"
  case "$size" in
    XS) python3 -c "print(max(1, $base // 3))" ;;
    S)  python3 -c "print(max(1, $base // 2))" ;;
    M)  echo "$base" ;;
    L)  python3 -c "print($base * 2)" ;;
    XL) python3 -c "print($base * 3)" ;;
    *)  echo "$base" ;;
  esac
}
