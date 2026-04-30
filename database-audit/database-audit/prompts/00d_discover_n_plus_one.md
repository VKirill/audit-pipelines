# 00d — Deep discovery: N+1 candidates (pre-validated)

> **Цель:** в manifest положить только **проверенные ручной проверкой** suspect'ы (≤ 30). Шумные heuristic кандидаты остаются для детектора `find_n_plus_one.py`.

---

## Шаги

### 1. Базовый heuristic-скан

```bash
# JS/TS
rg -nE -B 5 '(prisma\.\w+\.\w+|\.findMany|\.findFirst|\.findOne|\.findById)' \
   -g '*.{ts,tsx,js}' -g '!node_modules' . \
   | grep -E -B 5 '(for\s|forEach|\.map\(|while\s|Promise\.all\(.*\.map)' | head -100

# Python
rg -nE -B 5 '\.objects\.|session\.query|\.filter\(' --type py \
   | grep -E -B 5 '(for\s|while\s|async\s+for)' | head -100

# Go
rg -nE -B 5 '\.Find\(|\.First\(|\.Where\(' --type go \
   | grep -E -B 5 'for\s' | head -100
```

### 2. Ранжирование confidence

Для каждого кандидата прочитай контекст 10 строк выше/ниже:

| Паттерн | Confidence | Severity |
|---|---|---|
| Loop `for x of array` где `array` — результат БД-запроса, и внутри `prisma.x.findUnique({ where: { id: x.id } })` | **high** | high (если на горячем пути) / critical (с подтверждением EXPLAIN) |
| `Promise.all(items.map(i => db.query(i.id)))` | **medium** | high — параллельный N+1 жрёт connection pool |
| Loop в админ-эндпоинте / cron / report | **medium** | medium |
| Loop в bg job / migration | **low** | low — не критичен |
| Closure без зависимости от итератора (`for of array; doSomething()`) | **low** (false positive) | skip |

### 3. Заполнение manifest (≤ 30 топовых)

```yaml
hints:
  n_plus_one_candidates:
    - file: apps/crm/src/features/content/jobs/[id]/audit-export.ts
      lines: "40-65"
      inside_loop: true
      symbol: exportArticles
      # Optional: confidence (если уверен)
      confidence_hint: high
      route: "GET /jobs/:id/audit-export"
    - file: apps/crm/src/features/ads/orchestrator.ts
      lines: "120-180"
      inside_loop: true
      symbol: rebuildAdSet
      confidence_hint: medium
```

### 4. Что НЕ кладёшь в manifest

- **Сырые grep-кандидаты без верификации** — это работа `find_n_plus_one.py` детектора
- **False positives** (closure без iterator deps) — skip
- **Тесты** (`*.test.ts`, `*.spec.py`) — обычно не на hot path

### 5. Альтернативные паттерны (тоже N+1-like)

Иногда не классический N+1, но похожее по эффекту:

- **DataLoader без batching** (используется DataLoader, но `.load()` в loop без `.loadMany()`)
- **GraphQL resolver без DataLoader** (resolver делает БД-запрос на каждое поле)
- **Lazy loading в шаблоне** (Handlebars/EJS вытаскивает relation в loop)

Помечай `kind: dataloader-misuse` или `kind: graphql-resolver-leak` (можно расширить enum при необходимости — закомментируй в notes).

### 6. Quality gate

```bash
python3 -c "
import yaml
m = yaml.safe_load(open('database-audit.manifest.yml'))
n = m.get('hints',{}).get('n_plus_one_candidates',[])
print(f'n_plus_one_candidates: {len(n)} (target: 5-30)')
for c in n[:5]:
    print(f'  {c[\"file\"]}:{c[\"lines\"]}')
"
```

---

## Источники

- Mihalcea, *High Performance Java Persistence* Ch. 10
- Karwin, *SQL Antipatterns* §24 Magic Beans (косвенно)
- DataLoader documentation (Facebook/Meta — pattern)
