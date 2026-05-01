# PHASE 04 — CODE QUALITY

**Цель:** Найти code smells на уровне функций, классов, модулей. Оценить читаемость и когнитивную нагрузку.

**Источники:**
- Fowler, *Refactoring* 2e — каталог smells и refactorings (гл. 3).
- Martin, *Clean Code* — имена (гл. 2), функции (гл. 3), комментарии (гл. 4), классы (гл. 10).
- McConnell, *Code Complete* 2e — §5 Design, §7 Routines, §11 Naming, §17 Unusual Control Structures.
- Kernighan & Pike, *The Practice of Programming* — простота и ясность.
- Ousterhout, *Philosophy of Software Design* — комментарии как первый класс.

**Exit gate этой фазы:**
- **≥ 8 findings** для M-проекта;
- **обязательно прочитаны тела** не менее **20 функций** из хотспотов (не только их имена/LOC);
- минимум 2 файла в `audit/evidence/04_code_quality/`: `large_functions.md` + `todo_grep.txt`;
- ≥ 150 строк в отчёте;
- разумное распределение confidence (не все `high`).

---

## 1. Входы
- `audit/01_inventory.md` — топ-20 больших файлов, hotspots.
- `audit/02_architecture.md` — shallow modules, central symbols (приоритет проверки).

---

## 2. Чек-лист проверок

### 2.1. Топ-20 функций для ОБЯЗАТЕЛЬНОГО ручного чтения

Перед всеми smells — составь список и прочитай тела. Это **требование пайплайна**: без ручного чтения ты не имеешь права писать `confidence: high` про качество кода.

- [ ] Соберите кандидаты:
  - Топ-20 файлов по LOC (из evidence фазы 01).
  - Топ-10 hot-spots по частоте коммитов (из фазы 01).
  - Shallow/god modules из фазы 02.
- [ ] Для каждого файла получи список функций:
  - Через Serena: `get_symbols_overview`, затем для самых больших — `find_symbol include_body=true`.
  - Через fallback: `grep -nE "^(export )?(async )?(function|const [A-Za-z_]+ =|class) "` + ручное чтение диапазонов.
- [ ] Выбери **20 функций** с наибольшим LOC.
- [ ] **Прочитай тело каждой.** Для каждой зафиксируй в таблице:
  | file:symbol | LOC | Примерная CC | Вложенность (max if/for) | Ветки ошибок | Кол-во параметров | Проблемы |
  |-------------|-----|--------------|---------------------------|---------------|-------------------|----------|
- [ ] Сохрани таблицу в `audit/evidence/04_code_quality/large_functions.md`.

**CC (cyclomatic complexity) считается грубо:** `1 + (число if, else if, case, for, while, catch, &&, ||, тернарников)`. Не идеал, но достаточно для классификации.

### 2.2. Long Function (Fowler)

- [ ] Из таблицы большие функции: LOC > 80 → кандидат на finding `medium`; LOC > 150 → `high`; LOC > 300 → `critical`.
- [ ] Проверь через GitNexus `impact` / ручной `grep`, **не dead ли это код**. Dead long function → finding `low` (удалить), не `high` (рефакторить).
- [ ] Для каждой подтверждённой: рекомендация Extract Method с указанием 2–4 кандидатов-участков для извлечения (читаешь тело и говоришь: «строки X-Y — это valiдация, можно вынести; строки Z-W — dispatch, можно вынести»).

### 2.3. Большие классы / god class (Fowler §10, Clean Code)

**Через GitNexus:**
- [ ] Cypher:
  ```cypher
  MATCH (c:Class)<-[:CodeRelation {type: 'MEMBER_OF'}]-(m)
  WHERE m:Method OR m:Function
  WITH c, count(m) AS method_count
  WHERE method_count > 15
  RETURN c.name, c.filePath, method_count
  ORDER BY method_count DESC
  ```

**Через fallback grep:**
- [ ] `grep -c "^\s*\(async \)\?\(public\|private\|protected\)\? " <class-file>` — счёт методов в классе.
- [ ] Для TS/JS: считать стрелочные методы `name\s*=\s*(async )?(\(|function)` + обычные `methodName(`.

- [ ] Классы > 20 методов или > 500 LOC → finding `medium`/`high`.
- [ ] Для подозрительных — проверь cohesion: делают ли методы разные вещи с разными полями (low cohesion = god class).

### 2.4. Именование (Clean Code §2, McConnell §11)

Выборочно (топ-30 публичных API из фазы 02):
- [ ] Абстрактные имена без смысла: `Manager`, `Handler`, `Helper`, `Util*`, `Data`, `Info`, `Service` без квалификатора, `Common`, `Base` без наследников. Для каждого массового случая (встречается > 5 раз) → finding `low`.
- [ ] Несогласованные префиксы/суффиксы: `User`, `UserDTO`, `UserModel`, `UserEntity`, `UserPOJO` как синонимы → finding `medium`.
- [ ] Аббревиатуры без словаря: `qry`, `usr`, `mng`, `tmp` в публичных именах → finding `low`.
- [ ] Имена, противоречащие поведению: функция `getUser` делающая `INSERT`; флаг `isDisabled`, инвертированный в теле. Проверить топ-20 критичных → каждое → finding `medium`.
- [ ] Boolean-параметры в публичных API без named args (особенно > 1) → finding `medium` (Control Couple — Fowler).

### 2.5. Дублирование (Fowler — Duplicated Code)

- [ ] Если установлен `jscpd`, `simian`, `pmd-cpd` — запустить через bash.
- [ ] Иначе — через GitNexus `query` для семантически похожих функций или ручной `grep` на характерные сигнатуры.
- [ ] Порог: 5+ повторов блока > 10 строк → finding `medium`.
- [ ] Примеры (3–5) сохрани в `audit/evidence/04_code_quality/duplication_samples.md`.

### 2.6. Feature Envy (Fowler §3)

- [ ] Через cypher: функции, которые вызывают методы *другого* класса чаще, чем свои:
  ```cypher
  MATCH (caller:Method)-[:CodeRelation {type: 'MEMBER_OF'}]->(own:Class)
  MATCH (caller)-[r:CodeRelation {type: 'CALLS'}]->(callee:Method)
  -[:CodeRelation {type: 'MEMBER_OF'}]->(target:Class)
  WHERE own <> target
  WITH caller, own, target, count(r) AS external_calls
  WHERE external_calls > 5
  RETURN caller.name, own.name, target.name, external_calls
  ORDER BY external_calls DESC
  LIMIT 30
  ```
- [ ] Каждый значимый случай → finding `low`/`medium` (Move Method).

### 2.7. Primitive Obsession & Data Clumps (Fowler)

- [ ] `search_for_pattern` / grep на функции с длинной сигнатурой (> 5 параметров):
  ```
  function\s+\w+\([^)]{120,}\)
  def\s+\w+\([^)]{120,}\):
  func\s+\w+\([^)]{120,}\)
  ```
- [ ] Если одни и те же ≥ 3 параметра повторяются в ≥ 5 функциях → data clump, finding `medium` (Introduce Parameter Object).
- [ ] Строки/int вместо value objects для email, id, money, date-range → finding `low` (primitive obsession).

### 2.8. Shotgun Surgery (Fowler)

- [ ] Для центральных символов фазы 02 запусти `impact` (upstream).
- [ ] Если изменение одного символа требует обновления > 10 мест в > 3 кластерах → shotgun surgery, finding `high` (Inline Method / Move Method).

### 2.9. Divergent Change

- [ ] Из git-hotspots фазы 01: файл, который изменяется по очень разным причинам (много разных авторов × разнородные commit messages).
- [ ] `git log --oneline <file> | head -30` — если темы коммитов несвязанные → finding `medium`.

### 2.10. TODO / FIXME / HACK (ОБЯЗАТЕЛЬНО)

- [ ] `search_for_pattern` / grep:
  ```
  TODO|FIXME|HACK|XXX|@deprecated|@hack
  ```
- [ ] Для топ-50: `git blame -L <line>,<line> <file>` — возраст.
- [ ] Сохрани полный список в `audit/evidence/04_code_quality/todo_grep.txt`.
- [ ] TODO старше 180 дней → finding `low`; старше 2 лет → `medium` (мёртвая метка).
- [ ] `FIXME` / `HACK` — сразу `medium`, уточнить в фазе 10.

### 2.11. Закомментированный код

- [ ] Эвристика: блоки ≥ 10 подряд строк `//...` / `#...` / `--...` без содержимого документации.
- [ ] `search_for_pattern` на такие паттерны; выборочная проверка. → finding `low` (удалить, git помнит).

### 2.12. Магические числа и строки

- [ ] `search_for_pattern`: числовые литералы в условиях (`> \d{2,}`, `== \d{3,}`). Строковые enum-подобные в switch/if-else.
- [ ] Топ-20 самых часто повторяющихся → finding `low` (Replace Magic Number with Symbolic Constant).

### 2.13. Комментарии (Clean Code §4, Ousterhout §13)

- [ ] Комментарии, описывающие *что* делает строка (шум): finding `info` группировкой.
- [ ] Отсутствие комментариев у публичных API центральных модулей → finding `medium`.
- [ ] Комментарии, противоречащие коду: finding `high` (немедленно править).

### 2.14. Уровни абстракции (Clean Code §3)

Для топ-10 длинных функций:
- [ ] Смешиваются ли высокоуровневые вызовы (`user.save()`) и низкоуровневые (`buf[i] = x & 0xFF`) в одной функции?
- [ ] Да → finding `medium` (Extract Method чтобы выровнять уровни).

### 2.15. Mutable global state

- [ ] `search_for_pattern`:
  - JS/TS: `let\s+\w+\s*=` на module-level (не в функциях);
  - Python: globals в модуле (без ALL_CAPS), `global` в функциях.
  - Go: package-level `var` без `const`.
- [ ] Глобальное мутабельное состояние в бизнес-логике → finding `medium`/`high`.

---

## 3. Приоритизация проверок для L/XL

Для больших проектов семпл:
- Топ-20 больших файлов (фаза 01).
- Топ-20 hotspots (фаза 01).
- Топ-20 центральных символов (фаза 02).
- Shallow modules (фаза 02).

Пересечения этих множеств — **обязательная проверка**.

---

## 4. Quota check перед завершением

- [ ] **≥ 8 findings** для M-проекта. Если меньше — вернись к §2.1, прочитай больше функций руками.
- [ ] **Прочитаны тела ≥ 20 функций** — это фиксируется в `large_functions.md`.
- [ ] **Разумное распределение confidence** (не все `high`).
- [ ] `large_functions.md` и `todo_grep.txt` созданы.

---

## 5. Артефакт — `audit/04_code_quality.md`

### Обязательные разделы
1. **Цель фазы**
2. **Что проверено** (чек-лист с отметками)
3. **Ключевые наблюдения**
   - **Distribution of long functions** — гистограмма по диапазонам LOC.
   - **Top-20 worst functions** — таблица `file:symbol | LOC | CC | callers | recommendation`.
   - **God classes** — таблица.
   - **Naming issues** — примеры.
   - **Duplication** — сводная.
   - **Feature envy / shotgun surgery / divergent change** — примеры.
   - **TODO/FIXME/HACK** — сводка по возрасту.
   - **Magic numbers / primitives** — сводка.
4. **Находки**
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Сколько в среднем минут займёт у нового разработчика понимание топ-5 центральных функций? Обоснуй. Если > 30 минут для одной функции → finding.
   - **Q2.** Какие 3 файла ты бы рефакторил первыми и почему? Это войдёт в ROADMAP.
7. **Следующая фаза:** `phases/phase_05_error_handling.md`

---

## 6. Memory

```markdown
# Phase 04 memory
Completed: YYYY-MM-DD

Quality summary:
- functions_read_manually: <N>
- long_functions_gt_50_loc: <N>
- functions_cc_gt_20: <N>
- god_classes: <N>
- duplication_hotspots: <N>
- naming_issues_flagged: <N>
- todo_fixme_total: <N> (aged >1yr: <N>)

Top candidates for refactoring (for ROADMAP):
1. <file:symbol> — <reason>
2. ...

Next phase: phase_05_error_handling.md
```

---

## 7. Отчёт пользователю

> Фаза 4/10 завершена. Качество: прочитано <N> функций вручную, <M> длинных функций, <K> god classes, <L> мест с дублированием, <P> устаревших TODO. Топ-3 кандидата на рефакторинг: <список>. Добавлено <N> findings. Перехожу к фазе 5 — обработка ошибок.

Перейди к `phases/phase_05_error_handling.md`.
