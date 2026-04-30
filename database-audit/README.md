<div align="center">

  <h1>🗄️ Database Audit Pipeline <code>v5.2</code></h1>

  <p>
    <b>Production-grade manifest-driven аудит БД с 100% MCP integration.</b><br/>
    Autonomous master prompt · Serena LSP + GitNexus cypher · 30 детекторов · 11 ORM · auto-fill phase 11/10a · multi-project compare.
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-v5.2-orange" alt="v5.1"/>
    <img src="https://img.shields.io/badge/architecture-manifest--driven-blue" alt="Manifest-driven"/>
    <img src="https://img.shields.io/badge/MCP-Serena%20%2B%20GitNexus-purple" alt="MCP native"/>
    <img src="https://img.shields.io/badge/detectors-30-green" alt="30 detectors"/>
    <img src="https://img.shields.io/badge/ORM-11_supported-success" alt="11 ORMs"/>
    <img src="https://img.shields.io/badge/SQLi-detected-red" alt="SQLi detection"/>
    <img src="https://img.shields.io/badge/auto--fill-phase_11/10a-9b59b6" alt="Auto-fill"/>
    <img src="https://img.shields.io/badge/mode-read--only-success" alt="Read-only"/>
  </p>

  <p>
    <a href="../README.md">← Назад к Audit Pipelines</a> ·
    <a href="../codebase">Универсальный пайплайн</a> ·
    <a href="../frontend">Фронтенд-пайплайн</a> ·
    <a href="../ci-hardening">CI Hardening</a>
  </p>
</div>

<br/>

> **v5.1 — финальная итерация.** Один автономный мастер-промт ([`MASTER_PROMPT.md`](./MASTER_PROMPT.md)) — пользователь даёт PROJECT_PATH + mode, ИИ выполняет все 8 stages без интерактивности (bootstrap → GitNexus indexing → discovery через Serena LSP + cypher → manifest validation → 14 фаз → phase 11 enrichment с Fix variants A/B/C → phase 10a calibration → finalize → single-message report).
>
> Дальше **30 детерминированных детекторов** работают по manifest. Phase 11 deep_dive auto-fills trace + blast radius через `gitnexus impact`, phase 10a adversary review с severity calibration.

---

## 🚀 v5.1 — что нового

### Автономный режим (главное)

```
Прочитай database-audit/MASTER_PROMPT.md и проведи полный аудит.
PROJECT_PATH=/your/project
mode=live
DATABASE_URL=postgresql://audit_ro:***@host/db
```

ИИ автономно делает 8 stages: bootstrap → indexing → discovery → validate → run → enrich phase 11 → calibrate → finalize → отчёт.

### v5.1 фичи

| Фича | Файл | Что делает |
|---|---|---|
| **Live drift verification** | `00b_discover_transactions.md` | Обязательный SQL invariant check для каждой денормализации (balance vs sum, inventory vs reserved, ...). На vechkasov v4 нашли реальную утечку 7593 RUB (vechkasov live-mode прогон) у клиента SKUDOV.NET. |
| **GitNexus auto-index** | `init.sh` | Автоматически запускает `gitnexus analyze` если проект не индексирован — фиксит auto-fill phase 11 sections. |
| **Idempotency unique-constraint check** | `00f_discover_serena_deep.md` | 3-уровневая classification: false / partial (header без БД constraint) / true (header + unique constraint). |
| **Route map PII exposure** | `00g_discover_gitnexus_graph.md` | Cross-reference HTTP routes с pii_candidates → endpoint-aware findings. |
| **FK priority by table size** | `find_missing_fk_indexes.py` | Live evidence cross-ref: `>1M rows = critical`, `100k-1M = high`, `<10k = low`. Static-mode default = high. |
| **Verify-fix prompt** | `prompts/verify_fix.md` | Re-check applied fixes для конкретных finding IDs. Snapshots previous run, re-verifies invariants, статусы fixed/partial/still-open/regressed. |
| **ROADMAP time-budget** | `synthesize_roadmap.py` | Авто-секции: ⚡ Quick wins (S effort) · 📅 Sprint plan (M effort) · 🎯 Quarter goals (L+) · effort budget в engineer-hours. |
| **Multi-project compare** | `run.sh compare` | Severity/category matrix, common subcategories, unique findings, worst offenders ranking. |
| **Phase 10a v5 enforcement** | `validate_phase.sh` | Required sections: Strong findings, Severity calibration, Systematic risks. Fail если high>50% без calibration justification. |

---

## Что находит этот пайплайн

### 🔴 Critical issues (блокируют деплой)

| # | Что | Как находим | Источник |
|---|---|---|---|
| 1 | **SQL Injection** через `$queryRawUnsafe`/`$executeRawUnsafe` | `find_raw_sql_unsafe.py` + dynamic interpolation detection + GitNexus cypher | Karwin §20, OWASP |
| 2 | **Race conditions** в денежных операциях (lost update, write skew) | `find_transactions.py` + body inspection через Serena `find_symbol include_body=true` | Bernstein & Newcomer §6, Kleppmann §7 |
| 3 | **Float для денег** (precision drift) | `find_money_floats.py` с `business_critical` calibration | Karwin §9 Rounding Errors |
| 4 | **Отсутствие idempotency** на money endpoints | `find_no_idempotency.py` через `manifest.hints.money_endpoints` | Helland *Life Beyond Distributed Transactions* |
| 5 | **Plain credentials/passwords** в БД | `find_pii_extended.py` (passwords, refresh_token, oauth_token, api_secret, webhook_secret) | NIST SP 800-218, GDPR Art. 32 |
| 6 | **Cross-tenant data leakage** | GitNexus cypher `MATCH (h:Handler)-[:CALLS*]->(q) WHERE NOT q.body CONTAINS tenant_id` | OWASP Multi-tenant guidelines |

### 🟠 High-impact issues

| # | Что | Как находим |
|---|---|---|
| 7 | **FK без индекса** | `find_missing_fk_indexes.py` парсит `schema_summary.json` |
| 8 | **N+1 queries** с confidence ranking | `find_n_plus_one.py`: high (for-loop с iterator-зависимым ORM call) / medium (Promise.all+map) / low (likely false positive) |
| 9 | **Custom SQL wrappers без параметризации** (`dbExec`, `dbQuery`) | `find_orm_wrappers.py` — surface для review |
| 10 | **Auth bypass** на /api/* | GitNexus cypher: handlers без `withAuth` middleware |
| 11 | **Dangerous DDL** в миграциях (DROP без `IF EXISTS`, `CREATE INDEX` без `CONCURRENTLY`, large-tx-wrap) | `find_dangerous_ddl.py` |
| 12 | **External I/O внутри транзакций** (Helland antipattern) | `manifest.hints.transaction_sites[].kind == external-io-inside-transaction` |
| 13 | **Connection pool multiplication** (`max=20 × N сервисов = exhaustion`) | `find_pool_settings.py` |
| 14 | **Long-lived DB credentials** в коде/env | `gitleaks` integration в `find_secrets_in_repo.py` |

### 🟡 Medium / quality issues

| # | Что | Как находим |
|---|---|---|
| 15 | Mixed naming (`snake_case` + `camelCase` в одной схеме) | `find_naming_inconsistency.py` |
| 16 | JSON columns где должна быть нормализация (Karwin §5 EAV) | `find_json_overuse.py` |
| 17 | `status TEXT` без `CHECK constraint` | `find_status_without_check.py` |
| 18 | `SELECT *` в hot paths | `find_select_star.py` |
| 19 | Forward-only миграции без rollback strategy | `find_reversibility.py` |
| 20 | Отсутствие slow query log / pg_stat_statements | `find_observability.py` |
| 21 | Backup без verified restore drill | `find_backup_strategy.py` |

---

## Как работает анализ

### Stage 0 — Discovery (один раз на проект)

```
bash database-audit/init.sh
        ↓
ИИ-модель читает database-audit/_staging/init.md
        ↓
┌─────────────────────────────────────────────────┐
│ 00_discover.md — orchestrator (skeleton)        │
│   ↓                                              │
│ 00a_discover_money.md — money columns + endpoints│
│ 00b_discover_transactions.md — race candidates   │
│ 00c_discover_pii.md — PII + secrets              │
│ 00d_discover_n_plus_one.md — N+1 vetting         │
│ 00e_discover_migrations.md — migrations + DDL    │
│ 00f_discover_serena_deep.md — Serena LSP проход  │
│ 00g_discover_gitnexus_graph.md — GitNexus cypher │
│ 00z_validate_manifest.md — self-validation gate  │
└─────────────────────────────────────────────────┘
        ↓
database-audit/manifest.yml (project-specific facts)
```

**Что использует ИИ при discovery:**

- **Serena MCP** (LSP-based):
  - `find_symbol(name, include_body=true)` для каждой transaction-функции
  - `find_referencing_symbols(column)` для каждой money колонки → точные usage sites
  - `search_for_pattern(regex, glob)` для SQLi surface
  - `write_memory()` для прогресса аудита

- **GitNexus MCP** (knowledge graph):
  - `route_map` — все HTTP endpoints проекта
  - `impact <symbol> --direction upstream` — blast radius (для phase 11)
  - `context <symbol>` — 360° view callers/callees/processes
  - `cypher` — 7 готовых запросов:
    1. SQLi callers: `MATCH (caller)-[:CALLS]->(target {name:'$queryRawUnsafe'})`
    2. Auth bypass: handlers без `withAuth` middleware
    3. Race candidates: SELECT+UPDATE без `FOR UPDATE` / `$transaction`
    4. Cross-tenant leak: query без `tenant_id` filter
    5. N+1 graph-based: ORM call в for-body
    6. Vector search: `embedding <=>` использование
    7. Money writes: все `WRITES → balance/amount/cost`

### Stage 1..N — Phases (повторяемо)

```
bash database-audit/run.sh all
        ↓
┌──────────────────────────────────────┐
│ Phase 00 — Setup                     │  valid manifest + preflight (live mode)
│ Phase 01 — Inventory                 │  extract_schema, extract_query_inventory
│ Phase 02 — Schema Design             │  find_money_floats, find_naming, find_json, find_status
│ Phase 03 — Indexes & Keys            │  find_missing_fk_indexes, find_index_recommendations
│ Phase 04 — Query Patterns            │  find_n_plus_one, find_select_star, find_string_concat_sql
│ Phase 05 — Transactions Consistency  │  find_transactions, find_isolation_levels
│ Phase 05b — Money Invariants         │  find_money_floats, find_no_idempotency, find_atomic_updates
│ Phase 06 — Migrations Evolution      │  find_migrations, find_dangerous_ddl, find_reversibility
│ Phase 07 — Data Integrity & Security │  find_string_concat_sql, find_raw_sql_unsafe (NEW),
│                                      │  find_orm_wrappers (NEW), find_pii_extended (NEW), find_pii_in_logs
│ Phase 08 — Performance & Scaling     │  find_pool_settings, find_cache_strategy
│ Phase 09 — Observability & Ops       │  find_observability, find_backup_strategy
│ Phase 10 — Synthesis                 │  synthesize_roadmap → ROADMAP.md + auto-TL;DR
│ Phase 10a — Self-Audit               │  adversary_review → bias-check + reclassification
│ Phase 11 — Deep Dive                 │  deep_dive → 6 секций per critical finding
│                                      │    sections 1, 3 auto-populated через GitNexus
│                                      │    sections 2, 4, 5, 6 — agent fills (creative)
└──────────────────────────────────────┘
        ↓
finalize.sh exit 0
        ↓
database-audit/results/ — все артефакты
```

### Hard exit gates (не пропускают slop)

После каждой фазы — `validate_phase.sh NN`:

1. ✅ Findings count ≥ scaled quota (по `manifest.project.size`)
2. ✅ Все `confidence: high` имеют `confidence_rationale ≥ 40` символов
3. ✅ Все `severity: critical` имеют `exploit_proof ≥ 40` символов
4. ✅ `location.lines` непустой для high
5. ✅ Required evidence файлы присутствуют
6. ✅ Stop-words отсутствуют («допустимо», «приемлемо» — запрещены)
7. ✅ **v5.1: Phase 11 sections не содержат `_agent fills_` placeholders**
8. ✅ **v5.1: Phase 10a `_adversary_review.md` > 500 байт + не template**

`finalize.sh` блокирует завершение если хоть один gate не прошёл.

---

## Файловая структура

```
project/
└── database-audit/                    ← всё внутри одной папки
    │
    │── pipeline (committed code) ─────────────────────────
    ├── README.md                      ← ты здесь
    ├── 00_START_HERE.md
    ├── 01_ORCHESTRATOR.md
    ├── REFERENCE_TOOLS.md             ← Serena/GitNexus/SQL utils
    ├── REFERENCE_BOOKS.md             ← классика (Date, Karwin, Winand, ...)
    ├── REFERENCE_2026_STATE_OF_ART.md ← modern (Petrov, Pavlo CMU, pgroll)
    ├── REFERENCE_MCP_TOOLS.md         ← Serena+GitNexus cookbook (7 cypher queries)
    ├── TEMPLATES.md
    ├── TOOLS_VERSIONS.md              ← зависимости + CVE awareness
    ├── CHANGELOG.md
    │
    ├── init.sh                        ← STAGE 0 + --refresh
    ├── run.sh                         ← STAGE 1..N + reset
    ├── requirements.txt               ← PyYAML>=6.0, jsonschema>=4.23
    │
    ├── manifest.schema.yml            ← JSON Schema (с 2026 hints)
    ├── manifest.example.yml           ← Prisma-monorepo пример
    │
    ├── prompts/                       ← chunked discovery (10 files)
    │   ├── 00_discover.md             ← orchestrator
    │   ├── 00a..00e_discover_*.md     ← deep по теме
    │   ├── 00f_discover_serena_deep.md     ← v5 — Serena LSP
    │   ├── 00g_discover_gitnexus_graph.md  ← v5 — GitNexus cypher
    │   ├── 00z_validate_manifest.md        ← self-validation
    │   └── refresh.md                       ← --refresh mode
    │
    ├── phases/                        ← 14 phase docs
    │
    ├── detectors/                     ← 30 детекторов:
    │   ├── extract_schema.py          ← 11 ORM (Prisma/Drizzle/TypeORM/Sequelize/
    │   │                                Mongoose/SQLAlchemy/Django/GORM/ActiveRecord/
    │   │                                Hibernate/raw SQL)
    │   ├── extract_query_inventory.py
    │   │
    │   ├── find_money_floats.py       ← с business_critical calibration
    │   ├── find_no_idempotency.py
    │   ├── find_transactions.py
    │   ├── find_atomic_updates.py
    │   │
    │   ├── find_missing_fk_indexes.py
    │   ├── find_index_recommendations.py
    │   │
    │   ├── find_n_plus_one.py         ← confidence ranking
    │   ├── find_select_star.py
    │   ├── find_string_concat_sql.py
    │   ├── find_raw_sql_unsafe.py     ← v5 — $queryRawUnsafe SQLi
    │   ├── find_orm_wrappers.py       ← v5 — dbExec/dbQuery surface
    │   │
    │   ├── find_isolation_levels.py
    │   ├── find_dangerous_ddl.py
    │   ├── find_migrations.py
    │   ├── find_reversibility.py
    │   │
    │   ├── find_pii_in_logs.py
    │   ├── find_pii_extended.py       ← v5 — passwords/tokens/payment-card
    │   ├── find_secrets_in_repo.py
    │   │
    │   ├── find_pool_settings.py
    │   ├── find_cache_strategy.py
    │   ├── find_observability.py
    │   ├── find_backup_strategy.py
    │   │
    │   ├── find_naming_inconsistency.py
    │   ├── find_json_overuse.py
    │   ├── find_status_without_check.py
    │   │
    │   ├── synthesize_roadmap.py      ← auto-TL;DR + categorical map
    │   ├── adversary_review.py        ← v5 — auto-draft + bias check
    │   └── deep_dive.py               ← v5 — GitNexus auto-fill trace+blast
    │
    ├── validators/
    │   ├── validate_manifest.py       ← strict mode + sanity thresholds
    │   ├── preflight.py               ← live mode + read-only role check
    │   ├── validate_phase.sh          ← v5 enforcement (no skeleton)
    │   ├── validate_confidence.py
    │   ├── check_evidence_citations.py
    │   ├── generate_meta_json.py
    │   └── finalize.sh
    │
    ├── lib/
    │   ├── env.sh                     ← PIPELINE_DIR/AUDIT_DIR/MANIFEST/STAGING_DIR
    │   ├── manifest_lib.py            ← + dedup helpers
    │   ├── id_gen.py                  ← category IDs (DB-MONEY-001) + fingerprint
    │   └── stack_aware.py             ← ORM-specific regex patterns
    │
    ├── viewer/
    │   └── index.html                 ← интерактивный HTML просмотр findings
    │
    ├── .gitignore                     ← исключает runtime ↓
    │
    │── runtime (gitignored) ──────────────────────────────
    ├── manifest.yml                   ← создаётся ИИ при init
    ├── _staging/                      ← prompts для ИИ
    │   ├── init.md                    ← создаётся при init.sh
    │   └── refresh.md                 ← создаётся при init.sh --refresh
    └── results/
        ├── findings.jsonl             ← все findings, category-based IDs
        ├── ROADMAP.md                 ← главный артефакт + auto-TL;DR
        ├── _meta.json                 ← машинная сводка (verdict + counts)
        ├── 11_deep_dive.md            ← critical-only forensic-grade
        ├── _adversary_review.md       ← bias-check
        ├── _known_unknowns.md         ← static-mode limitations
        ├── 10a_self_audit.md
        ├── 10_synthesis.md
        ├── 00_setup.md … 09_*.md      ← phase reports
        └── evidence/                  ← all detector outputs
            ├── 01_phase/schema_summary.json
            ├── 04_phase/n_plus_one_suspects.md
            ├── 07_phase/raw_sql_unsafe.md
            ├── 07_phase/orm_wrappers.md
            ├── 07_phase/pii_extended.md
            └── _serena_gitnexus/      ← GitNexus cypher results
```

---

## Quick start

### Автономный режим (рекомендуется) ⭐

После установки → один промт в Claude Code:

```
Прочитай database-audit/MASTER_PROMPT.md и проведи полный автономный аудит.

PROJECT_PATH=/home/ubuntu/apps/<project>
mode=<static | live>
DATABASE_URL=<если live, postgresql://audit_ro:...>
```

ИИ сам делает: GitNexus indexing → 9-step discovery → manifest → run all phases → enrich phase 11 → finalize → final report. **От пользователя — только путь и mode.**

### Manual mode (если хочется контроля)

### 1. Установка (один раз на машину)

```bash
# Serena (MCP server)
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant

# GitNexus (MCP server + CLI)
npm install -g gitnexus
gitnexus setup

# Базовые
sudo apt install jq python3 python3-pip ripgrep git
pip install -r database-audit/requirements.txt   # PyYAML>=6.0, jsonschema>=4.23

# Опц. для live mode (зависит от вашей БД)
sudo apt install postgresql-client mysql-client
# mongosh: https://www.mongodb.com/try/download/shell
```

См. полную справку зависимостей в [`TOOLS_VERSIONS.md`](./TOOLS_VERSIONS.md).

### 2. Скопировать в проект + индексировать

```bash
cd /your/project
cp -r /path/to/audit-pipelines/database-audit .
gitnexus analyze --embeddings   # индексирует код для cypher queries
```

### 3. INIT — discovery

```bash
bash database-audit/init.sh
```

Откройте Claude Code в этой директории:

```
Прочитай database-audit/_staging/init.md и выполни discover-фазу.
Создай database-audit/manifest.yml.
```

ИИ выполнит chunked discovery (orchestrator + 7 sub-prompts включая Serena+GitNexus deep). Результат — `database-audit/manifest.yml`.

### 4. Review manifest

```bash
python3 database-audit/validators/validate_manifest.py database-audit/manifest.yml --strict
less database-audit/manifest.yml
```

При необходимости отредактируйте yaml вручную (например, пометить `business_critical: false` для AI-token-cost полей).

### 5. RUN — все фазы

```bash
bash database-audit/run.sh all
```

### 6. Read

```bash
cat database-audit/results/ROADMAP.md
jq . database-audit/results/_meta.json

# HTML viewer
cd database-audit/results
cp ../viewer/index.html .
python3 -m http.server 8000
# открыть http://localhost:8000/index.html
```

### 7. Refresh (после изменений в проекте)

```bash
bash database-audit/init.sh --refresh
```

ИИ найдёт diff с git_head из `manifest.refresh_state`, обновит только релевантные секции.

### 8. Reset (clean restart)

```bash
bash database-audit/run.sh reset
# → удаляет manifest.yml, _staging/, results/
# → pipeline код остаётся
```

---

## Findings формат

Каждый finding в `database-audit/results/findings.jsonl`:

```json
{
  "id": "DB-MONEY-001",
  "phase": "05b",
  "category": "money",
  "subcategory": "no-idempotency",
  "severity": "critical",
  "confidence": "high",
  "title": "deductFromBalance не имеет idempotency_key",
  "location": {
    "file": "apps/crm/src/features/content/lib/cbr.ts",
    "lines": "40-99",
    "symbol": "deductFromBalance",
    "db_object": "content_projects.balanceRub"
  },
  "evidence": "Function signature accepts (projectId, costUsd) — no operation id...",
  "confidence_rationale": "Прочитана функция через find_symbol include_body=true; параметр idempotency_key отсутствует...",
  "exploit_proof": "Worker deducts balance and crashes before marking job as charged. Retry calls same function — second deduction.",
  "impact": "Двойное списание клиента при retry/worker crash.",
  "recommendation": "1) Add operation_id parameter. 2) Unique constraint (project_id, operation_id) в БД. 3) Idempotent endpoint.",
  "effort": "M",
  "references": [
    "Helland, Life Beyond Distributed Transactions",
    "Kleppmann, Designing Data-Intensive Applications Ch. 7"
  ]
}
```

**Category-based IDs** (легко группировать):

| Prefix | Категория |
|---|---|
| `DB-MONEY-***` | money/balance issues |
| `DB-IDX-***` | indexes |
| `DB-TX-***` | transactions |
| `DB-SEC-***` | security (SQLi, auth bypass) |
| `DB-PII-***` | PII unencrypted |
| `DB-SCH-***` | schema design |
| `DB-MIG-***` | migrations |
| `DB-PERF-***` | performance |
| `DB-QRY-***` | queries |
| `DB-OPS-***` | operations |

---

## Confidence calibration

| Confidence | Когда |
|---|---|
| `high` | Прочитал строки и цитирую; статически видно или EXPLAIN; нет правдоподобного контр-объяснения; **`confidence_rationale ≥ 40` символов** |
| `medium` | Видел паттерн, но эффект зависит от рантайма/нагрузки; ручная валидация частична |
| `low` | Грубая эвристика; ручная валидация не проводилась |

**Запреты (нарушение → откат severity):**
- `critical` без `exploit_proof ≥ 40` символов с конкретным сценарием
- `high` confidence для performance findings без EXPLAIN или прямой статической очевидности
- `high` для transaction findings без чтения тела функции

---

## Smoke test (vechkasov, 90k LOC monorepo)

```
Total findings: 111
Critical:    14
High:        67
Medium:      29
Low:          1
Verdict:     fail (есть critical)

By category:
  DB-IDX:    30  (FK без индекса)
  DB-SEC:    29  (SQLi $queryRawUnsafe + cmsApiKey)
  DB-PII:    27  (passwords, tokens, secrets)
  DB-MONEY:  11
  DB-SCH:    10
  DB-TX:      1  (deductFromBalance race)
  DB-MIG:     1
  DB-QRY:     1
  DB-PERF:    1

Highlights:
  - 27 SQLi findings (главный фикс v3 → v4)
  - 70 $queryRawUnsafe hits в 27 файлах
  - 249 ORM wrapper definitions (dbExec/dbQuery surface)
  - 156 N+1 candidates с confidence ranking
  - 30 FK без индекса в 9 prisma schemas
```

---

## Integration points

### CI/CD

`database-audit/results/_meta.json` машиночитаем — можно собрать GitHub Action:

```yaml
- run: bash database-audit/run.sh all
- run: |
    verdict=$(jq -r .verdict database-audit/results/_meta.json)
    if [ "$verdict" = "fail" ]; then
      echo "::error::DB audit verdict=fail"
      jq -r '.blockers[]' database-audit/results/_meta.json
      exit 1
    fi
```

### Live mode

```bash
export DATABASE_URL="postgresql://readonly:***@host:5432/dbname"
# В manifest: mode.type: live
bash database-audit/run.sh preflight   # verifies read-only role
bash database-audit/run.sh all         # adds EXPLAIN, pg_indexes, pg_stat_statements
```

### Multi-project

```bash
cd project-a && bash database-audit/init.sh && bash database-audit/run.sh all
cd project-b && bash database-audit/init.sh && bash database-audit/run.sh all
# Каждый проект имеет свой database-audit/manifest.yml + results/
```

---

## Литература

См. полные списки:
- [`REFERENCE_BOOKS.md`](./REFERENCE_BOOKS.md) — Date, Karwin, Winand, Schwartz, Smith, Sadalage, Kleppmann, Mihalcea, Helland, Bernstein
- [`REFERENCE_2026_STATE_OF_ART.md`](./REFERENCE_2026_STATE_OF_ART.md) — Petrov *Database Internals*, Pavlo CMU 15-445/15-721 (2024-2025), Mihalcea 3rd ed, Fontaine *Art of PostgreSQL*, Schönig *Mastering PostgreSQL 15*, pgroll, Atlas, NIST SP 800-218
- [`REFERENCE_MCP_TOOLS.md`](./REFERENCE_MCP_TOOLS.md) — Serena + GitNexus cookbook (7 cypher queries для DB-аудита)

---

<div align="center">

<a href="../README.md">← Назад к Audit Pipelines</a>

</div>
