#!/usr/bin/env bash
# run.sh — Stage 1..N dispatcher for database-audit v2.
#
# Usage:
#   bash database-audit/run.sh all                # all phases + finalize
#   bash database-audit/run.sh phase 02           # single phase
#   bash database-audit/run.sh detector find_money_floats  # single detector
#   bash database-audit/run.sh validate           # only validators
#   bash database-audit/run.sh finalize           # only final gate

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/env.sh"

c_red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
c_yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
c_green()  { printf '\033[32m%s\033[0m\n' "$*" >&2; }
c_dim()    { printf '\033[2m%s\033[0m\n' "$*" >&2; }

require_manifest() {
  if [[ ! -f "$MANIFEST" ]]; then
    c_red "Manifest not found: $MANIFEST"
    echo "Run init.sh first:  bash database-audit/init.sh"
    exit 1
  fi
}

validate_manifest() {
  c_dim "validating manifest..."
  python3 "$SCRIPT_DIR/validators/validate_manifest.py" "$MANIFEST" || {
    c_red "manifest invalid — fix and retry"
    exit 1
  }
}

list_detectors_for_phase() {
  local phase="$1"
  python3 -c "
import yaml, sys
m = yaml.safe_load(open('$MANIFEST'))
plan = m.get('phase_plan', {}).get('$phase', {})
if plan.get('skip_reason'):
    print('SKIP:' + plan['skip_reason'])
    sys.exit(0)
for d in plan.get('detectors', []):
    print(d)
"
}

run_detector() {
  local name="$1"
  local phase="${2:-}"

  local script_py="$SCRIPT_DIR/detectors/${name}.py"
  local script_sh="$SCRIPT_DIR/detectors/${name}.sh"

  if [[ -f "$script_py" ]]; then
    c_dim "  detector: $name (py)"
    AUDIT_DIR="$AUDIT_DIR" PROJECT_ROOT="$PROJECT_ROOT" \
      python3 "$script_py" --manifest "$MANIFEST" ${phase:+--phase "$phase"} || {
      c_yellow "  detector $name returned non-zero (continuing)"
    }
  elif [[ -f "$script_sh" ]]; then
    c_dim "  detector: $name (sh)"
    AUDIT_DIR="$AUDIT_DIR" PROJECT_ROOT="$PROJECT_ROOT" MANIFEST="$MANIFEST" \
      bash "$script_sh" "$phase" || {
      c_yellow "  detector $name returned non-zero (continuing)"
    }
  else
    c_yellow "  detector $name NOT FOUND (looked at $script_py and $script_sh)"
  fi
}

phase_run() {
  local phase="$1"
  echo
  echo "==> phase $phase"

  local out
  out="$(list_detectors_for_phase "$phase")"

  if [[ "$out" == SKIP:* ]]; then
    c_yellow "phase $phase skipped: ${out#SKIP:}"
    # Record skip reason in audit/<phase>_*.md if not present
    return 0
  fi

  if [[ -z "$out" ]]; then
    c_dim "(no detectors registered for phase $phase)"
  else
    while read -r d; do
      [[ -z "$d" ]] && continue
      run_detector "$d" "$phase"
    done <<< "$out"
  fi

  # Validate phase
  bash "$SCRIPT_DIR/validators/validate_phase.sh" "$phase" || {
    c_red "phase $phase: validation failed"
    return 1
  }
  c_green "phase $phase: ok"
}

cmd="${1:-help}"

case "$cmd" in
  all)
    require_manifest
    validate_manifest
    for phase in 00 01 02 03 04 05 05b 06 07 08 09 10 10a 11; do
      phase_run "$phase" || c_yellow "phase $phase had errors — review and continue"
    done
    bash "$SCRIPT_DIR/validators/finalize.sh"
    ;;

  phase)
    [[ -n "${2:-}" ]] || { echo "Usage: run.sh phase <NN>"; exit 2; }
    require_manifest
    validate_manifest
    phase_run "$2"
    ;;

  detector)
    [[ -n "${2:-}" ]] || { echo "Usage: run.sh detector <name> [phase]"; exit 2; }
    require_manifest
    run_detector "$2" "${3:-}"
    ;;

  validate)
    require_manifest
    validate_manifest
    ;;

  finalize)
    require_manifest
    bash "$SCRIPT_DIR/validators/finalize.sh"
    ;;

  *)
    cat <<EOF
database-audit v2 — phase dispatcher

Usage:
  bash database-audit/run.sh all
  bash database-audit/run.sh phase <NN>
  bash database-audit/run.sh detector <name> [phase]
  bash database-audit/run.sh validate
  bash database-audit/run.sh finalize

Environment:
  AUDIT_DIR   default 'audit'
  MANIFEST    default 'database-audit.manifest.yml'

Run init.sh first:
  bash database-audit/init.sh
EOF
    ;;
esac
