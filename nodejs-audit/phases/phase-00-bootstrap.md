# Phase 00 — Bootstrap

> **Цель:** определить контекст проекта, ничего не устанавливая в `package.json`.

## Inputs (читай перед стартом)

- (нет — это первая фаза)

## Outputs

- `nodejs-audit/reports/00-bootstrap.md`
- `nodejs-audit/reports/errors.log` (создать пустым)
- `nodejs-audit/reports/raw/` (создать)

## Шаги

### 1. Package manager

Посмотри какой lock-файл есть в корне:

| lock | manager | команды |
|---|---|---|
| `package-lock.json` | npm | `npx --yes` |
| `yarn.lock` | yarn | `yarn dlx` |
| `pnpm-lock.yaml` | pnpm | `pnpm dlx` |
| `bun.lockb` | bun | `bunx` |

Запомни — все следующие фазы используют этот runner.

### 2. TypeScript

```bash
test -f tsconfig.json -o -f tsconfig.base.json && echo "TS:yes" || echo "TS:no"
```

### 3. Monorepo / single project

```bash
jq -r '.workspaces // [] | length' package.json 2>/dev/null
ls apps/ packages/ 2>/dev/null
```

Если есть `workspaces` или папки `apps/`+`packages/` — это monorepo. Запомни список workspace'ов.

### 4. Git состояние

```bash
git status --porcelain | head -20
git log --oneline -5
```

Если есть незакоммиченные изменения — это ОК, просто зафиксируй факт. **Не требуй коммита, не создавай ветку.**

### 5. Размер проекта

```bash
# Подсчитай файлы и LOC по workspace'ам, исключая node_modules/.nuxt/.output/dist
find <src-roots> -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.vue" \) \
  ! -path "*/node_modules/*" ! -path "*/.nuxt/*" ! -path "*/.output/*" ! -path "*/dist/*" \
  | wc -l
```

### 6. .env.example

```bash
test -f .env.example && wc -l .env.example
git ls-files | grep -E "^\.env(\..+)?$" | grep -v "example\|sample"
```

Если в git есть `.env` без `.example` — это **уже finding** (фаза 7).

### 7. Существующая документация

```bash
ls README.md AGENTS.md CLAUDE.md PROJECT.md 2>&1
test -d wiki && ls wiki | head -20
test -d docs && ls docs | head -20
```

## Шаблон отчёта `00-bootstrap.md`

```markdown
# Bootstrap

- Дата: <ISO timestamp>
- Package manager: <npm/yarn/pnpm/bun>
- TypeScript: <yes/no>
- Тип репо: <single-project / monorepo>
- Workspaces: <список или —>
- Точки входа: <main из package.json или эвристика>
- Размер исходников: <N файлов, ~M строк>
- package.json:
  - name: ...
  - private: true/false
  - dependencies: <count>
  - devDependencies: <count>
- tsconfig: strict=<yes/no>, paths=<есть/нет>
- git: <чистый / N изменённых>
- .env.example: <есть/нет, N строк>
- Существующая документация: <README/AGENTS/CLAUDE/PROJECT/wiki/docs — что есть>
- Особенности (что бросилось в глаза): <1-3 строки>
```

## Критерии завершения

- `reports/00-bootstrap.md` существует и заполнен.
- `reports/errors.log` создан (можно пустым).
- `reports/raw/` создан.

## Сигналы в чат

- Старт: `[PHASE 00] STARTED — Bootstrap`
- Конец: `[PHASE 00] DONE — reports/00-bootstrap.md`

→ Переход к **phase-01-mcp-probe.md**.
