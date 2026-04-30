# 01 — ORCHESTRATOR (v1)

**Это главный диспетчер пайплайна. Ты вернёшься в этот документ между фазами.**

> Архитектурно повторяет `codebase/v3`, специализирован под БД. Все методы валидации (детерминированные exit gates, `confidence_rationale`, `exploit_proof`, anti-recursion) переиспользованы.

---

## 1. Архитектура пайплайна

Пайплайн — **11 основных фаз + 2 мини + 1 опциональная** (всё обязательное при наличии critical).

```
phase_00_setup.md                       → подготовка, детект стека, опц. live-DB connect, run_external_tools.sh
phase_01_inventory.md                   → инвентаризация БД, моделей, миграций, raw SQL
phase_02_schema_design.md               → нормализация, типы, naming, NULL/DEFAULT, constraints
phase_03_indexes_keys.md                → PK, FK, индексы, missing/redundant
phase_04_query_patterns.md              → N+1, SELECT *, JOIN-патология, EXPLAIN top-N
phase_05_transactions_consistency.md    → isolation, race, atomicity, deadlocks
phase_05b_money_invariants.md           → МИНИ: денежные/счётные/state-инварианты
phase_06_migrations_evolution.md        → обратимость, zero-downtime, backfill
phase_07_data_integrity_security.md     → PII, encryption-at-rest, RLS, SQLi surface, GDPR
phase_08_performance_scaling.md         → pooling, кэш, partitioning, репликация
phase_09_observability_ops.md           → slow log, мониторинг, бэкапы, DR
phase_10_synthesis_roadmap.md           → ROADMAP
phase_10a_self_audit.md                 → МИНИ: рефлексия, adversary review
phase_11_deep_dive.md                   → forensic-grade (обязателен при ≥ 1 critical)
```

---

## 2. Контракт между фазами

Каждая фаза:
- читает артефакты предыдущих фаз;
- выполняет проверки строго по своему чек-листу;
- **запускает `scripts/validate_phase.sh NN`** — это hard gate, exit ≠ 0 = фаза не завершена;
- записывает `audit/NN_<n>.md` — отчёт;
- добавляет находки в `audit/findings.jsonl` (с обязательными полями);
- наполняет `audit/evidence/NN_<n>/` минимум двумя файлами из обязательного списка (см. `scripts/required_evidence_files.sh NN`);
- сохраняет состояние в `.serena/memories/db_audit_phase_NN`;
- обновляет `.serena/memories/db_audit_progress`;
- возвращает управление → сообщает пользователю статус → переходит к следующей.

---

## 3. Правила поведения агента

### 3.1. Read-only
Никаких правок в коде проекта. **И — никаких записывающих SQL** в БД, даже в staging. Разрешены только `SELECT`, `EXPLAIN`, `EXPLAIN ANALYZE` (если включён read-only пользователь, у которого нет прав на write — это твоя главная страховка). Перед первым SQL подтверди, что подключение идёт под read-only ролью (`SELECT current_user, current_setting('default_transaction_read_only')` в Postgres).

### 3.2. Evidence-based

Каждое утверждение в отчёте — со ссылкой:
- на файл+строки в коде/схеме/миграции;
- или на конкретный фрагмент `EXPLAIN`;
- или на строку `evidence/*.txt|json` из `run_external_tools.sh`.

**Без цитаты конкретных строк/SQL утверждение не может попасть в отчёт.** «По всей видимости индекс отсутствует» — не finding. «`prisma/schema.prisma:42`, модель `Order`, поле `userId`, нет `@@index`» — finding.

### 3.3. Калибровка confidence

| Confidence | Условия — **все** должны быть выполнены |
|------------|-----------------------------------------|
| `high`     | (а) ты прочитал конкретные строки и цитируешь их в `evidence`; (б) проблема видна статически (схема/миграция/код), либо подтверждена EXPLAIN-ом; (в) нет правдоподобного объяснения, делающего это не проблемой; (г) **обязательно** заполнено `confidence_rationale` ≥ 40 символов и `location.lines` непустой. |
| `medium`   | (а) ты видел паттерн; (б) но эффект зависит от рантайма/нагрузки/данных, которые ты не можешь подтвердить без EXPLAIN или statistics; (в) или ручная валидация сделана только для части случаев. |
| `low`      | (а) срабатывание эвристики/grep; (б) ручная валидация не проводилась; (в) возможны false positives. |

**Запреты (нарушение = откат finding на ступень ниже):**

- `severity: critical` без поля `exploit_proof` ≥ 40 символов с конкретным сценарием (data loss / double-spend / security breach / un-recoverable state).
- `confidence: high` для performance findings, кроме трёх случаев:
  1. **EXPLAIN подтвердил** seq scan / nested loop / sort (live-mode).
  2. **N+1 виден статически** — ORM-вызов внутри for/while/.map с явной зависимостью от элемента.
  3. **FK без индекса** виден прямо в схеме.
- `confidence: high` для transaction-findings без чтения тела транзакции и явной демонстрации race-сценария.
- `confidence: high` для security-findings без либо доказательства exploit-pathway, либо подтверждения по OWASP cheatsheet.

### 3.4. Запрет «допустимо»

В отчётах фаз **запрещены** формулировки: «допустимо», «приемлемо», «можно считать», «соответствует §X (даже если не соответствует)». Если правило нарушено — пиши явно: «нарушение, причина: …, действие: …». Скрипты ловят нарушения; не пытайся обойти словами.

### 3.5. Экономия контекста

- Не читай файлы целиком, если хватит `get_symbols_overview` + точечного `find_symbol`.
- Большие миграции — по диапазонам через `view_range`.
- Перед чтением schema-файла > 500 строк — сначала `get_symbols_overview` либо `extract_schema_summary.sh` (он выдаст компактный список моделей).
- **Но если фаза требует ручной проверки тела функции/транзакции/миграции — читай**. Экономия контекста не отменяет exit gate.

### 3.6. Цитирование SQL

Все цитаты SQL — в `evidence/NN_*/snippets/` как отдельные файлы:
```
evidence/04_query_patterns/snippets/orders_list_n_plus_one.sql
evidence/04_query_patterns/snippets/orders_list_n_plus_one.code.ts
```
Это нужно чтобы цитата проходила через `check_evidence_citations.py` и оставалась читаемой при просмотре отчёта.

### 3.7. Привязка к книге

Каждая `recommendation` в finding содержит ссылку на источник. Минимум одна запись в `references` обязательна. Допустимые источники:
- Книги из `REFERENCE_BOOKS.md` с указанием главы/параграфа.
- Официальная документация СУБД (PostgreSQL, MySQL, MongoDB).
- OWASP Cheatsheet (для security findings).
- Документация ORM (Prisma docs, SQLAlchemy docs и т.д.).

«Best practice» без источника — не источник. Если нечего сослаться — finding сомнителен, либо понизь confidence, либо найди ссылку.

### 3.8. Severity

| Severity | Когда | Примеры |
|----------|-------|---------|
| `critical` | Data loss / double-spend / security breach / unrecoverable state. **Требует `exploit_proof`.** | Race в транзакции с деньгами без `SELECT FOR UPDATE`; миграция, которая удаляет колонку без backfill; SQL-инъекция через interpolation; PII в логах. |
| `high` | Серьёзный performance / надёжность / compliance, но не катастрофа. | FK без индекса на таблице >1M строк; нет idempotency на critical endpoint; backup делается, но не проверяется. |
| `medium` | Технический долг с реальным impact-ом, но без прямой угрозы. | N+1 на не-горячем пути; денормализация без причины; magic numbers в таймаутах. |
| `low` | Стилистика, naming, мелкие неточности. | Mixed-case naming таблиц; `SELECT *` в запросах с малой выборкой. |

### 3.9. Универсальность по стекам

Если стек редкий (например, Diesel + Postgres + Redis + кастомный graph-store) — **не пропускай фазу**, делай через bash + ручной обзор. Каждая фаза описывает универсальные принципы, которые применимы вне зависимости от ORM. Если конкретный детектор-скрипт стек не покрывает — фиксируй в `_known_unknowns.md`, делаешь обход вручную.

### 3.10. Anti-recursion на инструментах

После **3 пустых/одинаковых ответов** от инструмента (Serena, GitNexus, или live-DB) — переключаешься на fallback (см. §7). Не зацикливайся.

---

## 4. Hard exit gates

После каждой фазы **обязательно**:

```bash
bash database-audit/scripts/validate_phase.sh NN
```

Скрипт проверяет:
1. `audit/findings.jsonl` валидный JSON по строкам.
2. Количество findings фазы ≥ scaled quota (см. таблицу ниже × масштабатор размера проекта из §6).
3. Все `high` имеют `confidence_rationale` ≥ 40 символов и `location.lines` непустой.
4. Все `critical` имеют `exploit_proof` ≥ 40 символов.
5. В `audit/evidence/NN_*/` присутствуют все файлы из `required_evidence_files.sh NN`.
6. В отчёте `audit/NN_*.md` нет «допустимо», «приемлемо» (стоп-слов).
7. Каждая ссылка на файл:строки резолвится (`check_evidence_citations.py` — глобально на финале).

### Базовые квоты findings (M-проект, 10k–100k LOC)

| Phase | Min findings | Logic |
|-------|--------------|-------|
| 00 setup | 0 | подготовка |
| 01 inventory | 0 | описательная |
| 02 schema | 5 | даже у хорошего проекта найдётся 5 типизационных/naming/normalization шероховатостей |
| 03 indexes | 3 | минимум один FK без индекса встречается почти всегда |
| 04 queries | 5 | N+1, SELECT *, неоптимальный JOIN |
| 05 transactions | 3 | хотя бы isolation level не задан явно |
| 05b money | 2 если применимо, 0 если нет | пропуск только если в проекте нет денег/счётчиков (это решение фиксируется в `audit/01_*.md`) |
| 06 migrations | 3 | irreversible / dangerous DDL почти всегда есть |
| 07 security | 3 | encryption-at-rest, audit log, PII классификация |
| 08 performance | 2 | pooling/кэш |
| 09 ops | 2 | DR test почти никогда не проводился |
| 10 synthesis | 0 | агрегирующая |
| 10a self-audit | 0 | рефлексия |
| 11 deep-dive | — | по необходимости |

Меньше квоты = `validate_phase.sh` падает. Если действительно проблем меньше — уменьшай scope проекта (через `audit_phase_00.md` → `size: XS/S`), масштабатор сам пересчитает.

---

## 5. Порядок выполнения

```
1. phase_00_setup → создать audit/, проверить инструменты, run_external_tools.sh.
2. phase_01_inventory → описать все БД, ORM, модели, миграции, raw SQL.
3. phase_02_schema_design → дизайн схемы.
4. phase_03_indexes_keys → ключи и индексы.
5. phase_04_query_patterns → паттерны запросов (+ EXPLAIN если live-mode).
6. phase_05_transactions_consistency → транзакции, isolation, race.
7. phase_05b_money_invariants → ЕСЛИ применимо.
8. phase_06_migrations_evolution → миграции.
9. phase_07_data_integrity_security → безопасность данных.
10. phase_08_performance_scaling → масштабирование.
11. phase_09_observability_ops → ops.
12. phase_10_synthesis_roadmap → ROADMAP черновик.
13. phase_10a_self_audit → adversary review → возможен возврат к фазам.
14. phase_11_deep_dive → если ≥ 1 critical.
15. bash database-audit/scripts/finalize.sh → exit 0 = готово.
16. Финальный tl;dr пользователю.
```

**Между фазами не импровизируй.** Если во время фазы N заметил находку для фазы M>N — запиши в `.serena/memories/db_audit_cross_phase_notes`, в фазе M проверь системно.

---

## 6. Адаптация под размер проекта

Размер БД считается отдельно от размера кода. В `phase_00_setup.md` фиксируешь оба, для квот используется **наибольший**.

| Размер | LOC кода | Моделей/таблиц | Корректировка квот |
|--------|----------|----------------|-------------------|
| XS | < 2k | < 5 | квоты ÷ 3 (мин. 1) |
| S | 2k–10k | 5–15 | квоты ÷ 2 |
| M | 10k–100k | 15–80 | квоты как в §4 |
| L | 100k–1M | 80–300 | квоты × 2, семплируй топ-30 моделей |
| XL | > 1M | > 300 | квоты × 3, разбей на подсхемы/bounded context |

`validate_phase.sh` берёт размер из `.serena/memories/db_audit_phase_00`. Если файла нет — считает M.

---

## 7. Fallback-протоколы

### 7.1. Serena недоступна
**Признаки:** `activate_project` не работает, `find_symbol` пусто.

**Протокол:**
1. `get_current_config` — активен ли проект.
2. Повтори `activate_project` с абсолютным путём.
3. Если стабильно не работает — переключись на bash + ripgrep:
   - `find_symbol` → `rg -n "function <name>|class <name>|def <name>"`
   - `find_referencing_symbols` → `rg -n "<name>"` с фильтром по типу файлов
   - `search_for_pattern` → `rg -E "<pattern>"`
4. Зафиксируй в `audit/00_setup.md` ограничение.
5. **Глубина анализа НЕ падает**, только скорость.

### 7.2. GitNexus недоступен
1. Прочитай `gitnexus://repo/{name}/schema` — могла измениться схема.
2. Адаптируй cypher без сложных WHERE/JOIN.
3. Если 3 попытки пустые — fallback на ручной импорт-граф через ripgrep.

### 7.3. Live-DB недоступна
**Признаки:** `DATABASE_URL` не задан, или `psql --version` отсутствует, или connection rejected.

**Протокол:**
1. Зафиксируй в `audit/00_setup.md`: «mode = static-only».
2. Все findings, требующие EXPLAIN, помечай `confidence: medium` максимум, добавляй пометку в `evidence`: «требует EXPLAIN ANALYZE для подтверждения».
3. Перенеси задачу в `_known_unknowns.md`: «Phase 04 — top-10 query plans not verified live».
4. **Не пропускай фазы**. Static-mode достаточно для 70% findings.

### 7.4. ORM не детектируется автоматически
1. Проверь `package.json`/`requirements.txt`/`go.mod`/`composer.json` вручную.
2. Если стек кастомный (raw `pg.Pool`, raw `database/sql`) — фиксируй стек = `raw`, переходи к ручному обзору.
3. Не считай отсутствие ORM проблемой само по себе.

### 7.5. Миграции не находятся
Возможные причины:
- Миграции живут в отдельном репо.
- Миграции применяются вручную через DBA.
- Используется declarative-схема (Atlas, Skeema) без классических миграций.

В каждом случае — спроси пользователя в `phase_00_setup.md`. Не выдумывай отсутствие миграций как finding.

---

## 8. Live mode vs Static mode

Пайплайн поддерживает два режима, оба полностью рабочие:

### Static mode (по умолчанию)
- Схема извлекается из манифестов ORM (`prisma/schema.prisma`, `models.py`, `*.entity.ts`).
- Миграции — из директорий миграций.
- Запросы — из исходного кода.
- N+1 — эвристически (запрос внутри loop).
- Индексы — задекларированные в схеме (не в реальной БД).

### Live mode (если задан `DATABASE_URL`)
Дополнительно к static:
- `EXPLAIN ANALYZE` на топ-N запросов из `extract_query_inventory.sh`.
- Реальные индексы из `pg_indexes` / `INFORMATION_SCHEMA.STATISTICS`.
- Статистика использования индексов из `pg_stat_user_indexes` (mark unused).
- Slow query log из `pg_stat_statements` (если включён).
- Размер таблиц — `pg_relation_size` / `INFORMATION_SCHEMA.TABLES`.

**Live mode тебе ничего не разрешает писать в БД.** Только чтение системных таблиц и `EXPLAIN`. Перед первым live-вызовом подтверди read-only роль (см. §3.1).

---

## 9. Структура артефактов на выходе

```
audit/
├── 00_setup.md
├── 01_inventory.md
├── 02_schema_design.md
├── 03_indexes_keys.md
├── 04_query_patterns.md
├── 05_transactions_consistency.md
├── 05b_money_invariants.md      ← мини, опционально
├── 06_migrations_evolution.md
├── 07_data_integrity_security.md
├── 08_performance_scaling.md
├── 09_observability_ops.md
├── 10_synthesis.md
├── 10a_self_audit.md            ← обязательный
├── 11_deep_dive.md              ← обязательный при ≥ 1 critical
├── ROADMAP.md                   ← ГЛАВНЫЙ РЕЗУЛЬТАТ
├── findings.jsonl
├── _meta.json                   ← генерируется finalize.sh
├── _known_unknowns.md           ← Phase 10a
├── _adversary_review.md         ← Phase 10a
└── evidence/
    ├── 01_inventory/
    ├── 02_schema_design/
    ├── 03_indexes_keys/
    ├── 04_query_patterns/
    └── ...
```

---

## 10. Возобновление сессии

1. Прочитай `.serena/memories/db_audit_progress`.
2. Прочитай `.serena/memories/db_audit_phase_XX` для последней завершённой фазы.
3. Прочитай `audit/findings.jsonl` и `audit/_meta.json` (если есть).
4. Запусти `bash database-audit/scripts/validate_phase.sh XX` — убедись, что предыдущая фаза прошла gate.
5. Если не прошла — допили её. Если прошла — следующая.

---

## 11. Финальные обязательства

Пайплайн считается завершённым только если **`bash database-audit/scripts/finalize.sh` возвращает 0**. Скрипт проверяет:

- все `validate_phase.sh NN` для каждой созданной фазы;
- `validate_confidence.py` (глобальное распределение confidence-уровней vs severity);
- `check_evidence_citations.py` (все цитаты резолвятся);
- `audit/ROADMAP.md`, `audit/_known_unknowns.md`, `audit/_adversary_review.md`, `audit/10a_*.md` присутствуют;
- если есть critical findings — `audit/11_*.md` присутствует;
- `audit/_meta.json` сгенерирован, `verdict: pass`;
- пользователю отдан финальный tl;dr.

Теперь перейди к `REFERENCE_TOOLS.md`.
