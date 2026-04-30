#!/usr/bin/env bash
# Inventory of transaction usage patterns.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/01_inventory"
mkdir -p "$OUT_DIR"

require_cmd rg

{
  echo "# Transaction usage inventory"
  echo "Generated: $(date -Iseconds)"
  echo

  echo "## Explicit transaction openings"
  echo
  echo "### Prisma — \$transaction"
  echo '```'
  rg -nE '\$transaction\s*\(' --type ts --type js -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo "### TypeORM / Sequelize / Knex"
  echo '```'
  rg -nE '\.(transaction|withTransaction|startTransaction|begin)\s*\(' --type ts --type js -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo "### SQLAlchemy"
  echo '```'
  rg -nE '(session\.(begin|begin_nested)|with\s+\w+\.begin\(\)|with_for_update)' --type py 2>/dev/null | head -50
  echo '```'

  echo "### Django"
  echo '```'
  rg -nE '(transaction\.atomic|with\s+transaction\.atomic|@transaction\.atomic)' --type py 2>/dev/null | head -50
  echo '```'

  echo "### Go"
  echo '```'
  rg -nE 'db\.Begin(Tx)?\(' --type go 2>/dev/null | head -50
  echo '```'

  echo "### Raw SQL"
  echo '```'
  rg -nE 'BEGIN(\s+TRANSACTION)?|START\s+TRANSACTION' --type sql 2>/dev/null | head -50
  echo '```'

  echo
  echo "## Isolation level mentions"
  echo '```'
  rg -nE '(SET\s+TRANSACTION\s+ISOLATION\s+LEVEL|isolationLevel|Isolation\.|with_isolation_level|isolation:)' \
     -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo
  echo "## Row-level locks (SELECT FOR UPDATE)"
  echo '```'
  rg -nE '(FOR\s+UPDATE|forUpdate|with_for_update|pessimistic_lock|lock\(\.write|skipLocked)' \
     -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo
  echo "## Optimistic locking"
  echo '```'
  rg -nE '(@Version|optimistic_lock|@@\[increment_lock_version\]|version\s*\+\s*1|UPDATE.*WHERE.*version\s*=)' \
     -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo
  echo "## External I/O inside transactions (smell)"
  echo "Heuristic: fetch/http/email/publish call within \$transaction body. Manual review required."
  echo '```'
  rg -nE -B 3 '(fetch\(|axios\.|http\.|sendMail|publish\(|kafka\.)' --type ts --type js -g '!node_modules' . 2>/dev/null | grep -B 3 -A 0 '\$transaction\|transaction\.atomic\|begin' | head -50
  echo '```'

} > "$OUT_DIR/transactions_list.md"

ok "transactions_list.md written"
