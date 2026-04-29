# PHASE 01 — INVENTORY

**Цель:** Получить полную нейтральную картину «что есть в репозитории». На этой фазе ничего не оцениваем, только описываем.

**Источники:**
- Feathers, *Working Effectively with Legacy Code* — «characterization before change».
- Hunt & Thomas, *The Pragmatic Programmer* — «tracer bullets».

---

## 1. Входы
- `audit/00_setup.md`, `.serena/memories/audit_phase_00`.

## 2. Чек-лист действий

### 2.1. Карта файловой структуры
- [ ] `list_dir` рекурсивно до глубины 3 по корню. Отметь верхнеуровневые папки.
- [ ] Bash: топ-20 самых больших файлов по LOC
  ```bash
  find . -type f \( -name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.tsx' -o -name '*.jsx' -o -name '*.java' -o -name '*.kt' -o -name '*.go' -o -name '*.rs' -o -name '*.rb' -o -name '*.cs' -o -name '*.cpp' -o -name '*.c' -o -name '*.php' -o -name '*.swift' \) \
    -not -path './node_modules/*' -not -path './dist/*' -not -path './build/*' -not -path './.git/*' \
    -exec wc -l {} + | sort -rn | head -21
  ```
- [ ] Топ-20 самых больших папок (суммарный LOC).
- [ ] Соотношение prod / test / config / docs (грубая оценка по папкам `test*`, `docs*` и расширениям).

### 2.2. Точки входа и публичный контракт
- [ ] Из GitNexus: `gitnexus://repo/{name}/processes` — получи список execution flows. Зафиксируй top-10 по сложности/количеству шагов.
- [ ] Если GitNexus недоступен: Serena `find_file` для типичных entry points (`main.*`, `index.*`, `cmd/*`, `bin/*`).
- [ ] HTTP API: `search_for_pattern` по маркерам роутинга (нейтральный перечень, не все сработают):
  - Python: `@app\.route|@router\.(get|post|put|delete|patch)|APIRouter|FastAPI|flask\.Blueprint`
  - Node: `app\.(get|post|put|delete|patch)\(|router\.(get|post|put|delete|patch)\(|@Controller|@Get\(|@Post\(`
  - Java/Kotlin: `@(Rest)?Controller|@GetMapping|@PostMapping|@RequestMapping`
  - Go: `http\.HandleFunc|r\.(GET|POST|PUT|DELETE)|chi\.(Get|Post)`
  - C#: `\[HttpGet|\[HttpPost|\[Route\(|ApiController`
- [ ] Спецификации: `find_file` для `openapi*`, `swagger*`, `*.proto`, `schema.graphql`, `asyncapi*`. Зафиксируй наличие.
- [ ] CLI: `find_file` для `argparse`, `click`, `typer`, `cobra`, `commander`, `yargs` — только как наличие/отсутствие.

### 2.3. Кластеры (сырой список, без интерпретации)
- [ ] `gitnexus://repo/{name}/clusters` — получи все функциональные сообщества.
- [ ] Для каждого top-10 кластера по размеру зафиксируй: имя/label, число символов, cohesion score (если GitNexus отдаёт).
- [ ] **Никаких оценок здесь** — это сырой факт. Интерпретация — в фазе 02.

### 2.4. Конфигурация (только наличие, без чтения содержимого)
- [ ] `find_file`: `.env*`, `config*`, `settings*`, `application*.yml|yaml|properties`, `appsettings*.json`, `*.config.js|ts`, `Dockerfile*`, `docker-compose*`, `k8s/`, `kustomize/`, `helm/`.
- [ ] Зафиксируй список. **Не читай `.env*` целиком** — секреты проверим в фазе 06 по безопасному паттерну.

### 2.5. Документация
- [ ] `README*`, `CONTRIBUTING*`, `ARCHITECTURE*`, `docs/`, `ADR*`, `CHANGELOG*`, `LICENSE*`.
- [ ] Для каждого: есть/нет, размер в строках, дата последнего изменения (`git log -1 --format=%ci -- <file>`).
- [ ] Прочитай `README.md` целиком (если есть и < 500 строк). Это повлияет на интерпретацию в следующих фазах.
- [ ] Если есть `docs/adr/` — зафиксируй список ADR.

### 2.6. Git-мета (дополнительно к фазе 00)
- [ ] Файлы, изменявшиеся чаще всего за последние 180 дней (потенциальные hot-spots):
  ```bash
  git log --since="180 days ago" --name-only --pretty=format: | grep -v '^$' | sort | uniq -c | sort -rn | head -30
  ```
- [ ] Соотношение authors per hot-spot (много разных авторов в одном файле = возможно proxy для fragility / shotgun surgery).

### 2.7. Зависимости (только перечисление, deep-dive в фазе 03)
- [ ] Для каждого найденного манифеста — число прямых зависимостей (первый уровень).

## 3. Что ищем на этой фазе

**Пока — ничего не оцениваем.** Собираем факты. Единственные возможные находки здесь — структурные:
- Отсутствие README / CONTRIBUTING / LICENSE (`low` findings).
- Файлы > 1000 строк (`medium`, пометка на фазу 04 для проверки).
- Папки, не соответствующие своему названию (увидишь в processes/clusters фазы 02).

## 4. Артефакт — `audit/01_inventory.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено** (чек-лист с отметками)
3. **Ключевые наблюдения**
   - **Структура верхнего уровня** — дерево папок до глубины 2 (можно ascii).
   - **Языки и размеры** — таблица (уже из фазы 0, но уточнённая).
   - **Топ-20 больших файлов** — таблица `файл | LOC | язык`.
   - **Hot-spots (180 дней)** — таблица `файл | коммитов | уникальных авторов`.
   - **Точки входа** — список с подтверждением (GitNexus process / файл).
   - **Публичный контракт** — API эндпоинты (число + примеры), CLI-флаги (число), очереди/топики (если видно).
   - **Кластеры (сырой)** — таблица.
   - **Конфигурация** — список файлов.
   - **Документация** — таблица `документ | есть? | LOC | last modified`.
4. **Находки** (обычно 2–5, уровней low/info/medium)
5. **Неполные проверки**
6. **Контрольные вопросы (ответить письменно)**
   - **Q1.** Можешь ли ты одним абзацем (5–6 предложений) описать, **что делает** эта система, опираясь только на собранные факты? Если нет — это finding уровня `medium` (missing architecture overview).
   - **Q2.** Соответствует ли структура папок ментальной модели кластеров из GitNexus? Если совсем нет — зафиксируй для фазы 02.
7. **Следующая фаза:** `phases/phase_02_architecture.md`

### Evidence в подпапке
- `audit/evidence/01_inventory/dir_tree.txt` — полное дерево.
- `audit/evidence/01_inventory/top_files.txt` — полный список больших файлов.
- `audit/evidence/01_inventory/hotspots.txt` — полная таблица hot-spots.

## 5. Memory

`.serena/memories/audit_phase_01`:

```markdown
# Phase 01 memory
Completed: YYYY-MM-DD HH:MM

Inventory highlights:
- top-level dirs: [<list>]
- primary module areas (self-observed, not yet GitNexus-validated): [<list>]
- entry points: [<list>]
- public API surface: <N endpoints / commands>
- hotspots top-5: [<file>, <file>, ...]
- large files (>500 LOC): <N>
- docs quality: <качественная оценка — есть/нет/частично>

GitNexus clusters observed: <N>, top-5 by size: [<list>]

For next phases:
- phase_04 needs to look at: [<large files list>]
- phase_09 needs to look at hotspots

Findings added: F-00XX to F-00YY
Next phase: phase_02_architecture.md
```

Обнови `audit_progress`.

## 6. Отчёт пользователю

> Фаза 1/10 завершена. Инвентаризация: ~<N> файлов, <M> LOC в <K> основных папках. <X> точек входа, <Y> публичных API эндпоинтов, <Z> функциональных кластеров. Топ hot-spot: `<file>` (<commits> коммитов за 180 дней). Перехожу к фазе 2 — архитектура.

Перейди к `phases/phase_02_architecture.md`.
