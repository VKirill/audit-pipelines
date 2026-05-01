# Deprecated phase files (autonomous-v1)

Эти файлы — оригинальный пайплайн до редизайна на `chained-v2` (2026-05-02).

В **chained-v2** каждый файл явно перечисляет свои inputs/outputs, использует MCP-first probe, добавляет hot-spot анализ (Tornhill), DDD-словарь и Trade-off matrix Richards & Ford. Артефактов теперь 4 типа (FINAL-REPORT, QUICK-WINS, ROADMAP, ADR-DRAFTS, REFACTORING) вместо одного.

Если нужны старые версии для сравнения — они здесь. Активные файлы — в `phases/phase-NN-*.md`.

| Старый файл | Новый файл |
|---|---|
| `00-bootstrap.md` | `phases/phase-00-bootstrap.md` |
| `01-recon.md` | `phases/phase-02-recon.md` (теперь после MCP probe) |
| `02-deterministic.md` | `phases/phase-03-deterministic.md` |
| `03-architecture.md` | `phases/phase-05-architecture-ddd.md` (+ DDD-словарь) |
| `04-readability.md` | `phases/phase-06-readability.md` |
| `05-security.md` | `phases/phase-07-security.md` (+ ASVS) |
| `06-performance.md` | `phases/phase-08-performance.md` |
| `07-observability.md` | `phases/phase-09-observability.md` |
| `08-ai-readability.md` | `phases/phase-10-ai-readability.md` |
| `09-final-report.md` | `phases/phase-11-synthesis.md` (+ Trade-off matrix) |
| `10-fix-loop.md` | `phases/phase-12-prod-roadmap.md` (теперь генерирует QUICK-WINS + ROADMAP + ADR-DRAFTS + REFACTORING) |
| (новый) | `phases/phase-01-mcp-probe.md` — gitnexus + serena |
| (новый) | `phases/phase-04-hotspots.md` — churn × fan-in |
