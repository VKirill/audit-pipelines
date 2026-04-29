# PHASE 06 — SECURITY (v2)

**Цель:** Найти уязвимости и плохие практики безопасности. Секреты, инъекции, auth, crypto, supply-chain (дополнение к фазе 03).

**Источники:**
- OWASP Top 10 (актуальная редакция).
- OWASP ASVS (Application Security Verification Standard).
- McGraw, *Software Security: Building Security In* — 7 touchpoints.
- CWE Top 25.

**Exit gate этой фазы:**
- **≥ 5 findings** для M-проекта (если меньше — явный раздел «Проверено и чисто» с перечислением OWASP-пунктов, которые **действительно** чистые с цитатами);
- **обязательно**: полный проход OWASP Top 10 с явной отметкой «найдено/чисто/не применимо» для каждого пункта;
- **обязательно**: route-by-route AuthN/AuthZ review для ВСЕХ эндпоинтов публичного слоя (или перечисление проверенных семплов с обоснованием для L+);
- минимум 2 файла в `audit/evidence/06_security/`: `owasp_checklist.md` + `auth_coverage.md` (+ `secret_scan.txt` если были попадания);
- ≥ 200 строк в отчёте (тема критичная, подробно).

**Напоминание о confidence:** `critical` ставь только при прямом подтверждении (секрет в plaintext, эксплуатируемая инъекция с трассой), не при подозрении.

---

## 1. Входы
- Фаза 03 — supply chain.
- Фаза 01 — список роутов/эндпоинтов.
- Фаза 02 — cross-cutting concerns (auth централизован или нет).

---

## 2. Чек-лист проверок

### 2.1. Секреты в коде (CWE-798, CWE-540)

**Паттерны для grep** (экранирование сохранить):

```bash
# Явные ключи
grep -rnE "-----BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----" <src>
grep -rnE "AKIA[0-9A-Z]{16}" <src>                                           # AWS access key
grep -rnE "ASIA[0-9A-Z]{16}" <src>                                           # AWS temp key
grep -rnE "aws_secret_access_key\s*[:=]\s*['\"][^'\"]{40}['\"]" <src>
grep -rnE "ghp_[A-Za-z0-9]{36}" <src>                                        # GitHub PAT
grep -rnE "github_pat_[A-Za-z0-9_]{82}" <src>
grep -rnE "gho_[A-Za-z0-9]{36}" <src>
grep -rnE "sk-[A-Za-z0-9]{20,}" <src>                                        # OpenAI/Anthropic-like
grep -rnE "sk-ant-[A-Za-z0-9_-]{40,}" <src>
grep -rnE "xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+" <src>                            # Slack bot
grep -rnE "eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}" <src>  # JWT

# Generic
grep -rniE "(api[-_]?key|apikey|secret|token|password|passwd|pwd)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{16,}['\"]" <src>
grep -rniE "bearer\s+[A-Za-z0-9_\-.]{20,}" <src>

# Private CA/SSH
grep -rnE "ssh-rsa\s+AAAA[A-Za-z0-9+/=]{100,}" <src>

# Google service account markers (часто в JSON)
grep -rnE "\"type\":\s*\"service_account\"" <src>
grep -rnE "\"private_key\":\s*\"-----BEGIN" <src>
```

- [ ] Каждый матч → проверить: placeholder (`xxxx`, `REPLACE_ME`, `your-api-key-here`, `<...>`) или реальный?
- [ ] Реальный → finding `critical`: location, тип, рекомендация (ротация + `git filter-repo`/BFG для истории).
- [ ] Если есть `trufflehog` / `gitleaks` — запусти:
  ```bash
  gitleaks detect --source . --report-format json \
    --report-path audit/evidence/06_security/gitleaks.json --no-banner
  trufflehog filesystem . --json > audit/evidence/06_security/trufflehog.json
  ```
- [ ] **Проверь историю git**:
  ```bash
  git log -p --all | grep -E "(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|BEGIN.*PRIVATE KEY)" | head -30
  ```
- [ ] Любое попадание секрета в **историю** → `critical`, даже если удалён в HEAD.
- [ ] Сохрани сводку в `audit/evidence/06_security/secret_scan.txt`.

### 2.2. Injection (CWE-89, CWE-78, CWE-79, CWE-94)

#### SQL injection
- [ ] grep строковой конкатенации в SQL:
  ```bash
  grep -rnE "\"(SELECT|INSERT|UPDATE|DELETE).+\"\s*\+" <src>
  grep -rnE "f\"(SELECT|INSERT|UPDATE|DELETE).+\{" --include="*.py" <src>
  grep -rnE "\`(SELECT|INSERT|UPDATE|DELETE).+\\\$\{" --include="*.ts" --include="*.js" <src>
  ```
- [ ] Проверь каждый матч: user input без параметризации? → finding `critical` (прямой путь), `high` (непонятно), `info` (через ORM/builder).

#### Command injection
- [ ] `subprocess.*shell=True`, `os.system(`, `Runtime.exec(`, `child_process.exec(`, `exec.Command(...)` с конкатенацией пользовательских данных.
- [ ] Любой `eval(`, `new Function(`, `exec(` на user input → `critical` или `high`.

#### XSS (для фронта)
- [ ] React `dangerouslySetInnerHTML`, Vue `v-html`, `innerHTML =` с не-константой → `high`.
- [ ] Шаблонизаторы server-side с отключенным escaping: `{% autoescape false %}`, `{!! $var !!}` (Laravel), `String.raw` в JS.

#### Path traversal
- [ ] `open(user_input)`, `fs.readFile(req.query.file)`, `path.join(root, req.params.path)` без проверки `../`.

#### Template injection
- [ ] Сквозной user input в шаблоны Jinja/ERB/Thymeleaf без строгого escaping.

### 2.3. Authentication — ОБЯЗАТЕЛЬНЫЙ route-by-route review

- [ ] Возьми полный список роутов из фазы 01 (HTTP endpoints).
- [ ] Для **каждого** роута (для L+ — ≥ 80% случайной выборки) заполни таблицу:

  | Метод | Путь | Handler | Auth middleware | Тип auth | Чувствительность | Риск |
  |-------|------|---------|-----------------|----------|------------------|------|
  | POST | `/api/admin/login` | `login.post.ts` | ❌ нет (это login) | — | high | ok |
  | GET | `/api/admin/users` | `users.get.ts` | ✅ `requireAdminSession` | cookie | high | ok |
  | POST | `/api/public/upload` | `upload.post.ts` | ❌ | — | medium | **risk** |

- [ ] Сохрани в `audit/evidence/06_security/auth_coverage.md`.
- [ ] Каждый роут без auth с non-public контекстом → finding `high` (если sensitive data) или `medium`.
- [ ] Admin-роуты (содержат `admin`, `internal`, `debug`) без двухуровневой защиты → `high`.

### 2.4. Auth implementation details

- [ ] JWT:
  - `alg: none` разрешён? → `critical`.
  - `jwt.decode(...)` без verify → `critical`.
  - Timing-safe сравнение подписей? → поиск `timingSafeEqual`, `constant_time_compare`. Отсутствие → `medium`.
- [ ] Пароли — хранение:
  - `bcrypt`, `argon2`, `scrypt`, `PBKDF2` — хорошо.
  - `md5`, `sha1`, `sha256` без соли → `critical`.
  - Plaintext в БД миграциях → `critical`.
- [ ] Session fixation: session ID генерируется до authenticate и не регенерируется после login → `medium`.
- [ ] **Shared password / single-account admin auth** — finding `high` (нет audit trail, нет per-user accountability).
- [ ] HMAC signature validation (webhooks, Telegram auth) — используется ли `timingSafeEqual`? Без неё — `medium` (timing attack).

### 2.5. Authorization (access control) — CWE-285

- [ ] IDOR (insecure direct object reference): эндпоинты `/users/{id}` без проверки, что запрос от владельца или админа.
- [ ] Через GitNexus `context` / ручное чтение handler'ов — вызывается ли ACL/policy-функция?
- [ ] Отсутствие → `high`.

### 2.6. Cryptography

- [ ] Слабые алгоритмы: `DES`, `3DES`, `RC4`, `MD5`, `SHA1` для integrity → `high`.
- [ ] `ECB` режим block cipher → `high`.
- [ ] Хардкоженый IV, salt, key → `critical`.
- [ ] `Math.random()` / `random.random()` для токенов/ID → `high` (должно быть CSPRNG: `secrets`, `crypto.randomBytes`).

### 2.7. TLS / HTTPS

- [ ] `verify=False` (Python `requests`), `rejectUnauthorized: false` (Node) → `high`.
- [ ] `TrustManager` trust-all в Java, `InsecureSkipVerify: true` в Go → `high`.

### 2.8. CORS / CSRF

- [ ] `Access-Control-Allow-Origin: *` + `Allow-Credentials: true` → `high`.
- [ ] Отсутствие CSRF-защиты на state-changing эндпоинтах (cookies-based модель) → `medium`/`high`.

### 2.9. Input validation

- [ ] Используются ли схемы (Pydantic, Zod, Joi, class-validator, JSON Schema)?
- [ ] Центральные публичные API без схемы → finding `medium`.
- [ ] Глубина / размер запроса ограничены? (body-parser limit, max depth для GraphQL) → `medium` при отсутствии.

### 2.10. Deserialization (CWE-502)

- [ ] `pickle.loads(`, `yaml.load(` (без `SafeLoader`), `ObjectInputStream.readObject(`, `Unmarshal` с типами от user → `high`/`critical`.

### 2.11. Logging sensitive data

- [ ] grep:
  ```bash
  grep -rnE "(logger\.|console\.log|print\().*?(password|token|secret|credit|cvv|ssn)" <src>
  ```
- [ ] Finding `high` — пересекается с GDPR/PCI-DSS.

### 2.12. Hardcoded IPs / URLs / connection strings

- [ ] grep:
  ```bash
  grep -rnE "(mongodb|postgres|mysql|redis|amqp)://[^\s\"']+" <src>
  grep -rnE "jdbc:[^\s\"']+" <src>
  grep -rnE "(https?://)[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" <src>
  ```
- [ ] С credentials в URL (`://user:pass@`) → `high`.
- [ ] Без credentials, но продакшен-хост в коде → `low`.

### 2.13. Docker/Compose/K8s

- [ ] `Dockerfile`: `USER root` (не сменён), `ADD` из внешних URL, `COPY . .` с секретами.
- [ ] `docker-compose.yml`: `privileged: true`, порты host networking.
- [ ] `k8s`: `privileged: true`, `hostPath`, отсутствие `runAsNonRoot`, `allowPrivilegeEscalation: true`.

### 2.14. CI secrets exposure

- [ ] `.github/workflows/*`, `.gitlab-ci.yml`:
  - `echo ${{ secrets.X }}` в логи → `high`.
  - Секреты в `env:` публичного PR workflow → `high`.
  - `pull_request_target` на untrusted forks без review → `high`.

### 2.15. ОБЯЗАТЕЛЬНО — OWASP Top 10 checklist

Явный чек-лист в `audit/evidence/06_security/owasp_checklist.md`:

| # | Категория | Статус | Проверено где | Findings |
|---|-----------|--------|---------------|----------|
| A01 | Broken Access Control | ⚠️ / ✅ / ❌ / N/A | route-by-route review + §2.5 | F-XXXX, F-YYYY |
| A02 | Cryptographic Failures | ⚠️ / ✅ / ❌ / N/A | §2.6, §2.7 | F-ZZZZ |
| A03 | Injection | ⚠️ / ✅ / ❌ / N/A | §2.2 | — |
| A04 | Insecure Design | ⚠️ / ✅ / ❌ / N/A | архитектурные notes | — |
| A05 | Security Misconfiguration | ⚠️ / ✅ / ❌ / N/A | §2.13, §2.14 | — |
| A06 | Vulnerable Components | ⚠️ / ✅ / ❌ / N/A | фаза 03 | F-XXXX |
| A07 | Identification and Auth Failures | ⚠️ / ✅ / ❌ / N/A | §2.3, §2.4 | — |
| A08 | Software and Data Integrity | ⚠️ / ✅ / ❌ / N/A | §2.10, CI | — |
| A09 | Security Logging / Monitoring | ⚠️ / ✅ / ❌ / N/A | §2.11, фаза 08 | — |
| A10 | SSRF | ⚠️ / ✅ / ❌ / N/A | §2.2 + ручная проверка | — |

**Каждая клетка должна быть заполнена.** Пустых `?` не допускается.

### 2.16. SCA (дополнение к фазе 03)

- [ ] Перенеси findings из фазы 03 с severity ≥ high в security-сводку (reference, не дубликат).

---

## 3. Специальные правила

- [ ] Если это **open-source public repo** — **удвой приоритет секретов в истории**.
- [ ] При обнаружении `critical` secret → в отчёте явно: «немедленная ротация — действие #1 в ROADMAP».

---

## 4. Quota check перед завершением

- [ ] **≥ 5 findings** для M-проекта. Если меньше — вернись к OWASP-чек-листу и проверь каждый статус `?`.
- [ ] **OWASP-чек-лист 100% заполнен.**
- [ ] **Auth-coverage таблица** содержит все роуты (или объяснённую выборку).
- [ ] Разумное распределение confidence.

---

## 5. Артефакт — `audit/06_security.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено** (OWASP чек-лист кратко)
3. **Ключевые наблюдения**
   - **Secrets** — таблица (без самих значений).
   - **Injection surface** — таблица.
   - **AuthN/AuthZ coverage** — N роутов защищено / M не защищено.
   - **Crypto** — проблемные места.
   - **TLS/CORS** — сводка.
   - **Validation coverage** — сводка.
   - **OWASP Top 10** — сводка по статусам.
4. **Находки**
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Какой самый короткий путь от неавторизованного запроса до чтения БД? Последовательность `endpoint → middleware? → handler → repo → DB` с указанием конкретных файлов и строк.
   - **Q2.** Если завтра утечёт один из .env — какие секреты придётся ротировать, и есть ли документированный процесс ротации?
7. **Следующая фаза:** `phases/phase_07_tests.md`

---

## 6. Memory

```markdown
# Phase 06 memory
Completed: YYYY-MM-DD

Security posture:
- secrets_in_repo: <N> (critical)
- secrets_in_git_history: <N> (critical)
- injection_hotspots: <N>
- routes_total: <N>
- routes_without_auth: <N>
- crypto_issues: <N>
- tls_issues: <N>
- sensitive_logging: <N>
- owasp_clean: [<list of categories>]
- owasp_issues: [<list of categories>]

Immediate actions for ROADMAP phase 0:
1. <действие>
2. ...

Next phase: phase_07_tests.md
```

---

## 7. Отчёт пользователю

> Фаза 6/10 завершена. Безопасность: <N> critical, <M> high findings. <K> подозрений на секреты, <L> эндпоинтов без auth из <T> всего. **Требующее немедленного действия:** <если есть critical — 1 строкой>. OWASP Top 10: <X> категорий с issues, <Y> чистых, <Z> неприменимо. Добавлено <N> findings. Перехожу к фазе 7 — тесты.

Перейди к `phases/phase_07_tests.md`.
