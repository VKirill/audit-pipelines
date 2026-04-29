# PHASE 07 — TESTS

**Цель:** Оценить состояние тестов как защитной сетки: объём, пирамида, качество, надёжность.

**Источники:**
- Beck, *Test-Driven Development by Example*.
- Freeman & Pryce, *Growing Object-Oriented Software, Guided by Tests* (GOOS).
- Meszaros, *xUnit Test Patterns* — каталог test smells.
- Feathers, *Working Effectively with Legacy Code* — seam-точки для тестирования.
- Google, *Software Engineering at Google* — test sizes (small/medium/large).
- Fowler, *UnitTest*, *TestPyramid* — bliki.

---

## 1. Входы
- `audit/02_architecture.md` — central symbols (они должны быть покрыты тестами).
- `audit/05_error_handling.md` — error branches (проверяется ли обработка ошибок?).

## 2. Чек-лист проверок

### 2.1. Инвентаризация тестов
- [ ] Найди тестовые директории:
  - `test/`, `tests/`, `__tests__/`, `spec/`
  - `src/**/*.test.*`, `src/**/*.spec.*`
  - `*_test.go`, `*Test.java`, `*Tests.cs`, `*.Tests` (C# projects)
  - Python: `test_*.py`, `*_test.py`
- [ ] Число тестовых файлов, суммарный LOC тестов.
- [ ] **Ratio:** `test_loc / prod_loc`. Ориентиры (эвристика, не догма):
  - < 0.2 — low coverage, finding `medium`/`high` в зависимости от критичности проекта.
  - 0.2–0.8 — обычная зона.
  - > 1.5 — возможен over-testing/mock-heavy; может быть finding `low` (сомнительная ценность дополнительных тестов).

### 2.2. Типы тестов (пирамида — Fowler/Cohn)
- [ ] По именам/папкам/фикстурам определи:
  - **Unit** — изолированные, без I/O. `src/**/*.spec.ts`, `tests/unit/`.
  - **Integration** — с БД/HTTP/файлами. `tests/integration/`, `tests/contract/`.
  - **E2E** — целый стек. `tests/e2e/`, `cypress/`, `playwright/`, `selenium/`.
- [ ] Соотношение: здоровая пирамида — unit >> integration >> e2e (например 70% / 20% / 10%).
- [ ] Перевёрнутая пирамида (много e2e, мало unit) — finding `medium` (медленно, хрупко).
- [ ] Если только unit и никаких integration в веб-проекте с БД — finding `medium` (contract gap).

### 2.3. Test frameworks — единообразие
- [ ] Сколько разных фреймворков используется? (Jest + Mocha + Vitest — избыточно для одной кодбазы.)
- [ ] Mix → finding `low` (cognitive load).

### 2.4. Покрытие (best effort)
Если в проекте уже настроено покрытие — прочитай последний отчёт (`coverage/`, `.coverage`, `jacoco.xml`, `coverage.xml`). Не запускай тесты сам.

- [ ] Общее покрытие (lines / branches).
- [ ] Критично: покрытие топ-30 центральных символов из фазы 02.
- [ ] Если покрытие не измеряется вообще — finding `medium` (нет видимости прогресса).

**Альтернативная оценка через GitNexus** (когда нет coverage):
- [ ] Через `cypher`: доля символов, на которые ссылаются из тестовых файлов.
  ```cypher
  MATCH (t:File)-[:CodeRelation]->(sym)
  WHERE t.path CONTAINS 'test' OR t.path CONTAINS 'spec'
  RETURN count(DISTINCT sym) AS tested_symbols
  ```
  сравнить с общим числом публичных символов.
- [ ] Центральные символы, не фигурирующие ни в одном тесте → finding `high` для каждого.

### 2.5. Test smells (Meszaros)

#### Disabled / skipped tests
- [ ] `search_for_pattern`:
  - `@Disabled`, `@Ignore`, `@Skip`
  - `xit(`, `xdescribe(`, `it.skip(`, `describe.skip(`
  - `@pytest.mark.skip`, `@pytest.mark.xfail`
  - `t.Skip(` в Go
- [ ] Для каждого — git blame (сколько времени назад отключили). > 90 дней → finding `medium` (мёртвый тест).

#### Flaky tests индикаторы
- [ ] `sleep(`, `time.sleep(`, `Thread.sleep(`, `setTimeout(` в тестах без deterministic wait → finding `medium` (timing-dependent).
- [ ] Зависимости от текущего времени (`Date.now()`, `datetime.now()`) без фикс-моков.
- [ ] Random без фиксированного seed.
- [ ] Зависимости от порядка тестов (проверь — используются ли `@Order`, beforeAll с глобальным состоянием).

#### Test coupling
- [ ] Тесты, вызывающие другие тесты или зависящие от side-effects предыдущих.
- [ ] Обнаружение сложно автоматически — пропусти, но при случайной находке — finding.

#### Assertion roulette
- [ ] Тесты без assertions или с одним generic assert.
- [ ] Тесты с > 20 assertions в одном методе (monster tests).

#### Mock-heavy
- [ ] Если топ-10 тестов по размеру импортируют > 5 mocks — это «testing the mock», не код. Finding `medium`.

#### Testing private / internal
- [ ] `@ts-ignore`, `(obj as any)._private` в тестах, reflection для тестирования приватных — finding `low`/`medium` (дизайн-запах самих продукционных классов).

### 2.6. Error branches coverage
Из фазы 05 у тебя есть список мест с обработкой ошибок. Проверь:
- [ ] Для топ-10 мест с `catch`/`except` — есть ли тесты на error path?
- [ ] `search_for_pattern` на `toThrow`, `assertThrows`, `raises`, `assert.Error` в тестах. Сколько их относительно общих? Если < 10% — значит happy-path-only testing, finding `medium`.

### 2.7. Интеграционные контракты
Если есть `api/` или микросервисы:
- [ ] Contract tests (Pact, Spring Cloud Contract, OpenAPI contract tests)?
- [ ] Отсутствие при наличии внешних потребителей API → finding `medium`.

### 2.8. Тестовые данные
- [ ] Хардкоженые тестовые фикстуры vs фабрики (FactoryBoy, factory_bot, MSW). Второе лучше.
- [ ] Тесты, использующие прод-данные (персональные данные, реальные credentials) → finding `high` (compliance risk).
- [ ] Огромные `__snapshots__` без review-дисциплины — finding `low`.

### 2.9. CI тесты
- [ ] Тесты запускаются в CI (видно из workflows)?
- [ ] Если есть tests/ но CI их не гоняет → finding `high` (иллюзия безопасности).
- [ ] Fail the build on test failure? (обычно да, но иногда отключают `continue-on-error: true`)

### 2.10. Мутационное тестирование (опционально)
- [ ] Есть ли `stryker`, `pitest`, `mutmut`? Если есть и работает — отметить как хороший знак. Если нет — не finding, но предложение в ROADMAP (for mature teams).

### 2.11. Property-based testing (опционально)
- [ ] `hypothesis`, `fast-check`, `jqwik`, `quickcheck`. Отсутствие — не finding. Наличие — плюс (отметить).

### 2.12. Seams (Feathers)
Для кода без тестов из центральных символов:
- [ ] Можно ли добавить unit-тест без разбиения кода? Или класс жёстко связан со своими зависимостями?
- [ ] Выбери топ-5 «тестабельно-плохих» символов и для каждого finding `medium` с рекомендацией конкретного seam pattern (constructor injection / subclass-to-test / parameterize method).

## 3. Артефакт — `audit/07_tests.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено**
3. **Ключевые наблюдения**
   - **Inventory** — числа тестов, LOC, ratio.
   - **Пирамида** — таблица `тип | число файлов | LOC | %`.
   - **Coverage** — общее и по центральным символам (если доступно).
   - **Disabled/skipped tests** — список с возрастом.
   - **Flaky indicators** — список.
   - **Error path coverage** — оценка.
   - **CI integration** — да/нет/детали.
4. **Находки**
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Если команда **удалит все тесты старше 6 месяцев** — что конкретно сломается в понимании того, как система должна работать? Если «ничего» — значит, тесты не являются живой документацией, это finding.
   - **Q2.** Для топ-5 центральных символов из фазы 02 — покрыты ли они **счастливый путь + хотя бы 2 error branches** каждый? Если нет — это #1 задача фазы «Test pyramid rebuild».
7. **Следующая фаза:** `phases/phase_08_ops_observability.md`

## 4. Memory

```markdown
# Phase 07 memory
Completed: YYYY-MM-DD

Testing posture:
- test_loc: <N>
- test_to_prod_ratio: <X.XX>
- pyramid_shape: <healthy/inverted/missing-layer>
- coverage_overall: <N%> (source: <coverage report / estimated>)
- central_symbols_covered: <X / Y>
- disabled_tests: <N> (aged >90d: <M>)
- flaky_indicators: <N>
- ci_runs_tests: <yes/no>

Top test-debt items:
1. <central symbol без теста>
2. ...

Next phase: phase_08_ops_observability.md
```

## 5. Отчёт пользователю

> Фаза 7/10 завершена. Тесты: <N> файлов, ratio test/prod = <X>, пирамида <форма>, покрытие ~<N%>. <K> центральных символов из фазы 02 не покрыты. Добавлено <N> findings. Перехожу к фазе 8 — CI/CD и observability.

Перейди к `phases/phase_08_ops_observability.md`.
