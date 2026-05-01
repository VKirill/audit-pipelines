# PHASE 05 — TRANSACTIONS & CONSISTENCY

**Цель:** Найти проблемы атомарности, изоляции, race conditions, deadlocks, идемпотентности.

**Источники:**
- Bernstein & Newcomer, *Principles of Transaction Processing* — §6 Locking, §7 System Recovery.
- Kleppmann, *Designing Data-Intensive Applications* — Ch. 7 Transactions, Ch. 9 Consistency and Consensus.
- Pat Helland, *Life Beyond Distributed Transactions* — идемпотентность.
- Vlad Mihalcea, *High Performance Java Persistence* — Ch. 14 Concurrency Control.

---

## 1. Входы

- `evidence/01_inventory/transactions_list.md`.
- Список денежных/счётных операций — для phase 05b.

## 2. Что проверяешь

### 2.1. Покрытие транзакциями

Bernstein §1: транзакция должна покрывать **полное бизнес-действие**, не только одну запись.

- [ ] Создание заказа (orders + order_items + reserve stock) — в одной транзакции?
- [ ] Списание баланса + запись в ledger — в одной?
- [ ] Каскадное удаление вручную через несколько DELETE — в одной?
- [ ] Endpoint, делающий два write на разные таблицы без транзакции → finding (high).

### 2.2. Isolation level

Kleppmann §7.2: weak isolation levels допускают аномалии.

| Аномалия | RC (Read Committed) | RR (Repeatable Read) | SI (Snapshot) | SER (Serializable) |
|----------|---------------------|----------------------|---------------|--------------------|
| Dirty read | предотвращён | предотвращён | предотвращён | предотвращён |
| Non-repeatable read | возможен | предотвращён | предотвращён | предотвращён |
| Phantom read | возможен | возможен в MySQL/RR* | возможен в SI* | предотвращён |
| Lost update | возможен | зависит от движка | возможен | предотвращён |
| Write skew | возможен | возможен | возможен | предотвращён |

*Postgres SI и MySQL InnoDB RR имеют свои нюансы — см. главу 7 Kleppmann.

Действия:
- [ ] Какой default isolation в проекте? (`SHOW default_transaction_isolation` для PG, `SELECT @@tx_isolation` для MySQL).
- [ ] Где явно повышается до `SERIALIZABLE` или `REPEATABLE READ`?
- [ ] Если default `READ COMMITTED` (PG/Oracle) и в проекте есть денежные операции без `SELECT FOR UPDATE` — почти гарантированно finding (high+).

### 2.3. Lost update / Write skew

Bernstein §6.3:

**Сценарий lost update:** два транзакции читают значение, обе вычисляют новое, обе пишут — одно перетёрлось.

Где искать:
- [ ] Балансы (account.balance, wallet.amount).
- [ ] Счётчики (likes_count, view_count).
- [ ] Stock/inventory (product.quantity).
- [ ] Reservation patterns (booking_seats).

Защиты:
- `SELECT … FOR UPDATE` (pessimistic).
- Optimistic locking через `version` колонку (`UPDATE … WHERE version = old_version`).
- Atomic SQL: `UPDATE accounts SET balance = balance - $1 WHERE id = $2` (без read-modify-write в коде).
- `SERIALIZABLE` isolation.

Каждое место с `read → calc → write` без защиты → finding.

**Confidence: high допустимо** только если:
- Прочитал тело транзакции (через `find_symbol include_body=true`).
- Подтвердил отсутствие FOR UPDATE через grep по файлу.
- Подтвердил isolation level (или показал, что default прокатывает).
- Заполнил `exploit_proof` пошаговым сценарием race.

### 2.4. Phantom read и range queries

Kleppmann §7.2.4:
- [ ] Запросы с диапазоном (`WHERE created_at BETWEEN`) внутри транзакции с RR/RC?
- [ ] Подсчёт `COUNT` + `INSERT` (anti-EAV pattern booking) без serializable → write skew.

### 2.5. Deadlocks

- [ ] Какой порядок захвата локов? Если несколько транзакций берут локи в разном порядке — потенциальный deadlock.
- [ ] `LOCK TABLES` / `LOCK TABLE` явный — если есть, это редко удачно.
- [ ] Retry-логика на deadlock detected — есть? Большинство ORM не делают auto-retry.

### 2.6. Транзакции и I/O

Helland (paper):
- [ ] HTTP-запрос внутри транзакции — antipattern, лок держится пока ходит наружу.
- [ ] Email-send внутри транзакции — то же.
- [ ] Любой external call → должен быть после commit или через outbox pattern.

Это **частая** проблема в ORM-кодах: запихнули всё в `prisma.$transaction(async (tx) => { … fetch(...) … })`.

### 2.7. Длительные транзакции

- [ ] Транзакция, начатая в начале endpoint и закрытая в конце, может быть слишком длинной.
- [ ] Bulk-операции (`UPDATE … WHERE … 1M строк`) в одной транзакции — блокирует таблицу. Лучше batch-апдейт.
- [ ] Backfill-миграции в одной транзакции — phase 06.

### 2.8. Idempotency (Helland)

- [ ] Endpoints, выполняющие финансовые/state-changing операции, имеют `idempotency_key`?
- [ ] Уникальный constraint на `(operation_type, idempotency_key)` обеспечивает at-most-once?
- [ ] Ретраи клиентов учитываются? (мобильное приложение всегда ретраит).

Без idempotency на критичных endpoint → finding (severity зависит от criticality).

### 2.9. Outbox pattern

Если проект публикует события (Kafka, Redis pub/sub, webhooks):
- [ ] Используется outbox pattern? (запись в таблицу `outbox` в той же транзакции, отправка отдельным процессом).
- [ ] Или отправка идёт прямо из endpoint после commit? — может потерять событие при падении между commit и send.

### 2.10. Save-and-publish race

- [ ] Read-after-write: `db.save(x); return x;` — может возвращать stale данные если есть replication lag и read из реплики.
- [ ] CQRS / event sourcing проекты — отдельная история, добавь в `_known_unknowns.md`.

## 3. Quotas

Минимум 3 findings (M-проект). Реалистично — 5–10.

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 05
```

Required evidence:
- `evidence/05_transactions_consistency/transaction_coverage.md`
- `evidence/05_transactions_consistency/isolation_levels.md`
- `evidence/05_transactions_consistency/race_candidates.md`

## 5. Артефакты

- `audit/05_transactions_consistency.md`

---

## Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.transaction_sites` (kind: missing-transaction, external-io-inside-transaction)

**Запуск:**
```bash
bash database-audit/run.sh phase 05
```

После детекторов агент дополняет `audit/05_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
