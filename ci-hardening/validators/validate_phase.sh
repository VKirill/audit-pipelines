#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PIPELINE_DIR/lib/env.sh"

require_cmd python3
PHASE="${1:-}"
[[ -n "$PHASE" ]] || { echo "Usage: $0 <NN>"; exit 2; }

errors=0
[[ -f "$FINDINGS" ]] || die "$FINDINGS missing"

# 1. Findings count check
phase_count=$(python3 -c "
import json
n=0
with open('$FINDINGS') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try:
            obj=json.loads(line)
            if str(obj.get('phase','')) == '$PHASE': n+=1
        except: pass
print(n)
")
base_quota="$(phase_min_findings_M "$PHASE")"
info "phase $PHASE findings: $phase_count, quota: $base_quota"
if (( phase_count < base_quota )); then
  c_yellow "phase $PHASE: findings ($phase_count) < quota ($base_quota) — soft fail"
fi

# 2. Required evidence
ev_dir="$(phase_evidence_dir "$PHASE")"
required="$(phase_required_evidence "$PHASE")"
if [[ -n "$required" && -n "$ev_dir" ]]; then
  for f in $required; do
    if [[ ! -f "$ev_dir/$f" ]]; then
      c_yellow "missing evidence: $ev_dir/$f"
    fi
  done
fi

# 3. confidence_rationale на high
high_no_rat=$(python3 -c "
import json, sys
n=0
with open('$FINDINGS') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try:
            o=json.loads(line)
            if str(o.get('phase','')) != '$PHASE': continue
            if o.get('confidence') == 'high':
                if len(o.get('confidence_rationale','') or '') < 40: n+=1
        except: pass
print(n)
")
if (( high_no_rat > 0 )); then
  c_red "phase $PHASE: $high_no_rat high-confidence findings без rationale ≥ 40 chars"
  errors=$((errors+1))
fi

# 4. exploit_proof на critical
crit_no_proof=$(python3 -c "
import json
n=0
with open('$FINDINGS') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try:
            o=json.loads(line)
            if str(o.get('phase','')) != '$PHASE': continue
            if o.get('severity') == 'critical':
                if len(o.get('exploit_proof','') or '') < 40: n+=1
        except: pass
print(n)
")
if (( crit_no_proof > 0 )); then
  c_yellow "phase $PHASE: $crit_no_proof critical findings без exploit_proof ≥ 40 chars (soft)"
fi

# 5. v2: phase 10 enforcement
if [[ "$PHASE" == "10" && -f "$AUDIT_DIR/10_deep_dive.md" ]]; then
  if grep -q "_agent fills_" "$AUDIT_DIR/10_deep_dive.md" 2>/dev/null; then
    c_yellow "phase 10: _agent fills_ placeholders present — agent should complete"
  fi
fi

if (( errors > 0 )); then
  c_red "phase $PHASE: $errors error(s)"; exit 1
fi
ok "phase $PHASE: gate passed"
