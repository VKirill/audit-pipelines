# CHANGELOG

## v3 (2026-04-30) — Production-grade hardening

Финальная итерация. Идеальный manifest-driven pipeline для production-уровня аудита.

### Архитектурно

- **Chunked discovery** — `prompts/00_discover.md` стал orchestrator, deep work делегирован в:
  - `prompts/00a_discover_money.md` (money columns + endpoints)
  - `prompts/00b_discover_transactions.md` (transactions + race candidates)
  - `prompts/00c_discover_pii.md` (PII + secrets)
  - `prompts/00d_discover_n_plus_one.md` (N+1 candidates)
  - `prompts/00e_discover_migrations.md` (migrations + dangerous DDL)
  - `prompts/00z_validate_manifest.md` (self-validation gate)
  - `prompts/refresh.md` (для `init.sh --refresh`)

- **Modern hint categories** в manifest:
  - `vector_db_indexes` — pgvector / pinecone / qdrant
  - `time_series_tables` — TimescaleDB / native partitioning
  - `sharding_strategy` — Citus / Vitess / app-level
  - `multi_tenant_isolation` — RLS / discriminator / schema-per-tenant
  - `cdc_outbox_pattern` — Debezium / outbox / event-sourcing

- **Live mode preflight** — `validators/preflight.py` проверяет DSN, client, read-only role до запуска фаз.

- **`init.sh --refresh`** — incremental update existing manifest вместо полного re-discover.

- **`viewer/index.html`** — интерактивный HTML просмотр findings (фильтры, expand evidence). Открывается локально или через `python3 -m http.server`.

### Детекторы

- **`extract_schema.py`** — поддерживает 11 ORM:
  - Prisma, SQLAlchemy, Django, TypeORM, Drizzle, **Mongoose**, **Sequelize**, **GORM**, **ActiveRecord** (Rails schema.rb), **Hibernate**, raw SQL
  - Раньше — 5 ORM
- **`find_n_plus_one.py`** — confidence ranking:
  - `high` — orm-call в for-loop с iterator-зависимым аргументом
  - `medium` — `Promise.all(map())`, async iterator, неясная зависимость
  - `low` — orm-call в loop без iterator dependency (likely false positive)
- **`synthesize_roadmap.py`** — auto-TL;DR на основе severity × category counts
- **`find_money_floats`** — теперь идемпотентен через дедупликацию на уровне fingerprint

### Дедупликация

- **Category-based ID**: `DB-MONEY-001`, `DB-IDX-042`, `DB-TX-007` вместо глобальной нумерации
- **Fingerprint dedup**: одна и та же `(category, file, db_object, lines)` даёт **одно** finding, повторный append возвращает `None`
- Это решает проблему v2 где `find_money_floats` запускался в фазах 02 и 05b и создавал дубли

### Новая литература

- **`REFERENCE_2026_STATE_OF_ART.md`** — обновлённые источники:
  - Alex Petrov *Database Internals* (2019)
  - Andy Pavlo CMU 15-445/15-721 lectures (2024-2025)
  - Mihalcea *High Performance Java Persistence* (3rd ed, 2024)
  - Dimitri Fontaine *The Art of PostgreSQL* (2nd ed, 2020)
  - Hans-Jürgen Schönig *Mastering PostgreSQL 15* (2023)
  - Modern tools: pgroll, Atlas, Reshape, Squawk, pgAnalyze, pixie, eBPF
  - DSPM tools для PII discovery
  - NIST SP 800-218 (replaces SP 800-122 для secure software)
  - Annie Duke *Thinking in Bets* (2018) — для adversary review

### Lib

- **`lib/id_gen.py`** — category-aware ID + fingerprint
- **`lib/stack_aware.py`** — regex patterns по ORM (transaction, raw SQL, lazy-load) — детекторы используют один источник вместо хардкода
- **`lib/manifest_lib.py`** — `append_finding(dedup=True)`, `already_exists()`

### Validators

- **`preflight.py`** — НОВЫЙ — live mode preflight
- `validate_manifest.py` — strict mode + расширенные sanity checks (vector/timeseries/sharding/multi-tenant)

### Schema

- `manifest.schema.yml` v3 — расширен под 2026 patterns
- `refresh_state` секция — для `--refresh` bookkeeping

### Совместимость

- v1 и v2 manifest читаются (read-only)
- findings.jsonl формат остался совместим
- ROADMAP.md, _meta.json не сломаны для downstream консьюмеров

---

## v2 (2026-04-30) — Manifest-driven architecture

См. ниже. Главное:
- ИИ при init заполняет manifest, детекторы потом работают по нему
- Решило проблему монорепо / нестандартных путей из v1

## v1 (2026-04-30) — Initial release

11 фаз + 2 мини. Эвристические детекторы. См. early commits.
