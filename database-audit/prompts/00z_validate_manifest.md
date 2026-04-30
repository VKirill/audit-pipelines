# 00z — Self-validation gate

> Запускается после того как ты заполнил manifest. **До** того как сообщить пользователю «discover complete».

---

## 1. Run validator

```bash
python3 database-audit/validators/validate_manifest.py database-audit.manifest.yml --strict
```

Цель: **exit 0** в `--strict` режиме (sanity warnings = errors).

Если падает — прочитай ошибки, исправь, повтори.

## 2. Self-check coverage matrix

Для каждой обязательной hint-секции — проверь, что заполнено когда должно быть.

| Условие | Должно быть заполнено |
|---|---|
| Stack = Prisma | `paths.schema_files` ≥ 1, `paths.migration_files` определён |
| В коде есть `payment\|wallet\|balance` | `hints.money_columns` ≥ 1 |
| `hints.money_columns` непустой | `hints.money_endpoints` ≥ 1 (где-то меняем) |
| `hints.money_columns` имеет Float | `hints.transaction_sites` с `kind: missing-transaction` (ищи RMW) |
| Multi-tenant проект (>1 tenant в коде/конфиге) | `hints.multi_tenant_isolation` определён |
| Mongo проект | `paths.schema_files` содержит mongoose файлы |
| AI/ML проект (есть `pgvector`/`embedding`/`vector`) | `hints.vector_db_indexes` определён |
| Time-series в проекте (`event_log`/`metric`) | `hints.time_series_tables` определён |

```bash
# Автоматическая проверка
python3 - <<'PY'
import yaml, re, subprocess
m = yaml.safe_load(open('database-audit.manifest.yml'))
problems = []

# Money
def has_words(words):
    try:
        r = subprocess.run(['rg', '-c', '-iE', '|'.join(rf'\b{w}\b' for w in words),
                            '-g', '!node_modules', '-g', '!.git', '-g', '!*.lock', '.'],
                           capture_output=True, text=True, timeout=20)
        return bool(r.stdout.strip())
    except: return False

if has_words(['payment','wallet','balance','charge','invoice']) \
   and not m.get('hints',{}).get('money_columns'):
    problems.append('Money words in code but money_columns empty')

floats = [c for c in m.get('hints',{}).get('money_columns',[])
          if c['type'].lower() in ('float','double','real')]
if floats and not [t for t in m.get('hints',{}).get('transaction_sites',[])
                    if t['kind'] == 'missing-transaction']:
    problems.append('Float money exists but no missing-transaction site found — re-check')

# Vector / AI
if has_words(['embedding','pgvector','vector_search']) \
   and not m.get('hints',{}).get('vector_db_indexes'):
    problems.append('AI/ML project signals but vector_db_indexes empty')

# Migrations
mig = m.get('paths',{}).get('migration_files',{}) or {}
if not mig.get('tool') or mig.get('tool') == 'unknown':
    problems.append('migration tool unknown — clarify')

if problems:
    for p in problems: print(f'  PROBLEM: {p}')
    print(f'\nTotal: {len(problems)} issues — re-discover before proceeding')
    exit(1)
print('OK: coverage checks pass')
PY
```

## 3. Confidence on own work

Перед фиксацией задай себе 3 вопроса:

- [ ] Я **открыл и прочитал** каждый файл из `paths.schema_files`?
- [ ] Я **проверил по 5 разным признакам** (имя, тип, контекст использования) для каждой money-колонки?
- [ ] Я **запустил `rg`** на критичные паттерны хотя бы 5 раз?

Если на любой ответ «нет» — вернись и допили.

## 4. Записать `manifest.confidence`

После прохождения — добавь в manifest (не обязательно, но желательно):

```yaml
discovery_confidence:
  schema_coverage: high     # все schema файлы прочитаны полностью
  money_coverage: high      # systematic rg + manual review
  transactions_coverage: medium  # не все RMW проверены ручно
  pii_coverage: high
  migrations_coverage: high
```

(Технически не часть schema, но валидатор пропустит если в `additionalProperties: false` нет; при необходимости — фиксируй в `audit/00_setup.md`.)

## 5. Готово

Если всё прошло — сообщи пользователю:

> Discover complete. Manifest saved at `database-audit.manifest.yml`.
> Found: N money_columns (M Float), K transaction_sites (J missing), P pii_candidates (Q unencrypted).
> Recommend manual review before running phases.
