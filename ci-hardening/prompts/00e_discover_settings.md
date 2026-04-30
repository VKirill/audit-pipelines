# 00e — GitHub Code security settings

```bash
gh api repos/$OWNER/$REPO --jq '.security_and_analysis'
```

Output структура:
```json
{
  "advanced_security": {"status": "enabled|disabled"},
  "secret_scanning": {"status": "..."},
  "secret_scanning_push_protection": {"status": "..."},
  "dependabot_security_updates": {"status": "..."},
  "code_scanning_default_setup": {"status": "..."}
}
```

Заполни:
```yaml
security_features:
  dependabot_alerts: ...
  dependabot_security_updates: ...
  secret_scanning: ...
  secret_scanning_push_protection: ...
  code_scanning: ...
  private_vulnerability_reporting: ...
```

**Findings:**
- Public repo + secret_scanning disabled → high (CI-SET-001)
- Dependabot security updates disabled → medium (CI-SET-002)
- Code scanning не настроен → medium (CI-SET-003)
- Private vulnerability reporting disabled → low (CI-SET-004)
