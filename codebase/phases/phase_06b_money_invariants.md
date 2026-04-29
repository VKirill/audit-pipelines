# PHASE 06b — MONEY & STATE INVARIANTS

**Цель:** Найти классические state-инварианты в финансово/статусно-критичных операциях: deduct→refund, idempotency, race conditions на shared state, persisted-vs-in-memory, ACID-границы. Это не security в OWASP-смысле, а **invariant safety** — где система может «потерять деньги» или «потерять/задвоить заказ» при сбое в середине операции.

**Когда запускать:** после `phase_06_security.md`. **Если в проекте нет** платежей, токенов/кредитов, заказов, бронирований, статусных машин с переходами `pending→processing→done` — пропусти и зафиксируй секцией «Не применимо: stateless API без финансового домена».

**Источники методики:**
- Pat Helland, *Life beyond Distributed Transactions* (compensation, идемпотентность).
- Jim Gray, *Notes on Data Base Operating Systems* (ACID).
- Kleppmann, *Designing Data-Intensive Applications*, Ch. 7-9 (transactions, consistency, replication).
- Nygard, *Release It!* §5 (Stability Patterns) — bulkhead, circuit breaker, timeouts.
- Microsoft Saga Pattern, AWS Step Functions reliability docs.

**Exit gate:**
- `bash audit_pipeline/scripts/validate_phase.sh 06b` возвращает 0;
- ≥ 3 findings (для M-проекта с финансовым доменом);
- evidence: `money_invariants.md` + `state_mutations.md` (≥ 2 файла);
- каждая критичная операция (платёж/refund/order) явно отмечена в `money_invariants.md` с ATOMICITY-вердиктом.

---

## 1. Входы

- Phase 02 — карта кластеров (особенно payment, billing, orders, queues).
- Phase 02b trust map — sinks SQL для денежных таблиц.
- Phase 05 error handling — наблюдения по retry/idempotency.
- Phase 09 performance — shared state mutations (если уже найдены).

---

## 2. Чек-лист действий

### 2.1. Identify financial / state-critical operations

Грепы на типичные имена:

```bash
rg -lE "deduct|refund|charge|chargeback|invoice|payment|payout|topup|withdraw|balance|credit|debit|transaction" \
   --type ts --type js --type py --type go > audit/evidence/06b_money_invariants/_money_files.txt

rg -lE "createOrder|updateOrder|cancelOrder|reserveStock|releaseStock|bookSeat|reservation" \
   --type ts --type js --type py --type go >> audit/evidence/06b_money_invariants/_money_files.txt

rg -lE "status\\s*=\\s*['\"](pending|processing|completed|failed|refunded|cancelled)" \
   --type ts --type py >> audit/evidence/06b_money_invariants/_money_files.txt
```

Если файлов 0 → секция «Не применимо», skip фазы.

### 2.2. Per-operation invariant table (`money_invariants.md`)

Для каждой критичной операции:

```markdown
| Operation | Steps | ACID? | Compensation? | Idempotent? | Persisted-state? | Risk | Finding |
|-----------|-------|-------|---------------|-------------|------------------|------|---------|
| createGenerationWorker | 1.deductTokens 2.uploadS3 3.createGeneration 4.sendResult | NO (нет $transaction) | flag tokensDeducted in ctx → refund в catch | partial (refund by status) | **NO** (ctx in-memory, SIGKILL = lost) | money loss on crash between 1 and catch | F-0018, F-0031 |
| CloudPayments webhook refund | 1.verify HMAC 2.lookup transaction 3.if not refunded → refund tokens 4.mark refunded | per-row UPDATE (atomic) | n/a | YES (status check) | YES (DB) | clean | — |
| Telegram Stars invoicePayload | 1.create payload=tx_id 2.user pays 3.webhook | n/a | invoice idempotent by payload | YES (provider-side) | YES | clean | — |
| OrderService.cancel | 1.set status=cancelled 2.releaseStock 3.refund | NO | none | NO (повтор cancel ломает stock) | partially | double-refund / wrong stock | F-NNNN |
```

Колонки:
- **Operation** — название (имя функции / endpoint).
- **Steps** — нумерованная последовательность шагов write-to-state.
- **ACID?** — обёрнуто ли в одну транзакцию БД? (`$transaction`, `BEGIN/COMMIT`, `unit_of_work`)
- **Compensation?** — есть ли явный compensation path (refund) при failure после части шагов?
- **Idempotent?** — повторный вызов с тем же ID не ломает state?
- **Persisted-state?** — флаг прогресса хранится в БД (можно восстановиться после crash)?
- **Risk** — short verdict: `clean` / `money loss on crash` / `double-spend` / `lost order` / …
- **Finding** — `F-NNNN` если выписан.

### 2.3. State mutations on shared resources (`state_mutations.md`)

Глобальные mutating writes — кандидаты на race condition:

```bash
# Node/TS
rg -nE "process\\.env\\.[A-Z_]+\\s*=" --type ts --type js
rg -nE "global\\.[a-zA-Z_]+\\s*=" --type ts --type js
rg -nE "module\\.exports\\.[a-zA-Z_]+\\s*=\\s*[a-zA-Z]" --type ts --type js  # mutable export

# Python
rg -nE "^([A-Z_]+|[a-z_]+)\\s*=\\s*" --type py | rg -v "= ('|\"|\\d|None|True|False|\\[|\\{|lambda)" | head

# In-memory caches без блокировок
rg -nE "new Map\\(\\)|new Set\\(\\)|defaultdict|OrderedDict" --type ts --type py | head
```

Каждая такая mutation в context concurrency (worker pool, async tasks, request handlers) → потенциальный race. Phase 06b проверяет:
- Кто читает эту переменную?
- Между write и read — есть ли сериализация?
- Если есть много concurrent writers — какой будет финальный value? (ответ обычно: «последний выигрывает», что часто нежелательно)

Документировать как: `<file>:<lines> mutates <var> in concurrent context (concurrency=N) — race possible when <scenario>`.

### 2.4. Saga / Compensation pattern check

Если есть multi-step distributed operations — проверь:
- [ ] Каждый шаг имеет обратный compensation шаг.
- [ ] Compensation шаги тоже идемпотентны.
- [ ] Идентификатор саги (correlation ID) логируется на каждом шаге.
- [ ] При partial failure — есть процедура «recover from logs».

Отсутствие → finding `medium`/`high` зависит от severity потерь.

### 2.5. Outbox pattern / dual-write check

Если код пишет в БД и затем публикует событие в очередь (или внешний API):

```bash
rg -nE "(commit\\(\\)|\\$queryRaw|prisma\\.\\$transaction|update.*await).*\\n.*(publish|emit|sendMessage|axios|fetch)" \
   --type ts --type js --multiline | head -20
```

Проблема: между commit и publish сервис может крашнуть — событие не отправлено, БД-запись осталась. Решение: outbox table + worker. Отсутствие → `medium`.

### 2.6. Retry vs idempotency cross-check

Из phase 05 — какие операции retry'ятся? Каждая такая должна быть idempotent. Если нет — двойное списание / двойная отправка.

### 2.7. Time-of-check / time-of-use (TOCTOU)

```javascript
// Anti-pattern:
if (user.balance >= amount) {  // CHECK
  user.balance -= amount;       // USE — два concurrent запроса оба прошли check
}
```

Грепы:
```bash
rg -nE "balance\\s*[<>]=?|balance\\s*-=" --type ts --type py --type js
```

Каждое match читай вручную: используется ли row-lock (`SELECT ... FOR UPDATE`) или atomic update (`UPDATE ... SET balance = balance - $1 WHERE balance >= $1 RETURNING *`)?

---

## 3. Quota check перед завершением

- [ ] **≥ 3 findings** для проектов с финансовым доменом (или явная «Не применимо» секция с обоснованием).
- [ ] **money_invariants.md** содержит каждую критичную операцию.
- [ ] **state_mutations.md** содержит ≥ 1 анализ shared-state race (или «не найдено»).
- [ ] Запусти `bash audit_pipeline/scripts/validate_phase.sh 06b`.

---

## 4. Артефакт — `audit/06b_money_invariants.md`

### Обязательные разделы

1. **Цель фазы** — invariant safety в финансовом / state-критическом домене.
2. **Что проверено** — список операций, проверенных на ACID/compensation/idempotency.
3. **Ключевые наблюдения**
   - Сводка money_invariants.md.
   - Самые рискованные операции.
   - Race conditions на shared state.
   - Outbox / dual-write проблемы.
4. **Находки**
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Если worker крашнется ровно после `deductTokens`, но до `createGeneration` — что произойдёт с балансом? Опиши последовательность с цитатами файлов.
   - **Q2.** Покажи операцию, которая НЕ идемпотентна. Что случится при двойной доставке webhook?
7. **Следующая фаза:** `phases/phase_07_tests.md`

---

## 5. Memory

```markdown
# Phase 06b memory
Completed: YYYY-MM-DD

Money operations summary:
- operations_total: <N>
- operations_acid: <N>
- operations_with_compensation: <N>
- operations_idempotent: <N>
- operations_persisted_state: <N>
- shared_state_race_suspects: <N>

Critical invariant gaps:
1. ...

Findings added: F-XXXX to F-YYYY (count)

Next phase: phase_07_tests.md
```

---

## 6. Отчёт пользователю

> Фаза 06b/13 завершена. Финансовых операций — <N>. С полной ACID — <K>; с compensation — <M>; идемпотентных — <I>. Race-suspects — <R>. Critical invariant gaps — <G>. Добавлено <N> findings. Перехожу к фазе 07.

Перейди к `phases/phase_07_tests.md`.
