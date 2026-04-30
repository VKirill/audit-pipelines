# Master Prompt — Autonomous CI Hardening Audit

> **Single prompt, single argument.** Пользователь даёт путь к проекту → ИИ выполняет ВЕСЬ аудит CI/CD без дополнительных команд.

---

## Как использовать (для пользователя)

В Claude Code запусти **одной командой**:

```
Прочитай /home/ubuntu/projects/audit-pipelines/ci-hardening/MASTER_PROMPT.md
и выполни полный аудит CI/CD проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

**От пользователя — ТОЛЬКО путь.** Всё остальное ИИ определяет сам:

- ✅ **GitHub repo auto-detect** через `git remote get-url origin`
- ✅ **GitHub API access** через `gh auth status` — full/limited/none
- ✅ **Workflow files inventory** — все `.github/workflows/*.yml`
- ✅ **Third-party actions** + recommended SHA через `pinact`/GitHub API
- ✅ **Branch protection** + Code security settings через `gh api`
- ✅ **Secrets/environments** через `gh secret list`
- ✅ Все 11 фаз + auto-fill phase 10 deep_dive + calibration phase 09a
- ✅ Финальный отчёт + готовые fix-PR

Override flags (опционально):
- `mode=static` — без gh API calls (если нет токена)
- `repo=<owner/repo>` — явное указание (если git remote неправильный)
- `dry_run=true` — генерируй файлы, но не предлагай PR

---

## Контракт автономности

### Что разрешено

- Читать любые файлы в `$PROJECT_PATH` (`.github/`, code, configs)
- Запускать read-only `gh api`/`gh secret list` (если authenticated)
- Использовать `pinact` для resolve action SHA
- Использовать `gitleaks` для secret scanning
- Использовать `zizmor` для workflow lint
- Использовать MCP tools (Serena, GitNexus если доступны)
- Создавать/изменять файлы внутри `$PROJECT_PATH/ci-hardening/`
- Генерировать `proposed-changes/` директорию с предлагаемыми правками для PR

### Что запрещено

- Писать в `.github/` напрямую (правки только через `proposed-changes/`)
- Writing/deleting через `gh api` (только GET endpoints)
- Изменять секреты, branch protection settings, etc — это решение пользователя
- Останавливаться без финального отчёта
- Оставлять `_agent fills_` placeholders

---

## Stage 0 — Bootstrap

```bash
cd "$PROJECT_PATH"

# 0.1 Установить pipeline в проект
if [ ! -d "ci-hardening" ]; then
    cp -r /home/ubuntu/projects/audit-pipelines/ci-hardening ./
fi

# 0.2 Зависимости
python3 -c "import yaml, jsonschema" || pip install -r ci-hardening/requirements.txt

# 0.3 Проверить gh CLI
if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    GH_AUTH=true
else
    GH_AUTH=false
fi
```

## Stage 0.5 — Auto-detect mode

Логика:
1. **Если есть `git remote get-url origin`** + parse owner/repo → save в manifest
2. **Если `gh auth status` exit 0** → `mode: live`
3. **Иначе** → `mode: static` + note в `_known_unknowns.md`

```bash
# Detect GitHub repo from git remote
git_remote=$(git -C "$PROJECT_PATH" remote get-url origin 2>/dev/null)
if [[ "$git_remote" =~ github\.com[:/]([^/]+)/([^.]+)(\.git)?$ ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
fi

# Mode decision
if [[ "$GH_AUTH" == "true" ]] && [[ -n "$OWNER" ]]; then
    MODE=live
    # Verify access
    if gh api "repos/$OWNER/$REPO" >/dev/null 2>&1; then
        API_ACCESS=full
    else
        API_ACCESS=limited
    fi
else
    MODE=static
    API_ACCESS=none
fi
```

Single user-facing checkpoint:

```
🔍 Auto-detected:
- repo: <owner>/<repo>
- mode: live | static
- gh CLI: authenticated | not-authenticated
- api_access: full | limited | none

Продолжаю автоматически.
```

## Stage 1 — Discovery (через 7 sub-prompts)

Прочитай и выполни **в указанном порядке**:

```
1. prompts/00_discover.md                    — orchestrator (skeleton)
2. prompts/00a_discover_workflows.md         — все .github/workflows/*.yml
3. prompts/00b_discover_actions.md           — third-party actions inventory + pinning status
4. prompts/00c_discover_secrets.md           — secrets, OIDC opportunities, gitleaks
5. prompts/00d_discover_branch_protection.md — gh api branch protection + settings
6. prompts/00e_discover_settings.md          — Dependabot/Secret scanning/Code scanning
7. prompts/00z_validate_manifest.md          — self-validation gate
```

## Stage 2 — Manifest validation

```bash
python3 ci-hardening/validators/validate_manifest.py \
  ci-hardening/manifest.yml --strict
```

Если `--strict` fails: исправь manifest, повтори. Не запрашивай review у пользователя.

## Stage 3 — Run all phases

```bash
bash ci-hardening/run.sh all
```

После каждой фазы — `validate_phase.sh NN` exit 0. Если fail — fix → retry.

## Stage 4 — Phase 10 deep_dive enrichment

Для каждого critical finding:
- **Section 1 — Trace**: какой workflow, какая job, какие triggers
- **Section 2 — Exploit reproduction**: пошаговый сценарий атаки (например tj-actions style)
- **Section 3 — Blast radius**: какие secrets/permissions exposed
- **Section 4 — Fix variants**:
  - **Variant A (quick)**: 1-line fix (e.g. `persist-credentials: false`)
  - **Variant B (proper)**: правильный multi-step (Phase 0/1)
  - **Variant C (architectural)**: rewrite workflow / OIDC migration
- **Section 5 — Verification**: как проверить что fix сработал
- **Section 6 — Recommended next step**: priority order

## Stage 5 — Phase 09a adversary review

```markdown
## Severity calibration

### Inflation (понижено)
- DB-OUT-NNN (outdated action with no security impact) → low

### Confirmed (severity осталась)
- DB-PIN-NNN (unpinned tj-actions/changed-files in production) → critical

### Deflation (повышено)
- DB-DT-NNN (pull_request_target on untrusted code) → critical (через GitNexus impact reveal)

## Strong findings | Weaker findings | Systematic risks
```

## Stage 6 — Generate proposed PR

В `ci-hardening/results/proposed-changes/`:

```
proposed-changes/
├── README.md                       — описание изменений для PR
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  — обновлённый (если нужно)
│   │   └── ci.yml.diff             — diff
│   ├── dependabot.yml              — auto-generated если нет
│   └── CODEOWNERS                  — если команда > 2
└── SECURITY.md                     — если отсутствует
```

Команда пользователю в финальном отчёте:

```bash
# Применить changes:
cp -r ci-hardening/results/proposed-changes/.github/* .github/
cp ci-hardening/results/proposed-changes/SECURITY.md .

# Создать PR:
gh pr create --title "ci: harden workflows (audit findings)" \
             --body "$(cat ci-hardening/results/proposed-changes/README.md)"
```

## Stage 7 — Finalize + report

```bash
bash ci-hardening/validators/finalize.sh
```

Финальный отчёт **одним сообщением**:

```markdown
# 🔒 CI Hardening Audit — <project_name>

**Repo:** <owner>/<repo>
**Verdict:** `pass | pass-with-conditions | fail`
**Mode:** live | static
**Findings:** <total> (critical: N, high: M, medium: K, low: L)

## 🔴 Top 3 critical

1. **DB-PIN-001** — actions/checkout @v4 (unpinned)
   `.github/workflows/ci.yml:12` — supply-chain risk (tj-actions style)
   Fix: `actions/checkout@<sha> # v4.2.2`

## 📊 Categories
| Category | Count |
|---|---|
| supply-chain (unpinned actions) | N |
| permissions | M |
| secrets / OIDC | K |
| branch-protection | L |
| settings (Dependabot/SAST) | P |

## 📁 Output
- `ci-hardening/results/ROADMAP.md` — 4-phase roadmap
- `ci-hardening/results/proposed-changes/` — готовые правки для PR
- `ci-hardening/results/_meta.json` — машинная сводка

## ⚡ Что делать сейчас (Phase 0 — полдня)

[конкретные команды]

## 📅 Phase 1 (1-3 дня)

[пункты]

## 🎯 Phase 2-3 (неделя/квартал)

[архитектурные изменения]
```

---

## Anti-patterns

❌ Изменять `.github/` напрямую — только через `proposed-changes/`
❌ Делать `gh api` POST/PATCH/DELETE без явного user request
❌ Оставлять `_agent fills_` в любом артефакте
❌ Пропускать `validate_phase.sh exit 0`
❌ Запускать без `gh auth status` check
❌ Игнорировать `pull_request_target` в существующих workflows

## Fallback protocols

### Если gh CLI не authenticated
- `mode: static`
- Все findings про branch protection / settings / secrets-list — `confidence: low` + warning «requires gh auth»
- Помечай в `_known_unknowns.md`

### Если `pinact` недоступен
- Используй `gh api repos/<owner>/<action>/git/refs/tags/<tag>` для resolve SHA
- Fallback на простой regex inventory

### Если `zizmor` недоступен
- Reduce script-injection coverage до базового regex
- Помечай в `_known_unknowns.md`

---

## Версионирование

Master prompt = `v1` для ci-hardening (унаследовал паттерны database-audit v5.2).
Pipeline = `ci-hardening v2` (manifest-driven, autonomous).
