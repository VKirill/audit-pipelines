# PHASE 00 — SETUP

**Цель:** Подготовить окружение, детектировать стек БД и ORM, опционально установить read-only подключение к БД, прогнать `run_external_tools.sh`.

**Источник:** общие инженерные практики; SRE Book §26 «Data Integrity».

---

## 1. Входы

- Путь к проекту (от пользователя).
- Установленные `serena` и `gitnexus`.
- Опционально: `DATABASE_URL` в env (read-only роль).

## 2. Чек-лист действий

### 2.1. Базовые проверки
- [ ] Путь проекта существует (`list_dir`).
- [ ] Это git-repo: `git rev-parse --is-inside-work-tree`. Если нет — фазы 06 и 09 частично деградируют.
- [ ] Зафиксируй HEAD: `git rev-parse HEAD`, ветку `git rev-parse --abbrev-ref HEAD`.

### 2.2. Структура артефактов
- [ ] Создай `audit/`, `audit/evidence/`, `.serena/memories/`.
- [ ] Создай пустой `audit/findings.jsonl`.

### 2.3. Serena
- [ ] `check_onboarding_performed`. Если нет — `onboarding`.
- [ ] `activate_project`.
- [ ] Проверь `.serena/project.yml` → `read_only: true`. Если нет — поправь (это единственная правка вне `audit/`/`memories/`).
- [ ] `get_current_config` — версия, язык, активный проект → в memory.

### 2.4. Детект стека (главное в этой фазе)

Запусти:
```bash
bash database-audit/scripts/detect_db_stack.sh > audit/evidence/00_setup/stack_detection.txt
```

Скрипт ищет признаки:
- **Prisma:** `prisma/schema.prisma`, `@prisma/client` в `package.json`
- **Drizzle:** `drizzle.config.ts`, `drizzle-orm` в deps
- **TypeORM:** `typeorm` в deps, `*.entity.ts` файлы
- **Sequelize:** `sequelize` в deps
- **Mongoose:** `mongoose` в deps, `*.schema.ts`/`*.model.ts`
- **SQLAlchemy:** `sqlalchemy` в `requirements.txt`/`pyproject.toml`
- **Django ORM:** `django` + `models.py`
- **GORM (Go):** `gorm.io/gorm` в `go.mod`
- **sqlx/sqlc (Go):** `jmoiron/sqlx`, `kyleconroy/sqlc` в `go.mod`
- **Eloquent (Laravel):** `database/migrations/`, `app/Models/`
- **Doctrine:** `composer.json` с `doctrine/orm`
- **ActiveRecord (Rails):** `Gemfile` с `rails`
- **Hibernate:** `pom.xml`/`build.gradle` с `hibernate-core`, `*.entity.java`
- **Diesel (Rust):** `diesel` в `Cargo.toml`

И целевой БД:
- Postgres / MySQL / MariaDB / SQLite / MongoDB / Redis / Elasticsearch / ClickHouse / DynamoDB
по DSN в env-файлах, по драйверам, по миграциям.

Если детектится несколько ORM или несколько БД — это норма для микросервисного монорепо. Все отмечаются.

### 2.5. Ручное подтверждение стека

Если автодетект пуст или вызывает сомнения — **спроси пользователя**:
- «Я не вижу очевидной ORM. Какая БД и каким драйвером она используется?»

Зафиксируй ответ в `audit/00_setup.md` секция «Stack manual confirmation».

### 2.6. Live-mode проверка (опционально)

Если `DATABASE_URL` задан:
- [ ] `psql --version` / `mysql --version` / `mongosh --version` доступен.
- [ ] **Подтверждение read-only:**
  - Postgres: `psql "$DATABASE_URL" -c "SELECT current_user, current_setting('default_transaction_read_only')"`.
  - MySQL: `mysql -e "SELECT CURRENT_USER(), @@transaction_read_only"`.
  - Mongo: `mongosh "$DATABASE_URL" --eval 'db.runCommand({connectionStatus:1}).authInfo.authenticatedUserRoles'` — должны быть только read-роли.
- [ ] Если роль НЕ read-only — отказ от live-mode, переход в static-only с записью в `audit/00_setup.md`.

### 2.7. Размер проекта

Из `evidence/00_setup/stack_detection.txt` определи:
- LOC через `cloc` или fallback (см. ORCHESTRATOR §7.4).
- Кол-во моделей (приблизительно — кол-во `class` в `models.py` / `model` в `schema.prisma` / `Entity` в `*.entity.ts`).
- Кол-во миграций (файлы в `migrations/`/`db/migrate/`).

Запиши в `.serena/memories/db_audit_phase_00`:
```yaml
- size: M           # XS|S|M|L|XL — наибольший из (LOC, models)
- loc: 47000
- models: 42
- migrations: 87
- databases: [postgresql]
- orms: [prisma]
- mode: live        # или static
- read_only_role_confirmed: true
```

### 2.8. Запуск внешних инструментов

```bash
bash database-audit/scripts/run_external_tools.sh
```

Скрипт прогоняет все детекторы, парсит схему, миграции, опционально дёргает live-DB. Результат — в `audit/evidence/`. Это **первый и единственный раз**, когда ты вызываешь этот скрипт. Дальше используешь evidence.

## 3. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 00
```

Проверяет:
- `audit/00_setup.md` существует и содержит секции: Stack, Mode, Size.
- `evidence/00_setup/stack_detection.txt` непустой.
- `.serena/memories/db_audit_phase_00` содержит обязательные ключи.

## 4. Артефакты

- `audit/00_setup.md` — отчёт фазы.
- `audit/evidence/00_setup/stack_detection.txt`
- `audit/evidence/00_setup/git_stats.txt`
- `audit/evidence/00_setup/live_db_handshake.txt` (если live)
- `.serena/memories/db_audit_phase_00`
- `.serena/memories/db_audit_progress`

## 5. Что НЕ делаешь в этой фазе

- Не оцениваешь схему — это phase 02.
- Не читаешь миграции глубоко — это phase 06.
- Не делаешь EXPLAIN — это phase 04.

Фаза 00 = только описание ландшафта.

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** (нет — этап делает init.sh)

**Запуск:**
```bash
bash database-audit/run.sh phase 00
```

После детекторов агент дополняет `audit/00_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
