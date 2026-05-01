# Phase 11 — Synthesis (FINAL-REPORT.md + _meta.json + Trade-off matrix)

> **Цель:** собрать все фазы в один документ для владельца + машинную сводку для CI + Trade-off matrix Richards & Ford.
>
> **Книги:** Richards & Ford *Fundamentals of Software Architecture* §5-6 · Ford *Building Evolutionary Architectures* §2.

## Inputs (читай в этом порядке)

- `reports/00-bootstrap.md`
- `reports/01-mcp-probe.md`
- `reports/02-recon.md`
- `reports/03-deterministic.md`
- `reports/04-hotspots.md`
- `reports/05-architecture.md`
- `reports/06-readability.md`
- `reports/07-security.md`
- `reports/08-performance.md`
- `reports/09-observability.md`
- `reports/10-ai-readability.md`
- `reports/errors.log`

**ВАЖНО:** в этой фазе **не перечитывай код**. Только синтез из готовых отчётов.

## Outputs

- `nodejs-audit/reports/FINAL-REPORT.md`
- `nodejs-audit/reports/_meta.json`

## Шаги

### 1. Собери все findings в одну таблицу

Из phase-05/07/08/09 — все идентифицированные проблемы по severity.

### 2. Собери все промты в один сквозной список

Каждый промт получает номер #1, #2, …, #N.

### 3. Trade-off matrix Richards & Ford (10 ilities)

| Characteristic | Текущий | Цель | Как двигаться |
|---|---:|---:|---|
| Deployability | X/10 | Y/10 | <ссылка на ADR/REFACTORING> |
| Reliability | | | |
| Recoverability | | | |
| Observability | | | |
| Security | | | |
| Modifiability | | | |
| Testability | | | |
| Performance | | | |
| Scalability | | | |
| Cost-efficiency | | | |

Оценки выводи из соответствующих фаз. Цели — реалистичные на 3 месяца.

### 4. Verdict

- `fail` — есть хотя бы один `critical`, или какая-то фаза не завершилась.
- `warn` — нет critical, но есть `high`, или общая оценка < 65%.
- `pass` — нет critical, нет high, общая оценка ≥ 65%.

## Шаблон `FINAL-REPORT.md`

```markdown
# Финальный отчёт аудита

**Проект:** <name>
**Дата:** <ISO>
**Версия пайплайна:** chained-v2

---

## Executive Summary

[5-7 предложений простым языком, для не-программиста.]

---

## Общая оценка: X / Y

| Слой | Оценка | Статус |
|------|--------|--------|
| Форматирование | X/10 | ✅/⚠️/❌ |
| Линтинг | X/10 | |
| Типизация | X/10 | |
| Тесты | X/10 | |
| Безопасность | X/30 | |
| Зависимости | X/10 | |
| Производительность | X/30 | |
| Архитектура | X/60 | |
| Читаемость | X/50 | |
| Observability | X/40 | |
| AI-readability | X/60 | |

---

## Trade-off matrix (Richards & Ford, 10 ilities)

| Characteristic | Current | Target | Action |
|---|---:|---:|---|
| Deployability | 8/10 | 10/10 | ROADMAP §<X> |
| Reliability | | | |
| Recoverability | | | |
| Observability | | | |
| Security | | | |
| Modifiability | | | |
| Testability | | | |
| Performance | | | |
| Scalability | | | |
| Cost-efficiency | | | |

---

## ТОП-10 критических проблем

### #1: <название>
- **Где:** <file:line>
- **Серьёзность:** Critical/High
- **Категория:** Architecture / Security / Performance / ...
- **Cited:** <book §chapter>
- **Чем грозит:** ...
- **Артефакты:** QUICK-WINS промт #N + (если архитектурное) ADR-DRAFTS/ADR-XXX.md + REFACTORING/<slug>.md

### #2 ... #10

---

## Метрики до и после

| Метрика | Сейчас | Цель | Команда verify |
|---------|--------|------|----------------|

---

## Что не было проверено

[Список того, что не получилось — из errors.log + manual followups.]

---

## Куда идти дальше

- **Сегодня:** `reports/QUICK-WINS.md` — 3 атомарных коммита из P0.
- **На этой неделе:** оставшиеся P1 из QUICK-WINS.md.
- **На этом месяце-трёх:** `reports/ROADMAP.md` — стратегические фазы.
- **Каждое архитектурное решение:** `reports/ADR-DRAFTS/ADR-XXX.md` → wiki/decisions.md.
- **Каждый рефакторный таргет:** `reports/REFACTORING/<slug>.md` — fitness function в CI.

---

*Отчёт создан автономно через `nodejs-audit/MASTER_PROMPT.md` (chained-v2).
Для повторного аудита через 3 месяца — запусти ту же команду.*
```

## Шаблон `_meta.json`

```json
{
  "version": "chained-v2",
  "generated_at": "<ISO-8601 timestamp>",
  "project": {
    "name": "<из package.json>",
    "package_manager": "<npm|yarn|pnpm|bun>",
    "typescript": true,
    "src_files": 0,
    "dependencies": 0,
    "dev_dependencies": 0
  },
  "scores": {
    "formatting": 0,
    "linting": 0,
    "typing": 0,
    "tests": 0,
    "security": 0,
    "deps": 0,
    "performance": 0,
    "architecture": 0,
    "readability": 0,
    "observability": 0,
    "ai_readability": 0,
    "total": 0,
    "max_total": 320
  },
  "ilities": {
    "deployability": { "current": 0, "target": 10 },
    "reliability": { "current": 0, "target": 10 },
    "recoverability": { "current": 0, "target": 10 },
    "observability": { "current": 0, "target": 10 },
    "security": { "current": 0, "target": 10 },
    "modifiability": { "current": 0, "target": 10 },
    "testability": { "current": 0, "target": 10 },
    "performance": { "current": 0, "target": 10 },
    "scalability": { "current": 0, "target": 10 },
    "cost_efficiency": { "current": 0, "target": 10 }
  },
  "verdict": "<pass|warn|fail>",
  "counts": {
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "blockers": [],
  "high_findings": [],
  "phases_completed": [0,1,2,3,4,5,6,7,8,9,10,11],
  "phases_failed": [],
  "errors_log_size": 0,
  "report_paths": {
    "final": "nodejs-audit/reports/FINAL-REPORT.md",
    "quick_wins": "nodejs-audit/reports/QUICK-WINS.md",
    "roadmap": "nodejs-audit/reports/ROADMAP.md",
    "adr_drafts": "nodejs-audit/reports/ADR-DRAFTS/",
    "refactoring": "nodejs-audit/reports/REFACTORING/",
    "phases": "nodejs-audit/reports/",
    "errors": "nodejs-audit/reports/errors.log"
  }
}
```

## Критерии завершения

- `reports/FINAL-REPORT.md` существует.
- `reports/_meta.json` существует и проходит `jq . _meta.json > /dev/null`.

## Сигналы в чат

- Старт: `[PHASE 11] STARTED — Synthesis`
- Конец: `[PHASE 11] DONE — reports/FINAL-REPORT.md + _meta.json`

→ Переход к **phase-12-prod-roadmap.md**.
