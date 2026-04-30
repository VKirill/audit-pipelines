# CHANGELOG

## v1 (2026-04-30) — Initial release

Первый релиз Database Audit Pipeline. Архитектурно зеркалит `codebase/v3`:
- 11 основных фаз + 2 мини (05b money, 10a self-audit) + 1 опциональная (11 deep-dive)
- Детерминированные `validate_phase.sh` / `finalize.sh` как hard gates
- Обязательные `confidence_rationale` (для high) и `exploit_proof` (для critical)
- Static-mode (без подключения к БД) и live-mode (с `DATABASE_URL`) — оба полностью рабочие
- 11 детектор-скриптов в `scripts/` для статической части
- Anti-recursion на инструментах, fallback-протоколы для Serena/GitNexus

### Скрипты-детекторы

- `detect_db_stack.sh` — Prisma / Drizzle / TypeORM / Sequelize / Mongoose / Knex / Kysely / SQLAlchemy / Django / Tortoise / GORM / sqlx / sqlc / Eloquent / Doctrine / ActiveRecord / Hibernate / Diesel
- `extract_schema_summary.sh` — нормализованная сводка схемы из манифестов ORM или SQL-миграций
- `extract_query_inventory.sh` — каталог raw SQL и ORM-вызовов
- `find_n_plus_one.sh` — эвристика «query внутри loop»
- `find_missing_indexes.py` — FK без индекса (по схеме)
- `find_select_star.sh` — `SELECT *` usage
- `find_string_concat_sql.sh` — SQLi surface (interpolation в raw SQL)
- `find_transactions.sh` — паттерны транзакций, isolation level mentions
- `find_migrations.sh` — миграции, обратимость, dangerous DDL
- `live_db_probe.sh` — (опц.) `EXPLAIN`, `pg_stat_user_indexes`, `pg_stat_statements`, MySQL `INFORMATION_SCHEMA`

### Привязка к книгам

Каждая фаза цитирует конкретные главы:
- Date — *Database Design and Relational Theory* (фаза 02)
- Karwin — *SQL Antipatterns* (фазы 02, 04)
- Celko — *SQL for Smarties*, *SQL Programming Style* (фазы 02, 04)
- Winand — *Use the Index, Luke* / *SQL Performance Explained* (фаза 03)
- Schwartz et al. — *High Performance MySQL* (фаза 08)
- Smith — *PostgreSQL High Performance* (фаза 08, 09)
- Sadalage & Ambler — *Refactoring Databases* (фаза 06)
- Kleppmann — *Designing Data-Intensive Applications* (фазы 05, 08)
- Mihalcea — *High Performance Java Persistence* (фаза 04, N+1)
- Helland — *Life Beyond Distributed Transactions* (фаза 05, идемпотентность)
- Bernstein & Newcomer — *Principles of Transaction Processing* (фаза 05)
- Sadalage & Fowler — *NoSQL Distilled* (Mongo-ветви)
