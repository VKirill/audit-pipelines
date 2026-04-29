# Phase 5 — DX, Tooling, CI/CD prompt

```
Phase 5 — DX, Tooling, CI/CD (audit-pipeline/06-dx-tooling.md).

Задачи:
1. Прочитай конфиги: package.json (scripts, deps), tsconfig.json, .eslintrc*, .prettierrc*, .stylelintrc*, .github/workflows/*, .gitlab-ci.yml, .husky/, lint-staged.config.*.
2. Проверь README — есть ли инструкция запуска, актуальна ли. Попробуй мысленно пройти setup-шаги.
3. ESLint:
   - какие плагины
   - правила: complexity, max-lines, max-depth включены?
   - eslint-plugin-jsx-a11y подключён?
4. Через Serena/grep посчитай:
   - // eslint-disable (всех видов)
   - @ts-ignore, @ts-expect-error
   - any (с учётом валидных случаев)
   Топ-10 файлов по количеству этих пометок.
5. TypeScript: strict, noUncheckedIndexedAccess, noImplicitAny — что включено.
6. Тесты:
   - какие фреймворки (Vitest, Jest, Playwright, Cypress)
   - coverage если есть данные
   - покрытие hot spots (Phase 0/1) — критично
7. CI pipeline:
   - что запускается (lint, typecheck, test, build)
   - время прогона
   - кэширование, параллелизация
   - тесты в CI или нет
8. Monitoring:
   - Sentry / Bugsnag / Rollbar в проде?
   - source maps загружаются?
   - RUM (см. Phase 2)
   - uptime monitoring
   - alerting
9. Storybook, ADR, документация компонентов — есть/нет.
10. Через GitNexus собери DORA-метрики за последние 90 дней:
    - частота релизов (мержи в main)
    - lead time (PR opened → merged), если можно вытащить
    - hotfix-коммиты в main (по сообщению "fix"/"hotfix"/"revert")
11. Заполни reports/06-dx-tooling-report.md.
12. Допиши findings.json. ID prefix DX-NNN.

Правила:
- DX-проблемы часто причина других проблем. Указывай связи: "DX-002 (нет тестов hot spots) блокирует ARCH-005 (рефакторинг cart/)".
- Severity по импакту на скорость и безопасность доставки.
```
