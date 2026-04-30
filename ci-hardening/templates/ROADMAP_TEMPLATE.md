# CI/CD Roadmap (2026 baseline)

Шаблон. Заполняется AI после прогона `AUDIT_PROMPT.md`. Каждая фаза — отдельный PR.

> **Backbone этого плана** — рекомендации [GitHub Security Hardening for Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions), [GitHub Actions 2026 Security Roadmap](https://github.blog/news-insights/product-news/whats-coming-to-our-github-actions-2026-security-roadmap/), и lessons learned из публичных incident reports (tj-actions, trivy-action, axios, bitwarden/cli).

---

## Phase 0 — Foundation (полдня — день)

**Цель:** базовый CI, который не должен ломать существующий процесс.

### Действия

- [ ] Скопировать `.github/workflows/ci.yml` из `audit-kit/`
- [ ] **Перепиннить все actions к актуальным SHA** (см. [pinact](https://github.com/suzuki-shunsuke/pinact)):
  ```bash
  # Установка
  go install github.com/suzuki-shunsuke/pinact/v3/cmd/pinact@latest
  # Прогон
  pinact run
  ```
- [ ] Убедиться, что `permissions: contents: read` стоит на уровне workflow
- [ ] Убедиться, что у каждого job есть `timeout-minutes`
- [ ] Убедиться, что есть `concurrency` с `cancel-in-progress`
- [ ] Локально проверить что `typecheck`/`lint`/`build` команды работают
- [ ] Первый зелёный запуск в Actions

### Acceptance criteria

- PR в main триггерит CI, все джобы зелёные или skipped
- Время CI на типичный PR < 5 минут
- Никаких новых требований к разработчикам пока что
- Все third-party actions запиннены к 40-char SHA с комментарием версии

### Scope-out

Не делаем в Phase 0:
- ❌ Тесты в CI (Phase 1)
- ❌ Branch protection rules (Phase 1)
- ❌ Security блокировки (Phase 1-2)
- ❌ Coverage thresholds (Phase 2)

---

## Phase 1 — Safety Net (1-3 дня)

**Цель:** базовая защита от очевидных утечек, supply-chain атак и регрессий.

### Действия

#### Тесты в CI
- [ ] Включить тесты в `ci.yml` (раскомментировать соответствующий job)
- [ ] Добавить хотя бы 3 теста на самые критичные пути если их нет

#### Dependency management
- [ ] Скопировать `.github/dependabot.yml` из `audit-kit/`
- [ ] Альтернатива: установить Renovate App + скопировать `templates/renovate.json` в корень репо
- [ ] Включить Dependabot security alerts: Settings → Code security → Dependabot alerts

#### Secret scanning
- [ ] Включить GitHub secret scanning: Settings → Code security → Secret scanning (бесплатно для public, GHAS для private)
- [ ] Прогнать gitleaks/trufflehog по всей истории (workflow `secret-scan` уже в ci.yml)
- [ ] Если найдены секреты:
  - Ротировать их в первую очередь
  - Удалить из истории через `git-filter-repo` или [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
  - Force-push (с уведомлением команды)

#### Runtime monitoring
- [ ] Harden-Runner в audit mode уже включён в `ci.yml`
- [ ] После 1-2 недель посмотреть [insights](https://app.stepsecurity.io) и собрать baseline egress
- [ ] Собрать список доменов, к которым CI ходит легитимно

#### Workflow security
- [ ] Прогнать [zizmor](https://woodruffw.github.io/zizmor/) локально и пофиксить findings:
  ```bash
  pip install zizmor
  zizmor .
  ```
- [ ] Добавить workflow `pinact.yml` для проверки SHA-пинов на PR

#### Branch protection
- [ ] Включить branch protection на main:
  - Require pull request before merging
  - Require approvals: 1 (или 0 для соло-проекта, но всё равно через PR)
  - Require status checks to pass: `CI Success`
  - Require linear history (опционально, но улучшает читаемость истории)
  - Do not allow bypassing (даже для админов, для соло — оставить bypass для себя)

### Acceptance criteria

- PR с упавшим CI или без апрува не мержится в main
- Новые версии зависимостей и actions приходят PR-ами автоматически
- Видны egress-логи Harden-Runner за последнюю неделю
- Известные секреты удалены из истории и ротированы
- zizmor проходит без critical findings

### Scope-out

- ❌ Coverage thresholds (Phase 2)
- ❌ SAST (Phase 2)
- ❌ Conventional commits enforcement (Phase 2)

---

## Phase 2 — Quality Gates (неделя)

**Цель:** поддержание качества при росте кодовой базы. Ужесточение security-rails.

### Действия

#### SAST
- [ ] Скопировать `.github/workflows/codeql.yml`
- [ ] Включить только релевантные языки в matrix
- [ ] Альтернатива: Settings → Code security → "Default setup" для CodeQL (проще, меньше контроля)
- [ ] Прогнать первый full scan, разгрести existing findings (приоритизировать high/critical)

#### Coverage
- [ ] Замерить текущий coverage локально
- [ ] Установить threshold = текущее значение (ratchet, не задирать сразу)
- [ ] Подключить [codecov](https://about.codecov.io/) или [coveralls](https://coveralls.io/) для PR-комментариев
- [ ] Постепенно поднимать threshold, не более 5% за раз

#### Conventional commits
- [ ] PR title check уже включён в `ci.yml` (warn-only)
- [ ] Через 2 недели после Phase 1 убрать `continue-on-error: true` — сделать blocking
- [ ] Опционально: commitlint для всех коммитов в PR

#### Repo metadata
- [ ] Скопировать `.github/pull_request_template.md`
- [ ] Скопировать `.github/ISSUE_TEMPLATE/*.yml`
- [ ] Скопировать `SECURITY.md`
- [ ] Создать `.github/CODEOWNERS` если команда > 2

#### Tighten security
- [ ] Убрать `continue-on-error: true` с `gitleaks` — сделать blocking
- [ ] Pinact из warn-only сделать blocking (когда все actions уже мигрированы)
- [ ] Если используется cloud-deploy: мигрировать на OIDC
  - [AWS OIDC setup](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services)
  - [Azure OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure)
  - [GCP OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-google-cloud-platform)
  - Удалить long-lived AWS_ACCESS_KEY_ID и аналоги из секретов

#### Documentation hygiene
- [ ] Добавить `.github/workflows/links.yml` с lychee для проверки markdown-ссылок (опционально)
- [ ] Добавить typos для проверки опечаток в документации (опционально)

### Acceptance criteria

- Coverage не падает PR-за-PR (ratchet работает)
- Все third-party actions запиннены к SHA, pinact passes
- Long-lived cloud credentials удалены из секретов (если применимо)
- CodeQL проходит без новых high/critical findings
- Conventional commits enforced в PR titles

### Scope-out

- ❌ Preview-окружения (Phase 3)
- ❌ Performance budgets (Phase 3)
- ❌ Container signing / SBOM (Phase 3)

---

## Phase 3 — Advanced (только при наличии конкретного кейса)

**Цель:** инкрементальные улучшения для зрелого проекта. Каждый пункт = отдельный PR с обоснованием.

### Кандидаты на внедрение

#### Supply chain (продвинутое)
- [ ] Harden-Runner перевести из `audit` в `block` mode с allowlist (после ≥2 недель audit baseline)
- [ ] [`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance) для подписи артефактов
- [ ] SBOM через [syft](https://github.com/anchore/syft) или `attest-sbom`
- [ ] Container signing через [cosign](https://github.com/sigstore/cosign)
- [ ] Включить OpenSSF Scorecard (`scorecard.yml` уже в audit-kit, для public repos)

#### Performance & DX
- [ ] Bundle size budget ([size-limit](https://github.com/ai/size-limit))
- [ ] [Lighthouse CI](https://github.com/GoogleChrome/lighthouse-ci) для веб-приложений
- [ ] Performance regression tests (vitest bench)
- [ ] Self-hosted runners через [actions-runner-controller](https://github.com/actions/actions-runner-controller) если упёрлись в лимиты

#### Деплой и релизы
- [ ] Preview-окружения для PR (Vercel/Netlify Deploy Preview, или собственный k8s preview)
- [ ] Smoke tests после deploy
- [ ] Automated changelog ([release-please](https://github.com/googleapis/release-please) / [changesets](https://github.com/changesets/changesets) / [semantic-release](https://github.com/semantic-release/semantic-release))
- [ ] Environment protection rules с required reviewers для prod
- [ ] Rollback automation

#### Тестирование (продвинутое)
- [ ] E2E в матрице (OS × browsers × Node versions)
- [ ] Mutation testing ([Stryker](https://stryker-mutator.io/) / [mutmut](https://github.com/boxed/mutmut))
- [ ] Integration tests с реальными сервисами через service containers

#### Observability
- [ ] Datadog CI Visibility / Foresight / GitHub Actions Insights для метрик
- [ ] Error tracking интеграция (Sentry, Bugsnag) с release-tagging

#### Tooling
- [ ] Reusable workflows для нескольких репо организации
- [ ] [Renovate](https://docs.renovatebot.com/) вместо Dependabot для более тонкого контроля
- [ ] Автоматический changelog генерация на релизе

### Принцип Phase 3

Каждый пункт включается **только когда есть документированный кейс**, который этот пункт решает. Не добавляй ради галочки. Лучше 3 работающих advanced проверки, чем 15 формальных.

---

## Анти-паттерны (чего избегаем всегда)

- ❌ CI длиной > 10 минут на типичном PR — рубит итерационную скорость
- ❌ Постоянно красные/жёлтые проверки, которые все игнорят — хуже отсутствия CI
- ❌ Линтер с 500 правилами «потому что в гайде так» — копится сопротивление
- ❌ Coverage 80% threshold на проекте, где сейчас 12% — ratchet вверх, не bottom-up
- ❌ Внедрение всех 4 фаз одним PR — 100% будут проблемы и откат
- ❌ Использование mutable refs (`@v4`, `@main`) для third-party actions — главный supply-chain риск
- ❌ `pull_request_target` без чёткого понимания — самая частая дыра в OSS-репах
- ❌ Установка trivy-action, gh-actions-from-untrusted-orgs — каждое такое решение это компромисс safety vs convenience

---

## Команды быстрого старта

### Установка core security tools локально

```bash
# pinact — pin actions to SHA
go install github.com/suzuki-shunsuke/pinact/v3/cmd/pinact@latest
pinact run

# zizmor — workflow security linter
pip install zizmor
zizmor .

# gitleaks — local secret scan
brew install gitleaks  # или curl install
gitleaks detect --no-git --source .
```

### Чек-лист готовности к Phase 0

- [ ] `git status` чистый
- [ ] Локально работает: `npm test`, `npm run build`, `npm run lint`, `npm run typecheck` (или эквиваленты)
- [ ] Нет hardcoded секретов в новом коде
- [ ] `.gitignore` содержит `.env*`, `node_modules`, build artefacts

### Что измерять

После Phase 1, раз в спринт смотри в Actions Insights:
- **Время выполнения** — растёт ли? Почему?
- **Failure rate** — флаки или реальные проблемы?
- **Cost minutes** — особенно для приватных репо на Free/Pro tier
- **Cache hit rate** — если low, кэш настроен неоптимально
