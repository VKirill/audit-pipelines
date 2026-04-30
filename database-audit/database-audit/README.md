<div align="center">

  <h1>🗄️ Database Audit Pipeline <code>v3</code></h1>

  <p>
    <b>Production-grade manifest-driven аудит БД.</b><br/>
    Chunked AI discovery · 11 ORM · 27 детекторов · category-based IDs · dedup · live preflight · HTML viewer.
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-v3-orange" alt="v3"/>
    <img src="https://img.shields.io/badge/architecture-manifest--driven-blue" alt="Manifest-driven"/>
    <img src="https://img.shields.io/badge/orm-11_supported-purple" alt="11 ORMs"/>
    <img src="https://img.shields.io/badge/detectors-27-green" alt="27 detectors"/>
    <img src="https://img.shields.io/badge/mode-read--only-success" alt="Read-only"/>
    <img src="https://img.shields.io/badge/exit_gates-hard-red" alt="Hard exit gates"/>
    <img src="https://img.shields.io/badge/2026-state--of--art-9b59b6" alt="2026 stack"/>
  </p>

  <p>
    <a href="../README.md">← Назад к Audit Pipelines</a> ·
    <a href="../codebase">Универсальный пайплайн</a> ·
    <a href="../frontend">Фронтенд-пайплайн</a> ·
    <a href="../ci-hardening">CI Hardening</a>
  </p>
</div>

<br/>

> **v3 = идеальная итерация v2.** Chunked discovery (главный + 5 sub-prompts), category-based IDs, fingerprint-dedup, live mode preflight, `init.sh --refresh`, HTML viewer, и 11 ORM в parser. Литература обновлена под 2026 (Petrov, Pavlo CMU 2024-2025, Mihalcea 3rd ed, pgroll, Atlas, NIST SP 800-218).

---

## Что делает v3 уникально

1. **Самодостаточный** — пользователь даёт одну команду `bash database-audit/init.sh`, дальше всё контролируется промтами.
2. **Universal stack** — Prisma, Drizzle, TypeORM, Sequelize, **Mongoose**, **GORM**, **ActiveRecord**, **Hibernate**, SQLAlchemy, Django, raw SQL.
3. **Modern (2026)** — pgvector, TimescaleDB, Citus, RLS multi-tenant, CDC/outbox.
4. **No false-confidence** — `confidence_rationale ≥ 40` для high; `exploit_proof ≥ 40` для critical; sanity thresholds ловят пустые секции.
5. **Repeatable** — `init.sh --refresh` делает diff с last manifest, обновляет только релевантные секции.
6. **Visual** — `viewer/index.html` показывает findings с фильтрами и expand-evidence.

---

## Workflow

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 0: INIT — bash database-audit/init.sh              │
│                                                           │
│   1. Стейджинг промта в .audit-init.md                    │
│   2. ИИ читает orchestrator prompts/00_discover.md        │
│   3. ИИ загружает sub-prompts по необходимости:           │
│      - 00a money    - 00b transactions                    │
│      - 00c pii      - 00d n+1                             │
│      - 00e migrations                                     │
│   4. ИИ создаёт database-audit.manifest.yml               │
│   5. validate_manifest.py --strict                        │
│   6. ИИ останавливается, ждёт user review                 │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  STAGE 1..N: PHASES — bash database-audit/run.sh all      │
│                                                           │
│   1. validate_manifest                                    │
│   2. preflight (если live mode)                           │
│   3. Гонит детекторы по phase_plan из manifest            │
│   4. validate_phase.sh exit 0 после каждой                │
│   5. finalize.sh + _meta.json                             │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  REVIEW: viewer/index.html  +  audit/ROADMAP.md           │
└──────────────────────────────────────────────────────────┘
```

---

## Что внутри

```
database-audit/
├── README.md                           ← ты здесь
├── 00_START_HERE.md                    ← точка входа
├── 01_ORCHESTRATOR.md                  ← правила Stage 1..N
├── REFERENCE_TOOLS.md                  ← Serena, GitNexus, SQL utils
├── REFERENCE_BOOKS.md                  ← классика
├── REFERENCE_2026_STATE_OF_ART.md      ← НОВОЕ — modern источники
├── TEMPLATES.md                        ← формат findings, ROADMAP
├── CHANGELOG.md
│
├── init.sh                             ← STAGE 0 + --refresh
├── run.sh                              ← STAGE 1..N + preflight
│
├── manifest.schema.yml                 ← JSON Schema (с 2026 hints)
├── manifest.example.yml                ← пример (Prisma-монорепо)
│
├── prompts/                            ← chunked discovery (8 файлов)
│   ├── 00_discover.md                  ← orchestrator
│   ├── 00a_discover_money.md           ← deep money
│   ├── 00b_discover_transactions.md    ← deep transactions
│   ├── 00c_discover_pii.md             ← deep PII
│   ├── 00d_discover_n_plus_one.md      ← N+1 vetting
│   ├── 00e_discover_migrations.md      ← migrations + DDL
│   ├── 00z_validate_manifest.md        ← self-validation
│   └── refresh.md                      ← для --refresh
│
├── phases/                             ← 14 phase docs
│
├── detectors/                          ← 27 детекторов
│   ├── extract_schema.py               ← 11 ORM parsers
│   ├── extract_query_inventory.py
│   ├── find_money_floats.py            ← КЛЮЧЕВОЙ + dedup
│   ├── find_n_plus_one.py              ← confidence ranking
│   ├── find_missing_fk_indexes.py
│   ├── find_select_star.py
│   ├── find_string_concat_sql.py
│   ├── find_transactions.py
│   ├── find_no_idempotency.py
│   ├── find_dangerous_ddl.py
│   ├── find_migrations.py
│   ├── find_pool_settings.py
│   ├── find_pii_in_logs.py
│   ├── find_naming_inconsistency.py
│   ├── find_json_overuse.py
│   ├── find_status_without_check.py
│   ├── synthesize_roadmap.py           ← auto-TL;DR
│   ├── adversary_review.py
│   ├── deep_dive.py
│   └── ... + 8 stub-детекторов
│
├── validators/
│   ├── validate_manifest.py            ← --strict mode
│   ├── preflight.py                    ← НОВОЕ — live mode preflight
│   ├── validate_phase.sh               ← per-phase gate
│   ├── validate_confidence.py
│   ├── check_evidence_citations.py
│   ├── generate_meta_json.py
│   └── finalize.sh
│
├── lib/
│   ├── env.sh                          ← AUDIT_DIR / PROJECT_ROOT / MANIFEST
│   ├── manifest_lib.py                 ← + dedup helpers
│   ├── id_gen.py                       ← НОВОЕ — category IDs + fingerprint
│   └── stack_aware.py                  ← НОВОЕ — ORM patterns
│
└── viewer/
    └── index.html                      ← НОВОЕ — HTML просмотр findings
```

---

## Quick start

### 1. Установка (один раз)

```bash
# Serena + GitNexus
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant
npm install -g gitnexus
gitnexus setup

# Базовые
sudo apt install jq python3 ripgrep
pip install pyyaml jsonschema

# Опц. для live mode
sudo apt install postgresql-client mysql-client
# Опц. для viewer
# (любой http-server, python -m http.server подойдёт)
```

### 2. Скопировать в проект

```bash
cp -r /path/to/audit-pipelines/database-audit/ /your/project/
cd /your/project
gitnexus analyze --embeddings
```

### 3. INIT (один раз на проект)

```bash
bash database-audit/init.sh
# ↓
# Открой Claude Code, дай команду:
#   Прочитай .audit-init.md и выполни discover-фазу. Создай database-audit.manifest.yml.
# ↓
# ИИ выполнит chunked discovery (orchestrator + 5 sub-prompts) — ~30-90 минут.
# Результат: database-audit.manifest.yml
```

### 4. Review manifest

```bash
python3 database-audit/validators/validate_manifest.py database-audit.manifest.yml --strict
less database-audit.manifest.yml
```

Поправь yaml вручную если ИИ что-то пропустил.

### 5. RUN

```bash
bash database-audit/run.sh all
```

### 6. Read

```bash
cat audit/ROADMAP.md
jq . audit/_meta.json

# HTML viewer
cd audit && cp ../database-audit/viewer/index.html .
python3 -m http.server 8000
# открой http://localhost:8000/index.html
```

### 7. Refresh (через 1-3 месяца)

```bash
bash database-audit/init.sh --refresh
# ИИ найдёт diff и обновит только изменённые секции
```

---

## Что v3 фиксит

| v2 → v3 | Решение |
|---|---|
| Дубли findings (DB-0002 + DB-0040 одно и то же) | Fingerprint-dedup + category-based ID |
| Глобальная нумерация (DB-0042) — непонятно где | `DB-MONEY-001`, `DB-IDX-042`, `DB-TX-007` |
| `find_n_plus_one` — все кандидаты one weight | Confidence ranking по 4 уровням |
| Только 5 ORM в schema parser | 11 ORM (включая Mongoose, GORM, ActiveRecord, Hibernate) |
| Discover-промт overwhelming на больших проектах | Chunked: orchestrator + 5 sub-prompts + validation gate |
| Manual update manifest при изменениях | `init.sh --refresh` с diff |
| Live mode не верифицирован до запуска | `preflight.py` проверяет DSN + client + read-only role |
| ROADMAP.md без авто-TL;DR | `synthesize_roadmap.py` генерирует bullets из severity × category |
| Только текстовый просмотр findings | `viewer/index.html` с фильтрами |
| Литература до 2017 в основном | Petrov, Pavlo CMU 2024-2025, Mihalcea 3rd ed, pgroll, Atlas |

---

## Modern 2026 patterns в manifest

```yaml
hints:
  vector_db_indexes:           # pgvector / Pinecone / Qdrant
    - table: embeddings
      column: vector
      dimension: 1536
      metric: cosine
      index_type: hnsw
  time_series_tables:           # TimescaleDB / native partitioning
    - table: events
      partitioning: hypertable
      retention_policy: "30 days"
  sharding_strategy:            # Citus / Vitess
    enabled: true
    kind: hash
    shard_key: tenant_id
  multi_tenant_isolation:       # RLS / discriminator / schema-per-tenant
    model: row-level-security
    discriminator_column: tenant_id
  cdc_outbox_pattern:           # Debezium / outbox / event-sourcing
    enabled: true
    tool: custom-outbox
    outbox_table: events_outbox
```

---

## Литература

См. полные списки в:
- [`REFERENCE_BOOKS.md`](./REFERENCE_BOOKS.md) — классика (Date, Karwin, Winand, Schwartz, Smith, Sadalage, Kleppmann, Mihalcea, Helland, Bernstein)
- [`REFERENCE_2026_STATE_OF_ART.md`](./REFERENCE_2026_STATE_OF_ART.md) — modern (Petrov, Pavlo, Fontaine, Schönig, pgroll, Atlas, NIST SP 800-218)

---

<div align="center">

<a href="../README.md">← Назад к Audit Pipelines</a>

</div>
