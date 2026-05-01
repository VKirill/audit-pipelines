# Phase 01 — MCP probe

> **Цель:** заранее опросить MCP-инструменты (gitnexus, serena, pipeline), чтобы дальше пользоваться графом знаний и LSP, а не тяжёлым grep'ом.
>
> **Эта фаза — главное отличие от старого пайплайна.** Если MCP доступны — следующие фазы делают анализ за минуты, а не часы, и точнее.

## Inputs (читай перед стартом)

- `reports/00-bootstrap.md` — нужны имя проекта и тип (mono/single).

## Outputs

- `nodejs-audit/reports/01-mcp-probe.md` — что доступно, что нет, какой график-индекс есть.
- `nodejs-audit/reports/raw/mcp-context.json` — сырые ответы MCP (для последующих фаз).

## Шаги

### 1. Проверь доступность MCP-инструментов

Каждая из этих команд может молча провалиться (сервер не подключён) — записывай результат в `errors.log` и продолжай.

| MCP | Что проверить |
|---|---|
| **gitnexus** | `mcp__gitnexus__list_repos` — есть ли индекс? |
| **serena** | `mcp__serena__list_memories` — отвечает ли LSP? |
| **pipeline** | `mcp__pipeline__pipeline_health` — отвечает ли pipeline? |
| **context7** | `mcp__context7__resolve-library-id` (с тестовым `react`) — отвечает ли? |

### 2. Если есть GitNexus-индекс этого проекта

Получи **shape кодовой базы за один запрос**:

- `mcp__gitnexus__context` (repo=`<bootstrap.name>`) — clusters, processes, hot-paths.
- `mcp__gitnexus__list_repos` — список индексированных репо.
- `mcp__gitnexus__route_map` — execution flows (запросы → handlers → DB → ответ).
- `mcp__gitnexus__tool_map` — какие внешние инструменты вызываются откуда.

Сохрани в `raw/mcp-context.json`:

```json
{
  "gitnexus": {
    "available": true,
    "indexed": true,
    "context": {
      "nodes": ...,
      "edges": ...,
      "clusters": ...,
      "flows": ...
    },
    "route_map_summary": "<top-10 routes>",
    "tool_map_summary": "<external integrations>"
  },
  "serena": {
    "available": true,
    "memories": [...]
  },
  "pipeline": { "available": true, "health": "ok" },
  "context7": { "available": true }
}
```

Если индекса нет — запиши «not indexed, will fallback to grep» в `errors.log`. **Не** запускай `npx gitnexus analyze` сам (это modify-операция, выходит за read-only контракт).

### 3. Если есть Serena LSP

Активируй проект:

```
mcp__serena__activate_project (path=$PROJECT_PATH)
mcp__serena__check_onboarding_performed
mcp__serena__list_memories
```

Если онбординг ещё не делали — пропусти (не запускай его, это запишет в проект).

Запомни: с этой минуты для навигации по символам используется `find_symbol`, `find_referencing_symbols`, `get_symbols_overview` — **не grep**.

### 4. Если есть Pipeline-память

Поищи готовые знания о проекте:

```
mcp__pipeline__search_memory (query="<bootstrap.name>")
mcp__pipeline__list_memories
```

Если есть ADR/gotchas/decisions — читай и **не дублируй** их в своих находках. Цитируй вместо повтора.

### 5. Если есть существующая wiki

Из bootstrap'а ты уже знаешь, есть ли `wiki/` или `docs/`. Если есть — прочитай корневой index/overview/architecture.md (≤300 строк каждый).

Прочитанное **не цитируй построчно** в своём отчёте — только пометь, что прочитал, чтобы следующие фазы знали и тоже не дублировали.

## Шаблон отчёта `01-mcp-probe.md`

```markdown
# MCP probe

## Доступные инструменты

| Tool | Доступен | Релевантен | Использовать в фазах |
|---|---|---|---|
| gitnexus | yes/no | yes/no | 4, 5, 8, 11 |
| serena | yes/no | yes/no | 2, 5, 6, 7 |
| pipeline | yes/no | yes/no | 5, 11 |
| context7 | yes/no | yes/no | 8 (если нужны актуальные API) |

## Shape кодовой базы (если gitnexus есть)

- Nodes: ...
- Edges: ...
- Clusters: ...
- Execution flows: ...
- Top-5 hot paths: ...
- External tool integrations (tool_map): ...

## Существующая документация (прочитано в этой фазе)

- `README.md`: <1 предложение о содержании>
- `wiki/architecture.md`: <1 предложение>
- `wiki/decisions.md`: <N ADR>, темы: ...
- `wiki/gotchas.md`: <N сильных/средних issues>
- `CLAUDE.md` / `AGENTS.md`: <ключевые правила>

## Strategy для следующих фаз

- Recon (phase-02): <использовать serena get_symbols_overview / fallback grep>
- Hot-spots (phase-04): <использовать gitnexus_impact / fallback git log>
- Architecture (phase-05): <использовать gitnexus_query route_map / fallback grep>
- Security (phase-07): <использовать serena find_referencing_symbols для crypto / fallback grep>
- AI-readability (phase-10): <читать wiki/decisions.md / fallback README>
```

## Критерии завершения

- `reports/01-mcp-probe.md` существует.
- `reports/raw/mcp-context.json` существует (даже если все доступности `false`).

## Сигналы в чат

- Старт: `[PHASE 01] STARTED — MCP probe`
- Конец: `[PHASE 01] DONE — reports/01-mcp-probe.md`

→ Переход к **phase-02-recon.md**.
