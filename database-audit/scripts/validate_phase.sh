#!/usr/bin/env bash
# Validate that phase NN passed its exit gate.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_cmd jq
require_cmd python3
require_audit_dir

PHASE="${1:-}"
[[ -n "$PHASE" ]] || { echo "Usage: $0 <NN>" >&2; exit 2; }

echo "==> validate_phase.sh phase=$PHASE"

errors=0

# 1. findings.jsonl exists and is valid
if [[ ! -f "$FINDINGS" ]]; then
  die "$FINDINGS missing"
fi

if ! python3 -c "
import json,sys
with open('$FINDINGS') as f:
    for i,line in enumerate(f,1):
        line=line.strip()
        if not line: continue
        try: json.loads(line)
        except Exception as e:
            print(f'line {i}: {e}'); sys.exit(1)
"; then
  c_red "findings.jsonl contains invalid JSON lines"
  errors=$((errors+1))
fi

# 2. Findings count for this phase
phase_findings_json="$(jq -c "select(.phase == \"$PHASE\" or (.phase|tostring) == \"$PHASE\")" "$FINDINGS" 2>/dev/null || true)"
phase_count=$(printf '%s\n' "$phase_findings_json" | grep -c . || true)
info "findings of phase $PHASE: $phase_count"

size="$(project_size)"
base_quota="$(phase_min_findings_M "$PHASE")"
scaled_quota="$(scale_quota_by_size "$base_quota" "$size")"
info "size=$size base_quota=$base_quota scaled_quota=$scaled_quota"

if (( phase_count < scaled_quota )); then
  c_red "findings count ($phase_count) < quota ($scaled_quota) for phase $PHASE"
  errors=$((errors+1))
fi

# 3. confidence_rationale on every high
high_without_rationale=$(jq -c "select((.phase == \"$PHASE\" or (.phase|tostring) == \"$PHASE\") and .confidence == \"high\" and ((.confidence_rationale // \"\") | length) < 40)" "$FINDINGS" 2>/dev/null || true)
if [[ -n "$high_without_rationale" ]]; then
  c_red "high-confidence findings without confidence_rationale (>=40 chars):"
  echo "$high_without_rationale"
  errors=$((errors+1))
fi

# 4. exploit_proof on every critical
critical_without_proof=$(jq -c "select((.phase == \"$PHASE\" or (.phase|tostring) == \"$PHASE\") and .severity == \"critical\" and ((.exploit_proof // \"\") | length) < 40)" "$FINDINGS" 2>/dev/null || true)
if [[ -n "$critical_without_proof" ]]; then
  c_red "critical findings without exploit_proof (>=40 chars):"
  echo "$critical_without_proof"
  errors=$((errors+1))
fi

# 5. location.lines is non-empty for high
high_no_lines=$(jq -c "select((.phase == \"$PHASE\" or (.phase|tostring) == \"$PHASE\") and .confidence == \"high\" and ((.location.lines // \"\") | length) == 0)" "$FINDINGS" 2>/dev/null || true)
if [[ -n "$high_no_lines" ]]; then
  c_red "high-confidence findings with empty location.lines:"
  echo "$high_no_lines"
  errors=$((errors+1))
fi

# 6. required evidence files present
ev_dir="$(phase_evidence_dir "$PHASE")"
required="$(phase_required_evidence "$PHASE")"
if [[ -n "$required" ]]; then
  if [[ -z "$ev_dir" ]]; then
    c_red "evidence dir for phase $PHASE not found"
    errors=$((errors+1))
  else
    for f in $required; do
      if [[ ! -f "$ev_dir/$f" ]]; then
        c_red "missing required evidence: $ev_dir/$f"
        errors=$((errors+1))
      fi
    done
  fi
fi

# 7. report file exists for phase (except 11 / 10a which have own files)
report="$(phase_report_file "$PHASE")"
if [[ "$PHASE" != "10a" && "$PHASE" != "11" && -z "$report" ]]; then
  c_red "report file audit/${PHASE}_*.md not found"
  errors=$((errors+1))
fi

# 8. Stop-words check
if [[ -n "$report" && -f "$report" ]]; then
  while IFS= read -r word; do
    [[ -z "$word" ]] && continue
    if grep -q "$word" "$report" 2>/dev/null; then
      c_red "stop-word '$word' found in $report"
      errors=$((errors+1))
    fi
  done < <(stop_words)
fi

# 9. Phase-10 specific: ROADMAP.md exists
if [[ "$PHASE" == "10" ]]; then
  [[ -f "$AUDIT_DIR/ROADMAP.md" ]] || { c_red "audit/ROADMAP.md missing"; errors=$((errors+1)); }
fi

# 10. Phase-10a specific
if [[ "$PHASE" == "10a" ]]; then
  [[ -f "$AUDIT_DIR/_adversary_review.md" ]] || { c_red "_adversary_review.md missing"; errors=$((errors+1)); }
  [[ -f "$AUDIT_DIR/_known_unknowns.md" ]] || { c_red "_known_unknowns.md missing"; errors=$((errors+1)); }
fi

# 11. Phase-11 specific
if [[ "$PHASE" == "11" ]]; then
  [[ -f "$AUDIT_DIR/11_deep_dive.md" ]] || { c_red "11_deep_dive.md missing"; errors=$((errors+1)); }
  # Check that every critical has a section
  while read -r fid; do
    [[ -z "$fid" ]] && continue
    if ! grep -q "$fid" "$AUDIT_DIR/11_deep_dive.md" 2>/dev/null; then
      c_red "critical $fid missing in 11_deep_dive.md"
      errors=$((errors+1))
    fi
  done < <(jq -r 'select(.severity == "critical") | .id' "$FINDINGS" 2>/dev/null)
fi

if (( errors > 0 )); then
  c_red "phase $PHASE: $errors error(s)"
  exit 1
fi
ok "phase $PHASE: gate passed"
exit 0
