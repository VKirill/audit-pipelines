# 01 — ORCHESTRATOR

**Это главный диспетчер пайплайна. Ты вернёшься в этот документ между фазами.**

> Контракт пайплайна:
> 1. **Детерминированные скрипты-валидаторы** в `scripts/` — exit gate не «совет», а исполнимая проверка. Если `validate_phase.sh NN` падает, фаза не считается завершённой.
> 2. **Обязательные поля `confidence_rationale` и `exploit_proof`** в findings — без них скрипт отвергает finding.
> 3. **Мини-фазы:** `02b Trust Map`, `06b Money & State Invariants`, `10a Self-Audit`. Phase 11 deep-dive **обязателен** при ≥ 1 critical finding.
> 4. **Внешние инструменты собираются заранее** через `scripts/run_external_tools.sh`.
> 5. **Финальный gate** `scripts/finalize.sh` — всё или ничего.
> 6. **Adversary review** перед ROADMAP — агент сам ищет причины не доверять собственному аудиту.

---

## 1. Архитектура пайплайна

Пайплайн состоит из **10 основных фаз + 3 мини-фаз + 1 опциональная** (12+1, при наличии critical — обязательны все).

```
phase_00_setup.md              → подготовка, проверка инструментов, запуск scripts/run_external_tools.sh
phase_01_inventory.md          → инвентаризация
phase_02_architecture.md       → структура, кластеры, слои
phase_02b_trust_map.md         → карта потоков данных (sources → sinks → trust)
phase_03_dependencies.md       → supply chain
phase_04_code_quality.md       → читаемость, сложность
phase_05_error_handling.md     → resilience
phase_06_security.md           → OWASP, secrets, auth
phase_06b_money_invariants.md  → финансовые/state-инварианты (если применимо)
phase_07_tests.md              → пирамида, покрытие
phase_08_ops_observability.md  → CI/CD, логи, метрики
phase_09_performance.md        → N+1, sync I/O, hot paths
phase_10_synthesis_roadmap.md  → ROADMAP
phase_10a_self_audit.md        → рефлексия пайплайна, adversary review
phase_11_deep_dive.md          → forensic-grade (обязателен при ≥ 1 critical)
```

---

## 2. Контракт между фазами

Каждая фаза:
- читает артефакты предыдущих фаз;
- выполняет проверки строго по своему чек-листу;
- **запускает `scripts/validate_phase.sh NN`** — это hard gate, exit ≠ 0 = фаза не завершена;
- записывает `audit/NN_<n>.md` — отчёт;
- добавляет находки в `audit/findings.jsonl` (со всеми обязательными полями схемы);
- наполняет `audit/evidence/NN_<n>/` минимум двумя файлами из обязательного списка (см. `scripts/required_evidence_files.sh NN`);
- сохраняет состояние в `.serena/memories/audit_phase_NN`;
- обновляет `.serena/memories/audit_progress`;
- возвращает управление → сообщает пользователю статус → переходит к следующей.

---

## 3. Правила поведения агента (критично!)

### 3.1. Read-only
Никаких правок в коде проекта. Только чтение проекта + запись в `audit/`, `.serena/memories/`. Если `.serena/project.yml` существует — убедись, что там `read_only: true`. Если файла нет — создай.

### 3.2. Evidence-based
Каждое утверждение в отчёте — со ссылкой на файл+строки или результат инструмента. **Без цитаты конкретных строк утверждение не может попасть в отчёт.**

### 3.3. Калибровка confidence

Confidence в finding **должен** быть назначен по строгим правилам. Нарушение → `validate_phase.sh` его поймает.

| Confidence | Условия — **все** должны быть выполнены |
|------------|-----------------------------------------|
| `high`     | (а) ты прочитал конкретные строки и цитируешь их в `evidence`; (б) проблема видна статически, без рантайма; (в) нет правдоподобного объяснения, делающего это не проблемой; (г) **обязательно** заполнено `confidence_rationale` ≥ 40 символов и `location.lines` непустой. |
| `medium`   | (а) ты видел паттерн в коде; (б) но эффект зависит от поведения, которое ты не можешь подтвердить без профайлера/данных/интервью; (в) или ручная валидация сделана только для части случаев. |
| `low`      | (а) срабатывание эвристики/grep; (б) ручная валидация не проводилась; (в) возможны false positives. |

**Запреты (нарушение = откат finding на ступень ниже):**
- `severity: critical` без поля `exploit_proof` ≥ 40 символов с конкретным сценарием атаки.
- `confidence: high` для performance-findings, кроме трёх случаев: `sync I/O в async`, `unbounded memory cache`, `N+1 с подтверждением вызова в цикле`.
- `confidence: high` для code-quality findings без ручной проверки тела функции.
- `confidence: high` для dependency findings без запуска `npm audit`/`osv-scanner`/`pip-audit`.
- `confidence: high` для architecture findings без построения dependency matrix или прохода `impact` через GitNexus.

**Перед тем как присвоить `high`, останови себя и заполни `confidence_rationale`** — конкретно: «прочитал строки X-Y в файле Z через `find_symbol`, увидел N веток, рантайм не нужен потому что …». Если не можешь сформулировать — понизь до `medium`.

### 3.4. Запрет «допустимо»

В отчётах фаз **запрещены** формулировки: «допустимо», «приемлемо», «можно считать», «соответствует §4.2 (даже если не соответствует)». Если правило нарушено — пиши явно: «нарушение, причина: …, действие: …». Скрипты ловят нарушения; не пытайся их обойти словами.

### 3.5. Экономия контекста
- Не читай файлы целиком, если хватит `get_symbols_overview` + точечного `find_symbol`.
- Большие файлы — по диапазонам через `view_range`.
- Перед чтением файла > 500 строк — сначала `get_symbols_overview`.
- Но **если фаза требует ручной проверки тела функции**, ты обязан её прочитать. Экономия контекста не отменяет exit gate.

### 3.6. Прогрессивная память
После каждой фазы:
- `write_memory audit_phase_NN` — 10–20 строк резюме;
- `write_memory audit_progress` — общий прогресс.

### 3.7. Не изобретать метрики
Любая метрика — либо классическая (LOC, CC, DORA-4, blast radius), либо с явным определением в тексте.

### 3.8. Язык
Отчёты — на русском. Имена файлов, символов, команд — как в коде.

### 3.9. Формат рекомендаций
НЕТ: «Улучшите тесты», «добавьте логирование».
ДА: «В `AuthService.validateToken` (src/auth/service.ts:45-120) есть 4 ветки ошибок, покрыта только первая (tests/auth.spec.ts:10). Добавить 3 недостающие unit-проверки».

### 3.10. Anti-recursion в инструментах

Если один и тот же запрос к `gitnexus_query` / `cypher` / `find_symbol` вернул пусто **3 раза подряд** — обязан переключиться на fallback из §7, не пробовать четвёртый раз. Счётчик: фиксируй в `.serena/memories/audit_tool_failures` (формат: `tool;query_hash;count`).

### 3.11. Размер отчётов
Каждый отчёт фазы — **минимум 150 строк, максимум ~400**. Детали — в `audit/evidence/NN_<n>/`. Если отчёт короче 150 — добавь раздел `## Проверено и чисто` с ≥ 5 пройденных пунктов с конкретикой, или вернись и допиши.

### 3.12. Контроль завершения фазы — exit gate

В конце каждой фазы **обязательно** запусти:

```bash
bash audit_pipeline/scripts/validate_phase.sh NN
```

Если exit ≠ 0 — фаза не завершена. Прочитай вывод, исправь findings/отчёт, перезапусти. **Не переходи к следующей фазе с failed gate.**

Дополнительно: вызови `think_about_task_adherence` и `think_about_whether_you_are_done` (если доступны).

---

## 4. Exit Gate — теперь скриптовый

`validate_phase.sh NN` проверяет (полный список см. в `scripts/validate_phase.sh`):

1. **Квота findings** для размера проекта.
2. **Распределение confidence** в фазе (нет 100%-моноблока при ≥ 3 findings).
3. **Все обязательные evidence-файлы** созданы.
4. **Все 7 разделов** в отчёте.
5. **Длина отчёта** ≥ 150 (или есть `## Проверено и чисто`).
6. **Каждый `confidence: high`** имеет `confidence_rationale` и `location.lines`.
7. **Каждый `severity: critical`** имеет `exploit_proof`.

### Глобальные финальные gates (через `finalize.sh`):

- `validate_confidence.py` — общее распределение high/medium/low в пределах §4.2 (high% ≤ 60%, low% ≥ 5%, medium% не пусто).
- `check_evidence_citations.py` — все `location.file:lines` резолвятся, цитаты из `evidence` действительно есть в файлах.
- `_meta.json` сгенерирован, `verdict: pass`.
- Phase 10a Self-Audit, `_known_unknowns.md`, `_adversary_review.md` присутствуют.
- Phase 11 deep-dive присутствует, **если** есть critical findings.

### Минимальные квоты findings (для размера M):

| Фаза | Минимум | Если меньше — что делать |
|------|--------|--------------------------|
| 00 setup | 0 | — |
| 01 inventory | 0 | — |
| 02 architecture | **≥ 5** | перечитай shallow/deep, проверь cypher |
| 02b trust map | **≥ 5** | пройди sources→sinks |
| 03 dependencies | **≥ 3** | запусти npm audit / pip-audit |
| 04 code quality | **≥ 8** | вернись к топ-20 большим файлам и читай руками |
| 05 error handling | **≥ 5** | grep по catch, проверь каждое место |
| 06 security | **≥ 5** | пройди OWASP Top 10 явно |
| 06b money invariants | **≥ 3** | если есть финансовый домен |
| 07 tests | **≥ 3** | покрытие central symbols, skipped |
| 08 ops | **≥ 3** | CI, логи, метрики, health |
| 09 performance | **≥ 3** | N+1, sync I/O, pagination |
| 10/10a/11 | 0 | — (синтез/рефлексия/deep-dive) |

Размеры XS/S — квоты ÷2/÷3, L/XL — ×2/×3 (выполняется автоматически в `validate_phase.sh` на основе `.serena/memories/audit_phase_00.size`).

---

## 5. Последовательность действий

```
1. Прочитай REFERENCE_TOOLS.md и TEMPLATES.md.
2. Запусти  bash audit_pipeline/scripts/run_external_tools.sh  (один раз, ~5-10 мин).
3. phase_00 → запусти validate_phase.sh 00 → отчитайся пользователю.
4. phase_01 → validate_phase.sh 01 → отчёт.
5. phase_02 → validate_phase.sh 02 → отчёт.
6. phase_02b (если применимо: есть HTTP-API / external inputs) → validate_phase.sh 02b.
7. ... phases 03 … 09 (см. §1).
8. phase_06b ВСТАВИТЬ если в проекте есть денежные операции / state-машины с инвариантами.
9. phase_10 → ROADMAP черновик.
10. phase_10a Self-Audit → adversary review → may require возврат к фазам.
11. phase_11 deep-dive (обязателен при ≥ 1 critical).
12. bash audit_pipeline/scripts/finalize.sh → exit 0 = готово.
13. Финальный tl;dr пользователю.
```

**Между фазами не импровизируй.** Если во время фазы N заметил находку для фазы M>N — запиши в `.serena/memories/audit_cross_phase_notes`, в фазе M проверь системно.

---

## 6. Адаптация под размер проекта

| Размер | LOC | Корректировка квот findings |
|--------|-----|----------------------------|
| XS | < 2k | квоты ÷ 3 (мин. 1) |
| S | 2k–10k | квоты ÷ 2 |
| M | 10k–100k | квоты как в §4 |
| L | 100k–1M | квоты × 2, семплируй топ-30 |
| XL | > 1M | квоты × 3, разбей на подпроекты |

`validate_phase.sh` берёт размер из `.serena/memories/audit_phase_00`. Если файла нет — считает M.

---

## 7. Fallback-протоколы для деградации инструментов

### 7.1. Serena недоступна
**Признаки:** `activate_project` не работает между вызовами, `find_symbol` возвращает пусто.

**Протокол:**
1. `get_current_config` — активен ли проект.
2. Повтори `activate_project` с абсолютным путём.
3. Если стабильно не работает — **переключись на bash + ripgrep**:
   - `get_symbols_overview` → `rg -nE "^(export |)(async |)(function|class|const|interface|type) " <file>`
   - `find_symbol` → `rg -n "function <name>|class <name>|const <name> =" <path>`
   - `find_referencing_symbols` → `rg -n "<name>" --type=ts --type=py`
   - `search_for_pattern` → `rg -E "<pattern>"`
4. В `audit/00_setup.md` зафиксируй: «Serena деградирована, symbol-level через grep».
5. **Глубина анализа НЕ падает**, только скорость.

### 7.2. GitNexus недоступен / cypher пуст
**Признаки:** `list_repos` не показывает проект, cypher возвращает 0.

**Протокол:**
1. Прочитай `gitnexus://repo/{name}/schema` — схема могла измениться.
2. Адаптируй запрос (без WHERE, без JOIN).
3. Если 3 попытки подряд пустые — **fallback на ручной import-граф**:
   - Phase 02: `rg -hE "^(import|from)" --type ts --type py | awk -F: '{print $1}' | sort -u | wc -l`
   - Phase 04: `rg -nE "^(export )?class " | head -50`
   - Central symbols: `rg -h <name> --type ts | wc -l` для топ-кандидатов.
4. Зафиксируй ограничение в `audit/00_setup.md`.

### 7.3. Пакетный аудит зависимостей недоступен
1. Попробуй `npm audit --registry=https://registry.npmjs.org`.
2. `osv-scanner` — работает с lockfile без install.
3. Если ничего не работает — прочитай lockfile и зафиксируй версии известных уязвимых пакетов как `low/medium`.
4. Не оставляй фазу 03 с 0 findings.

### 7.4. `cloc` недоступен
```bash
find . -type f \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.kt' -o -name '*.rb' -o -name '*.cs' -o -name '*.php' -o -name '*.swift' -o -name '*.c' -o -name '*.cpp' -o -name '*.vue' \) \
  -not -path '*/node_modules/*' -not -path '*/dist/*' -not -path '*/build/*' -not -path '*/.git/*' -not -path '*/vendor/*' \
  -exec wc -l {} + | tail -1
```
`scripts/run_external_tools.sh inventory` уже это делает и пишет в `evidence/01_inventory/file_counts.txt`.

### 7.5. gitleaks недоступен
`scripts/run_external_tools.sh secrets` запускает grep-fallback и пишет в `evidence/06_security/secret_scan.txt`. `secret_scan.txt` всегда не пуст.

---

## 8. Структура артефактов на выходе

```
audit/
├── 00_setup.md
├── 01_inventory.md
├── 02_architecture.md
├── 02b_trust_map.md          ← НОВОЕ
├── 03_dependencies.md
├── 04_code_quality.md
├── 05_error_handling.md
├── 06_security.md
├── 06b_money_invariants.md   ← НОВОЕ (если применимо)
├── 07_tests.md
├── 08_ops_observability.md
├── 09_performance.md
├── 10_synthesis.md
├── 10a_self_audit.md         ← НОВОЕ — обязательный
├── 11_deep_dive.md           ← обязательный при ≥ 1 critical
├── ROADMAP.md                ← ГЛАВНЫЙ РЕЗУЛЬТАТ
├── findings.jsonl
├── _meta.json                ← НОВОЕ — генерируется finalize.sh
├── _known_unknowns.md        ← НОВОЕ — Phase 10a
├── _adversary_review.md      ← НОВОЕ — Phase 10a
└── evidence/
    ├── 02_architecture/
    ├── 02b_trust_map/
    └── ...
```

---

## 9. Что делать при возобновлении сессии

1. Прочитай `.serena/memories/audit_progress`.
2. Прочитай `.serena/memories/audit_phase_XX` для последней завершённой фазы.
3. Прочитай `audit/findings.jsonl` и `audit/_meta.json` (если есть).
4. Запусти `bash audit_pipeline/scripts/validate_phase.sh XX` для последней фазы — убедись что она прошла gate. Если не прошла — сначала допили её.
5. Продолжи со следующей фазы.

---

## 10. Финальные обязательства

Пайплайн считается завершённым, только если **`bash audit_pipeline/scripts/finalize.sh` возвращает 0**. Скрипт проверяет:

- все `validate_phase.sh NN` для каждой созданной фазы;
- `validate_confidence.py` (глобальное распределение);
- `check_evidence_citations.py` (все цитаты резолвятся);
- `audit/ROADMAP.md`, `audit/_known_unknowns.md`, `audit/_adversary_review.md`, `audit/10a_*.md` присутствуют;
- если есть critical findings — `audit/11_*.md` присутствует;
- `audit/_meta.json` сгенерирован, `verdict: pass`;
- пользователю отдан финальный tl;dr.

Теперь перейди к `REFERENCE_TOOLS.md`.
