# PHASE 00 — SETUP

**Цель:** Подготовить окружение и убедиться, что все инструменты доступны. Без этой фазы остальные работать не могут.

**Источник:** общие инженерные практики (не специфичная книга).

---

## 1. Входы

- Путь к проекту (от пользователя).
- Установленные `serena` и `gitnexus` как MCP-серверы в Claude Code.

## 2. Чек-лист действий

### 2.1. Проверка базовых условий
- [ ] Убедись, что путь проекта существует (`list_dir` на корень).
- [ ] Проверь, это ли git-репозиторий: `git rev-parse --is-inside-work-tree`. Если нет — зафиксируй в ограничениях, фазы 08 и 10 частично деградируют.
- [ ] Зафиксируй коммит: `git rev-parse HEAD`, ветку: `git rev-parse --abbrev-ref HEAD`.

### 2.2. Создание структуры артефактов
- [ ] Создай папки: `audit/`, `audit/evidence/`, `.serena/memories/` (последнее часто уже создано Serena).
- [ ] Создай пустой файл `audit/findings.jsonl`.

### 2.3. Serena
- [ ] `check_onboarding_performed`. Если нет — `onboarding`.
- [ ] `activate_project` (или убедись, что активен нужный).
- [ ] Проверь `.serena/project.yml`. Если отсутствует или `read_only` не `true` — сделай его `true` (это единственная правка, разрешённая в фазе setup, и она не в коде проекта, а в конфиге Serena).
- [ ] `get_current_config` — зафиксируй версию, язык, активный проект.

### 2.4. GitNexus
- [ ] `list_repos` — есть ли запись для текущего проекта.
- [ ] Если нет — попроси пользователя запустить `gitnexus analyze --embeddings` в корне проекта. Это ~1–5 минут. Дождись подтверждения и повтори `list_repos`.
- [ ] Прочитай `gitnexus://repo/{name}/context` — размер индекса, staleness.
- [ ] Прочитай `gitnexus://repo/{name}/schema` — зафиксируй схему графа (понадобится для cypher позже).

### 2.5. Определение базовых характеристик проекта
Выполни через `bash`:
- [ ] `cloc . --exclude-dir=node_modules,dist,build,.git,vendor,target,.venv,venv,__pycache__,.next` (если `cloc` недоступен — запиши это в ограничения, используй fallback через `find + wc`).
- [ ] Языки и их доли (по LOC и по числу файлов).
- [ ] Package manager: проверь наличие `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `pom.xml`, `build.gradle*`, `Gemfile`, `composer.json`, `*.csproj`/`*.sln`. Перечисли найденные.
- [ ] Entry-point kandидаты: `find_file` для `main.*`, `index.*`, `app.*`, `manage.py`, `cmd/*/main.go`, `Program.cs`. Просто зафиксируй имена.

### 2.6. Git-метаданные (пригодятся потом)
- [ ] Дата первого и последнего коммита.
- [ ] Число коммитов всего.
- [ ] Число коммитов за последние 90 дней.
- [ ] Число уникальных авторов (`git shortlog -sne | wc -l`).
- [ ] Размер репозитория: `git count-objects -vH`.

### 2.7. Определение размера проекта (для адаптации)
По таблице из `01_ORCHESTRATOR.md §5` определи размер (XS/S/M/L/XL). Зафиксируй в отчёте.

## 3. Проверки «всё ли хорошо»

- [ ] `list_dir` в корне работает через Serena.
- [ ] `list_repos` через GitNexus возвращает текущий проект.
- [ ] `find_symbol` с любым публичным именем (например из файла `main.*` или первой строки `README`) возвращает результат — значит LSP работает.

Если что-то не работает — не блокируй пайплайн. Задокументируй в разделе ограничений отчёта.

## 4. Артефакт — `audit/00_setup.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено** (чек-лист выше с отметками)
3. **Ключевые наблюдения**
   - Размер проекта (размер-категория).
   - Языки (таблица: язык → LOC → %).
   - Package manager(s).
   - Entry point candidates.
   - Возраст проекта, активность, число авторов.
   - Статус Serena и GitNexus (версии, языки поддержки).
4. **Находки этой фазы** (таблица)
   - Находки: обычно мало, но могут быть, например:
     - `F-XXXX` / info: .env в репозитории.
     - `F-XXXX` / low: нет README / README < 10 строк.
     - `F-XXXX` / low: устаревший .gitignore (есть артефакты сборки в индексе).
     - `F-XXXX` / medium: git-репозиторий > 1 GB (возможны большие файлы в истории).
5. **Неполные проверки** (если что-то не сработало)
6. **Контрольные вопросы (ответить письменно)**
   - **Q1.** Можешь ли ты одной фразой сказать, что это за проект (язык/фреймворк/тип системы)? Если «нет» — добавь finding уровня `low` о недостаточной документации.
   - **Q2.** Активен ли проект (коммиты за 90 дней > 0)? Если нет — зафиксируй как контекст, это повлияет на приоритизацию в фазе 10 (для мёртвых проектов рефакторинг бессмыслен).
7. **Следующая фаза:** `phases/phase_01_inventory.md`

## 5. Memory

Создай `.serena/memories/audit_phase_00`:

```markdown
# Phase 00 memory
Completed: YYYY-MM-DD HH:MM
Commit: <hash>
Branch: <branch>

Project profile:
- size: <XS/S/M/L/XL>
- loc_total: <N>
- primary_language: <lang>
- languages: [<lang>: %, <lang>: %, ...]
- package_managers: [<pm>, ...]
- frameworks_hint: [<framework>, ...]  # если видно из манифестов
- entry_points: [<file>, ...]
- git_age_days: <N>
- active_90d: <bool>

Tools status:
- serena: OK/DEGRADED/MISSING (версия)
- gitnexus: OK/DEGRADED/MISSING (версия)

Findings added: F-0001 to F-000N (count)
Limitations:
- <что не удалось и почему>

Next phase: phase_01_inventory.md
```

Обнови `.serena/memories/audit_progress` по шаблону из `TEMPLATES.md §4`.

## 5a. v3 — запуск deterministic data collectors (один раз, в начале)

Запусти оркестратор внешних инструментов — он соберёт cloc/git stats/npm audit/gitleaks/coverage в `audit/evidence/` так, чтобы дальше эти данные были готовы:

```bash
bash audit_pipeline/scripts/run_external_tools.sh
```

Скрипт никогда не падает: если инструмент отсутствует — он создаст placeholder-файл с инструкцией по установке. Время — 1-10 минут зависит от размера проекта.

## 5b. v3 — exit gate

```bash
bash audit_pipeline/scripts/validate_phase.sh 00
```

Если exit ≠ 0 — исправь и повтори. Не переходи к фазе 01 с failed gate.

## 6. Отчёт пользователю

После фазы — один абзац в чат:

> Фаза 0/10 завершена. Проект: <язык/фреймворк>, ~<N> LOC (<size>), возраст ~<X> месяцев. Serena и GitNexus подключены (<статусы>). Обнаружено <N> предварительных находок. Перехожу к фазе 1 — инвентаризация.

Затем: перейди к `phases/phase_01_inventory.md`.
