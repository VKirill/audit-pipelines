#!/usr/bin/env bash
# Live DB probe — only runs if DATABASE_URL is set.
# READ-ONLY queries only.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/00_setup"
LIVE_DIR="${EVIDENCE_DIR}/_live"
mkdir -p "$OUT_DIR" "$LIVE_DIR"

if [[ -z "${DATABASE_URL:-}" ]]; then
  warn "DATABASE_URL not set — skipping live probe (static-mode)"
  echo "static-mode" > "$OUT_DIR/live_db_handshake.txt"
  exit 0
fi

# Detect DB type from URL scheme
case "$DATABASE_URL" in
  postgres://*|postgresql://*) DB_TYPE=postgres ;;
  mysql://*|mariadb://*) DB_TYPE=mysql ;;
  mongodb://*|mongodb+srv://*) DB_TYPE=mongo ;;
  *) DB_TYPE=unknown ;;
esac

info "DATABASE_URL detected: type=$DB_TYPE"

probe_postgres() {
  command -v psql >/dev/null 2>&1 || { warn "psql not installed"; return 1; }

  # Read-only role confirmation
  psql "$DATABASE_URL" -t -c \
    "SELECT current_user, current_setting('default_transaction_read_only')" \
    > "$OUT_DIR/live_db_handshake.txt" 2>&1
  if grep -q FATAL "$OUT_DIR/live_db_handshake.txt"; then
    warn "Postgres connection failed — see live_db_handshake.txt"
    return 1
  fi
  ok "PG handshake → $OUT_DIR/live_db_handshake.txt"

  # Indexes
  psql "$DATABASE_URL" -c "
    SELECT schemaname, tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname NOT IN ('pg_catalog','information_schema')
    ORDER BY schemaname, tablename, indexname
  " > "$LIVE_DIR/pg_indexes.txt" 2>&1 && ok "pg_indexes captured"

  # Index usage (mark unused)
  psql "$DATABASE_URL" -c "
    SELECT schemaname, relname, indexrelname, idx_scan,
           pg_size_pretty(pg_relation_size(indexrelid)) AS size
    FROM pg_stat_user_indexes
    ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC
    LIMIT 100
  " > "$LIVE_DIR/pg_index_usage.txt" 2>&1 && ok "index usage captured"

  # FK without index — PG-specific query
  psql "$DATABASE_URL" -c "
    SELECT c.conrelid::regclass AS table, a.attname AS column
    FROM pg_constraint c
    JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
    WHERE c.contype = 'f'
      AND NOT EXISTS (
        SELECT 1 FROM pg_index i
        WHERE i.indrelid = c.conrelid
          AND a.attnum = ANY(i.indkey)
      )
    ORDER BY 1, 2
  " > "$LIVE_DIR/pg_fk_without_index.txt" 2>&1 && ok "pg fk-without-index captured"

  # Table sizes
  psql "$DATABASE_URL" -c "
    SELECT schemaname, relname,
           pg_size_pretty(pg_relation_size(relid)) AS size,
           n_live_tup, n_dead_tup
    FROM pg_stat_user_tables
    ORDER BY pg_relation_size(relid) DESC
    LIMIT 30
  " > "$LIVE_DIR/pg_table_sizes.txt" 2>&1 && ok "pg table sizes captured"

  # pg_stat_statements (if extension enabled)
  psql "$DATABASE_URL" -c "
    SELECT query, calls, total_exec_time, mean_exec_time, rows
    FROM pg_stat_statements
    WHERE query NOT LIKE '%pg_stat_%'
    ORDER BY mean_exec_time DESC
    LIMIT 30
  " > "$LIVE_DIR/pg_stat_statements.txt" 2>&1
  if grep -qE 'does not exist|relation .* does not exist' "$LIVE_DIR/pg_stat_statements.txt"; then
    warn "pg_stat_statements not enabled — slow query data unavailable"
    echo "pg_stat_statements not enabled" > "$LIVE_DIR/pg_stat_statements.txt"
  else
    ok "pg_stat_statements captured"
  fi

  # Vacuum / dead tuples
  psql "$DATABASE_URL" -c "
    SELECT relname, last_vacuum, last_autovacuum, last_analyze,
           n_dead_tup, n_live_tup,
           CASE WHEN n_live_tup > 0 THEN n_dead_tup::float / n_live_tup ELSE 0 END AS dead_ratio
    FROM pg_stat_user_tables
    ORDER BY n_dead_tup DESC LIMIT 30
  " > "$LIVE_DIR/pg_vacuum_status.txt" 2>&1 && ok "vacuum status captured"
}

probe_mysql() {
  command -v mysql >/dev/null 2>&1 || { warn "mysql client not installed"; return 1; }
  warn "MySQL live-mode is partial — implement specifics for your version"
  echo "mysql probe placeholder" > "$LIVE_DIR/mysql_indexes.txt"
}

probe_mongo() {
  command -v mongosh >/dev/null 2>&1 || { warn "mongosh not installed"; return 1; }
  mongosh "$DATABASE_URL" --quiet --eval '
    db.runCommand({connectionStatus:1}).authInfo.authenticatedUserRoles
  ' > "$OUT_DIR/live_db_handshake.txt" 2>&1
  ok "Mongo handshake captured"

  mongosh "$DATABASE_URL" --quiet --eval '
    db.getCollectionNames().forEach(c => {
      print("\n=== " + c);
      printjson(db.getCollection(c).getIndexes());
    });
  ' > "$LIVE_DIR/mongo_indexes.txt" 2>&1 && ok "mongo indexes captured"
}

case "$DB_TYPE" in
  postgres) probe_postgres ;;
  mysql) probe_mysql ;;
  mongo) probe_mongo ;;
  *) warn "Unknown DB type ($DB_TYPE) — skipping live probe" ;;
esac
