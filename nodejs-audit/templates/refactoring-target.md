# Refactoring target: `<path>`

> **Tracked by:** [ADR-XXX](../ADR-DRAFTS/ADR-XXX-...md)
> **Source phases:** phase-04 (hot-spot), phase-06 (readability)

## Current state

| Metric | Value |
|---|---:|
| LOC | <N> |
| Imports (fan-in) | <M> |
| Hot-spot churn (90d) | <K> commits |
| ESLint errors | <if any> |
| In a circular cycle? | <yes/no> |
| Risk classification | <HIGH/MEDIUM/LOW> |

## Smell

<Конкретный анти-паттерн с одной фразой:>
- **God object** — слишком много ответственностей в одном модуле.
- **Shallow module** — много public функций, каждая делает мало (Ousterhout §4).
- **Hot-spot** — частые изменения × высокий fan-in (Tornhill §3).
- **Anemic** — только данные/queries, без поведения (Khononov §3).
- **Direct vendor coupling** — импорты вендорских типов в domain (Evans §14).

## Decomposition target

<Что должно стать после рефактора. Опиши **state**, не процесс.>

```
<схема файлов после рефактора>
```

## Cytometric criteria (fitness function)

Эти тесты должны быть **зелёными** после рефактора и жить в CI как guard:

```ts
// например: tests/architecture/<slug>.fitness.test.ts
test('<file> has fewer than <N> imports', () => {
  const count = grepCount("from '<path>'");
  expect(count).toBeLessThan(<N>);
});

test('<file> LOC ≤ <M>', () => {
  const loc = readFile('<path>').split('\n').length;
  expect(loc).toBeLessThanOrEqual(<M>);
});

test('no circular cycle including <file>', () => {
  expect(madge.checkCircular(<src>)).not.toContain('<path>');
});
```

## Migration plan (atomic commits)

### Step 1 — <одно действие>

**Goal:** <что станет>
**Commit message:** `refactor(<scope>): <action>`
**Files changed:** ...
**Verify:**
```bash
<команда> # ожидаемый output
```

### Step 2 — <одно действие>

...

### Step 3 — <…>

...

## Definition of Done

- [ ] Все 3 fitness-теста зелёные.
- [ ] `npm run test` без regression.
- [ ] `npm run lint` без regression.
- [ ] `npx madge --circular` не показывает новых циклов.
- [ ] `wiki/components/<area>.md` обновлён.

## References

- Adam Tornhill, *Your Code as a Crime Scene* §3 (Hot-spots), §7 (Coupling).
- John Ousterhout, *Philosophy of Software Design* §4 (Deep modules), §5 (Information hiding).
- <если применимо> Evans, *DDD* §14 (Anti-corruption layer).
