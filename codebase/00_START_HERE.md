# 00 — START HERE

**Это точка входа в аудит-пайплайн. Здесь две инструкции — одна для тебя (человека), одна для агента.**

---

## Для пользователя

Весь пайплайн — это набор связанных Markdown-документов в папке `audit_pipeline/` плюс детерминированные скрипты в `audit_pipeline/scripts/`. Они читаются агентом по очереди.

**Тебе нужно:**

1. Поставить инструменты (разово):
   ```bash
   # Serena
   uv tool install -p 3.13 serena-agent@latest --prerelease=allow
   claude mcp add serena -- serena start-mcp-server --context ide-assistant

   # GitNexus
   npm install -g gitnexus
   gitnexus setup
   ```

2. Опционально (но рекомендуется) — поставить инструменты валидации/сбора:
   ```bash
   sudo apt install jq cloc        # уже обычно есть
   # gitleaks для secret-history scan
   curl -sSfL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.21.1_linux_x64.tar.gz | tar -xz -C /usr/local/bin gitleaks
   ```
   Все они опциональны — `run_external_tools.sh` подставляет placeholder если отсутствуют.

3. Скопировать всю папку `audit_pipeline/` в корень проекта.

4. В корне проекта запустить `gitnexus analyze --embeddings` (~1-5 минут).

5. Запустить `claude` и дать одну команду:

   ```
   Прочитай audit_pipeline/01_ORCHESTRATOR.md и выполни весь пайплайн строго по инструкции.
   Все артефакты — в папку audit/. Режим работы — read-only.
   После каждой фазы запускай bash audit_pipeline/scripts/validate_phase.sh NN —
   если падает, исправляй и не переходи дальше. После phase_10_synthesis_roadmap
   обязательно phase_10a_self_audit. При наличии critical findings — phase_11_deep_dive.
   Финал — bash audit_pipeline/scripts/finalize.sh; exit 0 = аудит завершён.
   После каждой фазы сообщай 1-2 предложения статуса. Финал — tl;dr на 5-7 пунктов.
   ```

6. Ждать. На проекте ~50k LOC аудит занимает 90–180 минут.

7. Читать `audit/ROADMAP.md` — главный результат. И `audit/_meta.json` для машинной сводки.

**Если что-то пошло не так** — напиши агенту «продолжи с фазы N», он прочитает `audit/_meta.json` + `.serena/memories/audit_progress` и возобновится.

---

## Для агента

Ты читаешь этот файл, потому что пользователь запросил аудит кодовой базы.

**Твои следующие действия:**

1. Прочитай `audit_pipeline/01_ORCHESTRATOR.md` целиком. **Особое внимание — §3.3 (калибровка confidence), §3.4 (запрет «допустимо»), §3.10 (anti-recursion), §4 (exit gates), §7 (fallback-протоколы).**
2. Прочитай `audit_pipeline/REFERENCE_TOOLS.md` — справочник.
3. Прочитай `audit_pipeline/TEMPLATES.md` — формат findings (внимание на поля `confidence_rationale` и `exploit_proof`).
4. Запусти один раз: `bash audit_pipeline/scripts/run_external_tools.sh` (соберёт cloc/git/npm-audit/gitleaks/coverage в `audit/evidence/`).
5. Начни с `audit_pipeline/phases/phase_00_setup.md`.
6. После КАЖДОЙ фазы:
   - запусти `bash audit_pipeline/scripts/validate_phase.sh NN`;
   - exit 0 — переходи дальше; exit ≠ 0 — исправь и повтори;
   - обнови `.serena/memories/audit_progress`;
   - отчитайся пользователю одной строкой.
7. После phase 10 (synthesis) — **обязательно** phase 10a (self-audit).
8. Если в `findings.jsonl` есть ≥ 1 critical — phase 11 (deep-dive) обязательна.
9. Финал: `bash audit_pipeline/scripts/finalize.sh`. Только при exit 0 пиши пользователю tl;dr.

Строго соблюдай:
- `read-only` (§3.1)
- `evidence-based` с цитатами строк (§3.2)
- **`calibrated confidence`** (§3.3) — без `confidence_rationale` `high` запрещён
- **запрет «допустимо»** (§3.4) — нельзя обходить gate словами
- **anti-recursion** (§3.10) — после 3 пустых ответов от инструмента → fallback
- **exit gates через скрипты** (§4) — без exit 0 фаза не завершена
- **fallback protocols** (§7) — деградация инструмента ≠ деградация анализа

Не торопись. Лучше медленно и точно, чем быстро и поверхностно.
