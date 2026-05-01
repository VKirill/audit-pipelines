# PHASE 09 — OBSERVABILITY & OPS

**Цель:** Slow query log, метрики, бэкапы, disaster recovery, on-call процедуры.

**Источники:**
- Google SRE Book — Ch. 4 SLO, Ch. 6 Monitoring (4 golden signals), Ch. 26 Data Integrity.
- Brendan Gregg, *Systems Performance* — Ch. 5 Applications (USE method).
- Greg Smith, *PostgreSQL High Performance* — Ch. 7 Maintenance, Ch. 11 Activity & Statistics.

---

## 1. Входы

- `evidence/01_inventory/config_summary.md`.
- CI/CD конфигурация (для backup pipeline).

## 2. Что проверяешь

### 2.1. Slow query log

PostgreSQL:
- [ ] `log_min_duration_statement` установлен (например, 1000ms)?
- [ ] `pg_stat_statements` включён? (`shared_preload_libraries` + extension).
- [ ] Логи ротируются и куда отправляются?

MySQL:
- [ ] `slow_query_log = 1`, `long_query_time = 1`?
- [ ] `log_queries_not_using_indexes`?

MongoDB:
- [ ] Profiler включён (`db.setProfilingLevel(1, 100)`)?

Если slow log не настроен → finding (medium, ослепший в сложный момент).

### 2.2. Метрики

SRE 4 golden signals:
- **Latency** — p50/p95/p99 по запросам в БД.
- **Traffic** — RPS на БД.
- **Errors** — connection errors, deadlocks, timeouts.
- **Saturation** — connections used / max, CPU, IOPS.

- [ ] Эти метрики собираются? Куда (Prometheus / Datadog / New Relic / CloudWatch)?
- [ ] Дашборд для DB существует?
- [ ] Алерты на отклонения настроены?

### 2.3. Алертинг

- [ ] Алерт на: connection saturation > 80%?
- [ ] Алерт на: replication lag > N секунд?
- [ ] Алерт на: disk usage > 80%?
- [ ] Алерт на: backup failure?
- [ ] Алерт на: deadlock count?

Pages-on-call: страничные правила должны иметь runbook.

### 2.4. Backup

SRE Ch. 26:

| Тип | Когда | Зачем |
|-----|-------|-------|
| Full | weekly | base recovery |
| Incremental / WAL | continuous | point-in-time recovery |
| Logical (`pg_dump`/`mysqldump`) | weekly | cross-version restore |
| Snapshot (cloud) | daily | быстрое восстановление instance |

- [ ] Какая стратегия в проекте?
- [ ] Где хранятся бэкапы (S3 / GCS / on-disk)?
- [ ] Encryption at-rest бэкапов?
- [ ] Retention policy?
- [ ] Cross-region копия?

### 2.5. Recovery test

**Главный пункт фазы.** SRE: «backup ≠ recovery».

- [ ] Когда последний раз восстанавливались с бэкапа?
- [ ] Есть ли документированная процедура recovery?
- [ ] Знают ли два человека, как восстанавливать?
- [ ] Время восстановления (RTO) измерено?
- [ ] Recovery point (RPO) — сколько данных можем потерять?

**Если backups делаются, но никогда не тестировался recovery → high finding (это самая частая проблема).**

### 2.6. Disaster recovery план

- [ ] DR-план в Confluence/wiki/repo?
- [ ] План включает: «primary AZ down», «весь регион down», «случайный DROP TABLE»?
- [ ] runbook для on-call?
- [ ] Connection failover настроен (HAProxy / pgpool / Patroni)?

### 2.7. Schema diff в проде

- [ ] Существует ли стратегия отслеживания изменений схемы вне миграций? («ручные правки в проде»).
- [ ] Schema dump регулярно сравнивается с тем, что в репо?

В большом prod нередко находятся колонки, которых нет в схеме репо — это всегда finding (medium).

### 2.8. Тестовая среда

- [ ] Есть ли staging со схемой = prod?
- [ ] Данные на staging — production-like (анонимизированные)?
- [ ] Перенос dump prod → staging автоматизирован?

### 2.9. CI/CD для миграций

- [ ] Миграции применяются автоматически в CI?
- [ ] Перед прод-деплоем тестируются на staging?
- [ ] dry-run / `--check` режим есть?
- [ ] Rollback процедура — описана?

### 2.10. Connection-string handling в проде

- [ ] Через secret manager (Vault, AWS Secrets Manager, K8s secret)?
- [ ] Не в логах при ошибках?
- [ ] Rotation procedure для паролей?
- [ ] App переподключается без рестарта при rotation?

## 3. Quotas

Минимум 2 findings (M-проект).

## 4. Hard exit gate

```bash
bash database-audit/scripts/validate_phase.sh 09
```

Required evidence:
- `evidence/09_observability_ops/monitoring_inventory.md`
- `evidence/09_observability_ops/backup_strategy.md`
- `evidence/09_observability_ops/dr_readiness.md`

## 5. Артефакты

- `audit/09_observability_ops.md`

---

## Manifest workflow

**Какие manifest-секции читает эта фаза:** (пока stub — manual review)

**Запуск:**
```bash
bash database-audit/run.sh phase 09
```

После детекторов агент дополняет `audit/09_*.md` отчёт фазы согласно структуре в `TEMPLATES.md §2` (секции: Что проверено / Сводка / Findings / Ограничения / Артефакты).

Если детектор не нашёл ожидаемых hints в manifest — это сигнал что **discover упустил**, надо допилить manifest и перезапустить детектор.
