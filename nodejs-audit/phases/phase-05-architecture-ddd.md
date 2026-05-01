# Phase 05 — Architecture (DDD + Clean + 6 axes)

> **Цель:** дать архитектурную оценку через словарь DDD, Clean Architecture и Tornhill, а не «общими словами».
>
> **Книги:** Evans §4-6, §14 · Khononov §3, §7-8 · Martin §22-24 · Vernon IDDD §8 · Tornhill §3, §7.

## Inputs

- `reports/02-recon.md` — стек, паттерн, точки входа.
- `reports/03-deterministic.md` — циклы, knip unused.
- `reports/04-hotspots.md` — топ hot-spots.
- `reports/raw/mcp-context.json` — execution flows из gitnexus.

## Outputs

- `nodejs-audit/reports/05-architecture.md`

## Шаги

### Часть A — Quantitative анализ (через MCP/grep)

#### A.1. Layer leakage

Проверь, не утекает ли инфраструктура в presentation/router-слой:

```bash
# ORM/SQL в роутерах/handlers
grep -rEn "prisma\.|knex\.|db\.query|sequelize|pgPool" <router-paths> 2>/dev/null
```

Если в gitnexus есть — `mcp__gitnexus__shape_check` для FSD/Clean слоёв.

#### A.2. Execution flows

**Если есть gitnexus** — `mcp__gitnexus__route_map` дает реальные пути запросов. Запиши топ-10 flows: `<entry> → <handler> → <service> → <repo> → <DB>`.

**Без gitnexus** — построй вручную для 3 главных endpoints (по recon).

#### A.3. Boundary leaks vs domain isolation

Для каждого домена/feature:

```bash
# что domain импортирует
grep -rEn "^import" <domain-path> --include="*.ts" 2>/dev/null
```

Запрещённые импорты в domain (Martin §22):
- `prisma`, `pg`, `mongoose` — ORM/DB.
- `grammy`, `telegraf`, `discord.js` — UI frameworks.
- `fastify`, `express`, `nuxt`, `next` — HTTP.
- `bullmq`, `kafkajs` — message brokers.

Если такие импорты есть — это **anemic / mixed layers**.

### Часть B — DDD-классификация

Для каждого `entities/<X>/` (или `domain/<X>`):

| Признак | Anemic (плохо) | Rich (хорошо) |
|---|---|---|
| Файлы | `*-queries.ts`, `*-types.ts` only | `*-types.ts` + `*-aggregate.ts` с методами |
| Методы | геттеры, сеттеры | `Entity.deduct(amount): Result<...>` |
| Invariants | живут в use case или handler | живут в entity / aggregate |

Запиши вердикт: **anemic / rich / mixed**.

#### B.1. Aggregates с invariants

Проверь — где живёт самая важная бизнес-инварианта проекта (часто это refund / payment / token consistency):

```
mcp__serena__find_symbol (name_path="<refund-name>")
mcp__gitnexus__context (name="<refund-name>")
```

Если invariant разбросана между handler + service + repo + worker — это **«scattered invariant»** (Khononov §3).

#### B.2. Anti-corruption layer (ACL) для каждой external integration

Перечисли в recon-ом найденные external services (AI providers, payments, S3, Telegram, …). Для каждого проверь:

- Есть ли отдельный `adapters/<vendor>.ts` с явным domain-friendly интерфейсом?
- Не утекают ли вендорские типы (например, `stripe.Charge`, `axios.AxiosResponse`) в use case'ы?

Без ACL = **direct dependency**, тяжело менять провайдера.

### Часть C — 6 классических осей (для отчёта)

Для каждой — 0–10:

1. **Разделение слоёв** — utech/no leak.
2. **Связность/сцепление** — fan-in топ файла, циклы.
3. **SOLID** — DI, OCP пример, SRP примеры/нарушения.
4. **Доменные границы** — anemic/rich, ACL присутствие.
5. **Управление состоянием** — где живёт state, persisted vs in-memory, distributed vs single-instance.
6. **Обработка ошибок** — единая стратегия, Result vs throw, error categorization.

## Шаблон отчёта `05-architecture.md`

```markdown
# Architecture (DDD + Clean + classical)

## TL;DR
[3 предложения: тип архитектуры, где живут invariants, главный риск.]

## Quantitative findings (Phase 4 + gitnexus + grep)

### Execution flows (top-5)
1. `<entry> → <handler> → <service> → <repo> → <DB>`
2. ...

### Layer leakage
- ORM в routers: <count> [с файлами]
- HTTP framework в domain: <count>

### Hot-spots → architectural concerns
- `<file>` (churn=N, fan-in=M) — это <smell name> (см. phase 04)

## DDD-классификация

| Aggregate | Verdict | Invariants |
|---|---|---|
| User | rich/anemic/mixed | где живут |
| Generation | ... | ... |
| Payment | ... | ... |

## Anti-corruption layer

| Integration | ACL присутствует? | Vendor types утекают? |
|---|---|---|
| AI provider X | yes/no | yes/no |
| Stripe | yes/no | yes/no |
| ... | | |

## Оценки (X/60) — 6 осей

| Ось | Оценка | Главная проблема |
|---|---|---|
| Разделение слоёв | X/10 | ... |
| Связность/сцепление | X/10 | ... |
| SOLID | X/10 | ... |
| Доменные границы | X/10 | ... |
| Управление состоянием | X/10 | ... |
| Обработка ошибок | X/10 | ... |

## Топ-3 архитектурных риска

### Риск 1: <название>
- **Что:** ...
- **Где:** <файлы:строки>
- **Why bad (book):** Khononov §3 / Evans §6 / Tornhill §7
- **Чем грозит:** ...
- **Как чинить:** [план в 3-5 шагов]
- **Артефакт:** ADR-DRAFTS/ADR-XXX-<slug>.md (создаётся в phase-12)

### Риск 2 / Риск 3 ...

## Pre-draft ADR list (для phase-12)

- ADR-XXX: <название> — закроет Риск 1.
- ADR-YYY: <название> — закроет Риск 2.
- ADR-ZZZ: <название> — закроет Риск 3.
```

## Критерии завершения

- `reports/05-architecture.md` существует.

## Сигналы в чат

- Старт: `[PHASE 05] STARTED — Architecture (DDD + Clean)`
- Конец: `[PHASE 05] DONE — reports/05-architecture.md`

→ Переход к **phase-06-readability.md**.
