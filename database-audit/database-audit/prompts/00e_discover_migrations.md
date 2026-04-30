# 00e — Deep discovery: Migrations

---

## Шаги

### 1. Detect migration tool

```bash
# Standard locations
ls prisma/migrations/ 2>/dev/null      # → prisma-migrate
ls alembic/versions/ 2>/dev/null       # → alembic
ls db/migrate/ 2>/dev/null              # → activerecord-migrations
ls migrations/ 2>/dev/null              # → varied (Sequelize, TypeORM, Knex)
ls atlas.hcl 2>/dev/null                # → atlas
ls schema.sql 2>/dev/null               # → declarative
[ -f prisma/migrations/migration_lock.toml ] && echo "prisma-migrate"

# Modern 2026 zero-downtime tools
ls .pgroll/ 2>/dev/null                 # → pgroll (PG zero-downtime)
ls reshape/ 2>/dev/null                 # → reshape (similar)

# Date-prefixed raw SQL (vechkasov-стиль)
find . -type f -name '*.sql' -regextype posix-extended \
  -regex '.*/(20[0-9]{2}-[0-9]{2}-[0-9]{2}|[0-9]{14})_*.*\.sql' \
  -not -path '*/node_modules/*' | head -10
```

### 2. Перечисли файлы

Если ≤ 50 файлов — явный список в `paths.migration_files.files`.
Если > 50 — `paths.migration_files.dirs` + первые 10 в `files` (как примеры).

### 3. Dangerous DDL — critical для phase 06

Пройдись по **каждому** migration-файлу. Ищи паттерны:

```bash
# Проход по всем миграциям
for f in <migration files>; do
  echo "=== $f ==="
  rg -nE 'DROP\s+(TABLE|COLUMN|INDEX|CONSTRAINT)' "$f"
  rg -nE 'ALTER\s+(COLUMN|TABLE).*(TYPE|RENAME)' "$f"
  rg -nE 'ADD\s+COLUMN.*NOT\s+NULL\s+DEFAULT' "$f"
  rg -nE 'CREATE\s+(UNIQUE\s+)?INDEX' "$f" | rg -v 'CONCURRENTLY'
  rg -nE 'TRUNCATE\s+TABLE' "$f"
  rg -nE 'UPDATE\s+\w+\s+SET' "$f" | rg -vE 'WHERE|LIMIT'
  rg -nE 'ADD\s+CONSTRAINT' "$f" | rg -v 'NOT VALID'
done
```

Для каждой опасной операции — kind из enum:
- `drop-table`, `drop-column`, `rename-column`, `alter-column-type`
- `add-not-null-default`, `create-index-blocking`
- `add-constraint-validating`, `truncate`, `update-without-where`, `large-tx-wrap`

### 4. Заполнение

```yaml
paths:
  migration_files:
    tool: prisma-migrate  # или raw-sql-by-date / alembic / atlas
    dirs: [prisma/migrations]
    files: []  # список если ≤ 50

hints:
  dangerous_migrations:
    - file: packages/db/prisma/2026-04-30-ai-gateway-foundation.sql
      lines: "14-300"
      kind: large-tx-wrap
    - file: packages/db/prisma/2026-04-30-ai-gateway-foundation.sql
      lines: "197-210"
      kind: add-not-null-default
```

### 5. 2026 modern alternatives

Для PostgreSQL projects полезно отметить:
- Используется ли **pgroll** или **Reshape** для zero-downtime?
- Используется ли **Atlas DB schema-as-code**?
- Используется ли **dbmate** или **migrate** (CLI)?

Эти инструменты решают многие dangerous DDL автоматически.

### 6. Reversibility

Для каждого файла — есть ли down-script?

```bash
for f in <migration files>; do
  if rg -qE '(def\s+down|exports\.down|down\s*:|down\(|DOWN)' "$f"; then
    echo "$f -- has_down=yes"
  else
    echo "$f -- has_down=no"
  fi
done
```

Зафиксируй в `audit/01_inventory.md` (не hints — это inventory-факт).

---

## Источники

- Sadalage & Ambler, *Refactoring Databases* (главный источник)
- pgroll docs (https://github.com/xataio/pgroll) — modern zero-downtime
- Atlas docs (https://atlasgo.io)
