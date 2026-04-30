# Refresh — обновление существующего manifest

> Запускается через `bash database-audit/init.sh --refresh`. Цель: найти что изменилось в проекте с последнего init и обновить только релевантные секции manifest.

---

## Шаги

### 1. Прочитай существующий manifest

```bash
cat audit/manifest.yml | head -50
```

Зафиксируй:
- `refresh_state.previous_git_head` (если есть)
- `project.git_head` (текущий из manifest)
- `project.size`, models_count, migrations_count

### 2. Текущее состояние проекта

```bash
git rev-parse HEAD                              # current head
git diff --stat <prev_head>..HEAD               # changed files since
find . -name '*.prisma' -not -path '*/node_modules/*' | wc -l  # current schema files
find packages/db/prisma -name '*.sql' 2>/dev/null | wc -l       # current migrations
```

### 3. Diff против manifest

Проверь:
- [ ] Изменился ли список `paths.schema_files`? (новые `*.prisma` появились/удалены)
- [ ] Изменился ли `paths.migration_files.files`? (новые миграции)
- [ ] Изменились ли files в `hints.money_columns[*].file`? (модифицированы)
- [ ] Изменились ли `hints.transaction_sites[*].file`?

### 4. Targeted re-discover

Только для секций, у которых что-то изменилось:

| Что изменилось | Какой sub-prompt запустить |
|---|---|
| Новый/изменённый `*.prisma` | `00a_discover_money.md` (re-check money columns) + `00c_discover_pii.md` |
| Новая миграция | `00e_discover_migrations.md` |
| Изменён файл из `hints.transaction_sites` | `00b_discover_transactions.md` |
| Новые ORM-вызовы (множественные новые файлы в `apps/`) | `00d_discover_n_plus_one.md` |

### 5. Обнови manifest

Сохраняя структуру:
- **Не удаляй** старые hints, если файлы всё ещё существуют
- **Добавь** новые
- **Обнови** `lines` если файл менялся (line numbers сместились)
- Заполни `refresh_state`:
  ```yaml
  refresh_state:
    last_refresh_at: "2026-05-15T10:00:00+00:00"
    previous_git_head: "abc1234"
    changes_since_last:
      - "packages/db/prisma/models/billing.prisma (new)"
      - "apps/crm/src/payment.ts (lines shifted: 40 → 55)"
  ```

### 6. Re-validate

```bash
python3 database-audit/validators/validate_manifest.py audit/manifest.yml --strict
```

### 7. Сообщи пользователю

> Manifest refreshed.
> Diff: +3 schema files, +2 migrations, money_columns: 3→5, transaction_sites updated 2.
> Suggest re-running affected phases:
>   bash database-audit/run.sh phase 02
>   bash database-audit/run.sh phase 06
>   bash database-audit/run.sh finalize

---

## Когда delete + full re-discover лучше

- Major refactoring (>30% файлов схемы изменены)
- Изменение primary ORM
- Изменение размера проекта на класс (M → L)
- Прошло > 6 месяцев

В таких случаях — `rm audit/manifest.yml && bash database-audit/init.sh`.
