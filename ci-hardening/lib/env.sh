#!/usr/bin/env bash
set -euo pipefail
export PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
export PIPELINE_DIR="${PIPELINE_DIR:-$PROJECT_ROOT/ci-hardening}"
export AUDIT_DIR="${AUDIT_DIR:-$PIPELINE_DIR/results}"
export MANIFEST="${MANIFEST:-$PIPELINE_DIR/manifest.yml}"
export STAGING_DIR="${STAGING_DIR:-$PIPELINE_DIR/_staging}"
export FINDINGS="${FINDINGS:-$AUDIT_DIR/findings.jsonl}"
export EVIDENCE_DIR="${EVIDENCE_DIR:-$AUDIT_DIR/evidence}"
mkdir -p "$AUDIT_DIR" "$EVIDENCE_DIR" "$STAGING_DIR"
[[ -f "$FINDINGS" ]] || touch "$FINDINGS"
c_red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
c_green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }
c_dim()    { printf '\033[2m%s\033[0m\n' "$*" >&2; }
die() { c_red "FAIL: $*"; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required: $1"; }
phase_min_findings_M() {
  case "$1" in
    01) echo 0 ;; 02) echo 3 ;; 03) echo 3 ;; 04) echo 2 ;;
    05) echo 1 ;; 06) echo 2 ;; 07) echo 2 ;; 08) echo 2 ;;
    09) echo 0 ;; 09a) echo 0 ;; 10) echo 0 ;; *) echo 0 ;;
  esac
}
phase_required_evidence() {
  case "$1" in
    01) echo "workflows_inventory.md actions_list.md" ;;
    02) echo "unpinned_actions.md outdated_actions.md" ;;
    03) echo "permissions_audit.md" ;;
    04) echo "secrets_audit.md oidc_opportunities.md" ;;
    05) echo "branch_protection.md" ;;
    06) echo "dependabot_config.md dangerous_triggers.md" ;;
    07) echo "codeql_setup.md security_features.md" ;;
    08) echo "codeowners_check.md security_md_check.md" ;;
    *) echo "" ;;
  esac
}
stop_words() { cat <<'EOF'
допустимо
приемлемо
EOF
}
phase_report_file() {
  local n="$1"
  shopt -s nullglob; local m=("$AUDIT_DIR"/"${n}"_*.md); shopt -u nullglob
  (( ${#m[@]} > 0 )) && echo "${m[0]}" || echo ""
}
phase_evidence_dir() {
  local n="$1"
  shopt -s nullglob; local m=("$EVIDENCE_DIR"/"${n}"_*); shopt -u nullglob
  (( ${#m[@]} > 0 )) && echo "${m[0]}" || echo ""
}
project_size() { echo "M"; }
scale_quota_by_size() { echo "$1"; }
audit_mode() {
  python3 -c "
import yaml
try:
    m = yaml.safe_load(open('$MANIFEST'))
    print(m.get('mode',{}).get('type','static'))
except: print('static')
" 2>/dev/null || echo static
}
