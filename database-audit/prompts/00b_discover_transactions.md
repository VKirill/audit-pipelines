# 00b — Deep discovery: Transactions & race conditions

> Это **главный** источник `critical` findings после Float-money. Pleась, сделай эту фазу аккуратно.

---

## Шаги

### 1. Где транзакции есть (inventory)

Используя `lib/stack_aware.py` patterns:

```bash
# Prisma
rg -nE '\$transaction\s*\(' -g '*.{ts,tsx,js}' -g '!node_modules' .

# SQLAlchemy
rg -nE '(session\.begin|with_for_update|transaction\.atomic)' -g '*.py' .

# GORM
rg -nE '\.Transaction\s*\(|db\.Begin' -g '*.go' .

# Knex / Sequelize / TypeORM
rg -nE '\.transaction\s*\(' -g '*.{ts,js}' -g '!node_modules' .
```

Зафиксируй каждое **место использования** с `kind: explicit-transaction`.

### 2. Где должны быть, но НЕТ — главная задача

Это **read-modify-write** паттерны без транзакции.

#### 2.1. Поиск кандидатов

Для каждой money-колонки из `hints.money_columns`:
```bash
col="balanceRub"  # пример
# Все функции, которые и читают, и пишут эту колонку
rg -nE -B 3 -A 30 "${col}" -g '*.{ts,py,go}' -g '!node_modules' . \
  | grep -B 30 -A 3 "(update|set|=).*${col}"
```

Прочитай каждое функцию глазами:
- [ ] Есть ли SELECT/find** перед UPDATE/save (read-modify-write)?
- [ ] Внутри ли `prisma.$transaction` / `db.transaction` / `session.begin`?
- [ ] Используется ли atomic UPDATE (`balance = balance - $1`) — этот безопасен даже без явной транзакции?

#### 2.2. Stock/inventory колонки

Те же проверки для:
- `quantity`, `stock`, `inventory`
- `seats_available`, `tickets_left`, `slots`
- `reserved`, `taken`, `used`

### 3. External I/O внутри транзакций (антипаттерн Helland)

```bash
# Найди транзакционные блоки
rg -nE -A 30 '\$transaction\s*\(\s*(?:async\s*)?\(' \
   -g '*.{ts,tsx,js}' -g '!node_modules' . \
   | grep -E '(fetch\(|axios\.|http\.|sendMail|publish\(|kafka\.|webhook|stripe)'
```

Каждое попадание — `kind: external-io-inside-transaction` (high finding).

### 4. Заполнение manifest

```yaml
hints:
  transaction_sites:
    # Главное — kind: missing-transaction для critical race candidates
    - file: apps/crm/src/features/content/lib/cbr.ts
      lines: "40-92"
      symbol: deductFromBalance
      kind: missing-transaction
      note: "Read top-ups, update each in loop, aggregate, write balance — no $transaction. Money-related."
    # Inventory сайтов с транзакциями
    - file: apps/crm/src/features/orders/checkout.ts
      lines: "120-180"
      symbol: createOrder
      kind: explicit-transaction
      isolation: "default (READ COMMITTED)"
    # External IO внутри tx
    - file: apps/crm/src/features/notify/handler.ts
      lines: "55-78"
      symbol: notifyAndSave
      kind: external-io-inside-transaction
      note: "fetch к webhook внутри $transaction"
```

### 5. Optimistic vs pessimistic locking

Дополнительно зафиксируй (для phase 05):
- Где есть `@Version` / `version` колонка в моделях
- Где `SELECT ... FOR UPDATE` / `with_for_update` / `forUpdate()`
- Где `SELECT ... FOR UPDATE SKIP LOCKED` (queue-pattern)

Эти места — `kind: row-lock-for-update` или `optimistic-version`. Не findings сами по себе, но контекст для phase 05.

### 6. Quality gate

```bash
python3 -c "
import yaml
m = yaml.safe_load(open('database-audit/manifest.yml'))
ts = m.get('hints',{}).get('transaction_sites',[])
miss = [t for t in ts if t['kind'] == 'missing-transaction']
mc = m.get('hints',{}).get('money_columns',[])
print(f'transaction_sites total: {len(ts)}')
print(f'  missing: {len(miss)}')
print(f'money_columns: {len(mc)}')
if mc and not miss:
    print('  WARN: money columns exist but no missing-transaction sites — verify')
"
```

---

## Книги

- Bernstein & Newcomer, *Principles of Transaction Processing* §6 Locking
- Kleppmann, *Designing Data-Intensive Applications* Ch. 7 Transactions
- Helland, *Life Beyond Distributed Transactions*
- Mihalcea, *High Performance Java Persistence* Ch. 14

---

## 🔴 v5 — Live drift verification (если mode: live)

> **Это findings уровня DB-LIVE-001 на vechkasov v4.** Без этого шага скрытые утечки в проде остаются невидимыми.

### Шаг: invariant queries для каждого denormalization

Для каждой пары `(denormalized_field, source_aggregation)`:

```sql
-- Шаблон: balance vs sum(top-ups)
SELECT p.id, p.name,
       p.<denormalized_col> AS denormalized,
       COALESCE(t.computed, 0) AS computed,
       p.<denormalized_col> - COALESCE(t.computed, 0) AS drift
FROM <parent_table> p
LEFT JOIN (
  SELECT <fk_col>, SUM(<source_col>) AS computed
  FROM <source_table> GROUP BY <fk_col>
) t ON t.<fk_col> = p.id
WHERE ABS(p.<denormalized_col> - COALESCE(t.computed, 0)) > 0.01;
```

### Действия по результату

- **drift > 0.01 на N клиентах** → НЕМЕДЛЕННО создать finding `DB-LIVE-NNN`:
  - `severity: critical`, `confidence: high` (это **факт** в проде, не теория)
  - `exploit_proof`: «Не нужен — drift УЖЕ существует в проде на момент аудита»
  - `recommendation`: 1) urgent SQL sync, 2) fix root-cause race, 3) add monitoring
  - Сохранить `evidence/live/balance_drift.txt` с конкретными ID/числами

- **drift = 0** → отметить в evidence что invariant holds

### Известные кандидаты (общие паттерны)

| Денормализация | Source | Когда применять |
|---|---|---|
| `account.balance` | `SUM(transactions.amount)` | если есть transactional ledger |
| `project.balanceRub` | `SUM(top_ups.remainingRub)` | FIFO balance |
| `wallet.totalSpent` | `SUM(charges.amount)` | spending denorm |
| `inventory.available` | `total - SUM(reservations.qty)` | inventory pre-aggregation |
| `user.followerCount` | `COUNT(follows WHERE followee=user)` | social counters |

Если в проекте есть любая из этих пар — обязательно invariant check.
