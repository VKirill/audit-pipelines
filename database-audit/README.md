<div align="center">

  <h1>🗄️ Database Audit Pipeline <code>v2</code></h1>

  <p>
    <b>Manifest-driven глубокий аудит БД, схемы, запросов, эксплуатации.</b><br/>
    Сначала ИИ один раз сканирует проект и заполняет manifest. Дальше детекторы работают по точным путям, без эвристик.
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-v2-orange" alt="v2"/>
    <img src="https://img.shields.io/badge/architecture-manifest--driven-blue" alt="Manifest-driven"/>
    <img src="https://img.shields.io/badge/phases-11%2B2-blue" alt="11+2 phases"/>
    <img src="https://img.shields.io/badge/detectors-27-green" alt="27 detectors"/>
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

> **v2 — manifest-driven архитектура.** ИИ-модель один раз глубоко сканирует проект на стадии `init.sh` и фиксирует все найденные пути, money-колонки, transaction sites и т.д. в `database-audit.manifest.yml`. Дальше все 27 детекторов работают **строго по этому манифесту**, без эвристик «угадай где Prisma». Это даёт **универсальность для любого стека и структуры** + **прозрачность** (можно прочитать и поправить yaml перед запуском фаз).

---

## Зачем v2

В v1 каждый детектор был автономным «угадайщиком»: один искал Prisma в корневом `package.json`, другой искал миграции в `prisma/migrations/`. **На монорепо или нестандартной структуре они тихо провалились** — нашли ноль findings, агент потом всё делал руками.

В v2 эта проблема решена архитектурно:
- **Все «где?» вынесены в manifest** — ИИ заполняет один раз, точно
- **Детекторы — pure функции** `manifest → findings.jsonl`
- **Манифест валидируется** через JSON Schema + sanity thresholds
- **Промт `00_discover.md`** даёт ИИ-модели жёсткий контракт чек-листов, как искать

---

## Двухстадийный workflow

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 0: INIT — bash database-audit/init.sh             │
│                                                          │
│   1. Стейджинг промта в .audit-init.md                   │
│   2. ИИ читает prompts/00_discover.md (16 шагов)         │
│   3. ИИ глубоко сканирует проект (Serena + rg)           │
│   4. ИИ создаёт database-audit.manifest.yml              │
│   5. Validator проверяет manifest (schema + sanity)      │
│   6. Пользователь читает manifest и подтверждает         │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│  STAGE 1..N: PHASES — bash database-audit/run.sh all     │
│                                                          │
│   - Читает manifest                                      │
│   - Гоняет детекторы по фазам из phase_plan              │
│   - Каждая фаза: validate_phase.sh exit 0                │
│   - В конце: finalize.sh + _meta.json                    │
└──────────────────────────────────────────────────────────┘
```

---

## Что внутри

```
database-audit/
├── README.md                           ← ты здесь
├── 00_START_HERE.md                    ← точка входа
├── 01_ORCHESTRATOR.md                  ← правила поведения, exit gates
├── REFERENCE_TOOLS.md                  ← Serena, GitNexus, SQL utils
├── REFERENCE_BOOKS.md                  ← классика индустрии по фазам
├── TEMPLATES.md                        ← формат findings, ROADMAP, _meta.json
├── CHANGELOG.md                        ← история версий
│
├── init.sh                             ← STAGE 0 entry point
├── run.sh                              ← STAGE 1..N dispatcher
│
├── manifest.schema.yml                 ← JSON Schema манифеста
├── manifest.example.yml                ← пример заполненного манифеста
│
├── prompts/
│   ├── 00_discover.md                  ← мастер-промт для discover-фазы (16 шагов)
│   └── phase_NN_*.md                   ← инструкции каждой фазе (читают manifest.hints)
│
├── phases/                             ← evidence-bound описание каждой фазы
│   ├── phase_00_setup.md
│   ├── phase_01_inventory.md
│   ├── phase_02_schema_design.md
│   ├── phase_03_indexes_keys.md
│   ├── phase_04_query_patterns.md
│   ├── phase_05_transactions_consistency.md
│   ├── phase_05b_money_invariants.md
│   ├── phase_06_migrations_evolution.md
│   ├── phase_07_data_integrity_security.md
│   ├── phase_08_performance_scaling.md
│   ├── phase_09_observability_ops.md
│   ├── phase_10_synthesis_roadmap.md
│   ├── phase_10a_self_audit.md
│   └── phase_11_deep_dive.md
│
├── detectors/                          ← 27 pure-function детекторов
│   ├── extract_schema.py               ← Prisma/SQLAlchemy/Django/raw SQL парсер
│   ├── extract_query_inventory.py
│   ├── find_money_floats.py            ← КЛЮЧЕВОЙ для phase 02/05b
│   ├── find_n_plus_one.py
│   ├── find_missing_fk_indexes.py
│   ├── find_select_star.py
│   ├── find_string_concat_sql.py       ← SQLi surface
│   ├── find_transactions.py
│   ├── find_no_idempotency.py
│   ├── find_dangerous_ddl.py
│   ├── find_migrations.py
│   ├── find_pool_settings.py
│   ├── find_pii_in_logs.py
│   ├── find_naming_inconsistency.py
│   ├── find_json_overuse.py
│   ├── find_status_without_check.py
│   ├── synthesize_roadmap.py
│   ├── adversary_review.py
│   ├── deep_dive.py
│   └── ... ещё 8 stub-детекторов
│
├── validators/
│   ├── validate_manifest.py            ← schema + sanity thresholds
│   ├── validate_phase.sh               ← per-phase hard gate
│   ├── validate_confidence.py          ← global confidence rules
│   ├── check_evidence_citations.py     ← все file:lines резолвятся?
│   ├── generate_meta_json.py           ← _meta.json для CI
│   └── finalize.sh                     ← финальный gate
│
├── lib/
│   ├── env.sh                          ← AUDIT_DIR / PROJECT_ROOT / MANIFEST
│   └── manifest_lib.py                 ← общая Python библиотека для детекторов
│
└── scripts.v1/                         ← legacy v1 скрипты для совместимости
```

---

## Как пользоваться

### Шаг 1 — Установка

```bash
# Серена + GitNexus как в любом нашем пайплайне
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant
npm install -g gitnexus
gitnexus setup

# Зависимости пайплайна
sudo apt install jq python3 ripgrep
pip install pyyaml jsonschema

# Опционально для live mode
sudo apt install postgresql-client mysql-client
```

### Шаг 2 — Скопировать пайплайн в проект

```bash
cp -r /path/to/audit-pipelines/database-audit/ /your/project/
cd /your/project
gitnexus analyze --embeddings
```

### Шаг 3 — INIT

```bash
bash database-audit/init.sh
```

После этого открой Claude Code и дай команду:
```
Прочитай .audit-init.md и выполни discover-фазу. Создай database-audit.manifest.yml.
```

ИИ выполнит **16-шаговый discover-протокол** из `prompts/00_discover.md` и создаст манифест.

### Шаг 4 — Ревью манифеста

```bash
cat database-audit.manifest.yml | head -100
python3 database-audit/validators/validate_manifest.py database-audit.manifest.yml
```

Проверь глазами:
- Все ли money-колонки найдены? (если есть `payment/balance/charge` в коде — должны быть)
- Все ли transaction sites покрыты?
- Workspaces правильные?

При необходимости отредактируй yaml вручную.

### Шаг 5 — RUN

```bash
bash database-audit/run.sh all
```

Или по фазам:
```bash
bash database-audit/run.sh phase 02
bash database-audit/run.sh phase 05b
bash database-audit/run.sh finalize
```

Или один детектор:
```bash
bash database-audit/run.sh detector find_money_floats 02
```

### Шаг 6 — Читать результат

```bash
cat audit/ROADMAP.md           # главный артефакт
jq . audit/_meta.json          # машинная сводка
cat audit/_known_unknowns.md   # что осталось проверить
```

---

## Ключевые принципы

<table>
<tr><td><b>📋 Manifest-first</b></td><td>Все «где искать» — в manifest.yml. Детекторы не угадывают структуру проекта.</td></tr>
<tr><td><b>📂 Read-only</b></td><td>Никаких правок ни в коде, ни в БД. SELECT/EXPLAIN only в live-mode.</td></tr>
<tr><td><b>🔬 Evidence-based</b></td><td>Каждая находка — с цитатой строки/файла из manifest или live-EXPLAIN.</td></tr>
<tr><td><b>📚 По книгам</b></td><td>Каждое утверждение привязано к Date/Karwin/Winand/Kleppmann/Schwartz.</td></tr>
<tr><td><b>🔥 Money invariants</b></td><td>Phase 05b ловит race + Float + no-idempotency как critical с обязательным exploit_proof.</td></tr>
<tr><td><b>⚖️ Калибровка confidence</b></td><td><code>high</code> требует rationale ≥40 символов; <code>critical</code> требует exploit_proof.</td></tr>
<tr><td><b>🚪 Hard exit gates</b></td><td><code>validate_phase.sh</code> — exit ≠ 0 = фаза не завершена. <code>finalize.sh</code> — exit 0 = готово.</td></tr>
<tr><td><b>🧪 Sanity thresholds</b></td><td>Если в коде есть «balance» а manifest пустой — validator падает на init.</td></tr>
</table>

---

## Что v2 фиксит из v1

| Проблема в v1 | Решение в v2 |
|---|---|
| `detect_db_stack.sh` искал Prisma в корневом package.json — провал в монорепо | ИИ при init обходит **все** workspaces по чек-листу из 00_discover.md |
| Python-валидаторы хардкодили `audit/findings.jsonl` | Все читают `AUDIT_DIR` env через `lib/env.sh` и `manifest_lib.py` |
| `find_migrations.sh` не находил date-prefixed `.sql` | ИИ при init распознаёт нестандартные локации, фиксирует tool=raw-sql-by-date |
| `find_transactions.sh` ловил 0 матчей из-за rg `--type ts` | Детектор v2 читает manifest.hints.transaction_sites — список уже найденных мест |
| Детекторы тихо проваливались с 0 findings | Validator падает на sanity thresholds («есть payment слова → должны быть money_columns») |
| Нестандартный проект требовал правки кода | Можно отредактировать `database-audit.manifest.yml` без правки скриптов |
| Repeatable run = повторное сканирование | `init.sh refresh` делает только diff |

---

## Live mode vs Static mode

В manifest:
```yaml
mode:
  type: live           # или static
  live_db_url_env: DATABASE_URL
  read_only_role_required: true
```

**Static** (default) — все детекторы работают над schema-файлами и кодом из manifest.paths.

**Live** — дополнительно:
- `EXPLAIN ANALYZE` на топ-N запросов из manifest
- Реальные индексы из `pg_indexes` / `INFORMATION_SCHEMA.STATISTICS`
- Использование индексов из `pg_stat_user_indexes`
- Slow log из `pg_stat_statements` (если включён)

Live mode **ничего не пишет в БД**. Перед первым запросом — confirm read-only роль.

---

## Книги

См. [`REFERENCE_BOOKS.md`](./REFERENCE_BOOKS.md). Кратко:
- **Date** — *Database Design and Relational Theory*
- **Karwin** — *SQL Antipatterns*
- **Celko** — *SQL for Smarties*, *SQL Programming Style*
- **Winand** — *Use the Index, Luke* / *SQL Performance Explained*
- **Schwartz et al.** — *High Performance MySQL*; **Smith** — *PostgreSQL High Performance*
- **Sadalage & Ambler** — *Refactoring Databases*
- **Kleppmann** — *Designing Data-Intensive Applications*
- **Mihalcea** — *High Performance Java Persistence*
- **Helland** — *Life Beyond Distributed Transactions*
- **Bernstein & Newcomer** — *Principles of Transaction Processing*

---

<div align="center">

<a href="../README.md">← Назад к Audit Pipelines</a>

</div>
