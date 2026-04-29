#!/usr/bin/env bash
# validate_phase.sh — hard exit-gate for one audit phase.
# Usage: ./scripts/validate_phase.sh <NN>
#
# Checks:
#   1. Findings JSONL is valid and findings of this phase have all required fields
#   2. Quota of new findings >= scaled minimum (size-aware)
#   3. Report file exists, has all 7 mandatory h2 sections, has >= 150 lines
#      (or contains explicit "Проверено и чисто" section justifying lower count)
#   4. Evidence dir contains all required files for this phase
#   5. Per-phase confidence is not 100% one-bucket (when >=3 findings)
#   6. Each high-confidence finding has confidence_rationale of >= 40 chars
#      and location.lines is non-null
#   7. Each critical-severity finding has exploit_proof field of >= 40 chars
#
# Exit 0 = phase passed gate; exit 1 = at least one check failed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"

require_cmd jq
require_cmd python3
require_audit_dir

PHASE="${1:-}"
[[ -n "$PHASE" ]] || { echo "Usage: $0 <NN>" >&2; exit 2; }

echo "==> validate_phase.sh phase=$PHASE"

errors=0

# ------------------------------------------------------------------------------
# 1. findings.jsonl validity (whole file)
# ------------------------------------------------------------------------------
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

# Findings of this phase
phase_findings_json="$(jq -c "select(.phase == ($PHASE | tonumber))" "$FINDINGS" 2>/dev/null || true)"
phase_count=$(printf '%s\n' "$phase_findings_json" | grep -c . || true)
info "findings of phase $PHASE: $phase_count"

# ------------------------------------------------------------------------------
# 2. quota
# ------------------------------------------------------------------------------
size="$(project_size)"
base_quota="$(phase_min_findings_M "$PHASE")"
scaled_quota="$(scale_quota_by_size "$base_quota" "$size")"
info "size=$size base_quota=$base_quota scaled_quota=$scaled_quota"

report_file="$(phase_report_file "$PHASE")"
clean_section_present=0
if [[ -n "$report_file" ]] && grep -qE '^##\s*[0-9.]*\s*Проверено и чисто' "$report_file"; then
  clean_section_present=1
fi

if (( phase_count < scaled_quota )); then
  if (( clean_section_present )); then
    warn "phase $PHASE has $phase_count findings (< quota $scaled_quota), but 'Проверено и чисто' section present — accepted"
  else
    c_red "phase $PHASE has $phase_count findings, quota=$scaled_quota and no 'Проверено и чисто' section"
    errors=$((errors+1))
  fi
else
  ok "quota check ($phase_count >= $scaled_quota)"
fi

# ------------------------------------------------------------------------------
# 3. report exists, sections present, length
# ------------------------------------------------------------------------------
if [[ -z "$report_file" ]]; then
  c_red "no report file matches $AUDIT_DIR/${PHASE}_*.md"
  errors=$((errors+1))
else
  # Length
  lines=$(wc -l < "$report_file")
  if (( lines < 150 )) && (( PHASE != 0 )); then
    if (( clean_section_present )); then
      warn "report $report_file has $lines lines (< 150) — accepted because 'Проверено и чисто' present"
    else
      c_red "report $report_file has $lines lines (< 150) and no 'Проверено и чисто'"
      errors=$((errors+1))
    fi
  else
    ok "report length $lines"
  fi

  # Sections — match by leading number e.g. "## 1." (any heading text)
  missing_sections=()
  for n in 1 2 3 4 5 6 7; do
    if ! grep -qE "^##\s*${n}\.\s+" "$report_file"; then
      missing_sections+=("section $n")
    fi
  done
  if (( ${#missing_sections[@]} > 0 )); then
    c_red "missing sections in $report_file: ${missing_sections[*]}"
    errors=$((errors+1))
  else
    ok "all 7 sections present"
  fi
fi

# ------------------------------------------------------------------------------
# 4. evidence files
# ------------------------------------------------------------------------------
ev_dir="$(phase_evidence_dir "$PHASE")"
required="$(phase_required_evidence "$PHASE")"

if [[ -n "$required" ]]; then
  if [[ -z "$ev_dir" ]]; then
    c_red "evidence dir $EVIDENCE_DIR/${PHASE}_*/ not found"
    errors=$((errors+1))
  else
    missing_ev=()
    for f in $required; do
      [[ -f "$ev_dir/$f" ]] || missing_ev+=("$f")
    done
    if (( ${#missing_ev[@]} > 0 )); then
      c_red "missing evidence in $ev_dir: ${missing_ev[*]}"
      errors=$((errors+1))
    else
      ok "evidence files present ($(echo $required | wc -w))"
    fi
    # At least 2 files anyway
    ev_count=$(find "$ev_dir" -type f | wc -l)
    if (( ev_count < 2 )); then
      c_red "evidence dir $ev_dir contains only $ev_count files (need >=2)"
      errors=$((errors+1))
    fi
  fi
fi

# ------------------------------------------------------------------------------
# 5. per-phase confidence not 100% monoculture (when >=3 findings)
# ------------------------------------------------------------------------------
if (( phase_count >= 3 )); then
  conf_buckets=$(printf '%s\n' "$phase_findings_json" | jq -r '.confidence' | sort -u | wc -l)
  if (( conf_buckets <= 1 )); then
    c_red "phase $PHASE has $phase_count findings all of the same confidence — likely under-calibrated; review §3.3 of orchestrator"
    errors=$((errors+1))
  else
    ok "confidence diversity ($conf_buckets buckets)"
  fi
fi

# ------------------------------------------------------------------------------
# 6. high-confidence finding metadata: rationale + line citation
# ------------------------------------------------------------------------------
high_bad=$(printf '%s\n' "$phase_findings_json" | jq -r '
  select(.confidence == "high") |
  select((.confidence_rationale // "") | length < 40 or (.location.lines // null) == null) |
  .id' 2>/dev/null | grep -v '^$' || true)
if [[ -n "$high_bad" ]]; then
  c_red "high-confidence findings missing confidence_rationale (>=40 chars) or location.lines:"
  while IFS= read -r id; do echo "  - $id" >&2; done <<<"$high_bad"
  errors=$((errors+1))
else
  high_n=$(printf '%s\n' "$phase_findings_json" | jq -r 'select(.confidence == "high") | .id' | grep -c . || true)
  (( high_n > 0 )) && ok "all $high_n high-confidence findings have rationale + lines"
fi

# ------------------------------------------------------------------------------
# 7. critical-severity finding has exploit_proof
# ------------------------------------------------------------------------------
crit_bad=$(printf '%s\n' "$phase_findings_json" | jq -r '
  select(.severity == "critical") |
  select((.exploit_proof // "") | length < 40) |
  .id' 2>/dev/null | grep -v '^$' || true)
if [[ -n "$crit_bad" ]]; then
  c_red "critical-severity findings missing exploit_proof (>=40 chars):"
  while IFS= read -r id; do echo "  - $id" >&2; done <<<"$crit_bad"
  errors=$((errors+1))
fi

# ------------------------------------------------------------------------------
echo
if (( errors > 0 )); then
  c_red "validate_phase.sh: $errors error(s) for phase $PHASE — fix and rerun"
  exit 1
fi
c_green "validate_phase.sh: phase $PHASE PASSED gate"
exit 0
