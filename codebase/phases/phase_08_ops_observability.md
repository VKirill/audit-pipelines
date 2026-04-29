# PHASE 08 — OPS & OBSERVABILITY

**Цель:** Оценить инфраструктурную зрелость: как код попадает в production и как его поведение видно после деплоя.

**Источники:**
- Humble & Farley, *Continuous Delivery*.
- Forsgren, Humble & Kim, *Accelerate* — DORA 4 metrics (lead time, deploy frequency, MTTR, change fail rate).
- Google, *Site Reliability Engineering* — SLI/SLO, error budgets, golden signals.
- Majors, Fong-Jones, Miranda, *Observability Engineering* — events/metrics/traces, high-cardinality.
- Nygard, *Release It!* — operability.
- The *Twelve-Factor App*.

---

## 1. Входы
- `audit/01_inventory.md` — CI конфиги, Dockerfile, compose, k8s.
- `audit/02_architecture.md` — cross-cutting concerns (logging, metrics, tracing).

## 2. Чек-лист проверок

### 2.1. CI/CD конфигурация
- [ ] Найти конфиги: `.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `azure-pipelines.yml`, `bitbucket-pipelines.yml`.
- [ ] Для каждого workflow — какие стейджи? Ищем минимум: `lint`, `test`, `build`, `security` (SCA/SAST), `deploy`.
- [ ] Если проект имеет несколько окружений (dev/staging/prod) — видно ли промоушен между ними?

### 2.2. Pre-commit / git hooks
- [ ] `.husky/`, `.pre-commit-config.yaml`, `lefthook.yml`.
- [ ] Настроены ли: format check, lint, typecheck, быстрые тесты?
- [ ] Отсутствие — `low` finding (DX).

### 2.3. Линтеры и форматтеры
- [ ] Конфиги: `.eslintrc*`, `.prettierrc*`, `pyproject.toml` (`[tool.ruff]`, `[tool.black]`), `.editorconfig`, `golangci.yml`, `checkstyle.xml`, `.rubocop.yml`, `rustfmt.toml`.
- [ ] Запускаются ли они в CI? (grep в workflow-файлах на `lint`, `ruff`, `eslint`, и т. п.)
- [ ] Если конфиг есть, но в CI не запускается — finding `medium` (иллюзия стандарта).
- [ ] Отсутствует вообще — finding `medium` (для M+ проектов).

### 2.4. Типы / static analysis
- [ ] `mypy`, `pyright`, `tsc --strict`, SpotBugs, ESLint-tsc. Активен ли strict-mode?
- [ ] В TS: `"strict": true` в `tsconfig.json` — если `false` или частично — finding `low`/`medium`.
- [ ] В Python: `mypy` config и покрытие типами топ-файлов — если < 50% — finding `low`.

### 2.5. Build reproducibility
- [ ] `Dockerfile` — есть ли pinned base images? (`FROM node:20.10.0-slim` — ok; `FROM node:latest` — finding `medium`).
- [ ] Multi-stage для слоёв prod vs dev. Если всё в одном `node:18` и отдаёт 1+GB — finding `low`.
- [ ] Non-root user (`USER app`) — если запуск под root — `medium`.

### 2.6. Deploy strategy
По файлам инфраструктуры:
- [ ] Есть ли канарейки / blue-green / rolling?
- [ ] Rollback процедура документирована?
- [ ] Deploy по тегу или по push в main? (Второе — `low` если без тестов, `info` если тесты проходят.)
- [ ] IaC (Terraform, Pulumi, CloudFormation, Ansible) — есть или всё руками?

### 2.7. Feature flags
- [ ] Наличие FF-системы (LaunchDarkly, Unleash, собственная)? Отсутствие при размере проекта L+ — finding `low` (замедляет release cadence).

### 2.8. Logging
- [ ] **Структурированные логи?**
  - `search_for_pattern` на `console.log`, `print(` в не-тестовом коде — `low`/`medium` массово.
  - Наличие logger-библиотек: `pino`, `winston`, `bunyan`, `structlog`, `zerolog`, `slf4j` + Logback с json layout.
- [ ] **Уровни логов.** Используются ли `debug`/`info`/`warn`/`error`, или всё на одном уровне?
- [ ] **Correlation ID.** Протягивается ли request-id/trace-id через все слои?
  - Поиск: `x-request-id`, `correlation-id`, `traceId`, `requestId` в middleware/filter.
  - Отсутствие в многосервисной архитектуре — `high`.
- [ ] **Sensitive в логах** — пересечение с фазой 06.
- [ ] Логи отправляются централизованно (есть shipping — Fluentd, Vector, Filebeat, OTEL collector) или пишутся только в stdout/файл? Для L+ проектов центр. логирование — требование, finding `medium` при отсутствии.

### 2.9. Metrics
- [ ] Поиск: `prometheus_client`, `micrometer`, `prom-client`, `opentelemetry.metrics`.
- [ ] Golden signals (SRE book): latency, traffic, errors, saturation. Собираются ли?
- [ ] HTTP latency histograms, request rate, error rate — есть?
- [ ] Отсутствие метрик при наличии HTTP-API — finding `medium` (для small — `low`).
- [ ] Метрики высокой кардинальности без агрегации (user_id в label) — finding `medium` (prometheus cost).

### 2.10. Distributed tracing
- [ ] `opentelemetry`, `jaeger`, `zipkin`, `@opentelemetry/sdk*`.
- [ ] Instrumented ли HTTP и DB клиенты (auto-instrumentation)?
- [ ] Отсутствие при микросервисной архитектуре — finding `medium`/`high`.

### 2.11. Health checks
- [ ] `/health`, `/healthz`, `/ready`, `/live` эндпоинты.
- [ ] Различие liveness vs readiness (разные ответы)?
- [ ] Readiness проверяет downstream (DB, Redis)?
- [ ] Отсутствие — `medium` для дeploy-on-k8s/cloud-run/ECS.

### 2.12. Configuration management (12-factor)
- [ ] Конфиг через env vars vs файлы в репо?
- [ ] Разные конфиги для разных окружений (хорошо)?
- [ ] Секреты — через vault/secret manager, или в env CI → finding по уровню:
  - Только через CI env secrets: `medium` (acceptable для small/medium проектов).
  - В файлах в репо: → `critical` уже поймано в фазе 06.
- [ ] «Config dump на старте» (логирование всей конфигурации, включая секреты): finding `high`.

### 2.13. Resource limits
- [ ] Dockerfile / K8s: заданы ли `memory`, `cpu` limits/requests?
- [ ] Отсутствие — `medium` (для production workloads).

### 2.14. Backup & disaster recovery
Видно не всегда, но проверь:
- [ ] БД бэкапы настроены в IaC / skriптах / runbooks?
- [ ] Runbooks в `docs/runbooks/` или `docs/ops/`?
- [ ] Отсутствие упоминаний — `info`, это требует интервью с командой.

### 2.15. DORA метрики (по репозиторию)
Грубая оценка из git:
- [ ] **Deploy frequency**: если есть тег-релизы — `git tag --sort=creatordate | tail -20`, посчитай темп. Еженедельно — элитно. Раз в месяц — среднее. Раз в квартал — низкое. (Accelerate)
- [ ] **Lead time for changes**: среднее время от коммита до merge в main (требует анализа PR-истории — если есть `gh` CLI и `GITHUB_TOKEN`).
- [ ] **Change failure rate / MTTR**: не определяется без incident-системы. Пометить как «требует данных от команды».

### 2.16. Repository hygiene
- [ ] `.gitignore` — исключает `node_modules`, `__pycache__`, `dist`, `build`, `.env`?
- [ ] В git-индексе есть файлы, которые не должны быть там?
  ```bash
  git ls-files | grep -E "(node_modules|__pycache__|\.env|\.pyc|dist/|build/|\.DS_Store)" | head
  ```
- [ ] Большие файлы в истории?
  ```bash
  git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | awk '$1=="blob" && $3>1048576 {print $3, $4}' | sort -rn | head -10
  ```
- [ ] Бинарные артефакты в истории (`.jar`, `.tar.gz`, `.zip`, `.iso`) — finding `medium` (раздувают клонирование).

### 2.17. Stability patterns operability
Из фазы 05 вернись к:
- Timeouts / retries / circuit breakers — тут отметь финальной сводкой.
- Если их нет и нет метрик для их отслеживания — это фундаментальная проблема operability.

## 3. Артефакт — `audit/08_ops_observability.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено**
3. **Ключевые наблюдения**
   - **CI/CD pipeline** — diagramma/схема стейджей.
   - **Lint / typecheck / test в CI** — сводка.
   - **Logging** — структура, уровни, correlation, централизация.
   - **Metrics** — что собирается, golden signals coverage.
   - **Tracing** — есть/нет.
   - **Health checks** — liveness/readiness/deep.
   - **Config / secrets** — схема.
   - **Deploy / rollback** — схема.
   - **DORA estimates** — что можно оценить.
   - **Repo hygiene** — сводка.
4. **Находки**
5. **Неполные проверки** (часто многое недоступно без интервью — это нормально)
6. **Контрольные вопросы**
   - **Q1.** Если прод упадёт в 3 утра — сколько минут займёт оператору понять, *что именно* сломалось, используя только логи/метрики/дашборды, которые видно из кода? (Субъективно, но обоснованно.)
   - **Q2.** Сколько шагов (коммит → прод)? Все автоматизированы или есть ручные?
7. **Следующая фаза:** `phases/phase_09_performance.md`

## 4. Memory

```markdown
# Phase 08 memory
Completed: YYYY-MM-DD

Ops posture:
- ci_stages: [lint?, test?, sast?, sca?, build?, deploy?]
- logging: <structured/unstructured/mixed>
- correlation_id: <yes/no/partial>
- metrics: <full/partial/none>
- tracing: <yes/no>
- health_checks: <yes/no>
- deploy_automation: <full/partial/manual>
- repo_hygiene: <clean/dirty>

Observability gaps:
1. <gap>
2. ...

Next phase: phase_09_performance.md
```

## 5. Отчёт пользователю

> Фаза 8/10 завершена. Ops: CI <есть/нет>, deploy <автоматизирован/частично/ручной>, логи <структурированные/нет>, метрики <полные/частичные/нет>, трейсинг <да/нет>. Добавлено <N> findings. Перехожу к фазе 9 — производительность.

Перейди к `phases/phase_09_performance.md`.
