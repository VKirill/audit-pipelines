#!/usr/bin/env bash
# Print required evidence files for given phase number.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

PHASE="${1:-}"
[[ -n "$PHASE" ]] || { echo "Usage: $0 <NN>" >&2; exit 2; }

required="$(phase_required_evidence "$PHASE")"
if [[ -z "$required" ]]; then
  echo "(no required evidence files defined for phase $PHASE)"
  exit 0
fi
for f in $required; do echo "$f"; done
