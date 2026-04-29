# Phase 4 — Security & Dependencies prompt

```
Phase 4 — Security & Dependencies (audit-pipeline/05-security-deps.md).

Задачи:
1. npm audit --production и полный. Зафиксируй critical/high/moderate/low.
2. depcheck — неиспользуемые зависимости.
3. npm-check-updates — устаревшие. Major version отставания — отдельно.
4. license-checker --summary — несовместимые лицензии.
5. Через Serena найди:
   - все dangerouslySetInnerHTML — для каждого: статический контент или user input? Санитизация?
   - eval, new Function, innerHTML
   - все process.env.* — какие используются, какие public (NEXT_PUBLIC_), какие должны быть public но не помечены, какие случайно public
6. Через GitNexus:
   - история .env, .npmrc, config-файлов — был ли когда-то секрет в коммите
   - если был — это серьёзно, секрет считаем скомпрометированным даже если потом удалили
7. Если сайт деплойнут — curl -I по основным URL, проверь заголовки: CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy.
8. Проверь .gitignore — .env*, .DS_Store, build выходы, IDE-конфиги.
9. Auth (если применимо):
   - где хранятся токены: localStorage, sessionStorage, cookies? httpOnly?
   - есть refresh rotation?
10. Заполни reports/05-security-deps-report.md.
11. Допиши findings.json. ID prefix SEC-NNN.

Severity:
- critical: эксплуатируемые уязвимости в проде, секрет в коде/истории, XSS на user input, JWT в localStorage если есть оно
- high: known CVE high без патча, missing CSP, dangerouslySetInnerHTML без санитизации даже на доверенном контенте
- medium: устаревшие пакеты с патчами, missing Permissions-Policy, missing Referrer-Policy
- low: гигиена, dev-only deps уязвимости

Правила:
- Не паникуй из-за npm audit ложноположительных в dev. Уточни exploitability.
- Для каждой уязвимости — fix план: bump до версии X, или замена пакета.
- При выявлении секрета в истории — рекомендация: ротировать секрет (даже если он удалён из кода) + рассмотреть git filter-repo / BFG, но это решение продакта.
```
