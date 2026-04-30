# PHASE 10a — SELF-AUDIT (мини-фаза)

**Цель:** Рефлексия — что аудит мог пропустить, переоценить, недооценить. Adversary review.

**Источники:**
- Daniel Kahneman, *Thinking, Fast and Slow* — Ch. 11 Anchoring, Ch. 24 Overconfidence, Ch. 25 Bernoulli's errors.

---

## 1. Цель

Эта фаза — последняя страховка. Аудитор играет адвоката защиты: «если бы я был автором кода, на что бы я указал в этом аудите?».

Это не самобичевание, это калибровка. Слабые findings → понижаются. Пробелы → переносятся в `_known_unknowns.md`.

---

## 2. Что делаешь

### 2.1. Adversary review

Создай `audit/_adversary_review.md`. Для каждого finding со severity `critical`/`high`:

- [ ] Можешь ли воспроизвести exploit без рантайма?
- [ ] Если evidence требует EXPLAIN/нагрузки — confidence должен быть ≤ medium.
- [ ] Какие альтернативные объяснения ты не рассмотрел?
- [ ] Какой контр-аргумент привёл бы автор кода?

Если контр-аргумент звучит сильнее твоей находки — понизь severity или переведи в `low confidence`.

### 2.2. Поиск систематических blind spots

Проверь на типичные смещения аудитора:

| Bias | Что значит | Проверка |
|------|------------|----------|
| Anchoring (Kahneman §11) | Первая фаза задала тон, остальное искажено | Перечитай findings в обратном порядке. Меняется ли восприятие? |
| Availability heuristic | Проблемы из недавних incident reports «бьются по глазам» | Какие findings — по «модной» теме? Подтверждены ли они кодом проекта? |
| Confirmation bias | Найдя N+1, видишь его везде | Re-проверь 3 случайных N+1-finding на ложные срабатывания |
| Overconfidence (§24) | `high confidence` стало дефолтом | Сколько `high` в finding? Если > 60% — пере-калибруй |
| Hindsight bias | Очевидно после факта, неочевидно до | Если finding «очевидный» — почему его не нашли разработчики? Может, он не очевидный |

### 2.3. Заполнение `_known_unknowns.md`

- [ ] Что не проверено из-за ограничений mode (static vs live)?
- [ ] Какие phase passed `validate`, но ты подозреваешь что они слабые?
- [ ] Cross-DB consistency не проверена?
- [ ] Multi-tenant с RLS не верифицирована вживую?

Каждый пункт — будущая задача (без severity, просто как пометка для retest).

### 2.4. Распределение severity / confidence

Глобальный sanity-check:

```
critical: should be ≤ 5% of total findings (если больше — может, понижение нужно или выдуманное)
high: ≤ 25%
medium: 40-60% — норма
low: 20-40%
```

Если профиль резко отличается — почему? Маленький проект с 10 findings: распределение менее показательно. Большой с 100+ findings: критическое отклонение требует объяснения.

`validate_confidence.py` ловит явные отклонения (например, > 40% high без `confidence_rationale`).

### 2.5. Полнота coverage

- [ ] Все ли модели из `evidence/01_inventory/models_list.md` упомянуты в findings или явно проверены?
- [ ] Все ли фазы (00-09) сгенерировали свои required evidence файлы?
- [ ] Phase 05b пропущен корректно (если не money-проект)?

### 2.6. Возврат к фазам

Если в self-audit обнаружен пробел в фазе N:
1. Зафиксируй в `_adversary_review.md` как «возврат к фазе N».
2. Допроверь.
3. Перезапусти `validate_phase.sh N`.
4. Обнови `audit/N_*.md` и `findings.jsonl`.
5. Продолжи self-audit.

Это легитимная итерация, не должна быть «галочкой».

## 3. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 10a
```

Проверяет:
- `audit/_adversary_review.md` существует и непустой.
- `audit/_known_unknowns.md` существует.
- Если `findings.jsonl` содержит ≥ 1 critical — после self-audit это всё ещё true (либо разжалован).

## 4. Артефакты

- `audit/10a_self_audit.md` — сжатый отчёт что менялось.
- `audit/_adversary_review.md` — основной артефакт фазы.
- `audit/_known_unknowns.md` — список будущих проверок.

## 5. После self-audit

- Если ≥ 1 critical → phase_11_deep_dive **обязателен**.
- Если только high и ниже → можно сразу `finalize.sh`.
