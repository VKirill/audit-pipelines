#!/usr/bin/env bash
# Common environment loader. Sourced by run.sh, validators, detectors.
# Honors env-var overrides; sets sensible defaults.

set -euo pipefail

export PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
export AUDIT_DIR="${AUDIT_DIR:-$PROJECT_ROOT/audit}"
export MANIFEST="${MANIFEST:-$PROJECT_ROOT/database-audit.manifest.yml}"
export FINDINGS="${FINDINGS:-$AUDIT_DIR/findings.jsonl}"
export EVIDENCE_DIR="${EVIDENCE_DIR:-$AUDIT_DIR/evidence}"

mkdir -p "$AUDIT_DIR" "$EVIDENCE_DIR"
[[ -f "$FINDINGS" ]] || touch "$FINDINGS"

# Mirror common color helpers (kept compatible with old scripts/lib/common.sh)
c_red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
c_green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }
c_dim()    { printf '\033[2m%s\033[0m\n' "$*" >&2; }

die()  { c_red "FAIL: $*"; exit 1; }
warn() { c_yellow "WARN: $*"; }
ok()   { c_green "OK:   $*"; }
info() { c_dim   "      $*"; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

phase_min_findings_M() {
  case "$1" in
    00)  echo 0 ;;
    01)  echo 0 ;;
    02)  echo 5 ;;
    03)  echo 3 ;;
    04)  echo 5 ;;
    05)  echo 3 ;;
    05b) echo 0 ;;
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

phase_required_evidence() {
  case "$1" in
    00)  echo "stack_detection.txt" ;;
    01)  echo "schema_summary.json models_list.md migrations_list.md queries_inventory.md" ;;
    02)  echo "money_floats.md naming_inconsistency.md json_overuse.md" ;;
    03)  echo "fk_without_index.md declared_indexes.md" ;;
    04)  echo "n_plus_one_suspects.md select_star.md" ;;
    05)  echo "transaction_coverage.md isolation_levels.md race_candidates.md" ;;
    05b) echo "money_columns.md atomic_updates.md idempotency_coverage.md" ;;
    06)  echo "dangerous_ddl.md reversibility_audit.md" ;;
    07)  echo "pii_classification.md sqli_surface.md secret_scan.txt" ;;
    08)  echo "pool_settings.md cache_strategy.md" ;;
    09)  echo "monitoring_inventory.md backup_strategy.md" ;;
    10)  echo "" ;;
    10a) echo "" ;;
    11)  echo "" ;;
    *)   echo "" ;;
  esac
}

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
  (( ${#matches[@]} > 0 )) && echo "${matches[0]}" || echo ""
}

phase_evidence_dir() {
  local n="$1"
  shopt -s nullglob
  local matches=("$EVIDENCE_DIR"/"${n}"_*)
  shopt -u nullglob
  (( ${#matches[@]} > 0 )) && echo "${matches[0]}" || echo ""
}

project_size() {
  python3 -c "
import yaml, sys
try:
    m = yaml.safe_load(open('$MANIFEST'))
    print(m.get('project',{}).get('size','M'))
except Exception:
    print('M')
" 2>/dev/null || echo M
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

audit_mode() {
  python3 -c "
import yaml
try:
    m = yaml.safe_load(open('$MANIFEST'))
    print(m.get('mode',{}).get('type','static'))
except Exception:
    print('static')
" 2>/dev/null || echo static
}
