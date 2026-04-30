#!/usr/bin/env bash
# Detect ORM/DB stack in current project.
# Output: human-readable stack summary + parsable key=value lines.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

set +e
exists() { [[ -e "$1" ]]; }
in_file() { grep -qE "$1" "$2" 2>/dev/null; }

orms=()
dbs=()

# Node ecosystem
if exists package.json; then
  in_file '"@prisma/client"' package.json && orms+=(prisma)
  in_file '"drizzle-orm"' package.json && orms+=(drizzle)
  in_file '"typeorm"' package.json && orms+=(typeorm)
  in_file '"sequelize"' package.json && orms+=(sequelize)
  in_file '"mongoose"' package.json && orms+=(mongoose)
  in_file '"knex"' package.json && orms+=(knex)
  in_file '"kysely"' package.json && orms+=(kysely)
  in_file '"mikro-orm"' package.json && orms+=(mikro-orm)
  in_file '"pg"' package.json && orms+=(pg-raw)
  in_file '"mysql2"' package.json && orms+=(mysql2-raw)
  in_file '"better-sqlite3"' package.json && orms+=(sqlite-raw)

  in_file '"@prisma/client"' package.json && exists prisma/schema.prisma && info "Prisma schema: prisma/schema.prisma"
fi

# Python
for f in requirements.txt pyproject.toml setup.py; do
  exists "$f" || continue
  in_file 'sqlalchemy' "$f" && orms+=(sqlalchemy)
  in_file 'django' "$f" && orms+=(django-orm)
  in_file 'tortoise' "$f" && orms+=(tortoise)
  in_file 'peewee' "$f" && orms+=(peewee)
  in_file 'psycopg' "$f" && orms+=(psycopg-raw)
  in_file 'asyncpg' "$f" && orms+=(asyncpg-raw)
  in_file 'pymongo' "$f" && orms+=(pymongo)
done

# Go
if exists go.mod; then
  in_file 'gorm.io/gorm' go.mod && orms+=(gorm)
  in_file 'github.com/jmoiron/sqlx' go.mod && orms+=(sqlx)
  in_file 'github.com/sqlc-dev/sqlc' go.mod && orms+=(sqlc)
  in_file 'github.com/uptrace/bun' go.mod && orms+=(bun)
  in_file 'entgo.io/ent' go.mod && orms+=(ent)
  in_file 'database/sql' go.mod && orms+=(go-sql-raw)
fi

# PHP
if exists composer.json; then
  in_file 'doctrine/orm' composer.json && orms+=(doctrine)
  in_file 'illuminate/database' composer.json && orms+=(eloquent)
  in_file 'laravel/framework' composer.json && orms+=(eloquent)
fi

# Ruby
if exists Gemfile; then
  in_file 'rails' Gemfile && orms+=(activerecord)
  in_file 'sequel' Gemfile && orms+=(sequel)
fi

# Java/Kotlin
for f in pom.xml build.gradle build.gradle.kts; do
  exists "$f" || continue
  in_file 'hibernate-core' "$f" && orms+=(hibernate)
  in_file 'spring-boot-starter-data-jpa' "$f" && orms+=(spring-data-jpa)
  in_file 'jOOQ' "$f" && orms+=(jooq)
  in_file 'mybatis' "$f" && orms+=(mybatis)
done

# Rust
if exists Cargo.toml; then
  in_file 'diesel' Cargo.toml && orms+=(diesel)
  in_file 'sqlx' Cargo.toml && orms+=(sqlx-rust)
  in_file 'sea-orm' Cargo.toml && orms+=(sea-orm)
fi

# Detect databases via DSN patterns / drivers
maybe_dsn() {
  local pattern="$1" db_name="$2"
  if rg -nU "$pattern" --no-ignore -g '!node_modules' -g '!vendor' -g '!.git' -g '!dist' -g '!build' . 2>/dev/null | head -1 | grep -q .; then
    dbs+=("$db_name")
  fi
}

maybe_dsn 'postgres(ql)?://' postgresql
maybe_dsn 'mysql://' mysql
maybe_dsn 'mariadb://' mariadb
maybe_dsn 'sqlite:|sqlite3:|\.sqlite|\.db$' sqlite
maybe_dsn 'mongodb(\+srv)?://' mongodb
maybe_dsn 'redis://|rediss://' redis
maybe_dsn 'clickhouse://' clickhouse
maybe_dsn 'cassandra://' cassandra

# Migrations directories
mig_dirs=()
for d in prisma/migrations migrations db/migrate database/migrations app/Models/migrations alembic atlas; do
  exists "$d" && mig_dirs+=("$d")
done
# alembic
exists alembic.ini && mig_dirs+=(alembic)
exists alembic/versions && mig_dirs+=(alembic/versions)

# Schema files
schema_files=()
exists prisma/schema.prisma && schema_files+=(prisma/schema.prisma)
for f in $(find . -maxdepth 4 -type f \( -name 'schema.ts' -o -name '*.schema.ts' -o -name 'schema.py' -o -name 'models.py' \) -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | head -50); do
  schema_files+=("$f")
done

# Output
echo "# Stack detection — $(date -Iseconds)"
echo
echo "## ORMs detected"
if (( ${#orms[@]} == 0 )); then
  echo "(none detected — manual confirmation required)"
else
  printf '%s\n' "${orms[@]}" | sort -u | sed 's/^/- /'
fi

echo
echo "## Databases detected"
if (( ${#dbs[@]} == 0 )); then
  echo "(none detected via DSN — check env files manually)"
else
  printf '%s\n' "${dbs[@]}" | sort -u | sed 's/^/- /'
fi

echo
echo "## Migration directories"
if (( ${#mig_dirs[@]} == 0 )); then
  echo "(none — possibly declarative schema or external migration tool)"
else
  printf '%s\n' "${mig_dirs[@]}" | sort -u | sed 's/^/- /'
fi

echo
echo "## Schema files (top 50)"
if (( ${#schema_files[@]} == 0 )); then
  echo "(none)"
else
  printf '%s\n' "${schema_files[@]}" | sort -u | sed 's/^/- /'
fi

echo
echo "## Parsable summary"
echo "orms=$(printf '%s,' "${orms[@]}" | sed 's/,$//')"
echo "dbs=$(printf '%s,' "${dbs[@]}" | sed 's/,$//')"
echo "mig_dirs=$(printf '%s,' "${mig_dirs[@]}" | sed 's/,$//')"
