#!/usr/bin/env bash
# required_evidence_files.sh — print the list of evidence files a phase must produce.
# Usage: ./scripts/required_evidence_files.sh <NN>
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

PHASE="${1:-}"
[[ -n "$PHASE" ]] || { echo "Usage: $0 <NN>" >&2; exit 2; }

required="$(phase_required_evidence "$PHASE")"
if [[ -z "$required" ]]; then
  echo "(no required evidence files defined for phase $PHASE)"
  exit 0
fi
for f in $required; do echo "$f"; done
