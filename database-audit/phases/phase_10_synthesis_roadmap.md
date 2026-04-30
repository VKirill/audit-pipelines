# PHASE 10 — SYNTHESIS & ROADMAP

**Цель:** Свести все находки в приоритизированный roadmap. Это **главный артефакт пайплайна**.

**Источники:**
- Sadalage & Ambler — последовательность refactoring.
- SRE Book Ch. 26 — приоритизация data integrity.

---

## 1. Входы

- Все `audit/NN_*.md` (фазы 01–09).
- `audit/findings.jsonl`.
- `evidence/*` для перепроверки.

## 2. Что делаешь

### 2.1. Дедупликация и корреляция

- [ ] Найди findings, ссылающиеся на одно место в коде/схеме — объедини в один с `related_findings`.
- [ ] Найди cross-phase связи: finding из phase 02 (no FK) → phase 03 (FK без индекса) → phase 04 (JOIN seq scan).
- [ ] В таких связках выбери «корневой» finding и понизь severity производных.

### 2.2. Приоритизация

Формула:
```
priority = (impact × confidence × likelihood) / effort
```

Где:
- `impact` — 4 (critical) / 3 (high) / 2 (medium) / 1 (low)
- `confidence` — 3 (high) / 2 (medium) / 1 (low)
- `likelihood` — 3 (constantly) / 2 (occasional) / 1 (rare)
- `effort` — 1 (S, часы) / 2 (M, день) / 4 (L, неделя) / 8 (XL, месяц)

Топ-15 пунктов по `priority` → секция «🔴 Сейчас (Now)».

### 2.3. Sequencing

Не просто сортировать по priority — учитывать **последовательность работ**:

| Если в Now | Перед ним обязательно |
|------------|------------------------|
| Изменение индекса | VACUUM ANALYZE, baseline EXPLAIN |
| Денежная логика fix | Recovery test (фаза 09) |
| Schema rename | Multi-step plan (Sadalage Part II) |
| Index drop | 30 дней мониторинга `pg_stat_user_indexes` |
| Drop column | Проверка зависимостей: route_map + impact через GitNexus |

Зафиксируй в секции «Sequencing notes» в ROADMAP.

### 2.4. Структура ROADMAP

См. `TEMPLATES.md §3`. Обязательные секции:
- TL;DR (5–7 пунктов)
- Verdict
- 🔴 Сейчас (Now) — critical и high с low/medium effort
- 🟡 Дальше (Next) — high с medium/large effort, medium с большим impact
- 🟢 Потом (Later) — долг, мониторить
- Карта по категориям (matrix)
- Sequencing notes
- Источники (дедуплицированные books / docs)

### 2.5. Verdict

| Verdict | Условия |
|---------|---------|
| `pass` | 0 critical, ≤ 5 high, ≤ 30 medium |
| `pass-with-conditions` | 0 critical, ≤ 10 high, перечислить блокеры если решат двигать в прод |
| `fail` | ≥ 1 critical |

Verdict не блокирует пайплайн. Это сигнал владельцу. `fail` означает «есть проблема, которую нельзя оставить без внимания, в первую очередь раскрыть в Phase 11».

### 2.6. Effort estimation reality check

S (hours): tweak конфига, добавить индекс CONCURRENTLY, добавить timeout.
M (1-2 дня): рефакторинг одной функции, fix N+1 в одном месте, добавить idempotency_key endpoint.
L (неделя): миграция типа колонки multi-step, переход на pooling, partitioning одной таблицы.
XL (>1 неделя): переход на read replicas с правкой кода, sharding, переход на новую СУБД.

Не недооценивай. Лучше M на S-выглядящую задачу, чем S на M-задачу.

## 3. Что НЕ делаешь

- Не «списываешь» findings на этой фазе. Пере-калибровка confidence — да, отбрасывание — нет.
- Не выдумываешь рекомендации без findings.
- Не делаешь общие советы «использовать индексы». Каждый пункт roadmap — конкретен и привязан к finding.

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 10
```

Проверяет:
- `audit/ROADMAP.md` существует.
- Содержит секции из TEMPLATES.md §3.
- Verdict присутствует и валиден.

## 5. Артефакты

- `audit/10_synthesis.md` — что делал в этой фазе.
- `audit/ROADMAP.md` — главный артефакт.

После этой фазы → **обязательно** `phase_10a_self_audit.md`.
