# PHASE 01 — INVENTORY

**Цель:** Получить полную нейтральную картину «что есть в БД-слое». На этой фазе ничего не оцениваем, только описываем.

**Источники:**
- Feathers, *Working Effectively with Legacy Code* — characterization before change.
- Sadalage & Ambler, *Refactoring Databases* — Part I, «Database Inventory».

---

## 1. Входы

- `audit/00_setup.md`, `.serena/memories/db_audit_phase_00`.
- `evidence/00_setup/stack_detection.txt`.
- `evidence/01_inventory/*` от `run_external_tools.sh`.

## 2. Чек-лист действий

### 2.1. Каталог БД и схем
- [ ] Сколько физических БД? Какие схемы внутри (если PG — schemas, если Mongo — databases)?
- [ ] Зафиксируй версии: `SELECT version()` (live) или из `package.json`/`requirements.txt` (драйвер).
- [ ] Multi-tenancy? schema-per-tenant / row-level / database-per-tenant — зафиксируй паттерн.

### 2.2. Каталог моделей / таблиц

Источники (по стекам):

| ORM/Stack | Где смотреть |
|-----------|--------------|
| Prisma | `prisma/schema.prisma` — модели + DMMF из `prisma generate` |
| Drizzle | `drizzle/schema.ts` или `*/schema.ts` |
| TypeORM | `**/*.entity.ts` |
| Sequelize | `models/*.js` или `models/index.js` |
| Mongoose | `**/*.schema.ts`, `**/*.model.ts` |
| SQLAlchemy | модели наследующие `Base` (declarative) или `Table()` |
| Django | `**/models.py` |
| GORM | структуры с тегами `gorm:` |
| Eloquent | `app/Models/*.php` |
| ActiveRecord | `app/models/*.rb` |
| Hibernate | `@Entity` классы |
| raw SQL only | сами `*.sql` миграции |

- [ ] Через `extract_schema_summary.sh` получи плоский список:
  ```
  table_name | columns_count | has_pk | has_fk_count | indexes_declared | source_file:line
  ```
- [ ] Зафиксируй топ-10 самых широких таблиц (>20 колонок) — кандидаты для phase 02.
- [ ] Зафиксируй таблицы без PK — кандидаты для phase 02 critical.

### 2.3. Каталог миграций

- [ ] Через `find_migrations.sh` получи:
  ```
  migration_id | timestamp | filename | up_size_lines | down_size_lines | dangerous_keywords
  ```
- [ ] Посчитай: сколько миграций, сколько reversible (есть `down`), сколько содержат опасные DDL (DROP TABLE/COLUMN/INDEX, ALTER TABLE без `IF EXISTS`).
- [ ] Самая старая и самая свежая миграция — даты.
- [ ] Распределение миграций по времени: были ли «дни без миграций» = деплой с правками вручную в проде?

### 2.4. Каталог запросов

Через `extract_query_inventory.sh` собери:

**Raw SQL:**
- `*.sql` файлы (seeds, fixtures, отчёты).
- Строки в коде: `prisma.$queryRaw`, `db.execute`, `connection.query`, `cursor.execute`, `EntityManager.createNativeQuery`.

**ORM-вызовы:**
- `prisma.<model>.<method>` (count by method)
- `Model.objects.<method>` (Django)
- `Repository.<method>` (TypeORM)
- `db.session.query` (SQLAlchemy)
- `Model.findById/findAll` (Sequelize/Mongoose)

Зафиксируй:
- Топ-20 наиболее часто используемых ORM-вызовов (count + примеры).
- Топ-20 raw SQL-фрагментов (по длине / по уникальности).
- Использование raw SQL внутри ORM-проекта (smell? умысел?).

### 2.5. Каталог транзакций

Через `find_transactions.sh`:
- Где явно открываются транзакции? (`BEGIN`, `prisma.$transaction`, `db.session.begin`, `with transaction.atomic()`, `@Transactional`).
- Где используется явный isolation? (`SET TRANSACTION ISOLATION LEVEL`, `Isolation.Serializable`, `with_isolation_level`).
- Где используются row-level locks? (`SELECT FOR UPDATE`, `pessimistic_lock`, `with_for_update`).

Это вход для phase 05. Сейчас — только опись.

### 2.6. Каталог конфигурации

- [ ] Connection-параметры: pool size, max connections, timeout. Где конфиг (env var, code default, ORM config)?
- [ ] Replication / read-replicas — есть, нет, упоминания?
- [ ] Кэш-слой (Redis, Memcached) поверх БД?
- [ ] CDN/edge-cache, который кэширует запросы?

## 3. Размерные классы

В конце фазы зафиксируй:

| Категория | Кол-во |
|-----------|--------|
| Databases | 1 |
| Schemas | 1 |
| Tables/Models | 42 |
| Tables без PK | 0 |
| Migrations total | 87 |
| Migrations с DROP/ALTER danger | 6 |
| Raw SQL fragments | 12 |
| ORM call sites | 487 |
| Explicit transactions | 14 |
| FOR UPDATE locks | 3 |

В `.serena/memories/db_audit_phase_01`.

## 4. Findings

В этой фазе минимум 0 findings (фаза описательная). Но если **по факту описи** обнаружены кричащие проблемы (таблица без PK, DROP TABLE без `IF EXISTS`, raw SQL с `+ user_input +`), фиксируй их сразу как low/medium с пометкой «требует углубления в фазе NN».

## 5. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 01
```

## 6. Артефакты

- `audit/01_inventory.md`
- `audit/evidence/01_inventory/schema_summary.json`
- `audit/evidence/01_inventory/models_list.md`
- `audit/evidence/01_inventory/migrations_list.md`
- `audit/evidence/01_inventory/queries_inventory.md`
- `audit/evidence/01_inventory/transactions_list.md`
- `audit/evidence/01_inventory/config_summary.md`

---

## Manifest workflow

**Какие manifest-секции читает эта фаза:** `stack`, `paths.schema_files`, `paths.migration_files`, `paths.query_files`

**Запуск:**
```bash
bash database-audit/run.sh phase 01
```

После детекторов агент дополняет `audit/01_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
