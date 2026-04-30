<div align="center">

  <h1>🔒 CI Hardening Pipeline <code>v2</code></h1>

  <p>
    <b>Autonomous CI/CD security audit для любого GitHub-проекта.</b><br/>
    Single-arg master prompt · 16 детекторов · gh API integration · готовые fix-PR.
  </p>

  <p>
    <img src="https://img.shields.io/badge/version-v2-orange" alt="v2"/>
    <img src="https://img.shields.io/badge/architecture-manifest--driven-blue" alt="Manifest-driven"/>
    <img src="https://img.shields.io/badge/detectors-16-green" alt="16 detectors"/>
    <img src="https://img.shields.io/badge/integration-gh_API-purple" alt="GitHub API"/>
    <img src="https://img.shields.io/badge/baseline-2026-orange" alt="2026 baseline"/>
    <img src="https://img.shields.io/badge/SHA--pinned-actions-success" alt="SHA-pinned"/>
    <img src="https://img.shields.io/badge/mode-read--only-success" alt="Read-only"/>
  </p>

  <p>
    <a href="../README.md">← Назад к Audit Pipelines</a> ·
    <a href="../frontend">Фронтенд</a> ·
    <a href="../codebase">Codebase</a> ·
    <a href="../database-audit">Database</a>
  </p>
</div>

<br/>

> **v2 — autonomous pipeline.** Один промт, путь к проекту — ИИ сам обходит все workflows, читает gh API (branch protection, security features), ищет supply-chain риски, генерирует готовые `.github/` файлы для PR. Унаследовал паттерны database-audit v5.2 (manifest-driven, chunked discovery, hard exit gates, auto-fill phase deep_dive).

---

## 🚀 Quick start

### Single-command autonomous

```
Прочитай /home/ubuntu/projects/audit-pipelines/ci-hardening/MASTER_PROMPT.md
и выполни полный аудит CI/CD проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

**Только путь.** Всё остальное ИИ:
- Auto-detects `OWNER/REPO` через `git remote`
- `gh auth status` → mode (live с API / static без API)
- Читает все `.github/workflows/*.yml`
- Резолвит SHA через `gh api repos/.../git/refs/tags`
- Branch protection через `gh api`
- Security features (Dependabot/Secret scanning/Code scanning)
- 16 детекторов, 11 фаз, единый ROADMAP

---

## Что находит этот пайплайн

### 🔴 Critical (блокируют деплой)

| # | Что | Как находим | Источник |
|---|---|---|---|
| 1 | **Unpinned actions с branch ref** (`@main`, `@master`) | `detect_unpinned_actions.py` | tj-actions/changed-files (March 2025), trivy-action (March 2026) |
| 2 | **Script injection** через `${{ github.event.* }}` в `run:` | `detect_script_injection.py` | zizmor docs, GitHub Security Lab |
| 3 | **`pull_request_target` / `workflow_run`** на untrusted code | `detect_dangerous_triggers.py` | Adnan Khan: Attack via pull_request_target |
| 4 | **Branch protection disabled** на default branch | `detect_branch_protection.py` (gh api) | GitHub Docs |
| 5 | **Hardcoded secrets в коде** | gitleaks integration | OWASP |

### 🟠 High

| # | Что | Как находим |
|---|---|---|
| 6 | **Unpinned actions с tag ref** (`@v4`) | `detect_unpinned_actions.py` |
| 7 | **No explicit permissions** в workflow (default = write-all) | `detect_excessive_permissions.py` |
| 8 | **Long-lived AWS/GCP/Azure credentials** в secrets | `detect_long_lived_credentials.py` (рекомендуется OIDC) |
| 9 | **Dependabot alerts disabled** на public repo | `detect_security_features.py` |
| 10 | **Не настроен Dependabot/Renovate** | `detect_dependabot_config.py` |

### 🟡 Medium

| # | Что | Как находим |
|---|---|---|
| 11 | **`actions/checkout` без `persist-credentials: false`** | `detect_persist_credentials.py` |
| 12 | **Missing `SECURITY.md`** | `detect_codeowners.py` |
| 13 | **CodeQL не настроен** | `detect_codeql_setup.py` |
| 14 | **Push protection / Secret scanning disabled** | `detect_security_features.py` |
| 15 | **Required approvals = 0** в branch protection | `detect_branch_protection.py` |

### 🟢 Low

| # | Что |
|---|---|
| 16 | Missing `CODEOWNERS`, PR template, outdated actions |

---

## Архитектура

```
project/
└── ci-hardening/                              ← всё внутри одной папки
    │
    │── pipeline (committed) ─────────────────
    ├── README.md, CHANGELOG.md, MASTER_PROMPT.md
    ├── init.sh, run.sh, requirements.txt
    ├── manifest.schema.yml, manifest.example.yml
    │
    ├── prompts/                               ← chunked discovery
    │   ├── 00_discover.md                     ← orchestrator
    │   ├── 00a_discover_workflows.md
    │   ├── 00b_discover_actions.md
    │   ├── 00c_discover_secrets.md
    │   ├── 00d_discover_branch_protection.md
    │   ├── 00e_discover_settings.md
    │   ├── 00z_validate_manifest.md
    │   ├── 00_legacy_audit_prompt.md          ← v1 prompt (для обратной совместимости)
    │   └── refresh.md
    │
    ├── detectors/                             ← 16 detectors
    │   ├── detect_workflows.py
    │   ├── detect_unpinned_actions.py         ← supply-chain check
    │   ├── detect_excessive_permissions.py
    │   ├── detect_persist_credentials.py
    │   ├── detect_script_injection.py
    │   ├── detect_dangerous_triggers.py
    │   ├── detect_long_lived_credentials.py
    │   ├── detect_branch_protection.py
    │   ├── detect_security_features.py
    │   ├── detect_dependabot_config.py
    │   ├── detect_codeql_setup.py
    │   ├── detect_codeowners.py
    │   ├── synthesize_roadmap.py
    │   ├── adversary_review.py
    │   └── deep_dive.py
    │
    ├── validators/
    │   ├── validate_manifest.py               ← JSON Schema + sanity
    │   ├── validate_phase.sh                  ← per-phase gate
    │   └── finalize.sh                        ← _meta.json generator
    │
    ├── lib/
    │   ├── env.sh                             ← AUDIT_DIR/PIPELINE_DIR/MANIFEST
    │   ├── manifest_lib.py                    ← shared library
    │   └── github_api.py                      ← gh CLI wrapper
    │
    ├── templates/                             ← готовые шаблоны
    │   ├── workflows/                         ← ci.yml, codeql.yml, pinact.yml, scorecard.yml
    │   ├── dependabot.yml + renovate.json
    │   ├── pull_request_template.md + ISSUE_TEMPLATE/
    │   ├── SECURITY.md
    │   └── ROADMAP_TEMPLATE.md
    │
    ├── .gitignore                             ← исключает runtime ↓
    │
    │── runtime (gitignored) ─────────────────
    ├── manifest.yml                           ← создаётся ИИ при init
    ├── _staging/                              ← prompt staging
    │   ├── init.md
    │   └── refresh.md
    └── results/
        ├── findings.jsonl                     ← все findings, category-based IDs
        ├── ROADMAP.md                         ← главный артефакт + 4-фазный план
        ├── _meta.json                         ← machine-readable summary
        ├── 10_deep_dive.md
        ├── _adversary_review.md
        ├── _known_unknowns.md
        ├── 09_synthesis.md
        └── evidence/                          ← detector outputs per phase
            ├── 01_phase/workflows_inventory.md
            ├── 02_phase/unpinned_actions.md
            └── ...
```

---

## Workflow

```
bash ci-hardening/init.sh                 — bootstrap + auto-detect repo + gh auth check
        ↓
ИИ читает _staging/init.md
        ↓
chunked discovery (7 sub-prompts) — заполняет manifest.yml
        ↓
bash ci-hardening/run.sh all              — 11 фаз
        ↓
results/ROADMAP.md + proposed-changes/    — готовые правки для PR
```

---

## Категории findings (по prefix)

| Prefix | Категория | Пример |
|---|---|---|
| `CI-PIN-***` | supply-chain (unpinned actions) | `actions/checkout@v4` без SHA |
| `CI-PERM-***` | permissions | workflow без `contents: read` |
| `CI-SEC-***` | secrets / OIDC | `AWS_ACCESS_KEY_ID` long-lived |
| `CI-BRN-***` | branch protection | default branch без protection |
| `CI-SET-***` | GitHub Settings → Code security | Dependabot/Secret scanning off |
| `CI-WF-***` | workflow patterns | script-injection, `pull_request_target` |
| `CI-DEP-***` | dependencies | нет Dependabot/Renovate config |
| `CI-SAST-***` | static analysis setup | CodeQL не настроен |

---

## Команды

```bash
# Bootstrap
bash ci-hardening/init.sh                # init / refresh
bash ci-hardening/init.sh --refresh      # update existing manifest

# Run
bash ci-hardening/run.sh all              # все фазы
bash ci-hardening/run.sh phase 02         # одна фаза
bash ci-hardening/run.sh detector detect_unpinned_actions 02
bash ci-hardening/run.sh validate         # validate manifest
bash ci-hardening/run.sh finalize         # generate _meta.json
bash ci-hardening/run.sh reset            # wipe runtime

# Read result
cat ci-hardening/results/ROADMAP.md
jq . ci-hardening/results/_meta.json
```

---

## Sources

- [GitHub Docs · Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
- [GitHub Blog · Actions 2026 Security Roadmap](https://github.blog/news-insights/product-news/whats-coming-to-our-github-actions-2026-security-roadmap/)
- [zizmor docs](https://woodruffw.github.io/zizmor/) — workflow security linter
- [pinact](https://github.com/suzuki-shunsuke/pinact) — pin actions to SHA
- [OpenSSF Scorecard](https://github.com/ossf/scorecard)
- [StepSecurity Harden-Runner](https://docs.stepsecurity.io/harden-runner)
- Incident reports: tj-actions, trivy-action, axios, bitwarden/cli

---

<div align="center">
<a href="../README.md">← Назад к Audit Pipelines</a>
</div>
