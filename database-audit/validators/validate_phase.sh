#!/usr/bin/env bash
# Validate that phase NN passed its exit gate. Reads AUDIT_DIR from env.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PIPELINE_DIR/lib/env.sh"

require_cmd jq
require_cmd python3

PHASE="${1:-}"
[[ -n "$PHASE" ]] || { echo "Usage: $0 <NN>" >&2; exit 2; }

echo "==> validate_phase.sh phase=$PHASE  audit_dir=$AUDIT_DIR"

errors=0

# 1. findings.jsonl exists and parses
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

# Skip-marker support — phase can be skipped if manifest has skip_reason
skip_reason=$(python3 -c "
import yaml
try:
    m = yaml.safe_load(open('$MANIFEST'))
    print((m.get('phase_plan',{}).get('$PHASE',{}) or {}).get('skip_reason',''))
except Exception:
    pass
" 2>/dev/null || echo "")

if [[ -n "$skip_reason" ]]; then
  ok "phase $PHASE: skipped via manifest (reason: $skip_reason)"
  exit 0
fi

# 2. Findings count for this phase
phase_count=$(python3 -c "
import json
n=0
with open('$FINDINGS') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try:
            obj=json.loads(line)
            ph=str(obj.get('phase',''))
            if ph=='$PHASE' or ph.lstrip('0')==str('$PHASE').lstrip('0'):
                n+=1
        except: pass
print(n)
")
info "findings of phase $PHASE: $phase_count"

size="$(project_size)"
base_quota="$(phase_min_findings_M "$PHASE")"
scaled_quota="$(scale_quota_by_size "$base_quota" "$size")"
info "size=$size base_quota=$base_quota scaled_quota=$scaled_quota"

if (( phase_count < scaled_quota )); then
  c_red "findings count ($phase_count) < quota ($scaled_quota) for phase $PHASE"
  errors=$((errors+1))
fi

# 3-5. Confidence/exploit/lines checks via Python
python3 - "$PHASE" "$FINDINGS" <<'PYINNER' || errors=$((errors+1))
import sys, json
phase, findings_path = sys.argv[1], sys.argv[2]
errs = 0
with open(findings_path) as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try: obj=json.loads(line)
        except: continue
        ph=str(obj.get('phase',''))
        if not (ph==phase or ph.lstrip('0')==phase.lstrip('0')): continue
        fid = obj.get('id','?')
        if obj.get('confidence') == 'high':
            rat = obj.get('confidence_rationale','') or ''
            if len(rat) < 40:
                print(f'  ERR {fid}: high w/o rationale (len={len(rat)})'); errs+=1
            if not (obj.get('location') or {}).get('lines'):
                print(f'  ERR {fid}: high w/o location.lines'); errs+=1
        if obj.get('severity') == 'critical':
            ex = obj.get('exploit_proof','') or ''
            if len(ex) < 40:
                print(f'  ERR {fid}: critical w/o exploit_proof (len={len(ex)})'); errs+=1
sys.exit(1 if errs else 0)
PYINNER

# 6. required evidence files
ev_dir="$(phase_evidence_dir "$PHASE")"
required="$(phase_required_evidence "$PHASE")"
if [[ -n "$required" ]]; then
  if [[ -z "$ev_dir" ]]; then
    c_yellow "evidence dir for phase $PHASE not found (creating empty)"
    mkdir -p "$EVIDENCE_DIR/${PHASE}_phase"
    ev_dir="$EVIDENCE_DIR/${PHASE}_phase"
  fi
  for f in $required; do
    if [[ ! -f "$ev_dir/$f" ]]; then
      c_red "missing required evidence: $ev_dir/$f"
      errors=$((errors+1))
    fi
  done
fi

# 7. report file present (except 10a / 11)
report="$(phase_report_file "$PHASE")"
if [[ "$PHASE" != "10a" && "$PHASE" != "11" && -z "$report" ]]; then
  c_red "report file ${AUDIT_DIR}/${PHASE}_*.md not found"
  errors=$((errors+1))
fi

# 8. stop-words
if [[ -n "$report" && -f "$report" ]]; then
  while IFS= read -r word; do
    [[ -z "$word" ]] && continue
    if grep -qF "$word" "$report" 2>/dev/null; then
      c_red "stop-word '$word' found in $report"
      errors=$((errors+1))
    fi
  done < <(stop_words)
fi

# 9-11. Phase-specific
if [[ "$PHASE" == "10" ]]; then
  [[ -f "$AUDIT_DIR/ROADMAP.md" ]] || { c_red "$AUDIT_DIR/ROADMAP.md missing"; errors=$((errors+1)); }
fi
if [[ "$PHASE" == "10a" ]]; then
  [[ -f "$AUDIT_DIR/_adversary_review.md" ]] || { c_red "_adversary_review.md missing"; errors=$((errors+1)); }
  [[ -f "$AUDIT_DIR/_known_unknowns.md" ]] || { c_red "_known_unknowns.md missing"; errors=$((errors+1)); }
fi
if [[ "$PHASE" == "11" ]]; then
  [[ -f "$AUDIT_DIR/11_deep_dive.md" ]] || { c_red "11_deep_dive.md missing"; errors=$((errors+1)); }
  while read -r fid; do
    [[ -z "$fid" ]] && continue
    if ! grep -q "$fid" "$AUDIT_DIR/11_deep_dive.md" 2>/dev/null; then
      c_red "critical $fid missing in 11_deep_dive.md"
      errors=$((errors+1))
    fi
  done < <(jq -r 'select(.severity == "critical") | .id' "$FINDINGS" 2>/dev/null)
  # v4: section 4 (Fix variants) must NOT contain "_agent fills_" if any critical exists
  if [[ -f "$AUDIT_DIR/11_deep_dive.md" ]]; then
    if grep -q "Variant A (quick.*)\?:.*_agent fills_" "$AUDIT_DIR/11_deep_dive.md" 2>/dev/null; then
      c_red "11_deep_dive.md still has _agent fills_ placeholders in Fix variants — agent must complete"
      errors=$((errors+1))
    fi
    # section 5 (Test strategy)
    if grep -qE "^_agent fills:" "$AUDIT_DIR/11_deep_dive.md" 2>/dev/null; then
      c_red "11_deep_dive.md has unfilled sections — agent must complete"
      errors=$((errors+1))
    fi
  fi
fi

# v5: phase 10a — comprehensive enforcement
if [[ "$PHASE" == "10a" ]]; then
  if [[ -f "$AUDIT_DIR/_adversary_review.md" ]]; then
    size=$(wc -c < "$AUDIT_DIR/_adversary_review.md")
    if (( size < 500 )); then
      c_red "_adversary_review.md too small ($size bytes) — agent must enrich"
      errors=$((errors+1))
    fi
    if grep -q "_To be filled by agent_" "$AUDIT_DIR/_adversary_review.md" 2>/dev/null; then
      c_red "_adversary_review.md has placeholder text — agent must enrich"
      errors=$((errors+1))
    fi
    # v5: required sections
    for section in "Strong findings" "Severity calibration" "Systematic risks"; do
      if ! grep -qE "^## .*${section}" "$AUDIT_DIR/_adversary_review.md" 2>/dev/null; then
        c_red "_adversary_review.md missing section: ## $section"
        errors=$((errors+1))
      fi
    done
    # v5: confidence calibration check
    high_count=$(jq -c 'select(.confidence == "high")' "$FINDINGS" 2>/dev/null | grep -c . || true)
    total_count=$(grep -c . "$FINDINGS" 2>/dev/null || echo 1)
    if (( total_count > 0 )) && (( high_count * 100 / total_count > 50 )); then
      if ! grep -qE "(Confidence|calibration justification)" "$AUDIT_DIR/_adversary_review.md" 2>/dev/null; then
        c_red "_adversary_review.md: high>50% but no calibration justification"
        errors=$((errors+1))
      fi
    fi
  fi
fi

if (( errors > 0 )); then
  c_red "phase $PHASE: $errors error(s)"
  exit 1
fi
ok "phase $PHASE: gate passed"
exit 0
