# Phase 12 — Production Roadmap

> **Цель:** превратить FINAL-REPORT в **исполнимый план подготовки к продакшену**: атомарные quick-wins на неделю + стратегический roadmap на 3 месяца + черновики ADR + refactoring targets с fitness functions.
>
> Это финальная фаза — её артефакты пользователь будет открывать каждый день.
>
> **Книги:** Susan Fowler PRMS (8 pillars) · Newman *From Monolith* §1-3 · Hohpe *Software Architect Elevator*.

## Inputs

- `reports/FINAL-REPORT.md` — все findings и оценки.
- `reports/_meta.json` — структурированные данные.
- Все findings/promts/cytometric goals из phases 04-10.

## Outputs

- `nodejs-audit/reports/QUICK-WINS.md` — атомарные коммиты на 1 неделю (P0 + P1).
- `nodejs-audit/reports/ROADMAP.md` — фазы на 1-3 месяца с DAG зависимостей.
- `nodejs-audit/reports/ADR-DRAFTS/ADR-XXX-<slug>.md` — по черновику на каждое архитектурное решение из phase-05.
- `nodejs-audit/reports/REFACTORING/<slug>.md` — по таргету на каждый top hot-spot/god-file из phases 04 и 06.

## Шаги

### 1. QUICK-WINS.md — атомарные коммиты

Используй шаблон `templates/quick-wins.md`.

Структура:

```markdown
# Quick Wins (1 неделя, atomic commits)

> **Source:** FINAL-REPORT.md.
> **Goal:** закрыть все Critical + High + Medium hygiene за 1 спринт.

## P0 — Critical/High (1-2 дня)

### Step 1.1 — <ID> <название>
**Why:** ...
**Files:** ...
**Cytometric criteria (до/после):** ...
**Promt:**
\`\`\`
<готовый текст для новой сессии Claude Code>
\`\`\`
**Verify:** \`<команда>\` → expected output.
**Commit:** \`<conventional commit message>\`

### Step 1.2, 1.3 ...

## P1 — Medium hygiene (3-4 дня)

### Step 2.1 ...
```

**Принципы:**
- 1 шаг = 1 коммит = 1 PR (≤2 часа работы).
- Каждый шаг имеет **fitness verify** — команда + ожидаемый результат.
- Промт самодостаточный — копипаст в новую сессию даёт нужный диф.

### 2. ROADMAP.md — стратегический план на 3 месяца

Используй шаблон `templates/quick-wins.md` (там есть секция стратегии) или отдельный шаблон если нужен.

Структура:

```markdown
# Roadmap to Production-Grade (3 months)

> **Source:** FINAL-REPORT.md + ADR-DRAFTS/.
> **Goal:** перевести проект из current (X/Y) в production-ready (target).

## Зависимости (DAG)

\`\`\`mermaid
graph TD
  Phase0[Phase 0 — Quick wins<br/>1 неделя] --> Phase1A
  Phase1A[Phase 1A — Foundations<br/>3-4 недели] --> Phase2
  Phase1A --> Phase1B[Phase 1B — Observability<br/>2-3 недели]
  Phase2[Phase 2 — Domain layer<br/>4-6 недель] --> Phase3
  Phase3[Phase 3 — Events bus<br/>3-4 недели] --> Phase4
  Phase1B --> Phase4
  Phase4[Phase 4 — Production hardening<br/>2-3 недели]
\`\`\`

## Phase 0 — Quick wins (1 неделя)

См. QUICK-WINS.md.

## Phase 1A — Foundations (3-4 недели)

### ADR в фокусе: ADR-XXX, ADR-YYY
### Plan:
1. ...
2. ...
### Definition of Done:
- [ ] Все fitness tests зелёные.
- [ ] ADR в wiki/decisions.md.
- [ ] Production deploy без regression.

### Phase 1B, Phase 2, ...

## Глобальные Definition of Done на каждый шаг

1. ADR в wiki/decisions.md.
2. Plan-файл в TODO/architecture-2026/plans/ помечен `status: completed`.
3. Все fitness tests зелёные (CI gate).
4. wiki/components/<area>.md обновлён.
5. npm test зелёный, coverage не упало.
6. Production deploy без regression.

## Production-readiness checklist (Susan Fowler 8 pillars)

| Pillar | Сейчас | Цель | Где живёт ADR |
|---|:---:|:---:|---|
| Stability | | | |
| Reliability | | | |
| Scalability | | | |
| Fault-tolerance | | | |
| Performance | | | |
| Monitoring | | | |
| Documentation | | | |
| Understandability | | | |
```

### 3. ADR-DRAFTS — черновики архитектурных решений

Для каждого риска из phase-05 (top-3 минимум) — создай `reports/ADR-DRAFTS/ADR-XXX-<slug>.md` по шаблону `templates/adr-draft.md`.

Структура каждого:

```markdown
# ADR-XXX — <название>

- **Status:** proposed (<date>)
- **Owners:** TBD
- **Related:** <other ADRs>

## Context

[Что наблюдаем — со ссылками на findings из phase-05.]

## Decision

[Что предлагается. Конкретная архитектурная инвариата.]

## Consequences

### Positive
### Negative
### Trade-offs

## Implementation plan

1. ...
2. ...

## Fitness function (CI gate)

\`\`\`ts
test('<инвариант>', () => {
  expect(<метрика>).toEqual(<цель>);
});
\`\`\`

## References

- <book §chapter>
```

### 4. REFACTORING — file-level таргеты с fitness functions

Для каждого hot-spot из phase-04 (top-3) и каждого god-file из phase-06 (top-3) — создай `reports/REFACTORING/<slug>.md` по шаблону `templates/refactoring-target.md`.

Структура:

```markdown
# Refactoring target: <path>

## Current state

- LOC: N
- Imports (fan-in): M
- Churn (90d): K commits
- Risk: HIGH/MEDIUM/LOW

## Smell

[Какой анти-паттерн.]

## Decomposition target

[Что должно стать после.]

## Cytometric criteria (fitness function)

\`\`\`ts
test('<file> has fewer than <N> imports after migration', () => {
  expect(grepCount('<path>')).toBeLessThan(<N>);
});

test('<file> LOC ≤ <M>', () => {
  expect(loc('<path>')).toBeLessThanOrEqual(<M>);
});
\`\`\`

## Migration plan

1. Step 1 (atomic commit) — extract <X> into <Y>.
2. Step 2 — wire <Y> into existing handlers.
3. Step 3 — delete dead code from <X>.

## References

- Tornhill *Crime Scene* §<chapter>
- Ousterhout *Philosophy* §<chapter>
```

### 5. Кросс-ссылки

В FINAL-REPORT.md (создан в phase-11) обнови раздел «Куда идти дальше» — должны быть ссылки на все 4 артефакта этой фазы (QUICK-WINS, ROADMAP, ADR-DRAFTS/, REFACTORING/).

В `_meta.json` (создан в phase-11) обнови `report_paths` — все 4 пути уже есть в шаблоне фазы 11.

## Финальное сообщение в чат

Выведи **только** это:

```
✅ Аудит завершён.

Проект: <name>
Verdict: <pass|warn|fail>
Общая оценка: X / Y
Critical: A · High: B · Medium: C · Low: D

Топ-3 проблемы:
1. <одно предложение>
2. <одно предложение>
3. <одно предложение>

Артефакты:
  Полный отчёт:        nodejs-audit/reports/FINAL-REPORT.md
  Машинная сводка:     nodejs-audit/reports/_meta.json
  Quick wins (P0+P1):  nodejs-audit/reports/QUICK-WINS.md
  Roadmap (3 месяца):  nodejs-audit/reports/ROADMAP.md
  ADR-DRAFTS:          nodejs-audit/reports/ADR-DRAFTS/
  Refactoring targets: nodejs-audit/reports/REFACTORING/
  По фазам:            nodejs-audit/reports/0*.md
  Ошибки:              nodejs-audit/reports/errors.log

Дальше:
1. Открой QUICK-WINS.md и выполни 3 атомарных коммита из P0 за 1-2 дня.
2. Параллельно открой ROADMAP.md и распределяй стратегические фазы на 3 месяца.
3. Каждое архитектурное решение — атомарный PR с ADR из ADR-DRAFTS/.
```

После этого — **работа закончена**. Не задавай вопросов, не предлагай follow-up.

## Критерии завершения

- `reports/QUICK-WINS.md` существует.
- `reports/ROADMAP.md` существует.
- `reports/ADR-DRAFTS/` содержит ≥1 файл (если в phase-05 были архитектурные риски).
- `reports/REFACTORING/` содержит ≥1 файл (если в phase-04/06 были hot-spots/god-files).
- В чат выведено финальное сообщение.

## Сигналы в чат

- Старт: `[PHASE 12] STARTED — Production Roadmap`
- Конец: финальное сообщение из «Финальное сообщение в чат» (вместо обычного `[DONE]`).

**Это последняя фаза.**
