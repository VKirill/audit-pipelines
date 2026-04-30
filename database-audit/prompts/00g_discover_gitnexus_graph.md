# 00g — Deep discovery via GitNexus (knowledge graph + cypher)

> Запускается **после** 00f. Цель — graph-based анализ что rg/Serena не достанут: blast radius, multi-step call chains, process flows.

---

## Pre-flight

```bash
gitnexus list_repos       # текущий проект индексирован?
gitnexus status           # свежий ли индекс?
# Если устарел:
npx gitnexus analyze --embeddings    # 1-5 минут
```

Если GitNexus недоступен — fallback на Serena + ripgrep, помечай `_known_unknowns.md`.

---

## Шаг 1 — `route_map` всех handlers (для PII + auth coverage)

```bash
gitnexus.route_map
# Output: list of HTTP routes with handler symbol + file
```

Для каждого route проверь:
- [ ] Авторизация (соответствует ли `withAuth`/`auth()` в теле handler)
- [ ] Возвращает ли PII (если да — нужен audit log)
- [ ] Меняет ли money state (если да — должен быть idempotency)

Это **верификация** того, что 00f нашёл через `search_for_pattern`. GitNexus вычисляет полный call-graph.

---

## Шаг 2 — `impact` на каждой transaction-функции

Для каждой `hints.transaction_sites[i]`:

```bash
gitnexus.impact <symbol_name> --direction upstream --depth 3
# Например:
gitnexus.impact deductFromBalance --direction upstream --depth 3
```

Output:
- Все upstream callers (routes/cron/workers, доходящие до функции)
- Confidence scores
- HIGH/CRITICAL риск маркеры

**Используется для phase 11 deep_dive section 3 «Blast radius»** — авто-fill.

Сохрани в evidence:
```
audit/evidence/_serena_gitnexus/impact_deductFromBalance.json
```

---

## Шаг 3 — `context` для понимания money функций

Для каждой `hints.money_endpoints[i]`:

```bash
gitnexus.context deductFromBalance --content
# Output: callers + callees + processes + step occupancy
```

Это даёт **trace** для phase 11 section 1.

---

## Шаг 4 — Cypher: SQLi callers map

```bash
gitnexus.cypher 'MATCH (caller:Function)-[:CALLS]->(target:Function)
WHERE target.name IN ["$queryRawUnsafe", "$executeRawUnsafe"]
RETURN caller.file, caller.name, caller.line
ORDER BY caller.file'
```

Сохрани результат — это полный SQLi surface map. Сравни с тем что нашёл `00f` через `search_for_pattern`. Должно совпасть; если differ — fix manifest.

---

## Шаг 5 — Cypher: handlers без auth

```bash
gitnexus.cypher 'MATCH (h:Handler)
WHERE h.path STARTS WITH "/api/"
  AND NOT EXISTS {
    MATCH (h)-[:CALLS|USES_MIDDLEWARE*1..3]->(m:Function)
    WHERE m.name =~ "(?i).*auth.*|.*authenticate.*|.*verify.*|withAuth"
  }
RETURN h.path, h.method, h.file, h.line'
```

Каждый result → potential auth bypass. Добавь в `hints.auth_bypass_candidates` (новая категория, добавить в schema).

---

## Шаг 6 — Cypher: race condition candidates

```bash
gitnexus.cypher 'MATCH (f:Function)
WHERE f.body CONTAINS "SELECT"
  AND f.body CONTAINS "UPDATE"
  AND NOT (f.body =~ "(?i).*FOR\\s+UPDATE.*"
        OR f.body =~ "(?i).*\\$transaction.*"
        OR f.body =~ "(?i).*BEGIN.*COMMIT.*")
RETURN f.file, f.name'
```

Это additional verification к 00b. Если найдены новые места → расширь `hints.transaction_sites` с `kind: missing-transaction`.

---

## Шаг 7 — Cypher: cross-tenant leakage

Для multi-tenant проектов (если `manifest.hints.multi_tenant_isolation.model = 'discriminator-column'`):

```bash
DISC=$(yq '.hints.multi_tenant_isolation.discriminator_column' audit/manifest.yml)
gitnexus.cypher "MATCH (h:Handler)-[:CALLS*1..5]->(q:Function)
WHERE q.body =~ '(?i).*find.*|.*select.*|.*update.*|.*delete.*'
  AND NOT q.body CONTAINS '${DISC}'
RETURN h.path, q.file, q.name
LIMIT 30"
```

Каждый result → handler делает query без tenant-filter → potential cross-tenant leak. Critical finding.

---

## Шаг 8 — Cypher: N+1 detection (graph-based, точнее чем 00d)

```bash
gitnexus.cypher 'MATCH (caller:Function)-[:CALLS]->(query:Function)
WHERE query.name =~ "(?i)find.*|first.*|select.*|query.*"
  AND caller.body =~ "(?s).*(for|forEach|\\.map\\().*\\b" + query.name + "\\b.*"
RETURN caller.file, caller.name, query.name
LIMIT 50'
```

Это **дополняет** heuristic из 00d более точным graph-based. Confidence находок выше.

---

## Шаг 9 — Cypher: vector search performance

Если `hints.vector_db_indexes` непустой:

```bash
gitnexus.cypher 'MATCH (f:Function)
WHERE f.body =~ "(?i).*embedding\\s*<=>.*|.*<#>.*|.*<\\->.*"
RETURN f.file, f.name'
```

Output: каждое использование vector similarity search. Проверь:
- [ ] Используется ли HNSW index? (быстро) или нет (sequential scan)
- [ ] Передаётся ли `ef_search` параметр?

Это для phase 08 perf review.

---

## Шаг 10 — Save evidence + memory

```
serena.write_memory(
    name='audit_phase_discover_gitnexus',
    content='GitNexus phase complete: route_map=N routes, impact analyzed=M critical funcs, cypher queries executed=K, new findings=P.'
)
```

Сохрани **все** GitNexus результаты в:

```
audit/evidence/_serena_gitnexus/
  ├── route_map.json
  ├── sqli_callers.cypher.json
  ├── auth_bypass.cypher.json
  ├── race_candidates.cypher.json
  ├── cross_tenant_leak.cypher.json
  ├── n_plus_one.cypher.json
  └── impact_<symbol>.json (per critical function)
```

---

## Quality gate перед переходом к 00z

- [ ] route_map exported
- [ ] impact для каждой `transaction_sites` запущен
- [ ] cypher SQLi callers + auth bypass + race + cross-tenant + N+1 запущены
- [ ] Все результаты сохранены в evidence
- [ ] Memory обновлено

Без этих результатов phase 11 deep_dive не сможет auto-fill blast radius.

---

## Auto-fill для phase 11 (что они дают)

Phase 11 deep_dive имеет 6 секций. GitNexus auto-fill секции:
- **1. Trace** — `gitnexus.context` (callers/callees/processes)
- **3. Blast radius** — `gitnexus.impact upstream` + `route_map` cross-reference

ИИ-агент остаётся для:
- **2. Exploit reproduction** (creative)
- **4. Fix variants** (creative)
- **5. Test strategy** (creative)
- **6. Recommended next step** (decision)

Это **резко** сокращает ручную работу ИИ в фазе 11.
