# Phase 07 — Security (OWASP Top 10 + ASVS L1-L2)

> **Цель:** OWASP Top 10 + ASVS L1-L2 чек-лист, не «попутно».
>
> **Источники:** OWASP Top 10 (2021) · OWASP ASVS 4.0 L1-L2 · 12factor §3 (Config).

## Inputs

- `reports/02-recon.md` — стек, internal/external boundaries.
- `reports/03-deterministic.md` — `npm audit`, secrets-grep.
- `reports/04-hotspots.md` — top auth/crypto-related hot-spots.
- `reports/raw/mcp-context.json` — есть ли serena/gitnexus.

## Outputs

- `nodejs-audit/reports/07-security.md`
- `nodejs-audit/reports/raw/sec-*.log` — по одному per category.

## Шаги — по категориям OWASP

### A01 Broken Access Control

```bash
# эндпоинты без auth middleware
grep -rEn "(app|router|fastify|hono)\.(get|post|put|delete|patch)\(" <src> --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-endpoints.log

# Cabinet/admin owner derivation
grep -rEn "body\.user_id|query\.user_id|params\.user_id" <src> 2>/dev/null
```

**Если есть serena** — `find_referencing_symbols` для middleware-функций (`requireAuth`, `requireSession`, etc.) — точно увидишь, какие endpoints **не** покрыты auth.

### A02 Cryptographic Failures

```bash
# слабая криптография
grep -rEn "md5|sha1\(|createHash\(['\"](md5|sha1)" <src> 2>/dev/null \
  > reports/raw/sec-weak-crypto.log

# сильная (для подтверждения, что есть)
grep -rEn "bcrypt|argon2|scrypt|@node-rs" <src> 2>/dev/null \
  > reports/raw/sec-strong-crypto.log

# secret reuse — один и тот же env var в разных ролях
grep -rEn "env\.(api\.)?internalSecret|env\.jwtSecret|JWT_SECRET|INTERNAL_SECRET" <src> 2>/dev/null \
  > reports/raw/sec-secret-reuse.log
```

**Если есть serena** — `find_referencing_symbols` для `crypto.createHash`, `jwt.sign` — точное число использований.

**ASVS V2 (Auth) + V6 (Crypto):**
- V2.1.1 — пароли через bcrypt/argon2/scrypt? (минимум L1)
- V6.2.3 — секреты через env, не в коде? (L1)
- V6.2.5 — секрет имеет одну роль? (L2 — ловит анти-паттерн «один INTERNAL_SECRET для JWT и для x-internal-secret»)

### A03 Injection

```bash
# SQL injection
grep -rEn 'query\(.*\$\{|\$queryRaw\(.*\$\{|raw\(.*\$\{' <src> --include="*.ts" 2>/dev/null \
  > reports/raw/sec-sqli.log

# XSS
grep -rEn "dangerouslySetInnerHTML|innerHTML\s*=|v-html" <src> 2>/dev/null \
  > reports/raw/sec-xss.log

# Command injection
grep -rEn "child_process|exec\(|execSync\(|spawn\(" <src> --include="*.ts" --include="*.js" 2>/dev/null \
  > reports/raw/sec-cmd.log
```

Для каждого XSS-хита проверь — обёрнуто ли в DOMPurify/sanitizer. Для каждого `exec` — есть ли user-input concat.

### A04 Insecure Design

- Idempotency keys для денежных операций — ищи термины `idempotency`, `idempotent`, `unique constraint`.
- Rate limiting — есть ли (см. phase-03)?
- Worker shutdown seam — известный паттерн для job-based проектов: между deduction и refund SIGTERM может потерять баланс. Если есть BullMQ/Bull/Sidekiq-like — отметь.

### A05 Security Misconfiguration

```bash
# CORS *
grep -rEn "Access-Control-Allow-Origin.*\\*|origin:.*['\"]\\*['\"]" <src> 2>/dev/null \
  > reports/raw/sec-cors.log

# Helmet / security headers
grep -rEn "helmet\(\)|@fastify/helmet" <src> package.json 2>/dev/null \
  > reports/raw/sec-helmet.log

# Stack traces в response
grep -rEn "err\.stack|error\.stack" <src> --include="*.ts" 2>/dev/null \
  | grep -E "reply\.send|res\.send|res\.json" \
  > reports/raw/sec-stack.log
```

### A06 Vulnerable Components

Из `reports/raw/audit.json` (phase-03) — counts по severity.

### A07 Authentication Failures

```bash
# JWT
grep -rEn "jwt\.sign|jsonwebtoken|expiresIn" <src> 2>/dev/null > reports/raw/sec-jwt.log
```

Проверь:
- TTL JWT — какой?
- Где хранится refresh token?
- Один ли секрет для JWT и для других ролей?

### A08 Software & Data Integrity

- Webhook signature verification — для каждого incoming webhook (payment, telegram, …).
- Raw body preservation — критично для HMAC.

### A09 Security Logging Failures

```bash
# PII/secrets в логах
grep -rEn "log.*req\\.body|log\\.(info|error)\\(.*password|log.*token|log.*secret" <src> 2>/dev/null \
  > reports/raw/sec-pii.log
```

### A10 SSRF

```bash
# fetch/axios с user-controlled URL
grep -rEn "(fetch|axios\\.get|axios\\.post)\\([^)]*req\\." <src> --include="*.ts" 2>/dev/null \
  > reports/raw/sec-ssrf.log

# private CIDR validation присутствует?
grep -rEn "10\\.0\\.0\\.0/8|172\\.16\\.0\\.0|192\\.168\\.0\\.0" <src> --include="*.ts" 2>/dev/null \
  > reports/raw/sec-ssrf-guard.log
```

### Secrets в git

```bash
git ls-files | grep -E "^\\.env(\\..+)?$" | grep -v "example\\|sample" \
  > reports/raw/sec-env-in-git.log || true
```

## Шаблон отчёта `07-security.md`

```markdown
# Security audit (OWASP Top 10 + ASVS L1-L2)

## TL;DR
[Один абзац: безопасен ли код, есть ли критичные находки.]

## Сводка findings

| ID | Категория | Серьёзность | ASVS | Файл |
|----|-----------|-------------|------|------|
| SEC-001 | A03 SQLi | Critical | V5.3.4 | src/X.ts:45 |

## OWASP Top 10 — статус

### A01 Broken Access Control: ✅/⚠️/❌
[Что проверил, что нашёл]

### A02 Cryptographic Failures: ...
- ASVS V2.1.1: ✅/❌
- ASVS V6.2.3: ✅/❌
- ASVS V6.2.5 (secret-per-role): ✅/❌

### A03 Injection
- SQLi: <count>
- XSS: <count> (sanitized: yes/no)
- Command injection: <count>

### A04 Insecure Design
- Idempotency keys: ✅/❌
- Rate limiting: ✅/❌
- Worker-shutdown seam: <если применимо>

### A05 Security Misconfiguration
- CORS *: ✅/❌
- Helmet: ✅/❌
- Stack-traces в response: ✅/❌

### A06 Vulnerable Components
[Из npm audit]

### A07 Authentication Failures
- JWT TTL: ...
- Secret reuse: <yes/no — критичный анти-паттерн>

### A08 Software/Data Integrity
- Webhook signature verification: ✅/❌
- Raw body preserved before parsing: ✅/❌

### A09 Logging Failures
- PII redaction: ✅/❌

### A10 SSRF
- Private-CIDR guard: ✅/❌

## Findings (детально)

### SEC-001: <название>
**Категория:** A0X
**Серьёзность:** Critical / High / Medium / Low
**ASVS:** V<X.Y.Z>
**Файл:** ...
**Уязвимый код:**
\```
[код]
\```
**Как чинить:**
\```
[код]
\```

### ... остальные

## Готовые промты для фиксов
[Промты для critical/high — будут собраны в QUICK-WINS.md в phase-12]
```

## Критерии завершения

- `reports/07-security.md` существует.

## Сигналы в чат

- Старт: `[PHASE 07] STARTED — Security (OWASP + ASVS)`
- Конец: `[PHASE 07] DONE — reports/07-security.md`

→ Переход к **phase-08-performance.md**.
