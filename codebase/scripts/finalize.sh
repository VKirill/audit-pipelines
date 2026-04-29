#!/usr/bin/env bash
# finalize.sh — final hard gate before declaring audit complete.
#
# Steps:
#   1. validate_phase.sh for every phase that has a report
#   2. validate_confidence.py (global distribution)
#   3. check_evidence_citations.py (no broken file:line refs)
#   4. mandatory artefacts present (ROADMAP.md, _adversary_review.md,
#      _known_unknowns.md, 10a_self_audit report)
#   5. generate_meta_json.py
#
# Exit 0 = pipeline complete; exit 1 = at least one gate failed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

require_audit_dir
require_cmd jq
require_cmd python3

errors=0

echo "==> finalize.sh — final v3 gate"
echo

# 1. Per-phase validators
phases=()
for f in "$AUDIT_DIR"/[0-9]*.md; do
  base=$(basename "$f")
  phase=$(echo "$base" | grep -oE '^[0-9]+[a-z]?')
  [[ -n "$phase" ]] || continue
  phases+=("$phase")
done
# Deduplicate
mapfile -t phases < <(printf '%s\n' "${phases[@]}" | sort -u)

for p in "${phases[@]}"; do
  echo "--- phase $p"
  if ! bash "$SCRIPT_DIR/validate_phase.sh" "$p"; then
    errors=$((errors+1))
  fi
  echo
done

# 2. Confidence distribution
echo "--- global confidence"
if ! python3 "$SCRIPT_DIR/validate_confidence.py"; then
  errors=$((errors+1))
fi
echo

# 3. Evidence citations
echo "--- evidence citations"
if ! python3 "$SCRIPT_DIR/check_evidence_citations.py" --root .; then
  errors=$((errors+1))
fi
echo

# 4. Mandatory final artefacts
echo "--- final artefacts"
required_files=(
  "$AUDIT_DIR/ROADMAP.md"
  "$AUDIT_DIR/_adversary_review.md"
  "$AUDIT_DIR/_known_unknowns.md"
)
for f in "${required_files[@]}"; do
  if [[ -f "$f" ]]; then
    ok "$f present"
  else
    c_red "missing: $f"
    errors=$((errors+1))
  fi
done

# Self-audit phase report
if compgen -G "$AUDIT_DIR/10a_*.md" > /dev/null; then
  ok "self-audit phase report present"
else
  c_red "missing: $AUDIT_DIR/10a_self_audit.md (Phase 10a is mandatory in v3)"
  errors=$((errors+1))
fi

# critical findings → require phase 11 deep-dive report
crit_count=$(jq -r 'select(.severity=="critical")' "$FINDINGS" 2>/dev/null | grep -c '"id"' || true)
if (( crit_count > 0 )); then
  if compgen -G "$AUDIT_DIR/11_*.md" > /dev/null; then
    ok "Phase 11 deep-dive present (required: $crit_count critical findings)"
  else
    c_red "missing: $AUDIT_DIR/11_deep_dive.md — REQUIRED in v3 when critical findings exist ($crit_count)"
    errors=$((errors+1))
  fi
fi

# 5. _meta.json
echo
echo "--- generate _meta.json"
if python3 "$SCRIPT_DIR/generate_meta_json.py"; then
  ok "_meta.json written"
else
  c_red "_meta.json generation failed"
  errors=$((errors+1))
fi

echo
if (( errors > 0 )); then
  c_red "finalize.sh: $errors gate(s) failed — audit NOT complete"
  exit 1
fi
c_green "finalize.sh: ALL GATES PASSED — audit v3 complete"
exit 0
