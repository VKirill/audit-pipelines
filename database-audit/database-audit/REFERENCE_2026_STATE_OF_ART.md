# REFERENCE — 2026 state-of-art DB engineering

Источники последних 5 лет, на которых базируется v3.

---

## Foundations (книги, которые читать обязательно)

### Alex Petrov — *Database Internals* (O'Reilly, 2019)
Парный к Kleppmann. Глубокая декомпозиция storage engines (B-tree, LSM, BW-tree), distributed coordination (Raft, Paxos), CRDT.
- Ch. 1-7: storage internals (relevant phase 03, 08)
- Ch. 8-13: distributed (relevant phase 05, 08)

### Andy Pavlo — CMU 15-445 / 15-721 lectures (CMU Database Group)
**Самый актуальный курс по БД 2024-2025.** 15-445 = intro, 15-721 = advanced.
Темы:
- Modern storage (DuckDB, Velox, Photon)
- Vectorized execution
- HTAP (PostgreSQL + ClickHouse merging)
- Large-table operations under load

URL: https://15445.courses.cs.cmu.edu / 15721.courses.cs.cmu.edu

### Laine Campbell, Charity Majors — *Database Reliability Engineering* (O'Reilly, 2017)
DBRE = SRE для БД. Ch. 4 (Operational Visibility) и Ch. 7 (Backup) — основа phase 09.

### Dimitri Fontaine — *The Art of PostgreSQL* (2nd ed, 2020)
Современный PG-style. Window functions, JSON-ops, extensions ecosystem.

### Hans-Jürgen Schönig — *Mastering PostgreSQL 15* (Packt, 2023)
Практика от консультанта Cybertec. Tuning, replication, monitoring, BRIN indexes for time-series.

---

## ORM patterns (modern + battle-tested)

### Vlad Mihalcea — *High Performance Java Persistence* (3rd ed, 2024)
Обновлено под Hibernate 6, Spring Boot 3.x. Глава 16 (CDC + Outbox), Ch. 14 (Optimistic locking with @Version).

### Eloquent / ActiveRecord patterns (community)
- Jeffrey Way — Laracasts «Eloquent Performance Patterns» (2024)
- Aaron Patterson — «Active Record Performance» talks (RailsConf 2023)

### Modern TypeScript ORMs comparison (2024+)
- **Drizzle vs Prisma** benchmarks: prisma больше features, drizzle ближе к SQL
- **Kysely** — type-safe SQL builder, нет схемы, query builder
- **MikroORM** — DataMapper pattern, identity map (как Doctrine)

---

## Distributed & cloud-native (2024+)

### Citus / pg_dist (Microsoft Azure Database for PostgreSQL)
PostgreSQL extension для horizontal sharding. Обновлено в 2024 — поддерживает PG 16+.

### TimescaleDB 2.13+ (2024)
- Continuous aggregates на hypertables
- Compression (10x reduction on time-series)
- Native columnar storage в hypertables

### CockroachDB v23.x (2024)
SERIALIZABLE по умолчанию, geo-distributed. Хороший пример «correctness-first» дизайна.

### Yugabyte / TiDB
Distributed SQL — PG/MySQL wire-compatible, Spanner-style.

---

## Modern migration tools (2026 alternatives to classics)

### Atlas (atlasgo.io) — schema-as-code
Декларативный schema management. Hashicorp-style HCL или SQL. Diff и плановое применение.

### pgroll (Xata, 2024) — zero-downtime PG migrations
Делает многошаговый rollout автоматически. Решает RENAME COLUMN / ALTER TYPE без блокировок.

### Reshape (Fabian Lindfors, 2023)
Аналог pgroll. Использует PG views для multi-version schema.

### dbmate / migrate (CLI)
Простые tools без ORM-зависимости. Всегда reversible.

### Squawk (Square, 2024)
Lint для PG migration files. Ловит dangerous DDL до прода.

---

## Observability 2026

### pgAnalyze, pganalyze.com
Continuous query intelligence. EXPLAIN history + index recommendations + log analysis.

### pg_stat_kcache (PG extension)
Per-statement disk/CPU stats. Дополняет pg_stat_statements.

### auto_explain (PG built-in)
Logs slow queries with full plan automatically.

### OpenTelemetry для DB
- otel-collector + receivers для Postgres/MySQL/Mongo
- Vendor: Datadog DB Monitoring, New Relic, Honeycomb

### eBPF для DB observability
- pixie.io (PG/MySQL trace без code changes)
- BPF tools для disk IO

---

## Vector DBs / AI integration (новое в 2024+)

### pgvector (Supabase, 2023+)
PG extension для vector embeddings. HNSW + IVFFlat indexes.

### Lance (lancedb.com, 2024)
Columnar vector DB на Apache Arrow.

### Modern best practice: hybrid search
Embedding similarity + full-text + filtering — все в одном запросе.

См. подходы:
- Marqo (open-source, 2023)
- Vespa (Yahoo, modern docs 2024)

---

## Security 2026

### NIST SP 800-218 — *Secure Software Development Framework v1.1* (2022)
Замена SP 800-122 для PII. SSDF practices для DB security.

### OWASP Database Security Cheat Sheet (last update 2024)
- TLS 1.3 only
- Postgres SCRAM-SHA-256 (replaces md5)
- Cloud-managed secret rotation (AWS RDS Master Key, Azure Key Vault)

### DSPM (Data Security Posture Management) — 2024+
Категория продуктов: Cyera, Sentra, Symmetry — автоматическая PII discovery и lineage.

### GDPR Article 25 — *Data Protection by Design and by Default*
Не новое, но строже трактуется в 2024+ enforcement (см. cases CNIL, Garante).

---

## Money & precision (specifics для phase 05b)

### "Falsehoods Programmers Believe About Prices" — Patrick McKenzie
Список edge cases (currencies, rounding, tax/VAT, B2B vs B2C).

### Stripe & PCI-DSS docs (2024+)
Идемпотентность как обязательная. Idempotency-Key header → unique constraint в БД.

### Even-cents rule (banking)
Все money — integer minor units (cents/копейки). DECIMAL(p,s) только для отображения.

---

## Performance benchmarks 2024+

### TPC-H, TPC-DS — классика, всё ещё актуальна

### CH-benCHmark (HTAP)
TPC-H + TPC-C combined для HTAP-баз.

### YCSB (Yahoo!) — обновлено в 2024
Для NoSQL и distributed SQL.

---

## Когнитивные ошибки и meta-аудит

### Daniel Kahneman — *Thinking, Fast and Slow* (2011) — основа
Anchoring (§11), Overconfidence (§24).

### Annie Duke — *Thinking in Bets* (2018)
Когда «pass» решение и когда «fail» — probabilistic decision making, applied to data integrity calls.

### Forsgren, Humble, Kim — *Accelerate* (2018) + *DORA Report 2024*
Связь архитектуры БД с deployment frequency. Используется в phase 06 для оценки migration tool maturity.

---

## Где какая литература применяется в фазах v3

| Phase | 2026 источники |
|-------|----------------|
| 02 schema | Petrov Ch. 1-3, Karwin §9, Stripe docs (для money) |
| 03 indexes | Pavlo CMU 15-445 lectures, Smith Ch. 7, pgAnalyze blog |
| 04 queries | Mihalcea (3rd ed) Ch. 10, pganalyze case studies |
| 05 transactions | Petrov Ch. 12-13, CockroachDB docs, Mihalcea Ch. 14 |
| 05b money | McKenzie blog, Stripe Idempotency docs, Banking integer-cent rule |
| 06 migrations | pgroll docs, Atlas docs, Squawk rules, Sadalage (foundation) |
| 07 security | NIST SP 800-218, OWASP 2024, DSPM tools |
| 08 perf/scaling | TimescaleDB 2024, Citus docs, Schwartz (4th ed) |
| 09 ops | DBRE, pganalyze, OpenTelemetry collector docs |
| 10a self-audit | Annie Duke + Kahneman |
