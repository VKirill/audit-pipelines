# PHASE 02 — ARCHITECTURE (v2)

**Цель:** Понять структурную организацию системы и найти архитектурные дефекты.

**Источники:**
- Ousterhout, *A Philosophy of Software Design* 2e — глубина/простота модулей, leaks abstraction, information hiding.
- Parnas (1972) *On the Criteria To Be Used in Decomposing Systems into Modules* — information hiding.
- Evans, *Domain-Driven Design* — bounded contexts, язык домена.
- Fowler, *Patterns of Enterprise Application Architecture* — layering.
- Martin, *Clean Architecture* — dependency rule.

**Exit gate этой фазы:**
- ≥ 5 findings для M-проекта (или обоснование в разделе «Проверено и чисто»);
- минимум 2 файла в `audit/evidence/02_architecture/`;
- построена матрица cluster×cluster (через cypher ИЛИ через grep-fallback);
- проведён deep/shallow анализ для ≥ 10 центральных символов;
- ≥ 150 строк в отчёте.

---

## 1. Входы
- `audit/01_inventory.md`, `.serena/memories/audit_phase_01`.
- GitNexus index (критичный для этой фазы).
- Схема графа (из `gitnexus://repo/{name}/schema`).

---

## 2. Чек-лист действий

### 2.1. Матрица межкластерных зависимостей (ОБЯЗАТЕЛЬНО — главный артефакт)

**Путь А (основной, через GitNexus):**

- [ ] Прочитай `gitnexus://repo/{name}/schema`. **Зафиксируй фактические имена типов nodes и edges.** Примеры ниже могут не совпадать с твоей схемой — адаптируй.
- [ ] Попробуй запрос на актуальных именах:
  ```cypher
  MATCH (a)-[r:CodeRelation {type: 'IMPORTS'}]->(b)
  MATCH (a)-[:CodeRelation {type: 'MEMBER_OF'}]->(ca:Community)
  MATCH (b)-[:CodeRelation {type: 'MEMBER_OF'}]->(cb:Community)
  WHERE ca.heuristicLabel <> cb.heuristicLabel
  RETURN ca.heuristicLabel AS from_cluster,
         cb.heuristicLabel AS to_cluster,
         count(*) AS edges
  ORDER BY edges DESC
  ```
- [ ] **Если запрос возвращает пусто — не сдавайся.** Попробуй:
  - Упрощённый запрос: `MATCH (a)-[r]->(b) RETURN type(r), count(*) LIMIT 20` — чтобы увидеть, какие отношения вообще есть.
  - Запрос без community: `MATCH ()-[r {type: 'IMPORTS'}]->() RETURN count(*)` — есть ли вообще IMPORTS.
  - Изменения названий: `File` vs `Module`, `Community` vs `Cluster`, `filePath` vs `path`.

**Путь Б (fallback, если GitNexus не даёт матрицу):**

Обязательно выполнить, не оставлять пустым.

- [ ] Построй матрицу по импортам руками:
  ```bash
  # Для JS/TS monorepo
  grep -rhE "^(import|from) ['\"]([^'\"]+)['\"]" --include="*.ts" --include="*.tsx" --include="*.js" \
    apps/ packages/ src/ 2>/dev/null | \
    grep -oE "['\"]\./[^'\"]+|['\"][^.][^'\"]+['\"]" | \
    sort | uniq -c | sort -rn | head -50
  ```
- [ ] Для M-проекта: определи «папки верхнего уровня» как cluster (например `apps/bot/src/features/*`, `apps/bot/src/shared/*`, `apps/web/server/*`). Построй таблицу `from_folder → to_folder → import_count` ручным анализом.
- [ ] Python-аналог:
  ```bash
  grep -rhE "^(from|import) " --include="*.py" <src> | \
    awk '{print $2}' | sort | uniq -c | sort -rn | head -50
  ```

**Результат фиксируй в `audit/evidence/02_architecture/cluster_matrix.md`** как markdown-таблицу. Без этого файла фаза не считается завершённой.

- [ ] На основе матрицы построй Mermaid-диаграмму (топ-N рёбер, иначе нечитаемо). **Сохрани в `audit/evidence/02_architecture/cluster_graph.mmd`**.
- [ ] Ищи **циклы между кластерами**: если `A → B` и `B → A` с существенным весом — зафиксируй finding `high`.
- [ ] Ищи **god-кластер**: суммарный in+out >> среднего (вероятно нарушены границы) → finding.

### 2.2. Deep vs shallow modules — Ousterhout §4 (ОБЯЗАТЕЛЬНО)

Для топ-15 «центральных» символов (максимальный upstream impact):

**Через GitNexus:**
- [ ] Получи топ-30 символов по in-degree:
  ```cypher
  MATCH (fn)<-[r:CodeRelation {type: 'CALLS'}]-()
  RETURN fn.name, fn.filePath, count(r) AS incoming
  ORDER BY incoming DESC
  LIMIT 30
  ```

**Через grep-fallback** (если GitNexus не даёт):
- [ ] Из топ-20 больших файлов (фаза 01) + центральные папки — выбери топ-30 функций/классов вручную:
  ```bash
  # Найти функции/классы и их использования
  for sym in getTranslation createLogger queryOne ...; do
    count=$(grep -rh "\b$sym\b" --include="*.ts" --include="*.tsx" . | wc -l)
    echo "$count $sym"
  done | sort -rn | head -30
  ```

**Для каждого из топ-15 выполни deep/shallow анализ:**
- [ ] Прочитай файл с определением символа (или получи `find_symbol include_body=true`).
- [ ] Посчитай:
  - **API-size:** число exported members / параметров / публичных методов.
  - **Impl-size:** LOC реализации / число приватных методов / сложность.
- [ ] Классифицируй:
  - **Deep** (хорошо): маленький API, большая реализация — абстракция скрывает сложность.
  - **Shallow** (плохо): большой API, маленькая реализация — шум.
  - **Classifier/God** (плохо): большой API + большая реализация — делает слишком много.
- [ ] Запиши в **`audit/evidence/02_architecture/central_symbols.md`** таблицу:
  | символ | файл | API-size | impl-LOC | callers | классификация | комментарий |
  |--------|------|----------|----------|---------|---------------|-------------|
- [ ] **Для каждого shallow/god символа → finding.** Severity = `medium` или `high` в зависимости от числа вызывающих (blast radius).

### 2.3. Слоистость и dependency rule (Martin, Fowler PoEAA)

- [ ] Определи предполагаемые слои по именам кластеров/папок. Типичные варианты:
  - `controllers/api` → `services/domain` → `repositories/infrastructure` → `entities`
  - FSD: `app → processes → pages → widgets → features → entities → shared`
  - Hexagonal: `domain → application → adapters`
- [ ] Через cypher/grep проверь направление зависимостей:
  - Domain не должен импортировать Infrastructure.
  - Domain не должен импортировать Controllers.
  - Entities не должны импортировать Services.
  - В FSD: нижние слои не должны импортировать из верхних.
- [ ] Подсчитай **количество нарушений** и **список конкретных файлов**. Запиши в evidence.
- [ ] Каждое массовое нарушение → finding (`high` если их > 10, `medium` если единичные).
- [ ] Если слои не выделены вообще (всё в одной плоской структуре) — finding `medium` для крупных проектов, `low` для S/XS.

### 2.4. Ядро и интеграторы

- [ ] Cypher/grep: топ-30 символов по in-degree (ядро).
- [ ] Cypher/grep: топ-30 символов по out-degree (интеграторы — связывают многое).
- [ ] Пересечение — **критические узлы**. Для каждого — finding `info` с пометкой для фаз 04 (quality), 07 (tests), 09 (performance).

### 2.5. Cross-cutting concerns (ОБЯЗАТЕЛЬНО — отдельная секция в отчёте)

- [ ] `search_for_pattern` / `grep` по маркерам:
  - logging: `logger\.|log\.|Logger|logging\.`
  - caching: `@cache|@lru_cache|Redis|Memcach|cache\.(get|set)`
  - auth: `@require_auth|@authenticate|IsAuthenticated|Authorize`
  - retry: `@retry|retryable|Polly|resilience`
  - transactions: `@transactional|BEGIN TRANSACTION|db\.transaction`
  - metrics: `metrics\.|prometheus|statsd|opentelemetry`
- [ ] Для каждого concern заполни таблицу:

  | Concern | Количество файлов | Централизован? | Где обёртка (если есть) |
  |---------|-------------------|----------------|-------------------------|
  | logging | N                 | yes/no/partial | `shared/lib/logger`     |
  | ...     |                   |                |                         |

- [ ] Если разбросан по десяткам файлов без обёртки — finding `medium` (suggest: middleware/decorator/aspect).

### 2.6. Bounded contexts (DDD lens)

Только если проект — backend-бизнес-система:
- [ ] Сопоставь кластеры с бизнес-доменами (по именам моделей, роутов).
- [ ] Если модель с одним именем существует в разных частях графа с разными полями/методами — два разных концепта под одним именем. Finding.
- [ ] Если один кластер объединяет несколько бизнес-доменов → finding `medium`.

### 2.7. ADR-совместимость

- [ ] Если в `docs/adr/` / `wiki/decisions.md` есть ADR — прочитай ключевые (accepted), извлеки архитектурные решения.
- [ ] Проверь через cypher/search, соблюдаются ли. Расхождение → finding.

### 2.8. Entry points vs реальное использование

- [ ] Для каждой точки входа из фазы 01: `gitnexus://repo/{name}/process/{name}` — глубина, число шагов, кластеры.
- [ ] Точка входа, которая не ведёт в бизнесовые кластеры — потенциально dead entry (finding `low`).

---

## 3. Красные флаги (сразу — findings)

| Сигнал | Severity |
|--------|----------|
| Цикл между двумя кластерами (с существенным весом рёбер) | high |
| > 60% всех IMPORTS-рёбер в одном гигантском кластере | high (big ball of mud) |
| Domain-кластер импортирует infrastructure-кластер | high |
| > 3 shallow modules среди топ-15 центральных | medium–high |
| Logging/auth/transactions разбросаны по > 20 файлам без обёртки | medium |
| Один бизнес-домен разнесён по > 3 несоседних кластерам | medium |
| Публичный API есть, но OpenAPI/Swagger отсутствует | medium |
| ADR принят, но код систематически нарушает | high |

---

## 4. Quota check перед завершением

- [ ] **≥ 5 findings** для M-проекта. Если меньше — вернись к deep/shallow анализу и cross-cutting concerns, почти всегда там есть что сказать.
- [ ] **Минимум 2 файла в evidence/02_architecture/**: `cluster_matrix.md` + `central_symbols.md` — обязательны. Mermaid-диаграмма — плюс.
- [ ] **Разумное распределение confidence** (см. orchestrator §4.2).

---

## 5. Артефакт — `audit/02_architecture.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено** (чек-лист с отметками)
3. **Ключевые наблюдения**
   - **Кластеры** — таблица + Mermaid-диаграмма зависимостей (только если рёбер ≤ 30).
   - **Dependency matrix** — таблица cluster×cluster с числом импортов (отсылка к evidence).
   - **Deep vs shallow** — таблица топ-15 центральных с классификацией.
   - **Слоистость** — схема фактическая vs идеальная; нарушения с цифрами.
   - **Ядро системы** — топ-10 критичных узлов.
   - **Cross-cutting concerns** — таблица.
   - **Bounded contexts** (если применимо).
   - **ADR-совместимость** (если применимо).
4. **Находки этой фазы** (обычно 5–20)
5. **Неполные проверки** (что не удалось даже с fallback)
6. **Контрольные вопросы**
   - **Q1.** Можешь ли ты на одном листе нарисовать эту систему так, чтобы через неделю сам понимал рисунок? Если нет — структура слишком размыта, это само по себе — finding.
   - **Q2.** Если в эту команду придёт новый старший разработчик, какие 3 вопроса он задаст первым? Сможешь ли ты на них ответить из собранной карты?
7. **Следующая фаза:** `phases/phase_03_dependencies.md`

---

## 6. Memory

`.serena/memories/audit_phase_02`:

```markdown
# Phase 02 memory
Completed: YYYY-MM-DD

Architecture summary:
- style: <layered/hexagonal/FSD/monolith/microservices-ish/ball-of-mud/unknown>
- clusters_count: <N>
- matrix_build_path: <cypher/grep-fallback>
- cycles_between_clusters: <bool + list>
- layering_violations: <count>
- shallow_modules: [<list>]
- central_symbols: [<top-5>]
- cross_cutting_centralized: {logging: yes/no, auth: yes/no, ...}

Major architectural findings: F-XXXX..F-YYYY

Implications for next phases:
- phase_04: обратить внимание на <shallow modules> и <god classes>
- phase_07: покрытие тестами для <central_symbols> критично
- phase_09: performance hotspots вероятно в <list>

Next phase: phase_03_dependencies.md
```

Обнови `audit_progress`.

---

## 7. Отчёт пользователю

> Фаза 2/10 завершена. Архитектура: <стиль>, <N> кластеров, <X> циклов между кластерами, <Y> нарушений слоистости, <Z> shallow modules в ядре. Матрица построена через <cypher/grep-fallback>. Добавлено <N> findings (<critical_count> critical, <high_count> high, <medium_count> medium). Перехожу к фазе 3 — зависимости и supply chain.

Перейди к `phases/phase_03_dependencies.md`.
