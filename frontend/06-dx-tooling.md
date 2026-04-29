# Phase 5 — DX, Tooling & CI/CD

**Цель:** оценить инструменты разработки, процесс CI/CD, скорость обратной связи. Хороший DX = меньше багов, быстрее доставка.

**Длительность:** 1–1.5 часа.

**Опора на источники:**
- *Accelerate* (Forsgren, Humble, Kim) — четыре метрики DORA.
- *Continuous Delivery* (Humble, Farley).
- Kent C. Dodds — статьи про testing trophy.
- Matt Pocock — TypeScript best practices.

---

## Инструменты

- Чтение конфигов: `.eslintrc*`, `.prettierrc`, `tsconfig.json`, `.github/workflows/`, `.husky/`, `package.json` scripts.
- **Claude Code** — основной.
- **Serena** — поиск ESLint disable comments и других обходов.
- **GitNexus** — статистика мержей, скорость доставки.

---

## Чек-лист

### 5.1 Локальный DX

- [ ] `README.md` — есть инструкция запуска, набор скриптов задокументирован.
- [ ] `package.json scripts` — понятные имена (`dev`, `build`, `lint`, `test`, `typecheck`).
- [ ] Есть ли `dev` который реально удобен (HMR, error overlay)?
- [ ] Время холодного старта `dev` — приемлемо?
- [ ] Время `build` — приемлемо?
- [ ] Cache в build (.next/cache, .turbo, .vite/cache) — используется ли?

### 5.2 Линтинг и форматирование

- [ ] ESLint настроен. Какие плагины включены? (`react`, `react-hooks`, `import`, `jsx-a11y`, `next` если Next).
- [ ] Prettier есть, не конфликтует с ESLint (`eslint-config-prettier`).
- [ ] Stylelint для CSS (если применимо).
- [ ] Подсчитать `// eslint-disable` через Serena/grep — сколько и в каких файлах. Много — плохой знак.
- [ ] Линт прогоняется в pre-commit (через husky + lint-staged) и в CI.

### 5.3 TypeScript

- [ ] `tsconfig.json strict: true`?
- [ ] Включены: `noImplicitAny`, `strictNullChecks`, `noUncheckedIndexedAccess`, `noFallthroughCasesInSwitch`, `noImplicitReturns`?
- [ ] Path aliases (`@/components/*`) настроены?
- [ ] `tsc --noEmit` запускается в CI?
- [ ] Кол-во `any` (см. Phase 1) — повторное напоминание.

### 5.4 Тесты

- [ ] Unit тесты (Vitest/Jest) — есть, на что покрыты?
- [ ] Component тесты (Testing Library) — на ключевые компоненты?
- [ ] E2E (Playwright/Cypress) — на критические user flows (логин, оплата, основная конверсия)?
- [ ] Coverage — не самоцель, но измерять полезно. Проверить что hot spots покрыты.
- [ ] Тесты быстрые? CI прогон под 5 минут — хорошо.

### 5.5 Git workflow

- [ ] Conventional Commits? (полезно для авто-changelog)
- [ ] PR template?
- [ ] Code review обязательно перед мержем?
- [ ] Защита main/master ветки?
- [ ] Squash merge / rebase / regular merge — стратегия выбрана осознанно?

### 5.6 CI/CD

- [ ] CI настроен (GitHub Actions / GitLab CI / другое).
- [ ] Pipeline включает: lint, typecheck, test, build.
- [ ] Кэширование зависимостей и build artefacts.
- [ ] Параллелизация (jobs запускаются параллельно где возможно).
- [ ] Деплой автоматический на staging, ручной apply на prod (или PR-based).
- [ ] Preview deployments на PR (Vercel это делает из коробки).

### 5.7 Мониторинг продакшна

- [ ] Error tracking (Sentry, Bugsnag, Rollbar)?
- [ ] Source maps загружаются в Sentry для расшифровки стеков?
- [ ] Uptime monitoring?
- [ ] RUM (web vitals в проде, см. Phase 2).
- [ ] Алертинг при росте ошибок?

### 5.8 Documentation

- [ ] README покрывает: setup, scripts, deployment, contribution.
- [ ] Storybook — есть, покрывает основные компоненты?
- [ ] ADR (Architecture Decision Records) — для важных решений.
- [ ] Component documentation (props, examples) — JSDoc или MDX в Storybook.

### 5.9 Onboarding

- [ ] Новый разработчик может запустить проект за <30 минут? (от clone до running локально)
- [ ] Тест: один из шагов в README сейчас провалится? (проверить актуальность)

### 5.10 DORA-метрики (через GitNexus)

- [ ] Deployment Frequency — сколько релизов в неделю/месяц?
- [ ] Lead Time for Changes — медиана от commit до prod.
- [ ] Change Failure Rate — % релизов с откатами/хотфиксами (по тегам/коммит-мессаджам).
- [ ] Mean Time to Recovery — для случившихся факапов.

Если данных нет — отметить и предложить как трекать.

---

## Шаблон отчёта `reports/06-dx-tooling-report.md`

```markdown
# DX, Tooling & CI/CD Report

## Local DX
- Cold dev start: ~6s ✓
- Cold prod build: ~85s ✓
- README setup steps: works (verified)

## Lint & format
- ESLint: configured, plugins: [react, react-hooks, jsx-a11y, next]
- Prettier: configured, no conflicts
- eslint-disable count: 47 (top file: src/legacy/old-cart.tsx with 12)
- Pre-commit: husky + lint-staged ✓

## TypeScript
- strict: true ✓
- noUncheckedIndexedAccess: false → DX-001 medium
- any count: 89 (см. Phase 1)
- tsc in CI: yes

## Tests
- Vitest: 124 unit tests, coverage 38%
- Playwright: 6 E2E tests (login, checkout)
- Hot spots coverage:
  - ProductCard.tsx (hot, 47 commits): 0% → DX-002 high
  - cart/api.ts: 0% → DX-003 high

## CI
- GitHub Actions: lint + typecheck + build (no tests in CI) → DX-004 high
- Cache: yes (npm)
- Parallel jobs: no (sequential)
- Average run: 4m 20s

## Monitoring
- Sentry: ❌ not connected → DX-005 high
- RUM: ❌ → DX-006 medium (см. Phase 2)
- Uptime: Vercel dashboard only

## Documentation
- README: ok
- Storybook: ❌
- ADR: ❌

## DORA (last 90 days, via GitNexus)
- Deployment frequency: ~2/week
- Lead time (PR opened → merged): median 2.1 days
- Hotfix commits (containing "fix" or "hotfix" in main): 8 (≈12% of 67 PR)

## Findings
[в findings.json]
```

---

## Промпт для Claude Code

```
Phase 5 — DX, Tooling, CI/CD.

План:
1. Прочитай конфиги: package.json (scripts, deps), tsconfig.json, .eslintrc, .prettierrc, .github/workflows/*, .husky/.
2. Через Serena посчитай // eslint-disable, @ts-ignore, any.
3. Если есть тесты — оцени покрытие, особенно hot spots из Phase 0/1.
4. Проверь CI pipeline — что именно запускается, есть ли тесты, кэш, параллелизация.
5. Через GitNexus собери DORA-метрики за последние 90 дней:
   - кол-во мержей в main
   - медианное время от первого коммита PR до мержа (если можно)
   - коммиты с "fix", "hotfix", "revert" в main
6. Заполни reports/06-dx-tooling-report.md.
7. Допиши findings.json.

Замечания:
- DX-проблемы часто причина других проблем. Например: нет тестов → много багов. Нет Sentry → не знаем про реальные ошибки.
- В findings указывай связь: "DX-002 связана с ARCH-005 — без тестов нельзя безопасно рефакторить hot spot".
```
