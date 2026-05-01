# 01 — ORCHESTRATOR

**Это главный диспетчер пайплайна для STAGE 1..N (выполнение фаз).**

> **STAGE 0 (discover) описан отдельно** в `prompts/00_discover.md`. Оркестратор работает уже после того, как `database-audit/manifest.yml` создан и валиден.

---

## 1. Архитектура

```
phase_00_setup                    → manifest+evidence sanity (фаза в основном уже сделана init.sh)
phase_01_inventory                → extract_schema, extract_query_inventory, find_transactions
phase_02_schema_design            → find_money_floats, find_naming_inconsistency, find_json_overuse,
                                    find_status_without_check
phase_03_indexes_keys             → find_missing_fk_indexes, find_index_recommendations
phase_04_query_patterns           → find_n_plus_one, find_select_star, find_string_concat_sql
phase_05_transactions_consistency → find_transactions, find_isolation_levels
phase_05b_money_invariants        → find_money_floats (для money phase), find_no_idempotency,
                                    find_atomic_updates
phase_06_migrations_evolution     → find_migrations, find_dangerous_ddl, find_reversibility
phase_07_data_integrity_security  → find_string_concat_sql (SQLi), find_pii_in_logs, find_secrets_in_repo
phase_08_performance_scaling      → find_pool_settings, find_cache_strategy
phase_09_observability_ops        → find_observability, find_backup_strategy
phase_10_synthesis_roadmap        → synthesize_roadmap (генерирует skeleton, агент заполняет narrative)
phase_10a_self_audit              → adversary_review
phase_11_deep_dive                → deep_dive (только при ≥1 critical)
```

---

## 2. Контракт между фазами

```
1. run.sh phase NN  →
2.   detector1.py --manifest --phase NN  → пишет findings.jsonl + evidence/NN_*/
3.   detector2.py ...
4.   ...
5. validate_phase.sh NN  → exit 0 = фаза готова, иначе fix
6. Агент пишет database-audit/results/NN_*.md report по prompts/phase_NN_*.md
7. validate_phase.sh NN  → ещё раз с заполненным report
8. → следующая фаза
```

Детекторы добавляют findings и evidence. **Агент дополняет отчётом фазы** (`database-audit/results/NN_<name>.md`) с narrative обзором (что проверено, что найдено сверх детекторов, ограничения).

---

## 3. Правила поведения агента

### 3.1. Read-only
Никаких правок в коде проекта. И — никаких write-SQL. SELECT/EXPLAIN only. Перед первым live SQL подтверди read-only роль.

### 3.2. Evidence-based
Каждое утверждение в отчёте — со ссылкой на:
- `manifest.hints.X` (пред-найденное на discover)
- evidence-файл из детектора
- конкретные file:lines в коде

### 3.3. Калибровка confidence

| Confidence | Условия |
|------------|---------|
| `high`     | Прочитал строки и цитируешь; статически видно либо EXPLAIN; нет правдоподобного объяснения; **`confidence_rationale` ≥ 40 символов**. |
| `medium`   | Видел паттерн, но эффект зависит от данных/нагрузки; ручная валидация частична. |
| `low`      | Грубая эвристика; ручная валидация не делалась. |

**Запреты:**
- `severity: critical` без `exploit_proof` ≥ 40 символов
- `confidence: high` для performance — только если EXPLAIN, или N+1 виден статически, или FK без индекса прямо в схеме
- `confidence: high` для transaction findings без чтения тела функции

### 3.4. Запрет «допустимо»

В отчётах фаз **запрещены** формулировки: «допустимо», «приемлемо», «можно считать допустимым», «не критично, оставим». Скрипты ловят, обходить словами нельзя.

### 3.5. Manifest is source of truth

Если ты обнаружил проблему, **которая не отражена в manifest** (например, новая money-колонка, которую ИИ пропустил на discover):
1. Добавь её в `database-audit/manifest.yml` (это валидно — manifest можно править)
2. Перезапусти `validate_manifest.py`
3. Перезапусти соответствующий детектор: `bash database-audit/run.sh detector <name> <phase>`
4. Зафиксируй обновление в `database-audit/results/00_setup.md` под секцией «Manifest amendments».

### 3.6. Экономия контекста
- Не читай файлы целиком — `get_symbols_overview` сначала
- Большие файлы — диапазонами через `view_range`

### 3.7. Цитирование

Цитаты SQL и code — в `database-audit/results/evidence/NN_*/snippets/`. Это нужно чтобы `check_evidence_citations.py` резолвил все ссылки.

### 3.8. Severity

| Severity | Когда |
|----------|-------|
| `critical` | Data loss / double-spend / breach / unrecoverable. **Требует `exploit_proof`.** |
| `high` | Серьёзный perf/reliability/compliance |
| `medium` | Тех.долг с реальным impact |
| `low` | Стилистика, naming |

### 3.9. Anti-recursion

После 3 пустых ответов от инструмента → fallback на bash + ripgrep. Не зацикливайся.

---

## 4. Hard exit gates

```bash
bash database-audit/validators/validate_phase.sh NN
```

Проверяет:
1. `findings.jsonl` валидный JSON
2. Findings count ≥ scaled quota (см. таблицу + размер из manifest.project.size)
3. `confidence_rationale ≥ 40` для `high`
4. `exploit_proof ≥ 40` для `critical`
5. `location.lines` непустой для `high`
6. Required evidence файлы из `lib/env.sh:phase_required_evidence` присутствуют
7. Stop-words в отчёте отсутствуют
8. Phase-specific (10 → ROADMAP.md, 10a → adversary_review, 11 → deep_dive с секцией на каждый critical)

### Quotas (M-проект, базовые)

| Phase | Min |
|-------|-----|
| 02 | 5 |
| 03 | 3 |
| 04 | 5 |
| 05 | 3 |
| 06 | 3 |
| 07 | 3 |
| 08 | 2 |
| 09 | 2 |

Scaling по `manifest.project.size`: XS÷3, S÷2, M=1, L×2, XL×3.

---

## 5. Порядок выполнения

```bash
# Простой путь:
bash database-audit/run.sh all
bash database-audit/validators/finalize.sh

# Или по фазам с проверкой каждой:
for ph in 00 01 02 03 04 05 05b 06 07 08 09 10 10a 11; do
  bash database-audit/run.sh phase $ph
done
bash database-audit/validators/finalize.sh
```

---

## 6. Адаптация под размер проекта

Размер фиксируется в `manifest.project.size`. Validators автоматически масштабируют quotas.

| Размер | LOC | Models |
|--------|-----|--------|
| XS | < 2k | < 5 |
| S | 2k–10k | 5–15 |
| M | 10k–100k | 15–80 |
| L | 100k–1M | 80–300 |
| XL | > 1M | > 300 |

---

## 7. Fallback-протоколы

### 7.1. Manifest повреждён / отсутствует
Запусти `init.sh` (или `init.sh --refresh`). Не пытайся работать без manifest.

### 7.2. Детектор упал
1. Проверь exit code, прочитай stderr.
2. Проверь корректность `manifest.hints.<group>` для этого детектора.
3. Если детектор требует hint, который пуст — это **discover-промт пропустил**. Допиши вручную в manifest.
4. Перезапусти детектор.

### 7.3. Live mode недоступен
Зафиксируй в `database-audit/results/00_setup.md`: `mode: static`. Все findings, требующие EXPLAIN — `confidence ≤ medium`.

### 7.4. Serena недоступна
Fallback на ripgrep + Read tool в Claude Code.

---

## 8. Live mode vs Static mode

В manifest:
```yaml
mode:
  type: live | static
  live_db_url_env: DATABASE_URL
  read_only_role_required: true
```

**Live**: добавляются `EXPLAIN ANALYZE`, `pg_indexes`, `pg_stat_user_indexes`, `pg_stat_statements`. Только чтение системных таблиц.

**Static**: только manifest + код. Помечай findings, требующие EXPLAIN, как `medium` confidence с пометкой в evidence.

---

## 9. Структура артефактов

```
audit/
├── 00_setup.md
├── 01_inventory.md
├── 02_schema_design.md
├── 03_indexes_keys.md
├── 04_query_patterns.md
├── 05_transactions_consistency.md
├── 05b_money_invariants.md
├── 06_migrations_evolution.md
├── 07_data_integrity_security.md
├── 08_performance_scaling.md
├── 09_observability_ops.md
├── 10_synthesis.md
├── 10a_self_audit.md
├── 11_deep_dive.md         ← обязателен при ≥1 critical
├── ROADMAP.md              ← главный артефакт
├── findings.jsonl
├── _meta.json              ← finalize.sh
├── _known_unknowns.md
├── _adversary_review.md
└── evidence/
    ├── 01_inventory/schema_summary.json
    ├── 02_schema_design/money_floats.md
    └── ...
```

---

## 10. Возобновление сессии

1. Прочитай `database-audit/manifest.yml` — чтобы знать стек.
2. Прочитай `database-audit/results/_meta.json` если есть — статус прогресса.
3. Найди последнюю завершённую фазу (`database-audit/results/NN_*.md`).
4. Запусти `validate_phase.sh` на ней.
5. Если ok — следующая фаза. Если fail — допили текущую.

---

## 11. Финальные обязательства

`bash database-audit/validators/finalize.sh` exit 0:
- все `validate_phase.sh NN` для каждой созданной фазы
- `validate_confidence.py` глобально
- `check_evidence_citations.py` (все file:lines резолвятся)
- `database-audit/results/ROADMAP.md`, `_known_unknowns.md`, `_adversary_review.md`, `10a_*.md` присутствуют
- если есть critical — `database-audit/results/11_deep_dive.md` присутствует с секцией на каждый
- `_meta.json` сгенерирован, `verdict: pass | pass-with-conditions | fail`

Только при exit 0 — пиши пользователю tl;dr.
