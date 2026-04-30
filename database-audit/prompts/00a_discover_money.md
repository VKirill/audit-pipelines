# 00a — Deep discovery: Money columns

> **Когда применять:** в проекте есть слова `payment | wallet | balance | invoice | charge | deduct | topup | payout | salary` в коде или схеме. Если ни одного — пропусти и явно зафиксируй в `manifest.hints.money_columns: []` с комментарием.
>
> **Quality bar:** на проектах с money-функционалом пропуск даже одной колонки = пропущенный critical в финале. Плати вниманием здесь.

---

## Шаги

### 1. Найди подозрительные колонки в схемах

Прогони по **всем** schema-файлам из `paths.schema_files`:

```bash
for f in <schema_files>; do
  rg -nE '(balance|amount|total|sum|price|cost|fee|commission|payout|salary|wallet|refund|deposit|withdraw|charge|invoice|kop|rub|usd|eur|gbp|cny|jpy|btc|eth|sat|stock|quantity|inventory|seats|tickets_left|reserved|available)' "$f"
done
```

Каждый match — потенциальный кандидат. Не каждый — money (например, `total_count` — счётчик, не деньги). Используй контекст.

### 2. Для каждого кандидата прочитай тело модели

Используя `find_symbol` или просто открывая schema-файл по диапазону:
- Какой **DB-тип**? (`Float`, `DECIMAL(p,s)`, `Numeric`, `Int`, `BigInt`, `Money` для PG)
- Какая **валюта**? (явная в имени `balanceRub` / `amountUsd`, или общая колонка `currency` в той же модели)
- Какой **класс**? balance / price / fee / payout / exchange-rate / quantity / other

### 3. Заполни `hints.money_columns`

Формат:
```yaml
hints:
  money_columns:
    - table: ContentProject
      file: packages/db/prisma/models/content.prisma
      lines: "91"          # ровно одна строка ИЛИ диапазон "89-92"
      symbol: ContentProject.balanceRub
      columns: [balanceRub]
      type: Float
      currency_hint: RUB
      classification: balance
```

**Правила:**
- Если колонки логически связаны (`amountRub`, `remainingRub`, `exchangeRate` в одной модели) — объедини в один hint с `columns: [...]`.
- `type` — точно как объявлено. `Float` ≠ `Float?` (nullable matters).
- `lines` — диапазон где они объявлены, не вся модель.

### 4. Quality gate

Прежде чем сохранять manifest, проверь:

- [ ] Если в коде есть `payment | balance | charge` слова — у меня **>= 1** money_column?
- [ ] Если есть Float/Double у money-колонки — она в hints (это будет critical)?
- [ ] Если есть `*Rub | *Usd | *Eur` — currency_hint заполнен?

**Если хоть один пункт нет — вернись к шагу 1, ты что-то упустил.**

### 5. Money endpoints (отдельная под-секция)

Money endpoints — это **функции/routes, которые меняют money state**. Они нужны для phase 05b (no_idempotency).

```bash
# Найди функции, изменяющие money_columns
for col in <money columns from step 2>; do
  rg -nE "${col}\s*[:=]" -g '*.{ts,py,go,rs,java,kt}' -g '!node_modules' .
done

# И функции с явными money-словами в имени
rg -nE 'function\s+(charge|debit|credit|refund|deduct|topUp|topup|withdraw|deposit|transfer)' \
   -g '*.{ts,py,go,rs,java,kt}' -g '!node_modules' .
```

Для каждой:
- `route` — если HTTP endpoint
- `mutation_kind`: debit / credit / transfer / charge / refund / mixed
- `has_idempotency_key` — есть ли `Idempotency-Key` header / `operation_id` параметр / уникальный constraint в схеме

**Заполни:**
```yaml
hints:
  money_endpoints:
    - file: apps/crm/src/features/content/lib/cbr.ts
      lines: "40-92"
      symbol: deductFromBalance
      mutation_kind: debit
      has_idempotency_key: false
```

### 6. Sanity check после заполнения

```bash
python3 -c "
import yaml
m = yaml.safe_load(open('database-audit/manifest.yml'))
mc = m.get('hints',{}).get('money_columns',[])
me = m.get('hints',{}).get('money_endpoints',[])
print(f'money_columns: {len(mc)}')
print(f'money_endpoints: {len(me)}')
floats = [c for c in mc if c['type'].lower() in ('float','double','real')]
print(f'  of which Float: {len(floats)} (each = critical finding)')
"
```

Если `Float != 0` и `money_endpoints == 0` — у тебя дисбаланс. Деньги хранятся, но никто их не меняет? Проверь повторно.

---

## Книги для контекста

- Karwin, *SQL Antipatterns* §9 Rounding Errors
- Mihalcea, *High Performance Java Persistence* Ch. 14 Concurrency Control
- Helland, *Life Beyond Distributed Transactions* (idempotency)
- Patrick McKenzie — *"Falsehoods Programmers Believe About Prices"* — для понимания, какие edge cases проверить
