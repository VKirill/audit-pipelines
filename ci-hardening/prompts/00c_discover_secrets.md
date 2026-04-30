# 00c — Secrets + OIDC opportunities

## Шаг 1 — gh secret list (live)

```bash
gh secret list -R $OWNER/$REPO
```

Для каждого secret:
- name
- found in workflow files: `rg -l '\${{ secrets.SECRET_NAME }}' .github/workflows/`

## Шаг 2 — Long-lived credentials → OIDC opportunities

| Secret pattern | Target cloud | OIDC alternative |
|---|---|---|
| `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | aws | `aws-actions/configure-aws-credentials@<sha>` + role-to-assume |
| `GCP_SA_KEY` | gcp | `google-github-actions/auth@<sha>` |
| `AZURE_CLIENT_SECRET` | azure | `azure/login@<sha>` + federated identity |
| `NPM_TOKEN` (для publish) | npm | `npm publish --provenance` + OIDC |

Каждый long-lived → finding `CI-SEC-NNN [high]` с recommendation OIDC migration.

## Шаг 3 — Hardcoded secrets in code

```bash
gitleaks detect --no-banner --source . --report-format json --report-path /tmp/gitleaks.json
# Если gitleaks unavailable — fallback grep:
rg -nE 'sk_live_|sk_test_|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}' \
   -g '!node_modules' -g '!.git' .
```

Каждый hit → critical finding (CI-SEC-NNN).

## Шаг 4 — Заполни manifest

```yaml
hints:
  long_lived_credentials:
    - secret_name: AWS_ACCESS_KEY_ID
      usage_files: [.github/workflows/deploy.yml]
      target_cloud: aws
  secrets_in_code:
    - file: ...
      line: ...
      rule: aws-access-key
```
