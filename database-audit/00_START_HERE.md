# 00 — START HERE (v5)

> **🚀 Хочешь автономный режим?** Один промт, путь к проекту — и пайплайн делает всё сам.
> См. **`MASTER_PROMPT.md`** — единая точка для полного аудита без интерактивности.

---

**Это точка входа в Database Audit Pipeline v5. Архитектура — manifest-driven.**

---

## Для пользователя

### Шаг 1. Установка инструментов (один раз на машину)

```bash
# Serena + GitNexus
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant
npm install -g gitnexus
gitnexus setup

# Базовые утилиты
sudo apt install jq python3 ripgrep
pip install pyyaml jsonschema

# Опционально для live-mode
sudo apt install postgresql-client mysql-client
```

### Шаг 2. Скопировать пайплайн в проект

```bash
cp -r /path/to/audit-pipelines/database-audit/ /your/project/
cd /your/project
gitnexus analyze --embeddings   # ~1-5 минут
```

### Шаг 3. INIT — discover-фаза

```bash
bash database-audit/init.sh
```

Это создаст `database-audit/_staging/init.md` со ссылкой на мастер-промт. Открой Claude Code:

```
Прочитай database-audit/_staging/init.md и выполни discover-фазу. Создай database-audit/manifest.yml.
```

ИИ-модель выполнит **chunked discovery (orchestrator + 5 sub-prompts) протокол** из `prompts/00_discover.md` и создаст `database-audit/manifest.yml`. Это занимает ~20-40 минут на средний проект.

### Шаг 4. Ревью манифеста

```bash
# Валидация
python3 database-audit/validators/validate_manifest.py database-audit/manifest.yml

# Прочитать
less database-audit/manifest.yml
```

**Что проверять:**
- `stack.primary_orm` корректный?
- `paths.schema_files` — все ли модели там? (если в проекте N моделей — должно быть N)
- `paths.migration_files.tool` определён, не `unknown`?
- `hints.money_columns` непустой, если в проекте есть деньги?
- `hints.transaction_sites` хотя бы 5 для проекта >50k LOC?
- `hints.pool_settings` заполнен?

Если ИИ что-то пропустил — **отредактируй yaml вручную и повтори validation**. Это нормальная часть workflow.

### Шаг 5. Опционально — live mode

Если у тебя есть staging БД с read-only ролью:
```bash
export DATABASE_URL="postgresql://readonly:***@host:5432/dbname"
# В manifest установи mode.type: live
```

Перед запуском фаз пайплайн подтвердит read-only.

### Шаг 6. RUN — фазы

```bash
# Все фазы + finalize
bash database-audit/run.sh all

# Или одна фаза
bash database-audit/run.sh phase 05b

# Или один детектор
bash database-audit/run.sh detector find_money_floats 02
```

После каждой фазы → строка статуса. После всех фаз → `database-audit/results/ROADMAP.md`.

### Шаг 7. Читать результат

```bash
cat database-audit/results/ROADMAP.md           # главный артефакт
jq . database-audit/results/_meta.json          # машинная сводка
cat database-audit/results/_known_unknowns.md   # что осталось проверить
cat database-audit/results/_adversary_review.md # рефлексия
```

---

## Для агента

Ты читаешь этот файл, потому что пользователь запросил аудит БД.

### Если нет manifest.yml

Это **discover-фаза**. Действия:

1. Прочитай `database-audit/prompts/00_discover.md` целиком — это твой мастер-промт.
2. Прочитай `database-audit/manifest.schema.yml` — это контракт схемы.
3. Прочитай `database-audit/manifest.example.yml` — пример заполненного.
4. Выполни 16 шагов discover-протокола.
5. Создай `database-audit/manifest.yml`.
6. Запусти `python3 database-audit/validators/validate_manifest.py database-audit/manifest.yml`.
7. Если exit 0 — сообщи пользователю одной строкой: «Discover complete. Manifest saved. Recommend manual review before running phases.» И **остановись**.
8. Если exit ≠ 0 — исправь и повтори.

**Не запускай фазы сам** — это решение пользователя после ревью манифеста.

### Если manifest.yml есть и пользователь сказал «run phases»

1. Прочитай `database-audit/01_ORCHESTRATOR.md` — правила поведения для всех фаз.
2. Прочитай `database-audit/REFERENCE_TOOLS.md`.
3. Прочитай `database-audit/REFERENCE_BOOKS.md`.
4. Прочитай `database-audit/TEMPLATES.md`.
5. Запусти `bash database-audit/run.sh all`.
6. Между фазами читай `prompts/phase_NN_*.md` — там описано, что добавить в `database-audit/results/NN_*.md` отчёт фазы помимо детекторов.
7. После каждой фазы — `validate_phase.sh NN` exit 0.
8. Финал — `finalize.sh` exit 0 → отчитайся пользователю tl;dr.

### Если manifest.yml есть, но устарел

```bash
bash database-audit/init.sh --refresh
```

Это перепроходит discover и показывает diff с предыдущим manifest. Пользователь решает что мержить.

---

## Что изменилось с v1

| Аспект | v1 | v3 |
|--------|----|----|
| Архитектура | эвристическая | manifest-driven |
| Discover | размазано по `detect_db_stack.sh` | один промт `00_discover.md` |
| Универсальность | ломалось на монорепо | ИИ сам обходит все workspaces |
| Edit под проект | правка кода скриптов | edit yaml |
| Repeatable | повторное сканирование | `init.sh --refresh` с diff |
| Детекторы | bash + грубые pipes | Python pure functions над manifest |
| Validators | хардкод путей | env-aware (`AUDIT_DIR`/`PROJECT_ROOT`) |
| Скрипты | 14 в `scripts/` | 27 в `detectors/` + 6 в `validators/` |

Старая версия сохранена в `scripts.v1/` для совместимости.
