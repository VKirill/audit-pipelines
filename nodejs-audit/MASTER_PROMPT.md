# Master Prompt — Autonomous Production-Grade Node.js Audit

> **Single prompt, single argument.** Пользователь даёт путь к проекту → ИИ выполняет ВСЮ цепочку из 13 фаз без остановок и подтверждений.

---

## Как использовать (для пользователя)

В Claude Code запусти **одной командой**:

```
Прочитай /home/ubuntu/projects/audit-pipelines/nodejs-audit/MASTER_PROMPT.md
и выполни полный аудит проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

Всё остальное ИИ делает сам — устанавливает пайплайн, проходит 13 фаз, пишет отчёт + roadmap для подготовки к продакшену.

---

## Контракт автономности

**Ты — ИИ-агент с правами read-only на проект.**

### Что разрешено

- Читать любые файлы в `$PROJECT_PATH`.
- Запускать `npx --yes <tool>` (prettier, eslint, typescript, depcheck, knip, madge).
- Запускать `npm test` / `npm audit` / git read-only команды (`git status`, `git ls-files`, `git log`).
- Использовать MCP-инструменты, если они подключены: `mcp__gitnexus__*`, `mcp__serena__*`, `mcp__pipeline__*`, `mcp__context7__*`.
- Создавать/изменять файлы **только** внутри:
  - `$PROJECT_PATH/nodejs-audit/reports/` (отчёты, артефакты).
  - `$PROJECT_PATH/.gitignore` — одна строка `nodejs-audit/reports/`.

### Что запрещено

- Писать в код проекта (любые `.ts/.tsx/.js/.jsx/.json/.vue` вне `nodejs-audit/`).
- Делать `git commit` / `git push` / `git checkout -b`.
- Устанавливать пакеты в `package.json` (только `npx --yes`).
- Останавливаться между фазами / задавать уточняющие вопросы.

---

## Архитектура пайплайна

Раньше был один большой `AUDIT.md`. Сейчас — **цепочка из 13 файлов**, каждый отвечает за свою фазу. Каждая фаза:

1. **Читает** перечисленные в её head-секции отчёты предыдущих фаз.
2. **Выполняет** свой набор шагов.
3. **Пишет** свой отчёт в `reports/NN-name.md` + (опционально) артефакты в `reports/{REFACTORING,ADR-DRAFTS,raw}/`.
4. **Сигналит** прогресс в чат: `[PHASE NN] STARTED — <название>` в начале и `[PHASE NN] DONE — reports/NN-...md` в конце.

Это даёт два эффекта:
- Контекст не накапливается — каждая фаза работает только с нужными ей данными.
- Аудит легче улучшать поэтапно — обновляешь один phase-файл, не трогая остальные.

### Цепочка фаз

| # | Файл | Артефакт |
|---|------|----------|
| 0 | `phases/phase-00-bootstrap.md` | `00-bootstrap.md` |
| 1 | `phases/phase-01-mcp-probe.md` | `01-mcp-probe.md` (+ `raw/mcp-context.json`) |
| 2 | `phases/phase-02-recon.md` | `02-recon.md` |
| 3 | `phases/phase-03-deterministic.md` | `03-deterministic.md` (+ `raw/*`) |
| 4 | `phases/phase-04-hotspots.md` | `04-hotspots.md` (+ `raw/hotspot-matrix.tsv`) |
| 5 | `phases/phase-05-architecture-ddd.md` | `05-architecture.md` |
| 6 | `phases/phase-06-readability.md` | `06-readability.md` |
| 7 | `phases/phase-07-security.md` | `07-security.md` |
| 8 | `phases/phase-08-performance.md` | `08-performance.md` |
| 9 | `phases/phase-09-observability.md` | `09-observability.md` |
| 10 | `phases/phase-10-ai-readability.md` | `10-ai-readability.md` |
| 11 | `phases/phase-11-synthesis.md` | `FINAL-REPORT.md` + `_meta.json` |
| 12 | `phases/phase-12-prod-roadmap.md` | `QUICK-WINS.md`, `ROADMAP.md`, `ADR-DRAFTS/*`, `REFACTORING/*` |

---

## Пошаговый план (твой авто-runbook)

### Stage 0 — Bootstrap pipeline files

1. **Проверь `$PROJECT_PATH` существует и читаем.**
   ```bash
   test -d "$PROJECT_PATH" && cd "$PROJECT_PATH" || { echo "PROJECT_PATH not found"; exit 1; }
   ```

2. **Sanity check — это JS/TS проект?**
   ```bash
   has_pkg=$(test -f package.json && echo yes || echo no)
   has_tsc=$(test -f tsconfig.json -o -f tsconfig.base.json && echo yes || echo no)
   has_src=$(find . -maxdepth 4 -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.vue" \) ! -path "*/node_modules/*" 2>/dev/null | head -1)
   ```
   Если `has_pkg=no` И `has_tsc=no` И `has_src=` (пусто) — **не JS/TS проект**. Создай `nodejs-audit/reports/FINAL-REPORT.md` с одним абзацем «not a JS/TS project, audit aborted» и `_meta.json` с `verdict: "fail"`. Останови пайплайн.

3. **Установи пайплайн в проект** (idempotent):
   ```bash
   if [ ! -f "$PROJECT_PATH/nodejs-audit/MASTER_PROMPT.md" ]; then
     cp -r /home/ubuntu/projects/audit-pipelines/nodejs-audit "$PROJECT_PATH/nodejs-audit"
   fi
   ```

4. **Patch `.gitignore`** (idempotent):
   ```
   nodejs-audit/reports/
   !nodejs-audit/reports/.gitkeep
   !nodejs-audit/reports/FINAL-REPORT.md
   !nodejs-audit/reports/_meta.json
   !nodejs-audit/reports/QUICK-WINS.md
   !nodejs-audit/reports/ROADMAP.md
   !nodejs-audit/reports/ADR-DRAFTS/
   !nodejs-audit/reports/REFACTORING/
   ```

5. **Создай runtime-структуру:**
   ```bash
   mkdir -p "$PROJECT_PATH/nodejs-audit/reports/raw"
   mkdir -p "$PROJECT_PATH/nodejs-audit/reports/REFACTORING"
   mkdir -p "$PROJECT_PATH/nodejs-audit/reports/ADR-DRAFTS"
   touch "$PROJECT_PATH/nodejs-audit/reports/.gitkeep"
   touch "$PROJECT_PATH/nodejs-audit/reports/errors.log"
   ```

### Stage 1 — Run all 13 phases non-stop

**Для каждой фазы N от 0 до 12:**

1. Прочитай `nodejs-audit/phases/phase-NN-<name>.md` целиком.
2. Прочитай отчёты, перечисленные в её секции «**Inputs (читай перед стартом)**».
3. Сигналь в чат: `[PHASE NN] STARTED — <название>`.
4. Выполни шаги фазы.
5. Запиши отчёт в путь, указанный в её секции «**Outputs**».
6. Сигналь в чат: `[PHASE NN] DONE — <путь к отчёту>`.
7. **Не останавливайся.** Переходи к следующей фазе без подтверждений.

**Глобальные правила (повтори себе перед стартом каждой фазы):**

1. **Не останавливайся между фазами.** Никаких вопросов.
2. **При ошибке — продолжай.** Лог в `reports/errors.log` формата `[фаза N] [ISO time] описание`.
3. **Read-only код.** Только файлы из `nodejs-audit/reports/`.
4. **`npx --yes` для всех инструментов.** Никаких `npm install`.
5. **Сохраняй промежуточные результаты сразу.** Контекст не накапливать — каждая фаза читает только то, что ей нужно.
6. **Бюджет фазы:** 5–7 попыток на одну проблему — потом skip + errors.log.
7. **MCP-first.** Если MCP-сервер доступен (`mcp__gitnexus__list_repos` отвечает) — пользуйся им. Если нет — fallback на grep/find.

### Stage 2 — Verify

После завершения phase-12:

1. Убедись что существуют:
   - `nodejs-audit/reports/FINAL-REPORT.md`
   - `nodejs-audit/reports/_meta.json`
   - `nodejs-audit/reports/QUICK-WINS.md`
   - `nodejs-audit/reports/ROADMAP.md`
   - `nodejs-audit/reports/ADR-DRAFTS/` (≥1 файл, если были архитектурные находки)
   - `nodejs-audit/reports/REFACTORING/` (≥1 файл, если были god-files / hot-spots)
2. Валидация `_meta.json`:
   ```bash
   jq . nodejs-audit/reports/_meta.json > /dev/null
   ```
3. **Verdict логика** (зашита в фазу 11):
   - `fail` — ≥1 critical, или фаза не завершилась.
   - `warn` — нет critical но есть high, или score < 65% от max.
   - `pass` — нет critical, нет high, score ≥ 65%.

### Stage 3 — Final message в чат

Выведи **только** это, ничего больше:

```
✅ Аудит завершён.

Проект: <name>
Verdict: <pass|warn|fail>
Общая оценка: X / Y
Critical: A · High: B · Medium: C · Low: D

Топ-3 проблемы:
1. <одно предложение>
2. <одно предложение>
3. <одно предложение>

Артефакты:
  Полный отчёт:        nodejs-audit/reports/FINAL-REPORT.md
  Машинная сводка:     nodejs-audit/reports/_meta.json
  Quick wins (P0+P1):  nodejs-audit/reports/QUICK-WINS.md
  Roadmap (3 месяца):  nodejs-audit/reports/ROADMAP.md
  ADR-DRAFTS:          nodejs-audit/reports/ADR-DRAFTS/
  Refactoring targets: nodejs-audit/reports/REFACTORING/
  По фазам:            nodejs-audit/reports/0*.md
  Ошибки:              nodejs-audit/reports/errors.log

Дальше:
1. Открой QUICK-WINS.md и выполни 3 атомарных коммита из P0 за 1-2 дня.
2. Параллельно открой ROADMAP.md и распределяй стратегические фазы на 3 месяца.
3. Каждое архитектурное решение — атомарный PR с ADR из ADR-DRAFTS/.
```

После этого сообщения — **твоя работа закончена**. Не предлагай дальнейших действий.

---

## Контракт ошибок

| Ситуация | Что делать |
|---|---|
| `$PROJECT_PATH` не существует | Сообщить одной строкой и остановиться (без отчёта). |
| Не JS/TS проект | Минимальный FINAL-REPORT.md + _meta.json (verdict=fail), сообщить, остановиться. |
| `npx --yes <tool>` не работает | errors.log, продолжать со следующей проверки. |
| MCP-сервер недоступен | errors.log, fallback на grep/find. Не блокировать пайплайн. |
| Тесты падают | Это **finding**, не ошибка пайплайна. Зафиксировать, продолжать. |
| Фаза N упала на полпути | Запиши `phases_failed: [N]` в `_meta.json`, верни partial-отчёт, не падай молча. |

---

## После аудита: цикл фиксов

В `QUICK-WINS.md` — атомарные промты на 1 неделю.
В `ROADMAP.md` — стратегический план на 3 месяца с фазами.
В `ADR-DRAFTS/ADR-XXX.md` — готовые черновики архитектурных решений для wiki/decisions.md.
В `REFACTORING/<target>.md` — file-level таргеты с fitness functions.

Применяй по одному в новой сессии:

```bash
git checkout -b fix/qw-1
```

```
Прочитай nodejs-audit/reports/QUICK-WINS.md и выполни промт #1.
Минимальные изменения, по одному коммиту на логический шаг.
После каждого коммита — тесты. Сломалось — откат.
```

Один промт = одна сессия = одна ветка = один merge.

---

<div align="center">

[← Назад к README](./README.md) ·
[AUDIT.md (индекс)](./AUDIT.md) ·
[REFERENCES.md (15 книг)](./REFERENCES.md) ·
[Audit Pipelines](../README.md)

</div>
