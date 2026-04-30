# 00d — Branch protection

```bash
gh api repos/$OWNER/$REPO/branches/$DEFAULT_BRANCH/protection
```

Заполни manifest.hints.branch_protection:

```yaml
branch_protection:
  enabled: true | false
  require_pr: true | false
  required_status_checks: [...]
  require_signed_commits: true | false
  require_linear_history: true | false
  required_approvals: N
  dismiss_stale_reviews: true | false
  enforce_admins: true | false
```

**Decision:**
- `enabled: false` → critical finding (CI-BRN-001)
- `require_pr: false` → high
- `required_approvals: 0` (для public/team repo) → medium
- `enforce_admins: false` → medium
