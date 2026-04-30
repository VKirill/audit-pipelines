# TEMPLATES — форматы артефактов

Формат важен: по нему строится итоговый ROADMAP **и** работают валидаторы из `scripts/`. Отклонение от схемы → `validate_phase.sh` падает и фаза не считается завершённой.

---

## 1. Finding (запись в `audit/findings.jsonl`)

**Формат:** JSON Lines — одна находка = одна строка валидного JSON.

### Схема

```json
{
  "id": "DB-0042",
  "phase": 5,
  "category": "transaction",
  "subcategory": "lost-update",
  "severity": "critical",
  "confidence": "high",
  "title": "Race condition в списании баланса — отсутствует SELECT FOR UPDATE",
  "location": {
    "file": "services/payments/charge.ts",
    "symbol": "PaymentService.charge",
    "lines": "88-104",
    "db_object": "accounts.balance"
  },
  "evidence": "В транзакции (строки 88-104) сначала SELECT balance FROM accounts WHERE id=$1, проверка balance >= amount, затем UPDATE accounts SET balance = balance - $2. Между SELECT и UPDATE нет блокировки. Изоляция READ COMMITTED (default), параллельные транзакции прочитают одно и то же значение balance.",
  "confidence_rationale": "Прочитал тело метода charge() через find_symbol include_body=true (строки 88-104). Подтвердил отсутствие FOR UPDATE через rg 'FOR UPDATE' в services/payments/. Изоляцию подтвердил из app config (db.config.ts:15: isolation default). Сценарий race воспроизводим без рантайма.",
  "exploit_proof": "Два параллельных запроса POST /charge {amount: 100} с balance=100. Транзакция A: SELECT balance=100 → проверка ok → UPDATE -100. Транзакция B (параллельно): SELECT balance=100 → проверка ok → UPDATE -100. Результат: balance=-100 (минус), деньги списаны дважды.",
  "impact": "Прямая возможность двойного списания клиента или ухода в минус. На charge endpoint трафик 50 RPS в пике (логи nginx). Реальные потери возможны в часы пикового трафика.",
  "recommendation": "1) Добавить SELECT … FOR UPDATE в начале транзакции. 2) Поднять isolation до REPEATABLE READ или SERIALIZABLE для charge(). 3) Добавить unique constraint на (account_id, idempotency_key) — критическая защита от ретраев.",
  "effort": "M",
  "references": [
    "Bernstein & Newcomer, Principles of Transaction Processing, §6.3 Lost Updates",
    "Karwin, SQL Antipatterns, §16 Poor Man's Search Engine — анти-pattern, обратная сторона того же",
    "Kleppmann, Designing Data-Intensive Applications, §7.2 Weak Isolation Levels",
    "Helland, Life Beyond Distributed Transactions"
  ],
  "related_findings": ["DB-0018"],
  "status": "open"
}
```

### Обязательные поля

| Поле | Тип | Обязательность |
|------|-----|----------------|
| `id` | `DB-NNNN` | всегда |
| `phase` | int 0–11 | всегда |
| `category` | строка | всегда |
| `severity` | `critical`/`high`/`medium`/`low` | всегда |
| `confidence` | `high`/`medium`/`low` | всегда |
| `title` | строка ≥ 10 символов | всегда |
| `location.file` | путь | всегда |
| `location.lines` | `N-M` или `N` | всегда (НЕ пустая строка) |
| `location.db_object` | таблица/колонка/индекс | если применимо |
| `evidence` | ≥ 40 символов | всегда |
| `confidence_rationale` | ≥ 40 символов | **обязательно если `confidence: high`** |
| `exploit_proof` | ≥ 40 символов | **обязательно если `severity: critical`** |
| `impact` | строка | всегда |
| `recommendation` | строка | всегда |
| `effort` | `S`/`M`/`L`/`XL` | всегда |
| `references` | array, минимум 1 элемент | всегда |
| `status` | `open`/`accepted`/`rejected` | всегда — на этапе аудита всегда `open` |

### Категории

| Category | Применяется в фазе |
|----------|-------------------|
| `inventory` | 01 |
| `schema` | 02 |
| `index` | 03 |
| `query` | 04 |
| `transaction` | 05 |
| `money` | 05b |
| `migration` | 06 |
| `security` | 07 |
| `pii` | 07 |
| `performance` | 08 |
| `ops` | 09 |
| `meta` | 10a (находки про сам аудит) |

---

## 2. Отчёт фазы (`audit/NN_*.md`)

Каждый отчёт фазы строго следует этой структуре:

```markdown
# Phase NN — <Название>

**Source books:** <главные книги фазы из REFERENCE_BOOKS>
**Mode:** static | live
**Time spent:** ~XX min

## 1. Что проверено

Краткий пересказ чек-листа фазы — что прошёл по факту.

## 2. Сводка

Таблица или 5–10 пунктов — главные факты по БД с этой фазы.

## 3. Findings

Перечисление findings, добавленных в этой фазе. Каждый — кратко (id, severity, title, ссылка на location). Подробности в JSONL.

## 4. Что не проверено / ограничения

Чего не сделал и почему. Перенос в `_known_unknowns.md` если это блокер для другой фазы.

## 5. Артефакты

Список файлов в `audit/evidence/NN_*/`.
```

---

## 3. ROADMAP.md

Главный артефакт. Формат:

```markdown
# Database Audit ROADMAP

**Project:** <name>  | **Stack:** <db + ORM>  | **Date:** YYYY-MM-DD  | **Mode:** static | live

## TL;DR

5–7 пунктов — что главное.

## Verdict

`pass` | `pass-with-conditions` | `fail`

Если `fail` — что блокирует прод, кратко.

---

## 🔴 Сейчас (Now)

Critical и high-impact с low effort.

### DB-0042 — Race в charge() [critical]
**Где:** `services/payments/charge.ts:88-104`, таблица `accounts`
**Почему сейчас:** возможность двойного списания, 50 RPS в пике.
**Как:** SELECT FOR UPDATE + unique constraint(account_id, idempotency_key).
**Effort:** M (1-2 дня).
**Источник:** Bernstein & Newcomer §6.3, Kleppmann §7.2.

[аналогично для каждого critical/high-now]

---

## 🟡 Дальше (Next)

High с medium effort, medium с большим impact.

[аналогично]

---

## 🟢 Потом (Later)

Долг, который надо знать, но не срочно.

[аналогично]

---

## Карта по категориям

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| schema   | 0 | 2 | 5 | 3 |
| index    | 0 | 4 | 1 | 0 |
| query    | 0 | 1 | 6 | 2 |
| transaction | 1 | 1 | 0 | 0 |
| money    | 1 | 0 | 0 | 0 |
| ...      | ... |

## Sequencing notes

Порядок не от severity, а от последовательности изменений:
- Перед index changes — VACUUM ANALYZE.
- Перед миграцией money — backup verify.
- Изменения схемы под нагрузкой — multi-step (Sadalage & Ambler).

## Источники

[перечень книг и док из всех findings, дедуплицированный]
```

---

## 4. `_meta.json`

Машинная сводка для CI/dashboards. Генерируется `finalize.sh`.

```json
{
  "version": "1.0",
  "pipeline": "database-audit",
  "pipeline_version": "v1",
  "generated_at": "2026-04-30T12:00:00Z",
  "project": {
    "path": "/path/to/project",
    "size": "M",
    "git_head": "abc1234",
    "branch": "main"
  },
  "stack": {
    "databases": ["postgresql"],
    "orms": ["prisma"],
    "models_count": 42,
    "migrations_count": 87
  },
  "mode": "live",
  "phases_completed": ["00","01","02","03","04","05","05b","06","07","08","09","10","10a"],
  "findings_total": 78,
  "by_severity": { "critical": 1, "high": 12, "medium": 38, "low": 27 },
  "by_category": { "schema": 11, "index": 5, "query": 14, "transaction": 4, "money": 2, "migration": 8, "security": 6, "performance": 8, "ops": 5, "pii": 3, "meta": 12 },
  "verdict": "pass-with-conditions",
  "blockers": ["DB-0042"]
}
```

---

## 5. `_known_unknowns.md`

```markdown
# Known unknowns

Что осталось непроверенным и почему. Каждый пункт — будущая задача.

## Static-mode limitations
- [ ] EXPLAIN ANALYZE на топ-30 запросов — требует live DATABASE_URL.
- [ ] Реальное использование индексов (vs декларированных) — pg_stat_user_indexes.
- [ ] Slow queries — pg_stat_statements не включён в текущей среде.

## Cross-DB consistency
- [ ] Postgres + Redis: счётчик баланса в кэше Redis vs reality в Postgres — не сверено.

## Прочее
- [ ] Миграции live-тестирование на реальном объёме данных не выполнено.
```

---

## 6. `_adversary_review.md`

```markdown
# Adversary review (Phase 10a)

«Если бы я был защитником этой кодовой базы и хотел оспорить аудит — на что бы я указал?»

## Слабые findings

### DB-0017 — потенциальный N+1
**Адвокат:** запрос внутри loop вызывается только в админ-эндпоинте, max 100 элементов на страницу.
**Аудитор:** согласен, понизил до medium → low.

### DB-0029 — индекс на created_at
**Адвокат:** таблица 50k строк, full scan быстрее random IO по индексу для запросов с диапазоном > 50%.
**Аудитор:** требует EXPLAIN на реальных данных. Помечен `low` confidence в static-mode.

## Сильные findings (ничего не оспаривается)

### DB-0042 — race в charge()
Воспроизводим из кода + конфига, exploit_proof проверен пошагово. Подтверждено.

## Систематические риски аудита

- Static-mode: 14 findings помечены требующими EXPLAIN. Реальный prod может изменить severity.
- Stack-blindness: проект использует кастомный wrapper над pg.Pool, часть запросов могла остаться скрытой. Перенесено в _known_unknowns.
```
