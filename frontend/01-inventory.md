# Phase 0 — Inventory & Mapping

**Цель:** получить полную карту проекта без оценок. Что есть, где лежит, какой возраст, какие технологии. Это база для всех следующих фаз.

**Длительность:** 30–60 минут на средний проект.

---

## Инструменты в этой фазе

- **Claude Code** — выполняет команды, собирает данные.
- **GitNexus** — возраст репозитория, частота коммитов, активные авторы, hot spots.
- **Serena** — индексация символов проекта (нужно один раз в начале).
- **Bash/CLI** — `cloc`, `tree`, `git log`, `npm ls`.

---

## Чек-лист

### 0.1 Метаданные репозитория

- [ ] Возраст репо (первый коммит, последний коммит)
- [ ] Кол-во коммитов суммарно и за последние 90 дней
- [ ] Активные ветки и стратегия ветвления (trunk / git-flow / github-flow)
- [ ] Активные контрибьюторы (последние 90 дней)
- [ ] Релизы / теги — есть ли semver?

> **GitNexus:** запросить статистику коммитов, авторов, активность по месяцам.

### 0.2 Стек и версии

- [ ] Node.js версия (`.nvmrc`, `engines` в package.json)
- [ ] Package manager (npm/yarn/pnpm) — определить по lockfile
- [ ] React версия, Next.js версия (если есть), router — Pages или App Router
- [ ] TypeScript версия и `strict` режим (вкл/выкл)
- [ ] Стилизация — CSS Modules / styled-components / Tailwind / Emotion / vanilla
- [ ] State — Redux / Zustand / Jotai / Context / TanStack Query / SWR
- [ ] Тесты — Jest / Vitest / Playwright / Cypress / нет
- [ ] Сборщик — Webpack / Turbopack / Vite / Rollup
- [ ] Деплой — Vercel / self-hosted / static / SSR

### 0.3 Структура проекта

- [ ] Дерево директорий до 3-го уровня (`tree -L 3 -I 'node_modules|.next|.git|dist'`)
- [ ] Кол-во файлов по типам (`cloc`)
- [ ] Точки входа (entry points) — `pages/`, `app/`, `src/index.tsx`
- [ ] Где живут компоненты, хуки, утилиты, типы, ассеты, тесты

### 0.4 Маршруты и публичная поверхность

- [ ] Список всех страниц/маршрутов (для Next.js — карта `app/` или `pages/`)
- [ ] API routes (если есть)
- [ ] Публичные ассеты (`/public`)
- [ ] Динамические vs статические страницы

### 0.5 Внешние интеграции

- [ ] Аналитика (GA, Yandex Metrica, GTM, Plausible, …)
- [ ] CMS (если есть) — headless / WordPress / Strapi / …
- [ ] Backend API (свой / сторонний / GraphQL / REST)
- [ ] CDN, хостинг изображений
- [ ] Сторонние скрипты на странице (виджеты, чаты, рекламные сети)

### 0.6 Инфраструктура и процессы

- [ ] CI/CD — есть ли (.github/workflows, .gitlab-ci.yml)?
- [ ] Линтеры и форматтеры (eslint, prettier, stylelint)
- [ ] Husky / lint-staged / pre-commit
- [ ] Документация (README, ADR, Storybook)
- [ ] Тип лицензии

### 0.7 Hot spots (через GitNexus)

- [ ] Топ-20 файлов по количеству коммитов за всё время
- [ ] Топ-10 файлов по количеству коммитов за последние 90 дней
- [ ] Файлы которые часто меняются вместе (couple analysis)
- [ ] Файлы с одним автором (bus factor risk)

> Это золото. Hot spots = места где скапливается тех.долг и баги. В Phase 1 будем смотреть их детально.

### 0.8 Индексация Serena

- [ ] Запустить индексацию проекта через Serena (`activate_project`, дождаться завершения)
- [ ] Убедиться что символы проиндексированы (тестовый запрос — найти любой компонент)

---

## Шаблон отчёта `reports/01-inventory-report.md`

```markdown
# Inventory Report

## Repo
- First commit: YYYY-MM-DD
- Last commit: YYYY-MM-DD
- Total commits: N
- Last 90 days: N
- Active contributors (90d): N
- Branching strategy: ...

## Stack
- Node: 20.x
- Package manager: pnpm 9.x
- Framework: Next.js 15.x (App Router)
- TypeScript: 5.x, strict: true
- Styling: Tailwind 4
- State: Zustand + TanStack Query
- Tests: Vitest + Playwright
- Build: Turbopack
- Deploy: Vercel

## Structure
[tree вывод, обрезанный до 3 уровней]

LOC by language (cloc):
- TS/TSX: N
- CSS: N
- JSON: N

## Routes
- / (static)
- /blog (SSG)
- /blog/[slug] (SSG, ~120 страниц)
- /api/contact (POST)
...

## External integrations
- Yandex Metrica: ID 12345678 (загружается в _app.tsx)
- API: https://api.example.com (REST, без типизации схемы)
...

## Infrastructure
- CI: GitHub Actions (lint + build, без тестов)
- ESLint: next/core-web-vitals
- Prettier: yes
- Husky: yes (pre-commit: eslint)

## Hot spots (top-10 by commit frequency, all time)
| File | Commits | Last touched | Authors |
|---|---|---|---|
| src/components/ProductCard.tsx | 47 | 2026-04-10 | 3 |
| ...

## Hot spots (last 90 days)
...

## Coupling (часто меняются вместе)
- ProductCard.tsx ↔ ProductList.tsx ↔ api/products.ts
...

## Bus factor risks
- src/lib/payment.ts — 1 автор, последние 12 коммитов
...

## Open questions
- Что такое src/legacy/? Используется ли?
- Почему две папки components — /components и /src/components?
```

---

## Промпт для Claude Code

> Файл `prompts/phase-0-inventory.md` — копируй и вставляй в Claude Code.

```
Сейчас выполняем Phase 0 аудита (см. audit-pipeline/01-inventory.md).

Задачи:
1. Собери все данные из чек-листа Phase 0.
2. Используй bash для метрик файловой системы (tree, cloc, git log).
3. Используй MCP GitNexus для статистики репозитория и hot spots.
4. Используй MCP Serena: вызови activate_project на корне репо чтобы проиндексировать символы. Дождись завершения индексации.
5. Заполни шаблон отчёта в reports/01-inventory-report.md.
6. В конце выведи "Open questions" — что осталось непонятно и нужно уточнить у меня.

Не делай никаких оценок. Только факты. Оценки будут в следующих фазах.
```
