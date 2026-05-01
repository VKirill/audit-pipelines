<div align="center">

  <h1>⚡ Node.js Audit Pipeline <code>chained-v2</code></h1>

  <p>
    <b>Автономный архитектурный аудит JS/TS проекта за один прогон Claude Code.</b><br/>
    Один промт · 13 фаз · MCP-first · подготовка к продакшену
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-chained--v2-orange" alt="chained-v2"/>
    <img src="https://img.shields.io/badge/stack-JS%20%2F%20TS%20%2F%20Node-339933?logo=node.js&logoColor=white" alt="JS/TS/Node"/>
    <img src="https://img.shields.io/badge/phases-13-blue" alt="13 phases"/>
    <img src="https://img.shields.io/badge/MCP-first-purple" alt="MCP-first"/>
    <img src="https://img.shields.io/badge/mode-read--only-success" alt="Read-only"/>
    <img src="https://img.shields.io/badge/output-FINAL%20%2B%20QUICK--WINS%20%2B%20ROADMAP%20%2B%20ADR%20%2B%20REFACT-9b59b6" alt="4 outputs"/>
  </p>

  <p>
    <a href="../README.md">← Назад к Audit Pipelines</a> ·
    <a href="./MASTER_PROMPT.md">📋 MASTER_PROMPT</a> ·
    <a href="./AUDIT.md">📑 AUDIT (индекс)</a> ·
    <a href="./REFERENCES.md">📚 REFERENCES (15 книг)</a>
  </p>

</div>

<br/>

> **Идея.** Ты вставляешь один промт в новую сессию Claude Code — Claude сам идёт по **13 поэтапным файлам** (`phases/phase-00…phase-12`), на каждой фазе использует MCP-инструменты (gitnexus, serena, pipeline-память), и в конце выдаёт **5 артефактов**: полный отчёт, машинную сводку, quick-wins на неделю, roadmap на 3 месяца, черновики ADR и refactoring-таргеты с fitness functions.
>
> Цель — не просто «найти баги», а **подготовить codebase к продакшену** так, чтобы будущие доработки и обновления делались без боли.

---

## Чем `chained-v2` отличается от `autonomous-v1`

| Аспект | v1 (старая) | chained-v2 (текущая) |
|---|---|---|
| Структура | Один большой `AUDIT.md` (40 KB) | 13 phase-файлов в `phases/`, каждый self-contained |
| Знания о коде | grep + npx-tools | **MCP-first**: gitnexus графы, serena LSP, pipeline-память — fallback на grep |
| Hot-spots | нет | **Phase 04** — `churn × fan-in` (Tornhill) |
| Архитектура | 6 абстрактных «осей» | **DDD-словарь** (anemic/rich, aggregates, ACL) + Clean Architecture + 6 осей |
| Security | OWASP Top 10 «в общем» | **OWASP Top 10 + ASVS L1-L2** чек-лист |
| Книги | без атрибуции | **15 книг** с главами (REFERENCES.md), каждый finding ссылается |
| Финальный отчёт | один markdown | **5 артефактов**: FINAL-REPORT, _meta.json, QUICK-WINS, ROADMAP, ADR-DRAFTS, REFACTORING |
| Trade-off matrix | нет | **Richards & Ford 10 ilities** (current → target) |
| Fitness functions | нет | в каждом ADR-DRAFT и REFACTORING-target — CI-test |
| Cytometric criteria | нет | у каждого refactor — «before metric → after metric» |
| Совместимость | autonomous-v1 в `_meta.json` | `version: "chained-v2"` в `_meta.json` |

---

## Запуск

В Claude Code в корне проекта:

```
Прочитай /home/ubuntu/projects/audit-pipelines/nodejs-audit/MASTER_PROMPT.md
и выполни полный аудит проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

**От пользователя — только путь.** Всё остальное модель делает сама:
- ✅ Копирует пайплайн в `<project>/nodejs-audit/`.
- ✅ Patch-ит `.gitignore`.
- ✅ Опрашивает MCP-серверы (gitnexus / serena / pipeline / context7).
- ✅ Идёт по 13 фазам non-stop.
- ✅ Пишет 5 артефактов в `nodejs-audit/reports/`.
- ✅ В чат — короткое финальное сообщение.

---

## Архитектура пайплайна

```
nodejs-audit/
├── MASTER_PROMPT.md                ← диспетчер (короткий, без логики фаз)
├── AUDIT.md                        ← индекс
├── README.md                       ← этот файл
├── REFERENCES.md                   ← 15 книг + главы
├── IMPROVEMENT_NOTES.md            ← заметки по апгрейду v1→v2
├── phases/                         ← 13 поэтапных файлов
│   ├── phase-00-bootstrap.md
│   ├── phase-01-mcp-probe.md       (NEW: gitnexus + serena + wiki RAG)
│   ├── phase-02-recon.md
│   ├── phase-03-deterministic.md
│   ├── phase-04-hotspots.md        (NEW: churn × fan-in, Tornhill)
│   ├── phase-05-architecture-ddd.md (DDD + Clean + 6 осей)
│   ├── phase-06-readability.md
│   ├── phase-07-security.md         (OWASP Top 10 + ASVS L1-L2)
│   ├── phase-08-performance.md
│   ├── phase-09-observability.md
│   ├── phase-10-ai-readability.md
│   ├── phase-11-synthesis.md        (+ Trade-off matrix Richards & Ford)
│   ├── phase-12-prod-roadmap.md     (NEW: 4 артефакта)
│   └── _deprecated/                 ← старая v1 для совместимости
├── templates/
│   ├── adr-draft.md                ← черновик архитектурного решения
│   ├── refactoring-target.md       ← file-level таргет с fitness function
│   ├── quick-wins.md               ← атомарные коммиты на неделю
│   ├── roadmap.md                  ← 3-месячный план
│   ├── trade-off-matrix.md         ← Richards & Ford 10 ilities
│   ├── eslint.config.js            ← (старые шаблоны для CI)
│   ├── prettierrc.json
│   ├── tsconfig.strict.json
│   ├── github-actions-audit.yml
│   └── findings-template.md
└── configs/
    └── (per-tool configs)
```

---

## Артефакты на выходе

После полного прогона в `<project>/nodejs-audit/reports/`:

```
reports/
├── 00-bootstrap.md          ← phase-00
├── 01-mcp-probe.md          ← phase-01: что доступно из MCP
├── 02-recon.md              ← phase-02: стек и стиль
├── 03-deterministic.md      ← phase-03: prettier/eslint/tsc/tests/audit/depcheck/knip/madge
├── 04-hotspots.md           ← phase-04: топ опасных файлов
├── 05-architecture.md       ← phase-05: DDD-классификация + 6 осей
├── 06-readability.md        ← phase-06
├── 07-security.md           ← phase-07: OWASP + ASVS
├── 08-performance.md        ← phase-08
├── 09-observability.md      ← phase-09: 8 pillars Susan Fowler
├── 10-ai-readability.md     ← phase-10: тест «5 минут»
├── FINAL-REPORT.md          ← phase-11: главный отчёт + Trade-off matrix
├── _meta.json               ← phase-11: машинная сводка для CI
├── QUICK-WINS.md            ← phase-12: атомарные коммиты на неделю
├── ROADMAP.md               ← phase-12: 3-месячный план с DAG
├── ADR-DRAFTS/              ← phase-12: черновики архитектурных решений
│   ├── ADR-001-...md
│   └── ...
├── REFACTORING/             ← phase-12: file-level таргеты с fitness functions
│   ├── <slug>.md
│   └── ...
├── errors.log               ← аккумулятор ошибок пайплайна
└── raw/                     ← сырые логи каждого инструмента
```

**Что с этим делать:**
- **`FINAL-REPORT.md`** — открыть, прочитать Executive Summary + топ-10.
- **`QUICK-WINS.md`** — каждый шаг = 1 атомарный коммит, выполняй по 1 в день.
- **`ROADMAP.md`** — стратегический план, по нему распределяешь работу на квартал.
- **`ADR-DRAFTS/ADR-XXX.md`** — каждый = атомарный PR в проект (после approval идёт в `wiki/decisions.md`).
- **`REFACTORING/<slug>.md`** — каждый = атомарный PR с fitness function в CI.

---

## MCP-инструменты (опционально, но круто)

Если в Claude Code подключены — пайплайн использует их автоматически:

| MCP | Зачем |
|---|---|
| **gitnexus** | Knowledge graph (clusters, flows, fan-in) — для phase-04 (hot-spots) и phase-05 (architecture). |
| **serena** | LSP — для точной навигации по символам в phase-02/05/07. |
| **pipeline** | Память pipeline (lessons, gotchas) — для phase-10 (AI-readability). |
| **context7** | Актуальная документация библиотек — для phase-08 (performance, version-specific советы). |

Без MCP пайплайн работает через grep — медленнее и менее точно, но рабочий.

---

## CI integration

```yaml
- name: Run audit
  run: |
    claude --print "Прочитай nodejs-audit/MASTER_PROMPT.md и выполни полный аудит проекта: PROJECT_PATH=$PWD"

- name: Check verdict
  run: |
    verdict=$(jq -r .verdict nodejs-audit/reports/_meta.json)
    if [ "$verdict" = "fail" ]; then
      echo "::error::Audit verdict=fail"
      jq -r '.blockers[]' nodejs-audit/reports/_meta.json
      exit 1
    fi

- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: audit-report
    path: nodejs-audit/reports/
    retention-days: 30
```

`_meta.json` содержит `verdict` (`pass`/`warn`/`fail`), `scores`, `ilities`, `blockers`, `phases_completed/failed`.

---

## Цикл фиксов после аудита

Применяй артефакты по одному в **новой сессии**:

```bash
git checkout -b fix/qw-1
```

```
Прочитай nodejs-audit/reports/QUICK-WINS.md и выполни шаг 1.1.
Минимальные изменения. Один коммит. После — npm run lint && npm run test.
```

Один шаг = одна сессия = одна ветка = один merge.

Для **архитектурных** изменений:

```bash
git checkout -b adr-021
```

```
Прочитай nodejs-audit/reports/ADR-DRAFTS/ADR-021-...md.
Выполни план. Добавь fitness-test в CI. Перенеси ADR в wiki/decisions.md.
```

---

## Когда использовать chained-v2

> ✅ Перед стратегической работой над проектом (квартальный roadmap).
> ✅ Когда проект готовят к продакшену.
> ✅ Когда нужен **архитектурный** взгляд, не только linting.
> ✅ Когда есть `wiki/`, ADR, ИИ-агенты — пайплайн их учитывает.

> ❌ Если нужен **просто quick smoke-check** на 10 минут — используй меньшие пайплайны (frontend / codebase).
> ❌ Для не-JS/TS проектов — этот пайплайн откажется работать.

---

## Версии

- **autonomous-v1** — старая, single `AUDIT.md`. Архивирована в `phases/_deprecated/`.
- **chained-v2** — текущая, цепочка из 13 файлов + MCP-first + 4 артефакта.

`_meta.json.version` поле даёт обратную совместимость для CI.

---

<div align="center">

[← Назад к Audit Pipelines](../README.md) ·
[MASTER_PROMPT](./MASTER_PROMPT.md) ·
[AUDIT.md](./AUDIT.md) ·
[REFERENCES.md](./REFERENCES.md)

</div>
