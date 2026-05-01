# Фаза 2: Детерминированные проверки

## Твоя роль

Ты — инженер по качеству кода. Твоя задача: запустить все автоматические
проверки и зафиксировать результаты. Не оценивать, не интерпретировать.
Просто факты: что прошло, что упало, какие числа.

## Предварительные требования

- Фазы 0 и 1 завершены.
- Прочитай `reports/01-recon.md` — нужен контекст по стеку.

## Структура отчёта

Создай файл `nodejs-audit/reports/02-deterministic.md`:

```markdown
# Детерминированные проверки

Дата: <ISO>

## Сводная таблица

| Слой | Команда | Статус | Метрика |
|------|---------|--------|---------|
| Форматирование | prettier --check | ✅/❌ | X файлов с проблемами |
| Линтинг | eslint | ✅/❌ | X errors, Y warnings |
| Типизация | tsc --noEmit | ✅/❌ | X errors |
| Покрытие типами | type-coverage | — | X.XX% |
| Тесты | vitest run | ✅/❌ | X passed, Y failed |
| Покрытие тестами | vitest --coverage | — | lines: X%, branches: Y% |
| Уязвимости | npm audit | ✅/❌ | crit: X, high: Y, mod: Z |
| Неиспольз. зависимости | depcheck | — | X найдено |
| Мёртвый код | knip | — | X файлов, Y экспортов |
| Циклические импорты | madge | ✅/❌ | X циклов |
| Размер бандла | (если фронт) | — | X KB gzipped |

## Подробности по каждой проверке

### Слой 1: Форматирование (prettier)

[Полный вывод команды или summary если длинный]

[Если есть проблемы — список первых 20 файлов]

### Слой 2: Линтинг (eslint)

[Топ-10 правил, которые нарушаются чаще всего, с количеством]
[Файлы с наибольшим количеством ошибок]

### Слой 3: Типизация (tsc)

[Если есть ошибки — первые 30 с путями]
[Категории ошибок]

### ... (и так далее)

## Файлы-горячие точки

[Топ-10 файлов с наибольшим суммарным количеством проблем по всем линтерам.
Это кандидаты на рефакторинг в первую очередь.]

## Готовность к фазе 3
- [ ] Все команды запущены
- [ ] Результаты задокументированы
- [ ] Файлы-горячие точки определены
```

## Шаги

### Шаг 1: Установить недостающее

Если в фазе 0 что-то не установилось — переустанови. Проверь:

```bash
npx prettier --version
npx eslint --version
npx tsc --version  # если TS
```

### Шаг 2: Форматирование

```bash
npx prettier --check "src/**/*.{js,ts,jsx,tsx,json,md}" 2>&1 | tee reports/raw/prettier.log
```

Зафиксируй: количество файлов с проблемами форматирования.

### Шаг 3: Линтинг

```bash
npx eslint "src/**/*.{js,ts,jsx,tsx}" --format json --output-file reports/raw/eslint.json || true
npx eslint "src/**/*.{js,ts,jsx,tsx}" 2>&1 | tee reports/raw/eslint.log
```

Из JSON извлеки:
- Топ-10 правил (по количеству нарушений)
- Топ-10 файлов (по количеству проблем)
- Распределение error/warning

### Шаг 4: Типизация

Только если проект на TypeScript:

```bash
npx tsc --noEmit 2>&1 | tee reports/raw/tsc.log
```

Если ошибки — категоризируй:
- `TS2xxx` — типы
- `TS6xxx` — компилятор
- `TS7xxx` — implicit any
- и т.д.

```bash
npx type-coverage --strict --detail 2>&1 | tee reports/raw/type-coverage.log
```

### Шаг 5: Тесты

Сначала проверь что они вообще есть:

```bash
find . -name "*.test.*" -o -name "*.spec.*" | grep -v node_modules | head -20
```

Если тестов нет — зафиксируй это и пропусти шаг.

Если есть:

```bash
# Адаптируй под фреймворк
npx vitest run 2>&1 | tee reports/raw/tests.log
npx vitest run --coverage 2>&1 | tee reports/raw/coverage.log
```

### Шаг 6: Безопасность зависимостей

```bash
npm audit --json > reports/raw/audit.json
npm audit 2>&1 | tee reports/raw/audit.log
```

Категоризируй: critical / high / moderate / low.

### Шаг 7: Зависимости

```bash
npx depcheck --json > reports/raw/depcheck.json 2>&1
npx knip --reporter json > reports/raw/knip.json 2>&1 || true
npx madge --circular --extensions ts,tsx,js,jsx src/ 2>&1 | tee reports/raw/madge.log
```

### Шаг 8: Размер бандла (если фронт)

Только если в проекте есть production build:

```bash
# Узнай команду из package.json scripts
npm run build 2>&1 | tee reports/raw/build.log

# Размер dist/
du -sh dist/ build/ 2>/dev/null

# Размер каждого JS-файла
find dist build -name "*.js" 2>/dev/null | xargs ls -la 2>/dev/null
```

### Шаг 9: Поиск секретов

```bash
# Простой поиск явных паттернов
grep -rEn "(api[_-]?key|secret|password|token)[\"' ]*[:=][\"' ]*[A-Za-z0-9]{16,}" \
  --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" \
  --include="*.json" --include="*.env*" \
  src/ 2>&1 | tee reports/raw/secrets-grep.log

# Если установлен gitleaks
which gitleaks && gitleaks detect --source . --no-git -v 2>&1 | tee reports/raw/gitleaks.log
```

### Шаг 10: Размер файлов и функций

```bash
# Топ-20 самых больших файлов в src/
find src -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
  -exec wc -l {} + | sort -rn | head -20 | tee reports/raw/largest-files.log
```

## Сборка отчёта

После всех шагов — собери `reports/02-deterministic.md` по шаблону выше.

В конце:
- Выведи **топ-5 проблем**, которые видны из автоматических проверок.
- Перечисли, **какие проверки не получилось запустить и почему** (нет тестов,
  нет TypeScript и т.д.).
- Создай `reports/02-deterministic-DONE.md`.

## Правила

- Сохраняй **все raw-логи** в `reports/raw/`. Они нужны следующим фазам.
- Если команда падает — попробуй понять почему. Зафиксируй ошибку, не пропускай.
- Если предупреждений / ошибок очень много (тысячи) — приведи топы и
  распределения, не вываливай всё.
- Не интерпретируй "это критично / некритично" — это в следующих фазах.

## Готов? Начинай с шага 1.
