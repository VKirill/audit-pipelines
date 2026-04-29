# Phase 2 — Performance & Core Web Vitals

**Цель:** замерить производительность, найти узкие места, дать конкретные fix'ы. Опираемся на измерения, а не на догадки.

**Длительность:** 2–3 часа.

**Опора на источники:**
- Ilya Grigorik, *High Performance Browser Networking*.
- Steve Souders, *High Performance Web Sites* + *Even Faster Web Sites*.
- Jeremy Wagner, *Web Performance in Action*.
- Web.dev (Google) — гайды по Core Web Vitals, INP, LCP.
- Next.js Performance documentation.
- Addy Osmani — статьи по оптимизации React и изображений.

---

## Метрики которые меряем

| Метрика | Цель (good) | Цель (poor) |
|---|---|---|
| LCP (Largest Contentful Paint) | <2.5s | >4s |
| INP (Interaction to Next Paint) | <200ms | >500ms |
| CLS (Cumulative Layout Shift) | <0.1 | >0.25 |
| FCP | <1.8s | >3s |
| TTFB | <0.8s | >1.8s |
| TBT (lab) | <200ms | >600ms |

Плюс bundle size:
- Initial JS (parsed) — таргет <170KB на main route.
- CSS critical path — <50KB.

---

## Инструменты

- **Lighthouse CI** — лабораторные замеры, batch по всем маршрутам.
- **WebPageTest** или **PageSpeed Insights** — реальные условия, разные локации.
- **Chrome DevTools Performance + Coverage** — для глубокого анализа конкретной страницы.
- **Next.js Bundle Analyzer** (`@next/bundle-analyzer`) — что в JS бандле.
- **source-map-explorer** — альтернатива, для не-Next проектов.
- **react-scan** или **why-did-you-render** — лишние ререндеры.
- **Real User Monitoring** — если есть (GA4 web vitals, Vercel Analytics, SpeedCurve).
- **Claude Code** — оркестрация и анализ.
- **Serena** — для точечного поиска проблемных компонентов в коде.
- **GitNexus** — соотнести регрессии производительности с коммитами (если RUM показывает деградацию — найти когда началось).

---

## Чек-лист

### 2.1 Базовые лабораторные замеры

- [ ] Lighthouse прогон на Production по топ-5 маршрутам (dekstop + mobile).
- [ ] Зафиксировать: Performance score, LCP, INP, CLS, FCP, TBT, TTFB.
- [ ] Сравнить с целями. Какие маршруты в красной зоне?

### 2.2 Реальные пользователи (RUM)

- [ ] Если есть RUM — выгрузить медианы и p75 по CWV за последние 28 дней.
- [ ] Сегментация по устройству (mobile/desktop) и стране.
- [ ] Если RUM нет — критичная находка, добавить в roadmap.

### 2.3 Bundle analysis

Next.js:
- [ ] `next build` с `ANALYZE=true` (через @next/bundle-analyzer).
- [ ] Зафиксировать размер: каждой страницы (First Load JS), shared chunks, отдельных chunks.
- [ ] Найти библиотеки занимающие много веса (moment, lodash, большие иконпаки).

Не-Next:
- [ ] `source-map-explorer build/static/js/*.js`.

Подозреваемые:
- [ ] `moment` — заменить на `date-fns` или `dayjs`.
- [ ] `lodash` целиком — переключить на `lodash-es` с tree shaking, или нативные методы.
- [ ] Полные иконпаки (`@mui/icons-material`, `react-icons` без modular imports) — импортировать только то что нужно.
- [ ] Дублирующиеся библиотеки разных версий (`npm ls <pkg>`).

### 2.4 Изображения

- [ ] Используется ли `next/image` (для Next) или нативный `loading="lazy"` + `srcset` (для других)?
- [ ] Изображения отдаются в современных форматах (AVIF/WebP)?
- [ ] LCP-картинка — `priority` (Next) или предзагружена через `<link rel="preload">`?
- [ ] Размеры заданы (width/height или CSS aspect-ratio) — иначе CLS.
- [ ] Hero-изображения не превышают разумных размеров (>1MB на десктопе — это плохо).

### 2.5 Шрифты

- [ ] Self-hosted или с Google Fonts напрямую? (self-hosted быстрее)
- [ ] `next/font` или эквивалент — есть ли `font-display: swap`?
- [ ] Preload критичных шрифтов?
- [ ] Subsetting для языка (для русского — кириллический сабсет, не весь латиница+кириллица+экзотика)?
- [ ] Variable fonts вместо нескольких файлов разной плотности?

### 2.6 Сторонние скрипты

- [ ] Список всех `<script>` тегов — что и зачем.
- [ ] Аналитика, GTM, рекламные скрипты — загружаются ли через `next/script` со стратегией (afterInteractive/lazyOnload)?
- [ ] Виджеты чатов, попапы — на каждой ли странице нужны?
- [ ] iframe'ы (YouTube, карты) — lazy load? Facade pattern?

### 2.7 CSS

- [ ] Размер CSS на критическом пути.
- [ ] Coverage в DevTools — сколько % CSS не используется на конкретной странице?
- [ ] Глобальные стили против CSS Modules / Tailwind purge.
- [ ] Анимации на `transform` и `opacity` (composited) или на `top/left/width` (force layout)?
- [ ] `will-change` не злоупотреблено?

### 2.8 JavaScript runtime

- [ ] Длинные таски (>50ms) на загрузке — Performance tab → Bottom-up.
- [ ] React профайлер — компоненты с долгим рендером.
- [ ] Лишние ререндеры — react-scan на ключевых страницах. Подозреваемые: пропсы-объекты создаваемые в рендере, не-мемоизированные коллбэки в больших списках.
- [ ] Виртуализация длинных списков (react-window, tanstack-virtual)? Где списки >100 элементов без виртуализации — флажок.

### 2.9 Server / SSR / Streaming (для Next.js)

- [ ] Какие страницы SSG, какие SSR, какие ISR — соответствует ли смыслу?
- [ ] Server Components используются адекватно (App Router) — или всё в `'use client'`?
- [ ] Suspense boundaries для streaming — есть ли?
- [ ] `fetch` cache strategies — тэги, revalidate указаны осознанно?
- [ ] Edge runtime vs Node runtime — где это даёт смысл?

### 2.10 Сеть

- [ ] HTTP/2 или HTTP/3 включён?
- [ ] Brotli compression?
- [ ] Cache-Control для статики (год + immutable для хешированных ассетов)?
- [ ] Resource hints — preconnect, dns-prefetch, preload — используются осмысленно (не на всё подряд)?

### 2.11 INP конкретно

INP — самая частая проблема в 2025-2026.

- [ ] Найти longest interactions через DevTools / RUM.
- [ ] Тяжёлые обработчики кликов (валидация, сортировка списка, синхронные вычисления) — переместить в `requestIdleCallback`, `useTransition`, или offload в Web Worker.
- [ ] Большие state-апдейты которые синхронно ререндерят полстраницы — `useTransition` или дебаунс.

---

## Шаблон отчёта `reports/03-performance-report.md`

```markdown
# Performance & CWV Report

## Lab metrics (Lighthouse, mobile, slow 4G simulation)

| Route | Perf | LCP | INP | CLS | TBT |
|---|---|---|---|---|---|
| / | 78 | 3.1s | 240ms | 0.05 | 320ms |
| /blog | 65 | 4.2s | 180ms | 0.18 | 480ms |
| ...

Красные зоны: ...

## RUM (last 28 days, p75)
[если есть, иначе finding "no RUM"]

## Bundle
First Load JS shared by all: 234 KB (gzipped)
Top routes by initial JS:
- / : 312 KB
- /blog/[slug] : 287 KB

Top dependencies by weight:
1. moment.js — 76 KB → заменить на dayjs (8 KB), сэкономим ~68 KB
2. @mui/icons-material (полный пак) — 120 KB → modular imports, сэкономим ~110 KB
3. ...

## Images
- LCP image на / — не priority, теряем ~600ms
- 14 изображений без width/height → CLS 0.18 на /blog
- 6 PNG hero-изображений >800KB → AVIF/WebP сэкономит ~70%

## Fonts
- Используется Google Fonts <link>, без preconnect → +180ms TTFB на критическом пути
- 4 веса шрифта подгружаются, реально нужны 2

## Scripts
- Yandex Metrica загружается синхронно в <head> → блокирует main thread на 90ms
- Чат-виджет грузится на каждой странице, нужен только на /contact

## CSS
- Глобальный bundle.css 142 KB, на главной используется 18% → unused CSS
- Анимация на .menu использует left/top → переписать на transform

## JS runtime
- ProductList: 320 ререндеров за пользовательскую сессию из-за inline-обработчика
- Корзина: тяжёлая валидация в onChange → переместить в useDeferredValue

## SSR/Streaming
- Все компоненты в pages/blog/[slug] обёрнуты 'use client', хотя это статика → перевести на Server Components
- Нет Suspense boundary вокруг блока комментариев → блокирует TTFB

## Findings
[в findings.json]
```

---

## Промпт для Claude Code

```
Phase 2 — Performance.

План:
1. Установи зависимости (с моего разрешения): @next/bundle-analyzer (если Next), lighthouse, webpagetest cli (опционально).
2. Прогоните lighthouse по топ-5 маршрутам из inventory. Соберите метрики в таблицу.
3. Bundle analysis: запусти ANALYZE=true npm run build (или эквивалент). Парси вывод, выдели топ-10 тяжёлых модулей.
4. Через Serena найди:
   - все import из 'moment', 'lodash' (не lodash-es), 'date-fns' с глобальными импортами
   - все <img> теги (не next/image) и проверь размеры
   - все <script> теги и проверь стратегию загрузки
   - все use client директивы — какие компоненты они оборачивают
5. Если есть RUM — попроси у меня доступ или дамп.
6. Заполни reports/03-performance-report.md.
7. Допиши находки в findings.json. Severity по импакту: LCP >4s = critical, бандл >300KB на главной = high, отсутствующий next/image для LCP = high, и т.д.

Замечания:
- Не предлагай преждевременные оптимизации. Только то что подтверждается замерами.
- Для каждого fix'а оцени экономию: "сэкономит ~Xms LCP" или "~Y KB бандла".
- Сошлись на источники (web.dev, Next.js docs).
```
