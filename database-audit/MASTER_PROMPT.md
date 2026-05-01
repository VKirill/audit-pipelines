# Master Prompt — Autonomous Database Audit

> **Single prompt, single argument.** Пользователь даёт путь к проекту → ИИ выполняет ВЕСЬ пайплайн без дополнительных команд.

---

## Как использовать (для пользователя)

В Claude Code запусти **одной командой**:

```
Прочитай /home/ubuntu/projects/audit-pipelines/database-audit/MASTER_PROMPT.md
и выполни полный аудит проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

**От пользователя — ТОЛЬКО путь к проекту.** Всё остальное ИИ определяет сам:

- ✅ **Mode auto-detect** (static vs live) — через попытку найти DSN в проекте
- ✅ **DATABASE_URL discovery** — через MCP/env/config files (см. Stage 0.5)
- ✅ **Pipeline install** в проект
- ✅ **GitNexus indexing** через MCP
- ✅ **Chunked discovery** (9 sub-prompts через Serena+GitNexus MCP)
- ✅ **Manifest creation + validation**
- ✅ **Все 14 фаз** + auto-fill phase 11 + calibration phase 10a
- ✅ **Финальный отчёт** одним сообщением

---

## Контракт автономности

**Ты — ИИ-агент с правами read-only на проект и (опционально) live-DB.**

### Что разрешено

- Читать любые файлы в `$PROJECT_PATH` (включая .env*, config/*, settings.py)
- Запускать read-only SQL через MCP postgres (если доступен) ИЛИ через `$DATABASE_URL` (только если read-only role verified)
- Использовать MCP-инструменты:
  - **Serena**: find_symbol / find_referencing_symbols / search_for_pattern / write_memory
  - **GitNexus**: query / context / impact / cypher / route_map
  - **postgres** (если доступен): pg_query (read-only) / pg_list_databases / pg_describe_table — для DSN-free live mode
- Использовать `gitnexus analyze` для индексации
- Создавать/изменять только файлы внутри `$PROJECT_PATH/database-audit/` (pipeline + runtime)
- Запускать `bash database-audit/init.sh`, `run.sh`, `validators/*.{sh,py}`

### Что запрещено

- Писать в БД (никаких `INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE`)
- Менять код проекта вне `database-audit/`
- Останавливаться без финального отчёта пользователю
- Оставлять `_agent fills_` placeholders в phase 11
- Оставлять template-only `_adversary_review.md`
- Пропускать `validate_phase.sh NN` exit 0 проверки

---

## Пошаговый план (твой авто-runbook)

### Stage 0 — Bootstrap

```bash
cd "$PROJECT_PATH"

# 0.1 Установить pipeline в проект
if [ ! -d "database-audit" ]; then
    cp -r /home/ubuntu/projects/audit-pipelines/database-audit ./
    echo "✅ Pipeline installed"
fi

# 0.2 Проверить зависимости
python3 -c "import yaml, jsonschema" || pip install -r database-audit/requirements.txt
```

### Stage 0.5 — DSN/mode auto-detection

> **Цель:** определить может ли быть запущен `live mode` без интерактивности от пользователя.

#### 0.5.1 — Проверка MCP postgres (предпочтительный способ)

```python
# Если в Claude Code доступен MCP server "postgres" — используй его
# вместо прямого DATABASE_URL. Это безопаснее (read-only enforced на MCP уровне).

# Псевдокод:
mcp_servers = check_available_mcp_servers()  # gitnexus, serena, postgres, ...
if 'postgres' in mcp_servers:
    databases = mcp_postgres.pg_list_databases()
    # Найти БД проекта по имени из package.json/composer.json/etc
    project_db = guess_project_db(databases, project_name=basename(PROJECT_PATH))
    if project_db:
        mode = 'live'
        connection_method = 'mcp-postgres'
        # Здесь pg_query будет использоваться напрямую через MCP
```

#### 0.5.2 — Поиск DSN в env-файлах проекта

Если MCP postgres недоступен или не находит проектную БД:

```bash
# Сканируй env файлы (в priority order)
for env_file in     "$PROJECT_PATH/.env"     "$PROJECT_PATH/.env.local"     "$PROJECT_PATH/.env.development"     "$PROJECT_PATH/apps/*/.env"     "$PROJECT_PATH/packages/*/.env"; do
    if [ -f "$env_file" ]; then
        # Найди DATABASE_URL, DB_URL, POSTGRES_URL, PG_CONNECTION etc
        DSN=$(grep -E '^(DATABASE_URL|DB_URL|POSTGRES_URL|PG_URL|MONGO_URL|MYSQL_URL)=' "$env_file" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
        if [ -n "$DSN" ]; then
            echo "Found DSN in $env_file"
            break
        fi
    fi
done
```

#### 0.5.3 — Поиск DSN в config files

```bash
# config/database.yml (Rails)
# config/database.json (Node)
# settings.py (Django) — DATABASES dict
# application.yml (Spring)
# Через Serena search_for_pattern
serena.search_for_pattern(
    substring_pattern=r'(DATABASE_URL|connectionString|datasource\.url|DATABASES\s*=)',
    glob='**/config/**/*.{yml,yaml,json,py}',
    paths_include=[PROJECT_PATH]
)
```

#### 0.5.4 — Безопасность: read-only verification ОБЯЗАТЕЛЬНО

Если DSN найден → **перед** использованием в live mode:

```bash
# 1. Проверь default_transaction_read_only
psql "$DSN" -t -c "SELECT current_user, current_setting('default_transaction_read_only')"

# 2. Если current_user имеет write права — НЕ использовать live mode
# 3. Если есть отдельная audit_ro роль — переключись на неё
# 4. Иначе → mode = static, помечай в _known_unknowns.md
```

**Решение mode (decision matrix):**

| Условие | mode | source |
|---|---|---|
| MCP postgres доступен + проектная БД найдена | `live` | mcp-postgres |
| DSN найден в env + read-only role verified | `live` | env-file |
| DSN найден, но write-allowed user | `static` | + warn в `_known_unknowns.md` |
| DSN не найден | `static` | + note «consider live mode for invariant checks» |
| Несколько DSN (production + staging) | `live` для staging only, не production | env-priority |

#### 0.5.5 — Сообщи пользователю auto-detected mode

В первом ответе после bootstrap:

```
🔍 Auto-detected:
- mode: <static | live>
- source: <mcp-postgres | env-file:.env.local | none>
- read_only_role: <verified | not-verified | n/a>

[Если live] Запускаю live drift verification + EXPLAIN на топ-30 запросов.
[Если static] Запускаю static analysis. Live invariant checks помечены в _known_unknowns.

Продолжаю автоматически. Если хочешь принудительно static-mode — прерви и запусти повторно с `mode=static` в команде.
```

Это **single user-facing checkpoint**. После него — без интерактивности до финального report.

#### 0.5.6 — Run init.sh

```bash
bash database-audit/init.sh
# init.sh теперь видит mode из 0.5 и записывает в _staging/init.md
```

### Stage 1 — GitNexus indexing (auto, 1-5 минут)

**Это критический шаг для phase 11 deep_dive auto-fill.** Без него секции trace и blast radius будут пустыми.

```bash
PROJECT_NAME=$(basename "$PROJECT_PATH")

# Check if indexed
if ! gitnexus list 2>/dev/null | grep -q "$PROJECT_NAME"; then
    echo "🔧 GitNexus index missing — analyzing..."
    npx gitnexus analyze --embeddings 2>&1 | tail -10
else
    # Check freshness
    if gitnexus status 2>&1 | grep -qi "stale\|outdated"; then
        echo "🔧 GitNexus index stale — re-analyzing..."
        npx gitnexus analyze --embeddings 2>&1 | tail -10
    fi
fi
```

После этого `gitnexus.context`, `gitnexus.impact`, `gitnexus.cypher` будут возвращать реальные данные.

### Stage 2 — Discovery (autonomous chunked)

Прочитай и выполни **в указанном порядке**:

```
1. database-audit/prompts/00_discover.md       — orchestrator (skeleton: stack/paths/size)
2. database-audit/prompts/00a_discover_money.md           — money columns + endpoints
3. database-audit/prompts/00b_discover_transactions.md    — race candidates
4. database-audit/prompts/00c_discover_pii.md             — PII + secrets
5. database-audit/prompts/00d_discover_n_plus_one.md      — N+1 vetting
6. database-audit/prompts/00e_discover_migrations.md      — migrations + DDL
7. database-audit/prompts/00f_discover_serena_deep.md     — Serena LSP deep
8. database-audit/prompts/00g_discover_gitnexus_graph.md  — GitNexus cypher (7 queries)
9. database-audit/prompts/00z_validate_manifest.md        — self-validation gate
```

**Особое внимание:**

#### 2a. Live drift verification (если `mode: live`)

После 00b transactions — для каждой `money_columns` пары `(denormalized, source_aggregation)` запусти:

```sql
-- Пример для balanceRub vs sum(remainingRub)
SELECT p.id, p.name,
       p."balanceRub" AS denormalized,
       COALESCE(t.computed, 0) AS computed,
       p."balanceRub" - COALESCE(t.computed, 0) AS drift
FROM content_projects p
LEFT JOIN (
  SELECT "projectId", SUM("remainingRub") AS computed
  FROM content_balance_topups GROUP BY "projectId"
) t ON t."projectId" = p.id
WHERE ABS(p."balanceRub" - COALESCE(t.computed, 0)) > 0.01;
```

Если drift найден — **сразу** добавь `DB-LIVE-NNN` finding с severity `critical` + `confidence: high` (это **факт**, не теория).

#### 2b. Route map cross-reference (новое)

После 00g — для каждого endpoint из `gitnexus.route_map`:

```cypher
MATCH (h:Handler {path: '$endpoint_path'})-[:CALLS*1..5]->(q:Function)
WHERE q.body =~ '(?i).*select.*'
RETURN q.body
```

Если endpoint **возвращает** PII колонки (matched against `hints.pii_candidates`) и **нет audit log** call → finding `DB-PII-NNN [high]`.

### Stage 3 — Manifest review autonomous

После всех discover-промтов:

```bash
python3 database-audit/validators/validate_manifest.py \
  database-audit/manifest.yml --strict
```

**Если `--strict` fails:** прочитай ошибки, исправь manifest, повтори.

**Если все OK** — продолжай. **Не запрашивай review у пользователя** — это автономный режим.

### Stage 4 — Run all phases

```bash
bash database-audit/run.sh all
```

**После каждой фазы** — `validate_phase.sh NN`. Если fail:
1. Прочитай stderr
2. Если quota не пройдена — добавь findings вручную (только если они реально есть в коде)
3. Если evidence missing — заполни через Serena/GitNexus
4. Если `_agent fills_` в phase 11 — заполни Section 4 (Fix variants A/B/C), 5 (Test), 6 (Next step)
5. Повтори validate

**Не двигайся к следующей фазе пока gate не exit 0.**

### Stage 5 — Phase 11 enrichment (новое — обязательное)

После того как `deep_dive.py` создал skeleton, **для каждого critical finding** заполни:

#### Section 1 — Trace
Если GitNexus вернул context — используй его. Иначе:
- Найти `gitnexus.context <symbol>` в evidence
- Если пусто — `serena.find_referencing_symbols(symbol)` + ручной анализ
- Заполнить: entry points (routes), code path, affected DB objects

#### Section 2 — Exploit reproduction
- Раскрыть `finding.exploit_proof` в step-by-step сценарий
- Если live mode — ссылка на конкретные данные (как в DB-LIVE-001 на vechkasov)

#### Section 3 — Blast radius
- `gitnexus.impact <symbol> --direction upstream --depth 3`
- Перечислить routes/cron/workers, которые доходят до этой функции
- Оценить: сколько строк в БД может быть compromised, можно ли откатить

#### Section 4 — Fix variants (КРИТИЧНО — реальные snippets)

Для каждого critical — **3 варианта** с конкретным кодом:

```markdown
**Variant A (quick mitigation, effort: S):**
SQL fix или config change:
```sql
-- Concrete SQL here
```

**Variant B (proper fix, effort: M):**
Code change с pseudocode:
```typescript
// Before
await prisma.balance.update({ where: { id }, data: { amount: newAmount } });
// After
await prisma.$transaction(async (tx) => {
  await tx.$executeRaw`SELECT pg_advisory_xact_lock(${projectIdHash})`;
  await tx.balance.update({ where: { id }, data: { amount: newAmount } });
});
```

**Variant C (architectural, effort: L-XL):**
Описать архитектурный rewrite (e.g. "Удалить denormalization, single source of truth")
```

#### Section 5 — Test strategy
- Конкретный regression test
- Property-based test (если применимо)
- Production monitoring (alert query)

#### Section 6 — Recommended next step
- Какой Variant начать первым и почему
- Timeline (15 мин / неделя / квартал)

### Stage 6 — Phase 10a adversary review (новое — обязательное)

`adversary_review.py` создаёт draft. Дополни **обязательными** секциями:

```markdown
## Severity calibration

### Inflation (понижено severity)

- DB-MONEY-XXX (`costUsd` для AI tokens) → `business_critical=false` → medium
- DB-PERF-XXX → live SHOW max_connections подтвердил false alarm → medium

### Confirmed (severity осталась)

- DB-TX-XXX → live drift confirms

### Deflation (повышено severity)

- DB-LIVE-XXX → live данные превратили теорию в факт

## Confidence distribution

Total: 161, high: 99 (61%), medium: 62 (39%)

**Calibration justification:** ...
(если high >50% — обязательно явное обоснование)

## Systematic risks of this audit

1. ...
2. ...
3. ...
```

### Stage 7 — Finalize

```bash
bash database-audit/validators/finalize.sh
```

Должен exit 0. Если нет — прочитай ошибки, исправь, повтори.

### Stage 8 — Report пользователю

Сформируй финальный отчёт **одним сообщением** в формате:

```markdown
# 🗄️ Database Audit Report — <project_name>

**Verdict:** `<pass | pass-with-conditions | fail>`
**Mode:** <static | live>
**Findings:** <total> (critical: N, high: M, medium: K, low: L)

## 🔴 Top 5 critical (нужно срочно)

1. **DB-LIVE-001** — <title>
   `<file>:<lines>` — <одна строка impact>
   Fix: <Variant A inline command>

2. ...

## 📊 Categories
| Category | Count |
|---|---|
| security (SQLi, auth) | N |
| money | M |
| ...

## 📁 Output files
- `database-audit/results/ROADMAP.md` — приоритизированный roadmap
- `database-audit/results/11_deep_dive.md` — детальный разбор critical
- `database-audit/results/_adversary_review.md` — bias check
- `database-audit/results/_meta.json` — машинная сводка

## ⚡ Что делать сейчас (15 минут)

[Variant A для самого срочного critical — конкретная команда]

## ⏰ Что за неделю

[Variant B для top-3 critical]

## 🎯 Что за квартал

[Variant C — architectural improvements]
```

---

## Anti-patterns (что НЕ делать)

❌ Останавливаться и спрашивать пользователя «что дальше?»
❌ Оставлять manifest неполным («допилишь руками потом»)
❌ Пропускать validate_phase.sh exit 0 проверки
❌ Оставлять `_agent fills_` или `_To be filled by agent_` в любом артефакте
❌ Использовать только Serena без GitNexus или наоборот
❌ Пропускать Stage 1 (GitNexus indexing) — иначе deep_dive Section 1/3 пусты
❌ Запускать аудит без read-only role check в live mode
❌ Включать findings без `confidence_rationale ≥ 40` для high
❌ Включать `severity: critical` без `exploit_proof ≥ 40`

---

## Fallback protocols

### Если Serena недоступна
- Use ripgrep + Read tool
- Помечай в `_known_unknowns.md`: «Serena degraded»
- Не понижай качество анализа

### Если GitNexus недоступен / cypher возвращает пусто
- Use ripgrep + manual call-chain analysis
- Phase 11 Section 1/3 заполняй ручно через `find_referencing_symbols` + чтение тел
- Помечай в `_known_unknowns.md`

### Если live DB unavailable
- Mode = static
- Все findings требующие EXPLAIN → `confidence: medium` максимум
- Помечай `_known_unknowns.md`: «N findings need live verification»

### Если manifest validation fails after 3 attempts
- Сообщи пользователю с конкретной ошибкой
- Запроси его review текущего manifest
- Не продолжай вслепую

---

## Reporting checkpoint frequency

После каждой фазы — **одна строка** статуса в чате:

```
✅ Phase 02 (schema): 14 findings, validate exit 0, evidence written
✅ Phase 03 (indexes): 30 findings, top FK without index — content_balance_topups.projectId
🔄 Phase 04 (queries): in progress, 156 N+1 candidates triaged
```

После phase 11 finalize — **полный отчёт** (Stage 8).

---

## Time budget guideline

**Не оптимизация — для понимания scope:**

| Stage | Что делает |
|---|---|
| Bootstrap | install pipeline + check deps |
| GitNexus indexing | npx gitnexus analyze (1-5 min) |
| Discovery | 9 sub-prompts через Serena/GitNexus/rg |
| Phase 01-09 | детекторы (быстро, ~1-3 мин total) |
| Phase 11 enrichment | для каждого critical: 3 Variants + Test + Next step |
| Phase 10a calibration | severity inflation/deflation analysis |
| Finalize | exit 0 от всех гейтов |
| Report | один итоговый message |

**Не стоп без причины. Не задавай вопросов кроме критичных блокеров.**

---

## Команда пользователю — финальная (TL;DR)

```
Прочитай database-audit/MASTER_PROMPT.md и проведи полный автономный
аудит проекта.

PROJECT_PATH=<абсолютный путь>
```

**Это всё.** Один путь. ИИ автоматически:
- определит mode (static vs live) через MCP postgres / env-files / config
- проверит read-only безопасность
- запустит pipeline целиком
- даст финальный отчёт

Если нужно forced static mode — добавь `mode=static` в команду (override).
Если нужен явный DSN — добавь `DATABASE_URL=<dsn>` (override).
По умолчанию — full autonomous.
