# Master Prompt — Autonomous Node.js Audit

> **Single prompt, single argument.** Пользователь даёт путь к проекту → ИИ
> выполняет ВЕСЬ пайплайн без дополнительных команд, вопросов и
> подтверждений.

---

## Как использовать (для пользователя)

В Claude Code запусти **одной командой**:

```
Прочитай /home/ubuntu/projects/audit-pipelines/nodejs-audit/MASTER_PROMPT.md
и выполни полный аудит проекта:

PROJECT_PATH=/home/ubuntu/apps/<project_name>
```

**От пользователя — ТОЛЬКО путь к проекту.** Всё остальное ИИ определяет сам:

- ✅ **Pipeline install** — копирует `nodejs-audit/` внутрь проекта
- ✅ **Package manager auto-detect** — `npm/yarn/pnpm/bun` по lock-файлу
- ✅ **TS/JS auto-detect** — наличие `tsconfig.json`
- ✅ **Sanity check** — если не JS/TS проект, корректно остановиться
- ✅ **`.gitignore` patch** — добавить `nodejs-audit/reports/` если ещё нет
- ✅ **Все 10 фаз** через `npx --yes` (без установки в проект)
- ✅ **`FINAL-REPORT.md` + `_meta.json`** одним проходом
- ✅ **Финальный отчёт** одним сообщением в чат

---

## Контракт автономности

**Ты — ИИ-агент с правами read-only на проект.**

### Что разрешено

- Читать любые файлы в `$PROJECT_PATH`
- Запускать `npx --yes <tool>` (prettier, eslint, typescript, depcheck, knip, madge)
- Запускать `npm test` / `npm audit` / git read-only команды (`git status`, `git ls-files`)
- Создавать/изменять файлы **только** внутри:
  - `$PROJECT_PATH/nodejs-audit/reports/` (отчёты)
  - `$PROJECT_PATH/nodejs-audit/reports/raw/` (сырые логи)
  - `$PROJECT_PATH/.gitignore` — одна строка `nodejs-audit/reports/` (если её нет)
  - `$PROJECT_PATH/AGENTS.md` — только если файла нет (фаза 0, опционально)

### Что запрещено

- Писать в код проекта (любые `.ts/.tsx/.js/.jsx/.json` вне `nodejs-audit/`)
- Делать `git commit` / `git push` / `git checkout -b`
- Устанавливать пакеты в `package.json` (только `npx --yes`)
- Останавливаться между фазами / задавать уточняющие вопросы
- Запускать `npm run build`, Lighthouse, нагрузочные тесты, `playwright`
- Пропускать sanity check на старте (если не JS/TS — остановиться корректно)

---

## Пошаговый план (твой авто-runbook)

### Stage 0 — Bootstrap

1. **Проверь `$PROJECT_PATH` существует и читаем.**
   ```bash
   test -d "$PROJECT_PATH" && cd "$PROJECT_PATH" || { echo "PROJECT_PATH not found"; exit 1; }
   ```

2. **Sanity check — это JS/TS проект?**
   ```bash
   has_pkg=$(test -f package.json && echo yes || echo no)
   has_tsc=$(test -f tsconfig.json && echo yes || echo no)
   has_src=$(find . -maxdepth 3 -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) ! -path "*/node_modules/*" 2>/dev/null | head -1)
   ```
   Если `has_pkg=no` И `has_tsc=no` И `has_src=` (пусто) — это **НЕ JS/TS проект**.
   Создай `nodejs-audit/reports/FINAL-REPORT.md` с одним абзацем «not a JS/TS
   project, audit aborted» и `_meta.json` с `verdict: "fail"`,
   `phases_completed: []`, `errors_log_size` = 1, в `errors.log` запиши
   причину. Выведи короткое сообщение в чат и **остановись**.

3. **Установи пайплайн в проект.**
   - Если `nodejs-audit/` уже существует и содержит `AUDIT.md` — пропусти.
   - Иначе скопируй из источника:
     ```bash
     cp -r /home/ubuntu/projects/audit-pipelines/nodejs-audit "$PROJECT_PATH/nodejs-audit"
     ```
     Если этот путь недоступен — попробуй `~/projects/audit-pipelines/nodejs-audit`,
     или используй переменную `AUDIT_PIPELINES_DIR` если она задана. Если
     ни один путь не работает — запиши в errors.log и продолжай (AUDIT.md
     уже есть в проекте, раз ты его читаешь).

4. **Patch `.gitignore`** (idempotent — только если строки нет):
   ```
   nodejs-audit/reports/
   !nodejs-audit/reports/.gitkeep
   !nodejs-audit/reports/FINAL-REPORT.md
   !nodejs-audit/reports/_meta.json
   ```

5. **Создай runtime-структуру:**
   ```bash
   mkdir -p "$PROJECT_PATH/nodejs-audit/reports/raw"
   touch "$PROJECT_PATH/nodejs-audit/reports/.gitkeep"
   touch "$PROJECT_PATH/nodejs-audit/reports/errors.log"
   ```

### Stage 1 — Run all 10 phases

**Прочитай `nodejs-audit/AUDIT.md` (полная спека) и выполни ВСЕ 10 фаз
(0..9) подряд за один проход.**

Глобальные правила (из AUDIT.md, повтори себе перед стартом):

1. **Не останавливайся.** Никаких вопросов, подтверждений, пауз между фазами.
2. **При ошибке — продолжай.** Лог в `reports/errors.log` формата
   `[фаза N] [ISO time] описание`, переход к следующему шагу.
3. **Read-only код.** Только файлы из «что разрешено» выше.
4. **`npx --yes` для всех инструментов.** Никаких `npm install`.
5. **Сохраняй промежуточные результаты сразу.** После каждой фазы —
   `reports/0N-*.md` записан и закрыт. Контекст не накапливать.
6. **Бюджет фазы.** 5–7 попыток на одну проблему — потом skip + errors.log.
7. **Прогресс-маркеры.** В чат: `[PHASE N] STARTED — <название>` в начале,
   `[PHASE N] DONE — reports/0N-*.md` в конце.
8. **Фаза 9 не перечитывает код.** Только `reports/00..08-*.md` + `raw/`.

Фазы (детали — в `nodejs-audit/AUDIT.md`):

| # | Фаза | Артефакт |
|---|------|----------|
| 0 | Bootstrap | `00-bootstrap.md` |
| 1 | Recon | `01-recon.md` |
| 2 | Deterministic (prettier/eslint/tsc/tests/audit/depcheck/knip/madge) | `02-deterministic.md` |
| 3 | Architecture (6 осей) | `03-architecture.md` |
| 4 | Readability (5 осей) | `04-readability.md` |
| 5 | Security (OWASP Top 10 экспресс) | `05-security.md` |
| 6 | Performance (N+1, sync I/O, утечки) | `06-performance.md` |
| 7 | Observability (логи/метрики/трейсинг/ошибки) | `07-observability.md` |
| 8 | AI-readability (AGENTS.md, JSDoc, husky, CI) | `08-ai-readability.md` |
| 9 | Final synthesis | **`FINAL-REPORT.md` + `_meta.json`** |

### Stage 2 — Finalize

После завершения фазы 9:

1. Убедись что существуют:
   - `nodejs-audit/reports/FINAL-REPORT.md`
   - `nodejs-audit/reports/_meta.json`
   - все `reports/0N-*.md` (или их отсутствие отмечено в errors.log)
2. Валидация `_meta.json`:
   ```bash
   jq . nodejs-audit/reports/_meta.json > /dev/null
   ```
   Если упало — почини JSON и пересохрани.
3. **Verdict логика** (зашита в фазу 9):
   - `fail` — ≥1 critical, или фаза 9 не дошла
   - `warn` — нет critical но есть high, или score < 120/240
   - `pass` — нет critical, нет high, score ≥ 120/240

### Stage 3 — Final message в чат

Выведи **только** это, ничего больше:

```
✅ Аудит завершён.

Проект: <name>
Verdict: <pass|warn|fail>
Общая оценка: X / 240
Critical: A · High: B · Medium: C · Low: D

Топ-3 проблемы:
1. <одно предложение>
2. <одно предложение>
3. <одно предложение>

Полный отчёт:    nodejs-audit/reports/FINAL-REPORT.md
Машинная сводка: nodejs-audit/reports/_meta.json
По фазам:        nodejs-audit/reports/0*.md
Ошибки:          nodejs-audit/reports/errors.log

Дальше:
1. Открой FINAL-REPORT.md → Executive Summary
2. Топ-3 критических проблем
3. Выбери первый промт и запусти его в новой сессии Claude Code
```

После этого сообщения — **твоя работа закончена**. Не предлагай дальнейших
действий, не задавай вопросов, не делай follow-up.

---

## Контракт ошибок

| Ситуация | Что делать |
|---|---|
| `$PROJECT_PATH` не существует | Сообщить пользователю одной строкой и остановиться (без отчёта) |
| Не JS/TS проект | Создать минимальный FINAL-REPORT.md + _meta.json (verdict=fail), сообщить и остановиться |
| `npx --yes <tool>` не работает (нет интернета / npm down) | errors.log, продолжать со следующей проверки |
| `npm test` падает | Это **finding**, не ошибка пайплайна. Зафиксировать в `02-deterministic.md`, продолжать |
| `tsc --noEmit` находит сотни ошибок | Это **finding**. Не пытаться чинить. Записать категории и идти дальше |
| Файл слишком большой для чтения | Читать первые 100–200 строк, остальное по требованию. Не блокировать фазу |
| Зацикливание на одной проблеме > 5–7 попыток | skip + errors.log + следующий шаг |
| Фаза 9 упала на полпути | Запиши в `_meta.json` `phases_failed: [9]`, верни partial-отчёт, не падай молча |

---

## CI integration

Этот же промт можно запустить из GitHub Actions:

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

## После аудита: цикл фиксов

В `FINAL-REPORT.md` — пронумерованные промты. Применяй по одному в **новой
сессии**:

```
git checkout -b fix/audit-1
```

```
Прочитай nodejs-audit/reports/FINAL-REPORT.md и выполни промт #1.
Минимальные изменения, по одному коммиту на логический шаг.
После каждого коммита — тесты. Сломалось — откат.
```

Один промт = одна сессия = одна ветка = один merge.

---

<div align="center">

[← Назад к README](./README.md) ·
[AUDIT.md (полная спека 10 фаз)](./AUDIT.md) ·
[Audit Pipelines](../README.md)

</div>
