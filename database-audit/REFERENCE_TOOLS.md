# REFERENCE — инструменты

Справочник по инструментам, которые пайплайн использует. Читается один раз на старте.

---

## Serena (MCP, через LSP)

Семантическая навигация кода. Работает на уровне символов (модель, класс, метод), не строк.

| Tool | Зачем в database-audit |
|------|------------------------|
| `activate_project` | Активировать проект. Первое, что делаешь. |
| `get_symbols_overview` | Список моделей в `models.py`/`*.entity.ts`/`schema.prisma` без тел. |
| `find_symbol` | Поиск конкретной модели/класса. `include_body=true` только когда нужно тело транзакции/метода с raw SQL. |
| `find_referencing_symbols` | Кто ссылается на модель/функцию репозитория. Основа для blast-radius при предложении миграции. |
| `search_for_pattern` | Regex по проекту. Для `SELECT FOR UPDATE`, `BEGIN TRANSACTION`, raw SQL, `prisma.$queryRaw`, `db.execute`. |
| `list_dir` | Листинг (миграции, models, repositories). |
| `find_file` | Поиск файлов по маске (`*.sql`, `*entity*`, `migrations/*`). |
| `write_memory` / `read_memory` | `.serena/memories/db_audit_phase_NN`, прогресс, cross-phase notes. |

**Anti-pattern:** не используй `find_symbol include_body=true` без необходимости — каждый ORM-маппинг тащит много кода. Сначала overview, потом точечно.

---

## GitNexus (MCP)

Граф кода + git history. В database-audit используется для:

| Tool | Зачем |
|------|-------|
| `query` (cypher) | Граф зависимостей между моделями и репозиториями. «Кто пишет в `Account.balance`?» |
| `impact` | Blast-radius при предложении изменения схемы. «Что сломается, если переименовать `User.email` → `User.emailAddress`?» |
| `route_map` | API-routes которые трогают модель — для приоритизации critical paths. |
| `detect_changes` | Diff схемы между коммитами (за последние N дней / N релизов). |

**Cypher-примеры для DB-аудита:**

```cypher
// Все вызовы транзакций и кто их вызывает
MATCH (caller:Function)-[:CALLS]->(f:Function)
WHERE f.name IN ['$transaction', 'BEGIN', 'startTransaction', 'with_transaction']
RETURN caller.file, caller.name, f.name LIMIT 50

// Кто пишет в Account.balance (для money invariants)
MATCH (f:Function)-[:WRITES]->(field:Field {name: 'balance', class: 'Account'})
RETURN f.file, f.name, field.path
```

Если cypher 3 раза подряд пуст — fallback на ripgrep (см. §7.2 ORCHESTRATOR).

---

## Bash утилиты

Фундамент детектор-скриптов в `scripts/`.

| Команда | Назначение |
|---------|-----------|
| `rg` (ripgrep) | Быстрый regex-grep. Замена `grep -r`. Используется во всех детекторах. |
| `jq` | Парсинг JSON (вывод Prisma DMMF, EXPLAIN JSON, `cloc.json`). |
| `find` | Файловый обход (миграции, schema-файлы). |
| `awk`/`sed` | Парсинг таблиц вывода. |
| `python3` | Скрипты, где shell не справляется (`find_missing_indexes.py`, `validate_confidence.py`). |

---

## SQL утилиты (live mode)

Только для live-режима. **Все команды только на чтение.**

### PostgreSQL

```bash
# Подтверждение read-only роли
psql "$DATABASE_URL" -c "SELECT current_user, current_setting('default_transaction_read_only')"

# План запроса
psql "$DATABASE_URL" -c "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) <query>"

# Список индексов
psql "$DATABASE_URL" -c "SELECT * FROM pg_indexes WHERE schemaname = 'public'"

# Использование индексов (mark unused)
psql "$DATABASE_URL" -c "SELECT relname, indexrelname, idx_scan
                         FROM pg_stat_user_indexes
                         ORDER BY idx_scan ASC LIMIT 50"

# Slow queries (если pg_stat_statements включён)
psql "$DATABASE_URL" -c "SELECT query, calls, total_exec_time, mean_exec_time
                         FROM pg_stat_statements
                         ORDER BY mean_exec_time DESC LIMIT 30"

# Размер таблиц
psql "$DATABASE_URL" -c "SELECT relname, pg_size_pretty(pg_relation_size(relid))
                         FROM pg_stat_user_tables
                         ORDER BY pg_relation_size(relid) DESC LIMIT 20"

# FK без индекса (PG-специфичный)
psql "$DATABASE_URL" -f database-audit/scripts/sql/pg_fk_without_index.sql
```

### MySQL

```bash
mysql --defaults-extra-file=<(echo -e "[client]\nuser=$DB_USER\npassword=$DB_PASS") \
      -h "$DB_HOST" -e "EXPLAIN FORMAT=JSON <query>"

# Индексы
SELECT * FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = 'dbname'

# Slow log (если включён)
SELECT * FROM mysql.slow_log ORDER BY query_time DESC LIMIT 30
```

### MongoDB

```bash
mongosh "$DATABASE_URL" --eval 'db.collection.find({...}).explain("executionStats")'

# Индексы
db.collection.getIndexes()

# Профайлер (если включён)
db.system.profile.find().sort({millis: -1}).limit(30)
```

---

## Внешние сканеры (опционально)

| Tool | Используется в |
|------|----------------|
| `gitleaks` | Phase 07 — сканит DSN/пароли в истории git |
| `osv-scanner` | Phase 07 — известные уязвимости в драйверах БД |
| `sqlfluff` | Phase 04 — линт SQL (если в проекте есть `.sql` файлы) |

Все опциональные. Если не установлены — `run_external_tools.sh` пишет placeholder, валидация не падает.

---

## Anti-patterns при использовании инструментов

1. **Не читай миграции целиком** — у проекта может быть 200+ миграций. Используй `extract_schema_summary.sh` для агрегата, читай конкретные миграции только по делу.
2. **Не EXPLAIN-ай каждый запрос** — выбирай top-N по статистике/частоте. Бюджет: 20–30 EXPLAIN на средний проект.
3. **Не делай live-запросы без подтверждения read-only роли** (см. §3.1 ORCHESTRATOR).
4. **Не дёргай `pg_stat_statements`, если он не включён** — `run_external_tools.sh` детектит и пишет placeholder.
