# 00z — Self-validation

```bash
python3 ci-hardening/validators/validate_manifest.py ci-hardening/manifest.yml --strict
```

## Coverage matrix

- [ ] `paths.workflow_files` ≥ 1 если `.github/workflows/` exists
- [ ] `hints.unpinned_actions` populated если есть `@v\d+` или `@main` refs
- [ ] `hints.third_party_actions` ≥ 1 если есть не-actions/* uses
- [ ] `hints.branch_protection` populated если `mode: live`
- [ ] `hints.security_features` populated если `mode: live`
- [ ] `github.gh_cli_authenticated` отражает реальное состояние

Если что-то fail — fix и повтори.
