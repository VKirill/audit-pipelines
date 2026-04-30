# REFERENCE — MCP tools deep dive (Serena + GitNexus)

> **v4 — 100% использование Serena + GitNexus.** Каждый шаг discover/детектор инструктирует ИИ-агента использовать конкретный MCP-tool. Bash/rg остаётся как fallback.

---

## Serena (LSP-based semantic navigation)

### Главные tools для DB-аудита

| Tool | Сигнатура | Когда использовать в DB-аудите |
|------|-----------|--------------------------------|
| `find_symbol` | `(name_path, include_body=false, relative_path=null)` | Точечный поиск модели/класса/функции. `include_body=true` ТОЛЬКО когда читаешь тело транзакции. |
| `get_symbols_overview` | `(file_path)` | Перед чтением schema-файла или transaction module — overview без тел |
| `find_referencing_symbols` | `(name_path, file?)` | **CRITICAL для money discovery**. Нашёл `balance` колонку → `find_referencing_symbols('balance')` → ВСЕ места где она trogается |
| `search_for_pattern` | `(regex, glob_filter?)` | Regex по проекту. Для `$queryRawUnsafe`, `BEGIN`, `FOR UPDATE`, custom wrappers |
| `find_file` | `(mask)` | Прокси для `find -name` |
| `list_dir` | `(path, recursive?)` | Прокси для `ls -R` |
| `write_memory` | `(name, content)` | **Audit progress tracking**. После каждой фазы → `write_memory('audit_phase_NN', summary)` |
| `read_memory` | `(name)` | Возобновление сессии: `read_memory('audit_progress')` |
| `list_memories` | `()` | Список сохранённых заметок (auditor cross-phase notes) |

### Anti-patterns

❌ `find_symbol('SomeClass', include_body=true)` без необходимости — тащит всё тело
❌ `search_for_pattern(broad_regex)` на всём проекте — медленно; используй `relative_path` для скоупа
❌ Чтение whole-file через Read tool, когда можно `get_symbols_overview` + точечный `find_symbol`

### Лучшие сценарии для DB-аудита

#### 1. Discovery money endpoints (вместо ручного rg)

```
Step 1: get hints.money_columns from manifest
Step 2: for each money column, e.g. ContentProject.balanceRub:
        find_referencing_symbols('balanceRub')
Step 3: classify each caller:
        - Reads only? → ignored
        - Writes? → money_endpoint candidate (read body + check transaction wrapper)
```

#### 2. Verify transaction body

```
Step 1: hints.transaction_sites[i].symbol = 'deductFromBalance'
Step 2: find_symbol('deductFromBalance', include_body=true,
                    relative_path='apps/crm/src/features/content/lib/cbr.ts')
Step 3: parse body — есть ли $transaction, BEGIN, FOR UPDATE?
```

#### 3. SQLi surface

```
search_for_pattern(r'\$query(?:Raw)?Unsafe|\$execute(?:Raw)?Unsafe')
  → 14 hits в library-server.ts (vechkasov-style проект)
For each hit: read_file context −10/+10 lines + check if user input flow
```

#### 4. Multi-tenant verification

```
Step 1: route_map (GitNexus) → all HTTP handlers
Step 2: for each handler:
        find_symbol(handler_function, include_body=true)
        parse body for `where: { tenantId: ... }` or `WHERE tenant_id =`
Step 3: handlers без tenant filter в multi-tenant проекте → critical finding
```

---

## GitNexus (knowledge graph + cypher)

### MCP tools

| Tool | Параметры | Когда |
|------|-----------|-------|
| `query` | `search_query, context?, goal?, limit?, content?` | Концептуальный поиск: «найди places где меняется balance». Возвращает execution flows. |
| `context` | `name|uid, file?, content?` | 360° view: callers + callees + processes для конкретного символа |
| `impact` | `target, direction='upstream'|'downstream', depth=3` | **Главный для phase 11 deep_dive**. Blast radius при изменении функции |
| `cypher` | `query` | **Самый мощный**. Произвольные графовые запросы |
| `detect_changes` | `scope='staged'|'unstaged'` | Pre-commit risk analysis (полезно для CI integration) |
| `route_map` | `()` | Все HTTP routes проекта |
| `tool_map` | `()` | MCP tools (если проект — MCP server) |
| `list_repos` | `()` | Multi-repo навигация |

### Graph schema (Tree-sitter parsed)

**Nodes:**
- `Function`, `Method`, `Class`, `Interface`, `Module`
- `File`, `Folder`
- `Process` (execution flow)
- `Handler` (HTTP/MCP route)
- `Field` (property of class/struct)

**Edges:**
- `CALLS` — function/method calls
- `IMPORTS` — module imports
- `INHERITS` / `IMPLEMENTS` — class hierarchy
- `READS` / `WRITES` — field access
- `IS_PART_OF` — process step membership
- `EXPORTS` — module exports

### Cypher cookbook для DB-аудита

#### 1. Найти все callers $queryRawUnsafe (SQLi surface map)

```cypher
MATCH (caller:Function)-[:CALLS]->(target:Function)
WHERE target.name IN ['$queryRawUnsafe', '$executeRawUnsafe']
RETURN caller.file, caller.name, caller.line
ORDER BY caller.file
```

#### 2. Handlers без auth middleware (auth bypass detection)

```cypher
MATCH (h:Handler)
WHERE h.path STARTS WITH '/api/'
  AND NOT EXISTS {
    MATCH (h)-[:CALLS|USES_MIDDLEWARE*1..3]->(m:Function)
    WHERE m.name =~ '(?i).*auth.*|.*authenticate.*|.*verify.*'
  }
RETURN h.path, h.method, h.file, h.line
ORDER BY h.path
```

#### 3. Все функции, изменяющие money колонку

```cypher
MATCH (f:Function)-[:WRITES]->(field:Field)
WHERE field.name IN ['balance', 'balanceRub', 'amountRub', 'remainingRub']
RETURN f.file, f.name, field.class_name, field.name
```

#### 4. Race condition candidates: SELECT followed by UPDATE без FOR UPDATE

```cypher
MATCH (f:Function)
WHERE f.body =~ '(?s).*SELECT.*UPDATE.*'
  AND NOT f.body =~ '(?i).*FOR\\s+UPDATE.*'
  AND NOT f.body =~ '(?i).*\\$transaction.*'
RETURN f.file, f.name
LIMIT 50
```

#### 5. Functions с N+1 паттерном (call в for-loop)

```cypher
MATCH (caller:Function)-[:CALLS]->(query:Function)
WHERE query.name =~ '(?i)find.*|select.*|query.*'
  AND caller.body =~ '(?s).*for.*\\{[^}]*' + query.name + '.*'
RETURN caller.file, caller.name, query.name
```

#### 6. Cross-tenant data leakage (handler без tenant filter)

```cypher
MATCH (h:Handler)-[:CALLS*1..5]->(q:Function)
WHERE q.name =~ '(?i)find.*|select.*'
  AND NOT q.body =~ '(?i).*tenant[_]?id.*|.*workspace[_]?id.*|.*project[_]?id.*'
RETURN h.path, q.file, q.name
LIMIT 30
```

#### 7. Funcgions touching pgvector/embeddings (для AI/ML coverage)

```cypher
MATCH (f:Function)
WHERE f.body =~ '(?i).*embedding.*|.*vector.*|.*queryRawUnsafe.*<=>.*'
RETURN f.file, f.name
LIMIT 50
```

### `impact` для phase 11 deep_dive (auto-fill)

Для каждого critical finding:

```bash
# Auto-fill section "1. Trace" + "3. Blast radius"
gitnexus impact --direction upstream --depth 3 deductFromBalance
# Output: list of upstream callers with confidence
```

Это заменяет `_agent fills_` placeholder. ИИ-агент дополняет только creative секции (Fix variants, Test strategy).

### `context` для understanding before recommendation

```bash
gitnexus context deductFromBalance
# Output: callers, callees, processes, IS_PART_OF flow
```

Если функция входит в 3 разных process flows (например, content generation + ad spend + billing) → fix должен учитывать все 3.

---

## Combined workflow (Serena + GitNexus)

### Pattern A: Money column → endpoints

```
1. manifest.hints.money_columns[i].columns = ['balanceRub']
2. Serena.find_referencing_symbols('balanceRub')      # все символы, ссылающиеся на field
3. GitNexus.cypher(MATCH (f)-[:WRITES]->(:Field {name:'balanceRub'}))  # точные writers
4. Intersection — verified money endpoints (более точно чем regex)
```

### Pattern B: SQLi surface

```
1. Serena.search_for_pattern(r'\$query(?:Raw)?Unsafe')   # все вхождения
2. For each: Serena.find_symbol(<containing function>, include_body=true)
3. Read context — есть ли динамическая склейка?
4. GitNexus.impact direction=upstream — какие routes доходят сюда?
5. Если route public + динамическая склейка → critical SQLi
```

### Pattern C: Phase 11 deep_dive auto-fill

```
For each critical finding f:
1. GitNexus.impact(f.location.symbol, direction=upstream)  → trace + blast radius
2. GitNexus.context(f.location.symbol)                     → 360° view
3. Serena.find_symbol(f.location.symbol, include_body=true) → exploit body
4. Pre-fill deep_dive sections 1, 3, 4(callees) automatically
5. Agent fills only sections 4(fix variants), 5(test), 6(next step) — creative
```

---

## Anti-recursion на MCP инструментах

После 3 пустых ответов → fallback на bash/ripgrep. Обновляй `_known_unknowns.md` пометкой «MCP-tool degraded».

```
Serena unavailable     → ripgrep + Read tool
GitNexus stale         → npx gitnexus analyze; if still stale → bash + grep
GitNexus cypher empty  → попробуй query/context, потом ripgrep
```

---

## Sources

- [Serena GitHub](https://github.com/oraios/serena) — official LSP-based MCP server
- [GitNexus GitHub](https://github.com/abhigyanpatwari/GitNexus) — knowledge graph engine, MCP-native
- [GitNexus on MarkTechPost (April 2026)](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/) — overview of 7 MCP tools
- [GitNexus npm package](https://www.npmjs.com/package/gitnexus) — CLI + MCP

Sources:
- [Serena GitHub](https://github.com/oraios/serena)
- [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/)
- [GitNexus GitHub](https://github.com/abhigyanpatwari/GitNexus)
