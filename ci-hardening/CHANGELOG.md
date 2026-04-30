# CHANGELOG

## v2 (2026-05-01) — Manifest-driven autonomous

Полная переработка ci-hardening из набора шаблонов в **autonomous pipeline**
уровня database-audit.

### Главное

- **MASTER_PROMPT.md** — single-arg autonomous master prompt
  (только `PROJECT_PATH`, остальное auto-detect)
- **manifest-driven архитектура** — manifest.schema.yml + manifest.example.yml
- **gh CLI integration** — auto-detect repo, branch protection, security features
- **proposed-changes/** generator — готовые `.github/` файлы для PR

### Структура (новая)

```
ci-hardening/
├── README.md, CHANGELOG.md, MASTER_PROMPT.md
├── manifest.schema.yml + manifest.example.yml
├── init.sh, run.sh, requirements.txt, .gitignore
├── prompts/                   # 7 chunked sub-prompts + 00_legacy_audit_prompt.md
├── phases/                    # phase docs (TBD)
├── detectors/                 # 16 Python detectors
├── validators/                # validate_manifest.py, validate_phase.sh, finalize.sh
├── lib/                       # env.sh, manifest_lib.py, github_api.py
└── templates/                 # original .github/ templates сохранены
    ├── workflows/             #   ci.yml, codeql.yml, pinact.yml, scorecard.yml
    ├── dependabot.yml
    ├── renovate.json
    ├── pull_request_template.md
    ├── ISSUE_TEMPLATE/
    ├── SECURITY.md
    └── ROADMAP_TEMPLATE.md
```

### Detectors (16)

**Phase 01 — Inventory:**
- detect_workflows.py — все .github/workflows/*.yml

**Phase 02 — Supply chain:**
- detect_unpinned_actions.py — actions без SHA pinning (главный supply-chain check)

**Phase 03 — Permissions:**
- detect_excessive_permissions.py — workflow без explicit permissions
- detect_persist_credentials.py — actions/checkout без persist-credentials: false
- detect_script_injection.py — ${{ github.event.* }} в run: blocks (zizmor-style)

**Phase 04 — Secrets:**
- detect_long_lived_credentials.py — long-lived AWS/GCP/Azure → OIDC opportunities

**Phase 05 — Branch protection:**
- detect_branch_protection.py — gh api branch protection audit

**Phase 06 — Dependencies + dangerous triggers:**
- detect_dangerous_triggers.py — pull_request_target / workflow_run
- detect_dependabot_config.py — Dependabot/Renovate setup

**Phase 07 — SAST + settings:**
- detect_codeql_setup.py — CodeQL workflow check
- detect_security_features.py — Dependabot alerts/Secret scanning/Code scanning

**Phase 08 — Repo metadata:**
- detect_codeowners.py — CODEOWNERS + SECURITY.md + PR template

**Phase 09 — Synthesis:**
- synthesize_roadmap.py — ROADMAP.md + 4-фазный план + auto-TL;DR
- adversary_review.py — bias-check + severity calibration draft

**Phase 10 — Deep dive:**
- deep_dive.py — skeleton с 6 секциями per critical finding

### Category-based finding IDs

- CI-PIN-***  — supply-chain (unpinned actions)
- CI-PERM-*** — permissions issues
- CI-SEC-***  — secrets / OIDC
- CI-BRN-***  — branch protection
- CI-SET-***  — GitHub settings (Code security)
- CI-WF-***   — workflow patterns (script-injection, dangerous triggers)
- CI-DEP-***  — dependencies (Dependabot)
- CI-SAST-*** — static analysis setup

### Validators v2

- validate_manifest.py — JSON Schema + sanity (--strict mode)
- validate_phase.sh — per-phase gate (quotas, evidence, rationale)
- finalize.sh — generates _meta.json + verdict (pass/pass-with-conditions/fail)

### Совместимость

- Старые шаблоны workflows (ci.yml, codeql.yml, pinact.yml, scorecard.yml) сохранены в templates/workflows/
- AUDIT_PROMPT.md → prompts/00_legacy_audit_prompt.md (для обратной совместимости)
- ROADMAP_TEMPLATE.md → templates/ROADMAP_TEMPLATE.md

---

## v1 (2026-04-30) — Initial release

Набор шаблонов + master prompt + 4-фазный roadmap. См. templates/ для исходных
файлов.
