# Phase 08 — Performance

> **Цель:** найти узкие места — N+1, sync I/O, leaks, отсутствие тайм-аутов.
>
> **Книги:** Kleppmann §1, §7, §11 · Newman BM §13.

## Inputs

- `reports/02-recon.md` — стек.
- `reports/03-deterministic.md` — npm audit, knip dups.
- `reports/04-hotspots.md` — главные hot-spots.

## Outputs

- `nodejs-audit/reports/08-performance.md`
- `nodejs-audit/reports/raw/perf-*.log`

## Шаги

### 1. N+1 паттерны

```bash
grep -rEn "for.*\\{[^}]*await" <src> --include="*.ts" --include="*.js" -A 3 2>/dev/null \
  | head -100 > reports/raw/perf-nplus1.log

# map/forEach с async
grep -rEn "\\.map\\(.*async|\\.forEach\\(.*async" <src> --include="*.ts" 2>/dev/null \
  > reports/raw/perf-async-iter.log

# real for-of с await DB
grep -rEn "for \\(.*of " <src> --include="*.ts" -A 3 2>/dev/null \
  | grep -B 1 "await " | head -50
```

Различай **legitimate sequential** (бизнес-инвариант требует порядка) и **N+1** (мог бы быть Promise.all / bulk SQL).

### 2. Sync операции

```bash
grep -rEn "readFileSync|writeFileSync|execSync|readdirSync" <src> 2>/dev/null \
  > reports/raw/perf-sync.log
```

Проверь — все ли они на startup (приемлемо) или есть в hot-handler'ах (плохо)?

### 3. Cache layers

```bash
grep -rEn "redis|memcached|node-cache|lru-cache" package.json 2>/dev/null \
  > reports/raw/perf-cache-deps.log
```

### 4. Утечки

```bash
# setInterval без clearInterval
grep -rEn "setInterval\\(" <src> --include="*.ts" --include="*.tsx" --include="*.vue" 2>/dev/null \
  > reports/raw/perf-intervals.log

# для каждого файла из above — есть ли парный clearInterval?
for f in $(awk -F: '{print $1}' reports/raw/perf-intervals.log | sort -u); do
  has_clear=$(grep -c "clearInterval" "$f")
  echo "$f: clearInterval=$has_clear"
done
```

Особенно опасны **module-level setInterval** — стартуют при импорте, нет способа остановить.

### 5. Network timeouts

```bash
# fetch без AbortController/timeout
grep -rEn "(await )?fetch\\(" <src> --include="*.ts" 2>/dev/null > reports/raw/perf-fetch.log

# axios без timeout
grep -rEn "axios\\.(get|post|put|delete|patch)\\(" <src> --include="*.ts" 2>/dev/null \
  | grep -v "timeout:" > reports/raw/perf-axios-no-timeout.log
```

### 6. Lazy / dynamic imports

```bash
grep -rEn "lazy\\(|defineAsyncComponent|import\\(" <src> 2>/dev/null \
  > reports/raw/perf-lazy.log
```

### 7. Database

```bash
# Prisma indexes
find . -name "schema.prisma" -not -path "*/node_modules/*" 2>/dev/null \
  | head -1 | xargs grep -E "@@index|@index" 2>/dev/null \
  > reports/raw/perf-db-indexes.log

# SELECT * (anti-pattern)
grep -rEn "SELECT \\* FROM" <src> --include="*.ts" 2>/dev/null | wc -l
```

### 8. Connection pools

Проверь — в monorepo с 4 PM2 процессами не делает ли каждый свой пул? Это часто missed config.

### 9. **Не запускай**

- `npm run build`, Lighthouse, бенчмарки — слишком долго для автономного аудита.
- Если нужно — записать в «manual followup».

## Шаблон отчёта `08-performance.md`

```markdown
# Performance audit

## TL;DR
[Один абзац.]

## Сводная таблица проблем

| ID | Область | Серьёзность | Сложность фикса |
|----|---------|-------------|-----------------|
| PERF-001 | <слой> | High | S/M/L |

## Бэкенд

### N+1 запросы
[Анализ raw/perf-nplus1.log + классификация legitimate vs problem]

### Блокирующие операции
[Анализ perf-sync.log — startup / hot path]

### Кеширование
- Redis/memcached: <yes/no>
- HTTP cache headers для public endpoints: <yes/no>

## Фронтенд

### Code splitting / lazy loading
[Анализ perf-lazy.log]

### Bundle size
[Если build не запускался — отметить как manual followup]

## Утечки памяти
| Файл | setInterval | clearInterval | Module-level? |
|---|---|---|---|

## Network timeouts
- fetch без timeout: <count>
- axios без timeout: <count>
- Worker-slot drain risk: <yes/no — если есть BullMQ + bare fetch>

## БД
- Prisma indexes: <count>
- SELECT *: <count>

## Топ-5 быстрых побед
1. ...
2. ...

## Готовые промты
[Будут собраны в QUICK-WINS.md в phase-12]
```

## Критерии завершения

- `reports/08-performance.md` существует.

## Сигналы в чат

- Старт: `[PHASE 08] STARTED — Performance`
- Конец: `[PHASE 08] DONE — reports/08-performance.md`

→ Переход к **phase-09-observability.md**.
