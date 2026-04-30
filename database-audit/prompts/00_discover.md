# 00 — Discover (orchestrator)

> **v3 — chunked discovery.** Этот файл — оркестратор. Глубокая работа по специальным темам — в sub-prompts (`00a..00e`). На больших проектах загружай sub-prompts по необходимости, не пытайся всё в одном context-окне.

---

## Цель

Создать **полный, проверенный** `audit/manifest.yml` по схеме `manifest.schema.yml`. От качества этого файла зависят все 14 фаз пайплайна.

---

## Правила поведения

1. **Read-only.** Никаких правок в коде проекта. Запись только в `audit/manifest.yml` + `audit/00_setup.md` + `.serena/memories/db_audit_discover_log`.
2. **Точные пути.** Никаких glob-аппроксимаций где можно дать список.
3. **Точные строки.** Каждый `file:lines` ты сам прочитал.
4. **Stop при сомнении.** Если стек неопределим — спроси пользователя, не выдумывай.
5. **Quality > speed.** Лучше 40 минут на полный manifest, чем 10 на пустой.
6. **Validate перед фиксацией** (см. `00z_validate_manifest.md`).

---

## Pipeline

```
1. Skeleton:        этот файл, шаги 1-5 (стек, пути, размер)
2. Money:           prompts/00a_discover_money.md
3. Transactions:    prompts/00b_discover_transactions.md
4. PII:             prompts/00c_discover_pii.md
5. N+1:             prompts/00d_discover_n_plus_one.md
6. Migrations:      prompts/00e_discover_migrations.md
7. Modern (2026):   шаг 6 этого файла
8. Validate:        prompts/00z_validate_manifest.md
9. Report:          стоп, сообщи пользователю
```

---

## Шаг 1 — Skeleton

### 1.1. Project root + workspaces

```bash
pwd
[ -f package.json ]       && jq -r '.workspaces' package.json 2>/dev/null
[ -f pnpm-workspace.yaml ] && cat pnpm-workspace.yaml
[ -f Cargo.toml ]          && grep -A 20 '\[workspace\]' Cargo.toml
[ -f go.work ]             && cat go.work
```

### 1.2. Git state

```bash
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
```

### 1.3. Размер проекта

```bash
find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.kt' -o -name '*.rb' -o -name '*.php' \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/.venv/*' -not -path '*/.next/*' -not -path '*/.turbo/*' \
  | xargs wc -l 2>/dev/null | tail -1
```

Размер (XS/S/M/L/XL) по таблице из `01_ORCHESTRATOR.md §6`.

**Заполни:** `project.{root, name, type, workspaces, size, loc, git_head, git_branch}`.

---

## Шаг 2 — Stack detection

### 2.1. ORM (минимум 2 признака из 3)

В монорепо **обязательно** скан по всем `package.json`/`requirements.txt`/`go.mod`/`composer.json`/`Gemfile`/`Cargo.toml`/`pom.xml`:

```bash
# Node ecosystem (всегда сканировать ВСЕ package.json)
find . -name 'package.json' -not -path '*/node_modules/*' \
  -exec grep -lE '"(@prisma/client|drizzle-orm|typeorm|sequelize|mongoose|knex|kysely|@mikro-orm|pg|mysql2)' {} \; 2>/dev/null

# Python
find . \( -name 'pyproject.toml' -o -name 'requirements*.txt' -o -name 'setup.py' \) \
  -not -path '*/.venv/*' -exec grep -lE '(sqlalchemy|django|tortoise|peewee|psycopg|asyncpg|pymongo)' {} \; 2>/dev/null

# Go
find . -name 'go.mod' -exec grep -lE '(gorm.io/gorm|jmoiron/sqlx|sqlc-dev/sqlc|uptrace/bun|entgo.io)' {} \; 2>/dev/null

# Rust / PHP / Ruby / Java
find . -name 'Cargo.toml' -exec grep -lE '(diesel|sqlx|sea-orm)' {} \; 2>/dev/null
find . -name 'composer.json' -exec grep -lE '(doctrine/orm|illuminate/database|laravel/framework)' {} \; 2>/dev/null
find . -name 'Gemfile' -exec grep -lE '(rails|sequel)' {} \; 2>/dev/null
find . \( -name 'pom.xml' -o -name 'build.gradle*' \) -exec grep -lE '(hibernate|spring-boot-starter-data-jpa|jOOQ|mybatis)' {} \; 2>/dev/null

# Schema files (визуальное подтверждение)
find . -name '*.prisma' -not -path '*/node_modules/*' 2>/dev/null
find . -name '*.entity.ts' -not -path '*/node_modules/*' 2>/dev/null | head -20
find . -name 'models.py' -not -path '*/.venv/*' -not -path '*/site-packages/*' 2>/dev/null | head -20
rg -lE 'pgTable\(|mysqlTable\(|sqliteTable\(' --type ts -g '!node_modules' . 2>/dev/null
rg -lE 'gorm:"' --type go . 2>/dev/null
```

### 2.2. БД detection

```bash
# DSN patterns в env/config файлах
rg -nE 'postgres(ql)?://|mysql://|mariadb://|mongodb(\+srv)?://|redis://|sqlite:|sqlite3:|clickhouse://' \
   --no-ignore -g '!node_modules' -g '!.git' -g '*.env*' -g '*.yml' -g '*.yaml' -g '*.json' -g '*.toml' .
```

Если множественные БД — определи `primary_db` (где бизнес-данные).

**Заполни:** `stack.{primary_db, also_used_dbs, primary_orm, also_used_orms, orm_versions}`.

---

## Шаг 3 — Schema files (точный список)

См. `01_ORCHESTRATOR.md §6.7.1` для команд по каждому ORM.

```bash
# Prisma
find . -name '*.prisma' -not -path '*/node_modules/*' | sort

# SQLAlchemy
rg -lE 'declarative_base|DeclarativeBase|class\s+\w+\s*\(.*Base' --type py -g '!.venv' . 2>/dev/null

# Django
find . -name 'models.py' -not -path '*/.venv/*' -not -path '*/site-packages/*'

# TypeORM/Mongoose
rg -lE '@Entity|@Schema\(|new mongoose\.Schema|mongoose\.model' --type ts -g '!node_modules' . 2>/dev/null

# Drizzle
rg -lE 'pgTable\(|mysqlTable\(|sqliteTable\(' --type ts -g '!node_modules' . 2>/dev/null

# GORM (Go structs with gorm: tags)
rg -lE 'gorm:"' --type go . 2>/dev/null

# Eloquent / ActiveRecord
find . -path '*/Models/*.php' -o -path '*/app/models/*.rb' 2>/dev/null

# Hibernate
rg -l '@Entity' --type java . 2>/dev/null
```

**Заполни:** `paths.schema_files` (явный список путей).

---

## Шаг 4 — Migration files

→ См. `prompts/00e_discover_migrations.md`.

---

## Шаг 5 — Pool config

```bash
rg -lE '(new\s+Pool\(|Pool\(\{|connectionLimit|max:\s*[0-9]+|pool_size|max_connections|HikariCP|DataSource)' \
   -g '!node_modules' -g '!.git' . 2>/dev/null | head -20
```

Прочитай каждый кандидат глазами:
```yaml
hints:
  pool_settings:
    file: packages/db/src/pool.ts
    lines: "10-16"
    max_connections: 20
    idle_timeout_ms: 30000
    shared_across_processes: 5
    notes: "Fixed across all PM2 processes"
```

---

## Шаг 6 — Modern 2026 patterns (новое в v3)

### 6.1. Vector DB indexes (AI/ML проекты)

```bash
# pgvector
rg -nE '(vector\([0-9]+\)|@db\.Vector|USING\s+(hnsw|ivfflat))' \
   -g '*.prisma' -g '*.sql' -g '*.py' -g '*.ts' . 2>/dev/null

# Pinecone / Chroma / Qdrant clients
rg -nE 'pinecone|chromadb|qdrant-client' \
   -g 'package.json' -g 'requirements*.txt' -g 'pyproject.toml' . 2>/dev/null
```

Если есть — заполни `hints.vector_db_indexes`.

### 6.2. Time-series tables

```bash
# TimescaleDB
rg -nE "create_hypertable\s*\(|SELECT\s+create_hypertable" \
   -g '*.sql' -g '*.py' -g '*.ts' . 2>/dev/null

# Native PG partitioning by RANGE (created_at)
rg -nE 'PARTITION BY RANGE\s*\(\s*created_at' -g '*.sql' . 2>/dev/null
```

Заполни `hints.time_series_tables`.

### 6.3. Sharding

```bash
# Citus / Vitess / app-level sharding
rg -nE '(create_distributed_table|shard_key|tenant_id|workspace_id)' \
   -g '*.{sql,py,ts,go}' -g '!node_modules' . 2>/dev/null | head -20
```

Заполни `hints.sharding_strategy`.

### 6.4. Multi-tenant isolation

```bash
# RLS policies (PG)
rg -nE 'CREATE\s+POLICY|ENABLE\s+ROW\s+LEVEL\s+SECURITY|FORCE\s+ROW\s+LEVEL' \
   -g '*.sql' -g '*.prisma' . 2>/dev/null

# Discriminator columns
rg -nE '\b(tenant_id|workspace_id|org_id|account_id)\b' \
   -g '*.prisma' -g '*.sql' . 2>/dev/null | head -30
```

Заполни `hints.multi_tenant_isolation`.

### 6.5. CDC / Outbox

```bash
# Debezium / Kafka Connect
rg -nE '(debezium|kafka-connect|outbox_table|outbox_event)' \
   -g '*.{ts,py,go,java,kt}' -g '!node_modules' . 2>/dev/null
```

Заполни `hints.cdc_outbox_pattern`.

---

## Шаг 7 — Deep-discovery sub-prompts

Загрузи и выполни строго по порядку:

1. **`prompts/00a_discover_money.md`** — money_columns + money_endpoints
2. **`prompts/00b_discover_transactions.md`** — transaction_sites
3. **`prompts/00c_discover_pii.md`** — pii_candidates + secret scan
4. **`prompts/00d_discover_n_plus_one.md`** — n_plus_one_candidates
5. **`prompts/00e_discover_migrations.md`** — migrations + dangerous_migrations

На каждом sub-prompt — заполни соответствующую секцию manifest.

---

## Шаг 8 — Mode

```bash
[ -n "${DATABASE_URL:-}" ] && echo "live possible" || echo "static"

# Read-only role check (если live)
if [ -n "${DATABASE_URL:-}" ]; then
  psql "$DATABASE_URL" -t -c "SELECT current_user, current_setting('default_transaction_read_only')"
fi
```

```yaml
mode:
  type: static  # или live
  live_db_url_env: DATABASE_URL
  read_only_role_required: true
  read_replica_url_env: ""        # опц.
  pg_stat_statements_enabled: false
  explain_top_n: 30
```

---

## Шаг 9 — Phase plan

Скопируй из `manifest.example.yml` и адаптируй:
- Если `hints.money_columns` пусто → `phase_plan."05b".skip_reason: "no money detected"`
- Если `mode.type == 'static'` → `phase_plan."04".inputs.explain_topN: false`

---

## Шаг 10 — Validate

→ См. `prompts/00z_validate_manifest.md`.

---

## Шаг 11 — Report

После прохождения validation gate:

> Discover complete. Manifest saved.
> Stack: <db>+<orm>, mode: <static|live>, size: <X>.
> hints: money_columns=N, transaction_sites=M, pii_candidates=K, n_plus_one_candidates=P, dangerous_migrations=Q.
> Recommend manual review of `audit/manifest.yml` before running phases.

**Не запускай run.sh сам.** Это решение пользователя.

---

## Якоря для отладки

Если discover выглядит «слишком быстрым»:
- На M-проекте полный discover должен занять 20-40 минут
- На L-проекте — 40-90 минут
- Если ты сделал за 5 минут — почти гарантированно что-то пропустил

Если ты в тупике на каком-то шаге — спроси пользователя. Это **разрешено и приветствуется**.
