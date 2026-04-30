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

---

## v4 (2026-04-30) — Maximum MCP integration (Serena + GitNexus 100%)

После ретроспективы v3 на vechkasov: критический пропуск SQLi через `$queryRawUnsafe`,
custom DB wrappers, пустые phase 11/10a. v4 фиксит всё.

### Новые детекторы

- `find_raw_sql_unsafe.py` — обнаруживает `$queryRawUnsafe`, `$executeRawUnsafe`,
  `prisma.$queryRawUnsafe`, `sql.unsafe()` API. Two-tier severity:
  * **Critical** = Unsafe API + dynamic interpolation/concat в окрестности
  * **High** = Unsafe API только с positional placeholders (требует manual flow check)
- `find_orm_wrappers.py` — кастомные DB wrapper-функции (`dbExec`, `dbQuery`,
  `executeQuery`, `runQuery`). Эти функции — дыра в покрытии ORM-detectors.
- `find_pii_extended.py` — расширенный PII список: passwords, refresh_token,
  access_token, oauth_token, webhook_secret, payment-card (card/cvv/iban),
  GDPR Art. 9 special categories (health, biometric, religion).

### Auto-population phase 11/10a через GitNexus

- `deep_dive.py` v2: для каждого critical finding вызывает GitNexus CLI:
  * Section 1 «Trace» — auto-populated через `gitnexus context <symbol>`
  * Section 3 «Blast radius» — auto-populated через `gitnexus impact upstream`
  * Sections 2, 4, 5, 6 — agent fills (creative work)
- `adversary_review.py` v2: auto-draft на основе:
  * Confidence/severity distribution
  * Money severity inflation warning (>5 critical money = подозрение logging-only)
  * Strong/weak findings classification
  * Cognitive bias self-check questions

### Validators v4 enforcement

- `validate_phase.sh` теперь проверяет:
  * Phase 11: нет `_agent fills_` placeholders в Fix variants → fail
  * Phase 11: нет unfilled Test strategy секций → fail
  * Phase 10a: `_adversary_review.md` > 500 байт + нет `_To be filled by agent_` → fail
  Это предотвращает «skeleton-только» аудиты.

### Manifest schema v4 расширение

- `money_columns[].business_critical`: bool — отделяет AI-token-cost (logging) от
  customer-facing balance. business_critical=false → severity max=high, не critical.
- `auth_bypass_candidates`: HTTP handlers без auth middleware (детектируются
  GitNexus cypher).
- `cross_tenant_leak_candidates`: handlers без tenant filter в multi-tenant.

### Новые промты для max MCP usage

- `prompts/00f_discover_serena_deep.md` — 8 шагов через Serena LSP:
  * Verify money endpoints через `find_referencing_symbols` (вместо ручного rg)
  * SQLi surface через `search_for_pattern` с правильным regex
  * Verify transaction bodies через `find_symbol include_body=true`
  * Multi-tenant verification
  * Auth bypass coverage
  * PII enrichment (passwords/tokens)
  * Save progress в Serena memory
- `prompts/00g_discover_gitnexus_graph.md` — 10 шагов через GitNexus:
  * `route_map` — все handlers
  * `impact upstream` для каждой transaction-функции (заранее, для phase 11)
  * `context` для money функций
  * Cypher queries: SQLi callers, auth bypass, race candidates, cross-tenant,
    N+1 (graph-based), pgvector usage
  * Сохраняет результаты в `audit/evidence/_serena_gitnexus/`
- `REFERENCE_MCP_TOOLS.md` — полная документация Serena + GitNexus tools с
  cypher cookbook (7 ready-to-use queries для DB-аудита).

### Findings calibration

- `find_money_floats.py` v2: `business_critical=false` → severity high (не critical)
- `exchange-rate` classification → severity high (не money critical)

### Smoke test (v3 vs v4 на vechkasov, 90k LOC):

```
v3: 56 findings, 10 critical (но 7 — money inflation, 0 SQLi caught)
v4: ожидается ~80 findings:
  - 14+ SQLi findings (queryRawUnsafe в library-server.ts)
  - 2-3 auth bypass (GitNexus cypher)
  - PII расширенный (passwords если есть, tokens)
  - calibrated money: 4-5 critical (только real customer-facing) вместо 7
  - phase 11 auto-populated trace+blast-radius
  - phase 10a auto-drafted adversary review
```

---


### v5.1 — closing nice-to-have backlog (2026-05-01)

Все 4 отложенных пункта v5 реализованы:

#### #5 — FK index priority by table size
`find_missing_fk_indexes.py` v5: cross-references `evidence/live/top_tables_size.txt`
для калибровки severity:
- >1M rows → critical (с exploit_proof)
- 100k-1M → high
- 10k-100k → medium
- <10k → low

В static-mode (без live evidence) — default `high` + `confidence: medium`.

#### #8 — verify_fix.md prompt
`prompts/verify_fix.md` — re-checking applied fixes для конкретных finding IDs.
- Snapshots previous run as `findings.previous.jsonl`
- Re-runs targeted detector logic per finding subcategory
- Live invariant re-verification (drift queries, etc.)
- Generates `verify_report.md` with: fixed / partial / still-open / regressed
- Updates `_meta.json` с `verify` секцией

Использование:
```
PROJECT_PATH=... FINDING_IDS=DB-TX-005,DB-MONEY-012 mode=live
```

#### #9 — ROADMAP time-budget mode
`synthesize_roadmap.py` v5.1 добавляет 3 новые секции в ROADMAP.md:
- ⚡ Quick wins (S effort) — топ-10 high-impact findings что закрываются за часы
- 📅 Sprint plan (M effort) — недельный план
- 🎯 Quarter goals (L+ effort) — архитектурные изменения
- Effort budget estimate в engineer-hours (S=2h, M=12h, L=40h, XL=160h)

#### #10 — Multi-project comparison
`validators/compare_projects.py` + `run.sh compare`:
- Severity matrix через все проекты
- Category matrix (heat-map style)
- Common subcategories (что есть в >1 проекте — паттерн команды)
- Unique findings (что есть только в одном — точечная проблема)
- Worst offenders ranking (4×critical + high score)
- Cross-project critical money/security findings list

Использование:
```bash
bash database-audit/run.sh compare /path/to/proj-a /path/to/proj-b /path/to/proj-c
# или с output:
python3 database-audit/validators/compare_projects.py /path/a /path/b -o report.md
```

---

## v5 (2026-05-01) — Autonomous master prompt + retroactive fixes

После live-mode прогона на vechkasov v4: 161 findings (включая `DB-LIVE-001` — реальная утечка денег в проде SKUDOV.NET / abiteq), 33 critical, mode=live с 8 evidence файлами. Ретроспектива выявила 7 точек улучшения.

### 🚀 Master prompt (главное)

- **`MASTER_PROMPT.md`** — единый автономный промт. Пользователь даёт только PROJECT_PATH + mode → ИИ выполняет ВСЕ stages без интерактивности:
  - Stage 0: bootstrap (install pipeline + check deps)
  - Stage 1: GitNexus auto-index (новое)
  - Stage 2: Discovery (chunked через 9 sub-prompts)
  - Stage 3: Manifest validation (autonomous, без user review)
  - Stage 4: Run all phases
  - Stage 5: Phase 11 enrichment (Fix variants A/B/C — обязательно)
  - Stage 6: Phase 10a calibration (severity inflation/deflation)
  - Stage 7: Finalize
  - Stage 8: Single-message final report

### Critical retroactive fixes

#### 1. GitNexus auto-index в init.sh
В v4 deep_dive показал `_GitNexus context unavailable_` для всех 33 critical (Section 1, 3 пусты). Причина: `gitnexus analyze` не запускался автоматически.

**Fix:** init.sh теперь auto-detects если проект не индексирован → запускает `gitnexus analyze --embeddings` автоматически. Phase 11 secs 1, 3 теперь auto-fill через GitNexus context/impact.

#### 2. Live drift verification (00b)
В v4 `DB-LIVE-001` нашли **только потому что ИИ сам додумался**. Промт не требовал этого шага.

**Fix:** `00b_discover_transactions.md` теперь обязывает: для каждой пары `(denormalized, source_aggregation)` запустить SQL invariant query. 5 готовых паттернов в шаблоне (balance/topup, wallet/spend, inventory/reservations, follower-count, totalSpent).

#### 3. Idempotency unique-constraint check (00f)
В v4 `no-idempotency` findings основывались на signature функций — медленно и неточно.

**Fix:** `00f_discover_serena_deep.md` добавил Serena LSP проверку:
- `@@unique([..., idempotency_key])` в Prisma schema
- `UNIQUE` constraint в SQL миграциях
- `Idempotency-Key` header parse в HTTP routes
3-уровневая classification: `false` / `partial` / `true`.

#### 4. Route map PII exposure (00g)
В v4 PII findings были, но **не связаны** с конкретными API endpoints.

**Fix:** `00g_discover_gitnexus_graph.md` обязывает cross-reference `route_map` с `pii_candidates`:
- Endpoint exposes PII + audit_log → OK
- Endpoint exposes PII + no audit_log → finding `DB-PII-NNN [high]`
- Endpoint exposes credentials/payment-card + no audit_log → critical

### Validator v5 enforcement

`validate_phase.sh phase 10a`:
- Required sections: `Strong findings`, `Severity calibration`, `Systematic risks` — fail если отсутствуют
- Confidence calibration: если `high > 50%` от total — обязательно секция «Confidence calibration» с обоснованием

### Smoke test on vechkasov

v4 → v5 ожидается:
- DB-LIVE-NNN findings растут (invariant verification обязателен) — больше скрытых утечек найдётся
- DB-PII-NNN с link на endpoint (route_map cross-ref) — точнее findings
- Phase 11 Section 1, 3 — реально auto-populated через GitNexus
- 99% автономность — пользователь только указывает PROJECT_PATH
