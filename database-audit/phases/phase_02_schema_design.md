# PHASE 02 — SCHEMA DESIGN

**Цель:** Проверить дизайн схемы — нормализация, типы, NULL-стратегия, naming, constraints.

**Источники:**
- C.J. Date, *Database Design and Relational Theory* — §3 Predicates, §6 Normalization, §10 Constraints.
- Bill Karwin, *SQL Antipatterns* — §1–13.
- Joe Celko, *SQL Programming Style* — §1 Naming, §4 Scales and Measurements.
- Vlad Mihalcea, *High Performance Java Persistence* — Ch. 9 Identifiers, Ch. 11 Inheritance.

---

## 1. Входы

- `audit/01_inventory.md`, `evidence/01_inventory/schema_summary.json`, `models_list.md`.

## 2. Что проверяешь (систематически)

### 2.1. Naming convention
- [ ] Единый стиль: `snake_case` или `camelCase` — но **один на проект**. Смешение → finding (low).
- [ ] Имена таблиц во множественном или единственном числе? Главное — единообразно.
- [ ] Колонки `id` или `<table>_id` — оба валидны, но не вперемешку.
- [ ] FK именуется как `<ref_table>_id` (Karwin §3 ID Required).

**Ссылка:** Celko *SQL Programming Style* §1.2; Karwin §3.

### 2.2. Типы данных

Систематический проход по `schema_summary.json`:

| Smell | Что искать | Что значит |
|-------|------------|-----------|
| `FLOAT`/`DOUBLE` для денег | `price`, `amount`, `balance`, `total` с типом float | **High/Critical** в зависимости от использования. Karwin §9 Rounding Errors. → Использовать `DECIMAL(p,s)` или integer-в-копейках. |
| `VARCHAR(255)` по умолчанию | каждый текстовый столбец `varchar(255)` | Указывает на cargo-cult. Размер должен иметь смысл. Karwin §10. |
| `TEXT` для коротких enum-полей | колонка `status TEXT` со значениями {`active`, `inactive`} | Должно быть либо CHECK constraint, либо ENUM, либо lookup table. Karwin §10, §5. |
| `TIMESTAMP WITHOUT TIMEZONE` | даты без TZ | В мульти-региональном проекте — bug. Использовать `TIMESTAMPTZ`. |
| `UUID` хранится как `VARCHAR(36)` | вместо native UUID | Лишние 12 байт + indexing penalty. Mihalcea Ch. 9. |
| `BLOB`/`BYTEA` для файлов | поле с бинарными данными | Karwin §11 Phantom Files. → Хранить в object storage, в БД только метаданные. |
| `JSON`/`JSONB` для структурированных данных | поле, которое могло бы быть отдельной таблицей | EAV smell, Karwin §5. |

### 2.3. Nullability и DEFAULTs

Date §3: «Each column must have a meaningful predicate. NULL means «applicability unknown», не «empty»».

- [ ] Каждая `NOT NULL` колонка — оправдана?
- [ ] Каждая `NULL`-колонка — есть ли смысл в неприменимости?
- [ ] DEFAULTs на временных колонках (`created_at DEFAULT NOW()`) — есть?
- [ ] DEFAULTs на boolean — явные?
- [ ] Колонки `deleted_at TIMESTAMP NULL` (soft-delete pattern) — есть индекс? обработано в queries?

### 2.4. Constraints

- [ ] `PRIMARY KEY` на каждой таблице (нет — critical, фиксируй здесь, проверяй в phase 03).
- [ ] `FOREIGN KEY` на reference-полях. **Отсутствие FK = high.**
- [ ] `UNIQUE` constraints на бизнес-уникальных полях (email, slug, idempotency_key).
- [ ] `CHECK` constraints на enum-подобных колонках без отдельной таблицы.
- [ ] `NOT NULL` строгость соответствует бизнес-логике.

### 2.5. Нормализация

Date §6: пройди по моделям и проверь:

- **1NF:** все ли значения атомарны? (CSV в одном поле = Karwin §1 Jaywalking).
- **2NF:** в композитных ключах — каждая не-ключевая колонка зависит от **полного** ключа?
- **3NF:** транзитивные зависимости устранены?
- **BCNF:** каждый детерминант — superkey?

В реальности:
- Слишком плоские таблицы (избыточная denormalization без причины) → high.
- Слишком нормализованные (5 JOIN для отображения профиля) → medium.
- Сознательная denormalization для performance — нормально, **но должно быть задокументировано** (комментарий в schema или ADR). Иначе → medium с рекомендацией задокументировать.

### 2.6. Антипаттерны Karwin

Систематический проход:

| Antipattern | Где смотреть |
|-------------|--------------|
| §1 Jaywalking (CSV в поле) | колонки tags/categories/permissions с разделителями |
| §2 Naive Trees (Adjacency List только) | parent_id pattern без расширений |
| §5 EAV (Entity-Attribute-Value) | таблицы вида (entity_id, attribute_name, value) |
| §6 Polymorphic Associations | колонка с `entity_type` + `entity_id` без FK |
| §7 Multicolumn Attributes | `tag1`, `tag2`, `tag3` |
| §8 Metadata Tribbles | разные таблицы для разных тенантов через имя |

Каждый найденный — finding.

### 2.7. Audit-поля

- [ ] `created_at`, `updated_at` — есть на бизнес-таблицах?
- [ ] `created_by`, `updated_by` — есть где надо для аудита?
- [ ] `version`/`row_version` для optimistic locking — есть на таблицах с конкурентной записью? (см. phase 05).

### 2.8. Идентификаторы

Mihalcea Ch. 9:

| Тип ID | Pros | Cons | Когда |
|--------|------|------|-------|
| `BIGINT` auto | компактно, быстрые индексы | угадываемые, проблемы в распределённой среде | один сервис, не api-public ID |
| `UUID v4` | глобально уникальные, не угадываемые | hot writes по btree-индексу, размер | distributed |
| `UUID v7` / `ULID` | sortable, не угадываемые | менее распространены | new projects |
| `serial` (PG) / `auto_increment` | классика | sequence gaps при rollback | legacy |

Если ID = sequential int + используется как public ID в URL → finding (medium, security/IDOR risk, плюс утечка business metrics).

## 3. Quotas

Минимум 5 findings (M-проект). Если меньше — либо ты не дочитал систематически, либо проект очень мал (обнови `size` в memory).

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 02
```

Required evidence:
- `evidence/02_schema_design/normalization_analysis.md`
- `evidence/02_schema_design/types_audit.md`
- `evidence/02_schema_design/karwin_antipatterns.md`

## 5. Артефакты

- `audit/02_schema_design.md`
- evidence файлы выше

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.money_columns` (для money_floats), `hints.json_overuse`, evidence/01/schema_summary.json

**Запуск:**
```bash
bash database-audit/run.sh phase 02
```

После детекторов агент дополняет `audit/02_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
