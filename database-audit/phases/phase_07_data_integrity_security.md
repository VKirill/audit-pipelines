# PHASE 07 — DATA INTEGRITY & SECURITY

**Цель:** PII классификация, шифрование at-rest и in-transit, доступ к БД, SQLi surface, audit log, GDPR.

**Источники:**
- Karwin, *SQL Antipatterns* — §19 Readable Passwords, §20 SQL Injection.
- OWASP — *Database Security Cheat Sheet*, *SQL Injection Prevention Cheat Sheet*.
- NIST SP 800-122 — *Guide to Protecting PII*.
- GDPR Articles 5, 17, 20, 32, 33.

---

## 1. Входы

- `evidence/01_inventory/schema_summary.json` — все колонки.
- `evidence/06_migrations_evolution/*` — есть ли миграции для encryption/RLS.

## 2. Что проверяешь

### 2.1. Классификация PII

NIST SP 800-122 — два уровня PII:
- **Sensitive PII:** SSN, credit card, passport, biometric, health, financial details.
- **Non-sensitive PII:** имя, email, телефон, дата рождения отдельно — но в комбинации могут стать sensitive.

Проход по колонкам:
```bash
rg -nE '(name|email|phone|address|ssn|passport|birthday|dob|card|cvv|bank|iban|swift|gender|race|religion)' \
   audit/evidence/01_inventory/schema_summary.json
```

Для каждой найденной:
- [ ] Это PII? (да/нет).
- [ ] Senior/non-sensitive?
- [ ] Зашифровано at-rest?
- [ ] Доступно через какие endpoint? (см. GitNexus route_map).
- [ ] Логируется где-нибудь? (см. phase 09).

Создай таблицу `evidence/07_*/pii_classification.md`.

### 2.2. Encryption at rest

- [ ] СУБД имеет TDE (Transparent Data Encryption)? Включено?
- [ ] Application-level encryption на sensitive PII? (например, `pgcrypto`, app-side AES).
- [ ] Encryption keys где? (KMS, env, hardcoded?)
- [ ] Backups зашифрованы?

Application-level — золотой стандарт для sensitive: SSN, card. Если хранится в plaintext → critical.

### 2.3. Passwords и secrets

Karwin §19 Readable Passwords:

- [ ] Пароли хранятся хешированными? (bcrypt / argon2id / scrypt — current best).
- [ ] **Не** MD5/SHA1/SHA256 без salt — это finding (critical).
- [ ] Salt уникальный per-record?
- [ ] Recovery flow безопасен (token expires, hashed)?

Проверь:
```bash
rg -nE '(MD5|SHA1|sha1)\(' --type sql --type ts --type py --type go
rg -nE 'bcrypt|argon2|scrypt' --type-add 'all:*'
```

### 2.4. SQL Injection surface

Karwin §20:
```bash
bash database-audit/scripts/find_string_concat_sql.sh > audit/evidence/07_*/sqli_surface.md
```

Скрипт ищет:
- ` + variable + ` в SQL-строках (TS/JS/Java).
- `f"SELECT … {var}"` (Python f-strings).
- `"SELECT … " + var` (Go).
- `${variable}` в JS template strings внутри `query`.
- `%s % var` (Python old-style).

Каждый match → проверь:
- [ ] Это user-controlled input? (через прохождение route → controller).
- [ ] Параметризуется через prepared statement / placeholder?
- [ ] Если interpolation для имени колонки/таблицы — есть allowlist?

User-controlled + interpolation → **critical** finding с exploit_proof.

ORM не страховка: raw queries (`prisma.$queryRaw`, `Model.objects.raw`, `db.execute`) могут быть уязвимы. Проверяй каждый.

### 2.5. Доступ к БД

OWASP Database Security:

- [ ] Application user — какие права? `GRANT SELECT/INSERT/UPDATE/DELETE` или `GRANT ALL`?
- [ ] DDL (CREATE/ALTER/DROP) у app-user отключён?
- [ ] Отдельный read-only user для отчётов / аналитики?
- [ ] DBA-account защищён MFA, не используется приложением?

Если app-user = superuser → **high** finding.

### 2.6. Connection security

- [ ] TLS к БД? (`sslmode=require`, MongoDB TLS).
- [ ] Connection string через secret manager (не hardcoded, не в `.env` в репо)?
- [ ] DSN не утекает в логи / error messages?

Проверь:
```bash
gitleaks detect --no-git --source . > audit/evidence/07_*/secret_scan.txt
rg -nE 'postgres://[^:]+:[^@]+@' --type-not lock --type-not log
```

### 2.7. Row-level security (PG)

Multi-tenant без RLS = всегда риск. Если у вас PG и multi-tenant:
- [ ] Используется RLS (`CREATE POLICY`)?
- [ ] Или isolation в коде (`WHERE tenant_id = $1` в каждом запросе)?
- [ ] Есть тест, что один тенант не может прочитать данные другого?

Если ни RLS, ни consistent guard в коде → critical (cross-tenant data leakage).

### 2.8. Audit log

- [ ] Есть `audit_log` таблица для критичных операций (login, balance change, role change)?
- [ ] Эта таблица append-only? (нет UPDATE/DELETE).
- [ ] Защищена от подделки (cryptographic signing если требует compliance)?

GDPR Article 33: notification of breach in 72h. Без audit log невозможно понять, что утекло.

### 2.9. GDPR / privacy

| Article | Что значит | Что проверяем |
|---------|------------|---------------|
| Art. 5 | Минимизация данных | Хранится ли только необходимое? |
| Art. 17 | Right to erasure | Есть процедура удаления? Каскадная? Backup учтён? |
| Art. 20 | Data portability | Есть export per-user? |
| Art. 32 | Security of processing | Encryption, access control, monitoring |
| Art. 33 | Breach notification | Audit log, monitoring, alerting |

- [ ] Есть `users.deleted_at` = soft-delete или hard-delete? Hard-delete корректнее для GDPR.
- [ ] Анонимизация для аналитики используется?
- [ ] Право на забвение каскадирует на вторичные таблицы (orders, sessions, logs)?

### 2.10. Backup и recovery security

- [ ] Бэкапы зашифрованы?
- [ ] Доступ к бэкапам ограничен (S3 IAM, GPG)?
- [ ] При recovery PII восстанавливается в test-environment не в plain?

Phase 09 проверяет надёжность бэкапов. Здесь — security аспект.

## 3. Quotas

Минимум 3 findings (M-проект). Реалистично — 5–8.

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 07
```

Required evidence:
- `evidence/07_data_integrity_security/pii_classification.md`
- `evidence/07_data_integrity_security/sqli_surface.md`
- `evidence/07_data_integrity_security/secret_scan.txt`
- `evidence/07_data_integrity_security/db_user_privileges.md`

## 5. Артефакты

- `audit/07_data_integrity_security.md`

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.pii_candidates`, `hints.raw_sql_in_code`

**Запуск:**
```bash
bash database-audit/run.sh phase 07
```

После детекторов агент дополняет `audit/07_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
