# Phase 04 — Hot-spots (churn × fan-in)

> **Цель:** объективно найти самые опасные файлы кодовой базы. Хот-спот = высокая частота изменений × высокая зависимость от других модулей.
>
> **Книга:** Adam Tornhill, *Your Code as a Crime Scene* 2e (2024) §3 Hot-spots, §7 Coupling.

## Inputs

- `reports/00-bootstrap.md` — путь и тип репо.
- `reports/01-mcp-probe.md` — есть ли gitnexus.
- `reports/03-deterministic.md` — `largest-files.log`, `madge` circular.

## Outputs

- `nodejs-audit/reports/04-hotspots.md`
- `nodejs-audit/reports/raw/hotspot-churn.tsv` — `count\tpath`
- `nodejs-audit/reports/raw/hotspot-matrix.tsv` — объединённая матрица `churn × fan-in × LOC × risk`

## Шаги

### 1. Churn — частота изменений за 90 дней

```bash
git log --since=90.days --name-only --pretty=format: \
  | grep -E '\.(ts|tsx|vue|js|jsx)$' \
  | grep -v -E "node_modules|\.nuxt|\.output|dist" \
  | sort | uniq -c | sort -rn | head -50 \
  > reports/raw/hotspot-churn.tsv
```

Это даёт топ-50 файлов, в которые чаще всего коммитят.

### 2. Fan-in — сколько файлов импортируют этот файл

#### Вариант A — есть GitNexus (быстро и точно)

Для каждого из top-50 файлов из шага 1:

```
mcp__gitnexus__impact (target=<symbol>, direction=upstream)
```

Сохрани счётчик direct callers + transitively affected processes + risk level.

#### Вариант B — нет GitNexus (медленно, через grep)

Для каждого файла из top-50:

```bash
basename=$(basename "$file" .ts)
fanin=$(grep -rEn "from ['\"].*${basename}['\"]" <src-roots> --include="*.ts" --include="*.vue" 2>/dev/null | wc -l)
```

Это приблизительно — не поймает alias-импорты по умолчанию. Для FSD-проектов с alias `@shared/`, `@features/` — добавь поиск по path-aliases из tsconfig.

### 3. LOC

Из `raw/largest-files.log` (phase-03) — сразу есть.

### 4. Объединить в матрицу

Запиши TSV `raw/hotspot-matrix.tsv`:

```
path	churn	fan_in	loc	risk
apps/bot/src/shared/middleware/session.ts	8	167	200	HIGH
...
```

**Risk score** (упрощённая формула Tornhill):

- `HIGH`: churn ≥ 5 И (fan_in ≥ 50 ИЛИ LOC ≥ 500).
- `MEDIUM`: churn ≥ 3 ИЛИ fan_in ≥ 30.
- `LOW`: остальное.

### 5. Cross-reference с deterministic findings

Проверь — топ-5 hot-spot файлов:
- Есть ли среди них файлы с самым высоким ESLint-errors из phase-03? Это **компаундный риск** — много багов И много изменений.
- Есть ли среди них файлы из madge circular cycles? — тоже компаундный.

## Шаблон отчёта `04-hotspots.md`

```markdown
# Hot-spot analysis (churn × fan-in)

> **Method:** Tornhill, *Your Code as a Crime Scene* §3.

## TL;DR

[2 предложения: главный hot-spot и почему он главный.]

## Топ-15 hot-spots

| # | Файл | Churn (90d) | Fan-in | LOC | Risk | Compound |
|---|------|------------:|-------:|----:|------|----------|
| 1 | session.ts | 8 | 167 | 200 | HIGH | + 3 ESLint err, in cycle |
| 2 | ... |
| ... |

## Top-3 для немедленного внимания

### #1 <path>
- **Метрики:** churn=N · fan-in=M · LOC=K
- **Smell:** [какой анти-паттерн — god-object / shallow / hot-cycle]
- **Why dangerous:** [короткий рассказ — что ломается при следующем изменении]
- **Какая фаза подхватит:** Phase 5 (architecture) / Phase 6 (readability) / Phase 11 (refactoring target)

### #2, #3

## Что не получилось измерить

- Если fan-in — приблизительный (нет gitnexus): запиши «approx via grep, expect ±20% error».
- Если churn короткий (репо < 90 дней): запиши «only N days history available».
```

## Критерии завершения

- `reports/04-hotspots.md` существует.
- `reports/raw/hotspot-matrix.tsv` существует и валиден.

## Сигналы в чат

- Старт: `[PHASE 04] STARTED — Hot-spots (churn × fan-in)`
- Конец: `[PHASE 04] DONE — reports/04-hotspots.md`

→ Переход к **phase-05-architecture-ddd.md**.
