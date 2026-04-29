# REFERENCE — инструменты

Справочник по инструментам, которые пайплайн использует. Читается один раз на старте.

---

## Serena (MCP, через LSP)

Семантическая навигация кода. Работает на уровне символов (функция/класс/метод), не на уровне строк.

### Основные инструменты

| Tool | Зачем |
|------|-------|
| `activate_project` | Активировать проект по пути. Первое, что делаешь. |
| `check_onboarding_performed` | Проверка — был ли онбординг. |
| `onboarding` | Первичное сканирование, если ещё не было. |
| `get_symbols_overview` | Верхнеуровневый список символов в файле (без тел). Предпочтительно ПЕРВЫМ перед чтением файла. |
| `find_symbol` | Поиск символа по имени. Параметры: `name_path`, `include_body` (false по умолчанию — не тяни тело зря), `relative_path` (скоуп по файлу/папке). |
| `find_referencing_symbols` | Кто ссылается на символ. Основа для dead-code и blast-radius. |
| `search_for_pattern` | Regex-поиск по проекту. Для TODO, секретов, опасных функций. |
| `list_dir` | Листинг директории (recursive опционально). |
| `find_file` | Поиск файла по маске (например `*.config.*`). |
| `write_memory` | Записать markdown-заметку в `.serena/memories/`. |
| `read_memory` | Прочитать заметку. |
| `list_memories` | Список заметок. |
| `think_about_collected_information` | Мета-проверка: хватает ли собранного? |
| `think_about_task_adherence` | Мета-проверка: не ушёл ли в сторону? |
| `think_about_whether_you_are_done` | Мета-проверка: всё ли сделано? |

### НЕ использовать в аудите (read-only)

`create_text_file`, `replace_symbol_body`, `insert_after_symbol`, `insert_before_symbol`, `replace_regex`, `delete_lines`, `rename_symbol`, `execute_shell_command` (с мутацией проекта).

`execute_shell_command` разрешён **только для неинвазивных команд чтения**: `git log`, `git rev-parse`, `cloc`, `npm outdated`, `cat` и т.п. Никаких `git commit`, `npm install`, `pip install`.

### Примеры хороших вызовов

```
# Обзор файла перед чтением
get_symbols_overview(relative_path="src/services/user.ts")

# Поиск конкретного класса и его полей (без тел методов)
find_symbol(name_path="UserService", include_body=false, depth=1)

# Кто импортирует/вызывает UserService
find_referencing_symbols(name_path="UserService", relative_path="src/services/user.ts")

# Все TODO в проекте
search_for_pattern(substring_pattern="TODO|FIXME|HACK|XXX", relative_path=".")
```

---

## GitNexus (MCP, через граф KuzuDB)

Графовое представление кодовой базы. Работает на уровне отношений (CALLS, IMPORTS, EXTENDS, MEMBER_OF и т.д.), поверх Tree-sitter AST.

### Перед первым использованием

Убедись, что репозиторий проиндексирован:
```bash
gitnexus analyze --embeddings   # ~1-5 минут на средний проект
```

Если индекса нет — на пользователе: он должен это запустить (см. фазу 00). Если GitNexus недоступен — фазы 02 и 03 деградируют, но не падают.

### Основные инструменты

| Tool | Зачем |
|------|-------|
| `list_repos` | Какие репозитории проиндексированы. |
| `query` | Гибридный поиск (BM25+семантика+RRF), группирует по процессам. Для исследовательских вопросов. |
| `context` | 360° вид символа: входящие/исходящие вызовы, в каких процессах участвует, соседи. |
| `impact` | Blast radius: `direction` = upstream/downstream, `maxDepth`, `minConfidence`, `relationTypes`. Главный инструмент для оценки риска изменения. |
| `detect_changes` | По git-diff показывает затронутые процессы. Для проверки миграций в будущем — в этом пайплайне не используется, кроме фазы 10. |
| `cypher` | Сырые запросы к графу. Для систематических проверок архитектуры. |

### Ресурсы GitNexus

| Resource | Зачем |
|----------|-------|
| `gitnexus://repos` | Список репозиториев. |
| `gitnexus://repo/{name}/context` | Статистика + актуальность индекса. |
| `gitnexus://repo/{name}/clusters` | Все функциональные кластеры (Leiden). |
| `gitnexus://repo/{name}/cluster/{name}` | Содержимое кластера. |
| `gitnexus://repo/{name}/processes` | Все execution flows (от entry points). |
| `gitnexus://repo/{name}/process/{name}` | Конкретный трейс процесса. |
| `gitnexus://repo/{name}/schema` | Схема графа (нужно перед cypher!). |

### Шаблоны полезных Cypher-запросов

Перед любым cypher-запросом **обязательно** прочитай `gitnexus://repo/{name}/schema`. Схема может меняться между версиями GitNexus. Запросы ниже — отправная точка, адаптируй под актуальную схему.

```cypher
-- Межкластерные импорты (таблица зависимостей слоёв)
MATCH (a)-[r:CodeRelation {type: 'IMPORTS'}]->(b)
MATCH (a)-[:CodeRelation {type: 'MEMBER_OF'}]->(ca:Community)
MATCH (b)-[:CodeRelation {type: 'MEMBER_OF'}]->(cb:Community)
WHERE ca.heuristicLabel <> cb.heuristicLabel
RETURN ca.heuristicLabel AS from, cb.heuristicLabel AS to, count(*) AS edges
ORDER BY edges DESC

-- Топ-N самых цитируемых символов (узлы ядра)
MATCH (fn)<-[r:CodeRelation {type: 'CALLS'}]-()
RETURN fn.name, fn.filePath, count(r) AS incoming
ORDER BY incoming DESC
LIMIT 30

-- Возможно dead code (никто не вызывает и не экспортирует)
MATCH (fn:Function)
WHERE NOT (()-[:CodeRelation {type: 'CALLS'}]->(fn))
  AND NOT (fn.isExported = true)
RETURN fn.name, fn.filePath
LIMIT 100

-- Классы с большим количеством методов (возможен God Class)
MATCH (c:Class)<-[:CodeRelation {type: 'MEMBER_OF'}]-(m:Method)
RETURN c.name, c.filePath, count(m) AS methodCount
ORDER BY methodCount DESC
LIMIT 20
```

---

## Разделение труда

| Вопрос | Инструмент |
|--------|-----------|
| Содержимое файла/символа | **Serena** `find_symbol include_body=true` |
| Что из себя представляет файл (обзор) | **Serena** `get_symbols_overview` |
| Regex / текстовый поиск | **Serena** `search_for_pattern` |
| Кто ссылается на этот символ | **Serena** `find_referencing_symbols` (точнее для конкретного символа) или GitNexus `context` (шире, с процессами) |
| Blast radius изменения | **GitNexus** `impact` |
| Границы модулей / кластеры | **GitNexus** `gitnexus://repo/.../clusters` |
| Сквозные сценарии | **GitNexus** `gitnexus://repo/.../processes` |
| Архитектурный Cypher-запрос | **GitNexus** `cypher` |
| Git-метаданные | `bash` через `git ...` |
| Диаграмма | Markdown + Mermaid в отчёте |

---

## Базовые bash-команды (разрешённые, неинвазивные)

```bash
git rev-parse HEAD                        # текущий коммит
git rev-parse --abbrev-ref HEAD           # текущая ветка
git log --format="%ci" | head -1          # дата последнего коммита
git log --format="%ci" | tail -1          # дата первого коммита
git log --oneline | wc -l                 # число коммитов
git shortlog -sne                         # контрибьюторы с count
git log --since="90 days ago" --oneline | wc -l   # активность за 90 дней

cloc . --exclude-dir=node_modules,dist,build,.git,vendor,target   # LOC
find . -type f -name "*.ext" | wc -l      # число файлов

# Manifest inspection (чтение, не установка!)
cat package.json
cat pyproject.toml
cat go.mod
cat Cargo.toml
```

Если `cloc` недоступен — сымитируй через `find . -type f \( -name '*.py' -o -name '*.ts' \) -print0 | xargs -0 wc -l`.

---

## Что делать, если инструмент не отвечает

1. Попробуй один раз — если таймаут/ошибка.
2. Проверь `list_repos` (GitNexus) / `get_current_config` (Serena).
3. Если всё ещё не работает — зафиксируй в `audit/00_setup.md` в разделе «Ограничения» и пометь затронутые фазы как деградированные.
4. Не блокируй пайплайн. Двигайся дальше.

---

Теперь перейди к `TEMPLATES.md`.
