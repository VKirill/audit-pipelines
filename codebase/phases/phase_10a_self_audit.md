# PHASE 10a — SELF-AUDIT (рефлексия пайплайна)

**Цель:** Поймать обход правил самим агентом. Между Phase 10 (синтез ROADMAP) и `finalize.sh` агент обязан **явно проверить свою же работу**: распределение confidence, реальность цитат, состоятельность критичных findings, ситуация «может я договорился сам с собой».

Эта фаза — главная защита пайплайна против сценария «отчёт выглядит хорошо, но half findings — выдуманные / overconfident».

**Когда запускать:** ровно после `phase_10_synthesis_roadmap.md`. Перед `phase_11_deep_dive.md` (если требуется) и `finalize.sh`.

**Источники методики:**
- Karl Popper, *The Logic of Scientific Discovery* — фальсификация: гипотеза ценна, если её можно опровергнуть.
- Bach & Bolton, *Rapid Software Testing* — heuristic of «adversarial review».
- Daniel Kahneman, *Thinking, Fast and Slow*, ch. 24 — «premortem».
- Atul Gawande, *The Checklist Manifesto* — checklist в финале сложной процедуры.

**Exit gate:**
- `bash audit_pipeline/scripts/validate_phase.sh 10a` возвращает 0;
- три обязательных артефакта созданы: `audit/10a_self_audit.md`, `audit/_known_unknowns.md`, `audit/_adversary_review.md`;
- `validate_confidence.py` и `check_evidence_citations.py` запущены и их output отражён в `10a_self_audit.md`;
- 3 случайно выбранных high-finding'а перепроверены вручную (cited file → reread → match? отметка в отчёте).

---

## 1. Входы

- ВСЕ предыдущие фазы и artefacts.
- `audit/findings.jsonl`.
- `audit/ROADMAP.md` (черновик из Phase 10).

---

## 2. Чек-лист действий

### 2.1. Запустить deterministic validators и записать результат

```bash
python3 audit_pipeline/scripts/validate_confidence.py     | tee audit/evidence/_self_audit/conf.txt
python3 audit_pipeline/scripts/check_evidence_citations.py --root . | tee audit/evidence/_self_audit/cites.txt
```

В `10a_self_audit.md` явно процитируй любые VIOLATIONS / WARNINGS / ERRORS. Если нет — пиши «оба валидатора прошли чисто».

### 2.2. Сэмпл 3 случайных high-confidence findings (manual recheck)

Псевдо-случайная выборка (фиксируй seed):

```bash
SEED=$(date +%j)
jq -r 'select(.confidence=="high") | .id' audit/findings.jsonl \
  | shuf --random-source=<(yes "$SEED") | head -3 > audit/evidence/_self_audit/_resample.txt
cat audit/evidence/_self_audit/_resample.txt
```

Для каждого выбранного:

1. Открой `location.file` по `location.lines`.
2. Сравни прочитанное с `evidence`. Совпадает дословно? Совпадает по смыслу? Не совпадает?
3. Если **не совпадает** — finding автоматически downgrade на `medium` или удаляется. И флагается весь `subcategory` для проверки.
4. В отчёте — таблица:

| ID | Reread match? | Action |
|----|---------------|--------|
| F-0034 | exact | keep |
| F-0018 | partial (function moved 200 → 187 LOC) | update lines, keep |
| F-0029 | does not exist anymore | downgrade to low + flag subcategory `missing-timeouts` for full re-check |

### 2.3. Premortem (Kahneman)

Сядь и спроси: «Через 3 месяца этот ROADMAP оказался плохим советом. Почему?». Запиши в отчёт ≥ 3 правдоподобных причин:

- Например: «Severity F-0034 преувеличена — на самом деле routes за CDN с auth-check на сетевом уровне».
- «Phase 0 нельзя выполнить за 7 дней — секрет-ротация требует координации с GCP-биллингом».
- «ROADMAP игнорирует, что 1 разработчик не сможет вести 4 эпика параллельно».

Каждая причина → либо downgrade severity / уточнение, либо явное упоминание в `_known_unknowns.md`.

### 2.4. Adversary review — 10 причин не доверять аудиту

Создай `audit/_adversary_review.md`. Прими роль «senior, который ненавидит этот аудит». Найди ≥ 10 причин его не принять:

```markdown
# Adversary review of audit
Generated: YYYY-MM-DD

## 10 reasons not to trust this audit

1. **Confidence skewed high (X%).** Author знал §4.2 но не понизил — risk: cherry-picked evidence.
2. **F-XXXX severity inflated** — описанная атака требует admin-credentials, которые сами по себе означают полный пробой; по сути это secondary risk.
3. **Phase 09 не запускал EXPLAIN** — все perf findings основаны на чтении кода, без реальных метрик; легко false positive.
4. **Tests Phase 07 не запустил `--coverage`** — оценка «10-15%» на глаз, не подтверждена.
5. **Anti-roadmap слишком аккуратный** — нет ни одного действительно непопулярного запрета.
6. **Phase 02 cypher выдал community 211 символов как «god», но agent не проверил, что это легитимный feature aggregate** — может быть false positive.
7. ... (минимум 10)

## What would change my mind
Для каждой причины — что нужно проверить, чтобы её снять (file, command, метрика).
```

### 2.5. `_known_unknowns.md` — явный список пробелов

```markdown
# Known unknowns

Полный список вопросов, на которые этот аудит **не ответил**, и как их закрыть.

| Вопрос | Почему не ответили | Как закрыть | Стоимость |
|--------|--------------------|-------------|-----------|
| Какие реальные slow-queries в prod? | Нет доступа к pg_stat_statements | Запросить read-only к prod БД, выгрузить top-50 | 1 час |
| Coverage реальное число | vitest --coverage упал из-за missing dep | npx --yes c8 npm test, вытащить json-summary | 30 мин |
| Полный gitleaks history | Не запущен | `gitleaks detect --log-opts="--all"` (см. scripts/run_external_tools.sh history) | 5 мин |
| Соответствие compliance (GDPR, PCI) | Не проверяли — outside scope phase 06 | Отдельный compliance-audit | дни |
```

### 2.6. Cross-check ROADMAP vs findings

Каждый critical и high finding **обязан** быть упомянут хотя бы в одной фазе ROADMAP. Скрипт-проверка:

```bash
python3 - <<'PY'
import json
findings = [json.loads(l) for l in open("audit/findings.jsonl") if l.strip()]
roadmap = open("audit/ROADMAP.md").read()
missed = [f["id"] for f in findings
          if f.get("severity") in ("critical", "high")
          and f["id"] not in roadmap
          and f.get("status") != "merged"]
print("missed in ROADMAP:", missed)
PY
```

Если есть пропущенные — вернись в Phase 10 и допиши.

### 2.7. Stop-words audit

Проверь, что в отчётах нет запрещённых слов из §3.4:

```bash
rg -nE "\\b(допустимо|приемлемо|можно считать|достаточно для §)\\b" audit/*.md
```

Любой матч → перепиши формулировку.

---

## 3. Quota check перед завершением

- [ ] `audit/10a_self_audit.md` ≥ 100 строк.
- [ ] `audit/_adversary_review.md` ≥ 10 пунктов.
- [ ] `audit/_known_unknowns.md` ≥ 3 строки в таблице.
- [ ] Все три случайных high-finding'а перепроверены и помечены keep/update/downgrade.
- [ ] `validate_confidence.py` exit 0 (или зафиксировано в отчёте, что violations осознанные с обоснованием — но финал требует exit 0).
- [ ] `check_evidence_citations.py` без ERRORS.
- [ ] Запусти `bash audit_pipeline/scripts/validate_phase.sh 10a`.

---

## 4. Артефакт — `audit/10a_self_audit.md`

### Обязательные разделы

1. **Цель фазы** — самопроверка пайплайна.
2. **Что проверено** — список §2.1 … §2.7 с пометками.
3. **Ключевые наблюдения**
   - Output validate_confidence.py (вставь дословно).
   - Output check_evidence_citations.py (вставь дословно).
   - Resample-таблица 3 high-findings.
   - Premortem (3+ причины).
   - Cross-check ROADMAP vs findings.
   - Stop-words audit результат.
4. **Корректировки findings** — таблица: `id | было | стало | причина` (downgrade/upgrade/удаление по результатам resample).
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Если бы я был тем самым «senior, который ненавидит этот аудит» — какой 1 finding я бы первым отверг и почему?
   - **Q2.** Какая часть ROADMAP сильнее всего зависит от данных, которых у меня нет?
7. **Следующая фаза:** `phases/phase_11_deep_dive.md` (если есть critical) или `scripts/finalize.sh`.

---

## 5. Memory

```markdown
# Phase 10a memory
Completed: YYYY-MM-DD

Validators:
- validate_confidence: pass / N violations
- check_evidence_citations: pass / N errors / M warnings

Resample (3):
- F-XXXX: keep / update / downgrade
- F-YYYY: ...
- F-ZZZZ: ...

Premortem reasons: <N>
Adversary points: <N>
Known unknowns: <N>
Stop-words found: <N>

Findings adjusted: <list>

Next phase: phase_11_deep_dive.md (if critical) else finalize.sh
```

---

## 6. Отчёт пользователю

> Фаза 10a/13 завершена. Self-audit: validate_confidence <pass/fail>, citations <pass/fail>. Перепроверил 3 случайных high-finding'а — <K> подтверждены, <M> скорректированы. Adversary review: <N> причин не доверять, главные — <1-2 строки>. Known unknowns: <N>. <Если есть critical> Перехожу к Phase 11 deep-dive. <иначе> Перехожу к finalize.sh.

Перейди к `phases/phase_11_deep_dive.md` ИЛИ запусти `bash audit_pipeline/scripts/finalize.sh`.
