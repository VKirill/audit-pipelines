# Node.js Audit Pipeline — Index

> Пайплайн разбит на **13 поэтапных файлов в `phases/`**, каждый отвечает за свою фазу. Этот файл — индекс, чтобы быстро найти нужный.

---

## Начало работы

- **Запуск аудита:** [`MASTER_PROMPT.md`](./MASTER_PROMPT.md). Один промт, один аргумент `PROJECT_PATH`.
- **Документация для пользователя:** [`README.md`](./README.md).
- **Annotated bibliography (15 книг):** [`REFERENCES.md`](./REFERENCES.md).

---

## Цепочка фаз (выполняются non-stop по порядку)

| # | Фаза | Файл | Артефакты в `reports/` |
|---|---|---|---|
| 0 | Bootstrap | [`phases/phase-00-bootstrap.md`](./phases/phase-00-bootstrap.md) | `00-bootstrap.md` |
| 1 | MCP probe | [`phases/phase-01-mcp-probe.md`](./phases/phase-01-mcp-probe.md) | `01-mcp-probe.md`, `raw/mcp-context.json` |
| 2 | Recon | [`phases/phase-02-recon.md`](./phases/phase-02-recon.md) | `02-recon.md` |
| 3 | Deterministic | [`phases/phase-03-deterministic.md`](./phases/phase-03-deterministic.md) | `03-deterministic.md`, `raw/*` |
| 4 | Hot-spots | [`phases/phase-04-hotspots.md`](./phases/phase-04-hotspots.md) | `04-hotspots.md`, `raw/hotspot-matrix.tsv` |
| 5 | Architecture (DDD + Clean) | [`phases/phase-05-architecture-ddd.md`](./phases/phase-05-architecture-ddd.md) | `05-architecture.md` |
| 6 | Readability | [`phases/phase-06-readability.md`](./phases/phase-06-readability.md) | `06-readability.md` |
| 7 | Security (OWASP + ASVS) | [`phases/phase-07-security.md`](./phases/phase-07-security.md) | `07-security.md` |
| 8 | Performance | [`phases/phase-08-performance.md`](./phases/phase-08-performance.md) | `08-performance.md` |
| 9 | Observability | [`phases/phase-09-observability.md`](./phases/phase-09-observability.md) | `09-observability.md` |
| 10 | AI-readability | [`phases/phase-10-ai-readability.md`](./phases/phase-10-ai-readability.md) | `10-ai-readability.md` |
| 11 | Synthesis | [`phases/phase-11-synthesis.md`](./phases/phase-11-synthesis.md) | `FINAL-REPORT.md`, `_meta.json` |
| 12 | Production Roadmap | [`phases/phase-12-prod-roadmap.md`](./phases/phase-12-prod-roadmap.md) | `QUICK-WINS.md`, `ROADMAP.md`, `ADR-DRAFTS/`, `REFACTORING/` |

---

## Шаблоны

Используются phase-12 при генерации артефактов:

- [`templates/quick-wins.md`](./templates/quick-wins.md) — атомарные коммиты на неделю.
- [`templates/roadmap.md`](./templates/roadmap.md) — стратегический план на 3 месяца.
- [`templates/adr-draft.md`](./templates/adr-draft.md) — черновик архитектурного решения.
- [`templates/refactoring-target.md`](./templates/refactoring-target.md) — file-level таргет с fitness function.
- [`templates/trade-off-matrix.md`](./templates/trade-off-matrix.md) — Richards & Ford 10 ilities.

Дополнительно (старые, сохранены для совместимости с GitHub Actions):

- [`templates/eslint.config.js`](./templates/eslint.config.js)
- [`templates/prettierrc.json`](./templates/prettierrc.json)
- [`templates/tsconfig.strict.json`](./templates/tsconfig.strict.json)
- [`templates/github-actions-audit.yml`](./templates/github-actions-audit.yml)
- [`templates/findings-template.md`](./templates/findings-template.md)
- [`templates/AGENTS.md.template`](./templates/AGENTS.md.template)

---

## Контракт между фазами

Каждый файл в `phases/`:

1. **Inputs** — какие отчёты предыдущих фаз обязан прочитать.
2. **Outputs** — какие файлы записать в `reports/`.
3. **Шаги** — что именно делать.
4. **Шаблон отчёта** — структура, которой должен соответствовать output.
5. **Сигналы в чат** — `[PHASE NN] STARTED` и `[PHASE NN] DONE`.

Это позволяет:
- Не накапливать контекст — каждая фаза работает только с нужными ей данными.
- Поэтапно улучшать пайплайн — обновляешь один phase-файл, не трогая остальных.
- Дебажить — если что-то не так, видно на какой фазе сломалось.

---

## Артефакты в `reports/`

После выполнения всего пайплайна структура:

```
reports/
├── 00-bootstrap.md           ← phase-00
├── 01-mcp-probe.md           ← phase-01
├── 02-recon.md               ← phase-02
├── 03-deterministic.md       ← phase-03
├── 04-hotspots.md            ← phase-04
├── 05-architecture.md        ← phase-05
├── 06-readability.md         ← phase-06
├── 07-security.md            ← phase-07
├── 08-performance.md         ← phase-08
├── 09-observability.md       ← phase-09
├── 10-ai-readability.md      ← phase-10
├── FINAL-REPORT.md           ← phase-11 (главный отчёт)
├── _meta.json                ← phase-11 (для CI)
├── QUICK-WINS.md             ← phase-12 (атомарные коммиты на неделю)
├── ROADMAP.md                ← phase-12 (3 месяца)
├── ADR-DRAFTS/               ← phase-12 (черновики архитектурных решений)
│   ├── ADR-001-...md
│   └── ...
├── REFACTORING/              ← phase-12 (file-level таргеты)
│   ├── <slug>.md
│   └── ...
├── errors.log                ← аккумулятор ошибок пайплайна
└── raw/                      ← сырые логи инструментов
    ├── prettier.log
    ├── eslint-*.json
    ├── tsc-*.log
    ├── audit.json
    ├── knip-*.json
    ├── madge-*.log
    ├── hotspot-matrix.tsv
    ├── largest-files.log
    ├── secrets-grep.log
    ├── mcp-context.json
    └── ...
```

---

## CI integration

В корне репо проекта добавь `.github/workflows/audit.yml`:

```yaml
- name: Run nodejs-audit
  run: |
    claude --print "Прочитай nodejs-audit/MASTER_PROMPT.md и выполни полный аудит проекта: PROJECT_PATH=$PWD"

- name: Check verdict
  run: |
    verdict=$(jq -r .verdict nodejs-audit/reports/_meta.json)
    if [ "$verdict" = "fail" ]; then
      echo "::error::Audit verdict=fail"
      jq -r '.blockers[]' nodejs-audit/reports/_meta.json
      exit 1
    fi

- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: audit-report
    path: nodejs-audit/reports/
    retention-days: 30
```

---

<div align="center">

[← README](./README.md) ·
[MASTER_PROMPT](./MASTER_PROMPT.md) ·
[REFERENCES](./REFERENCES.md) ·
[Audit Pipelines](../README.md)

</div>
