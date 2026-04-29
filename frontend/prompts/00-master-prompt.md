# Master Prompt — запуск всего аудита

Скопируй и вставь это в Claude Code как первое сообщение когда хочешь начать аудит.

---

```
Привет. Будем делать комплексный аудит этого фронтенд-проекта по пайплайну, который лежит в audit-pipeline/.

Прочитай audit-pipeline/00-MASTER-PLAN.md — там вся логика.

Потом по очереди выполняй фазы:
1. Phase 0 (audit-pipeline/01-inventory.md) → reports/01-inventory-report.md
2. Phase 1 (audit-pipeline/02-architecture.md) → reports/02-architecture-report.md
3. Phase 2 (audit-pipeline/03-performance.md) → reports/03-performance-report.md
4. Phase 3 (audit-pipeline/04-accessibility-seo.md) → reports/04-accessibility-seo-report.md
5. Phase 4 (audit-pipeline/05-security-deps.md) → reports/05-security-deps-report.md
6. Phase 5 (audit-pipeline/06-dx-tooling.md) → reports/06-dx-tooling-report.md
7. Phase 6 (audit-pipeline/07-roadmap-synthesis.md) → roadmap.md

Правила:
- После каждой фазы делай паузу, показывай отчёт, спрашивай "продолжаем?". Я проверю и дам go.
- Все находки агрегируй в reports/findings.json по схеме из 02-architecture.md.
- Используй MCP-инструменты:
  - Serena для семантической работы с кодом (find_symbol, find_references, get_symbols_overview)
  - GitNexus для истории и hot spots
  - Bash для измерений (lighthouse, npm audit, madge, jscpd, knip)
- Перед установкой любых dev-зависимостей спрашивай меня.
- Каждая находка должна иметь: severity, evidence (ссылка на файл/строку/команду), impact, fix, confidence, effort.
- Не предлагай переписывать с нуля. Только точечные fix'ы с обоснованием.
- Не делай преждевременных оптимизаций — только то что подтверждается измерениями.

Стартуй с Phase 0. До начала кратко подытожь план словами и дождись моего "поехали".
```

---

## Альтернативно — phase-by-phase

Если хочешь больше контроля, запускай каждую фазу отдельным сообщением. Промпты лежат в `prompts/phase-N-*.md`.
