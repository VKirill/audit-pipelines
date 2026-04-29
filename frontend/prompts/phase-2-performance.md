# Phase 2 — Performance prompt

```
Phase 2 — Performance & CWV (audit-pipeline/03-performance.md).

Задачи:
1. Спроси прежде чем устанавливать: lighthouse (если нет), @next/bundle-analyzer (если Next).
2. Lighthouse прогон по топ-5 маршрутам из inventory (mobile + desktop, slow 4G). Зафиксируй LCP, INP, CLS, FCP, TBT, TTFB, Performance score.
3. Bundle analysis:
   - для Next: ANALYZE=true npm run build (или эквивалент), парсь вывод
   - для других: source-map-explorer
   Топ-10 тяжёлых модулей. Найди подозреваемых: moment, lodash без tree-shake, полные иконпаки.
4. Через Serena найди:
   - все import 'moment'
   - все import * from 'lodash' (не lodash-es или modular)
   - все <img> теги (не next/image, не Image)
   - все <script> теги (не next/script)
   - все 'use client' директивы — какие компоненты ими помечены
5. Если RUM есть — попроси у меня дамп или доступ. Если нет — это finding "no RUM in production".
6. Для каждой проблемы оцени экономию ("сэкономит ~Xms LCP" или "~YKB бандла").
7. Заполни reports/03-performance-report.md.
8. Допиши findings.json. ID prefix PERF-NNN.

Правила:
- Только то что подтверждается измерениями. Никаких "тут возможно медленно".
- Severity: LCP >4s p75 = critical, бандл >300KB на главной = high, missing next/image для LCP = high.
- Ссылайся на web.dev и docs (Next.js, React).
```
