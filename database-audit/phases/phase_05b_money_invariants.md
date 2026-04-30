# PHASE 05b — MONEY & STATE INVARIANTS (мини-фаза)

**Цель:** Отдельная микро-проверка денежных и счётных инвариантов. Если в проекте нет денег/балансов/инвентаря — фаза пропускается с явной записью в `audit/01_inventory.md` секция «Money detection: NONE».

**Источники:**
- Karwin, *SQL Antipatterns* — §9 Rounding Errors, §22 See No Evil.
- Helland, *Life Beyond Distributed Transactions* — идемпотентность.
- Mihalcea, *High Performance Java Persistence* — Ch. 14 Concurrency Control.

---

## 1. Входы

- `evidence/01_inventory/schema_summary.json` — поиск денежных колонок.
- `audit/05_transactions_consistency.md` — race-candidates.

## 2. Применимость

Применять, если в проекте есть **хотя бы одно** из:
- Колонки с деньгами: `amount`, `balance`, `total`, `price`, `cost`, `fee`, `commission`, `payout`, `wallet`, `salary`.
- Счётные state: `quantity`, `stock`, `inventory`, `seats_available`, `tickets_left`, `likes_count`.
- Бизнес-инвариант: `sum(transactions.amount) == account.balance`.
- Учёт: ledger / double-entry bookkeeping.

Если есть — выполняй фазу. Если нет — короткая запись «N/A, причина: …» и переход к phase 06.

## 3. Что проверяешь

### 3.1. Тип денежных колонок (Karwin §9)

- [ ] **Деньги хранятся в DECIMAL(p,s) или integer-копейках?**
- [ ] FLOAT/DOUBLE для денег → **critical** (потеря точности на каждой операции).
- [ ] DECIMAL без указания scale → проверка default scale СУБД.
- [ ] Какая валюта? Хранится отдельной колонкой `currency` или подразумевается?

### 3.2. Атомарные обновления

```sql
-- Хорошо: одно SQL-выражение, СУБД сама атомизирует
UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1;

-- Плохо: read-modify-write в коде
SELECT balance FROM accounts WHERE id = $1;  -- transaction A читает
-- (transaction B одновременно делает то же)
UPDATE accounts SET balance = $2 WHERE id = $1;  -- кто-то перетёр
```

- [ ] Все списания/начисления — атомарным `UPDATE balance = balance ± X`?
- [ ] Если есть бизнес-проверка (нельзя в минус) — она в условии WHERE: `WHERE balance >= $1`?
- [ ] Если read-modify-write неизбежен — есть `SELECT FOR UPDATE` + проверка внутри транзакции?

Каждое нарушение → **critical** с обязательным `exploit_proof`.

### 3.3. Идемпотентность

Helland: всякий клиент рано или поздно ретраит.

- [ ] У каждого денежного endpoint есть `idempotency_key` (header или body)?
- [ ] Уникальный constraint `(account_id, idempotency_key)` или подобное?
- [ ] Дубль-запрос возвращает оригинальный результат, а не повторяет операцию?

### 3.4. Double-entry bookkeeping (если есть ledger)

- [ ] Каждая транзакция — пара (debit, credit) на одинаковую сумму?
- [ ] Сумма по всем счетам = 0 (инвариант)?
- [ ] Есть периодический контроль (cron + alert при расхождении)?

### 3.5. Обработка отказов

Karwin §22 See No Evil:

- [ ] Что происходит, если update прошёл, но запись в ledger не успела? Транзакция всё атомизирует?
- [ ] Что если payment-gateway вернул success, а БД упала перед записью? Idempotency защитит при ретрае?
- [ ] Compensating transactions — есть для отмены (refund)?

### 3.6. Замок инвентаря (oversell prevention)

Стандартный сценарий: 10 билетов, 100 пользователей кликают «купить».

- [ ] `UPDATE seats SET status='reserved' WHERE id = $1 AND status='free'` — атомарный, проверка через RowsAffected?
- [ ] Или `SELECT … FOR UPDATE` + проверка + UPDATE в одной транзакции?
- [ ] Какой isolation? Под нагрузкой — нужен SERIALIZABLE или явный lock.

### 3.7. Round / truncate стратегия

- [ ] Где деньги делятся (комиссии, пропорции) — какая стратегия округления? (Banker's rounding, ROUND_HALF_UP, etc.)
- [ ] Сумма после округлений = ожидаемый total? (одна копейка может теряться).

### 3.8. Precision/scale проверка

```bash
# Найди все DECIMAL колонки
rg -nE 'DECIMAL\(' migrations/  # SQL миграции
rg -nE '@db.Decimal' prisma/  # Prisma
rg -nE 'Numeric\(' models.py  # SQLAlchemy
```

Все результаты — в evidence. Каждый случай где `scale < 2` для денежной колонки → finding.

## 4. Что обязательно делать в этой фазе

Каждое critical finding **должно** иметь `exploit_proof` с:
- Двумя параллельными запросами/транзакциями.
- Конкретным state до и после.
- Подтверждением что текущий код это допускает.

## 5. Quotas

Если фаза применима — минимум 2 findings. Если 0 findings и фаза применима — почти гарантированно ты что-то пропустил, перепроверь чек-лист.

## 6. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 05b
```

Required evidence:
- `evidence/05b_money_invariants/money_columns.md`
- `evidence/05b_money_invariants/atomic_updates.md`
- `evidence/05b_money_invariants/idempotency_coverage.md`

## 7. Артефакты

- `audit/05b_money_invariants.md`

## 8. Связь с phase 11

Если в этой фазе есть ≥ 1 critical finding — phase 11 deep-dive обязателен и должен **в первую очередь** разобрать денежные сценарии полностью (включая трассировку всех endpoint, ходящих в balance/amount).

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.money_columns` (для money_floats), `hints.money_endpoints` (для no_idempotency)

**Запуск:**
```bash
bash database-audit/run.sh phase 05b
```

После детекторов агент дополняет `audit/05b_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
