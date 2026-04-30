# Discover Phase — мастер-промт для ИИ

> **Это Stage 0 пайплайна. Твоя единственная задача — построить полную и проверенную карту БД-слоя проекта в файл `database-audit.manifest.yml`.**
>
> От качества этого файла зависят **все** остальные фазы. Детекторы НЕ ищут «где Prisma» — они читают манифест и сразу работают по точным путям. Если ты пропустил здесь money-колонку, в фазе 05b её не найдут.

---

## Правила поведения

1. **Read-only.** Никаких правок в коде проекта. Запись только в `database-audit.manifest.yml` и (опционально) `.serena/memories/db_audit_discover_log`.
2. **Точные пути.** Никаких glob-аппроксимаций там, где можно дать список файлов. Точный путь надёжнее.
3. **Точные строки.** Для каждого hint — `file:lines` диапазон, который ты сам прочитал.
4. **Никаких «возможно» и «обычно».** Если не уверен — помечай явно `unknown: true` с пояснением. Лучше пробел, чем ложное эхо.
5. **Stop при сомнении.** Если в проекте не находишь стандартных признаков ORM или схемы — **спроси пользователя** и подожди ответа. Не выдумывай.
6. **Sanity-thresholds.** Перед сохранением убедись:
   - если есть Prisma — `paths.schema_files` непустой
   - если в `package.json` есть слова `pay|wallet|balance|invoice|charge` — `hints.money_columns` непустой ИЛИ объяснено почему не применимо
   - если найдены workspaces — обходишь каждую

---

## Шаги

### Шаг 1 — Project skeleton

```bash
# Project root, type, workspaces
pwd
[ -f package.json ] && jq -r '.workspaces' package.json 2>/dev/null
[ -f pnpm-workspace.yaml ] && cat pnpm-workspace.yaml
[ -f lerna.json ] && jq -r '.packages' lerna.json 2>/dev/null
[ -f Cargo.toml ] && grep -A 20 '\[workspace\]' Cargo.toml
[ -f go.work ] && cat go.work

# Git state
git rev-parse HEAD 2>/dev/null
git rev-parse --abbrev-ref HEAD 2>/dev/null

# LOC class
find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.kt' -o -name '*.rb' -o -name '*.php' \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' -not -path '*/.venv/*' \
  | xargs wc -l 2>/dev/null | tail -1
```

**Заполни:** `project.{root, name, type, workspaces, size, loc, git_head, git_branch}`.

Размер (XS/S/M/L/XL) — по таблице из `01_ORCHESTRATOR.md §6` (max из LOC и models_count).

---

### Шаг 2 — Стек (ORM + БД)

#### 2.1. ORM detection

Для **каждой** ORM требуется **минимум 2 признака из 3**, иначе не считаешь её обнаруженной.

```bash
# В монорепо ВСЕГДА сканируй ВСЕ package.json, не только корневой
find . -name 'package.json' -not -path '*/node_modules/*' -exec grep -lE '"(@prisma/client|prisma|drizzle-orm|typeorm|sequelize|mongoose|knex|kysely|@mikro-orm)' {} \; 2>/dev/null

# Python
find . -name 'pyproject.toml' -o -name 'requirements*.txt' -o -name 'setup.py' \
  -not -path '*/.venv/*' -exec grep -lE '(sqlalchemy|django|tortoise|peewee|psycopg|asyncpg|pymongo)' {} \; 2>/dev/null

# Go
find . -name 'go.mod' -exec grep -lE '(gorm.io/gorm|jmoiron/sqlx|sqlc-dev/sqlc|uptrace/bun|entgo.io)' {} \; 2>/dev/null

# Schema files (визуальное подтверждение)
find . -name '*.prisma' -not -path '*/node_modules/*' 2>/dev/null
find . -name 'schema.py' -o -name 'models.py' -not -path '*/.venv/*' 2>/dev/null | head -20
find . -name '*.entity.ts' -not -path '*/node_modules/*' 2>/dev/null | head -20
find . -name '*.schema.ts' -not -path '*/node_modules/*' 2>/dev/null | head -20

# Schema directories
find . -maxdepth 5 -type d \( -name 'prisma' -o -name 'models' -o -name 'entities' -o -name 'schema' \) -not -path '*/node_modules/*'
```

#### 2.2. БД detection

Сначала автодетект:
```bash
# DSN patterns (env files и manifests, не код)
rg -nE 'postgres(ql)?://|mysql://|mariadb://|mongodb(\+srv)?://|redis://|sqlite:|sqlite3:' \
   --no-ignore -g '!node_modules' -g '!.git' -g '*.env*' -g '*.yml' -g '*.yaml' -g '*.json' -g '*.toml' \
   . 2>/dev/null

# Драйверы
grep -hE '"pg"|"mysql2"|"better-sqlite3"|"redis"|psycopg|asyncpg|pymongo' $(find . -name 'package.json' -name 'requirements*.txt' -name 'go.mod' -name 'Cargo.toml' -name 'composer.json' -not -path '*/node_modules/*' 2>/dev/null) 2>/dev/null
```

Если **множественные** БД — определи какая primary (та, в которой бизнес-данные; кэш и Redis обычно secondary).

**Заполни:** `stack.{primary_db, also_used_dbs, primary_orm, also_used_orms, orm_versions}`.

---

### Шаг 3 — Schema files (точный список)

**Принцип:** перечислить каждый файл, описывающий модели.

**Prisma:**
```bash
find . -name '*.prisma' -not -path '*/node_modules/*' | sort
```

**SQLAlchemy:**
```bash
# Файлы с declarative_base / Mapped / Column
rg -lE 'declarative_base|DeclarativeBase|Mapped\[|class\s+\w+\s*\(.*Base' --type py -g '!.venv' . 2>/dev/null
```

**Django:**
```bash
find . -name 'models.py' -not -path '*/.venv/*' -not -path '*/site-packages/*'
```

**TypeORM/Mongoose:**
```bash
rg -lE '@Entity|@Schema\(|new mongoose.Schema|mongoose.model' --type ts -g '!node_modules' . 2>/dev/null
```

**Drizzle:**
```bash
rg -lE 'pgTable\(|mysqlTable\(|sqliteTable\(' --type ts -g '!node_modules' . 2>/dev/null
```

**GORM:**
```bash
rg -lE 'gorm:"' --type go . 2>/dev/null
```

**Eloquent / ActiveRecord:**
```bash
find . -path '*/Models/*.php' -o -path '*/app/models/*.rb' 2>/dev/null
```

**Hibernate:**
```bash
rg -l '@Entity' --type java . 2>/dev/null
```

**Заполни:** `paths.schema_files` (явный список).

---

### Шаг 4 — Migration files

Migrations — **критическое** место. Тут чаще всего косячит автодетект (нестандартные локации).

**Алгоритм:**
1. Сначала спроси: **«Прочитал ли я README/docs проекта про миграции?»** Если нет — прочитай первым.
2. Проверь все классические места:
   ```bash
   for d in prisma/migrations migrations db/migrate database/migrations alembic alembic/versions \
            sql/migrations migration packages/*/migrations packages/*/db/migrations; do
     [ -d "$d" ] && find "$d" -type f \( -name '*.sql' -o -name '*.ts' -o -name '*.js' -o -name '*.py' -o -name '*.rb' \) | head -5
   done
   ```
3. Проверь **нестандартные паттерны** (как в vechkasov-стиле):
   ```bash
   # date-prefixed raw SQL files
   find . -type f -name '*.sql' -regextype posix-extended \
     -regex '.*/(20[0-9]{2}-[0-9]{2}-[0-9]{2}|[0-9]{14})_*.*\.sql' \
     -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null

   # version-prefixed files
   find . -type f -regextype posix-extended \
     -regex '.*/[Vv][0-9]+_+.*\.(sql|java)' -not -path '*/node_modules/*'
   ```
4. Если ничего нет — спроси: **«Где живут миграции? Atlas/Skeema declarative? Или DBA-applied вручную?»**

**Tool detection:**
- `prisma/migrations/` + `_prisma_migrations` → `prisma-migrate`
- `alembic/versions/` + `alembic.ini` → `alembic`
- `db/migrate/*.rb` + `Gemfile` с rails → `activerecord-migrations`
- `migrations/*.ts` + `drizzle.config.ts` → `drizzle-kit`
- raw `.sql` с date — `raw-sql-by-date`
- `atlas.hcl` / `schema.sql` declarative — `atlas`
- ничего не найдено — `unknown`, **спроси пользователя**

**Заполни:** `paths.migration_files.{tool, dirs, files}`. Если файлов <50 — пиши явный список. Если >50 — ограничься dirs + 10 примеров.

---

### Шаг 5 — Pool config files

```bash
# Поиск файлов с pool-конфигом
rg -lE '(new\s+Pool\(|Pool\(\{|connectionLimit|max:\s*[0-9]+|pool_size|max_connections|HikariCP|DataSource)' \
   -g '!node_modules' -g '!.git' . 2>/dev/null | head -20
```

Прочитай каждый кандидат глазами. Зафиксируй:
- `paths.pool_config_files` — список файлов
- `hints.pool_settings` — конкретные значения (max, idle_timeout, заметки)

Если pool разделён через PgBouncer/HikariCP — упомяни в `notes`.

---

### Шаг 6 — Money columns (КРИТИЧНО для phase 05b)

Это **самая важная** часть discover. Промах здесь = пропущенный critical в финале.

**Алгоритм:**
1. Прочитай **каждый** schema-файл из `paths.schema_files`.
2. Ищи колонки с подстроками в имени:
   ```
   balance, amount, total, sum, price, cost, fee, commission, payout, salary,
   wallet, refund, deposit, withdraw, charge, invoice, kop, rub, usd, eur,
   gbp, cny, jpy, btc, eth, sat
   ```
3. Также — слова вне «money», но возможно state-инвариант:
   ```
   stock, quantity, inventory, seats, tickets_left, reserved, available
   ```
4. Для **каждой** найденной — зафиксируй:
   - `table` (имя модели)
   - `file:lines` (точно)
   - `columns` (массив, если несколько связаны: `[amountRub, remainingRub, exchangeRate]`)
   - `type` — **точный DB-тип как объявлено** (`Float`, `DECIMAL(10,2)`, `Numeric`, `Int`, …)
   - `currency_hint` — если по имени видно (`RUB`, `USD`)
   - `classification` — `balance` / `price` / `fee` / `payout` / `exchange-rate` / `quantity` / `other`

**Quality bar:** если в коде есть слова `payment|invoice|wallet|charge` и `hints.money_columns` пустой — это, скорее всего, твой промах. Проверь повторно или явно объясни в `notes`.

**Заполни:** `hints.money_columns`.

---

### Шаг 7 — Transaction sites

Найди:
1. **Где транзакции есть** (для inventory).
2. **Где транзакций НЕТ, но должны быть** (это уже почти findings).

```bash
# Where transactions ARE
rg -nE '(\$transaction\(|\.transaction\(|\.startTransaction\(|with\s+transaction\.atomic|@transaction\.atomic|session\.begin\(|with_for_update|forUpdate\(|SELECT.*FOR\s+UPDATE|BEGIN\s+TRANSACTION|START\s+TRANSACTION)' \
   -g '!node_modules' -g '!.git' -g '!dist' -g '!build' \
   -g '*.{ts,tsx,js,jsx,mjs,cjs,py,go,rs,java,kt,rb,php}' \
   . 2>/dev/null

# Suspicious places (read-modify-write WITHOUT transaction)
# Грубый паттерн: SELECT/findFirst/findMany followed by UPDATE within same function
# — это требует реального чтения функций глазами
```

Для каждого транзакционного места — определи `kind`:
- `explicit-transaction` — явная `.transaction()`
- `missing-transaction` — read-modify-write без обёртки (главный источник critical)
- `external-io-inside-transaction` — fetch/HTTP/email внутри `$transaction` (Helland antipattern)
- `implicit-via-orm-batch` — `prisma.user.update()` одиночный, ORM сам атомизирует
- `row-lock-for-update` — `SELECT FOR UPDATE` или `with_for_update`
- `optimistic-version` — `@Version` или `version_column`

**Quality bar:** для проекта >50k LOC `transaction_sites` < 5 = подозрительно. Проверь.

**Заполни:** `hints.transaction_sites`.

---

### Шаг 8 — Raw SQL embedded в коде

```bash
rg -nE '(\$queryRaw|\$executeRaw|raw\(|sql`[^`]+`|connection\.query|db\.execute|cursor\.execute|createNativeQuery|createQuery)' \
   -g '!node_modules' -g '!.git' -g '!dist' \
   -g '*.{ts,tsx,js,jsx,mjs,cjs,py,go,rs,java,kt,rb,php}' \
   . 2>/dev/null
```

Для каждого — **прочитай контекст**, определи:
- `kind` (см. enum в schema)
- `uses_user_input` — попадает ли user input через интерполяцию (важно для phase 07 SQLi)

**Заполни:** `hints.raw_sql_in_code`.

---

### Шаг 9 — PII candidates

Из всех schema-файлов выяви колонки, попадающие под PII:

| Подстрока в имени | Classification |
|-------------------|----------------|
| `email`, `phone`, `address`, `name`, `birthday`, `dob` | non-sensitive |
| `ssn`, `passport`, `tax_id`, `national_id` | sensitive |
| `card`, `cvv`, `iban`, `swift`, `bank` | payment-card |
| `password`, `api_key`, `secret`, `token`, `credentials` | credentials |
| `gender`, `race`, `religion`, `health`, `medical` | special-category |
| `biometric`, `fingerprint` | biometric |

Для каждой:
- Зафиксируй `table`, `column`, `file:lines`, `type`
- `encrypted_at_rest` — попробуй определить по конфигу (если есть `pgcrypto`, app-side AES, иначе `false`)

**Заполни:** `hints.pii_candidates`.

---

### Шаг 10 — Money endpoints

Это **endpoints**, которые **меняют** money state. Связь с phase 05b.

```bash
# Поиск endpoints, делающих изменения над money колонками из шага 6
# Пример: для balanceRub
rg -nE '(balanceRub|amountRub|remainingRub|deductFromBalance|chargeBalance)' \
   -g '!node_modules' -g '!*.prisma' -g '!*.sql' \
   -g '*.{ts,tsx,js,py,go}' \
   . 2>/dev/null
```

Для каждого endpoint/функции:
- `route` (если HTTP)
- `mutation_kind`: debit / credit / transfer / charge / refund / mixed
- `has_idempotency_key` — есть ли `Idempotency-Key` header / `operation_id` параметр

**Заполни:** `hints.money_endpoints`.

---

### Шаг 11 — N+1 candidates (pre-validate)

Прогони базовый поиск:
```bash
# ORM-call inside loop — heuristic
rg -nE -B 5 '(prisma\.\w+\.\w+\(|\.findMany\(|\.findFirst\(|\.findOne\(|\.findById|\.objects\.|session\.query|\.find_by_)' \
   -g '*.{ts,py,go,rs,java,kt}' -g '!node_modules' . 2>/dev/null \
  | rg -B 0 -A 0 'for\s|forEach|\.map\(|while\s' | head -60
```

Для каждого suspect — **прочитай контекст глазами**:
- Действительно ли в loop?
- Зависит ли от итератора?
- Есть ли prefetch/include/joinedload родителем?

Зафиксируй только **подтверждённые ручной проверкой**. Не записывай 159 шумных матчей в манифест — это работа для phase 04 детектора, не для discover.

**Заполни:** `hints.n_plus_one_candidates` (рекомендую ≤ 30 топовых).

---

### Шаг 12 — Missing FK indexes

Если у тебя есть schema_files и они содержат FK-объявления — найди FK без индекса.

Это удобнее делать через `detectors/find_missing_fk_indexes.py` после init, но если успеешь — пред-наполни `hints.missing_fk_indexes`.

---

### Шаг 13 — Dangerous migrations

Из `paths.migration_files`:

```bash
# Ищи опасные DDL — пройдись по каждому migration файлу
for f in <migration files>; do
  rg -nE 'DROP\s+(TABLE|COLUMN|INDEX|CONSTRAINT)' "$f"
  rg -nE 'ALTER\s+(COLUMN|TABLE).*?(TYPE|RENAME)' "$f"
  rg -nE 'ADD\s+COLUMN.*NOT\s+NULL\s+DEFAULT' "$f"
  rg -nE 'CREATE\s+(UNIQUE\s+)?INDEX' "$f" | rg -v 'CONCURRENTLY'
  rg -nE 'TRUNCATE|UPDATE\s+\w+\s+SET' "$f"
done
```

Для каждой опасной операции — `kind` из enum.

**Заполни:** `hints.dangerous_migrations`.

---

### Шаг 14 — Mode

```bash
# Проверь DATABASE_URL
[ -n "${DATABASE_URL:-}" ] && echo "live mode possible" || echo "static mode"
```

Если есть `DATABASE_URL` — **подтверди read-only роль** перед фиксацией:
```bash
psql "$DATABASE_URL" -t -c "SELECT current_user, current_setting('default_transaction_read_only')"
```

**Заполни:** `mode.{type, live_db_url_env, read_only_role_required}`.

---

### Шаг 15 — Phase plan

Скопируй `phase_plan` из `manifest.example.yml` и адаптируй:
- Если `hints.money_columns` пустой и в проекте действительно нет денег → `phase_plan."05b".skip_reason: "no money detected"`.
- Если `mode.type == 'static'` → у `phase_plan."04".inputs.explain_topN: false`.

---

### Шаг 16 — Валидация манифеста

```bash
python3 database-audit/validators/validate_manifest.py database-audit.manifest.yml
```

Скрипт проверит:
- Соответствие JSON Schema
- Sanity thresholds (Prisma → schema_files непустой; деньги в коде → money_columns непустой)
- Все `file` пути из hints резолвятся

Exit 0 = ok. Иначе — исправь и повтори.

---

## Sanity gate перед финалом

Прежде чем закончить discover-фазу, **сам проверь себя**:

1. [ ] Если стек = monorepo → я обошёл каждый workspace?
2. [ ] Если в коде есть слова `pay|wallet|balance|charge|invoice` → у меня непустой `money_columns`?
3. [ ] Если стек = Prisma → у меня перечислены все `*.prisma` файлы?
4. [ ] Если найдены миграции → определил `tool` и не оставил `unknown`?
5. [ ] Каждое `file:lines` я **сам прочитал**, не угадал по имени?
6. [ ] Если `mode = live` → подтвердил read-only роль?
7. [ ] `validate_manifest.py` exit 0?

Если хоть один пункт нет — **не сохраняй**. Доработай.

---

## Что дальше

После того как `database-audit.manifest.yml` создан и валиден:
1. Сообщи пользователю одну строку: «Discover complete. Manifest saved. Recommend manual review before running phases.»
2. Жди подтверждения от пользователя.
3. По команде «run phases» — переходи на `prompts/phase_NN_*.md` инструкции (читать из `prompts/`).

Не запускай `run.sh` сам — это решение пользователя после ревью манифеста.
