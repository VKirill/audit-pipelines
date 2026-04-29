# Phase 1 — Architecture prompt

```
Phase 1 — Architecture & Code Health (audit-pipeline/02-architecture.md).

Контекст: Phase 0 готова, отчёт в reports/01-inventory-report.md. Используй hot spots оттуда.

Задачи:
1. Спроси меня прежде чем установить dev-зависимости: madge, jscpd, knip.
2. Граф зависимостей через madge. Найди циклы, god modules.
3. Через Serena get_symbols_overview по src/ собери метрики компонентов:
   - LOC, кол-во props, кол-во хуков
   - Не читай файлы целиком. Только overview, потом find_symbol на подозрительных.
4. Через Serena find_references на ключевые компоненты — props drilling, использование, dead exports.
5. tsc --noEmit, jscpd, knip — собери метрики типов, дублирования, мёртвого кода.
6. ESLint с правилами complexity, max-lines, max-depth — топ функций по сложности.
7. Crime scenes: пересечь hot spots (Phase 0) с complexity/LOC. Файлы где часто меняется И сложно — критичны.
8. Для топ-5 crime scenes через GitNexus подними историю изменений: коммит-мессаги, авторы. Это даёт контекст почему файл стал таким.
9. Заполни reports/02-architecture-report.md.
10. Допиши находки в reports/findings.json (создай если нет).

Правила:
- Каждая находка: ID (ARCH-NNN), severity, evidence (файл:строка), impact, fix, references (ссылка на книгу/гайд), effort, confidence.
- Не предлагай переписывать с нуля. Точечные рефакторинги.
- Если Serena показывает что компонент >300 LOC и используется в 1 месте — кандидат на упрощение, не на разбиение.
- В конце — что неясно, что нужно уточнить у меня.
```
