# Phase 02 — Recon

> **Цель:** понять архитектуру, стек, стиль за один проход. Если есть Serena/GitNexus — пользоваться ими, не grep'ом.

## Inputs

- `reports/00-bootstrap.md` — package manager, размер, workspaces.
- `reports/01-mcp-probe.md` — какие MCP доступны, существующая wiki.
- `reports/raw/mcp-context.json` — shape кодовой базы (если есть).

## Outputs

- `nodejs-audit/reports/02-recon.md`

## Шаги

### 1. Прочитай README.md, AGENTS.md, CLAUDE.md, PROJECT.md (если ещё не прочитаны в phase-01)

По одному файлу. Не читай файлы > 500 строк целиком — читай первые 300.

### 2. package.json + tsconfig.json для каждого workspace

```bash
jq '{name, version, scripts: (.scripts // {} | length), deps: (.dependencies // {} | keys), devDeps: (.devDependencies // {} | keys)}' <pkg>
cat tsconfig.json | head -60
```

### 3. Точка входа

Найди по полю `main`/`module` или эвристикам:
- `src/index.ts`, `src/main.ts`, `src/app.ts`, `src/server.ts`
- Для Nuxt/Next — `nuxt.config.ts`, `next.config.js`.

Прочитай **первые 200 строк** entry-файла.

### 4. Структура src/

```bash
find <src-root> -maxdepth 2 -type d | head -40
```

Определи паттерн:
- **layered** (controllers/services/repositories)
- **feature-based** (features/*)
- **FSD** (app/widgets/features/entities/shared)
- **Nuxt/Next standard** (pages/components/composables)
- **chaos / mixed**

### 5. Sample файлов (5 штук, разнообразных)

**Если Serena доступна** — `get_symbols_overview` для каждой выборки за одно обращение. **Иначе** — `head -100` каждого файла:

- 1 контроллер/роут.
- 1 сервис/use case.
- 1 модель/тип.
- 1 утилиту.
- 1 компонент UI (если есть фронт).

### 6. Роутинг

```bash
# Express/Fastify/Hono
grep -rEn "(app|router|fastify|hono)\.(get|post|put|delete|patch)\(" <src> --include="*.ts" --include="*.js" | head -15

# Nuxt server/api
find <web>/server/api -type f 2>/dev/null | head -30

# Telegram bot
grep -rEn "bot\.(command|callbackQuery|on|hears)\(" <bot> --include="*.ts" | head -10
```

### 7. Стиль

```bash
# kebab-case vs PascalCase файлов
find <src> -type f -name "*[A-Z]*.ts" | head -10

# await vs .then
grep -rn "await " <src> --include="*.ts" --include="*.vue" | wc -l
grep -rn "\.then(" <src> --include="*.ts" --include="*.vue" | wc -l

# default vs named exports
grep -rEn "^export default" <src> --include="*.ts" | wc -l
grep -rEn "^export (function|const|class|async function|interface|type)" <src> --include="*.ts" | wc -l
```

## Шаблон отчёта `02-recon.md`

```markdown
# Recon

## Что за проект (5–7 предложений)
[По коду + README. Что делает, для кого, главные сущности.]

## Стек (точно из package.json)
- Runtime: ...
- Backend framework: ...
- Frontend framework: ...
- DB / ORM: ...
- Tests: ...
- Build: ...

## Размер
- Файлов в src/: N
- Строк кода: M
- Production deps: X · Dev deps: Y

## Структура (как есть)
[Дерево + что в каждой папке.]

## Архитектурный паттерн (первое впечатление)
[layered / feature-based / FSD / chaos / mixed]

## Стиль кода
- Именование файлов: kebab-case / camelCase / PascalCase / mixed
- async-стиль: await / .then / mixed (с числами)
- Импорты: alias / relative / mixed
- Экспорты: named / default / mixed (с числами)
- TS strict: yes / no / partial

## 3 примера кода (5–10 строк каждый)
[С указанием путей и строк.]

## 5 первых сигналов проблем
[Гипотезы для следующих фаз. С путями к файлам.]

## 3 положительных наблюдения
[Что хорошо. Если ничего хорошего — пиши честно.]

## Ссылка на главу REFERENCES.md
- Ousterhout §4-5 (deep modules vs shallow) — как оценивать в Phase 6.
```

## Критерии завершения

- `reports/02-recon.md` существует.

## Сигналы в чат

- Старт: `[PHASE 02] STARTED — Recon`
- Конец: `[PHASE 02] DONE — reports/02-recon.md`

→ Переход к **phase-03-deterministic.md**.
