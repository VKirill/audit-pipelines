#!/usr/bin/env bash
# Run all external detectors and write evidence/.
# Single entry point — call once at start of phase 00.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e  # don't exit on individual tool failures

require_audit_dir
mkdir -p "$EVIDENCE_DIR"/{00_setup,01_inventory,03_indexes_keys,04_query_patterns,06_migrations_evolution,07_data_integrity_security}

run_step() {
  local name="$1"; shift
  echo "==> $name"
  if "$@"; then ok "$name"; else warn "$name failed (continuing)"; fi
  echo
}

# 00 setup — stack detection
run_step "detect_db_stack" bash "$SCRIPT_DIR/detect_db_stack.sh" \
  > "$EVIDENCE_DIR/00_setup/stack_detection.txt"

# 00 setup — git stats
if [[ -d .git ]]; then
  {
    echo "# Git stats — $(date -Iseconds)"
    echo "## HEAD: $(git rev-parse HEAD 2>/dev/null)"
    echo "## Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "## Commits total: $(git rev-list --count HEAD 2>/dev/null)"
    echo "## Last 90d: $(git log --since='90 days ago' --oneline 2>/dev/null | wc -l)"
    echo
    echo "## Authors"
    git shortlog -sne 2>/dev/null | head -20
  } > "$EVIDENCE_DIR/00_setup/git_stats.txt"
  ok "git_stats.txt"
else
  warn "Not a git repo — skipping git_stats"
fi

# 01 inventory — schema summary
run_step "extract_schema_summary" bash "$SCRIPT_DIR/extract_schema_summary.sh"

# 01 inventory — query inventory
run_step "extract_query_inventory" bash "$SCRIPT_DIR/extract_query_inventory.sh"

# 01 inventory — transaction inventory
run_step "find_transactions" bash "$SCRIPT_DIR/find_transactions.sh"

# 03 indexes — missing FK indexes
run_step "find_missing_indexes" python3 "$SCRIPT_DIR/find_missing_indexes.py" \
  > "$EVIDENCE_DIR/03_indexes_keys/fk_without_index.md"

# 04 queries — N+1 suspects
run_step "find_n_plus_one" bash "$SCRIPT_DIR/find_n_plus_one.sh"

# 04 queries — SELECT *
run_step "find_select_star" bash "$SCRIPT_DIR/find_select_star.sh"

# 06 migrations — dangerous DDL
run_step "find_migrations" bash "$SCRIPT_DIR/find_migrations.sh"

# 07 security — SQLi surface
run_step "find_string_concat_sql" bash "$SCRIPT_DIR/find_string_concat_sql.sh"

# 07 security — secret scan (best-effort)
if command -v gitleaks >/dev/null 2>&1; then
  run_step "gitleaks" gitleaks detect --no-banner --no-git --source . \
    --report-path "$EVIDENCE_DIR/07_data_integrity_security/secret_scan.txt" \
    --report-format json
else
  # Grep fallback
  {
    echo "# Secret scan (grep fallback) — $(date -Iseconds)"
    echo "(install gitleaks for better coverage)"
    echo
    rg -nE 'postgres(ql)?://[^:]+:[^@]+@|mysql://[^:]+:[^@]+@|mongodb(\+srv)?://[^:]+:[^@]+@|sk_live_|sk_test_|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}' \
       -g '!node_modules' -g '!.git' -g '!*.lock' . 2>/dev/null | head -100
  } > "$EVIDENCE_DIR/07_data_integrity_security/secret_scan.txt"
  ok "secret_scan.txt (grep fallback)"
fi

# Live DB probe (no-op if DATABASE_URL not set)
run_step "live_db_probe" bash "$SCRIPT_DIR/live_db_probe.sh"

ok "External tools done. Review evidence/* before starting phases."
