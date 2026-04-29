# PHASE 02b — TRUST MAP (Sources → Sinks → Trust)

**Цель:** Построить карту потоков недоверенных данных по проекту. Это снимает с фаз 06/06b/09 повторяющуюся работу: вместо россыпи отдельных проверок (SQLi/SSRF/IDOR/XSS/path traversal) — одна таблица «откуда приходит данные → где валидируются → куда уходят». В результате почти все injection-class уязвимости видны в одной строке.

**Когда запускать:** после `phase_02_architecture.md`. Если в проекте нет HTTP-сервера / event consumer'ов / CLI-входов с user input — пропусти и зафиксируй в `audit/02b_trust_map.md` секцией «Не применимо: сервис без внешних входов».

**Источники методики:**
- OWASP Application Security Verification Standard (ASVS) §V5 (Validation, Sanitization, Encoding).
- Threat Modeling: Designing for Security — Adam Shostack (data flow diagrams).
- Saltzer & Schroeder (1975), §3 — Principle of Complete Mediation.

**Exit gate этой фазы:**
- `bash audit_pipeline/scripts/validate_phase.sh 02b` возвращает 0;
- ≥ 5 findings (для M-проекта);
- evidence: `trust_map.md` + `sources_sinks.md` (≥ 2 файла);
- ≥ 80% строк таблицы trust map имеют `validator` ≠ `none` ИЛИ `risk` явно поставлен.

---

## 1. Входы

- `evidence/01_inventory/...` — полный список HTTP-роутов, очередей, CLI-команд.
- Phase 02 — карта кластеров и центральных символов (особенно `CALLS` к `pg.query`, `fetch`, `axios`, `fs.readFile`).
- Phase 06 OWASP-чек-лист — параллельно может быть уже начат.

---

## 2. Чек-лист действий

### 2.1. Перечислить все sources (точки входа недоверенных данных)

```bash
# HTTP handlers (Node/TS пример)
rg -l "defineEventHandler|fastify\\.(get|post|put|delete|patch)|app\\.(get|post|put|delete|patch)|router\\.(get|post|put|delete)" \
  --type ts --type js | sort -u > audit/evidence/02b_trust_map/_handlers.txt

# Python (FastAPI/Django/Flask)
rg -l "@app\\.(get|post|put|delete)|@router\\.(get|post)|class .*\\((View|APIView)|@require_http_methods" \
  --type py | sort -u >> audit/evidence/02b_trust_map/_handlers.txt

# Очереди/события
rg -l "@(Subscribe|Consumer|EventHandler)|new Worker\\(|queue\\.process|kafka.*consume|consumeMessage" \
  --type ts --type js --type py | sort -u >> audit/evidence/02b_trust_map/_handlers.txt

# Webhook receivers
rg -l "webhook|callback" --type ts --type js --type py | sort -u
```

### 2.2. Перечислить все sinks (точки куда данные уходят)

| Sink-тип | Что грепать | Чем опасно |
|----------|-------------|-----------|
| SQL | `query(`, `queryOne(`, `Knex.raw`, `db.execute`, `pg.query`, `sequelize.query`, `.raw(` | SQLi |
| Shell | `child_process.exec`, `shell:true`, `os.system`, `subprocess.*shell=True`, `Runtime.exec` | command injection |
| HTTP outbound | `fetch(`, `axios.`, `requests.get/post`, `urllib.request`, `http.Get` | SSRF |
| Filesystem | `fs.readFile`, `fs.writeFile`, `open(`, `pathlib.Path(...).read_text()` | path traversal |
| Render | `v-html`, `dangerouslySetInnerHTML`, `innerHTML =`, `{!! $var !!}`, `Mark.safe(` | XSS |
| Template | `render_template_string`, `Jinja2.Template`, `eval(`, `new Function(`, `Function(` | template/code injection |
| Deserialization | `pickle.loads`, `yaml.load(` (без SafeLoader), `JSON.parse` user input в нестрогом контексте | RCE/prototype pollution |
| Auth/Session | `setCookie`, `jwt.sign`, `crypto.createHash`, `bcrypt`, `signSession` | weak crypto / session fixation |

### 2.3. Построить таблицу `trust_map.md`

Для каждой пары (source, sink) — одна строка:

```markdown
| Source | Untrusted? | Validator | Sink | Validator-to-Sink | Risk | Finding |
|--------|-----------|-----------|------|-------------------|------|---------|
| POST /api/cabinet/profiles/[id] body.name | yes | — | UPDATE user_profiles SET name=$1 WHERE id=$id | parameterized $1 (✅) but no ownership check | **IDOR** | F-0034 |
| POST /api/feed/[id]/like body.user_id | yes | — | INSERT into likes (user_id, …) | none | spoofing | F-0035 |
| POST /api/admin/upload-url body.url | admin | admin-auth | fetch(body.url) | no host allow-list | **SSRF** | F-0038 |
| GET /api/catalog/[slug] | yes | zod schema | SELECT * FROM catalog WHERE slug=$1 | parameterized | clean | — |
```

Колонки:
- **Source** — точка входа: HTTP-роут + поле, или event topic + поле.
- **Untrusted?** — `yes`/`admin`/`no` (anonymous/authenticated/admin).
- **Validator** — где проверяется/санитизируется на входе (zod/Pydantic/Joi/manual). `—` если нет.
- **Sink** — конкретный SQL/fetch/exec/render с цитатой строки.
- **Validator-to-Sink** — что между sources и sink: parameterized? sanitize? whitelist?
- **Risk** — `clean` / `IDOR` / `SQLi` / `SSRF` / `XSS` / `command-injection` / `RCE` / …
- **Finding** — `F-NNNN` если выписан в `findings.jsonl`. Если risk ≠ clean но finding нет — заведи.

### 2.4. Sources&Sinks reference (`sources_sinks.md`)

Параллельный документ — справочник:

```markdown
## Sources (N total)

### HTTP routes
- `POST /api/cabinet/profiles/[id]` — apps/web/server/api/cabinet/profiles/[id].put.ts:17
- `POST /api/feed/[id]/like` — apps/web/server/api/feed/[id]/like.post.ts:9
- ... (полный список из _handlers.txt)

### Queue consumers
- BullMQ `photoshoot` — apps/bot/src/shared/lib/queue/...

## Sinks (N total)

### SQL
- queryOne / pg.query in 80 files; topla:
  - apps/web/server/utils/db.ts:52 (queryOne wrapper)
  - apps/bot/src/entities/user/api/user-queries.ts (17 atomic queries)
- Sequelize/Prisma raw — none/N (grep `.raw(`)

### HTTP outbound
- fetch in 22 places (см. evidence/05_error_handling/external_calls_timeouts.md)
- axios.{get,post,put,delete} — N

### Filesystem write
- fs.writeFile/createWriteStream — N
```

### 2.5. Highlight: Complete Mediation

Saltzer & Schroeder: каждый доступ к ресурсу должен проходить через одну точку проверки. В таблице это значит: **для каждой группы routes** должен быть один auth/ownership middleware. Несовпадение → finding.

Пример: `apps/web/server/middleware/admin-auth.ts` фильтрует только `/admin|/api/admin`. Все другие `/api/cabinet/*` / `/api/feed/*` без middleware = нарушение complete mediation.

### 2.6. Что НЕ нужно проверять в этой фазе

- Конкретные алгоритмы шифрования — это §06.6.
- Зависимости с CVE — это §03.
- Внутренние state-инварианты (deduct→refund) — это §06b.

Trust map = только потоки **снаружи в систему** и **из системы в backend storage / external systems**.

---

## 3. Quota check перед завершением

- [ ] **≥ 5 findings** для M-проекта.
- [ ] **trust_map.md** содержит ≥ 80% всех роутов из `_handlers.txt`. Если меньше — явно поясни причину выборки.
- [ ] **sources_sinks.md** перечисляет каждый класс sinks с count.
- [ ] Запусти `bash audit_pipeline/scripts/validate_phase.sh 02b`.

---

## 4. Артефакт — `audit/02b_trust_map.md`

### Обязательные разделы
1. **Цель фазы** — карта потоков недоверенных данных.
2. **Что проверено** — sources / sinks по типам, complete mediation.
3. **Ключевые наблюдения**
   - Полный snapshot trust map (или ссылка на evidence/02b_trust_map/trust_map.md если > 50 строк).
   - Самые опасные (риск ≠ clean).
   - Сводка по mediator'ам — кто фильтрует что.
4. **Находки**
5. **Неполные проверки**
6. **Контрольные вопросы**
   - **Q1.** Опиши самый короткий путь от анонимного запроса до critical sink (БД/файл/exec). Конкретно: `endpoint → middleware? → handler → sink`.
   - **Q2.** Какой класс роутов проверяется НЕ всеми middleware? (например: `/api/admin/*` под admin-auth, но `/api/cabinet/*` ничем). Ответ: «X классов под Y middleware, Z классов без» с примерами.
7. **Следующая фаза:** `phases/phase_03_dependencies.md`

---

## 5. Memory

```markdown
# Phase 02b memory
Completed: YYYY-MM-DD

Trust map summary:
- sources_total: <N>
- sources_anonymous: <N>
- sources_admin: <N>
- sinks_sql: <N>
- sinks_http_outbound: <N>
- sinks_fs: <N>
- sinks_render_html: <N>
- mediation_gaps: [<route_glob>: <issue>, ...]

Findings added: F-XXXX to F-YYYY (count)

Next phase: phase_03_dependencies.md
```

---

## 6. Отчёт пользователю

> Фаза 02b/13 завершена. Trust map: <N> sources, <M> sinks. Опасных пар — <K>. Самый короткий путь от анонимного запроса до БД: <one line>. Добавлено <N> findings. Перехожу к фазе 03.

Перейди к `phases/phase_03_dependencies.md`.
