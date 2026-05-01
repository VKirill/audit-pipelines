# Phase 09 — Observability

> **Цель:** оценить готовность к production-эксплуатации — логи, метрики, трейсинг, error-tracking, SLO.
>
> **Книги:** Charity Majors *Observability Engineering* §3, §5, §7 · SRE Workbook (Beyer) · Susan Fowler PRMS §5-6.

## Inputs

- `reports/02-recon.md` — стек.
- `reports/03-deterministic.md` — есть ли test setup.

## Outputs

- `nodejs-audit/reports/09-observability.md`
- `nodejs-audit/reports/raw/obs-*.log`

## Шаги

### 1. Логи

```bash
# console.* — антипаттерн в production
grep -rEn "console\\.(log|error|warn|info|debug)" <src> 2>/dev/null \
  | grep -vE "shared/lib/logger|server/utils/logger|debug-log\\.ts" | wc -l

# структурный logger
grep -rEn "pino|winston|bunyan|@nestjs/common.*Logger" package.json <src> 2>/dev/null
grep -rEn "createLogger\\(|loggerFactory" <src> 2>/dev/null | wc -l
```

Проверь:
- Структурный logger (JSON-формат для prod)?
- PII redaction слой?
- `log.child({ requestId })` поддерживается?

### 2. Correlation / Request ID

```bash
grep -rEn "requestId|correlationId|traceId|x-request-id|reqId|genReqId" <src> 2>/dev/null \
  > reports/raw/obs-request-id.log
```

Проверь — request-id наследуется из header, или генерится UUID?

### 3. Health endpoints

```bash
grep -rEn "/health|/ready|/healthz|/livez|/_health" <src> --include="*.ts" 2>/dev/null \
  > reports/raw/obs-health.log
```

Различай:
- **liveness** (`/health`, простой 200) — «процесс жив».
- **readiness** (`/ready`, проба зависимостей) — «готов принимать траффик».

### 4. Метрики

```bash
grep -rEn "prom-client|@opentelemetry|prometheus" package.json <src> 2>/dev/null \
  > reports/raw/obs-metrics.log
```

Если `prom-client` есть — посмотри что экспортируется (HTTP latency, business counters?).

### 5. Distributed tracing

```bash
grep -rEn "@opentelemetry|trace\.startSpan|tracer\." <src> 2>/dev/null \
  > reports/raw/obs-tracing.log
```

OpenTelemetry — стандарт. Если нет — это Medium-finding для production-ready проекта.

### 6. Error tracking

```bash
grep -rEn "@sentry|bugsnag|rollbar" package.json <src> 2>/dev/null \
  > reports/raw/obs-error-tracking.log
```

### 7. Process-level handlers

```bash
grep -rEn "uncaughtException|unhandledRejection" <src> --include="*.ts" 2>/dev/null
```

Должны быть для каждого entry-process.

### 8. PII в логах

```bash
grep -rEn "log.*req\\.body|log.*password|log.*token" <src> 2>/dev/null \
  > reports/raw/obs-pii.log
```

### 9. SLO / dashboards (если есть монорепо с infra)

Поищи:
- `grafana/`, `dashboards/`, `prometheus.yml`, `alerts.yml`.

## Шаблон отчёта `09-observability.md`

```markdown
# Observability

## TL;DR
[Готов к production: да / нет / частично]

## Оценки (X/40)

| Столп | Оценка |
|-------|--------|
| Логи | X/10 |
| Метрики | X/10 |
| Трейсинг | X/10 |
| Мониторинг ошибок | X/10 |

## Детально

### Логи
- console.log использований: <N>
- Структурированный logger: <pino/winston/нет>
- JSON для prod: <yes/no>
- Корреляционный ID: <yes/no>
- PII redaction: <yes/no>

### Метрики
- prom-client / OTel: <да/нет>
- Health endpoints: liveness=<yes/no>, readiness with probe=<yes/no>
- Business metrics: <да/нет — ключевая отличительная характеристика>

### Трейсинг
- OpenTelemetry: <да/нет>
- Trace propagation в async (BullMQ/queue): <да/нет>

### Мониторинг ошибок
- Sentry/Bugsnag: <да/нет>
- uncaughtException + unhandledRejection: <yes/no — для каждого entry>

## Сценарий «что если в 3 ночи всё упадёт»
[Реалистичный анализ: можно ли понять что случилось.]

## Production-readiness gap (по Susan Fowler 8 pillars)
| Pillar | Статус |
|---|---|
| Stability | ✅/⚠️/❌ |
| Reliability | |
| Scalability | |
| Fault tolerance | |
| Performance | |
| Monitoring | |
| Documentation | |
| Understandability | |

## Топ-5 действий для production-готовности
1. ...

## Готовые промты
[Будут собраны в QUICK-WINS.md / ROADMAP.md в phase-12]
```

## Критерии завершения

- `reports/09-observability.md` существует.

## Сигналы в чат

- Старт: `[PHASE 09] STARTED — Observability`
- Конец: `[PHASE 09] DONE — reports/09-observability.md`

→ Переход к **phase-10-ai-readability.md**.
