# Автономный аудит JS/TS веб-приложения

> Этот файл — единый автономный пайплайн. Claude читает его один раз и
> выполняет ВСЕ фазы подряд без остановок и подтверждений, до создания
> FINAL-REPORT.md в конце.

## Запуск

**Рекомендуемый способ — одна команда с одним аргументом:**

```
Прочитай /home/ubuntu/projects/audit-pipelines/nodejs-audit/MASTER_PROMPT.md
и выполни полный аудит проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

`MASTER_PROMPT.md` — это auto-runbook: ИИ сам копирует пайплайн в проект,
делает sanity check и проходит все фазы из этого файла.

Альтернативно (если пайплайн уже в проекте) — прямая команда в корне:

```bash
claude "Прочитай nodejs-audit/AUDIT.md и выполни ПОЛНОСТЬЮ от начала до конца. Не останавливайся между фазами. Не запрашивай подтверждений. Все промежуточные результаты сохраняй в nodejs-audit/reports/. Финальный отчёт — nodejs-audit/reports/FINAL-REPORT.md. Если какой-то шаг невозможно выполнить — зафиксируй причину в reports/errors.log и продолжай со следующего шага. В конце выведи путь к FINAL-REPORT.md."
```

---

# ИНСТРУКЦИИ ДЛЯ CLAUDE

## Глобальные правила (соблюдать на протяжении всех фаз)

1. **Не останавливайся.** Не задавай вопросов между фазами. Выполни весь
   пайплайн от фазы 0 до фазы 9 за один проход.

2. **При ошибке — продолжай.** Если команда упала, файл не создаётся,
   инструмент не установлен — запиши ошибку в `reports/errors.log` в
   формате `[фаза N] [время] описание ошибки`, попробуй обходной путь,
   и переходи дальше. НЕ останавливай весь аудит из-за одной упавшей
   команды.

3. **Не меняй код проекта.** Аудит — только для чтения. Единственные
   разрешённые изменения: создание файлов в `nodejs-audit/reports/`,
   обновление `.gitignore` (одна строка), создание `AGENTS.md` если
   его нет (фаза 0).

4. **Не устанавливай тяжёлые зависимости в проект.** Все инструменты
   запускай через `npx --yes` без сохранения в package.json. Это
   гарантирует, что аудит не загрязнит проект.

5. **Сохраняй промежуточные результаты сразу.** Не накапливай данные
   в контексте. После каждой фазы — записал отчёт в файл, и
   используй файл как источник истины в следующих фазах.

6. **Бюджет на фазу — разумный.** Если ты бьёшься в одну проблему
   больше 5-7 попыток — пропусти, запиши в errors.log, продолжай.

7. **Финальная фаза 9 не должна перечитывать всё.** Она читает только
   готовые отчёты `reports/01-*.md` ... `reports/08-*.md` и собирает
   FINAL-REPORT.md. Это критично для экономии контекста.

8. **Сигналь прогресс.** В начале каждой фазы выводи в чат одну строку:
   `[PHASE N] STARTED — <название>`. В конце — `[PHASE N] DONE —
   reports/0N-*.md`. Это даёт владельцу видеть прогресс без чтения логов.

9. **Sanity check перед стартом.** Если в корне проекта нет ни
   `package.json`, ни `tsconfig.json`, ни `*.ts`/`*.tsx`/`*.js`/`*.jsx`
   файлов — это не JS/TS проект. Запиши факт в `reports/errors.log`,
   создай минимальный `FINAL-REPORT.md` с пометкой «not a JS/TS project»
   и остановись. НЕ продолжай аудит — данные будут пустыми.

---

## Фаза 0: BOOTSTRAP

**Цель:** определить контекст проекта, не устанавливая ничего лишнего.

**Шаги:**

1. Определи package manager — посмотри какой lock-файл есть:
   - `package-lock.json` → `npm` (команды: `npx`)
   - `yarn.lock` → `yarn` (команды: `yarn dlx`)
   - `pnpm-lock.yaml` → `pnpm` (команды: `pnpm dlx`)
   - `bun.lockb` → `bun` (команды: `bunx`)

   Дальше во всех командах используй найденный runner. Если ниже
   написано `npx --yes <tool>` — заменяй на эквивалент из своего
   менеджера.

2. Проверь наличие TypeScript:
   ```bash
   test -f tsconfig.json && echo "TS:yes" || echo "TS:no"
   ```
   Запомни значение — оно влияет на фазу 2.

3. Проверь git-состояние:
   ```bash
   git status --porcelain
   ```
   Если есть незакоммиченные изменения — это ОК, просто зафиксируй
   факт в `reports/00-bootstrap.md`. НЕ требуй коммита, НЕ создавай
   ветку.

4. Создай файл `reports/00-bootstrap.md`:

   ```markdown
   # Bootstrap

   - Дата: <ISO timestamp>
   - Package manager: <npm/yarn/pnpm/bun>
   - TypeScript: <yes/no>
   - Точка входа: <путь к main файлу>
   - Размер src/: <команда: find src -type f | wc -l>
   - Узнал из package.json:
     - name: ...
     - version: ...
     - dependencies count: ...
     - devDependencies count: ...
   - git: <чистый/N изменённых файлов>
   ```

5. Создай `reports/errors.log` (пустой файл, для последующих фаз).

6. Создай `reports/raw/` для сырых логов команд.

**Критерии завершения:** существуют `reports/00-bootstrap.md`, `errors.log`,
`raw/`. Переходи к фазе 1 без подтверждения.

---

## Фаза 1: RECON (разведка)

**Цель:** понять архитектуру, стек, стиль за один проход.

**Что прочитать (в этом порядке, по 1 файлу за раз, не дублировать
чтения):**

1. `README.md` — если есть
2. `AGENTS.md` или `CLAUDE.md` — если есть
3. `package.json` — секции scripts, dependencies, devDependencies
4. `tsconfig.json` — если есть, особенно `strict`, `target`, `paths`
5. Точка входа — найди по полю `main` в package.json или по эвристике:
   - `src/index.ts`, `src/main.ts`, `src/app.ts`, `src/server.ts`
6. Корневая структура `src/`:
   ```bash
   find src -maxdepth 2 -type d | head -30
   ```
7. **5 случайных файлов** из разных частей src/ — выбирай разнообразные:
   - 1 контроллер/роут
   - 1 сервис/use case
   - 1 модель/тип
   - 1 утилиту
   - 1 компонент (если есть фронт)

   Не читай файлы целиком если они > 200 строк — читай первые 100
   строк для понимания стиля.

8. Файл с роутингом — найди через grep:
   ```bash
   grep -rEn "app\.(get|post|put|delete)|router\.(get|post|put|delete)" src/ | head -10
   ```

**Создай `reports/01-recon.md`:**

```markdown
# Recon

## Что за проект (5-7 предложений)
[По коду, не по README. Что делает. Для кого. Главные сущности.]

## Стек (точно из package.json)
- Runtime: ...
- Backend framework: ...
- Frontend framework: ...
- DB / ORM: ...
- Tests: ...
- Build: ...

## Размер
- Файлов в src/: N
- Строк кода в src/: M (команда: `find src -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" | xargs wc -l 2>/dev/null | tail -1`)
- Production deps: X
- Dev deps: Y

## Структура src/ (как есть)
[Дерево с описанием что в каждой папке]

## Архитектурный паттерн (первое впечатление)
[layered / feature-based / hexagonal / chaos / mixed]

## Стиль кода
- Именование файлов: kebab-case / camelCase / mixed
- async-стиль: await / .then() / mixed
- Импорты: alias / relative / mixed
- Экспорты: named / default / mixed
- TS strict: yes / no / partial

## 3 примера кода (по 5-10 строк каждый, разные файлы)
[С указанием путей и строк.]

## 5 первых сигналов проблем
[Гипотезы для следующих фаз. С путями к файлам.]

## 3 положительных наблюдения
[Что хорошо. Если ничего хорошего — пиши честно.]
```

**Критерии завершения:** существует `reports/01-recon.md`. Переходи к
фазе 2 без подтверждения.

---

## Фаза 2: DETERMINISTIC (автоматические проверки)

**Цель:** запустить все возможные автоматические инструменты, собрать
сырые данные.

**Все инструменты запускай через `npx --yes <tool>` без установки в
проект.** Если команда не работает — записывай ошибку в errors.log и
переходи к следующей.

### Шаг 2.1: Форматирование

```bash
npx --yes prettier@latest --check "src/**/*.{js,ts,jsx,tsx,json,md}" 2>&1 \
  | tee reports/raw/prettier.log
echo "EXIT:$?" >> reports/raw/prettier.log
```

Из вывода извлеки: количество файлов с проблемами форматирования.

### Шаг 2.2: Линтинг

Если в проекте уже есть eslint config — используй его. Если нет — пропусти
с записью в errors.log.

```bash
test -f eslint.config.js -o -f eslint.config.mjs -o -f .eslintrc.json -o -f .eslintrc.js \
  && npx --yes eslint "src/**/*.{js,ts,jsx,tsx}" --format json \
     > reports/raw/eslint.json 2>reports/raw/eslint-stderr.log \
  || echo "no eslint config" >> reports/errors.log
```

Если JSON получился — извлеки:
- Топ-10 правил (по количеству нарушений)
- Топ-10 файлов (по сумме error+warning)
- Общее количество error и warning

### Шаг 2.3: Типизация (только если TypeScript)

```bash
test -f tsconfig.json && \
  npx --yes typescript@latest tsc --noEmit 2>&1 | tee reports/raw/tsc.log
```

Подсчитай количество ошибок (грep "error TS").

### Шаг 2.4: Тесты

Сначала посмотри в package.json scripts что есть. Если есть `test` или
`test:unit`:

```bash
npm test 2>&1 | tee reports/raw/tests.log
echo "EXIT:$?" >> reports/raw/tests.log
```

**Не запускай coverage отдельно если он медленный.** Если в `npm test`
уже есть coverage — хорошо. Если нет — пропусти, запиши в errors.log.

Если тестов нет вообще — это не ошибка, просто факт. Запиши в отчёт.

### Шаг 2.5: Безопасность зависимостей

```bash
npm audit --json > reports/raw/audit.json 2>&1 || true
```

Из JSON извлеки: critical, high, moderate, low counts.

### Шаг 2.6: Зависимости

```bash
npx --yes depcheck --json > reports/raw/depcheck.json 2>&1 || true
npx --yes knip --reporter json > reports/raw/knip.json 2>&1 || true
npx --yes madge --circular --extensions ts,tsx,js,jsx src/ \
  > reports/raw/madge.log 2>&1 || true
```

### Шаг 2.7: Размеры файлов

```bash
find src -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
  -exec wc -l {} + 2>/dev/null | sort -rn | head -25 \
  > reports/raw/largest-files.log
```

### Шаг 2.8: Поиск секретов (легковесный)

```bash
grep -rEn "(api[_-]?key|secret|password|token)[\"' ]*[:=][\"' ]*[A-Za-z0-9_-]{16,}" \
  --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
  src/ 2>&1 | grep -vE "test|spec|mock|process\.env|\\\$\\{" \
  > reports/raw/secrets-grep.log || echo "" > reports/raw/secrets-grep.log
```

### Шаг 2.9: Сборка отчёта

Создай `reports/02-deterministic.md`:

```markdown
# Deterministic checks

## Сводная таблица

| Проверка | Команда | Результат |
|----------|---------|-----------|
| Prettier | --check | <N> файлов с проблемами / OK |
| ESLint | --format json | <X> errors, <Y> warnings / config not found |
| TypeScript | tsc --noEmit | <Z> errors / OK / N/A (no TS) |
| Tests | npm test | <A> passed, <B> failed / no tests |
| npm audit | --json | crit:X high:Y mod:Z low:W |
| depcheck | | unused deps: <count> |
| knip | | unused exports: <count> |
| madge --circular | | <N> циклов |

## ESLint топ-10 правил
[Список из reports/raw/eslint.json]

## ESLint топ-10 файлов с проблемами
[Список с путями и количествами]

## TypeScript ошибки (категории)
[Категории по кодам TS2xxx, TS7xxx и т.д.]

## Циклические импорты
[Если есть, привести список]

## Топ-10 самых длинных файлов
[Из reports/raw/largest-files.log]

## Подозрительные секреты в коде
[Из reports/raw/secrets-grep.log, если что-то нашли]

## Что не удалось проверить
[Из reports/errors.log за этот шаг]
```

**Критерии завершения:** существует `reports/02-deterministic.md`. Переходи
к фазе 3.

---

## Фаза 3: ARCHITECTURE

**Цель:** оценить архитектурное здоровье по 6 осям.

**Не перечитывай весь код.** Используй данные из `reports/01-recon.md`,
`reports/02-deterministic.md` и `reports/raw/`. Дополнительно прочитай
3-4 ключевых файла, которые ещё не читал в фазе 1.

**6 осей оценки (каждая 0-10):**

1. **Разделение слоёв** — есть ли controller/service/repository?
   Не утекает ли SQL в контроллеры? Найди примеры:
   ```bash
   # ORM в контроллерах
   grep -rEn "(controllers?|routes?)/.*\.(ts|js)$" src/ -l 2>/dev/null \
     | xargs grep -lEn "prisma\.|knex\.|db\.query|sequelize" 2>/dev/null
   ```

2. **Связность/сцепление** — топ файлов по fan-in, циклы (уже есть в фазе 2).

3. **SOLID** — приведи 1-2 примера соблюдения и 1-2 нарушения. Не ищи
   нарушения там где их нет.

4. **Доменные границы** — anemic models или есть поведение?
   Бизнес-логика в контроллерах или в сервисах?

5. **Управление состоянием** — где живёт state? Если есть фронт — какой
   подход (useState / Zustand / Redux / Tanstack Query)?

6. **Обработка ошибок** — единая стратегия или каждый файл по-своему?

**Создай `reports/03-architecture.md`:**

```markdown
# Architecture

## TL;DR
[3 предложения: тип архитектуры, состояние, главный риск.]

## Оценки (X/60)

| Ось | Оценка | Главная проблема |
|-----|--------|------------------|
| Разделение слоёв | X/10 | ... |
| Связность/сцепление | X/10 | ... |
| SOLID | X/10 | ... |
| Доменные границы | X/10 | ... |
| Управление состоянием | X/10 | ... |
| Обработка ошибок | X/10 | ... |

## Детально по осям

### Ось 1: Разделение слоёв (X/10)
**Что хорошо:** [с файлами]
**Что плохо:** [с файлами и строками]
**Пример нарушения:**
\```
[конкретный код 5-10 строк с указанием файла]
\```

### ... (для каждой оси)

## Топ-3 архитектурных риска

### Риск 1: <название>
- Что: ...
- Где: <файлы>
- Чем грозит: ...
- Как чинить: <план в 3-5 шагов>

### Риск 2 / Риск 3 ...

## Готовый промт для рефакторинга #1
[Самодостаточный промт для Claude Code, который исправит главный риск.]
```

**Критерии завершения:** `reports/03-architecture.md` существует.

---

## Фаза 4: READABILITY

**Цель:** оценить читаемость и именование.

**Используй данные из `reports/raw/largest-files.log` и фазы 2.**

**5 осей (каждая 0-10):** именование, размеры, комментарии,
однородность, магия (числа/строки).

**Команды для сбора данных:**

```bash
# TODO/FIXME/HACK
grep -rn "TODO\|FIXME\|HACK\|XXX" src/ --include="*.ts" --include="*.tsx" \
  --include="*.js" --include="*.jsx" 2>/dev/null > reports/raw/todos.log

# Подозрительные имена файлов
find src -type f \( -name "*util*" -o -name "*helper*" -o -name "*manager*" \
  -o -name "*common*" -o -name "*misc*" \) 2>/dev/null > reports/raw/bad-names.log

# Магические числа
grep -rEn "[^0-9.]([0-9]{3,})[^0-9.]" src/ --include="*.ts" 2>/dev/null \
  | grep -v "test\|spec\|mock" | head -30 > reports/raw/magic-numbers.log

# Async style
grep -rn "\\.then(" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l \
  > reports/raw/then-count.log
grep -rn "await " src/ --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l \
  > reports/raw/await-count.log
```

Прочитай **ровно 3 файла** из топа `largest-files.log` (только их),
чтобы оценить качество написания крупных файлов.

**Создай `reports/04-readability.md`:**

```markdown
# Readability

## TL;DR
[Один абзац.]

## Оценки (X/50)

| Ось | Оценка |
|-----|--------|
| Именование | X/10 |
| Размер и структура | X/10 |
| Комментарии | X/10 |
| Однородность | X/10 |
| Магия | X/10 |

## Детально

### Именование
**Хорошие примеры:**
- src/X.ts:N — `<фрагмент>` — почему хорошо
**Плохие примеры:**
- src/Y.ts:N — `<фрагмент>` — почему плохо

### Размеры
| Файл | Строк | Что внутри (краткое описание) |
|------|-------|-------------------------------|
| src/X.ts | N | ... |

### Комментарии
- TODO/FIXME: <count> в <files>
- JSDoc/TSDoc на публичных функциях: примерное покрытие %
- Закомментированный код: <количество мест>

### Однородность
- await vs .then: <ratio>
- Файлы со смешанным стилем: ...

### Магия
- Магических чисел: ~N
- Магических строк: ~M
- Топ-5 кандидатов на константы: ...

## Топ-10 файлов на рефакторинг
| # | Файл | Главная проблема |
|---|------|------------------|

## Готовые промты для рефакторинга
[2 готовых промта для Claude Code.]
```

---

## Фаза 5: SECURITY

**Цель:** OWASP Top 10 — экспресс-проход.

**Команды для каждой категории:**

```bash
# A01: эндпоинты без auth middleware
grep -rEn "(app|router)\.(get|post|put|delete|patch)\(" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-endpoints.log

# A02: слабая криптография
grep -rEn "md5|sha1\(|createHash\(['\"](md5|sha1)" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-weak-crypto.log
grep -rEn "bcrypt|argon2|scrypt" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-strong-crypto.log

# A03: SQL injection
grep -rEn "query\(.*\\\$\\{|raw\(.*\\\$\\{" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-sqli.log

# A03: XSS
grep -rEn "dangerouslySetInnerHTML|innerHTML\s*=|v-html" src/ 2>/dev/null \
  > reports/raw/sec-xss.log

# A03: command injection
grep -rEn "exec\(|execSync\(|spawn\(.*req\\." src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-cmd.log

# A04: rate limiting
grep -rEn "rate.*limit|express-rate-limit|fastify-rate" src/ package.json 2>/dev/null \
  > reports/raw/sec-rate-limit.log

# A05: CORS *
grep -rEn "Access-Control-Allow-Origin.*\\*|origin:.*['\"]\\*['\"]" src/ 2>/dev/null \
  > reports/raw/sec-cors.log

# A05: helmet
grep -rEn "helmet\(\)" src/ 2>/dev/null > reports/raw/sec-helmet.log

# A05: error stack to client
grep -rEn "err\.stack|error\.stack" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-stack.log

# A07: JWT
grep -rEn "jwt.*sign|jsonwebtoken|expiresIn" src/ 2>/dev/null > reports/raw/sec-jwt.log

# секреты в .env в git
git ls-files 2>/dev/null | grep -E "^\\.env(\\..+)?$" | grep -v "example\|sample" \
  > reports/raw/sec-env-in-git.log || true

# уже сделанный audit.json из фазы 2
```

Анализируй вывод каждой команды. **Не выдумывай атаки.** Если вывод
пустой — значит этот класс проблем не обнаружен.

**Создай `reports/05-security.md`:**

```markdown
# Security audit

## TL;DR
[Один абзац: безопасен ли код, есть ли критичные находки.]

## Сводка findings

| ID | Категория | Серьёзность | Файл |
|----|-----------|-------------|------|
| SEC-001 | A03 SQLi | Critical | src/X.ts:45 |
| ... |

## OWASP Top 10 — статус по каждой категории

### A01 Broken Access Control: ❌/⚠️/✅
[Что проверил, что нашёл]

### A02 Cryptographic Failures: ...
### A03 Injection: ...
### A04 Insecure Design: ...
### A05 Security Misconfiguration: ...
### A06 Vulnerable Components: ...
[Тут используй reports/raw/audit.json]
### A07 Authentication Failures: ...
### A08 Software/Data Integrity: ...
### A09 Logging Failures: ...
### A10 SSRF: ...

## Findings (детально)

### SEC-001: <название>
**Категория:** ...
**Серьёзность:** Critical / High / Medium / Low
**Файл:** ...
**Уязвимый код:**
\```
[код]
\```
**Как чинить:**
\```
[код]
\```

### ... остальные findings

## Готовые промты для фиксов
[Промты для критических и high findings.]
```

---

## Фаза 6: PERFORMANCE

**Цель:** найти узкие места.

**Команды:**

```bash
# N+1 паттерны
grep -rEn "for.*\\{[^}]*await" src/ --include="*.ts" --include="*.js" -A 3 2>/dev/null \
  | head -100 > reports/raw/perf-nplus1.log

grep -rEn "\\.map\\(.*async|\\.forEach\\(.*async" src/ --include="*.ts" 2>/dev/null \
  > reports/raw/perf-async-iter.log

# Sync операции
grep -rEn "readFileSync|writeFileSync|execSync" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/perf-sync.log

# Кеширование
grep -rEn "redis|memcached|node-cache|lru-cache" package.json 2>/dev/null \
  > reports/raw/perf-cache-deps.log

# Утечки памяти — setInterval без clear
grep -rEn "setInterval\(" src/ --include="*.ts" --include="*.tsx" 2>/dev/null \
  > reports/raw/perf-intervals.log
grep -rEn "addEventListener\(" src/ --include="*.ts" --include="*.tsx" 2>/dev/null \
  > reports/raw/perf-listeners.log

# Размер бандла — если есть build script и dist
test -d dist && du -sh dist/ > reports/raw/perf-dist-size.log 2>&1
test -d build && du -sh build/ >> reports/raw/perf-dist-size.log 2>&1

# Lazy/dynamic imports
grep -rEn "lazy\(|import\\(" src/ --include="*.ts" --include="*.tsx" 2>/dev/null \
  > reports/raw/perf-lazy.log

# Индексы в БД — Prisma schema или миграции
find . -name "schema.prisma" -not -path "*/node_modules/*" 2>/dev/null \
  | head -1 | xargs cat 2>/dev/null | grep -E "@@index|@index" \
  > reports/raw/perf-db-indexes.log
```

**НЕ запускай Lighthouse, npm run build, бенчмарки** — это слишком долго
для автономного запуска. Если хочется — запиши в отчёт что это надо
сделать вручную.

**Создай `reports/06-performance.md`:**

```markdown
# Performance audit

## TL;DR
[...]

## Сводная таблица проблем

| ID | Область | Серьёзность | Сложность фикса |
|----|---------|-------------|------------------|

## Бэкенд

### N+1 запросы
[Анализ reports/raw/perf-nplus1.log с примерами]

### Блокирующие операции
[Анализ perf-sync.log]

### Кеширование
[Есть ли. Если нет — где было бы полезно.]

## Фронтенд (если есть)

### Code splitting / lazy loading
[Анализ perf-lazy.log]

### Bundle size
[Если есть perf-dist-size.log]

## Утечки памяти
[setInterval без clearInterval — для каждого случая надо проверить
есть ли парный clearInterval в том же файле]

## БД

### Индексы
[Анализ perf-db-indexes.log если применимо]

## Топ-5 быстрых побед
1. ...
2. ...

## Готовые промты для оптимизаций
[1-2 промта.]
```

---

## Фаза 7: OBSERVABILITY

**Цель:** оценить готовность к production-эксплуатации.

**Команды:**

```bash
# console.log в коде
grep -rn "console\\.log\\|console\\.error\\|console\\.warn" src/ \
  --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" 2>/dev/null \
  | wc -l > reports/raw/obs-console-count.log

# Logger
grep -rEn "pino|winston|bunyan" package.json 2>/dev/null > reports/raw/obs-logger-deps.log
grep -rEn "from ['\"]pino['\"]|from ['\"]winston['\"]" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/obs-logger-usage.log

# Request ID / correlation
grep -rEn "requestId|correlationId|traceId|x-request-id" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/obs-request-id.log

# Health endpoints
grep -rEn "/health|/ready|/healthz|/livez" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/obs-health.log

# Метрики
grep -rEn "prom-client|@opentelemetry|prometheus" package.json src/ 2>/dev/null \
  > reports/raw/obs-metrics.log

# Sentry / error tracking
grep -rEn "@sentry|bugsnag|rollbar" package.json src/ 2>/dev/null \
  > reports/raw/obs-error-tracking.log

# Логирование PII
grep -rEn "log.*req\\.body|log.*password|log.*token" src/ --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/obs-pii.log
```

**Создай `reports/07-observability.md`:**

```markdown
# Observability

## TL;DR
[Готов к production: да / нет / частично]

## Оценки (X/40)

| Столп | Оценка |
|-------|--------|
| Логи | X/10 |
| Метрики | X/10 |
| Трейсинг | X/10 |
| Мониторинг ошибок | X/10 |

## Детально

### Логи
- console.log использований: <N>
- Структурированный logger: <да pino / да winston / нет>
- Корреляционный ID: <да/нет>
- Логирование PII (риск): <да/нет, файлы>

### Метрики
- prom-client / OTel: <да/нет>
- Health check эндпоинты: <да/нет, какие>
- Бизнес-метрики: <да/нет>

### Трейсинг
- OpenTelemetry: <да/нет>

### Мониторинг ошибок
- Sentry/Bugsnag: <да/нет>
- uncaughtException handlers: <да/нет>

## Сценарий "что если в 3 ночи всё упадёт"
[Реалистичный анализ: можно ли понять что случилось.]

## Топ-5 действий для production-готовности
1. ...

## Готовые промты
[1 промт по самому важному.]
```

---

## Фаза 8: AI-READABILITY

**Цель:** оценить дружественность к ИИ-доработкам — это самая важная
ось для владельца проекта.

**Команды:**

```bash
# Документация для агентов
ls AGENTS.md CLAUDE.md README.md 2>&1 > reports/raw/ai-docs.log
test -f AGENTS.md && wc -l AGENTS.md >> reports/raw/ai-docs.log
test -f .env.example && echo "env.example: yes" >> reports/raw/ai-docs.log \
  || echo "env.example: no" >> reports/raw/ai-docs.log

# JSDoc покрытие — приближённо
PUBLIC_FUNCS=$(grep -rEn "^export (async )?function" src/ --include="*.ts" 2>/dev/null | wc -l)
JSDOC_BLOCKS=$(grep -rEn "^/\\*\\*$" src/ --include="*.ts" 2>/dev/null | wc -l)
echo "public functions: $PUBLIC_FUNCS" > reports/raw/ai-jsdoc.log
echo "jsdoc blocks: $JSDOC_BLOCKS" >> reports/raw/ai-jsdoc.log

# Husky / lint-staged
ls .husky/ 2>/dev/null > reports/raw/ai-husky.log
test -f .lintstagedrc -o -f .lintstagedrc.json && echo "lint-staged: yes" >> reports/raw/ai-husky.log

# CI
ls .github/workflows/ 2>/dev/null > reports/raw/ai-ci.log
ls .gitlab-ci.yml 2>/dev/null >> reports/raw/ai-ci.log

# Strict TS
grep -E "\"strict\":" tsconfig.json 2>/dev/null > reports/raw/ai-strict.log

# Path aliases
grep -E "\"paths\":" tsconfig.json 2>/dev/null > reports/raw/ai-paths.log
```

**Создай `reports/08-ai-readability.md`:**

```markdown
# AI-readability

## TL;DR
[Насколько проект дружественен к ИИ-доработкам.]

## Тест "5 минут"
Если бы я открыл этот репозиторий впервые, за 5 минут я понял бы:
- Что это за проект: <да/нет/частично>
- Как запустить: <да/нет/частично>
- Где главная бизнес-логика: ...
- Какие конвенции: ...

## Оценки (X/60)

| Ось | Оценка |
|-----|--------|
| Понимание за 5 минут | X/10 |
| Навигация | X/10 |
| Однородность | X/10 |
| Контекст в коде | X/10 |
| Тесты как документация | X/10 |
| Безопасность доработок | X/10 |

## Детально

### Документация для агентов
- AGENTS.md / CLAUDE.md: <есть/нет/неполный>
- README.md: <качество>
- .env.example: <да/нет>

### JSDoc
- Публичных функций: ~N
- JSDoc-блоков: ~M
- Покрытие: ~X%

### Защита от ошибок ИИ
- TypeScript strict: <да/нет/частично>
- Husky pre-commit: <да/нет>
- CI с проверками: <да/нет>
- Path aliases: <да/нет>

### Шаблоны
- Шаблон для нового эндпоинта: <есть/нет>
- Шаблон для новой таблицы: <есть/нет>
- Шаблон для нового компонента: <есть/нет>

## Топ-7 улучшений для AI-readability
1. ...

## Готовые промты
### Промт: создать/расширить AGENTS.md
\```
[готовый текст промта]
\```

### Промт: добавить JSDoc на публичные функции
\```
[готовый текст]
\```
```

---

## Фаза 9: FINAL REPORT

**Цель:** собрать всё в один документ для владельца.

**ВАЖНО:** в этой фазе ты читаешь ТОЛЬКО файлы `reports/01-recon.md`
до `reports/08-ai-readability.md`. Не перечитывай код проекта. Не
запускай команды. Только синтез.

**Действия:**

1. Прочитай по очереди (по 1 файлу за раз):
   - `reports/00-bootstrap.md`
   - `reports/01-recon.md`
   - `reports/02-deterministic.md`
   - `reports/03-architecture.md`
   - `reports/04-readability.md`
   - `reports/05-security.md`
   - `reports/06-performance.md`
   - `reports/07-observability.md`
   - `reports/08-ai-readability.md`
   - `reports/errors.log`

2. Собери все finding'и и оценки в одну таблицу.

3. Все готовые промты из всех фаз — собери в один сквозной список с
   нумерацией.

4. Создай `reports/FINAL-REPORT.md`:

```markdown
# Финальный отчёт аудита

**Проект:** <из bootstrap>
**Дата:** <ISO>
**Версия пайплайна:** autonomous-v1

---

## Executive Summary

[5-7 предложений простым языком, для не-программиста.]

---

## Общая оценка: X / 240

| Слой | Оценка | Статус |
|------|--------|--------|
| Форматирование | X/10 | ✅/⚠️/❌ |
| Линтинг | X/10 | |
| Типизация | X/10 | |
| Тесты | X/10 | |
| Безопасность | X/30 | |
| Зависимости | X/10 | |
| Производительность | X/30 | |
| Архитектура | X/60 | |
| Читаемость | X/50 | |
| Observability | X/40 | |
| AI-readability | X/60 | |

---

## ТОП-10 критических проблем

### #1: <название>
- Где: ...
- Серьёзность: ...
- Чем грозит: ...
- Готовый промт: см. #1 ниже

### #2 ... #10

---

## Roadmap исправлений

### Неделя 1 (P0): что фиксить сегодня
- [ ] ...

### Неделя 2-3 (P1): базовая гигиена
- [ ] ...

### Месяц 1 (P1-P2): архитектура
- [ ] ...

### Месяц 2 (P2): production-готовность
- [ ] ...

### Постоянно: поддержание

---

## Все готовые промты (сквозная нумерация)

### Промт #1: <название>
\```
[текст]
\```

### Промт #2 ... #N

---

## Метрики до и после

| Метрика | Сейчас | Цель | Команда |
|---------|--------|------|---------|

---

## Что не было проверено

[Список того, что не получилось — из errors.log + перечисление того,
что выходит за рамки автономного аудита: нагрузочное тестирование,
ручной penetration testing, UX, Lighthouse в CI и т.д.]

---

## Если коротко: что делать сейчас

1. **Сегодня:** запустить промт #1
2. **На этой неделе:** промты #2 и #3
3. **На этом месяце:** прочитать Roadmap полностью

---

## Контрольные вопросы для владельца

1. Понятны ли тебе топ-3 проблемы?
2. Готов ли ты запустить промт #1 в Claude Code?
3. Что вызывает сомнения / страх?

(Ответы на эти вопросы можешь записать сюда же или отдельно.)

---

*Отчёт создан автономно через nodejs-audit/AUDIT.md.
Для повторного аудита через 3 месяца: запусти ту же команду.*
```

5. **Создай машинную сводку `reports/_meta.json`** для CI и автоматических
   проверок. Формат:

```json
{
  "version": "autonomous-v1",
  "generated_at": "<ISO-8601 timestamp>",
  "project": {
    "name": "<из package.json name>",
    "package_manager": "<npm|yarn|pnpm|bun>",
    "typescript": true,
    "src_files": 0,
    "dependencies": 0,
    "dev_dependencies": 0
  },
  "scores": {
    "formatting": 0,
    "linting": 0,
    "typing": 0,
    "tests": 0,
    "security": 0,
    "deps": 0,
    "performance": 0,
    "architecture": 0,
    "readability": 0,
    "observability": 0,
    "ai_readability": 0,
    "total": 0,
    "max_total": 240
  },
  "verdict": "<pass|warn|fail>",
  "counts": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "blockers": [
    "<одно предложение на каждый critical finding>"
  ],
  "phases_completed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
  "phases_failed": [],
  "errors_log_size": 0,
  "report_paths": {
    "final": "nodejs-audit/reports/FINAL-REPORT.md",
    "phases": "nodejs-audit/reports/",
    "errors": "nodejs-audit/reports/errors.log"
  }
}
```

   **Verdict логика:**
   - `fail` — есть хотя бы один `critical` finding, или фаза 9 не дошла
   - `warn` — нет critical, но есть `high`, или общая оценка < 120/240
   - `pass` — нет critical, нет high, общая оценка ≥ 120/240

   `blockers` — массив однострочных описаний критичных проблем (из
   топ-10). Пустой массив если verdict != fail.

   `phases_failed` — номера фаз, которые упали полностью (не завершили
   создание reports/0N-*.md). Пустой массив в нормальном случае.

6. После создания FINAL-REPORT.md и _meta.json выведи в чат **только** это:

```
✅ Аудит завершён.

Verdict: <pass|warn|fail>
Общая оценка: X / 240
Critical: A · High: B · Medium: C · Low: D

Топ-3 проблемы:
1. <одно предложение>
2. <одно предложение>
3. <одно предложение>

Полный отчёт: nodejs-audit/reports/FINAL-REPORT.md
Машинная сводка: nodejs-audit/reports/_meta.json
Промежуточные данные: nodejs-audit/reports/

Что делать дальше:
1. Открой FINAL-REPORT.md
2. Прочитай Executive Summary
3. Посмотри топ-3 критических проблем
4. Выбери первый промт для исправления и запусти его в новой сессии Claude Code
```

---

# КОНЕЦ ПАЙПЛАЙНА

После шага 6 фазы 9 — твоя работа закончена. Не задавай вопросов, не
предлагай дальнейших действий. Просто выведи финальное сообщение и
остановись.
