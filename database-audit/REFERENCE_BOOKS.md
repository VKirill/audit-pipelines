# REFERENCE — книги и источники

Каждая фаза ссылается на конкретные главы. Это не «потому что круто звучит» — это якоря, к которым привязаны проверки и рекомендации.

---

## Дизайн схемы и реляционная теория

### C.J. Date — *Database Design and Relational Theory* (2nd ed., 2019)
- §3 «Predicates and Propositions» — типы и nullability
- §6 «Normalization Up to BCNF» — фаза 02
- §7 «Higher Normal Forms (4NF, 5NF)» — фаза 02 для агрегатных моделей
- §10 «Constraints» — фаза 02

### Joe Celko — *SQL Programming Style* (2005)
- §1 Naming Data Elements — фаза 02 (naming convention)
- §2 Fonts, Punctuation, Spacing — стиль SQL в коде
- §4 Scales and Measurements — типы для money/quantity
- §5 Data Encoding Schemes — enum vs lookup table

### Joe Celko — *SQL for Smarties* (5th ed.)
- §2 Auxiliary Tables — паттерны calendar/numbers
- §6 Set Theory — set-based мышление vs row-by-row (фаза 04)
- §10 Hierarchies — adjacency list vs nested set vs path enum (фаза 02 для деревьев)

### Bill Karwin — *SQL Antipatterns: Avoiding the Pitfalls of Database Programming* (2010)
**Главный источник для phase 02 и 04.** 25 антипаттернов:
- §1 Jaywalking (CSV в одном поле) — фаза 02
- §2 Naive Trees (Adjacency List) — фаза 02
- §3 ID Required (PK по привычке) — фаза 02
- §4 Keyless Entry (отсутствие FK) — фаза 03
- §5 Entity-Attribute-Value — фаза 02
- §6 Polymorphic Associations — фаза 02
- §7 Multicolumn Attributes — фаза 02
- §8 Metadata Tribbles (table-per-tenant) — фаза 02
- §9 Rounding Errors (FLOAT для денег) — фаза 02, 05b
- §10 31 Flavors (избыточный varchar для enum) — фаза 02
- §11 Phantom Files (BLOB в БД vs файлы) — фаза 02
- §12 Index Shotgun — фаза 03
- §13 Fear of the Unknown (NULL handling) — фаза 02
- §14 Ambiguous Groups (GROUP BY ошибки) — фаза 04
- §15 Random Selection — фаза 04
- §16 Poor Man's Search Engine (LIKE %x%) — фаза 04
- §17 Spaghetti Query — фаза 04
- §18 Implicit Columns (SELECT *) — фаза 04
- §19 Readable Passwords — фаза 07
- §20 SQL Injection — фаза 07
- §21 Pseudokey Neat-Freak — фаза 02
- §22 See No Evil (ignored errors) — фаза 05
- §23 Diplomatic Immunity (testless DB) — фаза 06
- §24 Magic Beans (ActiveRecord misuse) — фаза 04
- §25 Dogma (cargo culting) — финальная

---

## Индексы и производительность

### Markus Winand — *SQL Performance Explained* (2012) / *Use the Index, Luke* (онлайн)
**Главный источник для phase 03 и 04.**
- Ch. 1 «Anatomy of an Index» — B-tree, leaf nodes
- Ch. 2 «Where Clause» — какие предикаты используют индекс
- Ch. 3 «Performance and Scalability» — index range scan
- Ch. 4 «The Join Operation» — join-стратегии (NL/Hash/Merge)
- Ch. 5 «Clustering Data» — кластеризация
- Ch. 6 «Sorting and Grouping» — индексы для ORDER BY/GROUP BY
- Ch. 8 «Modifying Data» — стоимость записи при множестве индексов

### Schwartz, Zaitsev, Tkachenko — *High Performance MySQL* (4th ed., 2021)
- Ch. 6 «Schema Design and Management» — фаза 02
- Ch. 7 «Indexing for High Performance» — фаза 03
- Ch. 8 «Query Performance Optimization» — фаза 04
- Ch. 11 «Scaling MySQL» — фаза 08
- Ch. 13 «Backup and Recovery» — фаза 09

### Greg Smith — *PostgreSQL 9.0 High Performance* (2010, фундамент актуален)
- Ch. 4 «Disk Setup» — IOPS, sequential vs random
- Ch. 7 «Routine Maintenance» — VACUUM, ANALYZE — фаза 09
- Ch. 10 «Query Optimization» — EXPLAIN — фаза 04
- Ch. 11 «Database Activity and Statistics» — pg_stat_* — фаза 09
- Ch. 13 «Replication» — фаза 08

---

## Транзакции и консистентность

### Philip Bernstein, Eric Newcomer — *Principles of Transaction Processing* (2nd ed., 2009)
- Ch. 6 «Locking» — phantom reads, lost update
- Ch. 7 «System Recovery» — durability, WAL
- Ch. 9 «Replication» — eventual consistency

### Pat Helland — *Life Beyond Distributed Transactions: An Apostate's Opinion* (2007)
**Идемпотентность как фундамент.** Используется в фазе 05 и 05b.

### Martin Kleppmann — *Designing Data-Intensive Applications* (2017)
**Энциклопедия модерн-БД.**
- Ch. 5 «Replication» — фаза 08
- Ch. 6 «Partitioning» — фаза 08
- Ch. 7 «Transactions» — isolation levels, фаза 05
- Ch. 8 «The Trouble with Distributed Systems» — фаза 05
- Ch. 9 «Consistency and Consensus» — фаза 05, 08
- Ch. 11 «Stream Processing» — фаза 08 для CDC/event-sourcing
- Ch. 12 «The Future of Data Systems» — Lambda/Kappa архитектуры

### Vlad Mihalcea — *High Performance Java Persistence* (2019)
**N+1 и ORM-паттерны.** Несмотря на «Java» в названии, главы про N+1, fetch strategies, optimistic vs pessimistic locking универсальны.
- Ch. 3 «JDBC Connection Management» — фаза 08
- Ch. 4 «Batch Updates» — фаза 04
- Ch. 5 «Statement Caching» — фаза 08
- Ch. 9 «Identifiers» — UUID vs auto-increment vs ULID
- Ch. 10 «Relationships» — N+1, fetch strategies — фаза 04
- Ch. 11 «Inheritance» — единая, табличная, конкретная — фаза 02
- Ch. 14 «Concurrency Control» — оптимистические/пессимистические локи — фаза 05

---

## Эволюция схемы

### Pramod Sadalage, Scott Ambler — *Refactoring Databases: Evolutionary Database Design* (2006)
**Главный источник для phase 06.**
- Part II — Structural Refactorings (rename column, split table, merge table)
- Part III — Data Quality Refactorings (introduce default, replace literal with lookup table)
- Part IV — Referential Integrity Refactorings
- Part V — Architectural Refactorings (encapsulate table with view, replace one-to-many with associative table)
- Part VI — Method Refactorings (replace method with stored procedure)
- Part VII — Transformations (insert/migrate data)

Каждый refactoring описан **с zero-downtime стратегией** (multi-step deploy: add → backfill → switch reads → drop old).

### Sadalage, Fowler — *NoSQL Distilled* (2012)
- Ch. 4 «Distribution Models» — sharding/replication
- Ch. 5 «Consistency» — quorum reads/writes
- Ch. 7 «Document Databases» — Mongo schema design
- Ch. 8 «Column-Family Stores»
- Ch. 9 «Graph Databases»

---

## Безопасность и compliance

### OWASP — *Database Security Cheat Sheet*
- Authentication & Authorization
- Connection security (TLS to DB)
- SQL Injection prevention
- Sensitive data protection

### NIST SP 800-122 — *Guide to Protecting the Confidentiality of Personally Identifiable Information (PII)*
Используется в phase 07 для классификации PII.

### GDPR — Articles 5, 17, 20, 32, 33
- Article 5 — Principles relating to processing
- Article 17 — Right to erasure
- Article 20 — Right to data portability
- Article 32 — Security of processing
- Article 33 — Notification of breach

---

## Операционка и observability

### Brendan Gregg — *Systems Performance: Enterprise and the Cloud* (2nd ed., 2020)
- Ch. 5 «Applications» — методология USE
- Ch. 9 «Disks» — IOPS, latency
- Ch. 10 «Network»

### Google SRE Book (2016) и SRE Workbook (2018)
- Ch. 4 SLO — фаза 09 (определение SLO для БД)
- Ch. 6 Monitoring — четыре золотых сигнала
- Ch. 26 Data Integrity — фаза 09 (бэкапы, DR, RTO/RPO)

---

## Когнитивные ошибки в анализе

### Daniel Kahneman — *Thinking, Fast and Slow* (2011)
Ch. 11 — anchoring; Ch. 24 — overconfidence; Ch. 25 — Bernoulli's errors. Используется в `phase_10a_self_audit`.

### Forsgren, Humble, Kim — *Accelerate* (2018)
Ch. 8 «Architecture» — связь архитектуры БД с deployment frequency. Используется в `phase_06`.

---

## Где какая книга применяется (быстрый индекс)

| Phase | Главные источники |
|-------|-------------------|
| 02 schema | Date §6, Karwin §1-13, Celko *Style* §1-5 |
| 03 indexes | Winand chapters 1-8, Karwin §4, §12 |
| 04 queries | Winand chapters 4-6, Mihalcea §10, Karwin §14-18, §24 |
| 05 transactions | Bernstein & Newcomer §6-7, Kleppmann §7-9, Helland (paper) |
| 05b money | Karwin §9, Helland, Mihalcea §14 |
| 06 migrations | Sadalage & Ambler entire book, Forsgren §8 |
| 07 security | Karwin §19-20, OWASP DB Cheatsheet, NIST SP 800-122, GDPR |
| 08 perf/scaling | Schwartz §11, Smith §13, Kleppmann §5-6 |
| 09 ops | Smith §7-11, SRE Book §4, §6, §26, Gregg §5, §9 |
| 10a self-audit | Kahneman §11, §24-25 |
