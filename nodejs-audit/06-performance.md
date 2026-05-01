# Фаза 6: Производительность

## Твоя роль

Ты — performance engineer. Твоя задача: найти узкие места и дать
приоритизированный план оптимизации.

## Предварительные требования

- Фазы 0-3 завершены.
- Прочитай `reports/01-recon.md` (стек) и `reports/03-architecture.md`
  (горячие точки в графе зависимостей).

## 4 области проверки

### Область 1: Бэкенд

#### N+1 запросы
Самая частая проблема. Что искать:

```bash
# Циклы с await внутри (часто = N+1)
grep -rEn "for.*\\{[^}]*await" src/ --include="*.ts" --include="*.js" -A 3 | head -50

# .map с async внутри
grep -rEn "\\.map\\(.*async" src/ --include="*.ts"

# forEach с await (это вообще не работает корректно)
grep -rEn "\\.forEach\\(.*async" src/ --include="*.ts"
```

Анализируй: каждый цикл с await проверь — действительно ли нужно по запросу
на элемент или можно одним запросом с `WHERE id IN (...)`.

#### Индексы БД
Если используется ORM, проверь миграции на наличие индексов для:
- Foreign keys
- Полей в WHERE условиях частых запросов
- Полей в ORDER BY
- Полей в JOIN

```bash
# Поиск миграций
find . -path "*/migrations/*" -o -path "*/prisma/migrations/*" 2>/dev/null | head -10

# Поиск индексов в схеме
grep -rEn "@@index|CREATE INDEX|@Index" --include="*.prisma" --include="*.ts" --include="*.sql" src/ prisma/ 2>/dev/null
```

#### Кеширование
- Есть ли in-memory cache (Map / LRU)?
- Есть ли Redis?
- Кешируются ли тяжёлые запросы?
- Есть ли ETag / Cache-Control headers?

```bash
grep -rEn "redis|memcached|node-cache|lru-cache" package.json
grep -rEn "Cache-Control|ETag" src/ --include="*.ts"
```

#### Блокирующие операции
```bash
# Sync операции в event loop
grep -rEn "readFileSync|writeFileSync|execSync" src/ --include="*.ts" --include="*.js"

# CPU-heavy операции без worker_threads
# (нужен ручной анализ)
```

### Область 2: Фронтенд

Только если есть фронт.

#### Bundle size
Из фазы 2 уже есть `reports/raw/build.log`.

Дополнительно:
```bash
# Запусти visualizer
npx vite-bundle-visualizer 2>/dev/null || \
  npx source-map-explorer 'dist/**/*.js' --html reports/raw/bundle.html

# Топ-10 самых тяжёлых зависимостей
# (анализируй вручную или через bundle-buddy)
```

Цели:
- Initial bundle < 200KB gzipped (отлично), < 350KB (приемлемо)
- LCP < 2.5s
- INP < 200ms
- CLS < 0.1

#### Code splitting
```bash
# Lazy imports
grep -rEn "lazy\(|import\\(" src/ --include="*.ts" --include="*.tsx"

# React: есть ли Suspense?
grep -rEn "Suspense" src/
```

#### React-specific (если React)

```bash
# Re-renders проблемы
grep -rn "useEffect.*\\[\\]" src/ --include="*.tsx"  # пустой массив зависимостей — норм, иногда плохо
grep -rEn "useMemo|useCallback|memo" src/ --include="*.tsx"

# Большие inline объекты в JSX (создаются при каждом render)
# нужен ручной анализ
```

### Область 3: Сеть

```bash
# Сжатие
grep -rEn "compression\(|gzip|brotli" src/

# HTTP/2 / HTTP/3
# (зависит от инфраструктуры, не из кода)

# CDN для статики
# (анализируй nginx/caddy конфиги если есть)
```

### Область 4: Утечки памяти

Что искать:
- Подписки на события без отписки
- setInterval / setTimeout без clearInterval
- Закрытие соединений с БД
- WebSocket'ы без cleanup

```bash
grep -rEn "setInterval\(" src/ --include="*.ts" --include="*.tsx"
grep -rEn "addEventListener\(" src/ --include="*.ts" --include="*.tsx"
```

Для каждого setInterval — проверь есть ли clearInterval.
Для каждого addEventListener — есть ли removeEventListener.

## Структура отчёта

Создай `nodejs-audit/reports/06-performance.md`:

```markdown
# Аудит производительности

Дата: <ISO>

## TL;DR
[Один абзац: общее впечатление, главные узкие места.]

## Сводная таблица проблем

| ID | Область | Серьёзность | Влияние | Сложность фикса |
|----|---------|-------------|---------|-----------------|
| PERF-001 | Бэкенд | High | N+1 на главной странице, 50+ запросов | Низкая |
| PERF-002 | Фронт | Medium | Bundle 800KB, нет code splitting | Средняя |
| ... | | | | |

## Детально по областям

### Бэкенд

#### PERF-001: N+1 в /api/users/list

**Файл:** src/users/controller.ts:34-42
**Запросов на запрос:** 1 + N (где N — количество users)

**Проблемный код:**
```typescript
const users = await db.user.findMany();
for (const user of users) {
  user.orders = await db.order.findMany({ where: { userId: user.id } });
}
```

**Как исправить:**
```typescript
const users = await db.user.findMany({
  include: { orders: true }
});
```

**Ожидаемое улучшение:** с 100 запросов до 1 (для 100 users).

#### PERF-002: ...

### Фронтенд

[...]

### Сеть

[...]

### Утечки памяти

[...]

## Lighthouse / Web Vitals (если фронт)

[Если запустил Lighthouse:]
- LCP: X.X s (цель < 2.5s)
- INP: X ms (цель < 200ms)
- CLS: X.XX (цель < 0.1)
- TBT: X ms

## Топ-5 быстрых побед (низкий effort, высокое влияние)

1. **Добавить индекс на orders.user_id** — 30 мин работы, ускорение запросов x10
2. ...

## Топ-3 средних оптимизации

1. **Добавить Redis-кеш для GET /api/products** — 1 день работы
2. ...

## Готовые промты для оптимизаций

### Промт: исправить N+1
```
В файле src/users/controller.ts на строках 34-42 есть N+1 запрос.

Перепиши, используя include или join (зависит от ORM проекта).

ВАЖНО:
- Сохрани сигнатуру публичного API
- Сохрани shape возвращаемого объекта
- Не сломай тесты
- После запусти npm run audit:test и проверь что всё ок
- Если есть бенчмарки — измерь до и после
```

### ...

## Готовность к фазе 7
- [ ] Все 4 области проверены
- [ ] Топ-5 быстрых побед определены
- [ ] Промты для оптимизаций сгенерированы
```

## Правила

- **Измеряй, не гадай.** Если можешь запустить бенчмарк — запусти.
- **Контекст важен.** Оптимизация под нагрузку 1 RPS отличается от 1000 RPS.
- **Не оптимизируй преждевременно.** Если узкого места нет — не выдумывай.
- **Указывай ожидаемое влияние.** "x10 быстрее" лучше чем "будет быстрее".

## Чего не делать

- Не оптимизируй то, что не профилировалось
- Не предлагай менять алгоритм без подсчёта сложности
- Не меняй код

## Готов? Начинай с поиска N+1.
