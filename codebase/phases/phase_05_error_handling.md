# PHASE 05 — ERROR HANDLING & RESILIENCE (v2)

**Цель:** Как код ведёт себя, когда что-то идёт не так. Не проявятся ли отказы в production.

**Источники:**
- Nygard, *Release It!* 2e — гл. 5 «Stability Patterns» (Timeouts, Circuit Breaker, Bulkhead, Steady State, Fail Fast), гл. 4 «Antipatterns».
- Martin, *Clean Code* гл. 7 «Error Handling».
- Google SRE Book — graceful degradation, retries with jitter.
- Hunt & Thomas, *Pragmatic Programmer* — Design by Contract, Assertive Programming.

**Exit gate этой фазы:**
- **≥ 5 findings** для M-проекта;
- **обязательно**: выполнен полный sweep всех `catch`/`except` блоков (с учётом **каждого** fallback-grep'а, не sample);
- обязательно: таблица внешних вызовов с указанием наличия/отсутствия таймаута;
- минимум 2 файла в `audit/evidence/05_error_handling/`: `catch_blocks.txt` + `external_calls_timeouts.md`;
- ≥ 150 строк в отчёте.

---

## 1. Входы
- Все предыдущие отчёты.
- Список внешних интеграций (из фазы 02 cross-cutting или фазы 03).

---

## 2. Чек-лист проверок

### 2.1. ОБЯЗАТЕЛЬНО — полный sweep catch-блоков

**Это главная проверка фазы. Не пропускай даже при деградации Serena.**

- [ ] Выполни grep-sweep по всему репо:
  ```bash
  # Python
  grep -rn "except" --include="*.py" <src> > /tmp/all_catches_py.txt
  # JS/TS
  grep -rn "catch\s*(" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" <src> > /tmp/all_catches_js.txt
  # Java/C#
  grep -rn "catch\s*(" --include="*.java" --include="*.cs" <src> >> /tmp/all_catches_js.txt
  # Go (специально — if err != nil)
  grep -rn "if err != nil" --include="*.go" <src> > /tmp/all_catches_go.txt
  ```
- [ ] Сохрани объединённый результат в `audit/evidence/05_error_handling/catch_blocks.txt`.
- [ ] Посчитай общее число `catch`/`except`/`if err != nil`. Если их > 100 — семплируй топ-50 по подозрительности (см. ниже).

### 2.2. Swallowed errors (проглоченные исключения) — главный smell

**Nygard: «Never Let Errors Die Silently».**

- [ ] Пустые catch-блоки. Паттерны для grep:
  ```bash
  # Python — пустой except с pass
  grep -rPzl "except[^:]*:\s*\n\s*pass" --include="*.py" .
  # JS/TS — пустой catch
  grep -rPzl "catch\s*\([^)]*\)\s*\{\s*\}" --include="*.ts" --include="*.js" .
  # JS/TS — catch с только комментарием
  grep -rPzl "catch\s*\([^)]*\)\s*\{\s*//[^}]*\}" --include="*.ts" --include="*.js" .
  ```
- [ ] Только логирование без rethrow/обработки (log-and-forget):
  - Python: `except\s*.*:\s*\n\s*logger\.(warning|error).*\n\s*(pass|return\s*($|None))`
  - JS/TS: `catch\s*\([^)]*\)\s*\{[^}]*console\.(log|error|warn)[^}]*\}` (без `throw`)
- [ ] Go: `err :=` где err затем `_ =` присваивается, или не проверяется:
  ```bash
  grep -rnE "_\s*,?\s*_\s*:?=" --include="*.go" <src>
  grep -rnE "^\s*_\s*=\s*\w+\.\w+\(" --include="*.go" <src>
  ```
- [ ] Каждое подтверждённое проглатывание (не false positive) → finding `high` (в бизнес-логике) или `medium` (auxiliary).

### 2.3. Pokemon catch (ловим всё подряд)

- [ ] `except Exception:` без sub-type в Python → `medium`.
- [ ] `except:` голый (catches KeyboardInterrupt) → `high`.
- [ ] `catch (Exception e)` в Java → `medium`.
- [ ] `catch (err)` без проверки типа в TS → `low`.
- [ ] JS: `catch { ... }` без имени или `catch (e)` без instanceof-проверок → `low`.

### 2.4. Error propagation

- [ ] Публичные функции возвращают `null` / `undefined` / `-1` / `""` в случае ошибки вместо throw/Result? Error-as-sentinel → finding `medium`.
- [ ] Для топ-30 центральных функций (из фазы 02) проверь: есть ли молчаливо-успешные возвраты при внутренней ошибке?

### 2.5. Ресурсы и очистка

- [ ] Открытые файлы/соединения без `finally` / `with` / `using` / `defer`:
  - Python: `open\(` не внутри `with` блока — finding `high`.
  - JS/Node: `fs.createReadStream` без `.on('error')` / `.on('end')`.
  - Java: `new FileInputStream` без try-with-resources.
- [ ] Каждое явное → finding `high` (resource leak).

### 2.6. Stability Patterns (Nygard)

#### 2.6.1. Таймауты на внешние вызовы (ОБЯЗАТЕЛЬНАЯ ТАБЛИЦА)

- [ ] Найди все HTTP-клиенты grep'ом:
  - Python: `requests\.(get|post|put|delete|patch)\(`, `httpx\.`, `aiohttp\.ClientSession`, `urllib\.`
  - Node: `fetch\(`, `axios\.`, `got\.`, `node-fetch`, `http\.request`
  - Java: `HttpClient`, `RestTemplate`, `WebClient`, `OkHttp`
  - Go: `http\.Client\{\}`, `http\.Get`
- [ ] Для каждого — прочитай строки вокруг и проверь наличие timeout. Заполни таблицу:

  | Файл | Строка | Клиент | Вызов | Timeout установлен? | Значение |
  |------|--------|--------|-------|---------------------|----------|
  | `src/providers/vertex-client.ts` | 79 | `fetch` | `fetch(url)` | ❌ | — |
  | `src/payment/stripe.ts` | 42 | `axios` | `axios.post(...)` | ✅ | 5000ms |

- [ ] Сохрани в `audit/evidence/05_error_handling/external_calls_timeouts.md`.
- [ ] Каждый вызов **без таймаута** → finding:
  - В runtime hot path → `high`.
  - В init / rare → `medium`.
- [ ] Таймауты на DB-вызовы (connection pool timeouts, statement timeouts) — отдельный sweep.

#### 2.6.2. Retry

- [ ] Поиск retry логики:
  - Вручную прописанные циклы: `for i in range` + `try: ... except:`.
  - Библиотеки: `tenacity`, `retry`, `resilience4j`, `Polly`, `opossum`.
- [ ] Retry БЕЗ exponential backoff и jitter → finding `medium` (retry storm risk).
- [ ] Retry на non-idempotent операциях (POST, INSERT без idempotency key) → finding `high`.

#### 2.6.3. Circuit breaker

- [ ] Поиск: `CircuitBreaker`, `pybreaker`, `opossum`, `resilience4j`, `Polly.CircuitBreaker`.
- [ ] Если внешних интеграций ≥ 3 и circuit breaker отсутствует → finding `medium`.

#### 2.6.4. Bulkheads

- [ ] Разные пулы соединений для разных downstream-сервисов? → упоминание `info` в отчёте.
- [ ] Finding `low` только если видна явная общая очередь на критичные операции.

#### 2.6.5. Fail fast vs fail slow

- [ ] Функции, ждущие бесконечно при сбое (`while True: connect()`) → finding `high`.
- [ ] Валидация входа на границе — если в публичных API отсутствует → finding `medium`.

### 2.7. Идемпотентность критичных операций

- [ ] Эндпоинты `POST /payment`, `/transfer`, `/create-order`, webhook handlers — есть ли idempotency-key паттерн?
- [ ] Если нет — finding `high`.

### 2.8. Распределённые эффекты

Если видны очереди / MQ / event bus:
- [ ] Обработка «at-least-once» duplicates на потребителе? → `medium` при отсутствии.
- [ ] Dead letter queue (DLQ) настроена? → `medium` при отсутствии.
- [ ] Poison pill protection → `medium` при отсутствии.

### 2.9. Transactions

- [ ] Поиск `@transactional`, `db.transaction(`, `BEGIN`.
- [ ] Транзакция внутри HTTP-запроса должна быть короткой. Если видишь транзакцию, оборачивающую внешний HTTP-вызов → finding `high` (long transaction anti-pattern).
- [ ] Nested transactions без savepoints → `medium`.

### 2.10. Assertive programming (Pragmatic Programmer)

- [ ] Preconditions / postconditions на публичных функциях центральных модулей. Если публичная функция принимает любой мусор без валидации и падает глубоко в стеке → finding `medium`.

### 2.11. Logging ошибок (пересекается с фазой 08)

- [ ] При catch — логируется ли достаточно контекста (correlation ID, параметры, stack trace)?
- [ ] `console.log(e)` без контекста → finding `low`.
- [ ] `logger.error({err, ctx}, "operation failed")` — правильно.

### 2.12. Process-wide mutable state в error path

**Особое внимание** (реальный случай из прошлого аудита):
- [ ] `process.env.FOO = bar` во время request handling, worker job, или AI call → finding `high` (race-condition при concurrent jobs).
- [ ] Аналогично: глобальные singletons, меняющие состояние на каждый вызов.

---

## 3. Quota check перед завершением

- [ ] **≥ 5 findings** для M-проекта. Если меньше — перечитай все catch-блоки в `catch_blocks.txt`.
- [ ] **Таблица внешних вызовов с таймаутами** заполнена — минимум 10 строк для M-проекта.
- [ ] Оба evidence-файла созданы.
- [ ] Распределение confidence разумное.

---

## 4. Артефакт — `audit/05_error_handling.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено**
3. **Ключевые наблюдения**
   - **Catch-блоков всего** — N (ссылка на evidence).
   - **Error-swallowing hotspots** — таблица `file:lines | pattern | severity`.
   - **Timeouts coverage** — сколько внешних вызовов имеют таймаут / не имеют.
   - **Retry strategy** — сводка.
   - **Circuit breaker** — есть/нет.
   - **Transactions** — проблемные места.
   - **Idempotency** — для критичных операций.
   - **Resource leaks** — подтверждённые.
   - **Global state races** — если найдены.
4. **Находки**
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Если downstream сервис перестанет отвечать, как себя поведёт система — упадёт за секунды, зависнет на часы, или начнёт лавинообразно ретраить? Ответ должен быть обоснован кодом (ссылки на строки).
   - **Q2.** Назови 3 функции, в которых категорически нельзя проглатывать ошибки. Они сейчас это делают?
7. **Следующая фаза:** `phases/phase_06_security.md`

---

## 5. Memory

```markdown
# Phase 05 memory
Completed: YYYY-MM-DD

Resilience summary:
- catch_blocks_total: <N>
- swallowed_catches_confirmed: <N>
- external_calls_without_timeout: <N>
- retry_with_backoff: <yes/no/partial>
- circuit_breakers: <yes/no>
- long_transactions: <N>
- resource_leaks: <N>
- idempotency_on_critical_endpoints: <yes/no/partial>
- global_state_races: <N>

Top risks:
1. <описание>
2. <описание>
3. <описание>

Next phase: phase_06_security.md
```

---

## 6. Отчёт пользователю

> Фаза 5/10 завершена. Устойчивость: проверено <N> catch-блоков, <M> подтверждённых проглатываний, <X> внешних вызовов без таймаута, circuit breaker <есть/нет>. Основной риск: <кратко>. Добавлено <K> findings. Перехожу к фазе 6 — безопасность.

Перейди к `phases/phase_06_security.md`.
