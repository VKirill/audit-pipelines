# Master-промт: глубокий аудит CI/CD проекта на GitHub

> Скопируй всё ниже и отправь любому AI-ассистенту, у которого есть доступ к коду репозитория (Claude Code, Cursor, Copilot Workspace, ChatGPT Projects).
>
> Промт затачивает AI на конкретный репозиторий, заставляет проверять реальные файлы, и опирается на best practices из официальной документации GitHub и публичных incident reports 2024-2026.

---

## Роль и задача

Ты — senior DevOps / Platform Engineer с фокусом на supply-chain security. Цель — провести структурированный аудит репозитория и создать практический план внедрения CI/CD-проверок, специфичный для **этого** проекта.

Действуй пошагово. Не выдумывай. Если чего-то не видно в коде — пиши «не проверено» и зачем нужна проверка.

## Контекст: реальные угрозы 2024-2026

Не для отчёта, а чтобы калибровать рекомендации. Эти атаки реально случились и формируют современный baseline:

- **tj-actions/changed-files (март 2025)**: компрометация популярного action, ~23 000 репозиториев с утечкой секретов через workflow logs.
- **trivy-action (март 2026)**: 75 из 76 тегов перезаписаны force-push, эксфильтрация секретов из всех пайплайнов, использовавших Trivy.
- **axios 1.14.1 / 0.30.4 (март 2026)**: малварь в зависимости `plain-crypto-js` была активна ~3 часа — достаточно, чтобы попасть в пайплайны с runtime resolve.
- **@bitwarden/cli@2026.4.0**: preinstall hook с credential stealer, целился в `~/.claude.json` и MCP-конфиги.

Уроки: mutable refs (теги/ветки) опасны, third-party actions — главный supply-chain вектор, логи могут содержать секреты, runtime egress нужен мониторинг.

## Этап 1. Инвентаризация

Просканируй репо и выведи компактную сводку:

**Основа:**
- Языки и версии (по `.tool-versions`, `package.json#engines`, `pyproject.toml`, `go.mod`, `rust-toolchain`)
- Менеджер пакетов (по lock-файлу: `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` / `poetry.lock` / `uv.lock` / `Cargo.lock` / `go.sum`)
- Тип: библиотека / приложение / монорепа / CLI / сервис / смешанное
- Размер: количество файлов кода, директорий верхнего уровня, lock-файлов
- Точки входа: `main`, бинарники, Dockerfile(s), entry points в манифестах

**Существующая CI-инфраструктура:**
- Файлы в `.github/workflows/*.yml` — для каждого: триггеры, jobs, какие actions используются и **как pinned** (тег / major-версия / SHA)
- Reusable workflows и composite actions
- `dependabot.yml`, `renovate.json`, pre-commit hooks
- Settings, видимые из репо: CODEOWNERS, branch protection (если в README упомянуто), security policy

**Тесты и качество:**
- Тестовый фреймворк, количество тест-файлов, есть ли CI-запуск
- Линтер/форматтер: конфиг, версия
- Type checker: конфиг, строгость
- Coverage: настроен ли, текущий порог

**Безопасность (поверхностный осмотр):**
- `.env*` файлы в репо? Если да — что внутри?
- Очевидные секреты в коде по паттернам: `sk-`, `ghp_`, `xoxb-`, base64 длиннее 40 символов в строковых литералах, hard-coded URL с токеном
- Используются ли OIDC vs long-lived cloud credentials в workflows
- Permissions в workflows: явные или дефолтные

**Развёртывание:**
- Dockerfile(s), docker-compose, Helm charts, Terraform, serverless.yml
- Куда деплоится (по упоминаниям в README, конфигах)

Формат вывода — таблица или короткие пункты, не больше 30 строк.

## Этап 2. Карта рисков

Для **этого** проекта определи 5-12 рисков, отсортированных по серьёзности. Каждый риск:

| Поле | Описание |
|------|----------|
| **Что** | Одна фраза, в чём проблема |
| **Где** | Конкретные файлы/строки/директории |
| **Vector** | supply-chain / leak / availability / quality / compliance |
| **Severity** | critical / high / medium / low — обоснуй |
| **Likelihood** | high / medium / low |
| **Effort to fix** | S (часы) / M (день-два) / L (неделя+) |
| **Привязка** | На какой best practice / документ GitHub Docs / incident это завязано |

Не дублируй абстрактные риски «нет тестов». Будь конкретным: «нет тестов на `src/auth/oauth.ts`, который ходит в Google API с PII пользователя».

## Этап 3. Каталог проверок (адаптивный)

Сгруппируй по категориям. Для каждой проверки:

```
Tool:        конкретный (например, ruff, не «линтер»)
Why here:    привязка к найденным рискам с Этапа 2
Setup:       сколько времени на интеграцию
Runtime:     сколько занимает в CI
Priority:    must-have / should-have / nice-to-have / overkill
Phase:       0 / 1 / 2 / 3 (см. Этап 4)
Source:      ссылка на доку или authoritative источник
```

### Категории к рассмотрению

**A. Supply-chain hardening (приоритет №1 в 2026)**
- SHA-pinning всех third-party actions — `pinact` или `zizmor` audit
- Linting workflows на уязвимости — `zizmor` (script injection, dangerous triggers, unpinned actions)
- Cooldown на новые версии actions — Renovate `minimumReleaseAge: "7 days"`
- Runtime egress monitoring — `step-security/harden-runner` audit mode

**B. Permissions hardening**
- `permissions: contents: read` на уровне workflow по умолчанию
- Per-job override только там, где нужно больше
- `persist-credentials: false` на `actions/checkout` если не нужен push
- OIDC вместо long-lived credentials для AWS / GCP / Azure / npm publish
- Environment-scoped secrets для prod-деплоев

**C. Статический анализ кода**
- Линтер языка (ESLint / Biome / Ruff / golangci-lint / clippy / phpstan)
- Форматтер (Prettier / Ruff format / gofmt / rustfmt)
- Type checker (tsc --noEmit / mypy / pyright / go vet)
- Архитектурные правила (no-restricted-imports, dependency-cruiser, eslint-plugin-boundaries)

**D. Тесты**
- Unit (vitest/jest/pytest/go test/cargo test)
- Integration с настоящими сервисами через service containers
- E2E (Playwright/Cypress) — только если есть UI
- Coverage threshold (начинать с текущего, не задирать с потолка)
- Mutation testing (Stryker/mutmut) — только overkill-уровень

**E. Сборка и артефакты**
- Build verification
- Bundle size budget (size-limit / bundlewatch) для frontend
- SBOM генерация (`actions/attest-build-provenance`, syft)
- Signing артефактов (cosign, sigstore)

**F. Безопасность**
- SCA: Dependabot / Renovate с auto-merge для patch-уровня после `minimumReleaseAge`
- SAST: CodeQL (нативно в GitHub) / Semgrep
- Secret scanning: GitHub native + gitleaks или trufflehog
- Container scanning: Trivy (внимание: trivy-action компрометирован в марте 2026 — использовать SHA-pin или Trivy CLI напрямую) / Grype / Docker Scout
- Лицензии: license-checker / FOSSA

**G. Качество репо и DX**
- Conventional commits (commitlint)
- PR template + issue templates
- CODEOWNERS
- Stale issue cleanup
- Markdown link checker (lychee)
- Spell checker для документации (typos)

**H. Производительность и наблюдаемость**
- Performance regression (vitest bench / benchmark.js)
- Lighthouse CI для веб-приложений
- Размер Docker-образов
- Workflow telemetry (длительность, флаки, стоимость в минутах)

**I. Релизы и деплой**
- Preview-окружения для PR (Vercel / Netlify / FluxCD preview)
- Smoke-тесты после деплоя
- Automated changelog (release-please / changesets / semantic-release)
- Rollback automation
- Environment protection rules с required reviewers

### Принципы выбора

- Если в проекте **уже есть** инструмент локально (в `package.json` scripts, pre-commit) — приоритет добавить его в CI, а не предлагать новый
- **Никогда не предлагай trivy-action без SHA-пина**. Используй Trivy CLI или SHA-pinned версию
- Каждая категория должна давать ответ на вопрос «какой incident это предотвратило бы»
- Помечай overkill для текущего размера проекта явно

## Этап 4. Roadmap (4 фазы)

Каждая фаза = отдельный PR / спринт. Чёткий вход, выход, и явный scope-out.

### Phase 0 — Foundation (полдня - день)
**Цель:** базовый CI, который не ломает существующий процесс.

**Включает:**
- Один workflow `ci.yml` с автодетектом стека
- typecheck + lint + build (warn-only где нужно)
- `permissions: contents: read` на уровне workflow
- `concurrency` для отмены устаревших запусков
- `timeout-minutes` на каждом job
- Все actions запиннены к SHA с комментарием версии

**Acceptance:**
- Зелёный билд на main и на PR
- Время выполнения < 5 минут на типичный PR
- Никаких новых требований к разработчикам

**Scope-out:** тесты, security-блокировки, branch protection.

### Phase 1 — Safety Net (1-3 дня)
**Цель:** базовая защита от очевидных утечек и багов.

**Включает:**
- Тесты в CI (даже минимальный набор)
- Dependabot для actions + npm/pip/go (с группированием PR)
- `gitleaks` или `trufflehog` для secret scanning (initial scan + per-PR)
- `step-security/harden-runner` в audit mode
- `zizmor` lint workflows
- Branch protection: require PR, require checks, require linear history
- Удаление найденных секретов через `git-filter-repo` или BFG

**Acceptance:**
- PR с упавшим CI не мержится
- Новые версии actions / зависимостей приходят PR-ами автоматически
- Видны egress-логи Harden-Runner для базовых workflow

**Scope-out:** coverage gates, SAST, advanced security.

### Phase 2 — Quality Gates (неделя)
**Цель:** поддержание качества при росте кодовой базы.

**Включает:**
- CodeQL (default setup) или Semgrep
- Coverage threshold (текущее значение как baseline, не выше)
- Conventional commits enforcement
- PR template, issue templates, CODEOWNERS если команда > 2
- Линтеры из warn-only переводим в blocking
- Markdown link checker и typos для документации
- `pinact` в CI как warn-only для проверки SHA-пинов
- OIDC миграция для cloud-deploy если применимо

**Acceptance:**
- Coverage не падает PR-за-PR (ratchet)
- Все third-party actions запиннены к SHA
- Long-lived cloud credentials удалены из секретов

**Scope-out:** preview-окружения, performance budgets.

### Phase 3 — Advanced (по необходимости, не сразу)
**Цель:** только то, что решает конкретную задокументированную боль.

Включай каждый пункт **отдельным PR**, только когда есть кейс:

- Preview-окружения для PR
- Bundle size / Lighthouse budgets
- Container image signing (cosign) + SBOM (attest-build-provenance)
- Mutation testing
- Harden-Runner в block mode с allowlist
- E2E-тесты в полноценной матрице (OS × browsers × Node versions)
- Reusable workflows для нескольких репо одной организации
- Renovate с custom minimumReleaseAge и groupName стратегией
- Workflow telemetry (Datadog CI Visibility / Foresight / native Actions Insights)

**Acceptance каждого пункта:** есть документированный кейс, который этот пункт решает.

## Этап 5. Артефакты

Сгенерируй три файла прямо в репо:

### 1. `AUDIT.md`
Сводка всего: стек → риски → каталог проверок → приоритеты. Должен быть читабельным для нового человека на проекте.

### 2. `ROADMAP.md`
Чек-листы по 4 фазам с галочками `- [ ]`. Каждый пункт — конкретное действие с привязкой к файлам и инструментам. Не «улучшить тесты», а «добавить vitest и 3 теста на `src/auth/oauth.ts`».

### 3. `.github/workflows/ci.yml`
Готовый Phase 0 workflow для этого проекта. Все actions запиннены к актуальному SHA с комментарием версии. Permissions минимальны. Concurrency настроен. Включает только то, что **точно не упадёт** на пустом месте — typecheck/lint/build только если они уже работают локально.

## Этап 6. Сверка

После генерации артефактов проверь себя по чек-листу:

- [ ] Каждое предложение имеет привязку к найденному в коде риску, а не к абстракции
- [ ] Все third-party actions запиннены к SHA (`uses: owner/action@<40-char-sha> # vX.Y.Z`)
- [ ] Permissions явные и минимальные (`contents: read` дефолт)
- [ ] У каждого job есть `timeout-minutes`
- [ ] Есть `concurrency` group
- [ ] Lock-файлы проекта реально учтены в кэше setup-action
- [ ] Никаких `${{ github.event.* }}` напрямую в `run:` без quoting (script injection)
- [ ] Не предложен `trivy-action` без SHA-пина
- [ ] Phase 0 не содержит ничего, что может упасть на текущей кодовой базе
- [ ] У каждой Phase есть acceptance criteria и явный scope-out

## Принципы

1. **Привязывай к коду, не к моде.** «80% coverage» бессмысленно без контекста. «Тесты на `payment.ts` потому что туда ходят деньги» — осмысленно.
2. **SHA-пиннинг не опционален.** Это первая линия защиты от tj-actions-стиля атак. Major-теги — для собственных и официальных GitHub actions с осторожностью.
3. **Минимальные permissions всегда.** `contents: read` — дефолт, остальное — явно по job.
4. **Не доверяй полной репродукции описания.** Если рекомендуешь tool — приведи документированный пример его использования, не «обычно настраивают так».
5. **Не предлагай в Phase 0 ничего, чего сейчас нет в проекте локально.** CI должен начать с того, что уже работает, а не тащить новые тулзы.
6. **Помечай уверенность.** «Точно нашёл», «вероятно, имеется в виду», «не проверено — нужен ручной осмотр».

## Стоп-сигналы

- Не переходи к Этапу 3 без согласования рисков на Этапе 2
- Не пиши финальные артефакты, пока пользователь не подтвердил roadmap
- Если репо больше ~500 файлов — сначала пройдись по корню и top-10 директориям, явно помечай непроверенное

## Источники для самопроверки (упоминай явно когда применимо)

- GitHub Docs: Security hardening for GitHub Actions, Secure use reference
- GitHub Blog: Actions 2026 Security Roadmap
- OpenSSF Scorecard
- StepSecurity Harden-Runner документация
- Wiz: Hardening GitHub Actions guide
- zizmor audits documentation
