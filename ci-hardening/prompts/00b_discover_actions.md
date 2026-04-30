# 00b — Third-party actions

## Шаг 1 — Inventory всех `uses:`

```bash
rg -nE 'uses:\s+\S+' .github/workflows/ -g '*.yml' -g '*.yaml'
```

Для каждого:
- action (owner/name)
- ref (после `@`): SHA / @v4 / @main / @master
- file:line

## Шаг 2 — Classify

| ref | classification |
|---|---|
| 40-char SHA | ✅ pinned |
| `@v4`, `@v4.2.2` | ⚠️ tag (vulnerable to retag) |
| `@main`, `@master` | 🔴 mutable branch (worst) |
| `@<branch-name>` | 🔴 mutable branch |

## Шаг 3 — Resolve recommended SHAs (если live)

```bash
# Через pinact (если установлен):
pinact run --skip_push

# Или через gh api:
gh api repos/OWNER/ACTION/git/refs/tags/v4 --jq '.object.sha'
```

## Шаг 4 — Заполни manifest

```yaml
hints:
  unpinned_actions:
    - action: actions/checkout
      ref: v4
      file: .github/workflows/ci.yml
      line: 12
      recommended_sha: "08c6903c..."

  third_party_actions:
    - action: actions/checkout
      owner: actions
      usage_count: 3
      is_verified: true   # GitHub Verified Creator badge
```

**Verified Creator** проверяй через `gh api users/<owner> --jq '.is_verified'`.
