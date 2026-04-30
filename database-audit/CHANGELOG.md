# CHANGELOG

## v2 (2026-04-30) — Manifest-driven architecture

Полная переработка архитектуры. Главная идея: **ИИ один раз глубоко сканирует проект на стадии `init.sh` и фиксирует все факты в `database-audit.manifest.yml`. Дальше детекторы работают строго по манифесту, без эвристик.**

### Что нового

- **`init.sh`** — единственная точка входа в discover-фазу
- **`prompts/00_discover.md`** — мастер-промт ИИ-модели на 16 шагов с жёстким контрактом
- **`manifest.schema.yml`** — JSON Schema манифеста (валидируется через jsonschema)
- **`manifest.example.yml`** — пример заполненного манифеста для Prisma-монорепо
- **`run.sh`** — диспетчер фаз: `run.sh all`, `run.sh phase 05b`, `run.sh detector <name>`
- **27 детекторов** в `detectors/` — pure functions `manifest → findings.jsonl`
- **`validators/validate_manifest.py`** — schema + sanity thresholds (детектит «есть `balance` слова в коде, но manifest пустой»)
- **`lib/env.sh`** + **`lib/manifest_lib.py`** — универсальный env layer (AUDIT_DIR/PROJECT_ROOT/MANIFEST)

### Решено из v1

| Проблема v1 | Решение v2 |
|---|---|
| `detect_db_stack.sh` искал Prisma в корневом package.json — fail в монорепо | ИИ при init обходит все workspaces по чек-листу |
| Python-валидаторы хардкодили путь | Все читают AUDIT_DIR env через manifest_lib |
| `find_migrations.sh` не находил date-prefixed sql | ИИ распознаёт нестандартные локации, tool=raw-sql-by-date |
| `find_transactions.sh` ловил 0 матчей | Детектор v2 читает hints.transaction_sites — список уже найденных мест |
| Детекторы тихо проваливались | Validator падает на sanity thresholds |
| Нестандартный проект требовал правки кода | Можно отредактировать manifest.yml без правки скриптов |
| Repeatable run = повторное сканирование | `init.sh --refresh` делает только diff |

### Детекторы (27)

**Inventory:**
- `extract_schema.py` — Prisma/SQLAlchemy/Django/raw SQL parser
- `extract_query_inventory.py`

**Phase 02 — Schema:**
- `find_money_floats.py` ← КЛЮЧЕВОЙ для phase 02 + 05b
- `find_naming_inconsistency.py`
- `find_json_overuse.py`
- `find_status_without_check.py`

**Phase 03 — Indexes:**
- `find_missing_fk_indexes.py`
- `find_index_recommendations.py` (stub)

**Phase 04 — Queries:**
- `find_n_plus_one.py`
- `find_select_star.py`
- `find_string_concat_sql.py`

**Phase 05/05b — Transactions/Money:**
- `find_transactions.py`
- `find_isolation_levels.py` (stub)
- `find_no_idempotency.py`
- `find_atomic_updates.py` (stub)

**Phase 06 — Migrations:**
- `find_migrations.py`
- `find_dangerous_ddl.py`
- `find_reversibility.py` (stub)

**Phase 07 — Security:**
- `find_pii_in_logs.py`
- `find_secrets_in_repo.py` (stub)

**Phase 08 — Performance:**
- `find_pool_settings.py`
- `find_cache_strategy.py` (stub)

**Phase 09 — Ops:**
- `find_observability.py` (stub)
- `find_backup_strategy.py` (stub)

**Phase 10/10a/11 — Synthesis:**
- `synthesize_roadmap.py`
- `adversary_review.py`
- `deep_dive.py`

### Совместимость

- Старая v1 структура сохранена в `scripts.v1/` — можно использовать на проектах, где не работает manifest подход
- Формат findings.jsonl не менялся — `audit/findings.jsonl` совместим между v1 и v2
- ROADMAP.md, _adversary_review.md, _known_unknowns.md, _meta.json — структура та же

---

## v1 (2026-04-30) — Initial release

Первый релиз. См. `scripts.v1/` для исходных детекторов.

- 11 основных фаз + 2 мини (05b money, 10a self-audit) + 1 опциональная (11 deep-dive)
- Детерминированные `validate_phase.sh` / `finalize.sh` как hard gates
- Static-mode и live-mode (с `DATABASE_URL`)
- 11 bash/python детекторов
