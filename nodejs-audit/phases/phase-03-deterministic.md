# Phase 03 — Deterministic checks

> **Цель:** запустить все возможные автоматические инструменты, собрать сырые данные.

## Inputs

- `reports/00-bootstrap.md` — pkg manager, monorepo structure.
- `reports/02-recon.md` — список workspace'ов и их scripts.

## Outputs

- `nodejs-audit/reports/03-deterministic.md`
- `nodejs-audit/reports/raw/prettier.log`
- `nodejs-audit/reports/raw/eslint-<workspace>.json`
- `nodejs-audit/reports/raw/tsc-<workspace>.log`
- `nodejs-audit/reports/raw/tests-<workspace>.log`
- `nodejs-audit/reports/raw/audit.json`
- `nodejs-audit/reports/raw/depcheck-<workspace>.json`
- `nodejs-audit/reports/raw/knip-<workspace>.json`
- `nodejs-audit/reports/raw/madge-<workspace>.log`
- `nodejs-audit/reports/raw/largest-files.log`
- `nodejs-audit/reports/raw/secrets-grep.log`

## Правила

- Все инструменты через `npx --yes <tool>` без установки в проект.
- Если команда упала — `errors.log` + следующий шаг.
- Для monorepo — отдельный файл сырых логов на каждый workspace.

## Шаги

### 3.1 Prettier

```bash
npx --yes prettier@latest --check "<src-globs>" 2>&1 \
  | tee reports/raw/prettier.log
```

Извлеки: количество файлов с расхождениями.

### 3.2 ESLint (если конфиг есть)

Для каждого workspace с конфигом:

```bash
test -f eslint.config.js -o -f eslint.config.mjs -o -f eslint.config.cjs -o -f .eslintrc.json -o -f .eslintrc.js \
  && npx --yes eslint <src> --format json > reports/raw/eslint-<ws>.json 2>reports/raw/eslint-<ws>-stderr.log \
  || echo "no eslint config in <ws>" >> reports/errors.log
```

Из JSON извлеки:
- total errors, total warnings;
- топ-10 правил (по count);
- топ-10 файлов (по сумме err+warn);
- fatal-парс ошибки (`ruleId: null`).

### 3.3 TypeScript

Для каждого workspace с tsconfig.json:

```bash
# bot/api/server-side
npx --yes -p typescript@latest tsc --noEmit 2>&1 | tee reports/raw/tsc-<ws>.log

# Vue/Nuxt
npx --yes -p typescript@latest -p vue-tsc@latest vue-tsc --noEmit 2>&1 | tee reports/raw/tsc-<ws>.log
```

Подсчитай `grep -c "error TS"`.

### 3.4 Tests

Если в `scripts.test` есть `vitest` / `jest` / `mocha`:

```bash
timeout 240 npx <runner> run 2>&1 | tee reports/raw/tests-<ws>.log
```

**Не запускай coverage** — слишком долго.

### 3.5 npm audit

```bash
npm audit --json > reports/raw/audit.json 2>&1 || true
jq '.metadata.vulnerabilities' reports/raw/audit.json
```

### 3.6 Dependencies

```bash
npx --yes depcheck --json > reports/raw/depcheck-<ws>.json 2>&1 || true
npx --yes knip --reporter json > reports/raw/knip-<ws>.json 2>&1 || true
npx --yes madge --circular --extensions ts,tsx,js,jsx <src> > reports/raw/madge-<ws>.log 2>&1 || true
```

> **Важно:** depcheck для Nuxt-проектов даст много false positives (модули в `nuxt.config.ts`). Knip обычно точнее. Madge падает на `.vue` — для web записать «not applicable» в errors.log.

### 3.7 Размеры файлов

```bash
find <src-roots> -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.vue" \) \
  -exec wc -l {} + 2>/dev/null | sort -rn | head -25 \
  > reports/raw/largest-files.log
```

### 3.8 Секреты в коде (легковесный)

```bash
grep -rEn "(api[_-]?key|secret|password|token)[\"' ]*[:=][\"' ]*[A-Za-z0-9_-]{16,}" \
  --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.vue" \
  <src> 2>&1 | grep -vE "test|spec|mock|process\.env|\\\$\\{" \
  > reports/raw/secrets-grep.log || echo "" > reports/raw/secrets-grep.log
```

Большинство хитов — false positive (regex/parsing). Это **сигнал**, не приговор — детально проверишь в Phase 7.

## Шаблон отчёта `03-deterministic.md`

```markdown
# Deterministic checks

## Сводная таблица

| Проверка | Команда | Результат |
|---|---|---|
| Prettier | --check | <N> файлов с проблемами / OK |
| ESLint (<ws>) | --format json | <X> errors, <Y> warnings / config not found |
| TypeScript (<ws>) | tsc --noEmit | <Z> errors / OK |
| Tests (<ws>) | <runner> run | <A> passed, <B> failed / no tests |
| npm audit | --json | crit:X high:Y mod:Z low:W |
| depcheck (<ws>) | | unused: <count> |
| knip (<ws>) | | unused exports: <count>, files: <count> |
| madge --circular (<ws>) | | <N> циклов |

## ESLint топ-10 правил (<ws>)
[Список из raw/eslint-<ws>.json]

## ESLint топ-10 файлов
[С путями и числами]

## TypeScript ошибки (категории)
[По кодам TS2xxx, TS7xxx]

## Циклические импорты
[Если есть, привести список]

## Knip — топ файлов с unused exports
[С числами]

## Топ-10 самых длинных файлов
[Из raw/largest-files.log]

## Подозрительные секреты в коде
[Из raw/secrets-grep.log + классификация: real/false-positive]

## Что не удалось проверить
[Из errors.log за эту фазу]
```

## Критерии завершения

- `reports/03-deterministic.md` существует.
- В `reports/raw/` есть логи каждого инструмента (или запись в errors.log).

## Сигналы в чат

- Старт: `[PHASE 03] STARTED — Deterministic checks`
- Конец: `[PHASE 03] DONE — reports/03-deterministic.md`

→ Переход к **phase-04-hotspots.md**.
