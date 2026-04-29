# Phase 6 — Synthesis & Roadmap prompt

```
Phase 6 — Synthesis (audit-pipeline/07-roadmap-synthesis.md).

Контекст: 6 отчётов в reports/, findings.json с агрегированными находками.

Задачи:
1. Прочитай findings.json целиком. Убедись что у каждой находки есть severity, confidence, effort, evidence, fix.
2. Если у находки нет какого-то поля — оцени сам или спроси меня.
3. Посчитай priority_score:
   priority_score = (impact × confidence) / effort
   impact: critical=10, high=5, medium=2, low=1, nit=0.5
   effort: S=1, M=3, L=8, XL=20
   ×1.5 если файл/модуль находки совпадает с hot spot из Phase 0.
4. Сгруппируй находки в эпики по теме или модулю (не по фазе!). Например:
   - Epic: "Cart module health" — все ARCH-* и PERF-* и DX-* связанные с cart/
   - Epic: "Performance baseline"
   - Epic: "A11y compliance"
   - Epic: "Security hardening"
   - Epic: "Test safety net"
   - Epic: "Observability"
5. Распредели эпики по горизонтам:
   - Now (1–2 недели): прямые риски, quick wins, observability
   - Next (1–2 месяца): фундаментальные улучшения которые требуют подготовки
   - Later (квартал+): стратегические системные улучшения
6. Учти зависимости между эпиками. Не ставь рефакторинг до тестов. Не ставь алертинг до Sentry.
7. Найди топ-3 риска (что самое страшное прямо сейчас) и топ-3 quick wins (≤1 день, большой импакт).
8. Через Serena/GitNexus при необходимости уточни ещё раз hot spots.
9. Оцени состояние по 6 осям (architecture, performance, a11y, seo, security, dx) от 1 до 10. Это будет baseline.
10. Заполни roadmap.md по шаблону из 07-roadmap-synthesis.md.
11. В конце roadmap — сводка для бизнеса (3 абзаца, без жаргона):
    - что не так
    - что чиним сначала
    - какой ожидаемый эффект и сроки
12. Перечисли out of scope явно — что НЕ будем делать.

Правила:
- Будь честен по effort. Лучше переоценить.
- Definition of Done измеримо. Не "улучшить производительность", а "LCP p75 <2.5s на главной".
- Quick wins — реально быстрые. Если задача требует тестов и рефакторинга — это не quick win.
- Если что-то нельзя оценить без доп.данных — отметь "needs investigation, спросить у автора".

Финальный output: roadmap.md в корне audit-pipeline/.
```
