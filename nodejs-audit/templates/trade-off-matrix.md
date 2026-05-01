# Trade-off matrix (Richards & Ford, 10 ilities)

> Используется в `phase-11-synthesis.md` и переносится в `FINAL-REPORT.md`.
>
> **Книга:** Richards & Ford, *Fundamentals of Software Architecture* 2e §5-6.

---

## Описание метрик

| Characteristic | Что значит |
|---|---|
| **Deployability** | Как легко развернуть/откатить в prod (canary, blue-green, feature flags). |
| **Reliability** | Не теряет ли данные/деньги при отказе компонента (saga, outbox, idempotency). |
| **Recoverability** | За какое время восстановиться после сбоя (replay, snapshots, runbooks). |
| **Observability** | Можно ли в 3 ночи понять, что упало (logs, metrics, traces, errors). |
| **Security** | Defence-in-depth на каждом trust boundary (auth, crypto, secrets, audit). |
| **Modifiability** | Как быстро добавить новую фичу/провайдера/язык/платёж. |
| **Testability** | Можно ли тестировать в изоляции (unit ≥80%, integration на critical paths). |
| **Performance** | p95 latency, throughput, memory под realistic нагрузкой. |
| **Scalability** | Можно ли горизонтально (workers, replicas, sharded DB). |
| **Cost-efficiency** | Cost per request / per user, утилизация ресурсов. |

---

## Шкала оценок (0-10)

| Score | Meaning |
|---|---|
| 0-3 | Не реализовано или критично сломано. |
| 4-5 | Базово работает, но без resilience / advanced features. |
| 6-7 | Production-приемлемо для среднего размера. |
| 8-9 | Production-grade, есть автоматические guards. |
| 10 | Industry leader, fitness functions + dashboards. |

---

## Шаблон таблицы

| Characteristic | Current | Target | Action (ссылка) |
|---|:---:|:---:|---|
| Deployability | | | ROADMAP §<X> / ADR-XXX |
| Reliability | | | |
| Recoverability | | | |
| Observability | | | |
| Security | | | |
| Modifiability | | | |
| Testability | | | |
| Performance | | | |
| Scalability | | | |
| Cost-efficiency | | | |

---

## Как заполнять (правила)

1. **Current** — выводи из соответствующей фазы:
   - Deployability: phase-09 (CI) + phase-10 (zero-downtime?).
   - Reliability: phase-07 (idempotency) + phase-09 (uncaughtException).
   - Recoverability: phase-09 (health/ready + replay).
   - Observability: phase-09.
   - Security: phase-07.
   - Modifiability: phase-05 (ACL, layers).
   - Testability: phase-03 (tests passed) + phase-05 (mockable seams).
   - Performance: phase-08.
   - Scalability: phase-08 + phase-05 (single-process anti-patterns).
   - Cost-efficiency: phase-08 (provider routing, caching).

2. **Target** — реалистичная цель на 3 месяца. Не «10/10 везде» — обычно 1-2 ility делают +2, остальные +1.

3. **Action** — ссылка на конкретный ADR-DRAFT или phase в ROADMAP. Без ссылки — строка пустая.

---

## Пример заполнения

| Characteristic | Current | Target | Action |
|---|:---:|:---:|---|
| Deployability | 8 | 10 | ADR-022 zero-downtime migrations |
| Reliability | 8 | 10 | ADR-023 saga + outbox |
| Recoverability | 8 | 9 | event replay (event sourcing for refunds) |
| Observability | 7 | 10 | ADR-021 OpenTelemetry + Sentry |
| Security | 9 | 10 | ADR-024 secrets vault + SBOM |
| Modifiability | 7 | 10 | ADR-015 domain layer + ADR-019 ACL |
| Testability | 7 | 9 | Domain pure functions (после ADR-015) |
| Performance | 8 | 9 | Provider cost-aware routing |
| Scalability | 6 | 8 | Read replicas + Redis Cluster |
| Cost-efficiency | 8 | 9 | Cost-aware provider selection |
