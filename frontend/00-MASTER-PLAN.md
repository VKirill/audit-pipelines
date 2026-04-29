# Frontend Audit Pipeline — Master Plan

Универсальный аудит-пайплайн для React/Next.js проектов. Применим к любой кодовой базе. Опирается на классику: Clean Architecture (Martin), Refactoring (Fowler), Designing Data-Intensive Applications (Kleppmann), High Performance Browser Networking (Grigorik), Inclusive Components (Heydon Pickering), Web Performance in Action (Wagner), Atomic Design (Frost), а также официальные гайды React, Next.js, OWASP, W3C WAI-ARIA, Web.dev.

---

## Логика пайплайна

Аудит идёт от карты территории к точечным фиксам. Сначала понимаем что есть, потом измеряем здоровье по каждой оси, потом синтезируем roadmap.

```
Phase 0  → Inventory & Mapping        (что вообще есть)
Phase 1  → Architecture & Code Health (как оно устроено)
Phase 2  → Performance & Core Web Vitals
Phase 3  → Accessibility & SEO
Phase 4  → Security & Dependencies
Phase 5  → DX, Tooling & CI/CD
Phase 6  → Synthesis & Roadmap        (что чинить и в каком порядке)
```

Каждая фаза — отдельный MD с:
- целью фазы,
- инструментами (где Claude Code, где Serena, где GitNexus, где внешние тулзы),
- пошаговым чек-листом,
- шаблоном отчёта,
- готовыми промптами.

---

## Когда какой инструмент

**Claude Code** — основной исполнитель. Запускает команды, читает файлы, пишет отчёты, делает правки. Используется во всех фазах.

**Serena (MCP)** — семантический слой над кодом. Использовать когда нужно:
- найти все usages символа (компонент, хук, утилита) точно, а не grep'ом,
- понять структуру класса/модуля без чтения целиком,
- сделать рефакторинг с переименованием по всему проекту,
- получить definition / references / call hierarchy.
Дешевле по токенам чем читать файлы целиком. Незаменима в Phase 1 (архитектура) и Phase 6 (фиксы).

**GitNexus (MCP)** — историческая ось. Использовать когда нужно:
- найти hot spots (файлы с максимумом коммитов = риск-зоны),
- понять кто и когда вносил изменения в проблемный модуль (контекст для решений),
- увидеть совместное изменение файлов (скрытая связанность модулей),
- проследить эволюцию архитектуры.
Главное оружие в Phase 1 (тех.долг через историю) и Phase 6 (приоритизация).

**Внешние тулзы** (npm/CLI) — для замеров. Lighthouse, axe, source-map-explorer, depcheck, knip, madge, eslint, npm audit. Claude Code их запускает и парсит вывод.

---

## Файлы пайплайна

| Файл | Что делает |
|---|---|
| `00-MASTER-PLAN.md` | этот файл |
| `01-inventory.md` | инвентаризация проекта |
| `02-architecture.md` | архитектура и здоровье кода |
| `03-performance.md` | производительность и CWV |
| `04-accessibility-seo.md` | a11y и SEO |
| `05-security-deps.md` | безопасность и зависимости |
| `06-dx-tooling.md` | DX, инструменты, CI/CD |
| `07-roadmap-synthesis.md` | синтез и roadmap |
| `prompts/` | готовые промпты для Claude Code по фазам |

---

## Как запускать

1. Положи всю папку `audit-pipeline/` в корень проекта (или рядом).
2. Открой Claude Code в репозитории. Проверь что подключены MCP: Serena и GitNexus.
3. Скажи Claude Code: «Прочитай `audit-pipeline/00-MASTER-PLAN.md` и начни с Phase 0. После каждой фазы создавай отчёт в `audit-pipeline/reports/NN-<phase>-report.md` и жди подтверждения перед переходом к следующей».
4. Идём фаза за фазой. Не пропускай — каждая опирается на данные предыдущей.
5. На выходе Phase 6 — `roadmap.md` с приоритизированным списком задач.

---

## Принципы аудита

**Факты, не мнения.** Каждое утверждение в отчётах должно опираться на измерение, файл, коммит или цитату из официального гайда. Никаких «мне кажется тут плохо».

**Severity по импакту, не по эстетике.** Баг который тормозит LCP на 2с важнее чем неровные отступы. Severity: `critical` / `high` / `medium` / `low` / `nit`.

**Effort оценивается честно.** S (≤2ч), M (полдня-день), L (несколько дней), XL (неделя+).

**Приоритет = impact × confidence / effort.** В roadmap сортируем по этому.

**Каждая находка должна иметь fix.** Не «здесь плохо», а «здесь плохо, потому что X, чинится так Y, ссылка Z».

---

## Output structure (что получит пользователь в конце)

```
audit-pipeline/
├── reports/
│   ├── 01-inventory-report.md
│   ├── 02-architecture-report.md
│   ├── 03-performance-report.md
│   ├── 04-accessibility-seo-report.md
│   ├── 05-security-deps-report.md
│   ├── 06-dx-tooling-report.md
│   └── findings.json          # машиночитаемый список находок
└── roadmap.md                 # финальный план действий
```
