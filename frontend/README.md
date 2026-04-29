# Frontend Audit Pipeline

> Аудит React / Next.js сайта за один прогон Claude Code. Семь фаз — от инвентаризации до приоритизированного roadmap.

---

## Для кого это

- У тебя сайт или веб-приложение на **React, Next.js, или похожем стеке**
- Хочешь понять «а что у нас вообще под капотом» — особенно если код писали разные команды
- Готовишься к редизайну, миграции или продаже бизнеса — нужна объективная картина
- Видишь что сайт тормозит, но не знаешь почему
- Хочешь регулярно (раз в квартал) сверять health score проекта

---

## Что аудит покажет

После прогона ты узнаешь:

| Вопрос | Где ответ |
|---|---|
| Что вообще лежит в проекте, какие технологии | Phase 0 — Inventory |
| Архитектура чистая или это спагетти | Phase 1 — Architecture |
| Почему сайт грузится медленно (и сколько денег это стоит) | Phase 2 — Performance |
| Найдут ли тебя в Google, может ли пользоваться слепой человек | Phase 3 — Accessibility & SEO |
| Есть ли известные дыры в безопасности | Phase 4 — Security |
| Удобно ли разработчикам работать (текучка, скорость фич) | Phase 5 — DX & Tooling |
| **Что чинить в каком порядке** | Phase 6 — Roadmap (главный артефакт) |

---

## Быстрый старт

### Что нужно установить (один раз)

```bash
# Claude Code (если ещё нет)
# https://claude.com/claude-code

# Serena — навигация по коду
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant

# GitNexus — граф кода и история
npm install -g gitnexus
gitnexus setup
```

### Запуск аудита

1. **Скопируй папку `frontend/`** в корень проекта, который аудируем (рядом с `package.json`).
2. **Открой Claude Code** в этой папке проекта. Проверь `claude mcp list` — должны быть `serena` и `gitnexus`.
3. **Скопируй промпт** из `prompts/00-master-prompt.md` и вставь в чат.
4. Дальше — по шагам. После каждой фазы агент пишет 1-2 строки статуса, ты говоришь «дальше».
5. На выходе — **`roadmap.md`** в папке `audit-pipeline/reports/`.

Если хочется руководить процессом точечно — можно запускать каждую фазу отдельно через `prompts/phase-N-*.md`.

---

## Сколько это занимает

| Размер проекта | Время |
|---|---|
| Маленький лендинг (<5k LOC) | ~30 минут |
| Средний сайт (5k–30k LOC) | ~60-90 минут |
| Большое веб-приложение (30k+ LOC) | 2-3 часа |

Прогон не блокирующий — можно делать параллельно с другими задачами, агент работает сам.

---

## Структура папки

```
frontend/
├── README.md                       ← ты здесь
├── 00-MASTER-PLAN.md               ← логика всего пайплайна (для агента)
├── 01-inventory.md                 ← Phase 0: инвентаризация
├── 02-architecture.md              ← Phase 1: архитектура и тех.долг
├── 03-performance.md               ← Phase 2: производительность и Core Web Vitals
├── 04-accessibility-seo.md         ← Phase 3: доступность и SEO
├── 05-security-deps.md             ← Phase 4: безопасность и зависимости
├── 06-dx-tooling.md                ← Phase 5: DX, тулинг, CI/CD
├── 07-roadmap-synthesis.md         ← Phase 6: финальный план
└── prompts/                        ← готовые промпты для копипаста в Claude Code
    ├── 00-master-prompt.md         ← запустить весь пайплайн
    ├── phase-0-inventory.md        ← или каждую фазу отдельно
    ├── phase-1-architecture.md
    ├── phase-2-performance.md
    ├── phase-3-accessibility-seo.md
    ├── phase-4-security.md
    ├── phase-5-dx-tooling.md
    └── phase-6-roadmap.md
```

---

## Какие инструменты использует аудит

| Инструмент | Зачем |
|---|---|
| **Claude Code** | Оркестрация: читает конфиги, запускает bash, пишет отчёты |
| **Serena** (MCP) | Семантика кода: find_symbol, find_references — где что используется |
| **GitNexus** (MCP) | История репо: hot spots (где часто ломаются), авторы, DORA-метрики |
| **Lighthouse** | Замеры производительности, Core Web Vitals |
| **axe-cli** | Проверка accessibility |
| **madge / jscpd** | Циклические зависимости, дублирование кода |
| **npm audit** | Известные уязвимости в зависимостях |
| **knip / depcheck** | Поиск мёртвого кода и неиспользуемых пакетов |

Если каких-то инструментов нет — пайплайн работает в degraded режиме и помечает это в отчёте.

---

## Что получишь на выходе

```
audit-pipeline/reports/
├── 01-inventory-report.md          ← карта проекта
├── 02-architecture-report.md       ← архитектурные находки
├── 03-performance-report.md        ← замеры + узкие места
├── 04-accessibility-seo-report.md  ← WCAG + SEO находки
├── 05-security-deps-report.md      ← дыры + устаревшие пакеты
├── 06-dx-tooling-report.md         ← DX-проблемы
├── findings.json                   ← машиночитаемый список всех находок
└── roadmap.md                      ← Now / Next / Later план с DoD
```

**Roadmap** — главный артефакт. Эпики приоритизированы по формуле `(impact × confidence) / effort` с буст-множителем для hot spots (мест, которые часто ломаются по статистике git).

Каждая находка содержит: severity, evidence (файл:строка), impact, fix, references, effort, confidence.

---

## Принципы

- **Факты, не мнения.** Каждая находка с измерением или ссылкой на источник.
- **Severity по импакту, не по эстетике.**
- **Hot spots first.** Чиним там, где часто ломается (методология Adam Tornhill).
- **Тесты до рефакторинга.** Сначала характеризационные тесты, потом изменения (Michael Feathers).
- **Никаких преждевременных оптимизаций.** Только то, что подтверждено замерами.
- **Никаких переписываний с нуля.** Точечные fix'ы.
- **Read-only.** Пайплайн ничего не меняет в коде, только смотрит.

---

## Источники методики

- *Clean Architecture* — Robert C. Martin
- *Refactoring* — Martin Fowler
- *Your Code as a Crime Scene* — Adam Tornhill
- *Working Effectively with Legacy Code* — Michael Feathers
- *High Performance Browser Networking* — Ilya Grigorik
- *Web Performance in Action* — Jeremy Wagner
- *Inclusive Components* — Heydon Pickering
- *Accelerate* — Forsgren, Humble, Kim
- W3C WCAG 2.2, WAI-ARIA APG
- Web.dev (Core Web Vitals, A11y)
- Next.js, React official docs
- OWASP Top 10, OWASP Cheat Sheets

---

## Переаудит

Раз в квартал — повторный прогон по тем же фазам. Сравнить health score, увидеть прогресс, обновить roadmap. Это как ТО для машины: один раз — это снимок, регулярно — это контроль здоровья проекта.

---

## FAQ

**Это безопасно? Никто не утечёт мой код?**
Аудит запускается локально на твоей машине. Claude Code работает с твоего аккаунта Anthropic — данные передаются только в API Anthropic, как при обычном использовании Claude. Если у тебя enterprise-договор с Anthropic — всё под NDA.

**Можно запустить на закрытом проекте без интернета?**
Нет, Claude Code требует подключения к Anthropic API. Но **никаких других внешних сервисов** пайплайн не использует — всё остальное работает локально.

**А если у меня не Next.js, а Vue/Svelte/Angular?**
Этот пайплайн заточен под React-стек. Для других — используй универсальный пайплайн в [`../codebase/`](../codebase) — он работает с любым языком и фреймворком.

**Можно адаптировать под свой проект?**
Да, это просто markdown-инструкции. Меняй пороги severity, добавляй фазы, расширяй чек-листы. Главное — не ломай формат `findings.json`, он используется фазой Roadmap для синтеза.

---

## Автор

Кирилл Вечкасов · [vechkasov.pro](https://vechkasov.pro)
