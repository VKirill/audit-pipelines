#!/usr/bin/env bash
# Final gate: validate all phases, check global confidence, citations, generate _meta.json.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_audit_dir
require_cmd jq
require_cmd python3

errors=0

echo "==> finalize.sh — final gate"
echo

# 1. Per-phase validation
phases=()
for f in "$AUDIT_DIR"/[0-9]*.md; do
  base=$(basename "$f")
  phase=$(echo "$base" | grep -oE '^[0-9]+[a-z]?')
  [[ -n "$phase" ]] || continue
  phases+=("$phase")
done
mapfile -t phases < <(printf '%s\n' "${phases[@]}" | sort -u)

for p in "${phases[@]}"; do
  echo "--- phase $p"
  if ! bash "$SCRIPT_DIR/validate_phase.sh" "$p"; then
    errors=$((errors+1))
  fi
  echo
done

# 2. Global confidence/severity rules
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

# 4. Required artefacts
echo "--- required artefacts"
for f in ROADMAP.md _adversary_review.md _known_unknowns.md; do
  if [[ ! -f "$AUDIT_DIR/$f" ]]; then
    c_red "missing $AUDIT_DIR/$f"
    errors=$((errors+1))
  fi
done
# 10a report
shopt -s nullglob
m=("$AUDIT_DIR"/10a_*.md)
shopt -u nullglob
if (( ${#m[@]} == 0 )); then
  c_red "missing audit/10a_*.md"
  errors=$((errors+1))
fi

# Critical → 11 deep-dive required
critical_count=$(jq -c 'select(.severity == "critical")' "$FINDINGS" 2>/dev/null | grep -c . || true)
if (( critical_count > 0 )); then
  if [[ ! -f "$AUDIT_DIR/11_deep_dive.md" ]]; then
    c_red "critical findings present ($critical_count) but 11_deep_dive.md missing"
    errors=$((errors+1))
  fi
fi

echo

# 5. Generate meta
echo "--- generate _meta.json"
if ! python3 "$SCRIPT_DIR/generate_meta_json.py" > /dev/null; then
  c_red "_meta.json generation failed"
  errors=$((errors+1))
else
  ok "_meta.json generated"
fi

if (( errors > 0 )); then
  c_red "FAIL: $errors error(s) — pipeline not complete"
  exit 1
fi

c_green "PASS: pipeline complete"
exit 0
