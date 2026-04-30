<div align="center">

  <h1>🗄️ Database Audit Pipeline <code>v1</code></h1>

  <p>
    <b>Глубокий аудит данных, схемы, запросов и эксплуатации БД — за один прогон Claude Code.</b><br/>
    11 основных фаз + 2 мини · evidence-based, read-only · работает на любой ORM/SQL стек.
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-v1-orange" alt="v1"/>
    <img src="https://img.shields.io/badge/phases-11%2B2-blue" alt="11+2 phases"/>
    <img src="https://img.shields.io/badge/time-60--240_min-green" alt="60-240 min"/>
    <img src="https://img.shields.io/badge/mode-read--only-success" alt="Read-only"/>
    <img src="https://img.shields.io/badge/exit_gates-hard-red" alt="Hard exit gates"/>
    <img src="https://img.shields.io/badge/live--db-optional-9b59b6" alt="Live DB optional"/>
  </p>

  <p>
    <a href="../README.md">← Назад к Audit Pipelines</a> ·
    <a href="../codebase">Универсальный пайплайн</a> ·
    <a href="../frontend">Фронтенд-пайплайн</a> ·
    <a href="../ci-hardening">CI Hardening</a>
  </p>
</div>

<br/>

> Если у тебя есть проект, в котором что-то лежит в БД — этот пайплайн скажет, **выдержит ли это нагрузку, не теряются ли деньги, не пропадают ли данные при падении, и сколько чинить если уже больно**. На выходе — приоритизированный roadmap с пруфами из схемы, миграций и кода запросов.

---

## Зачем это нужно

База данных — это **самое дорогое место для ошибок**. Код можно переписать, БД — нельзя без миграции, downtime'а и часто потери данных. И это самое сложное место для понимания глазами: ORM прячет SQL, миграции живут отдельно от моделей, индексы создаются по интуиции, транзакции пишутся «как у всех» в копи-пасте.

Симптомы знакомые:

| Симптом | Что это значит на самом деле |
|---|---|
| «На 100 пользователях нормально, на 10 000 — встал колом» | Нет индексов на FK, есть N+1, нет connection pool |
| «Списали с клиента дважды, не понимаем как» | Нет идемпотентности, race в транзакции, отсутствие unique constraint |
| «Миграция в проде катилась 4 часа и сломала запись» | Нет zero-downtime стратегии, миграция меняет колонку с блокировкой |
| «Боюсь трогать схему — сломаю всё» | Миграции необратимы, бэкап давно не проверяли, нет staging-копии |
| «У нас GDPR-аудит через месяц» | Нет шифрования PII, нет audit log, нет права на забвение |
| «Бэкапы делаются, но восстановиться не пробовали» | Disaster recovery — только в плане, не в реальности |

Этот пайплайн **систематически проверяет**: дизайн схемы, индексы, паттерны запросов, транзакции, миграции, безопасность, масштабирование, операционку. Каждая находка — с пруфом из конкретной строки в коде/схеме/миграции и привязкой к книге индустрии.

---

## Что внутри

```
database-audit/
├── README.md                       ← ты здесь
├── 00_START_HERE.md                ← точка входа для пользователя и агента
├── 01_ORCHESTRATOR.md              ← главный диспетчер, правила поведения
├── REFERENCE_TOOLS.md              ← Serena, GitNexus, SQL/EXPLAIN tools
├── REFERENCE_BOOKS.md              ← классика индустрии — где какая глава применяется
├── TEMPLATES.md                    ← формат findings, evidence, ROADMAP
├── CHANGELOG.md                    ← история версий
├── phases/
│   ├── phase_00_setup.md
│   ├── phase_01_inventory.md
│   ├── phase_02_schema_design.md
│   ├── phase_03_indexes_keys.md
│   ├── phase_04_query_patterns.md
│   ├── phase_05_transactions_consistency.md
│   ├── phase_05b_money_invariants.md   ← мини-фаза, если есть деньги/счётчики
│   ├── phase_06_migrations_evolution.md
│   ├── phase_07_data_integrity_security.md
│   ├── phase_08_performance_scaling.md
│   ├── phase_09_observability_ops.md
│   ├── phase_10_synthesis_roadmap.md
│   ├── phase_10a_self_audit.md
│   └── phase_11_deep_dive.md           ← обязателен при ≥1 critical
└── scripts/
    ├── lib/common.sh                       ← общие функции (как в codebase/v3)
    ├── run_external_tools.sh               ← собирает evidence заранее
    ├── detect_db_stack.sh                  ← Prisma/SQLAlchemy/Sequelize/Mongoose/...
    ├── extract_schema_summary.sh           ← парсер прима/моделей в плоский summary
    ├── extract_query_inventory.sh          ← raw SQL + ORM-вызовы → каталог
    ├── find_n_plus_one.sh                  ← эвристика: запрос внутри цикла
    ├── find_missing_indexes.py             ← FK без индекса
    ├── find_select_star.sh                 ← SELECT * usage
    ├── find_string_concat_sql.sh           ← SQLi surface
    ├── find_transactions.sh                ← паттерны транзакций
    ├── find_migrations.sh                  ← миграции, обратимость, dangerous DDL
    ├── live_db_probe.sh                    ← (опц.) EXPLAIN, pg_stat_*
    ├── validate_phase.sh                   ← hard gate per phase
    ├── validate_confidence.py
    ├── check_evidence_citations.py
    ├── required_evidence_files.sh
    ├── generate_meta_json.py
    └── finalize.sh                         ← финальный gate
```

---

## Ключевые принципы

<table>
<tr><td><b>📂 Read-only</b></td><td>Пайплайн ничего не меняет ни в коде, ни в БД. Только наблюдает, читает план, пишет отчёт.</td></tr>
<tr><td><b>🔬 Evidence-based</b></td><td>Каждая находка — с цитатой из конкретной строки схемы/миграции/кода или вывод EXPLAIN. Без цитаты finding не принимается.</td></tr>
<tr><td><b>📚 По книгам</b></td><td>Каждое утверждение привязано к главе у Date / Karwin / Winand / Kleppmann / Schwartz. Не «мне кажется», а «§N.M в …».</td></tr>
<tr><td><b>🛠️ Static-first, live-optional</b></td><td>Базовый прогон — только статика (схема, миграции, код). Если есть подключение к БД — добавляются EXPLAIN, pg_stat, slow log. Static mode никогда не деградирует анализ, только глубину.</td></tr>
<tr><td><b>🔥 Money & State invariants</b></td><td>Мини-фаза 05b ловит проблемы с деньгами/счётчиками отдельно. Race + отсутствие idempotency = critical, обязателен Phase 11 deep-dive.</td></tr>
<tr><td><b>⚖️ Калибровка confidence</b></td><td>`high` confidence требует `confidence_rationale` ≥ 40 символов. `critical` требует `exploit_proof` с конкретным сценарием. Скрипт ловит нарушения.</td></tr>
<tr><td><b>🚪 Hard exit gates</b></td><td>После каждой фазы — `validate_phase.sh NN`. Exit ≠ 0 = фаза не завершена. Финал — `finalize.sh` exit 0.</td></tr>
</table>

---

## Какие стеки покрывает

**ORM / клиенты:**
- TypeScript/JS: Prisma, Drizzle, TypeORM, Sequelize, Mongoose, Knex, Kysely, raw `pg`/`mysql2`
- Python: SQLAlchemy, Django ORM, Tortoise, Peewee, raw `psycopg`/`asyncpg`
- Go: GORM, sqlx, sqlc, raw `database/sql`
- PHP: Eloquent (Laravel), Doctrine
- Ruby: ActiveRecord (Rails)
- Java/Kotlin: Hibernate/JPA, Spring Data, jOOQ
- Rust: Diesel, sqlx, sea-orm

**Базы данных:**
- PostgreSQL (полный набор проверок включая RLS, partitioning)
- MySQL/MariaDB (storage engines, `EXPLAIN FORMAT=JSON`)
- SQLite (с оговорками — concurrency-модель отличается)
- MongoDB (отдельный набор проверок: schema-on-read, индексы, агрегации)
- Redis как primary store (с предупреждениями)

Если стек не детектируется автоматически — пользователь указывает вручную в `phase_00_setup`. Анализ продолжается через ручной обход моделей/миграций.

---

## Как пользоваться (для не-программистов)

<table>
<tr>
<td width="60px" align="center"><b>1️⃣</b></td>
<td><b>Дай ссылку на этот репозиторий своему разработчику</b> и попроси прогнать аудит на проекте, где есть БД. Это ~2-4 часа его времени.</td>
</tr>
<tr>
<td align="center"><b>2️⃣</b></td>
<td><b>Получи <code>audit/ROADMAP.md</code></b> — приоритизированный список «что чинить сейчас, что через месяц, что вообще не трогать». На русском, человекочитаемый. Каждый пункт со ссылкой на книгу и место в коде.</td>
</tr>
<tr>
<td align="center"><b>3️⃣</b></td>
<td><b>Если есть подключение к staging-БД</b> — попроси прогнать с переменной <code>DATABASE_URL</code>. Тогда добавятся EXPLAIN-ы топ-запросов и анализ реальных индексов. Без подключения — только статика, всё равно полезно.</td>
</tr>
<tr>
<td align="center"><b>4️⃣</b></td>
<td><b>Раз в полгода повторяй.</b> БД меняется медленнее кода, но индексы устаревают, нагрузка растёт, новые миграции добавляют долги.</td>
</tr>
</table>

---

## Что нужно установить (один раз)

<table>
<tr>
<td width="33%" valign="top" align="center">
<h3>Claude Code</h3>
<a href="https://claude.com/claude-code">claude.com/claude-code</a><br/>
<i>основной оркестратор</i>
</td>
<td width="33%" valign="top" align="center">
<h3>Serena</h3>
<a href="https://github.com/oraios/serena">oraios/serena</a><br/>
<i>семантика кода (LSP)</i>
</td>
<td width="33%" valign="top" align="center">
<h3>GitNexus</h3>
<a href="https://www.npmjs.com/package/gitnexus">npmjs.com/gitnexus</a><br/>
<i>граф кода + история</i>
</td>
</tr>
</table>

**Опционально (для live-режима):**
- `psql` / `mysql` / `mongosh` — прямой доступ к БД
- `pg_stat_statements` включён на стороне PostgreSQL для анализа реально медленных запросов
- `EXPLAIN ANALYZE` доступен (read-only пользователь подойдёт)

---

## Главный артефакт — `audit/ROADMAP.md`

```
🔴 Сейчас (Now):
  └─ [critical] Race condition при списании баланса — services/payments.py:88-104
     evidence: транзакция читает balance, в коде нет SELECT FOR UPDATE,
               два параллельных вызова приведут к двойному списанию.
     impact: возможность списать клиента дважды или уйти в минус.
     fix: SELECT … FOR UPDATE + проверка балланса внутри транзакции +
          unique constraint на (account_id, idempotency_key).
     book: Bernstein & Newcomer §3.4 «Lost update»; Karwin Antipattern §16.

  └─ [critical] FK без индекса — orders.user_id → 17M строк, full scan на каждое JOIN
     evidence: schema dump prisma/schema.prisma:42, отсутствует @index.
     book: Winand «Use the Index, Luke», §2 The Index Leaf Nodes.

🟡 Дальше (Next):
  └─ [high] N+1 в загрузке списка заказов — services/orders.ts:118
     fix: prisma include или dataloader.
     book: Mihalcea «High Performance Java Persistence», ch.10.

🟢 Потом (Later):
  └─ [medium] Имена таблиц в смешанной нотации — 12 случаев
     book: Celko «SQL Programming Style», §1.2.
```

---

## Ограничения

- **Без live-DB** — невозможно подтвердить реальные планы запросов, реальные индексы (vs декларированные), статистику использования. Эти findings помечаются как `low/medium` confidence с пометкой «требует EXPLAIN».
- **Полиглот-стек** (Postgres + Mongo + Redis в одном проекте) — обходится последовательно, каждая БД по своему чек-листу. Cross-DB консистентность отдельной мини-фазы не имеет, фиксируется в `_known_unknowns.md`.
- **Multi-tenant и шардинг** — пайплайн обнаруживает паттерны, но архитектурное ревью шардинга — отдельная сессия, не помещается в стандартный прогон.

---

## На какой методике это построено

См. подробный список в [`REFERENCE_BOOKS.md`](./REFERENCE_BOOKS.md). Кратко:

- **C.J. Date** — *Database Design and Relational Theory* (нормализация, первая логика)
- **Joe Celko** — *SQL for Smarties* (set-based мышление), *SQL Programming Style*
- **Bill Karwin** — *SQL Antipatterns* (25 паттернов — наша база для phase 02/04)
- **Markus Winand** — *SQL Performance Explained* / *Use the Index, Luke* (индексы — фаза 03)
- **Baron Schwartz et al.** — *High Performance MySQL* (фаза 08, паттерны масштабирования)
- **Greg Smith** — *PostgreSQL 9.0 High Performance* (PG-специфика, vacuum, autovacuum, WAL)
- **Pramod Sadalage, Scott Ambler** — *Refactoring Databases* (фаза 06, эволюционная схема)
- **Martin Kleppmann** — *Designing Data-Intensive Applications* (репликация, консистентность, фаза 05/08)
- **Vlad Mihalcea** — *High Performance Java Persistence* (N+1, фаза 04 — релевантно за пределами Java)
- **Pat Helland** — *Life Beyond Distributed Transactions* (фаза 05, идемпотентность)
- **Bernstein & Newcomer** — *Principles of Transaction Processing* (фаза 05, isolation)
- **Sadalage & Fowler** — *NoSQL Distilled* (для MongoDB-веток)

---

<div align="center">

<a href="../README.md">← Назад к Audit Pipelines</a>

</div>
