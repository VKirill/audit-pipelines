# Phase 06 — Readability

> **Цель:** оценить читаемость и именование через Ousterhout (deep modules) и Sandi Metz (TRUE).
>
> **Книги:** Ousterhout *A Philosophy of Software Design* §4-5, §19 · Bugayenko *Elegant Objects*.

## Inputs

- `reports/03-deterministic.md` — топ-длинных файлов.
- `reports/04-hotspots.md` — компаунд-риски (длинный + churn).
- `reports/raw/largest-files.log` — список длинных файлов.

## Outputs

- `nodejs-audit/reports/06-readability.md`
- `nodejs-audit/reports/raw/todos.log`
- `nodejs-audit/reports/raw/bad-names.log`
- `nodejs-audit/reports/raw/magic-numbers.log`

## Шаги

### 1. TODO/FIXME/HACK/XXX

```bash
grep -rn "TODO\|FIXME\|HACK\|XXX" <src> \
  --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" --include="*.vue" \
  2>/dev/null > reports/raw/todos.log
```

### 2. Подозрительные имена файлов

```bash
find <src> -type f \( -name "*util*" -o -name "*helper*" -o -name "*manager*" \
  -o -name "*common*" -o -name "*misc*" -o -name "*processor*" \) \
  ! -path "*/node_modules/*" 2>/dev/null > reports/raw/bad-names.log
```

Эти имена — анти-паттерн (Ousterhout §5: имя должно намекать на ответственность).

### 3. Магические числа/строки

```bash
grep -rEn "[^0-9.A-Za-z_]([0-9]{3,})[^0-9.A-Za-z_]" <src> --include="*.ts" 2>/dev/null \
  | grep -v "test\|spec\|mock\|i18n\|locales\|http://\|https://" \
  | head -50 > reports/raw/magic-numbers.log
```

### 4. Однородность стилей (числа из phase-02 уже)

- await vs .then ratio.
- default vs named exports.
- kebab-case vs PascalCase.

### 5. Глубина 3 крупнейших файлов (Ousterhout §4)

Прочитай **первые 100 строк** топ-3 longest файлов из `largest-files.log`.

Оцени:
- **Deep module** — узкое API, глубокая реализация (мало публичных функций, много логики). ✅
- **Shallow module** — много публичных, но каждая делает мало. ❌

### 6. Комментарии

```bash
# Закомментированный код (грубая эвристика)
grep -rEn "^\s*//.*\b(function|const|return|await|import|export|class)\b" <src> --include="*.ts" 2>/dev/null \
  | grep -v "TODO\|FIXME\|JSDoc" | wc -l

# JSDoc coverage
PUBLIC=$(grep -rEn "^export (async )?function" <src> --include="*.ts" | wc -l)
JSDOC=$(grep -rEn "^/\\*\\*$" <src> --include="*.ts" | wc -l)
```

## Шаблон отчёта `06-readability.md`

```markdown
# Readability

## TL;DR
[Один абзац.]

## Оценки (X/50)

| Ось | Оценка |
|-----|--------|
| Именование | X/10 |
| Размер и структура | X/10 |
| Комментарии | X/10 |
| Однородность | X/10 |
| Магия | X/10 |

## Детально

### Именование (Ousterhout §5)
**Хорошие примеры:**
- `<file:line>` — `<fragment>` — почему хорошо
**Плохие примеры (`*-helper.ts`, `*-manager.ts`):**
- `<file>` — что делает, как переименовать

### Размеры (топ-10)
| Файл | Строк | Что внутри | Deep/Shallow |

### Комментарии
- TODO/FIXME: <count>
- JSDoc на публичных: <approx %>
- Закомментированный код: <count мест>

### Однородность
- await vs .then: <X : Y>
- Default vs named exports: <X : Y>
- Файлы со смешанным стилем: ...

### Магия
- Магических чисел: ~N
- Магических строк: ~M
- Топ-5 кандидатов на константы: ...

## Топ-10 файлов на рефакторинг

| # | Файл | Главная проблема | Cytometric target |
|---|------|------------------|-------------------|
| 1 | <path> | god-file 800 LOC | 800 → ≤300 LOC |
| 2 | ... | | |

## Pre-draft REFACTORING targets (для phase-12)

- `REFACTORING/<slug>.md` — для топ-3 файлов из таблицы выше.
```

## Критерии завершения

- `reports/06-readability.md` существует.

## Сигналы в чат

- Старт: `[PHASE 06] STARTED — Readability`
- Конец: `[PHASE 06] DONE — reports/06-readability.md`

→ Переход к **phase-07-security.md**.
