# 00 — START HERE

**Это точка входа в Database Audit Pipeline v1. Здесь две инструкции — одна для тебя (человека), одна для агента.**

---

## Для пользователя

Весь пайплайн — это набор связанных Markdown-документов в `database-audit/` плюс детерминированные скрипты в `database-audit/scripts/`. Они читаются агентом по очереди.

**Тебе нужно:**

1. Поставить инструменты (разово):
   ```bash
   # Serena
   uv tool install -p 3.13 serena-agent@latest --prerelease=allow
   claude mcp add serena -- serena start-mcp-server --context ide-assistant

   # GitNexus
   npm install -g gitnexus
   gitnexus setup

   # Базовые утилиты для скриптов (обычно есть)
   sudo apt install jq ripgrep
   ```

2. Опционально (рекомендуется для глубины):
   ```bash
   # Прямой доступ к БД для EXPLAIN/статистики
   sudo apt install postgresql-client mysql-client
   # или для Mongo:
   wget https://downloads.mongodb.com/compass/mongosh-2.3.0-linux-x64.tgz

   # gitleaks — на случай DSN/пароля в коде
   curl -sSfL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.21.1_linux_x64.tar.gz | tar -xz -C /usr/local/bin gitleaks
   ```

3. Скопировать всю папку `database-audit/` в корень проекта.

4. В корне проекта запустить `gitnexus analyze --embeddings` (~1–5 минут).

5. Опционально — выставить переменную `DATABASE_URL` если хочешь анализ с подключением к БД (read-only пользователь):
   ```bash
   export DATABASE_URL="postgresql://readonly:***@host:5432/dbname"
   # или
   export DATABASE_URL="mysql://readonly:***@host:3306/dbname"
   # или для Mongo:
   export DATABASE_URL="mongodb://host:27017/dbname"
   ```

6. Запустить `claude` и дать одну команду:

   ```
   Прочитай database-audit/01_ORCHESTRATOR.md и выполни весь пайплайн строго по инструкции.
   Все артефакты — в папку audit/. Режим работы — read-only (и для кода, и для БД).
   После каждой фазы запускай bash database-audit/scripts/validate_phase.sh NN — если падает,
   исправляй и не переходи дальше. После phase_10_synthesis_roadmap обязательно
   phase_10a_self_audit. При наличии critical findings — phase_11_deep_dive.
   Финал — bash database-audit/scripts/finalize.sh; exit 0 = аудит завершён.
   После каждой фазы сообщай 1-2 предложения статуса. Финал — tl;dr на 5-7 пунктов.
   ```

7. Ждать. На проекте ~50k LOC + 30 моделей + 80 миграций пайплайн занимает 90–240 минут.

8. Читать `audit/ROADMAP.md` — главный результат. И `audit/_meta.json` для машинной сводки.

**Если что-то пошло не так** — напиши агенту «продолжи с фазы N», он прочитает `audit/_meta.json` + `.serena/memories/db_audit_progress` и возобновится.

---

## Для агента

Ты читаешь этот файл, потому что пользователь запросил аудит базы данных.

**Твои следующие действия:**

1. Прочитай `database-audit/01_ORCHESTRATOR.md` целиком. **Особое внимание — §3.3 (калибровка confidence), §3.4 (запрет «допустимо»), §3.10 (anti-recursion), §4 (exit gates), §7 (fallback-протоколы), §8 (live-vs-static модусы).**
2. Прочитай `database-audit/REFERENCE_TOOLS.md` — справочник по инструментам.
3. Прочитай `database-audit/REFERENCE_BOOKS.md` — какая глава применяется в какой фазе.
4. Прочитай `database-audit/TEMPLATES.md` — формат findings (внимание на `confidence_rationale` и `exploit_proof`).
5. Запусти один раз: `bash database-audit/scripts/run_external_tools.sh` (детектит стек, парсит схему, собирает миграции, опционально дёргает live-DB и пишет всё в `audit/evidence/`).
6. Начни с `database-audit/phases/phase_00_setup.md`.
7. После КАЖДОЙ фазы:
   - запусти `bash database-audit/scripts/validate_phase.sh NN`;
   - exit 0 — переходи дальше; exit ≠ 0 — исправь и повтори;
   - обнови `.serena/memories/db_audit_progress`;
   - отчитайся пользователю одной строкой.
8. После phase 10 (synthesis) — **обязательно** phase 10a (self-audit).
9. Если в `findings.jsonl` есть ≥ 1 critical — phase 11 (deep-dive) обязательна.
10. Финал: `bash database-audit/scripts/finalize.sh`. Только при exit 0 пиши пользователю tl;dr.

Строго соблюдай:
- `read-only` (§3.1) — никаких ALTER/UPDATE/DELETE даже в staging
- `evidence-based` с цитатами строк/SQL (§3.2)
- **`calibrated confidence`** (§3.3) — без `confidence_rationale` `high` запрещён
- **запрет «допустимо»** (§3.4)
- **anti-recursion** (§3.10) — после 3 пустых ответов от инструмента → fallback
- **exit gates через скрипты** (§4)
- **fallback protocols** (§7) — деградация инструмента ≠ деградация анализа
- **live vs static mode** (§8) — если `DATABASE_URL` не задан, выполняй static-only ветви, помечай в `_known_unknowns.md` всё что не подтверждено EXPLAIN-ом

Не торопись. БД — самое дорогое место для ошибок аудитора (false positive стоит дороже чем в обычном код-ревью). Лучше понизить confidence чем перегнать.
