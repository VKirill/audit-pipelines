#!/usr/bin/env bash
# Inventory + dangerous DDL detection in migrations.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/06_migrations_evolution"
mkdir -p "$OUT_DIR"

# Find migration directories
MIG_DIRS=()
for d in prisma/migrations migrations db/migrate database/migrations alembic alembic/versions \
         sql/migrations migration; do
  [[ -d "$d" ]] && MIG_DIRS+=("$d")
done

# Inventory
{
  echo "# Migrations inventory"
  echo "Generated: $(date -Iseconds)"
  echo

  if (( ${#MIG_DIRS[@]} == 0 )); then
    echo "**No migration directories detected.** Possible reasons:"
    echo "- Declarative schema tool (Atlas, Skeema)."
    echo "- External migration repo."
    echo "- Manual DBA-applied migrations."
    echo "Manual confirmation required (see phase_06)."
    exit 0
  fi

  echo "## Directories detected"
  for d in "${MIG_DIRS[@]}"; do
    count=$(find "$d" -type f \( -name '*.sql' -o -name '*.ts' -o -name '*.js' -o -name '*.py' -o -name '*.rb' \) 2>/dev/null | wc -l)
    echo "- \`$d\` — $count files"
  done

  echo
  echo "## Migration files (sorted)"
  echo
  for d in "${MIG_DIRS[@]}"; do
    echo "### $d"
    echo '```'
    find "$d" -type f \( -name '*.sql' -o -name '*.ts' -o -name '*.js' -o -name '*.py' -o -name '*.rb' \) 2>/dev/null | sort | head -100
    echo '```'
  done

} > "$OUT_DIR/migrations_inventory.md"

# Dangerous DDL detection
{
  echo "# Dangerous DDL in migrations — Sadalage & Ambler analysis"
  echo "Generated: $(date -Iseconds)"
  echo
  echo "Each match needs review for **multi-step / zero-downtime safety**."
  echo

  echo "## DROP TABLE / COLUMN / INDEX"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'DROP\s+(TABLE|COLUMN|INDEX|CONSTRAINT)' "$d" 2>/dev/null | head -100
  done
  echo '```'

  echo
  echo "## ADD COLUMN with NOT NULL DEFAULT (rewrites table on PG <11)"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nUE 'ADD\s+COLUMN\s+\w+\s+\w+\s+NOT\s+NULL\s+DEFAULT' "$d" 2>/dev/null | head -100
  done
  echo '```'

  echo
  echo "## ALTER COLUMN TYPE (rewrites table)"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'ALTER\s+(COLUMN|TABLE).*?(TYPE|ALTER\s+COLUMN)' "$d" 2>/dev/null | head -100
  done
  echo '```'

  echo
  echo "## RENAME COLUMN (breaks app compatibility during rolling deploy)"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'RENAME\s+(COLUMN|TO)' "$d" 2>/dev/null | head -100
  done
  echo '```'

  echo
  echo "## CREATE INDEX without CONCURRENTLY (blocks writes on PG)"
  echo "Все CREATE INDEX, не помеченные как CONCURRENTLY, в проектах на PG:"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'CREATE\s+(UNIQUE\s+)?INDEX' "$d" 2>/dev/null | rg -v 'CONCURRENTLY' | head -100
  done
  echo '```'

  echo
  echo "## ADD CONSTRAINT without NOT VALID (validates synchronously)"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'ADD\s+CONSTRAINT' "$d" 2>/dev/null | rg -v 'NOT VALID' | head -50
  done
  echo '```'

  echo
  echo "## TRUNCATE TABLE"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'TRUNCATE\s+TABLE' "$d" 2>/dev/null | head -30
  done
  echo '```'

  echo
  echo "## UPDATE без LIMIT/WHERE (full table)"
  echo '```'
  for d in "${MIG_DIRS[@]}"; do
    rg -nE 'UPDATE\s+\w+\s+SET' "$d" 2>/dev/null | rg -vE 'WHERE|LIMIT' | head -50
  done
  echo '```'

} > "$OUT_DIR/dangerous_ddl.md"

# Reversibility audit (presence of down/rollback)
{
  echo "# Reversibility audit"
  echo "Generated: $(date -Iseconds)"
  echo
  echo "Каждая миграция: имеет ли соответствующий rollback?"
  echo
  for d in "${MIG_DIRS[@]}"; do
    echo "## $d"
    echo
    case "$d" in
      *prisma/migrations*)
        echo "Prisma migrations не поддерживают down-скрипты by design (forward-only). См. https://www.prisma.io/docs/orm/prisma-migrate/getting-started — нужна стратегия отката через новую миграцию."
        ;;
      *db/migrate*|*migrations*)
        # Rails / generic — каждый файл должен иметь либо `def down`, либо reversible operations
        echo '```'
        for f in $(find "$d" -type f \( -name '*.rb' -o -name '*.ts' -o -name '*.js' -o -name '*.py' \) 2>/dev/null | head -50); do
          has_down=no
          if rg -qE '(def\s+down|down\s*:|async\s+down\s*\(|exports\.down)' "$f" 2>/dev/null; then
            has_down=yes
          fi
          echo "$f -- has_down=$has_down"
        done
        echo '```'
        ;;
      *alembic*)
        echo "Alembic: каждая ревизия должна иметь и upgrade(), и downgrade()."
        echo '```'
        for f in $(find "$d" -type f -name '*.py' 2>/dev/null | head -50); do
          has_down=no
          rg -qE 'def\s+downgrade' "$f" 2>/dev/null && has_down=yes
          echo "$f -- has_downgrade=$has_down"
        done
        echo '```'
        ;;
    esac
    echo
  done
} > "$OUT_DIR/reversibility_audit.md"

# Multi-step analysis placeholder (manual review)
{
  echo "# Multi-step deploy analysis"
  echo "Generated: $(date -Iseconds)"
  echo
  echo "**Manual review required.** Используя `dangerous_ddl.md`, проверь для каждого RENAME/DROP/TYPE-изменения:"
  echo
  echo "1. Был ли pre-deploy с добавлением новой колонки?"
  echo "2. Был ли backfill?"
  echo "3. Был ли deploy с переключением кода?"
  echo "4. И только потом — миграция drop/rename?"
  echo
  echo "Sadalage & Ambler, Refactoring Databases, Part II — описание полной последовательности."
} > "$OUT_DIR/multi_step_analysis.md"

ok "Migration analysis written"
