# PHASE 11 — DEEP DIVE

**Цель:** Forensic-grade разбор каждого critical finding. Обязателен при ≥ 1 critical.

**Источники:** методология forensic incident analysis (NIST SP 800-86), причинно-следственный анализ (5 Whys, Toyota).

---

## 1. Когда применяется

Если в `audit/findings.jsonl` есть хотя бы один `severity: critical` (включая phase 05b money). Если 0 critical — фаза пропускается.

`finalize.sh` блокирует завершение если есть critical, но нет `audit/11_*.md`.

---

## 2. Что делаешь для каждого critical

### 2.1. Полная трассировка

Для каждого critical finding:

- [ ] **Точка входа:** какой endpoint / cron / event / migration вызывает проблемный код?
  - GitNexus `route_map` для endpoint.
  - GitNexus `impact` direction=upstream — кто звонит.
- [ ] **Полное тело транзакции:** прочитай через `find_symbol include_body=true`. Запиши в `evidence/11_*/<finding_id>/body.code`.
- [ ] **Все места, где затрагивается тот же объект:** для финансовых — все места записи в `balance`/`amount`.

### 2.2. Воспроизведение exploit

- [ ] Пошагово опиши сценарий атаки/race/data-loss в `evidence/11_*/<finding_id>/exploit.md`.
- [ ] Если возможно — псевдо-код двух параллельных запросов / последовательности шагов.
- [ ] Какие данные на входе / какое состояние БД до / после?

### 2.3. Blast radius

- [ ] Сколько endpoint затронуто?
- [ ] Сколько строк в БД могут быть скомпрометированы (оценка)?
- [ ] Можно ли откатить, если уже произошло? (audit log есть → да; нет → нет).

### 2.4. Альтернативные fix-стратегии

Каждый critical должен иметь **минимум 2 варианта решения** с trade-offs:

| Вариант | Pros | Cons | Effort | Когда выбирать |
|---------|------|------|--------|----------------|
| Quick fix (mitigation) | быстро в прод | не решает root cause | S | срочно остановить кровотечение |
| Proper fix | правильно | дольше | M | планомерное решение |
| Architectural | глубоко | переписывание | L-XL | если повторяется в нескольких местах |

### 2.5. Тестирование после fix

- [ ] Какой тест надо написать?
- [ ] Каким сценарием воспроизвести?
- [ ] Как замерить что fix работает в prod (метрика, alert)?

### 2.6. Compliance последствия

Если critical связан с PII / money:
- GDPR Article 33: notification of breach в 72h. Был ли инцидент уже? Не проверено? Перенеси в `_known_unknowns.md` как «требует юридического review».
- Финансовые: нужна ли отчётность регулятору?

## 3. Структура отчёта

```markdown
# Phase 11 — Deep Dive

Critical findings: N

## DB-NNNN: <title>

### 1. Trace
- Entry points: …
- Code path: …
- Affected DB objects: …

### 2. Exploit reproduction
- Step 1: …
- Step 2: …
- Result: …

### 3. Blast radius
- Endpoints: …
- Affected data: …
- Recoverability: …

### 4. Fix variants
- Variant A (quick): … — effort S
- Variant B (proper): … — effort M
- Variant C (architectural): … — effort L

### 5. Test strategy
- …

### 6. Recommended next step
- Pick variant X because Y.

---

[next critical finding]
```

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 11
```

Проверяет:
- `audit/11_deep_dive.md` существует.
- Для каждого critical finding в `findings.jsonl` есть соответствующая секция в 11_deep_dive.md.
- Каждая секция содержит все 6 подсекций.
- `evidence/11_deep_dive/<finding_id>/` содержит файлы exploit и body.

## 5. После phase 11

- Возможно, нужен возврат в phase 10 чтобы обновить ROADMAP с уточнёнными fix-вариантами.
- Затем — `finalize.sh`.

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** findings.jsonl где severity=critical

**Запуск:**
```bash
bash database-audit/run.sh phase 11
```

После детекторов агент дополняет `audit/11_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
