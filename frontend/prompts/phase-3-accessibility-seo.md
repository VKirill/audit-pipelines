# Phase 3 — A11y & SEO prompt

```
Phase 3 — Accessibility & SEO (audit-pipeline/04-accessibility-seo.md).

Задачи:

A11y:
1. Установи (с моего разрешения): @axe-core/cli или axe-playwright.
2. Прогони axe по топ-5 маршрутам. Собери violations по категориям severity.
3. Lighthouse a11y category по тем же маршрутам.
4. Через Serena найди потенциальные проблемы:
   - все role="..." и aria-* атрибуты — где, корректно ли по WAI-ARIA APG
   - компоненты с onClick на не-button/a (потенциально клавиатурно недоступные)
   - все <img> без alt
   - все формы — связь label-input через for/id или обёртку
   - все outline: none и outline-none без замены focus-visible
5. Список кастомных виджетов которые легко сделать недоступными: модалки, дропдауны, табы, аккордеоны, тултипы. Для каждого через Serena подними реализацию, проверь по APG pattern.

SEO:
6. Через Serena найди использование next/head или generateMetadata по всем страницам/маршрутам — title, description, canonical, og:* выставлены?
7. Проверь robots.txt, sitemap.xml (или next-sitemap конфиг).
8. Проверь view-source ключевых страниц — виден ли контент в HTML или только div#root?
9. Проверь Schema.org JSON-LD — где есть, где должно быть.
10. URL структура — читаемые, нет случайных параметров?

11. Заполни reports/04-accessibility-seo-report.md.
12. Допиши findings.json. ID prefix A11Y-NNN и SEO-NNN.

Правила:
- A11y severity по WCAG: уровень A нарушение = high+, AA = medium+, AAA = low.
- SEO severity по импакту на индексацию.
- Каждая находка с ссылкой на WCAG criterion / WAI-ARIA APG / Google Search Central.
- Если что-то требует ручной проверки скринридером — отметь, я проверю сам.
```
