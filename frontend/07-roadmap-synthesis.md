# Phase 6 — Synthesis & Roadmap

**Цель:** превратить шесть отчётов и `findings.json` в один приоритизированный план действий, готовый к работе. Это то ради чего весь аудит затевался.

**Длительность:** 1–2 часа.

**Опора:**
- Adam Tornhill — приоритизация по hot spots × severity.
- *Working Effectively with Legacy Code* (Michael Feathers) — характеризационные тесты перед изменениями.
- *Refactoring* (Fowler) — поэтапные безопасные изменения.

---

## Принципы синтеза

1. **Чинить риск, не вкус.** Сначала critical/high с большим impact и подтверждённым evidence.
2. **Кучковать по теме.** Если в одном модуле 5 находок — это одна задача "привести в порядок X", не пять.
3. **Учитывать зависимости.** Бесполезно рефакторить код у которого нет тестов — сначала тесты. Бесполезно ставить Sentry если нет deploy pipeline.
4. **Quick wins вперёд.** Они дают энергию команде и быстрый импакт.
5. **Не пытаться съесть всё за раз.** Roadmap на 3 горизонта: Now (1–2 недели), Next (1–2 месяца), Later (квартал+).

---

## Алгоритм приоритизации

Для каждой находки считаем `priority_score`:

```
priority_score = (impact × confidence) / effort

impact:      critical=10, high=5, medium=2, low=1, nit=0.5
confidence:  0.0–1.0 (из findings.json)
effort:      S=1, M=3, L=8, XL=20
```

Дополнительный множитель `×1.5` если файл/модуль находки совпадает с hot spot из Phase 0 (Tornhill — чинить там где часто меняется).

Сортируем по убыванию.

---

## Группировка в эпики

Объединяем находки по теме:

- **Epic: Performance baseline** — все находки Phase 2 в один эпик.
- **Epic: A11y compliance** — все a11y находки.
- **Epic: Architecture cleanup of [hot spot module]** — несколько архитектурных находок в одной зоне.
- **Epic: Security hardening** — заголовки + секреты + критичные deps.
- **Epic: Test safety net** — покрыть hot spots тестами как основа для рефакторинга.
- **Epic: Observability** — Sentry + RUM + alerting.

В каждом эпике — задачи с estimate, owner, definition of done.

---

## Структура roadmap.md

```markdown
# Frontend Audit — Roadmap

## TL;DR
Аудит выявил N находок: critical=X, high=Y, medium=Z.
Топ-3 риска:
1. [самое страшное]
2. ...
3. ...

Топ-3 quick wins (≤1 день, большой импакт):
1. ...
2. ...
3. ...

## Оценка состояния по осям

| Ось | Score | Комментарий |
|---|---|---|
| Architecture | 6/10 | hot spot в cart/, циклы зависимостей |
| Performance | 5/10 | LCP 4s на главной, тяжёлый бандл |
| A11y | 7/10 | базово ок, кастомные виджеты не доступны |
| SEO | 8/10 | нормально, но контент главной за JS |
| Security | 6/10 | нет CSP, deps критики 2 |
| DX/Tooling | 5/10 | нет тестов в CI, нет Sentry |

Общий health: 6.2/10.

---

## Now (1–2 недели) — Stop the bleeding

Цель: убрать прямые риски (security, falling RUM, broken UX), не трогая архитектуру.

### NOW-1: Установить Sentry и RUM
- Findings: DX-005, DX-006
- Effort: S
- Why first: без observability мы летим вслепую.
- Tasks: ...
- DoD: Sentry подключён, source maps загружаются, RUM шлёт CWV.

### NOW-2: Зафиксить critical security findings
- Findings: SEC-001, SEC-002, SEC-003
- Effort: M
- Tasks: bump react-syntax-highlighter, добавить DOMPurify в Comment.tsx, переместить test API key в .env.
- DoD: npm audit --production = 0 high+, dangerouslySetInnerHTML на user input использует DOMPurify.

### NOW-3: Quick wins по перфу
- Findings: PERF-002 (lcp image priority), PERF-005 (заменить moment на dayjs), PERF-008 (next/script async для метрики).
- Effort: M (всё вместе)
- DoD: LCP на главной <3s, бандл -75KB.

### NOW-4: Critical a11y
- Findings: A11Y-001, A11Y-002
- Effort: M
- DoD: alt у всех изображений, кастомный Dropdown заменён на Radix Combobox.

[...]

---

## Next (1–2 месяца) — Build foundation

Цель: положить фундамент для здоровых изменений.

### NEXT-1: Test safety net для hot spots
- Findings: DX-002, DX-003 + hot spots из Phase 0
- Effort: L
- Tasks:
  - Покрыть ProductCard.tsx, cart/api.ts unit тестами (характеризационные, фиксируем текущее поведение).
  - E2E на checkout flow.
- DoD: 70% coverage на топ-5 hot spots, тесты в CI.

### NEXT-2: Архитектурный рефакторинг cart/
- Findings: ARCH-001, ARCH-003, ARCH-007
- Effort: L
- Prerequisite: NEXT-1 (нужны тесты прежде чем трогать).
- Tasks:
  - Разбить cart/index.ts (612 LOC) на features/cart/{ui,api,model}.
  - Убрать циклическую зависимость через выделение types.ts.
  - useEffect-fetch заменить на TanStack Query.
- DoD: cart/ соответствует структуре features, 0 циклов, < 300 LOC на файл.

### NEXT-3: Полный CWV
- Findings: остальные PERF-*
- Effort: L
- DoD: Lighthouse mobile ≥85 на топ-5 маршрутах, CLS <0.1, INP <200ms.

[...]

---

## Later (квартал+) — Strategic

Цель: системные улучшения.

### LATER-1: Дизайн-система и Storybook
- Effort: XL
- Why: дублирование компонентов, нет единого языка стилей.
- DoD: Storybook покрывает 80% UI-компонентов, токены вынесены, контрибьюшн-гайд.

### LATER-2: Миграция на Server Components где разумно
- Effort: XL
- Prerequisite: понимание data-flow.
- Why: 'use client' избыточно, бандл можно урезать.

### LATER-3: ADR и архитектурная документация
- Effort: M (но непрерывно)

[...]

---

## Метрики успеха

После Now+Next должны достичь:
- Lighthouse mobile ≥85 на главной
- LCP p75 <2.5s, INP p75 <200ms (RUM)
- npm audit --production = 0 critical/high
- 0 циклов зависимостей
- Test coverage hot spots ≥70%
- DORA: lead time <1 day, change failure rate <15%

После Later:
- Health score ≥8.5/10 по всем осям
- Onboarding нового разработчика ≤15 минут до running локально

---

## Что не будем делать (out of scope)

Перечисли явно. Это так же важно как и список того что делаем.

- Полное переписывание на новый фреймворк
- Замена state management
- ...

---

## Риски и mitigation

- Риск: рефакторинг cart/ пока активная разработка фичи X → mitigation: запланировать на freeze-окно.
- Риск: команда из 1 человека (см. bus factor) → mitigation: ADR + документация по ходу.
- ...
```

---

## Промпт для Claude Code

```
Phase 6 — Synthesis & Roadmap.

Контекст: у тебя есть 6 отчётов в reports/ и findings.json со всеми находками.

План:
1. Прочитай findings.json целиком.
2. Для каждой находки убедись что есть severity, confidence, effort. Если чего-то нет — спроси меня или оцени.
3. Посчитай priority_score по формуле в audit-pipeline/07-roadmap-synthesis.md.
4. Сгруппируй находки в эпики по теме/модулю.
5. Распредели эпики по горизонтам Now / Next / Later.
6. Учти зависимости: то что нельзя делать без подготовки — отодвинь, подготовку поставь раньше.
7. Найди топ-3 риска и топ-3 quick wins.
8. Через Serena/GitNexus уточни ещё раз hot spots — задачи в hot spots поднимаются в приоритете (×1.5).
9. Заполни roadmap.md по шаблону.
10. В конце — сводная страница для бизнеса (3 абзаца, без жаргона): что не так, что чиним сначала, какой ожидаемый эффект.

Замечания:
- Будь честен по effort'ам. Лучше переоценить чем недооценить.
- Указывай Definition of Done для каждой задачи измеримо.
- Если что-то нельзя оценить без дополнительных данных — отметь "needs investigation".
```

---

## После roadmap — итерация

Roadmap не финал. Дальше:

1. Валидируем roadmap с тобой — что приоритизация совпадает с бизнес-целями.
2. Превращаем эпики в issues / задачи в трекере.
3. Идём по Now-задачам, после каждой обновляем findings.json (закрываем находки).
4. Переаудит через 3 месяца — короткий, по тем же фазам, чтобы увидеть прогресс по health score.
