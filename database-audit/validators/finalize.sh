#!/usr/bin/env bash
# Final gate. Reads AUDIT_DIR/MANIFEST from env (set by run.sh).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PIPELINE_DIR/lib/env.sh"

require_cmd jq
require_cmd python3

errors=0
echo "==> finalize.sh — final gate  audit_dir=$AUDIT_DIR"
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
  bash "$SCRIPT_DIR/validate_phase.sh" "$p" || errors=$((errors+1))
  echo
done

# 2. Global confidence
echo "--- global confidence"
AUDIT_DIR="$AUDIT_DIR" python3 "$SCRIPT_DIR/validate_confidence.py" || errors=$((errors+1))
echo

# 3. Citations
echo "--- evidence citations"
AUDIT_DIR="$AUDIT_DIR" PROJECT_ROOT="$PROJECT_ROOT" python3 "$SCRIPT_DIR/check_evidence_citations.py" || errors=$((errors+1))
echo

# 4. Required artefacts
echo "--- required artefacts"
for f in ROADMAP.md _adversary_review.md _known_unknowns.md; do
  [[ -f "$AUDIT_DIR/$f" ]] || { c_red "missing $AUDIT_DIR/$f"; errors=$((errors+1)); }
done
shopt -s nullglob
m=("$AUDIT_DIR"/10a_*.md)
shopt -u nullglob
(( ${#m[@]} == 0 )) && { c_red "missing $AUDIT_DIR/10a_*.md"; errors=$((errors+1)); }

critical_count=$(jq -c 'select(.severity == "critical")' "$FINDINGS" 2>/dev/null | grep -c . || true)
if (( critical_count > 0 )) && [[ ! -f "$AUDIT_DIR/11_deep_dive.md" ]]; then
  c_red "critical findings present ($critical_count) but 11_deep_dive.md missing"
  errors=$((errors+1))
fi
echo

# 5. Generate _meta.json
echo "--- generate _meta.json"
AUDIT_DIR="$AUDIT_DIR" MANIFEST="$MANIFEST" python3 "$SCRIPT_DIR/generate_meta_json.py" > /dev/null \
  && ok "_meta.json generated" \
  || { c_red "_meta.json failed"; errors=$((errors+1)); }

if (( errors > 0 )); then
  c_red "FAIL: $errors error(s) — pipeline not complete"
  exit 1
fi

c_green "PASS: pipeline complete"
exit 0
