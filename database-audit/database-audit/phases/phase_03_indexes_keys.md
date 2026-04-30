# PHASE 03 — INDEXES & KEYS

**Цель:** Найти отсутствующие, избыточные и неиспользуемые индексы. Проверить дизайн ключей.

**Источники:**
- Markus Winand, *Use the Index, Luke* / *SQL Performance Explained* — главный источник, главы 1–8.
- Schwartz et al., *High Performance MySQL* — Ch. 7 Indexing.
- Karwin, *SQL Antipatterns* — §4 Keyless Entry, §12 Index Shotgun.

---

## 1. Входы

- `evidence/01_inventory/schema_summary.json`, `models_list.md`.
- (live) `evidence/00_setup/live_db_*` — pg_stat_user_indexes, pg_indexes.

## 2. Что проверяешь

### 2.1. Primary keys

- [ ] У каждой таблицы есть PK (без PK → critical, replication ломается).
- [ ] PK natural vs surrogate — обоснован?
- [ ] Композитный PK — оправдан или artefact «просто так»? (Karwin §3 ID Required).
- [ ] PK тип: см. phase 02 §2.8.

### 2.2. Foreign keys

- [ ] Каждая reference-колонка с FK constraint? (Karwin §4 Keyless Entry).
- [ ] **Каждая FK-колонка имеет индекс?** ← главная проверка фазы.

В большинстве СУБД индекс на FK не создаётся автоматически (исключение — MySQL InnoDB). На больших таблицах JOIN без индекса = full scan.

Запусти:
```bash
python3 database-audit/scripts/find_missing_indexes.py \
  --schema audit/evidence/01_inventory/schema_summary.json \
  > audit/evidence/03_indexes_keys/fk_without_index.md
```

Каждая FK без индекса на таблице >100k строк → **high** finding (на >1M → critical с exploit_proof «full scan на каждый JOIN, p99 latency блокирует API»).

### 2.3. Индексы для частых WHERE

Из `evidence/01_inventory/queries_inventory.md` возьми топ-N запросов. Для каждого:

- [ ] Что в WHERE? (предикаты)
- [ ] Что в ORDER BY?
- [ ] Что в GROUP BY?

Winand §2: индекс используется только если **ведущая колонка композитного индекса** в WHERE с равенством или диапазоном. Если запрос `WHERE a=? AND b=?`, а индекс `(b,a)` — индекс работает; если индекс `(a,c,b)` — `b` через skip scan только в Oracle/PG13+, иначе полу-эффективен.

В live-mode подтверди EXPLAIN-ом:
```bash
psql "$DATABASE_URL" -c "EXPLAIN (ANALYZE, BUFFERS) <query>"
```
- `Seq Scan` на больших таблицах → finding.
- `Index Scan` с большим `Filter` → индекс не покрывает все условия.
- `Sort` после Index Scan → индекс не для ORDER BY.

### 2.4. Composite vs single indexes

Winand §3: **порядок колонок имеет значение**.

- [ ] Композитные индексы есть на колонках, которые часто запрашиваются вместе?
- [ ] Покрывающие индексы (covering / INCLUDE) — есть для hot-queries?
- [ ] Partial indexes (PG: `WHERE deleted_at IS NULL`) — используются для soft-deleted данных?
- [ ] Functional / expression indexes (`LOWER(email)`) — соответствуют запросам?

### 2.5. Избыточные индексы (Index Shotgun)

Karwin §12: «индексы на каждой колонке».

- [ ] Индексы на колонках с низкой кардинальностью (boolean, status с 3 значениями) — обычно вред, кроме partial.
- [ ] Дублирующиеся индексы: `idx(a)` + `idx(a,b)` — `idx(a)` избыточен, его покрывает первый.
- [ ] Префиксные дубли: индексы где один — префикс другого.

### 2.6. Неиспользуемые индексы (live-mode)

```sql
SELECT relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

Большие индексы с `idx_scan=0` за длительный период (>30 дней работы prod) → finding (medium, рекомендация: рассмотреть удаление в phase 06 после консультации с DBA).

В static-mode перенеси в `_known_unknowns.md`.

### 2.7. Стоимость записи

Mihalcea Ch. 5: каждый индекс — оверхед на INSERT/UPDATE.

Для таблиц с интенсивной записью (logs, events, audit_trail) проверь:
- [ ] Сколько индексов? Если >5 — оправданы?
- [ ] BRIN-индексы на time-series данных рассматривались? (PG-специфика, Smith Ch. 7).

### 2.8. Special cases

- **Full-text search:** GIN/GiST в PG / FULLTEXT в MySQL / Mongo text index. Если в WHERE используется `LIKE '%x%'` или `regex` — это Karwin §16 Poor Man's Search Engine, finding на medium (low если редкий код).
- **JSON indexes:** GIN на JSONB полях. Если приложение часто ходит в `jsonb_field->>'key'` — нужен expression index или вынести в колонку.
- **Spatial indexes:** GIST на geo-данных. Если есть geo-логика без индекса → finding.

## 3. Quotas

Минимум 3 findings (M-проект). Без FK-без-индекса в проекте редкость; если 0 findings — перепроверь схему и систему миграций.

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 03
```

Required evidence:
- `evidence/03_indexes_keys/fk_without_index.md`
- `evidence/03_indexes_keys/declared_indexes.md`
- `evidence/03_indexes_keys/index_recommendations.md`
- `evidence/03_indexes_keys/unused_indexes.md` (live) или explicit «не доступно — static mode».

## 5. Артефакты

- `audit/03_indexes_keys.md`
- evidence файлы выше

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.missing_fk_indexes`, evidence/01/schema_summary.json

**Запуск:**
```bash
bash database-audit/run.sh phase 03
```

После детекторов агент дополняет `audit/03_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
