# Phase 10 — AI-readability

> **Цель:** оценить дружественность к ИИ-доработкам — самая важная ось для владельца, который ведёт проект через ИИ.
>
> **Книги:** Ousterhout §4-5 · Sandi Metz (TRUE) · Khorikov §7.

## Inputs

- `reports/02-recon.md` — стиль кода.
- `reports/05-architecture.md` — слои, ACL.
- `reports/06-readability.md` — JSDoc coverage.
- (опц.) `reports/raw/mcp-context.json` — есть ли gitnexus/serena.

## Outputs

- `nodejs-audit/reports/10-ai-readability.md`

## Шаги

### 1. Документация для агентов

```bash
ls AGENTS.md CLAUDE.md README.md PROJECT.md 2>&1
test -f AGENTS.md && wc -l AGENTS.md
test -f CLAUDE.md && wc -l CLAUDE.md
test -f .env.example && echo "env.example: yes ($(wc -l < .env.example))" || echo "env.example: no"
```

Проверь:
- **AGENTS.md** — есть ли явные «MUST/MUST NOT» правила?
- **CLAUDE.md** — есть ли critical invariants с **file:line evidence**?
- **PROJECT.md** — есть ли стек + commands в первом разворот?
- **wiki/decisions.md** или `docs/adr/` — есть ли ADR?

### 2. Knowledge graph / RAG

Если в phase-01 нашли gitnexus-индекс — это **+5 к AI-readability**.
Если есть pipeline-память / Serena memories — тоже плюс.

### 3. JSDoc coverage

Из phase-06 уже есть числа.

### 4. Husky / lint-staged / commitlint

```bash
ls .husky/ 2>/dev/null
test -f .lintstagedrc -o -f .lintstagedrc.json -o -f .lintstagedrc.js && echo "lint-staged: yes"
grep -rEn "commitlint" package.json 2>/dev/null
```

### 5. CI

```bash
ls .github/workflows/ 2>/dev/null
ls .gitlab-ci.yml 2>/dev/null
```

Проверь — есть ли:
- lint+test+typecheck в CI?
- Weekly security scan (`npm audit`, `gitleaks`)?
- Build verification?

### 6. TypeScript strict + path aliases

```bash
grep -rE '"strict":|"paths":' tsconfig*.json 2>/dev/null
```

### 7. Шаблоны / scaffolding

Проверь, есть ли:
- Шаблон для нового endpoint'а (`src/templates/endpoint.ts.tmpl` или README с примером).
- Шаблон для новой migration.
- Шаблон для нового component.

Без шаблонов ИИ-агент копирует с соседнего файла — это работает, но размывает консистентность.

### 8. Тест «5 минут»

Открой проект «как впервые». За 5 минут можно ли понять:
- Что это за проект?
- Как запустить?
- Где главная бизнес-логика?
- Какие конвенции?

Если **на каждый «да»** — +1 балл.

## Шаблон отчёта `10-ai-readability.md`

```markdown
# AI-readability

## TL;DR
[Насколько проект дружественен к ИИ-доработкам.]

## Тест «5 минут»

| Вопрос | Ответ |
|---|---|
| Что это за проект? | yes/no/частично |
| Как запустить? | |
| Где главная бизнес-логика? | |
| Какие конвенции? | |

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
- AGENTS.md / CLAUDE.md / PROJECT.md: <есть/нет/неполный>
- README.md: <качество>
- .env.example: <да/нет>
- ADR / wiki/decisions.md: <count>
- Gotchas: <count>

### Knowledge graph / RAG
- GitNexus index: <yes/no — большой плюс>
- Pipeline memory / Serena memories: <yes/no>
- Wiki RAG (QMD/scout-embeddings): <yes/no>

### JSDoc coverage
- Public functions: ~N
- JSDoc blocks: ~M
- Покрытие: ~X%

### Защита от ошибок ИИ
- TypeScript strict: <yes/no/partial>
- Husky pre-commit: <yes/no>
- lint-staged: <yes/no>
- commitlint: <yes/no>
- CI с проверками: <yes/no, что именно>
- Path aliases: <yes/no>

### Шаблоны
- Endpoint template: <yes/no>
- Migration template: <yes/no>
- Component template: <yes/no>

## Топ-7 улучшений для AI-readability
1. ...

## Готовые промты
[Будут собраны в QUICK-WINS.md / ROADMAP.md в phase-12]
```

## Критерии завершения

- `reports/10-ai-readability.md` существует.

## Сигналы в чат

- Старт: `[PHASE 10] STARTED — AI-readability`
- Конец: `[PHASE 10] DONE — reports/10-ai-readability.md`

→ Переход к **phase-11-synthesis.md**.
