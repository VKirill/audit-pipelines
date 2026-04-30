# PHASE 04 — QUERY PATTERNS

**Цель:** Найти неоптимальные / опасные паттерны запросов. N+1, SELECT *, неэффективные JOIN, бесконтрольная пагинация, missing indexes на runtime.

**Источники:**
- Winand, *Use the Index, Luke* — Ch. 4 Join, Ch. 5 Clustering, Ch. 6 Sorting and Grouping.
- Vlad Mihalcea, *High Performance Java Persistence* — Ch. 10 Relationships (N+1, fetch strategies), Ch. 4 Batch Updates.
- Karwin, *SQL Antipatterns* — §14–18, §24.
- Celko, *SQL for Smarties* — §6 Set Theory.

---

## 1. Входы

- `evidence/01_inventory/queries_inventory.md`.
- `evidence/03_indexes_keys/*` — какие индексы есть.
- (live) `evidence/00_setup/live_db_*` — pg_stat_statements top-N.

## 2. Что проверяешь

### 2.1. N+1 (Mihalcea Ch. 10)

Это **самая частая проблема** в ORM-проектах. Симптом: список из 100 элементов делает 101 запрос (1 для списка + 100 для each).

Запусти:
```bash
bash database-audit/scripts/find_n_plus_one.sh > audit/evidence/04_query_patterns/n_plus_one_suspects.md
```

Скрипт ищет:
- ORM-вызовы (`prisma.user.findMany`, `Order.objects.filter`, `User.find`) **внутри** loop / map / forEach.
- Lazy-loading паттерны (`@OneToMany(fetch = LAZY)` + использование в сериализаторе).
- `await Promise.all(items.map(i => db.query(...)))` — параллельный N+1, тоже бьёт по пулу.

Для каждого suspect:
- Прочитай контекст 10 строк выше и ниже.
- Если действительно N+1 — finding (severity зависит от того, на горячем ли пути).
- На горячем пути → high (если EXPLAIN не подтверждён) / high+exploit_proof → critical.
- На холодном (admin reports, cron) → medium.

**Confidence для N+1 — `high` допустимо** только если:
- Цикл прямо в коде (виден статически).
- Внутри цикла вызывается ORM-метод с зависимостью от `item`.
- Нет prefetch/include/joinedload на родительском запросе.

Иначе — `medium` с пометкой «требует профайлинга / EXPLAIN».

### 2.2. SELECT * (Karwin §18)

```bash
bash database-audit/scripts/find_select_star.sh > audit/evidence/04_query_patterns/select_star.md
```

`SELECT *` опасен:
- Возвращает лишние данные → memory + bandwidth.
- Ломается при ALTER TABLE добавлении колонки (особенно с BLOB/JSON).
- В ORM может тащить связи неявно.

Severity:
- В hot path → medium-high.
- В отчётах/cron → low.
- В JOIN с большой таблицей где много колонок → high.

### 2.3. JOIN-патология

Winand Ch. 4: типы JOIN-планов:
- **Nested Loop** — оптимально для малых результатов с индексом.
- **Hash Join** — оптимально для больших равенств.
- **Merge Join** — оптимально на отсортированных данных.

Что искать в коде:
- [ ] JOIN без условия на индексированной колонке.
- [ ] LEFT JOIN, использующийся как INNER JOIN (no NULL handling после).
- [ ] CROSS JOIN или Cartesian (FROM a, b без ON).
- [ ] JOIN >5 таблиц на горячем пути — Karwin §17 Spaghetti Query, рекомендация: разбить, или использовать CTE/materialized view.

Live-mode:
```sql
EXPLAIN (ANALYZE, BUFFERS) <query>;
```
- `Nested Loop` с большим `loops` count и `rows × loops > 10^6` → finding.

### 2.4. Pagination

- [ ] **OFFSET-based pagination** на больших таблицах? Это Karwin косвенно (через perf antipattern). Симптом: `LIMIT 20 OFFSET 10000` сканирует 10020 строк.
- [ ] **Keyset pagination** (cursor-based, `WHERE id > last_id`) используется? — рекомендация для больших списков.

Если только OFFSET и нет keyset — finding (medium, на горячем пути — high).

### 2.5. LIKE и поиск

Karwin §16 Poor Man's Search Engine:
- [ ] `LIKE '%pattern%'` — leading wildcard блокирует индекс. → Использовать full-text search (GIN/GiST/MATCH AGAINST/ts_vector).
- [ ] `LIKE 'pattern%'` (trailing) — может использовать btree-индекс.
- [ ] `regex` в WHERE → почти всегда seq scan.

### 2.6. ORDER BY и LIMIT без индекса

Winand Ch. 6:
- [ ] `ORDER BY x LIMIT N` — есть индекс на `x`? (или на `(filter, x)` для покрывающего).
- [ ] `ORDER BY x DESC LIMIT N` — для PG нужен либо `ORDER BY x DESC` индекс, либо обычный (PG может сканировать в обратную сторону).

### 2.7. Aggregations

Karwin §14 Ambiguous Groups:
- [ ] `GROUP BY` со всеми non-aggregated колонками? (в строгом SQL — обязательно, в MySQL slack-режиме — опасно).
- [ ] `COUNT(*)` на больших таблицах — есть приближённое подсчёт (PG: `pg_class.reltuples`)?
- [ ] `DISTINCT` вместо корректного JOIN → smell.

### 2.8. Раздельные запросы вместо batch

Mihalcea Ch. 4: цикл `INSERT` × N вместо `INSERT … VALUES (…), (…), (…)`.
- [ ] `for x in items: db.insert(x)` без batching?
- [ ] ORM `bulk_create` / `createMany` / `INSERT … VALUES` используется где надо?

### 2.9. Top slow queries (live-mode)

Из `pg_stat_statements`:
```sql
SELECT query, calls, total_exec_time, mean_exec_time, rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_%'
ORDER BY mean_exec_time DESC LIMIT 30;
```

Для топ-10:
- [ ] EXPLAIN ANALYZE.
- [ ] Если `Seq Scan` или `Sort` без индекса → finding.
- [ ] Если `Buffers: shared read=>>shared hit` — холодные данные, кэш недоиспользован.

В static-mode — только на основе кода, помечай medium confidence.

## 3. Quotas

Минимум 5 findings (M-проект).

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 04
```

Required evidence:
- `evidence/04_query_patterns/n_plus_one_suspects.md`
- `evidence/04_query_patterns/select_star.md`
- `evidence/04_query_patterns/explain_topN.md` (live) или explicit «static-mode».

## 5. Артефакты

- `audit/04_query_patterns.md`
- evidence файлы выше + `snippets/` с цитатами SQL/code

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.n_plus_one_candidates`, `paths.query_files`

**Запуск:**
```bash
bash database-audit/run.sh phase 04
```

После детекторов агент дополняет `audit/04_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
