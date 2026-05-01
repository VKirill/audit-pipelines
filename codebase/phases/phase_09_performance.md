# PHASE 09 — PERFORMANCE

**Цель:** Найти статически видимые перф-риски. Без профайлера мы не можем измерить реальное — но можем увидеть паттерны, которые практически всегда создают проблему.

**Источники:**
- Knuth — «premature optimization is the root of all evil» (мы не оптимизируем, а ищем **уже совершённые** грехи).
- Fowler, *PoEAA* — Lazy Load, N+1, Identity Map.
- Kleppmann, *Designing Data-Intensive Applications* — нагрузка, индексы.
- Grigorik, *High Performance Browser Networking* (для фронта).
- SRE Book — capacity management.

**Exit gate этой фазы:**
- **≥ 3 findings** для M-проекта;
- **обязательно**: hot-path анализ для топ-10 центральных символов;
- **обязательно**: confidence для всех findings кроме 3 разрешённых случаев — **`medium` максимум**;
- минимум 2 файла в `audit/evidence/09_performance/`: `hotpath_analysis.md` + `n_plus_one_suspects.md`;
- ≥ 150 строк в отчёте.

**Правило confidence для этой фазы (критичное!):**

`high` разрешён **только** для:
- **Sync I/O в async контексте** — ты видишь `fs.readFileSync` / `requests.get` внутри `async def` или Node handler.
- **Unbounded memory cache** — ты видишь `cache = {}` без TTL, max size, или eviction policy.
- **N+1 с явным подтверждением** — ты прочитал цикл и видишь ORM-вызов внутри, не просто импорт ORM.

Для всего остального — `medium` максимум (даже если паттерн классический). Причина: без профайлера реальное влияние не подтверждено.

---

## 1. Входы
- Фаза 01 — hot-spots файлы.
- Фаза 02 — central symbols (узкие места обычно там).
- Фаза 03 — heavy зависимости.
- Фаза 05 — long transactions (могут быть perf-риском).

---

## 2. Чек-лист проверок

### 2.1. Hot path analysis (ОБЯЗАТЕЛЬНО — главная проверка фазы)

Из фазы 02 у тебя есть топ-30 символов по in-degree. Для топ-10:

- [ ] Для каждого: `find_symbol include_body=true` / ручное чтение тела.
- [ ] Для каждого заполни строку таблицы:

  | Символ | Файл | callers | Вызовов/sec (оценка) | Найденные паттерны | Worst паттерн |
  |--------|------|---------|----------------------|--------------------|----|
  | `getTranslation` | ... | 261 | hot (per user action) | sync I/O: нет, N+1: нет, hot loop: нет | — |
  | `queryOne` | ... | 81 | hot (per request) | pagination: есть, N+1: возможно в `/admin/*` | N+1 |

- [ ] Сохрани в `audit/evidence/09_performance/hotpath_analysis.md`.
- [ ] Центральный символ с явно медленной операцией внутри → finding `high` (попадает в одно из 3 разрешённых).

### 2.2. Database patterns

#### N+1 queries (Fowler) — обязательный sweep
Один из самых распространённых и дорогих смелов.

- [ ] ORM-специфичные индикаторы в цикле:
  - Django: `.objects.all()` + в цикле обращение к ForeignKey без `select_related` / `prefetch_related`.
  - SQLAlchemy: `.query.all()` + lazy-load в цикле.
  - JPA/Hibernate: `@OneToMany` без `FetchType.LAZY` + явного `JOIN FETCH`.
  - Mongoose: `.find()` + `.populate()` в цикле.
  - Prisma/TypeORM: `.find()` без `include`.
  - Rails/ActiveRecord: `.all` + `.each` без `includes`.
- [ ] grep:
  ```bash
  grep -rPzoE "\.objects\.all\(\)(?![^\n]*select_related|[^\n]*prefetch)" --include="*.py" <src>
  grep -rPzoE "for\s+\w+\s+in\s+.+\.all\(\)" --include="*.py" <src>
  grep -rnE "forEach|for\s*\(" --include="*.ts" <src> | grep -v test  # нужен ручной просмотр
  ```
- [ ] Сохрани список кандидатов в `audit/evidence/09_performance/n_plus_one_suspects.md`.
- [ ] **Для каждого кандидата прочитай окружение** (10–20 строк до и после). Подтверди, что цикл действительно содержит DB-вызов.
- [ ] Подтверждённый N+1 в hot path → finding `high`. Подозрение без подтверждения → `medium`.

#### Запросы без индексов

- [ ] Миграции — есть ли `CREATE INDEX` для часто фильтруемых колонок?
- [ ] Фильтрация по неиндексируемому полю (если видно из where-clause + миграций) → finding `low` с рекомендацией profile.
- [ ] `SELECT *` в hot-path → `medium`.

#### SELECT в цикле
- [ ] grep — SQL/ORM query внутри for-loop. Часто идёт вместе с N+1.

#### Missing pagination

- [ ] Эндпоинты `/list`, `/search`, `/all` — принимают ли `limit`, `offset` / `cursor`?
- [ ] Отсутствие пагинации на коллекционных эндпоинтах → `medium`/`high`.

#### Большие `IN (…)` / `WHERE id IN`
- [ ] Если список генерируется из другой таблицы — должен быть JOIN, не round-trip + IN.

#### Транзакции с внешними вызовами
Из фазы 05 — перенеси сюда в сводку как перф-риск тоже.

### 2.3. Алгоритмическая сложность

- [ ] Вложенные циклы над коллекциями:
  ```bash
  grep -rPzoE "for .* in .*:\s*\n\s*for .* in" --include="*.py" <src>
  grep -rPzoE "\.forEach\([^)]*\.forEach\(" --include="*.ts" --include="*.js" <src>
  ```
- [ ] Для каждого — проверить размер внутренней коллекции. Линейный скан внутри цикла для N>1000 → `medium`.
- [ ] `.indexOf()` / `.includes()` в цикле для поиска → `low` (следует Set/Map).
- [ ] Синхронные операции в цикле, когда могут быть параллельными (`Promise.all`, `asyncio.gather`, `errgroup`) → `low`/`medium`.

### 2.4. Memory patterns

- [ ] Загрузка всего файла в память когда можно стримом:
  - `fs.readFileSync` для больших файлов, `open().read()` без размера.
- [ ] Большие arrays / dicts без освобождения:
  - Long-lived module-level caches без TTL / max size.
- [ ] **Unbounded caches** (один из 3 разрешённых `high`):
  ```bash
  grep -rnE "self\.\w*cache\s*=\s*\{\}" --include="*.py" <src>
  grep -rnE "const \w*[Cc]ache\s*=\s*new Map\(\)" --include="*.ts" <src>
  ```
  Проверь окружение — есть ли eviction? Если нет → finding `high`.
- [ ] Memory leaks в JS: closures с большими контекстами, event listeners без cleanup — трудно автоматически; flag только если видно много `addEventListener` без off.

### 2.5. I/O patterns

#### Sync I/O в асинхронных контекстах (разрешённый `high`)

- [ ] Node.js: `fs.readFileSync`, `fs.writeFileSync`, `execSync` в хэндлерах request/job:
  ```bash
  grep -rnE "readFileSync|writeFileSync|execSync" --include="*.ts" --include="*.js" <src> | grep -v test
  ```
  Для каждого — прочитай окружение. В async функции / request handler / worker → finding `high`.
- [ ] Python asyncio: обычные `requests.get`, `time.sleep` внутри `async def`:
  ```bash
  grep -rB 5 "time\.sleep\|requests\.(get\|post\|put)" --include="*.py" <src> | grep -B 5 "async def"
  ```
- [ ] Go: блокирующие вызовы в горутинах без timeout/ctx → `medium`.

#### Много мелких HTTP-запросов к одному хосту
- [ ] Если видно цикл с `requests.get` / `fetch` к одному API → `medium` (batch/bulk endpoint).

#### HTTP client без connection pooling
- [ ] Python: каждый раз новый `requests` (должен быть `Session`).
- [ ] Node: `http.request` без агента с keep-alive.
- [ ] Java: новый `HttpClient` на каждый вызов.
- [ ] → `medium`.

### 2.6. Frontend-specific (если есть клиент)

- [ ] React: inline функции/объекты в props → re-renders. Локально `low`.
- [ ] Массивные bundle-импорты: `import _ from 'lodash'` вместо `import get from 'lodash/get'` → `medium`.
- [ ] Отсутствие code splitting (`React.lazy`, dynamic `import()`) в SPA > 1MB → `medium`.
- [ ] Не-оптимизированные изображения (`<img>` без `loading="lazy"`, без размеров) → `low`.
- [ ] Рендер больших списков без virtualization → `medium`.

### 2.7. Caching strategy

- [ ] Есть ли кэш вообще (Redis, Memcached, in-memory)?
- [ ] Кэширование дорогих чистых функций — оправдано.
- [ ] Кэширование user-specific данных в глобальном кэше без ключа пользователя → `high` (data leak, это и security).
- [ ] Отсутствие инвалидации / TTL → `medium`.
- [ ] Thundering herd protection (single-flight) — отсутствие в hot cache → `low`.

### 2.8. Concurrency bugs indicators

Статически поймать гонки сложно, смотрим на индикаторы:
- [ ] Shared mutable state без синхронизации (module-level mutable vars в concurrent code).
- [ ] Go: `go func()` без WaitGroup или без `ctx`.
- [ ] Python threading + shared dict/list без Lock.
- [ ] Double-checked locking (классический баг).

Всё это — `medium` с пометкой «требует verification via runtime analysis».

### 2.9. Connection pools

- [ ] DB: задан ли pool size? (дефолты часто 5 — мало для production).
- [ ] HTTP: keep-alive и max connections.
- [ ] Отсутствие явной конфигурации пулов при > 100 RPS → `medium`.

### 2.10. Existing benchmarks / profiling artifacts

- [ ] `find_file`: `benchmarks/`, `bench/`, `*.bench.*`, `jmh`, `criterion.rs`, `pytest-benchmark`, `k6`, `locust`.
- [ ] Наличие — positive signal.
- [ ] Отсутствие perf-тестов при утверждении «high-performance» в README → finding `low`.

---

## 3. Важное ограничение

**Без профилировщика в production мы не можем утверждать**, что именно тормозит. Все findings этой фазы имеют `confidence: medium` максимум, **кроме трёх разрешённых случаев** (см. шапку).

Формулировка для medium: «Паттерн X в коде обычно приводит к Y. Подтвердить требуется на реальной нагрузке.»

**Если ты обнаруживаешь, что у тебя получилось > 2 `high` findings вне разрешённых случаев — вернись и пересмотри каждый на `medium`.**

---

## 4. Quota check перед завершением

- [ ] **≥ 3 findings** для M-проекта.
- [ ] Hot-path таблица заполнена для **топ-10 центральных символов** (минимум).
- [ ] N+1 candidate list составлен.
- [ ] Правило confidence соблюдено: не более 3 `high` и все они из разрешённых случаев.

---

## 5. Артефакт — `audit/09_performance.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено**
3. **Ключевые наблюдения**
   - **Hot path analysis** — ссылка на evidence + 3-5 главных выводов.
   - **Database risks** — таблица N+1, missing pagination, selects in loop.
   - **Algorithmic risks** — список.
   - **Memory risks** — список.
   - **I/O risks** — список с цитатами строк.
   - **Frontend-specific** (если применимо).
   - **Caching strategy** — анализ.
4. **Находки**
5. **Неполные проверки** (вся фаза — без профайлера частично неполная; зафиксировать это честно)
6. **Контрольные вопросы**
   - **Q1.** Если завтра нагрузка вырастет в 10×, какие 3 места сломаются первыми? Обоснуй кодом.
   - **Q2.** Есть ли способ измерить текущие p50/p95/p99 для hot path без модификации кода? Если нет → добавь это в ROADMAP как часть observability-эпика.
7. **Следующая фаза:** `phases/phase_10_synthesis_roadmap.md`

---

## 6. Memory

```markdown
# Phase 09 memory
Completed: YYYY-MM-DD

Performance posture:
- hotpath_symbols_analyzed: <N>
- n_plus_one_suspects: <N>
- n_plus_one_confirmed: <N>
- sync_io_in_async: <N>
- unbounded_caches: <N>
- missing_pagination: <N>

Top 3 scalability risks:
1. <описание с цитатами>
2. <описание с цитатами>
3. <описание с цитатами>

Next phase: phase_10_synthesis_roadmap.md
```

---

## 7. Отчёт пользователю

> Фаза 9/10 завершена. Производительность: проанализированы <N> hot-path символов, <M> подозрений на N+1 (<K> подтверждено), <X> мест с sync I/O в async, <Y> unbounded caches. Без профайлера большая часть findings имеет confidence=medium (сознательное ограничение). Добавлено <N> findings. Перехожу к фазе 10 — синтез и ROADMAP.

Перейди к `phases/phase_10_synthesis_roadmap.md`.
