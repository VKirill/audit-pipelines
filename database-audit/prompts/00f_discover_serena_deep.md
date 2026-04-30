# 00f — Deep discovery via Serena (semantic navigation)

> Используется **после** 00a-00e базовых sub-prompts. Цель — глубокая verification + покрытие missed-by-rg случаев через Serena LSP.

---

## Pre-flight

```bash
# Проверь что Serena активна
serena.get_current_config
# Проверь онбординг
serena.check_onboarding_performed
# Если нет → serena.onboarding
serena.activate_project  # абсолютный путь проекта
```

Если Serena недоступна — fallback на ripgrep (помечай `degraded` в `audit/_known_unknowns.md`).

---

## Шаг 1 — Verify money endpoints через `find_referencing_symbols`

`rg` находит **текстовые** упоминания. Serena находит **семантические** ссылки (точно тот же символ).

Для каждой `hints.money_columns[i]`:

```
serena.find_referencing_symbols(
    name_path='balanceRub',         # имя поля
    file_or_class='ContentProject'  # disambiguation
)
```

Каждая ссылка → проверь:
- Read-only access? → ignore
- Write access (Update/Set/decrement)? → kandydat money_endpoint
- Через ORM-метод (`prisma.contentProject.update`) → точно money_endpoint
- Через raw SQL (`UPDATE content_projects SET balanceRub = ...`) → money_endpoint, ВНИМАНИЕ к транзакции

**Важно:** в monorepo ссылки могут быть в разных workspace. Серена обходит весь активный проект.

Расширь `hints.money_endpoints` после прохода через все колонки.

---

## Шаг 2 — Verify transaction bodies

Для каждой `hints.transaction_sites[i]` с `kind: missing-transaction`:

```
serena.find_symbol(
    name_path='deductFromBalance',
    include_body=True,
    relative_path='apps/crm/src/features/content/lib/cbr.ts'
)
```

Прочитай **полное тело**. Подтверди:
- [ ] Действительно нет `$transaction` / `BEGIN` / `FOR UPDATE`?
- [ ] Если есть atomic UPDATE (`SET balance = balance - $1 WHERE balance >= $1`) — это **safe**, понизь severity до medium с пометкой
- [ ] Если есть `await prisma.$transaction(async (tx) => { ... })` где-то выше по цепочке — это safe (caller wraps)
- [ ] Если RMW реальный → critical с exploit_proof

Auto-update `confidence_rationale` с реальной цитатой из тела функции.

---

## Шаг 3 — SQLi surface через `search_for_pattern`

**ОБЯЗАТЕЛЬНО** (это главный пропуск v3):

```
# Все Unsafe API
serena.search_for_pattern(
    substring_pattern=r'\$query(?:Raw)?Unsafe|\$execute(?:Raw)?Unsafe',
    glob='**/*.{ts,tsx,js,mjs,cjs}',
    paths_include=['apps', 'packages']
)

# Все custom wrappers (dbExec/dbQuery/executeQuery)
serena.search_for_pattern(
    substring_pattern=r'\b(dbExec|dbQuery|executeQuery|executeRaw|runQuery)\s*\(',
    glob='**/*.ts'
)

# Динамическая склейка SQL — main SQLi vector
serena.search_for_pattern(
    substring_pattern=r'\$\{[^}]+\}.*?(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)',
    glob='**/*.ts'
)
```

Для каждого hit:
- `serena.find_symbol(<containing function>, include_body=true)` → прочитай тело
- Откуда приходит input в interpolation? Если user-controlled → **critical SQLi**
- Если только positional placeholders ($1, $2) — high (требует verification по data flow)

Заполни `hints.raw_sql_in_code` с правильным `kind` и `uses_user_input` flag.

---

## Шаг 4 — Pool config validation

Для каждого `paths.pool_config_files[i]`:

```
serena.find_symbol('createPool', relative_path=<file>, include_body=true)
# или
serena.find_symbol('Pool', relative_path=<file>, include_body=true)
```

Прочитай и зафиксируй точные значения `max`, `idleTimeoutMillis`, `connectionTimeoutMillis`. Это уточняет `hints.pool_settings`.

---

## Шаг 5 — Multi-tenant verification (если применимо)

Если `manifest.hints.multi_tenant_isolation.model = 'discriminator-column'`:

Для каждого `paths.api_routes` (если есть, иначе пропускай):
```
serena.find_symbol(<handler function>, include_body=true)
```

Проверь что в теле есть `WHERE` clause с tenant discriminator (`projectId`, `tenantId`, `workspaceId`).

Если handler меняет данные **без** tenant filter — `kind: cross-tenant-leak` → critical finding.

---

## Шаг 6 — Auth bypass surface

Расширенный поиск с Serena:

```
serena.search_for_pattern(
    substring_pattern=r'export\s+(const|async)\s+(GET|POST|PUT|DELETE|PATCH)\s*=',
    glob='**/api/**/*.ts'
)
# или для Next.js Pages-style
serena.search_for_pattern(
    substring_pattern=r'export default async function handler',
    glob='**/api/**/*.ts'
)
```

Для каждого handler:
- Прочитай тело через `find_symbol include_body=true`
- Есть ли `withAuth(...)` / `requireAuth()` / NextAuth `auth()` / passport / `getServerSession()`?
- Если **нет auth** на /api/* + меняет state → critical

---

## Шаг 7 — PII расширенная коврovка

PII колонки выходят за рамки v3 списка. Дополнительно ищи через Serena:

```
serena.search_for_pattern(
    substring_pattern=r'(password|password_hash|hashedPassword|refresh_token|access_token|oauth_token|webhook_secret|api_secret|stripe_key|sendgrid_key)',
    glob='**/*.prisma'
)
serena.search_for_pattern(
    substring_pattern=r'(SSN|social_security|tax_id|passport_no|drivers_license|cvv|card_number)',
    glob='**/*.prisma'
)
```

Каждое попадание — добавь в `hints.pii_candidates` с правильным `classification` (см. `00c_discover_pii.md` enum).

---

## Шаг 8 — Save progress

```
serena.write_memory(
    name='audit_phase_discover',
    content='Discover phase complete. Manifest: <git_head>. Stack: postgresql+prisma. Money: N. Transactions: M. PII: K. Raw SQL Unsafe: P. SQLi surface: Q.'
)
```

Это помогает в `init.sh --refresh` — следующий прогон прочитает memory.

---

## Quality gate перед переходом к 00g

После 00f:

- [ ] Каждая money колонка проверена через `find_referencing_symbols`
- [ ] Каждая `transaction_sites[i] missing-transaction` подтверждена чтением тела
- [ ] `$queryRawUnsafe` / `$executeRawUnsafe` / custom wrappers найдены
- [ ] Multi-tenant handlers проверены (если применимо)
- [ ] PII enriched (passwords, tokens, payment-card)
- [ ] `_known_unknowns.md` обновлён случаями degraded MCP

Без всех галочек — не переходи к 00g.

---

## 🔴 v5 — Idempotency unique-constraint verification

> Для каждой `money_endpoints[i]` с `has_idempotency_key: false` — двойная проверка через Serena, не только grep по signature.

### Шаги

#### 1. Поиск unique constraint на (object_id, idempotency_key) в схеме

Для каждой money_column таблицы:

```
serena.search_for_pattern(
    substring_pattern=r'@@unique\s*\(\s*\[[^\]]*idempotency',
    glob='**/*.prisma'
)
serena.search_for_pattern(
    substring_pattern=r'UNIQUE.*\b(idempotency|operation_id|request_id)\b',
    glob='**/*.sql'
)
```

#### 2. Поиск Idempotency-Key header в HTTP routes

```
serena.search_for_pattern(
    substring_pattern=r'(Idempotency-Key|x-idempotency|idempotency_key)',
    glob='**/api/**/*.ts'
)
```

#### 3. Решение

- Constraint в БД + header parse в route → `has_idempotency_key: true`
- Только header без БД constraint → `partial` (header useless без БД enforcement) → finding `DB-MONEY-NNN [high]`
- Ничего → `has_idempotency_key: false` → finding `DB-MONEY-NNN [critical]`

Это **точнее** чем grep по signature функций — проверяется реальная защита на БД-уровне.
