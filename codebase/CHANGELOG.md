# CHANGELOG — audit_pipeline

## v3 (2026-04-23)

**Главная идея v3:** v2 ввёл правила, но не имел механизма принуждения. Агент мог обойти `§4.2 распределение confidence` фразой «допустимо». v3 превращает правила в исполнимые скрипты, которые **падают** при нарушении.

### Added — детерминированные валидаторы (`scripts/`)

| Скрипт | Назначение | Когда запускается |
|--------|-----------|-------------------|
| `scripts/validate_phase.sh NN` | Per-phase exit gate: квота, размер, evidence, JSON, разделы, моноблок, rationale, exploit_proof | Агентом в конце каждой фазы |
| `scripts/validate_confidence.py` | Глобальное распределение high/medium/low; per-phase моноблок; конкретные нарушения по правилам §4.2 | Phase 10a + finalize |
| `scripts/check_evidence_citations.py` | Каждый `location.file:lines` высоко-confidence finding'а резолвится в реальный файл; цитаты в `evidence` найдены в файлах | Phase 10a + finalize |
| `scripts/required_evidence_files.sh NN` | Печатает список обязательных evidence для фазы | Справочник для агента |
| `scripts/run_external_tools.sh [step]` | Сборщик cloc / git stats / npm audit / gitleaks / coverage в `audit/evidence/` — никогда не падает, ставит placeholder если инструмента нет | Phase 00 (один раз) |
| `scripts/generate_meta_json.py` | Машинная сводка `audit/_meta.json` с verdict pass/fail | finalize |
| `scripts/finalize.sh` | Единый финальный gate: всё или ничего | После Phase 10a (и Phase 11 если есть critical) |
| `scripts/lib/common.sh` | Общие функции: квоты, evidence-список, разрешение фаз | Sourced другими скриптами |

### Added — обязательные поля в findings

- `confidence_rationale` (≥ 40 символов) — обязательно при `confidence: high`. Описывает что именно прочитал и какой инструмент это подтвердил.
- `exploit_proof` (≥ 40 символов) — обязательно при `severity: critical`. Конкретный сценарий атаки с PoC-командой.
- `status: "open"|"merged"` + `merged_into` для дедуп-traceability.

### Added — новые мини-фазы

- `phases/phase_02b_trust_map.md` — карта потоков недоверенных данных (sources → sinks → trust). Снимает с phase 06 повторяющуюся работу по injection/IDOR/SSRF.
- `phases/phase_06b_money_invariants.md` — финансовые/state инварианты: ACID, compensation, idempotency, race на shared state. Запускается только если есть финансовый/state-критический домен.
- `phases/phase_10a_self_audit.md` — рефлексия пайплайна: запуск валидаторов, resample 3 случайных high-finding'а с manual recheck, premortem (Kahneman), adversary review (10+ причин не доверять), stop-words audit. **Обязательная фаза.**

### Changed — обязательность Phase 11

- v2: phase 11 deep-dive была опциональной всегда.
- v3: при ≥ 1 critical finding phase 11 **обязательна**. `finalize.sh` падает без `audit/11_*.md` в этом случае. Агент сам выбирает зону по subcategory первого critical и крупнейшему concentration.

### Added — финальные артефакты

- `audit/_meta.json` — машинная сводка с `verdict: pass|fail`. Для CI / dashboards.
- `audit/_known_unknowns.md` — таблица «вопрос / почему не ответили / как закрыть / стоимость». Создаётся в Phase 10a.
- `audit/_adversary_review.md` — самокритичный обзор «10 причин не доверять этому аудиту». Создаётся в Phase 10a.

### Added — поведенческие правила в orchestrator

- §3.4 «Запрет «допустимо»» — словесный обход gates запрещён, ловится grep'ом в Phase 10a.
- §3.10 «Anti-recursion в инструментах» — после 3 пустых ответов от cypher/find_symbol → переход на fallback. Счётчик в `.serena/memories/audit_tool_failures`.

### Changed — exit gates стали скриптовыми

- §4 теперь описывает **что проверяет `validate_phase.sh`**, не «надо проверить».
- §10 «Финальные обязательства» теперь требует `finalize.sh exit 0` и явно перечисляет все артефакты.

### Migration v2 → v3

Если у вас уже есть `audit/` от v2:

1. **Findings без `confidence_rationale` / `exploit_proof`** — `validate_phase.sh` пометит их. Можно либо допилить (рекомендуется), либо понизить confidence/severity.
2. **Phase 10a отсутствует** — создать через `phases/phase_10a_self_audit.md`.
3. **Phase 11 отсутствует при critical** — обязательно создать.
4. **`_meta.json`/`_known_unknowns.md`/`_adversary_review.md` отсутствуют** — создать.
5. Запустить `bash audit_pipeline/scripts/finalize.sh` — он покажет полный список того, что не хватает.

### Stats — что было бы в текущем real-world прогоне (selfystudio)

При прогоне на `/home/ubuntu/apps/selfystudio/audit` (49 findings, 80% high):

- `validate_confidence.py` — fail (high% > 60%, low% = 0%)
- `validate_phase.sh 07/08/09/10` — fail (отчёты < 150 строк)
- `validate_phase.sh 06` — fail (critical findings без `exploit_proof`)
- `check_evidence_citations.py` — 2 errors (lines out of range), 21 warnings (stale snippets, директории как файлы)
- `finalize.sh` — fail (нет 10a, нет 11 при 4 critical, нет _meta.json)

В v2 этот аудит проходил собственный самоконтроль («§4.2 допустимо»). В v3 — не пройдёт.

---

## v2 (2026-03-XX)

См. README.md «Главное отличие v2 от v1».

- Hard exit gates по квотам findings.
- Калибровка confidence (запрет «все high»).
- Обязательные evidence-файлы с конкретными именами.
- Минимум 150 строк в отчёте.
- Fallback-протоколы для деградации Serena/GitNexus.
- Обязательный OWASP Top 10 чек-лист.
- Route-by-route auth таблица.
- Опциональная phase 11 deep-dive.

---

## v1 (2026-01-XX)

First-pass risk scan. 10 фаз, базовый ROADMAP. Без жёстких квот и валидации.
