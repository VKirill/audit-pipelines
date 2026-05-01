# Quick Wins (1 неделя, atomic commits)

> **Source:** `nodejs-audit/reports/FINAL-REPORT.md`.
> **Goal:** закрыть все Critical + High + Medium hygiene findings за 1 спринт (≤7 дней).
> **Style:** 1 шаг = 1 коммит = 1 PR (≤2 часов работы).

---

## Принципы выполнения

1. **Atomic commit:** один шаг — один коммит, не batch'ить.
2. **Verify after each:** перед `git commit` запусти fitness-команду из шага.
3. **Branch per step:** `git checkout -b fix/qw-<N>` перед каждым шагом.
4. **Rollback friendly:** если шаг сломал тесты — `git reset --hard HEAD~1` и переоценить.
5. **Прокачка через ИИ:** копируй промт в новую сессию Claude Code.

---

## P0 — Critical / High (1-2 дня)

### Step 1.1 — <ID> <название>

**Severity:** <Critical/High>
**Why:** <одно предложение>
**Cited:** <book §chapter / ASVS V<X.Y>>

**Files:**
- `<path1>` — <что меняется>
- `<path2>` — <что меняется>

**Cytometric criteria (до/после):**
- До: <метрика>
- После: <ожидаемая метрика>

**Promt (для новой сессии):**

```
Прочитай nodejs-audit/reports/<phase>.md, finding <ID>. Выполни:
1. ...
2. ...
3. Запусти `npm run lint && npm run test`.
4. Один коммит. Заголовок: `<conventional commit>`.
```

**Verify:**

```bash
<команда>
# ожидаемый output: <что>
```

**Commit message:** `<type>(<scope>): <action>`

---

### Step 1.2 — <…>

(аналогичный формат)

### Step 1.3 — <…>

---

## P1 — Medium hygiene (3-4 дня)

### Step 2.1 — <ID> <название>

(аналогичный формат)

### Step 2.2 — <…>

### Step 2.3 — <…>

…

---

## Проверка после всех Quick Wins

После закрытия P0 + P1 — запусти полный smoke:

```bash
npm run lint
npm run test
npm audit --audit-level=high
npx prettier --check "<src-globs>"
npx knip --reporter compact
npx madge --circular --extensions ts,tsx,js,jsx <src-roots>
```

Обнови `nodejs-audit/reports/_meta.json` (или повторно запусти аудит) — ожидаем:

- `verdict`: `warn` → `pass` (если P0 закрыт без новых находок).
- `counts.high`: 0.
- `scores.formatting`: 10/10.
- `scores.linting`: 10/10 (или близко).

---

## Ссылки

- [FINAL-REPORT.md](./FINAL-REPORT.md) — полный список findings.
- [ROADMAP.md](./ROADMAP.md) — что после Quick Wins.
- [ADR-DRAFTS/](./ADR-DRAFTS/) — для архитектурных решений (не Quick Win).
- [REFACTORING/](./REFACTORING/) — file-level таргеты (не Quick Win).
