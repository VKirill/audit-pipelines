# ADR-XXX — <Название>

- **Status:** proposed (<YYYY-MM-DD>)
- **Supersedes:** —
- **Related:** <other ADR ids>
- **Owners:** TBD

## Context

<2-4 параграфа: что наблюдаем, какие проблемы, со ссылками на findings из соответствующих phase-отчётов>

Найденные проблемы (audit + book references):
- ...
- ...

## Decision

<Конкретное архитектурное решение. Описание новой инварианты.>

### Rules

1. ...
2. ...
3. ...

## Consequences

### Positive

- ...

### Negative

- ...

### Trade-offs

| Что выигрываем | Что теряем |
|---|---|
| ... | ... |

## Implementation plan

1. **Phase A** — ...
2. **Phase B** — ...
3. **Phase C** — ...

## Fitness function (CI gate)

```ts
test('<инвариант>', () => {
  // ...
  expect(<метрика>).toEqual(<цель>);
});
```

Эта проверка должна жить в `<repo>/<test-path>` и падать при нарушении инварианты.

## Migration strategy

- [ ] <первый incremental step>
- [ ] <second>
- [ ] <…>

Strangler fig pattern: новая логика добавляется параллельно, старая удаляется только после миграции всех вызывателей.

## Verification

После выполнения migration plan:
1. <команда> → <ожидаемый результат>
2. <команда> → <ожидаемый результат>

## References

- <Author>, *<Book>*, §<chapter>: <конкретный концепт>
- <Author>, *<Book>*, §<chapter>: <конкретный концепт>

## Open questions

- <вопрос #1>
- <вопрос #2>
