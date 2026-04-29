# Phase 4 — Security & Dependencies

**Цель:** найти уязвимости, утечки, плохие практики безопасности, проблемы с зависимостями.

**Длительность:** 1.5–2 часа.

**Опора на источники:**
- OWASP Top 10 (web application).
- OWASP Cheat Sheet Series — особенно DOM-based XSS, CSP, JWT.
- Snyk and GitHub security advisories.
- Mozilla Web Security guidelines.
- *Securing DevOps* — Julien Vehent.

---

## Инструменты

- `npm audit` / `pnpm audit` / `yarn audit` — известные уязвимости.
- `npx better-npm-audit` — игнорирует ложноположительные.
- `npx depcheck` — неиспользуемые зависимости.
- `npx npm-check-updates` — устаревшие пакеты.
- `npx license-checker` — лицензии.
- **Socket.dev** или **Snyk** (если доступно) — supply chain risks.
- **OWASP ZAP** или **Burp Suite Community** (опционально) — динамическое сканирование.
- **Mozilla Observatory** (`https://observatory.mozilla.org`) — заголовки безопасности.
- **securityheaders.com** — заголовки безопасности.
- **Serena** — поиск опасных паттернов в коде (innerHTML, eval, dangerouslySetInnerHTML).
- **GitNexus** — поиск истории секретов в коммитах (если когда-то коммитили токен).
- **Claude Code** — оркестрация.

---

## Чек-лист

### 4.1 Зависимости — известные CVE

- [ ] `npm audit --production` — продакшн зависимости (важнее).
- [ ] `npm audit` (полное) — включая dev.
- [ ] Зафиксировать: critical / high / moderate / low.
- [ ] Для каждой critical/high — есть ли fix в новой версии? Major bump?
- [ ] Транзитивные уязвимости — кто их тянет? (`npm ls <vulnerable-pkg>`).

### 4.2 Зависимости — гигиена

- [ ] `npx depcheck` — неиспользуемые зависимости (засоряют bundle, расширяют поверхность атаки).
- [ ] `npx npm-check-updates` — устаревшие. Обратить внимание на пакеты с major version отставанием.
- [ ] Заброшенные пакеты — последний релиз >2 лет, мало звёзд, мало поддержки. Особенно если это что-то критичное.
- [ ] Дубли версий одной библиотеки (`npm ls <pkg>`).

### 4.3 Lockfile

- [ ] Lockfile (package-lock.json / yarn.lock / pnpm-lock.yaml) закоммичен и актуален?
- [ ] CI использует `npm ci` (точно по lockfile), а не `npm install`?
- [ ] Один lockfile в репо (нет конфликтующих от разных package manager'ов).

### 4.4 Лицензии

- [ ] `npx license-checker --summary` — все лицензии совместимы с твоим использованием?
- [ ] GPL/AGPL в зависимостях — если коммерческий проект, это риск.

### 4.5 Supply chain

- [ ] Скрипты `postinstall`, `preinstall` в зависимостях — проверить топ-50 (или хотя бы знать что они есть).
- [ ] Если есть, рассмотреть `--ignore-scripts` в CI.
- [ ] Откуда берутся пакеты — npm registry (стандарт), или есть приватные registry/git-зависимости?

### 4.6 Секреты в коде

- [ ] `git log --all -p | grep -iE "(api[_-]?key|secret|token|password|aws_access)"` — ручной поиск (или установить `gitleaks`/`trufflehog`).
- [ ] Через GitNexus — посмотреть историю файлов `.env`, `config.*`, всё что может содержать секреты.
- [ ] `.env*` файлы не закоммичены (`.gitignore`).
- [ ] Хардкоженных API-ключей нет в коде (Serena find_symbol по подозрительным именам, regex на токены).

### 4.7 Переменные окружения

- [ ] Что в `process.env.NEXT_PUBLIC_*` — это публично, не секреты!
- [ ] `.env.example` есть, документирует все переменные.
- [ ] Для каждой переменной — где задаётся (Vercel/Docker/CI), как ротируется.

### 4.8 XSS и небезопасный HTML

Через Serena ищем:
- [ ] `dangerouslySetInnerHTML` — каждое использование оправдано? Контент санитизируется?
- [ ] `innerHTML =` — антипаттерн в React, искать в legacy коде.
- [ ] `eval(`, `new Function(`, `setTimeout('strings')` — недопустимо.
- [ ] User-input → DOM без санитизации (особенно в WYSIWYG, Markdown-рендеринге).
- [ ] DOMPurify используется где нужна санитизация HTML?

### 4.9 Authentication / Authorization (если применимо)

- [ ] JWT в localStorage — антипаттерн (XSS-уязвимо). Должно быть в httpOnly cookie.
- [ ] Срок жизни токенов разумный?
- [ ] Refresh token rotation?
- [ ] Auth0 / NextAuth / Clerk / своё решение — соответствует best practices?
- [ ] CSRF защита на изменяющих запросах (если используется cookie-based auth).

### 4.10 Заголовки безопасности

Проверить через `securityheaders.com` или curl:

- [ ] `Content-Security-Policy` — есть, не `unsafe-inline`/`unsafe-eval` без причин.
- [ ] `Strict-Transport-Security` (HSTS).
- [ ] `X-Content-Type-Options: nosniff`.
- [ ] `X-Frame-Options: DENY` или CSP frame-ancestors.
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`.
- [ ] `Permissions-Policy` — отключены ненужные API (camera, microphone, geolocation).

### 4.11 CORS

- [ ] Если есть свои API — CORS настроен на whitelist origins, а не `*` (если не публичный API).
- [ ] Credentials передаются с CORS осознанно.

### 4.12 Внешние скрипты и iframe'ы

- [ ] Сторонние скрипты — Subresource Integrity (SRI) для критичных?
- [ ] iframe'ы — `sandbox` атрибут?
- [ ] Загружаемые user-uploaded файлы — где хранятся, какие типы разрешены?

### 4.13 Логирование и приватность

- [ ] Логирование на клиенте — не логируются ли пароли, токены, PII?
- [ ] GDPR / 152-ФЗ (для RU) — cookie consent, политика конфиденциальности.
- [ ] Аналитика — анонимизация IP, opt-out?

### 4.14 Конфигурация Next.js / build

- [ ] `next.config.js`: `poweredByHeader: false`, headers() настроены, redirects() корректны.
- [ ] `productionBrowserSourceMaps` — обычно false (не отдавать исходники).
- [ ] Не отдаются ли source maps в проде через CDN?

---

## Шаблон отчёта `reports/05-security-deps-report.md`

```markdown
# Security & Dependencies Report

## Audit summary
- npm audit (production):
  - critical: 0
  - high: 2
  - moderate: 7
  - low: 12
- depcheck unused: 8 packages
- outdated (major behind): 14 packages
- unique dependencies: 312 (dev: 187, prod: 125)

## Critical / high vulnerabilities

### SEC-001 (high) — react-syntax-highlighter < 15.x
- Vector: Prototype pollution
- CVE: CVE-2024-XXXXX
- Path: app → react-syntax-highlighter@14.0.1
- Fix: bump to 15.5.0 (major, breaking)
- Effort: S

[...]

## Secrets check
- gitleaks: 0 findings (good)
- .env in .gitignore: yes
- hardcoded keys найдены в:
  - src/lib/analytics.ts:14 (Yandex Metrica ID — это публичный, не секрет)
  - но src/lib/payment.ts:8 содержит test API key — переместить в env

## Headers (Mozilla Observatory: B+)
- CSP: missing → SEC-005 high
- HSTS: present
- X-Content-Type-Options: present
- Referrer-Policy: missing → SEC-006 medium
- Permissions-Policy: missing → SEC-007 medium

## Code patterns
- dangerouslySetInnerHTML: 4 использования
  - 3 безопасных (статический HTML из MDX)
  - 1 рисковое: src/components/Comment.tsx — рендерит user input без DOMPurify → SEC-002 critical

## Auth
- Token хранится в localStorage → SEC-003 high
- Refresh rotation: нет → SEC-004 medium

## Findings
[в findings.json]
```

---

## Промпт для Claude Code

```
Phase 4 — Security & Dependencies.

План:
1. Запусти npm audit (или pnpm/yarn эквивалент). Production-only и полный. Зафиксируй уязвимости.
2. Запусти depcheck, npm-check-updates, license-checker.
3. Через Serena:
   - найди все dangerouslySetInnerHTML, eval, innerHTML
   - найди все process.env.* — выпиши какие используются
   - найди все вызовы fetch/axios — нет ли хардкоженых эндпоинтов с креденшелами в URL
4. Через GitNexus:
   - проверь историю изменений .env, .npmrc, любых config-файлов
   - был ли когда-то .env закоммичен (и потом удалён)
5. Если сайт развёрнут — проверь через securityheaders.com или curl основные заголовки.
6. Проверь .gitignore на корректность.
7. Заполни reports/05-security-deps-report.md.
8. Допиши findings.json.

Severity:
- critical: эксплуатируемые уязвимости в проде, утечка секретов, XSS на user input
- high: уязвимости deps без exploit'а, отсутствие CSP, JWT в localStorage
- medium: устаревшие пакеты с патчами, missing Referrer-Policy
- low: gigиена

Замечания:
- Не паникуй из-за npm audit ложноположительных в dev-зависимостях. Уточни exploitability.
- Для каждого fix'а: бамп версии, патч, или alt пакет.
```
