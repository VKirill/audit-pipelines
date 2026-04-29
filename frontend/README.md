<div align="center">

  <h1>🎨 Frontend Audit Pipeline</h1>

  <p>
    <b>Аудит React / Next.js сайта за один прогон Claude Code.</b><br/>
    Семь фаз — от инвентаризации до приоритизированного roadmap.
  </p>

  <p>
    <img src="https://img.shields.io/badge/stack-React_%2F_Next.js-61dafb?logo=react&logoColor=black" alt="React/Next.js"/>
    <img src="https://img.shields.io/badge/phases-7-blue" alt="7 phases"/>
    <img src="https://img.shields.io/badge/time-30--180_min-green" alt="30-180 min"/>
    <img src="https://img.shields.io/badge/mode-read--only-success" alt="Read-only"/>
  </p>

  <p>
    <a href="../README.md">← Назад к Audit Pipelines</a> ·
    <a href="../codebase">Универсальный пайплайн →</a>
  </p>

</div>

---

## Для кого это

> - У тебя сайт или веб-приложение на **React, Next.js, или похожем стеке**
> - Хочешь понять «а что у нас вообще под капотом» — особенно если код писали разные команды
> - Готовишься к редизайну, миграции или продаже бизнеса — нужна объективная картина
> - Видишь, что сайт тормозит, но не знаешь почему
> - Хочешь регулярно (раз в квартал) сверять health score проекта

---

## Что аудит покажет

<table>
<thead>
<tr><th>Фаза</th><th>На какой вопрос отвечает</th><th>Артефакт</th></tr>
</thead>
<tbody>
<tr><td><b>0</b> · Inventory</td><td>Что вообще лежит в проекте, какие технологии</td><td><code>01-inventory-report.md</code></td></tr>
<tr><td><b>1</b> · Architecture</td><td>Архитектура чистая или это спагетти</td><td><code>02-architecture-report.md</code></td></tr>
<tr><td><b>2</b> · Performance</td><td>Почему сайт грузится медленно (и сколько денег это стоит)</td><td><code>03-performance-report.md</code></td></tr>
<tr><td><b>3</b> · A11y + SEO</td><td>Найдут ли тебя в Google, может ли пользоваться слепой человек</td><td><code>04-accessibility-seo-report.md</code></td></tr>
<tr><td><b>4</b> · Security</td><td>Есть ли известные дыры в зависимостях и коде</td><td><code>05-security-deps-report.md</code></td></tr>
<tr><td><b>5</b> · DX & Tooling</td><td>Удобно ли разработчикам работать (текучка, скорость фич)</td><td><code>06-dx-tooling-report.md</code></td></tr>
<tr><td><b>6</b> · Roadmap</td><td><b>Что чинить в каком порядке</b> — главный артефакт</td><td><b><code>roadmap.md</code></b></td></tr>
</tbody>
</table>

---

## Быстрый старт

<details open>
<summary><b>📦 Что нужно установить (один раз)</b></summary>

```bash
# Claude Code (если ещё нет) — https://claude.com/claude-code

# Serena — навигация по коду
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant

# GitNexus — граф кода и история
npm install -g gitnexus
gitnexus setup

# Проверка
claude mcp list
# должны быть serena и gitnexus
```

</details>

<details open>
<summary><b>🚀 Запуск аудита</b></summary>

1. **Скопируй папку `frontend/`** в корень проекта, который аудируем (рядом с `package.json`)
2. **Открой Claude Code** в этой папке проекта
3. **Скопируй промпт** из `prompts/00-master-prompt.md` и вставь в чат
4. После каждой фазы агент пишет 1-2 строки статуса, ты говоришь «дальше»
5. На выходе — **`roadmap.md`** в папке `audit-pipeline/reports/`

Если хочется руководить процессом точечно — можно запускать каждую фазу отдельно через `prompts/phase-N-*.md`.

</details>

---

## Сколько это занимает

| Размер проекта | Время |
|---|---|
| Маленький лендинг (<5k LOC) | ~30 минут |
| Средний сайт (5k–30k LOC) | ~60-90 минут |
| Большое веб-приложение (30k+ LOC) | 2-3 часа |

> Прогон не блокирующий — можно делать параллельно с другими задачами, агент работает сам.

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

<table>
<tr>
<td valign="top">

**Оркестрация и навигация**
- 🧠 Claude Code — оркестрация
- 🔍 Serena (MCP) — find_symbol, references
- 📈 GitNexus (MCP) — hot spots, авторы

</td>
<td valign="top">

**Замеры и сканеры**
- 🚦 Lighthouse — Core Web Vitals
- ♿ axe-cli — accessibility
- 🔄 madge / jscpd — циклы и дубли
- 🛡 npm audit — известные уязвимости
- 💀 knip / depcheck — мёртвый код

</td>
</tr>
</table>

> Если каких-то инструментов нет — пайплайн работает в degraded режиме и помечает это в отчёте.

---

## Что получишь на выходе

```
audit-pipeline/reports/
├── 01-inventory-report.md          ← карта проекта
├── 02-architecture-report.md       ← архитектурные находки
├── 03-performance-report.md        ← замеры + узкие места
├── 04-accessibility-seo-report.md  ← WCAG + SEO находки
├── 05-security-deps-report.md     ← дыры + устаревшие пакеты
├── 06-dx-tooling-report.md         ← DX-проблемы
├── findings.json                   ← машиночитаемый список всех находок
└── roadmap.md                      ← Now / Next / Later план с DoD
```

**Roadmap** — главный артефакт. Эпики приоритизированы по формуле `(impact × confidence) / effort` с буст-множителем для hot spots.

---

## Принципы

- **Факты, не мнения.** Каждая находка с измерением или ссылкой на источник.
- **Severity по импакту, не по эстетике.**
- **Hot spots first.** Чиним там, где часто ломается (Adam Tornhill).
- **Тесты до рефакторинга.** Сначала характеризационные тесты, потом изменения (Michael Feathers).
- **Никаких преждевременных оптимизаций.** Только то, что подтверждено замерами.
- **Никаких переписываний с нуля.** Точечные fix'ы.
- **Read-only.** Пайплайн ничего не меняет в коде, только смотрит.

---

## Источники методики

<details>
<summary><b>📚 Список книг и стандартов</b></summary>

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

</details>

---

## FAQ

<details>
<summary><b>Это безопасно? Никто не утечёт мой код?</b></summary>

Аудит запускается локально на твоей машине. Claude Code работает с твоего аккаунта Anthropic — данные передаются только в API Anthropic, как при обычном использовании Claude. Если у тебя enterprise-договор с Anthropic — всё под NDA.

</details>

<details>
<summary><b>Можно запустить на закрытом проекте без интернета?</b></summary>

Нет, Claude Code требует подключения к Anthropic API. Но **никаких других внешних сервисов** пайплайн не использует — всё остальное работает локально.

</details>

<details>
<summary><b>А если у меня не Next.js, а Vue/Svelte/Angular?</b></summary>

Этот пайплайн заточен под React-стек. Для других — используй универсальный пайплайн в [`../codebase/`](../codebase) — он работает с любым языком и фреймворком.

</details>

<details>
<summary><b>Можно адаптировать под свой проект?</b></summary>

Да, это просто markdown-инструкции. Меняй пороги severity, добавляй фазы, расширяй чек-листы. Главное — не ломай формат `findings.json`, он используется фазой Roadmap для синтеза.

</details>

---

## Переаудит

Раз в квартал — повторный прогон по тем же фазам. Сравнить health score, увидеть прогресс, обновить roadmap. **Это как ТО для машины:** один раз — это снимок, регулярно — это контроль здоровья проекта.

---

<div align="center">

### Автор

**Кирилл Вечкасов** — [Telegram-канал](https://t.me/pomogay_marketing) · [vechkasov.pro](https://vechkasov.pro)

</div>
