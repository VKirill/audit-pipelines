#!/usr/bin/env bash
# Inventory of raw SQL strings + ORM call sites.
# Heuristic, not perfect — feeds phase 04.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/01_inventory"
mkdir -p "$OUT_DIR"

require_cmd rg

OUT="$OUT_DIR/queries_inventory.md"
SQL_DIR="$OUT_DIR/raw_sql_snippets"
mkdir -p "$SQL_DIR"

{
  echo "# Query Inventory — $(date -Iseconds)"
  echo

  echo "## 1. Raw SQL files"
  echo
  files=$(find . -type f -name '*.sql' -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/vendor/*' 2>/dev/null | sort)
  if [[ -z "$files" ]]; then
    echo "(none)"
  else
    echo '```'
    echo "$files"
    echo '```'
  fi

  echo
  echo "## 2. Raw SQL embedded in code"
  echo
  echo "### Patterns: \$queryRaw, db.execute, cursor.execute, EntityManager.createNativeQuery"
  echo
  echo '```'
  rg -nE '(\$queryRaw|\$executeRaw|connection\.query|connection\.execute|db\.execute|db\.query|cursor\.execute|createNativeQuery|raw\(|sql`)' \
     -g '!node_modules' -g '!.git' -g '!dist' -g '!build' -g '!vendor' -g '!*.lock' \
     . 2>/dev/null | head -200
  echo '```'

  echo
  echo "## 3. SELECT * usage"
  echo
  echo '```'
  rg -nE 'SELECT\s+\*\s+FROM' -g '!node_modules' -g '!.git' . 2>/dev/null | head -100
  echo '```'

  echo
  echo "## 4. ORM call sites — top patterns"
  echo

  echo "### Prisma"
  echo '```'
  rg -nE 'prisma\.\w+\.\w+\(' -g '!node_modules' -g '!.git' . 2>/dev/null | head -50
  echo '```'

  echo "### TypeORM (Repository)"
  echo '```'
  rg -nE '\.(find|findOne|findOneBy|findAll|save|update|delete|create|insert)\(' --type ts -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo "### Sequelize"
  echo '```'
  rg -nE '\.(findAll|findByPk|findOne|create|update|destroy|bulkCreate)\(' --type ts --type js -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo "### Django ORM"
  echo '```'
  rg -nE '\.objects\.(filter|get|all|create|update|delete|select_related|prefetch_related)\(' --type py 2>/dev/null | head -50
  echo '```'

  echo "### SQLAlchemy"
  echo '```'
  rg -nE '(session\.(query|execute|get|add|delete)|select\(|insert\(|update\(|delete\()' --type py 2>/dev/null | head -50
  echo '```'

  echo "### Mongoose"
  echo '```'
  rg -nE '\.(find|findOne|findById|findOneAndUpdate|aggregate|create|save|deleteOne|deleteMany)\(' --type ts --type js -g '!node_modules' . 2>/dev/null | head -50
  echo '```'

  echo
  echo "## 5. Pagination patterns"
  echo
  echo '```'
  rg -nE '(LIMIT\s+\d+\s+OFFSET|\.skip\(|\.offset\(|\.take\()' -g '!node_modules' . 2>/dev/null | head -30
  echo '```'

} > "$OUT"

ok "queries_inventory.md written"
