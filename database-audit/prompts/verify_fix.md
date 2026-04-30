# Verify-fix — проверка применённых fix-ов

> **Когда использовать:** после того как разработчик пофиксил critical/high finding из предыдущего аудита. Промт re-проверяет, что паттерн ушёл, и обновляет статус.

---

## Команда пользователю

```
Прочитай database-audit/prompts/verify_fix.md и проверь применённые fix-ы.

PROJECT_PATH=/home/ubuntu/apps/<project>
FINDING_IDS=DB-TX-005,DB-MONEY-012,DB-LIVE-001    # comma-separated, или "all-critical"
mode=<static | live>
DATABASE_URL=<если live и нужен retest invariants>
```

---

## Алгоритм

### Шаг 1 — Read previous run

```bash
cd "$PROJECT_PATH"

# Findings из предыдущего прогона
test -f database-audit/results/findings.jsonl || {
  echo "FAIL: previous results not found. Run full audit first."; exit 1;
}

# Snapshot предыдущего состояния
cp database-audit/results/findings.jsonl database-audit/results/findings.previous.jsonl
```

### Шаг 2 — Iterate findings to verify

Для каждого ID из `$FINDING_IDS`:

```bash
finding=$(jq -c --arg id "$ID" 'select(.id == $id)' database-audit/results/findings.previous.jsonl)
file=$(echo "$finding" | jq -r '.location.file')
lines=$(echo "$finding" | jq -r '.location.lines')
subcategory=$(echo "$finding" | jq -r '.subcategory')
```

### Шаг 3 — Re-run targeted detectors

В зависимости от `subcategory`:

| Subcategory | Action |
|---|---|
| `lost-update` / `missing-transaction` | Прочитать `$file:$lines` через `serena.find_symbol include_body=true`. Проверить наличие `$transaction` / `BEGIN` / `FOR UPDATE` |
| `money-type` | Прочитать schema на `$file:$lines`. Проверить тип: `Float` → `Decimal` / `Numeric`? |
| `no-idempotency` | Серена `search_for_pattern` для `idempotency_key` / unique constraint. Проверить signature endpoint |
| `sqli` / `sqli-raw-unsafe` | Прочитать `$file:$lines`. Проверить: убран `$queryRawUnsafe`? Если оставлен — есть ли allowlist на input? |
| `pii-unencrypted-credentials` | Schema check: добавлено ли `@db.Encrypted` / pgcrypto wrapper / vault reference? |
| `fk-no-index` | Live mode: `psql -c "SELECT * FROM pg_indexes WHERE tablename='$table'"`. Static: проверить `@@index` в schema |
| `large-tx-wrap` / `dangerous-ddl` | Прочитать миграцию. Найти `CONCURRENTLY` / `IF EXISTS` / multi-step? |
| `live-balance-drift` | **Re-run live invariant query** — drift всё ещё > 0.01? |

### Шаг 4 — Update finding status

Для каждого проверенного finding:

```python
# В новом файле database-audit/results/findings.jsonl
{
  "id": "DB-TX-005",
  ...,
  "status": "fixed" | "still-open" | "partial-fix" | "regressed",
  "verify": {
    "verified_at": "2026-05-15T10:00:00Z",
    "verified_by": "claude-opus-4-7",
    "previous_evidence": "Function deductFromBalance: read top-ups, update each in for-loop, no $transaction",
    "current_evidence": "Function now wraps loop in prisma.$transaction with isolationLevel: Serializable + advisory_xact_lock",
    "verdict": "fixed",
    "regression_risk": "low"
  }
}
```

### Шаг 5 — Live invariant re-verification (если applicable)

Для каждого `subcategory: live-balance-drift`:

```sql
-- Та же query что в 00b discover (см. invariant patterns)
SELECT id, name, denormalized, computed, denormalized - computed AS drift
FROM (...)
WHERE ABS(drift) > 0.01;
```

Если drift > 0.01 → finding `still-open` или новое `regressed`.
Если drift = 0 → `fixed`, evidence «invariant holds».

### Шаг 6 — Generate verify report

Сохрани в `database-audit/results/verify_report.md`:

```markdown
# Verify-fix report

**Date:** YYYY-MM-DD
**Verified findings:** N
**Status:**
- ✅ Fixed: K
- ⚠️ Partial: M
- ❌ Still open: P
- 🚨 Regressed: Q

## Detailed status

### DB-TX-005 — ✅ Fixed
**Previous:** Function `deductFromBalance` без $transaction
**Current:** Wrapped in `prisma.$transaction` + advisory lock (cbr.ts:42-110)
**Regression risk:** low — covered by integration test added in same commit

### DB-LIVE-001 — ⚠️ Partial fix
**Previous:** drift -7593 RUB on SKUDOV.NET
**Current:** drift = 0 на 4 проектах **но** новый case найден: tenant `xyz` drift +234 RUB
**Action:** root-cause не закрыт полностью, see new finding DB-LIVE-NNN

### DB-SEC-008 — ❌ Still open
**Previous:** $queryRawUnsafe в library-server.ts:96 (13 hits)
**Current:** 13 hits всё ещё present, без change

## New regressions
_(если найдены новые findings которые не было в previous run)_
```

### Шаг 7 — Diff в _meta.json

Добавь секцию verify в `_meta.json`:

```json
{
  ...,
  "verify": {
    "previous_run_at": "2026-04-30T...",
    "verified_at": "2026-05-15T...",
    "fixed_count": K,
    "still_open_count": P,
    "regressed_count": Q
  }
}
```

---

## Когда invoking ещё не было — exit clean

Если `findings.previous.jsonl` отсутствует и пользователь вызвал verify_fix.md → сообщи:

> No previous audit found. Run full audit first:
>   bash database-audit/init.sh
>   bash database-audit/run.sh all
> Then come back to verify_fix.md.

Не вычитывай pipeline для проекта в этой ситуации — это другая задача.
