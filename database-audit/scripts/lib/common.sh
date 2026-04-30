#!/usr/bin/env bash
# Common library for database-audit scripts.
# Mirrors codebase/v3 patterns.

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

# Минимальные quotas (для M-проекта).
phase_min_findings_M() {
  case "$1" in
    00)  echo 0 ;;
    01)  echo 0 ;;
    02)  echo 5 ;;
    03)  echo 3 ;;
    04)  echo 5 ;;
    05)  echo 3 ;;
    05b) echo 0 ;;  # quota — 0 если фаза не применима, иначе 2 (проверяется отдельно по applicability marker)
    06)  echo 3 ;;
    07)  echo 3 ;;
    08)  echo 2 ;;
    09)  echo 2 ;;
    10)  echo 0 ;;
    10a) echo 0 ;;
    11)  echo 0 ;;
    *)   echo 0 ;;
  esac
}

# Required evidence файлы для каждой фазы.
phase_required_evidence() {
  case "$1" in
    00)  echo "stack_detection.txt" ;;
    01)  echo "schema_summary.json models_list.md migrations_list.md queries_inventory.md" ;;
    02)  echo "normalization_analysis.md types_audit.md karwin_antipatterns.md" ;;
    03)  echo "fk_without_index.md declared_indexes.md index_recommendations.md" ;;
    04)  echo "n_plus_one_suspects.md select_star.md" ;;
    05)  echo "transaction_coverage.md isolation_levels.md race_candidates.md" ;;
    05b) echo "money_columns.md atomic_updates.md idempotency_coverage.md" ;;
    06)  echo "dangerous_ddl.md reversibility_audit.md multi_step_analysis.md" ;;
    07)  echo "pii_classification.md sqli_surface.md secret_scan.txt db_user_privileges.md" ;;
    08)  echo "connection_pool_analysis.md cache_strategy.md" ;;
    09)  echo "monitoring_inventory.md backup_strategy.md dr_readiness.md" ;;
    10)  echo "" ;;  # Roadmap проверяется отдельно
    10a) echo "" ;;
    11)  echo "" ;;  # проверяется через 11_deep_dive.md содержание
    *)   echo "" ;;
  esac
}

# Стоп-слова в отчётах фаз. Если в audit/NN_*.md встречается одно из этих слов — это nullification фазы.
stop_words() {
  cat <<'EOF'
допустимо
приемлемо
можно считать допустимым
не критично, оставим
EOF
}

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

project_size() {
  local mem=".serena/memories/db_audit_phase_00.md"
  [[ -f "$mem" ]] || mem=".serena/memories/db_audit_phase_00"
  if [[ -f "$mem" ]]; then
    local sz
    sz=$(grep -E '^\s*-\s*size:\s*' "$mem" 2>/dev/null | head -1 | sed -E 's/.*size:\s*([A-Z]+).*/\1/' | tr -d '[:space:]')
    case "$sz" in XS|S|M|L|XL) echo "$sz"; return ;; esac
  fi
  echo "M"
}

scale_quota_by_size() {
  local base="$1" size="$2"
  case "$size" in
    XS) python3 -c "print(max(1 if $base > 0 else 0, $base // 3))" ;;
    S)  python3 -c "print(max(1 if $base > 0 else 0, $base // 2))" ;;
    M)  echo "$base" ;;
    L)  python3 -c "print($base * 2)" ;;
    XL) python3 -c "print($base * 3)" ;;
    *)  echo "$base" ;;
  esac
}

# Проверка mode (live | static)
audit_mode() {
  local mem=".serena/memories/db_audit_phase_00.md"
  [[ -f "$mem" ]] || mem=".serena/memories/db_audit_phase_00"
  if [[ -f "$mem" ]]; then
    grep -E '^\s*-\s*mode:\s*' "$mem" 2>/dev/null | head -1 | sed -E 's/.*mode:\s*(\w+).*/\1/' | tr -d '[:space:]'
  else
    echo "static"
  fi
}
