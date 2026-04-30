# 00c — Deep discovery: PII & secrets in DB

---

## Шаги

### 1. Найди PII колонки в схемах

```bash
for f in <schema_files>; do
  rg -nE '(name|email|phone|address|ssn|passport|tax_id|national_id|dob|birthday|gender|race|religion|card|cvv|iban|swift|bank|biometric|fingerprint|password|api_key|secret|token|credentials|apikey|webhook|access_token|refresh_token)' "$f"
done
```

### 2. Классификация (NIST SP 800-122)

| Подстрока в имени | Classification |
|---|---|
| `email`, `phone`, `address`, `name`, `dob`, `birthday` | `non-sensitive` (но в комбинации могут стать sensitive) |
| `ssn`, `passport`, `tax_id`, `national_id` | `sensitive` |
| `card`, `cvv`, `iban`, `swift`, `bank` | `payment-card` |
| `password`, `api_key`, `secret`, `token`, `credentials`, `webhook_url`, `access_token` | `credentials` |
| `gender`, `race`, `religion`, `health`, `medical` | `special-category` (GDPR Art. 9) |
| `biometric`, `fingerprint` | `biometric` |

### 3. Encryption at-rest detection

Прочитай:
- Конфиг СУБД (TDE / pgcrypto)
- Application-side encryption (`crypto`, `node-forge`, `cryptography` Python, `golang.org/x/crypto`)
- Key management — KMS / Vault / env / hardcoded

```bash
rg -nE '(pgcrypto|crypto-js|node-forge|@aws-sdk/client-kms|HashiCorp Vault|encrypt|decrypt|aes-)' \
   -g '!node_modules' -g '!*.lock' .
```

### 4. Заполнение

```yaml
hints:
  pii_candidates:
    - table: User
      column: email
      file: packages/db/prisma/models/user.prisma
      lines: "12"
      type: String
      classification: non-sensitive
      encrypted_at_rest: false
    - table: Producer
      column: credentials
      file: packages/db/prisma/models/producer.prisma
      lines: "44-48"
      type: Json
      classification: credentials
      encrypted_at_rest: false  # plain Json field — critical
```

### 5. Multi-tenant + PII

Если проект multi-tenant — добавь:

```yaml
hints:
  multi_tenant_isolation:
    model: row-level-security  # или discriminator-column / schema-per-tenant
    discriminator_column: tenant_id
    policies_files:
      - packages/db/prisma/2026-04-30-rls-policies.sql
    notes: "PG RLS включён через CREATE POLICY"
```

Без RLS / без consistent guard в коде → cross-tenant data leakage = critical.

### 6. Secrets in repo (gitleaks scan)

```bash
gitleaks detect --no-banner --no-git --source . --report-format json --report-path /tmp/gitleaks.json
```

Если найдены секреты — это уже finding (не hint, а direct finding).

### 7. Quality gate

```bash
python3 -c "
import yaml
m = yaml.safe_load(open('database-audit/manifest.yml'))
pii = m.get('hints',{}).get('pii_candidates',[])
print(f'pii_candidates: {len(pii)}')
crit = [p for p in pii if p.get('classification') in ('credentials','payment-card','biometric','special-category') and not p.get('encrypted_at_rest')]
print(f'  unencrypted critical: {len(crit)}')
"
```

---

## Источники

- NIST SP 800-122 — *Guide to Protecting PII*
- GDPR Articles 5, 17, 20, 32, 33
- OWASP *Database Security Cheat Sheet*
- Karwin §19 Readable Passwords
