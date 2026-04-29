# PHASE 03 — DEPENDENCIES & SUPPLY CHAIN

**Цель:** Оценить здоровье внешних зависимостей и внутренних межмодульных связей.

**Источники:**
- *The Twelve-Factor App* (12factor.net) — dependencies declaration.
- Snyk / OWASP — Software Composition Analysis.
- Ousterhout — «minimize dependencies» как принцип.

---

## 1. Входы
- `audit/02_architecture.md`, `.serena/memories/audit_phase_02`.
- Манифесты пакетных менеджеров (из фазы 00).

## 2. Чек-лист действий

### 2.1. Внешние зависимости — инвентаризация
Для каждого манифеста:

**Node.js (`package.json`):**
- [ ] Прямые deps / devDeps / peerDeps — число каждой категории.
- [ ] Lockfile есть? (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`). Если нет — finding `high`.
- [ ] `bash`: `npm ls --depth=0 --parseable 2>/dev/null | wc -l` — прямых зависимостей.
- [ ] `npm ls --all --parseable 2>/dev/null | wc -l` — транзитивных (если успевает).

**Python:**
- [ ] `pyproject.toml` vs `requirements*.txt` — как задеклареновано.
- [ ] Lockfile (`poetry.lock`, `requirements.lock`, `uv.lock`). Если нет — finding `high`.
- [ ] Версии закреплены (`==`) или плавающие (`>=`)? Плавающие — finding `medium`.

**Go:** `go.mod` + `go.sum`. Прямые deps, replace-директивы (подозрительно если указывают на локальные пути в main).

**Rust:** `Cargo.toml` + `Cargo.lock`. Naming convention проверять не нужно.

**Java:** `pom.xml` / `build.gradle*`. Есть ли lockfile (`gradle.lockfile`)?

**C#:** `*.csproj` + `packages.lock.json`.

**Ruby:** `Gemfile` + `Gemfile.lock`.

**PHP:** `composer.json` + `composer.lock`.

### 2.2. Устаревшие зависимости
Попробуй выполнить неинвазивные команды проверки (они не меняют код):
- [ ] Node: `npm outdated --json` (ничего не ставит, только сравнение).
- [ ] Python: `pip list --outdated --format=json` (требует активного окружения; если нет — пропусти с пометкой).
- [ ] Go: `go list -u -m all` (безопасно).
- [ ] Rust: `cargo outdated` (требует плагина — может не быть).
- [ ] Java: `mvn versions:display-dependency-updates` (долго, опционально).

Если команды недоступны — по манифестам и web search уточнить *только* для зависимостей без минорных обновлений больше 2 лет. Но не обязательная проверка в пайплайне.

Для каждой группы:
- Major behind > 1 версии — finding `low` (обсуждаемо).
- Major behind > 2 версии — finding `medium`.
- Deprecated / unmaintained (нет релизов > 2 лет, на GitHub архивирован) — finding `high`.
- Known CVE (если инструменты запустились) — finding `critical` или `high` по CVSS.

### 2.3. Supply chain security
Если доступны инструменты — запусти:
- [ ] `npm audit --json` / `npm audit --production --json`.
- [ ] `pip-audit --format=json` (если установлен).
- [ ] `osv-scanner --format=json .` (универсальный).
- [ ] `govulncheck ./...` (Go).

Если никакие не установлены — добавь finding `medium` уровня: «отсутствует автоматизированная SCA-проверка в процессе».

### 2.4. Лицензионная чистота
- [ ] Для каждой зависимости (топ-50 прямых): лицензия (извлекается из манифестов/реестров).
- [ ] Несовместимые лицензии (GPL-виды в проприетарном проекте): finding `medium` или `high` по контексту.
- [ ] Отсутствие лицензии самого проекта в репозитории: finding `low`.

### 2.5. Дублирующиеся и избыточные зависимости
- [ ] В Node: `npm ls <dupe>` / `npm dedupe --dry-run` — множественные версии.
- [ ] Обёртки вокруг одной функции (например `lodash` + `underscore` + `ramda`): finding `low`.
- [ ] Зависимости только для типов (`@types/*`) — проверь, что в devDeps, не в deps. Если в deps — finding `low`.

### 2.6. Неиспользуемые зависимости
- [ ] Для каждой прямой зависимости: есть ли её импорт в коде?
  - Node: `depcheck` (если установлен).
  - Вручную через Serena `search_for_pattern` на имя пакета — но это дорого, делай только для топ-30 крупнейших/центральных.
- [ ] Неиспользуемая → finding `low` (удалить).

### 2.7. Внутренние зависимости (из GitNexus)
- [ ] Circular imports на уровне модулей/файлов (не кластеров — это было в фазе 02):
  ```cypher
  MATCH path = (a)-[:CodeRelation {type: 'IMPORTS'}*2..5]->(a)
  RETURN path LIMIT 30
  ```
- [ ] Каждый цикл → finding `medium`/`high` в зависимости от длины (длинные циклы опаснее).

### 2.8. Манифест-гигиена
- [ ] `package.json`: есть `engines`, `scripts` (минимум `test`, `lint`, `build`)?
- [ ] `.nvmrc` / `.tool-versions` / `.python-version`? Версии toolchain зафиксированы?
- [ ] Отсутствие — finding `low`.

## 3. Артефакт — `audit/03_dependencies.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено**
3. **Ключевые наблюдения**
   - **Сводка по манифестам** — таблица `manifest | direct | transitive | lockfile? | pinned?`.
   - **Outdated** — таблица `package | current | latest | major-behind`.
   - **Vulnerabilities** — если запустилось, таблица `package | CVE | CVSS | fix`.
   - **Licenses** — сводная таблица (с выделением рисковых).
   - **Unused / duplicate** — списки.
   - **Internal circular imports** — таблица (если есть).
4. **Находки**
5. **Неполные проверки** (важно — многие инструменты могут быть недоступны)
6. **Контрольные вопросы**
   - **Q1.** Если сегодня выйдет critical CVE в одной из прямых зависимостей, знает ли команда способ её быстро обновить без ручного разруливания конфликтов? Если нет (нет lockfile / плавающие версии / нет CI SCA) — finding.
   - **Q2.** Есть ли зависимость, от которой труднее избавиться, чем заменить? Если центральная — finding `medium` (lock-in).
7. **Следующая фаза:** `phases/phase_04_code_quality.md`

## 4. Memory

```markdown
# Phase 03 memory
Completed: YYYY-MM-DD

Dependencies summary:
- manifests: [<pm>, ...]
- direct_deps_total: <N>
- locked: <yes/no/partial>
- outdated_major: <N>
- vulnerabilities_found: <N critical / N high / N medium>
- unused_deps: <count>
- internal_cycles: <count>

Next phase: phase_04_code_quality.md
```

## 5. Отчёт пользователю

> Фаза 3/10 завершена. Зависимости: <N> прямых (<M> транзитивных), <X> устаревших (major), <Y> с известными CVE. Lockfile <присутствует/отсутствует>. Добавлено <K> findings. Перехожу к фазе 4 — качество кода.

Перейди к `phases/phase_04_code_quality.md`.
