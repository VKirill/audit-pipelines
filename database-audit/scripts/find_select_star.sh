#!/usr/bin/env bash
# Find SELECT * usage in raw SQL and ORM raw queries.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/04_query_patterns"
mkdir -p "$OUT_DIR"

require_cmd rg

{
  echo "# SELECT * usage — Karwin §18 Implicit Columns"
  echo "Generated: $(date -Iseconds)"
  echo
  echo "## In .sql files"
  echo '```'
  rg -nE 'SELECT\s+\*\s+FROM' --type sql -g '!node_modules' -g '!.git' . 2>/dev/null
  echo '```'
  echo
  echo "## In code (raw queries)"
  echo '```'
  rg -nE 'SELECT\s+\*\s+FROM' \
     -g '!*.sql' -g '!node_modules' -g '!.git' -g '!dist' -g '!build' -g '!vendor' \
     . 2>/dev/null | head -100
  echo '```'
} > "$OUT_DIR/select_star.md"

ok "select_star.md written"
