# PHASE 08 — PERFORMANCE & SCALING

**Цель:** Connection pool, кэширование, partitioning, репликация, hardware-related decisions.

**Источники:**
- Schwartz et al., *High Performance MySQL* — Ch. 11 Scaling.
- Greg Smith, *PostgreSQL High Performance* — Ch. 13 Replication, Ch. 4 Disk.
- Kleppmann, *Designing Data-Intensive Applications* — Ch. 5 Replication, Ch. 6 Partitioning.
- Mihalcea, *High Performance Java Persistence* — Ch. 3 JDBC Connection Management.

---

## 1. Входы

- `evidence/01_inventory/config_summary.md`.
- (live) Размер таблиц, статистика.

## 2. Что проверяешь

### 2.1. Connection pooling

Mihalcea Ch. 3:

- [ ] Используется ли pool на app-стороне? (PgBouncer, HikariCP, prisma-default-pool).
- [ ] Размер пула ≤ `max_connections` СУБД / N инстансов?
- [ ] Idle timeout настроен?
- [ ] Connection leak detection (особенно Java)?

**Антипаттерны:**
- Pool size = max_connections — при высокой нагрузке исчерпывается.
- Pool size = 1000 — overhead на стороне СУБД (каждое соединение жрёт RAM).
- Нет pool вообще, новое соединение per request → finding (high на любом проекте >100 RPS).

### 2.2. PgBouncer / ProxySQL (PG/MySQL)

Для PG:
- transaction-mode pooler перед app pool — рекомендация для микросервисной архитектуры.
- session-mode — если используются prepared statements, advisory locks, NOTIFY.

### 2.3. Кэширование

Kleppmann §5: read-replicas + cache.

| Слой | Что кэшируется | Проблемы |
|------|----------------|----------|
| App-level (in-memory) | hot lookup tables (currencies, settings) | invalidation на multi-instance |
| Redis / Memcached | пользовательские сессии, query results | stampede, stale data |
| HTTP-cache (CDN) | анонимные ответы | не подходит для personalised |
| Materialized views | агрегаты, отчёты | refresh strategy |

Проверь:
- [ ] Hot queries из phase 04 — кэшируются?
- [ ] Cache invalidation: TTL / event-based / write-through?
- [ ] Cache stampede protection (mutex / lock / probabilistic refresh)?

### 2.4. Read replicas

- [ ] Есть read replicas?
- [ ] Replication lag — сколько? Мониторится?
- [ ] Какие запросы идут в реплику? Только read-only?
- [ ] Read-after-write проблемы: если только что записал, а через секунду читаешь — попадёт в реплику со stale данными?

Если есть replicas без явной стратегии «когда читать из реплики vs primary» — finding (medium).

### 2.5. Partitioning (Kleppmann Ch. 6)

Когда нужно:
- Таблица > 100M строк.
- Time-series данные с retention policy.
- Multi-tenant со shard-by-tenant.

Проверь:
- [ ] Есть таблицы в категории «должны бы партиционироваться»?
- [ ] Если есть partitioning — стратегия (range / hash / list)?
- [ ] Pruning работает (partition selection в EXPLAIN)?

### 2.6. Sharding

Kleppmann §6.3:
- [ ] Есть приложение, которое уже на грани shard?
- [ ] Если есть sharding — как routing (hash / range / lookup table)?
- [ ] Как происходит rebalancing?
- [ ] Cross-shard queries — есть стратегия?

Sharding — большая тема, обычно не первая итерация. В аудите фиксируешь признаки роста, не предлагаешь sharding default.

### 2.7. VACUUM / ANALYZE (PG)

Smith Ch. 7:

Live-mode:
```sql
SELECT relname, last_vacuum, last_autovacuum, last_analyze,
       n_dead_tup, n_live_tup, n_dead_tup::float / GREATEST(n_live_tup, 1) AS dead_ratio
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC LIMIT 30;
```

- [ ] Таблицы с большим dead_ratio (> 0.2) → autovacuum не успевает.
- [ ] Большие апдейтные таблицы — настроен ли more aggressive autovacuum?

В static-mode — посмотри настройки `autovacuum_*` в конфиге если доступен.

### 2.8. Bloat

PG-специфика:
- [ ] Index bloat (REINDEX CONCURRENTLY можно сделать в phase 06 рекомендации).
- [ ] Table bloat (pg_repack, pg_squeeze).
- [ ] WAL retention — раздувание pg_wal? (replication slots, archive_command).

В static-mode — переноси в `_known_unknowns.md`.

### 2.9. Hardware-aware решения

Smith Ch. 4:
- [ ] SSD vs HDD для WAL и data — known?
- [ ] `random_page_cost` / `seq_page_cost` соответствуют hardware?
- [ ] `shared_buffers`, `work_mem`, `effective_cache_size` — настроены?

Это в основном DBA-задача, но если default-конфиг → финдинг (low) с пометкой «требует DBA review».

### 2.10. Query timeouts

- [ ] App имеет global query timeout? (`statement_timeout` в PG, `max_execution_time` в MySQL).
- [ ] Per-route timeout? (отчёты могут быть длинными, hot path — нет).

Если нет timeout — single slow query может выжрать pool → каскадный отказ.

## 3. Quotas

Минимум 2 findings (M-проект).

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 08
```

Required evidence:
- `evidence/08_performance_scaling/connection_pool_analysis.md`
- `evidence/08_performance_scaling/cache_strategy.md`

## 5. Артефакты

- `audit/08_performance_scaling.md`

---

## v2: Manifest workflow

**Какие manifest-секции читает эта фаза:** `hints.pool_settings`, `paths.pool_config_files`

**Запуск:**
```bash
bash database-audit/run.sh phase 08
```

После детекторов агент дополняет `audit/08_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
