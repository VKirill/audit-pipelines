# Phase 3 — Accessibility & SEO

**Цель:** проверить что сайт доступен с клавиатуры, скринридерами, и индексируется поисковиками. A11y и SEO часто пересекаются — семантический HTML работает на оба.

**Длительность:** 2–3 часа.

**Опора на источники:**
- W3C WAI-ARIA Authoring Practices Guide (APG).
- WCAG 2.2 (целимся в AA как минимум).
- Heydon Pickering, *Inclusive Components* и *Inclusive Design Patterns*.
- Adrian Roselli, серия статей про доступность.
- Web.dev Accessibility и SEO гайды.
- Google Search Central (ex Webmaster).
- Yandex Webmaster (если работаешь с RU-рынком — релевантно).

---

## Инструменты

- **axe-core** через `@axe-core/cli` или `axe-playwright` — автоматические проверки.
- **Lighthouse** — accessibility и SEO score.
- **Pa11y CI** — batch по маршрутам.
- **WAVE** browser extension — для ручной проверки.
- **NVDA / VoiceOver** — реальное использование скринридером (хотя бы по ключевым флоу).
- **Клавиатура** — пройти основные сценарии без мыши.
- **Screaming Frog** или `next-sitemap` audit — для SEO-обхода.
- **Google Search Console** + **Yandex Webmaster** — реальные данные индексации.
- **Serena** — поиск компонентов которые могут быть проблемными (кастомные модалки, дропдауны, табы — частые источники a11y-проблем).
- **Claude Code** — оркестрация.

---

## Часть A: Accessibility

### 3A.1 Автоматические проверки

- [ ] axe-core по всем маршрутам — собрать violations по категориям.
- [ ] Lighthouse a11y score по топ-5 маршрутам.
- [ ] Pa11y CI с конфигом (опционально для регулярных прогонов).

Помни: автоматика ловит ~30% проблем. Остальное — ручной аудит.

### 3A.2 Семантический HTML

- [ ] Один `<h1>` на страницу, иерархия заголовков без пропусков (h1 → h2 → h3).
- [ ] Лендмарки: `<header>`, `<nav>`, `<main>`, `<footer>`. Не дублируются.
- [ ] Списки оформлены как `<ul>/<ol>`, а не divs.
- [ ] Кнопки — это `<button>`, ссылки — это `<a href>`. Не наоборот.
- [ ] Формы: `<label>` связан с input через `for`/`id` или обёрткой.

### 3A.3 Клавиатурная навигация

Пройти по ключевым флоу (логин, корзина, форма заявки) только Tab/Shift+Tab/Enter/Space/Esc:

- [ ] Все интерактивные элементы достижимы.
- [ ] Tab order логичный (соответствует визуальному).
- [ ] Видимый focus ring на всех элементах. Не убирать `outline: none` без замены.
- [ ] Esc закрывает модалки, выпадайки.
- [ ] Skip link "к основному контенту" в начале страницы.
- [ ] Нет focus traps (где фокус застревает) кроме как в открытых модалках (там нужен trap).

### 3A.4 ARIA

ARIA — это последнее средство. Лучший ARIA — это никакой ARIA, если можно использовать нативный элемент.

- [ ] `role="button"` на div вместо `<button>` — антипаттерн.
- [ ] Кастомные виджеты (комбобокс, табы, дровер) — соответствуют WAI-ARIA APG?
- [ ] `aria-label` / `aria-labelledby` там где нужен текстовый ярлык.
- [ ] `aria-live` для динамических обновлений (тосты, ошибки форм).
- [ ] Не злоупотребляются `aria-hidden`.

### 3A.5 Изображения и медиа

- [ ] У каждой `<img>` есть `alt`. Декоративные — `alt=""`.
- [ ] Иконки-кнопки имеют `aria-label` или скрытый текст.
- [ ] Видео — субтитры, транскрипты.
- [ ] Аудио — транскрипты.

### 3A.6 Контраст и цвет

- [ ] Контраст текста ≥ 4.5:1 (обычный) и 3:1 (крупный).
- [ ] Контраст UI-элементов и focus ring ≥ 3:1.
- [ ] Информация не передаётся только цветом (ошибка формы — не только красная рамка, но и текст/иконка).

### 3A.7 Формы

- [ ] Поля связаны с лейблами.
- [ ] Ошибки валидации связаны с полем (`aria-describedby`, `aria-invalid`).
- [ ] Нативные типы input (email, tel, date) используются — даёт правильную клавиатуру и автозаполнение.
- [ ] Подсказки и автозаполнение (`autocomplete` атрибуты).

### 3A.8 Motion и preferences

- [ ] `prefers-reduced-motion` — анимации уменьшаются?
- [ ] Параллакс, авто-карусели — отключаются по prefers-reduced-motion?
- [ ] Нет flashing content (>3 раз/сек).

### 3A.9 Локализация и язык

- [ ] `<html lang="ru">` (или соответствующий) выставлен.
- [ ] Переключение языка — `lang` атрибут на блоках на других языках.
- [ ] Направление текста (`dir`) если поддерживается RTL.

---

## Часть B: SEO

### 3B.1 Базовые мета-теги

- [ ] Уникальный `<title>` на каждой странице, 50–60 символов.
- [ ] `<meta name="description">` уникальный, 140–160 символов.
- [ ] Canonical URL на каждой странице.
- [ ] OpenGraph (og:title, og:description, og:image, og:url) — для соцсетей.
- [ ] Twitter Card.
- [ ] Favicon, apple-touch-icon.

### 3B.2 Контентная семантика

- [ ] Заголовки h1–h6 структурированы (см. a11y).
- [ ] Микроразметка Schema.org (JSON-LD) — для типа контента (Article, Product, Recipe, Organization).
- [ ] Breadcrumbs — визуальные + микроразметка BreadcrumbList.

### 3B.3 Индексация

- [ ] `robots.txt` — корректный, не блокирует то что должно индексироваться.
- [ ] `sitemap.xml` — генерируется автоматически (next-sitemap или аналог)? Актуален?
- [ ] `<meta name="robots">` — нет ли случайных `noindex` на индексируемых страницах?
- [ ] Внутренние ссылки — реальные `<a href>`, не JS-обработчики.
- [ ] Дубли страниц (с/без слеша, с/без www, http/https) → 301-редиректы или canonical.

### 3B.4 Производительность для SEO

- [ ] Core Web Vitals (см. Phase 2) — это и SEO-фактор.
- [ ] Mobile-friendly (mobile-friendly test).
- [ ] Контент не за JavaScript — для статичных страниц рендер должен быть SSR/SSG, чтобы краулер видел текст без JS.

### 3B.5 SSR / Pre-render проверка

- [ ] Открыть `view-source:` страницы — виден ли весь основной контент в HTML?
- [ ] Если SPA-only — серьёзная находка.
- [ ] Hydration errors? (видны в console на проде)

### 3B.6 Поисковые консоли

- [ ] Google Search Console — есть ли ошибки индексации, какие страницы не индексируются.
- [ ] Yandex Webmaster (если RU) — то же.
- [ ] Покрытие, Core Web Vitals по реальным данным.

### 3B.7 Структура URL

- [ ] URL читаемые, на латинице (для RU — транслит, не русские буквы в URL).
- [ ] Без избыточных параметров.
- [ ] Стабильные (не меняются часто без редиректов).

### 3B.8 Внутренняя перелинковка

- [ ] Главная → разделы → страницы — есть путь в 3 клика?
- [ ] Связанные материалы (related posts) — есть?
- [ ] Якорные тексты осмысленные ("читать про X"), а не "тут".

---

## Шаблон отчёта `reports/04-accessibility-seo-report.md`

```markdown
# Accessibility & SEO Report

## A11y summary
- Lighthouse a11y avg: 87/100
- axe violations total: 42 (across 5 routes)
  - critical: 3 (missing alt, contrast, button name)
  - serious: 12
  - moderate: 18
  - minor: 9

## A11y findings (примеры)

### A11Y-001 (critical) — Missing alt on hero images
- 6 страниц, 8 изображений
- File: src/components/Hero.tsx
- Fix: добавить alt описывающий смысл, или alt="" если декоративная.
- Reference: WCAG 2.2, 1.1.1 Non-text Content

### A11Y-002 (high) — Custom dropdown без поддержки клавиатуры
- File: src/components/Dropdown.tsx
- Reproduce: Tab подводит фокус, но Enter не открывает, стрелки не работают.
- Fix: реализовать по WAI-ARIA Combobox pattern или заменить на Radix UI / Headless UI.
- Reference: WAI-ARIA APG Combobox

[...]

## SEO summary
- Все страницы имеют уникальный title: yes/no
- Описание (meta description) уникальное: % страниц
- Canonical: yes/no
- Sitemap: yes/no, актуальность
- Schema.org: какие типы используются
- Поисковые консоли подключены: yes/no

## SEO findings

### SEO-001 (high) — Контент главной за JavaScript
- Файл: pages/index.tsx (полностью CSR)
- Evidence: view-source показывает только div#root
- Impact: критично для индексации, особенно Yandex
- Fix: перевести на SSG (getStaticProps) или App Router server component
- Effort: M

[...]

## Findings (в findings.json)
```

---

## Промпт для Claude Code

```
Phase 3 — A11y и SEO.

План:
1. Установи (с моего разрешения): @axe-core/cli или axe-playwright.
2. Прогони axe по топ-5 маршрутам, собери violations по severity.
3. Прогони lighthouse a11y и SEO category. Сравни.
4. Через Serena найди потенциально проблемные кастомные виджеты:
   - найди все role="..." и aria-* атрибуты — где используются и корректно ли
   - найди компоненты с onClick на не-button/не-a (потенциальные клавиатурные баги)
   - найди все <img> без alt
   - найди все формы и проверь связь label-input
5. Для SEO:
   - проверь next/head или generateMetadata по всем страницам — title, description, canonical, og
   - проверь наличие robots.txt и sitemap
   - проверь view-source ключевых страниц на наличие контента в HTML
6. Заполни reports/04-accessibility-seo-report.md.
7. Допиши findings.json.

Замечания:
- Severity по WCAG levels: A нарушение = high+, AA = medium+, AAA = low.
- Для каждой находки — ссылка на WCAG critery или WAI-ARIA APG.
- Если нашёл что-то требующее ручной проверки скринридером — отметь это, я проверю сам.
```
