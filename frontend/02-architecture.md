# Phase 1 — Architecture & Code Health

**Цель:** оценить структурное здоровье кода. Найти архитектурные проблемы, тех.долг, дублирование, плохие зависимости. Это самая дорогая по времени фаза, но и самая полезная.

**Длительность:** 2–4 часа на средний проект.

**Опора на источники:**
- Robert C. Martin, *Clean Architecture* — границы, зависимости, инверсия.
- Martin Fowler, *Refactoring* — каталог запахов кода.
- Adam Tornhill, *Your Code as a Crime Scene* — hot spots, complexity × change frequency.
- Brad Frost, *Atomic Design* — иерархия компонентов.
- Dan Abramov, статьи по композиции React.

---

## Инструменты

- **Serena** — основной инструмент фазы. Все операции с символами идут через неё. Не читать целые файлы grep'ом, использовать `find_symbol`, `find_references`, `get_symbols_overview`.
- **GitNexus** — связка hot spots × сложность. Файл с 50 коммитами и 800 строками = криминальная сцена.
- **Claude Code** — оркестратор и автор отчёта.
- **Внешние тулзы:**
  - `madge` — граф зависимостей, циклы.
  - `eslint` с плагинами `eslint-plugin-react`, `eslint-plugin-import`, `eslint-plugin-boundaries`.
  - `tsc --noEmit` — типовые ошибки.
  - `knip` или `ts-prune` — мёртвый код.
  - `jscpd` — дублирование.
  - `complexity-report` или встроенные правила eslint (`complexity`, `max-lines`, `max-depth`).

---

## Чек-лист

### 1.1 Граф зависимостей и циклы

- [ ] Запустить `npx madge --circular --extensions ts,tsx,js,jsx src/` — есть ли циклы?
- [ ] `npx madge --image graph.svg src/` — визуализировать (опционально, для большого отчёта).
- [ ] Найти модули с >20 входящими зависимостями (god modules) и с >30 исходящими (god consumers).
- [ ] Проверить корректность направления зависимостей: UI зависит от логики, не наоборот. Логика не должна импортировать из `pages/` или `app/`.

### 1.2 Слои и границы

Идеальная структура (Clean Architecture для фронта):

```
app/ или pages/      → routes/composition (тонкий слой)
features/ или modules/ → бизнес-фичи (UI + state + api для одной фичи)
entities/            → доменные сущности (User, Product, …)
shared/              → переиспользуемые UI-киты, хуки, утилиты, конфиг
```

- [ ] Зафиксировать фактические слои в проекте.
- [ ] Найти нарушения: `shared/` импортирует из `features/`, два feature импортируют друг у друга, и т.д.
- [ ] Проверить `eslint-plugin-boundaries` — установить если нет, описать слои, прогнать.

### 1.3 Компоненты — здоровье

Через Serena (`get_symbols_overview` по компонентным папкам) собрать метрики:

- [ ] Размер компонентов (LOC). Флажок: >300 LOC.
- [ ] Кол-во props. Флажок: >10 props без явной группировки.
- [ ] Глубина props drilling — props передаются через >3 уровня.
- [ ] Смешение presentational и container логики (хуки данных + JSX в одном файле без причины).
- [ ] Inline-стили и magic numbers (через grep по `style={{`).
- [ ] Дублирование компонентов с похожими именами (`Button`, `MyButton`, `CustomButton`).

### 1.4 Хуки

- [ ] Каждый кастомный хук — что делает, где используется (Serena `find_references`).
- [ ] Хуки которые используются только один раз — кандидаты на инлайн.
- [ ] Хуки длиннее 100 строк — кандидаты на разбиение.
- [ ] Правила хуков: проверить что нет вызовов в условиях/циклах (eslint-plugin-react-hooks должен быть включён).
- [ ] `useEffect` злоупотребления: запросы которые должны быть в TanStack Query, синхронизация состояния которая не нужна, deps массивы с проблемами.

### 1.5 State management

- [ ] Карта глобального состояния. Что хранится глобально и почему.
- [ ] Server state vs client state — разделены ли (server state в TanStack Query/SWR, client state отдельно)?
- [ ] Локальное состояние которое должно быть глобальным (одни и те же данные fetch'атся в нескольких местах).
- [ ] Глобальное состояние которое должно быть локальным.
- [ ] Кэширование и инвалидация — стратегия описана?

### 1.6 Типизация

- [ ] `tsc --noEmit` — кол-во ошибок, кол-во `@ts-ignore` и `@ts-expect-error`.
- [ ] Подсчёт `any` и `as unknown as X` (grep).
- [ ] Подсчёт `// eslint-disable` (grep).
- [ ] Проверка строгости: `strict`, `noImplicitAny`, `strictNullChecks`, `noUncheckedIndexedAccess`.
- [ ] Контрактные типы с бэком — генерятся из OpenAPI/GraphQL или руками? Если руками — это риск.

### 1.7 Дублирование

- [ ] `npx jscpd src/ --min-lines 8 --min-tokens 60 --reporters console,json` — собрать топ дубликатов.
- [ ] Для каждого дубликата >30 LOC — решение: вынести в shared, оставить как есть, или это случайное совпадение?

### 1.8 Мёртвый код

- [ ] `npx knip` — экспорты без использования, файлы без импортов, неиспользуемые зависимости.
- [ ] Закомментированный код (grep `^//.*[a-z]` крупными блоками).
- [ ] Feature flags которые всегда true/false.

### 1.9 Сложность

- [ ] ESLint с правилами `complexity: [warn, 10]`, `max-lines: [warn, 300]`, `max-depth: [warn, 4]`, `max-params: [warn, 4]`.
- [ ] Топ-20 функций по цикломатической сложности.
- [ ] Соотнести с hot spots из Phase 0: высокая сложность + высокая частота изменений = красная зона (Tornhill).

### 1.10 Тестируемость

- [ ] Test coverage (если есть тесты).
- [ ] Какие компоненты/модули вообще не покрыты, особенно из hot spots.
- [ ] Качество тестов — снапшоты на всё подряд это плохой знак.

### 1.11 Документация и ADR

- [ ] README актуален? Есть инструкция запуска?
- [ ] Есть ли ADR (Architecture Decision Records)?
- [ ] Storybook — есть ли, актуален ли, покрытие?

---

## Шаблон отчёта `reports/02-architecture-report.md`

```markdown
# Architecture & Code Health Report

## Summary
- Циклов в графе зависимостей: N
- God modules (>20 входящих): N
- Компонентов >300 LOC: N
- TypeScript ошибок: N, @ts-ignore: N, any: N
- Дубликатов >30 LOC: N
- Мёртвых экспортов: N
- Покрытие тестами: N%

## Layers
[фактическая структура слоёв]

Нарушения границ:
1. src/shared/utils/foo.ts импортирует из src/features/cart/  — критично
2. ...

## Dependency graph
[ссылка на graph.svg или текстовое описание]

Циклы:
1. A.ts → B.ts → C.ts → A.ts
   Причина: ...
   Fix: ...

## God modules
| Модуль | Входящих | Исходящих | Заметки |
|---|---|---|---|
| src/lib/api.ts | 87 | 12 | один файл на весь API |

## Crime scenes (hot spot × complexity)
Файлы с >20 коммитов И сложность >15 ИЛИ LOC >400:

| Файл | Commits | LOC | Complexity | Owners | Severity |
|---|---|---|---|---|---|
| ProductCard.tsx | 47 | 612 | 22 | 3 | critical |
| ...

Это места куда пойдём в Phase 6 в первую очередь.

## Components health
- Total: N
- >300 LOC: N (список)
- >10 props: N (список)
- props drilling >3 уровня: N (список)

## Hooks
- Total custom hooks: N
- Used 1x: N (кандидаты на инлайн)
- >100 LOC: N
- useEffect для fetch (должно быть в TanStack Query): N

## State
- Глобальный state: [описание]
- Server state: [описание]
- Проблемы: ...

## Types
- TS errors: N
- @ts-ignore: N
- any: N (топ-10 файлов)
- Strict mode: ...

## Duplication
Топ-10 дубликатов с указанием файлов и рекомендацией.

## Dead code
- Unused exports: N
- Unused files: N (список)
- Unused deps: N (список)

## Findings
[список находок в формате findings.json — см. ниже]
```

---

## Формат findings.json

В конце Phase 1 (и каждой следующей) Claude Code дописывает находки в общий `reports/findings.json`:

```json
[
  {
    "id": "ARCH-001",
    "phase": "architecture",
    "title": "Циклическая зависимость в src/features/cart/",
    "severity": "high",
    "evidence": "madge output: cart/index.ts → cart/api.ts → cart/store.ts → cart/index.ts",
    "files": ["src/features/cart/index.ts", "src/features/cart/api.ts", "src/features/cart/store.ts"],
    "impact": "Сложно тестировать, риск runtime ошибок при tree-shaking, признак плохих границ.",
    "fix": "Вынести типы и интерфейсы в cart/types.ts, store не должен импортировать из index.ts.",
    "references": ["Clean Architecture, Ch. 14, Acyclic Dependencies Principle"],
    "effort": "M",
    "confidence": 0.95
  }
]
```

---

## Промпт для Claude Code

```
Сейчас выполняем Phase 1 аудита (audit-pipeline/02-architecture.md).

Контекст: ты уже сделал Phase 0, отчёт лежит в reports/01-inventory-report.md. Hot spots оттуда — твой основной таргет.

План:
1. Установи нужные dev-зависимости если их нет: madge, jscpd, knip. (спрашивай меня перед установкой)
2. Прогони граф зависимостей через madge. Найди циклы.
3. Через Serena (get_symbols_overview) собери метрики по компонентам и хукам в src/. Не читай файлы целиком — используй overview, потом find_symbol только для подозрительных.
4. Прогони jscpd, knip, tsc --noEmit. Собери метрики.
5. Возьми топ-20 hot spots из Phase 0 и для каждого через Serena посмотри overview + сложность. Это твои "crime scenes".
6. Через GitNexus возьми историю изменений по топ-5 crime scenes — кто менял, как часто, какие коммит-мессаги. Это даст контекст почему файл стал таким.
7. Заполни reports/02-architecture-report.md и допиши находки в reports/findings.json.

Правила:
- Каждая находка с severity, evidence, fix, ссылкой на источник.
- Не предлагай переписывать всё с нуля. Точечные fix'ы.
- Оценка effort честная: S/M/L/XL.
- В конце вопросы ко мне если что-то неясно.
```
