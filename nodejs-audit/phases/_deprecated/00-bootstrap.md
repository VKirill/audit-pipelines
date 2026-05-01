# Фаза 0: Bootstrap

## Твоя роль

Ты — DevOps-инженер. Твоя задача: подготовить проект к аудиту.
Установить инструменты, создать конфиги, создать AGENTS.md.

## Контекст

- Это JS/TS веб-приложение (бэкенд + фронт)
- Владелец не программист, делает проект через ИИ
- Главная цель пайплайна: чтобы код был легко дорабатываем ИИ в будущем

## Шаги

### Шаг 1: Создать ветку для аудита

```bash
git status
```

Если есть незакоммиченные изменения — попроси владельца их закоммитить, ничего
не трогай. После этого:

```bash
git checkout -b audit-2026
```

### Шаг 2: Определить package manager

Посмотри корень проекта. Найди один из файлов:
- `package-lock.json` → используй `npm`
- `yarn.lock` → используй `yarn`
- `pnpm-lock.yaml` → используй `pnpm`
- `bun.lockb` → используй `bun`

Зафиксируй в `reports/00-bootstrap.md` какой используется. Все команды дальше
адаптируй под него.

### Шаг 3: Установить инструменты

Установи в devDependencies (адаптируй команду под package manager):

```bash
npm install --save-dev \
  prettier \
  eslint \
  @typescript-eslint/parser \
  @typescript-eslint/eslint-plugin \
  eslint-config-prettier \
  eslint-plugin-import \
  eslint-plugin-security \
  eslint-plugin-sonarjs \
  eslint-plugin-unicorn \
  knip \
  depcheck \
  madge \
  type-coverage \
  audit-ci
```

Если в проекте уже есть тестовый фреймворк (vitest/jest) — не трогай.
Если тестов нет — установи `vitest` и `@vitest/coverage-v8`.

### Шаг 4: Создать конфиги

Скопируй файлы из `nodejs-audit/configs/` в корень проекта, **не перезаписывая
существующие** без подтверждения. Если файл уже есть — сохрани оба, новый с
суффиксом `.audit-suggested`, и попроси владельца сравнить.

- `configs/prettierrc.json` → `.prettierrc`
- `configs/eslint.config.js` → `eslint.config.js` (если нет ESLint flat config)
- `configs/tsconfig.strict.json` → если нет `tsconfig.json`, копируй; если есть
  — создай `tsconfig.strict.json` рядом для сравнения
- `configs/github-actions-audit.yml` → `.github/workflows/audit.yml`

### Шаг 5: Добавить скрипты в package.json

В разделе `scripts` добавь (только если их там ещё нет):

```json
{
  "scripts": {
    "audit:format": "prettier --check \"src/**/*.{js,ts,jsx,tsx,json,md}\"",
    "audit:lint": "eslint \"src/**/*.{js,ts,jsx,tsx}\" --max-warnings 0",
    "audit:types": "tsc --noEmit",
    "audit:test": "vitest run --coverage",
    "audit:security": "npm audit --audit-level=moderate",
    "audit:deps": "depcheck && knip && madge --circular --extensions ts,tsx,js,jsx src/",
    "audit:all": "npm run audit:format && npm run audit:lint && npm run audit:types && npm run audit:test && npm run audit:security && npm run audit:deps"
  }
}
```

Если проект не на TypeScript — `audit:types` замени на:
```
"audit:types": "echo 'TypeScript not used'"
```

### Шаг 6: Создать AGENTS.md

Создай в корне проекта файл `AGENTS.md` на основе шаблона
`nodejs-audit/templates/AGENTS.md.template`.

Заполни его на основе того, что ты видишь в проекте:
- Что за проект (1-2 предложения, посмотри README, package.json description)
- Стек (из package.json dependencies)
- Структуру папок (по факту что есть)
- Как запустить (из scripts в package.json)

Если чего-то не понял — оставь TODO и попроси владельца уточнить.

### Шаг 7: Добавить nodejs-audit/reports в .gitignore

Если в `.gitignore` ещё нет — добавь:

```
nodejs-audit/reports/
!nodejs-audit/reports/.gitkeep
!nodejs-audit/reports/FINAL-REPORT.md
```

### Шаг 8: Финальный отчёт фазы

Создай файл `nodejs-audit/reports/00-bootstrap.md` со структурой:

```markdown
# Bootstrap — отчёт

Дата: <ISO дата>
Package manager: <npm/yarn/pnpm/bun>

## Установлено
- [список установленных пакетов]

## Создано/изменено
- [список файлов]

## Существующие конфиги (не перезаписаны)
- [список файлов с суффиксом .audit-suggested]

## TODO для владельца
- [что нужно решить вручную]

## Готовность к фазе 1
- [ ] Все инструменты установились
- [ ] Конфиги на месте
- [ ] AGENTS.md создан
- [ ] git status чистый (всё закоммичено)
```

В конце создай `nodejs-audit/reports/00-bootstrap-DONE.md` с одной строкой:
```
Phase 0 completed at <ISO timestamp>
```

## Правила

- Не трогай код приложения. Только конфиги и установка пакетов.
- Если команда упала — зафиксируй ошибку в `reports/00-errors.md`, попробуй
  обходной путь, не молчи.
- Все изменения делай коммитами с понятными сообщениями: `chore(audit): ...`
- Если что-то непонятно про проект — спроси владельца, не угадывай.

## Готов? Начинай с шага 1.
