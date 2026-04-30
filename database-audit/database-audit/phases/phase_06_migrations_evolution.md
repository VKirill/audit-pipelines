# PHASE 06 — MIGRATIONS & EVOLUTION

**Цель:** Проверить миграционный pipeline — обратимость, zero-downtime, безопасность под нагрузкой, версионирование, тестируемость.

**Источники:**
- Pramod Sadalage, Scott Ambler, *Refactoring Databases: Evolutionary Database Design* — главный источник.
- Forsgren, Humble, Kim, *Accelerate* — Ch. 8 Architecture (frequency of deploy ↔ архитектура БД).

---

## 1. Входы

- `evidence/01_inventory/migrations_list.md`.
- Сами файлы миграций (sample top-30 по dangerous keywords).

## 2. Что проверяешь

### 2.1. Инструмент миграции

Зафиксируй какой:
- Prisma Migrate, Drizzle Kit, TypeORM CLI, Sequelize CLI, Knex, Alembic (Python), Django migrations, Flyway, Liquibase, Atlas, Skeema, golang-migrate, Phinx (PHP), Doctrine Migrations, ActiveRecord Migrations, Diesel.

Каждый имеет свои best practices. Определи и сверяйся с doc этого инструмента.

### 2.2. Reversibility (Sadalage Part II)

- [ ] Каждая миграция имеет `down`/`rollback`?
- [ ] Если нет — это осознанный выбор (forward-only philosophy) или забытое?
- [ ] Если forward-only — есть стратегия отката? (rollback через новую миграцию).

Forward-only — валидный подход (особенно для большого prod), **но должен быть задокументирован**. Если не задокументирован — finding.

### 2.3. Dangerous DDL под нагрузкой

Это **ядро** фазы. Какие операции опасны:

| Операция | Что блокирует | Mitigation |
|----------|---------------|-----------|
| `ALTER TABLE … ADD COLUMN NOT NULL DEFAULT x` | в PG <11 — rewrite таблицы; в MySQL — instant с DEFAULT не всегда | Multi-step: ADD nullable → backfill → SET NOT NULL |
| `ALTER TABLE … DROP COLUMN` | блокирует ACCESS EXCLUSIVE | Сначала remove из кода, потом миграция (multi-step deploy) |
| `ALTER TABLE … RENAME COLUMN` | мгновенно, но ломает старые app-инстансы | Multi-step: add new → backfill → switch reads → switch writes → drop old |
| `CREATE INDEX` без `CONCURRENTLY` (PG) | блокирует записи на всё время | Использовать `CREATE INDEX CONCURRENTLY` |
| `DROP INDEX` без `CONCURRENTLY` | блокирует | `DROP INDEX CONCURRENTLY` |
| `CREATE UNIQUE INDEX CONCURRENTLY` + дубли | падает в конце на дублях | Заранее очистить дубли |
| `ALTER TABLE … ALTER COLUMN TYPE` | rewrite | Multi-step: add new column → backfill → switch → drop old |
| `ALTER TABLE … ADD CONSTRAINT … CHECK` | блокирует — проверяется на всех строках | `… NOT VALID` сначала, потом `VALIDATE CONSTRAINT` |
| `ALTER TABLE … ADD FOREIGN KEY` | блокирует | `… NOT VALID` + `VALIDATE` |

Запусти:
```bash
bash database-audit/scripts/find_migrations.sh > audit/evidence/06_migrations_evolution/dangerous_ddl.md
```

Скрипт сканит миграции на эти паттерны. Каждая dangerous DDL без mitigation → finding (severity зависит от размера таблицы).

### 2.4. Backfill стратегия

Sadalage Part VII: «Transformations».

- [ ] Если миграция меняет данные (UPDATE с условием на много строк) — сделана batched? (UPDATE … WHERE id BETWEEN N AND M, по 10k за раз).
- [ ] Backfill в одной транзакции на млн строк → блокирует БД.
- [ ] Idempotency backfill: если упало посередине, при повторе не сломает уже-обновлённое?

### 2.5. Multi-step deploy

Sadalage Part II–V: каждый refactoring разложен на безопасные шаги.

Пример **rename column**:
1. **Migration A:** ADD COLUMN new_name (nullable).
2. **App deploy 1:** код пишет в обе колонки (dual-write), читает из old_name.
3. **Migration B:** Backfill new_name = old_name для legacy строк.
4. **App deploy 2:** код читает из new_name, пишет в обе.
5. **Migration C:** SET NOT NULL на new_name (если применимо).
6. **App deploy 3:** код пишет только в new_name.
7. **Migration D:** DROP COLUMN old_name.

В аудите ищи:
- [ ] Миграции с RENAME — есть ли соответствующий многошаговый процесс?
- [ ] Миграции с DROP — был ли период когда колонка была неиспользуемой?

В одношаговых RENAME/DROP без подготовки → finding (high, риск падения при rolling deploy).

### 2.6. Тестируемость миграций

Karwin §23 косвенно: миграции — это код, который тестируется хуже всего.

- [ ] Миграции тестируются в CI? (apply на пустой БД).
- [ ] Apply + rollback + apply снова работает?
- [ ] Apply на копии prod (или представительном dataset) делается перед релизом?

### 2.7. Идемпотентность миграций

- [ ] `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` используется где разумно?
- [ ] Двойной apply миграции вызывает ошибку или работает?
- [ ] `DROP … IF EXISTS` против `DROP …` — стиль проекта?

### 2.8. Schema versioning

- [ ] Версия схемы фиксируется в БД (`schema_migrations` таблица)?
- [ ] Конфликт версий между ветками деплоя обнаруживается?
- [ ] Schema dump / snapshot экспортируется в репо?

### 2.9. Data fixtures

- [ ] Seeds (`prisma db seed`, Django fixtures) — есть для dev?
- [ ] Seeds случайно не запускаются в prod?
- [ ] Sensitive data (production-likeness) в dev fixtures — нет ли утечки PII?

### 2.10. Migration history rewrite

- [ ] Миграции не перезаписывались в истории git? (`git log --all -- migrations/`).
- [ ] Squashing миграций — был ли, в каком моменте?

## 3. Quotas

Минимум 3 findings (M-проект). Меньше — практически нереально, в любом >100-миграционном проекте есть мин 3 dangerous DDL без правильного multi-step.

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 06
```

Required evidence:
- `evidence/06_migrations_evolution/dangerous_ddl.md`
- `evidence/06_migrations_evolution/reversibility_audit.md`
- `evidence/06_migrations_evolution/multi_step_analysis.md`

## 5. Артефакты

- `audit/06_migrations_evolution.md`

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `paths.migration_files`, `hints.dangerous_migrations`

**Запуск:**
```bash
bash database-audit/run.sh phase 06
```

После детекторов агент дополняет `audit/06_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
