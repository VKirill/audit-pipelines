# Что круче в TODO/architecture-2026 и как поднять наш `nodejs-audit` до архитектурного уровня

> Источник анализа: `/home/ubuntu/apps/selfystudio/TODO/architecture-2026/`
> 4 .md в корне, 15 ADR (013–027), 12 plan-файлов, 7 package-spec, 4 refactoring-target.

---

## 1. Чего у них есть, а у нас — НЕТ

### 1.1. Анализ через **GitNexus knowledge graph**

Они начинают аудит с **готового graph-индекса**: 14 693 nodes / 23 337 edges / 232 Leiden clusters / **300 execution flows**. Каждое рассуждение опирается на:
- **fan-in/fan-out конкретного символа** (например, `session.ts` — **167 import sites**, **8 hot-spot commits в 90 дней**) — это объективная метрика «бога-объекта», у нас её нет.
- **execution flow** «from receive_webhook to refund» как connected path в графе, а не на наш ручной grep.
- **Leiden clusters** — автоматическое обнаружение функциональных границ.

Наш пайплайн использует только `grep`/`madge`/`knip`, поэтому на больших проектах **архитектурные риски остаются гипотезами**, а не доказанными метриками.

### 1.2. Анализ через **Serena LSP**

Они **проверяют ключевые символы LSP'ом**:
> «Serena LSP: проверены ключевые символы — `createGenerationWorker`, `handlePipelineFailure`, `requireCabinetSession`, `validateCloudPaymentsWebhook`, `imageGenerator`, `smartEditOrSend`».

Это даёт точную сигнатуру + body + все ссылки за O(1). Мы делаем `head -100` и догадываемся.

### 1.3. **Wiki RAG через QMD** (semantic search по докам)

Они напрямую цитируют:
> «wiki/* через QMD HTTP search: `wiki/architecture.md`, `wiki/decisions.md` (12 ADR), `wiki/gotchas.md`, `wiki/components/{config, types, bot, web, entities, features, app}.md`, `wiki/gaps.md`».

У нас нет шага «прочитать wiki целиком и найти existing ADR/gotcha/inv invariant». Из-за этого мы по аудиту **повторно нашли** уже задокументированные gotcha (worker shutdown seam, raw-body parser order) — а они их атрибутировали правильно.

### 1.4. **Hot-spot churn анализ** (Tornhill «Code as a Crime Scene»)

```
session.ts — 167 import sites + 8 commits в 90 дней
```

Это формула `churn × complexity`. Файл, в который часто коммитят И от которого многое зависит = главный кандидат на рефакторинг. Мы не используем `git log --since=90.days --name-only`. **Без этого мы не находим самые опасные места кодовой базы.**

### 1.5. **Книжная атрибуция** (annotated bibliography)

Каждый их finding ссылается на **конкретную книгу + главу**:
- «Anemic FSD — Khononov §3, Vernon IDDD §1-3, Evans §4-6»
- «Session as god-object — Tornhill §3,7; Ousterhout §4-5»
- «No domain events — Vernon IDDD §8; Hohpe/Woolf §7-10; Kleppmann §11»

Это переводит **«мне кажется»** в **«это известная anti-pattern, описанная X»**. Принципиально другой уровень доверия и переубеждения владельца.

### 1.6. **Trade-off matrix по 8 «ilities»** (Richards & Ford)

Они оценивают проект по **10 архитектурных характеристик**:

| Characteristic | Сейчас | Цель |
|---|---:|---:|
| Deployability | 8/10 | 10/10 |
| Reliability | 8/10 | 10/10 |
| Recoverability | 8/10 | 9/10 |
| Observability | 7/10 | 10/10 |
| Security | 9/10 | 10/10 |
| Modifiability | 7/10 | 10/10 |
| Testability | 7/10 | 10/10 |
| Performance | 8/10 | 9/10 |
| Scalability | 6/10 | 8/10 |
| Cost-efficiency | 8/10 | 9/10 |

Наша «оценка X/320» — это сумма случайных подграмм. Их матрица — это **canonical модель из Software Architecture Fundamentals 2e**.

### 1.7. **ADR + Plan + Package spec + Refactoring target** как 4 отдельных артефакта

Их аудит производит 4 типа документов:
- **ADR** — архитектурное решение, для wiki/decisions.md (что и почему).
- **Plan** — пошаговый execution-runbook (как именно делать).
- **Package spec** — описание нового npm-пакета (что должно быть внутри).
- **Refactoring target** — file-level таргет с fitness-function (какая метрика должна стать какой).

У нас всё свёрнуто в «промт #N» — это операционное действие, но не архитектурная единица.

### 1.8. **Fitness functions как код** (Building Evolutionary Architectures, Ford)

Каждое архитектурное решение у них имеет **исполняемый тест в CI**:
```ts
test('session.ts has fewer than 50 imports after migration', () => {
  const count = grepCount('@shared/middleware/session');
  expect(count).toBeLessThan(50);
});

test('domain layer has no infrastructure imports', () => {
  expect(staticAnalysis.imports('packages/selfystudio-domain'))
    .not.toContain('prisma' | 'grammy' | 'fastify' | 'bullmq');
});

test('no circular imports', () => {
  expect(madge.checkCircular({...})).toEqual([]);
});
```

У нас рекомендации — это «прозы». У них — **CI-gates, которые невозможно нарушить незаметно**.

### 1.9. **Cytometric criteria** (числовые цели)

Каждый refactoring-target имеет точный «before/after»:
- session.ts: 167 imports → <50.
- god-pages: 802 LOC → ≤300.
- 1129 named exports → 50 unused (≤10 после cleanup).

У нас «топ-10 файлов на рефакторинг» — без целевой метрики. Они: «это число должно стать вот этим».

### 1.10. **Phase 0 — Roadmap Hardening**

Они **сначала делают meta-фазу**: проверяют сам roadmap на consistency, naming, ESM/CJS соответствие, пропущенные ADR, route inventory. Только потом — «закрытие quick wins».

Мы выводим Final-Report и сразу прыгаем в исправления. Без проверки целостности рекомендаций.

### 1.11. **Domain layer / Use cases / Anti-corruption layer**

Они применяют **Clean Architecture (Martin)** + **DDD (Evans)**. Это даёт реальные категории:
- «Это repository, а не entity» (anemic).
- «Это use case, а не handler» (transaction script).
- «Это adapter, а не client» (нет ACL).

У нас фаза «Architecture» использует абстрактные «6 осей». Конкретно сказать «у тебя anemic entities» — мы не можем без DDD-словаря.

### 1.12. **Strategic vs Quick wins** разделение

Они разделяют:
- **Quick wins (1 неделя, 10 atomic commits)** — наши промты #1–#13.
- **Strategic (4–6 недель, новый пакет)** — `@selfystudio/domain`, `@selfystudio/events`, `@selfystudio/result`.

Наши промты — все «средние». Нет крупных стратегических. Владельцу не из чего выбрать roadmap на квартал.

### 1.13. **Annotated bibliography обязательна**

Перед стартом каждой фазы — **обязательно прочесть минимум 1 главу** из соответствующего раздела библиографии. Без этого PR отклоняется на review.

У нас «прочитайте нашу спеку и поехали». Никакого знания глубже наших правил.

### 1.14. **Specific findings по каждой dimension**

Их «Top 10» гораздо предметнее:
- «**5 fat clients** в `image-generation/providers/{laozhang,kie,vertex,vertex-fallback}-client.ts` — каждый со своей retry/error/format логикой».
- «**14 Prisma models, 36 SQL migrations, 232 clusters, 300 flows**».
- «686 import statements в `apps/bot`, 209 в `apps/web`».

У нас «архитектурный паттерн — FSD». Ну и что.

### 1.15. **Production-readiness pillars** (Susan Fowler)

Они проверяют по 8-ми pillars Production-Ready Microservices:
1. Stability, 2. Reliability, 3. Scalability, 4. Fault-tolerance, 5. Performance, 6. Monitoring, 7. Documentation, 8. Understandability.

У нас observability и security — отдельно. А «как живёт это в продакшене 24/7 на год» — нет.

### 1.16. **Ссылка на конкретные DORA-метрики и SLO**

> «Цели: DORA-4 metrics tracked, зелёные SLO, автоматизированная saga для money-flow.»

У нас «verdict warn». DORA (Deployment Frequency / Lead Time / MTTR / Change Failure Rate) и SLO — не упоминаются.

---

## 2. Что внести в `nodejs-audit/` чтобы догнать

### Добавить в каждую фазу

1. **MCP-first протокол**:
   - **Phase 1 (Recon)**: запросить `mcp__gitnexus__list_repos` → `mcp__gitnexus__context` → если есть индекс, **читать его**, не grep'ать.
   - **Phase 1 (Recon)**: `mcp__serena__activate_project` + `get_symbols_overview` для каждого entry-point.
   - **Phase 3 (Architecture)**: `mcp__gitnexus__query` + `route_map` + `tool_map` — execution flows как первичная метрика.
   - **Phase 3 (Architecture)**: `mcp__gitnexus__impact` для топ-10 «ключевых» символов (refund handler, session, image-generator) — **получить их fan-in/fan-out как число, а не оценку**.
   - **Phase 5 (Security)**: `mcp__serena__find_referencing_symbols` для `crypto.createHash`, `jwt.sign`, `axios.create` — точное число использований.
   - **Phase 8 (AI-readability)**: использовать `wiki/`-RAG если есть (`mcp__pipeline__search_memory` или Serena memories), не grep'ать docs.

2. **Hot-spot churn анализ** (Phase 3 или новая Phase 3.5):
   ```bash
   # топ-15 файлов по `churn × fan-in`
   git log --since=90.days --name-only --pretty=format: \
     | grep -E '\.(ts|tsx|vue)$' | sort | uniq -c | sort -rn | head -50 \
     > raw/hotspot-churn.log
   # пересечение с топом по fan-in (gitnexus_context)
   ```
   **Финальный артефакт:** `raw/hotspot-matrix.md` — таблица «файл / churn / fan-in / risk score».

3. **Trade-off matrix Richards & Ford** в Phase 9:
   - Заменить «X / 320» на 10 строк по characteristics.
   - Текущая оценка + цель + delta.

4. **DDD-словарь в Phase 3**:
   - Anemic vs rich domain — **проверить, есть ли у entities методы, не только types/queries**.
   - Aggregates / Value objects — **где формализуются invariants**.
   - Anti-corruption layer — **есть ли он на каждой external integration**.

5. **Книжная атрибуция в Phase 3, 4, 6, 7**:
   - В каждый finding добавить «cited from: **<book> §<chapter>**».
   - Заранее в шаблон AUDIT.md встроить таблицу books → topics.

6. **Fitness function для каждого промта**:
   - В FINAL-REPORT.md в каждом промте добавить блок «**Fitness test:**».
   - Пример: «после промта #1 выполнить `grep -rEn 'env.api.internalSecret' apps/bot/src/features/web-api` → должно быть 0».

7. **Cytometric criteria для refactoring**:
   - Каждый рефакторный промт обязан содержать «**Before metric:** ... → **After metric:** ...».

8. **Phase 0 — Roadmap Hardening (опционально)**:
   - Метафаза «проверь сам отчёт» — naming consistency между фазами, нет ли противоречий между Architecture и Security findings, route inventory.

9. **Annotated bibliography как `nodejs-audit/REFERENCES.md`**:
   - Список книг + главы + когда применять.
   - Phase 3 (Architecture) ссылается на Evans/Khononov/Tornhill.
   - Phase 4 (Readability) ссылается на Ousterhout.
   - Phase 5 (Security) — OWASP ASVS.
   - Phase 6 (Performance) — Kleppmann §7-11.
   - Phase 7 (Observability) — Majors.
   - Phase 8 (AI-readability) — Sandi Metz, Khorikov.

10. **Three-tier output вместо одного FINAL-REPORT.md**:
    ```
    reports/
      00..09 — phase reports (как сейчас)
      FINAL-REPORT.md — executive summary + scoreboard
      QUICK-WINS.md  — atomic-commit план на 1 неделю (P0 + P1)
      ADRS-DRAFTS/   — 3-5 черновиков ADR для wiki/decisions.md
      REFACTORING/   — file-level targets с fitness functions
    ```

### Конкретные правки в `nodejs-audit/AUDIT.md`

#### Phase 1 (Recon) — добавить:

```markdown
### Шаг 1.0: Спросить MCP knowledge graph (если есть)

Если запущены MCP-серверы:
- `mcp__gitnexus__list_repos` — есть ли репо в индексе?
- если да: `mcp__gitnexus__context` для shape (clusters, flows, hot-paths).
- `mcp__serena__activate_project` — запустить LSP для точной навигации.
- `mcp__pipeline__search_memory` (если у проекта есть `wiki/` или память пайплайна) — заранее знать ADR/gotchas.

Если MCP недоступен — skip и работай через grep, отметь в errors.log.
```

#### Phase 3 (Architecture) — заменить «6 осей» на:

```markdown
**Сначала — quantitative анализ через MCP/git:**

1. **Hot-spot матрица** — `git log --since=90.days --name-only --pretty=format:`
   пересечь с fan-in из `mcp__gitnexus__impact` для top-50 файлов.
2. **Execution flows** — `mcp__gitnexus__route_map` дает реальные пути запросов.
3. **Boundary leaks** — `mcp__gitnexus__shape_check` для слоёв FSD/Clean.

**Потом — DDD-классификация:**
1. Anemic vs rich domain (Khononov §3, Evans §6).
2. Aggregates с invariants — где живут бизнес-правила?
3. Anti-corruption layer — для каждой external integration.

**Потом — Trade-off matrix Richards & Ford** (10 ilities).

**Только потом — 6 «осей» как сейчас.**
```

#### Phase 9 (Final) — добавить:

```markdown
### Дополнительные артефакты (наряду с FINAL-REPORT.md):

1. **`reports/QUICK-WINS.md`** — atomic-commit план для P0 (3 проблемы за день) и P1 (7 проблем за неделю).
2. **`reports/REFACTORING/<target>.md`** для каждого рефакторного таргета, формат:
   ```
   # Refactoring target: <path>
   ## Current state
   - LOC: N · imports: M · churn: K commits/90d
   ## Smell
   ## Decomposition target
   ## Cytometric criteria (fitness test)
   ## Migration plan
   ## References (book + chapter)
   ```
3. **`reports/ADR-DRAFTS/ADR-XXX.md`** для каждой архитектурной находки с trade-off matrix.
4. **`reports/REFERENCES.md`** — какие книги/паттерны цитируются.
```

---

## 3. Что у нас уже сильнее их

Чтобы не было однобоко:

1. **Полностью автономный single-prompt** запуск — у них multi-prompt сессии.
2. **Verifiable scores 0-10** на 11 dimensions — они дают только subjective trade-off matrix.
3. **`_meta.json`** для CI gating — у них только markdown.
4. **Деперсонифицированный OWASP-проход** — у них security «попутно».
5. **`npx --yes`** инструменты без mutate package.json — они полагаются на готовый dev environment.
6. **«No mock» policy для readiness probe** — мы дёргаем реальные `npm test` и реальный `tsc`. Они только реферируют.
7. **Один час на полный аудит** — у них multi-day работа.

Наши `_meta.json` + autonomous execution + repeatability = **operational аудит**. Их = **architectural консалтинг**. Цель — соединить.

---

## 4. Минимальный набор изменений (приоритет)

| Приоритет | Что | Где | Усилие |
|---|---|---|---|
| **P0** | Phase 1 — добавить MCP-first шаг (gitnexus + serena context) | AUDIT.md §Фаза 1 | 30 мин |
| **P0** | Phase 3 — добавить hot-spot churn × fan-in матрицу | AUDIT.md §Фаза 3 | 30 мин |
| **P0** | Phase 9 — Trade-off matrix Richards & Ford | AUDIT.md §Фаза 9 | 20 мин |
| **P1** | `nodejs-audit/REFERENCES.md` — annotated bibliography | новый файл | 1-2 ч |
| **P1** | Шаблон `reports/REFACTORING/<target>.md` | AUDIT.md + templates/ | 30 мин |
| **P1** | Шаблон `reports/QUICK-WINS.md` для P0/P1 split | AUDIT.md + templates/ | 30 мин |
| **P2** | Phase 3 — DDD-словарь (anemic, aggregates, ACL) | AUDIT.md §Фаза 3 | 30 мин |
| **P2** | Phase 5 — добавить OWASP ASVS чек-листы как ссылку | AUDIT.md §Фаза 5 | 15 мин |
| **P2** | Phase 9 — генерация ADR-DRAFTS для top-3 архитектурных находок | AUDIT.md §Фаза 9 | 40 мин |
| **P3** | `MASTER_PROMPT.md` — Stage 0.5 «опросить MCP» | MASTER_PROMPT.md | 15 мин |
| **P3** | Fitness-test секция в каждом промте FINAL-REPORT | AUDIT.md шаблон фазы 9 | 30 мин |

---

## 5. План внедрения

### Шаг 1 — обновить `MASTER_PROMPT.md`

Добавить **Stage 0.5 — MCP probe** между Stage 0 (Bootstrap) и Stage 1 (фазы). Если MCP-серверы доступны — выполнить `gitnexus list_repos`, `gitnexus context`, `serena activate_project`. Сохранить ответы в `reports/raw/mcp-context.json`.

### Шаг 2 — обновить `AUDIT.md`

В каждую фазу добавить «MCP-first probe» в начало. Полную замену делать постепенно (не сломать текущий single-prompt контракт).

### Шаг 3 — добавить `REFERENCES.md`

Аннотированная библиография 15 книг + ссылки на главы для каждой фазы.

### Шаг 4 — добавить шаблоны `templates/refactoring-target.md`, `templates/quick-wins.md`, `templates/adr-draft.md`

Phase 9 пользуется ими автоматически.

### Шаг 5 — поднять «total max» с 320 до сбалансированного значения и заменить на trade-off matrix

В `_meta.json` добавить новое поле `architecture_characteristics: { deployability: 8, reliability: 8, ... }`. Старое `total/max_total` остаётся для обратной совместимости.

---

## 6. Что копировать дословно из их аудита

1. Список **15 книг** из их `references.md` — это идеальная база.
2. **Trade-off matrix формат** (10 строк, current → target) — портировать в FINAL-REPORT.md.
3. **Refactoring-target** структура (4 файла в `refactoring/`) — портировать как шаблон.
4. **ADR + Plan + Package spec разделение** — взять как принцип.
5. **Phase 0 Roadmap Hardening** — взять как опциональный финальный валидатор аудита.
6. **Hot-spot формула** churn × fan-in — добавить как первый sanity-check в Phase 3.

---

## TL;DR (одно предложение)

Их аудит силён тем, что **опирается на graph-знания (gitnexus), LSP (serena), wiki-RAG (qmd), книжные паттерны (15 книг) и executable fitness-functions** — наш сейчас опирается только на grep + npx-tools. Достаточно добавить **MCP-first probe в Phase 1, hot-spot churn в Phase 3, Richards-Ford trade-off matrix в Phase 9 и аннотированную bibliography как `REFERENCES.md`** — это даст 80% разрыва за 4–6 часов работы.
