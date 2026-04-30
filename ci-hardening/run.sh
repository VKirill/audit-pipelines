#!/usr/bin/env bash
# run.sh — phase dispatcher for ci-hardening v2.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/env.sh"

require_manifest() {
  [[ -f "$MANIFEST" ]] || { c_red "Manifest not found: $MANIFEST. Run init.sh first."; exit 1; }
}

validate_manifest() {
  c_dim "validating manifest..."
  python3 "$SCRIPT_DIR/validators/validate_manifest.py" "$MANIFEST" || {
    c_red "manifest invalid"; exit 1
  }
}

list_detectors_for_phase() {
  local phase="$1"
  python3 -c "
import yaml, sys
m = yaml.safe_load(open('$MANIFEST'))
plan = m.get('phase_plan', {}).get('$phase', {}) or {}
if plan.get('skip_reason'): print('SKIP:'+plan['skip_reason']); sys.exit(0)
for d in plan.get('detectors', []): print(d)
"
}

run_detector() {
  local name="$1" phase="${2:-}"
  local script="$SCRIPT_DIR/detectors/${name}.py"
  if [[ -f "$script" ]]; then
    c_dim "  detector: $name"
    AUDIT_DIR="$AUDIT_DIR" PROJECT_ROOT="$PROJECT_ROOT" PIPELINE_DIR="$PIPELINE_DIR" \
      python3 "$script" --manifest "$MANIFEST" ${phase:+--phase "$phase"} || c_yellow "  $name returned non-zero"
  else
    c_yellow "  detector $name NOT FOUND"
  fi
}

phase_run() {
  local phase="$1"
  echo
  echo "==> phase $phase"
  local out; out="$(list_detectors_for_phase "$phase")"
  if [[ "$out" == SKIP:* ]]; then c_yellow "phase $phase skipped: ${out#SKIP:}"; return 0; fi
  if [[ -n "$out" ]]; then
    while read -r d; do
      [[ -z "$d" ]] && continue
      run_detector "$d" "$phase"
    done <<< "$out"
  fi
  bash "$SCRIPT_DIR/validators/validate_phase.sh" "$phase" || { c_red "phase $phase: validation failed"; return 1; }
  c_green "phase $phase: ok"
}

cmd="${1:-help}"
case "$cmd" in
  all)
    require_manifest
    validate_manifest
    for phase in 00 01 02 03 04 05 06 07 08 09 09a 10; do
      phase_run "$phase" || c_yellow "phase $phase had errors"
    done
    bash "$SCRIPT_DIR/validators/finalize.sh"
    ;;
  phase)
    [[ -n "${2:-}" ]] || { echo "Usage: run.sh phase <NN>"; exit 2; }
    require_manifest; validate_manifest
    phase_run "$2"
    ;;
  detector)
    [[ -n "${2:-}" ]] || { echo "Usage: run.sh detector <name> [phase]"; exit 2; }
    require_manifest
    run_detector "$2" "${3:-}"
    ;;
  validate)
    require_manifest; validate_manifest ;;
  finalize)
    require_manifest
    bash "$SCRIPT_DIR/validators/finalize.sh" ;;
  reset)
    echo "==> Removing manifest, _staging/, results/ — pipeline code preserved"
    rm -rf "$SCRIPT_DIR/results" "$SCRIPT_DIR/_staging" "$SCRIPT_DIR/manifest.yml"
    c_green "Reset done. Run init.sh to start fresh."
    ;;
  *)
    cat <<EOF
ci-hardening v2 — phase dispatcher

Usage:
  bash ci-hardening/run.sh all
  bash ci-hardening/run.sh phase <NN>
  bash ci-hardening/run.sh detector <name> [phase]
  bash ci-hardening/run.sh validate
  bash ci-hardening/run.sh finalize
  bash ci-hardening/run.sh reset

Run init.sh first: bash ci-hardening/init.sh
EOF
    ;;
esac
