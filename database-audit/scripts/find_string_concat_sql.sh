#!/usr/bin/env bash
# Find SQL injection surface — string concat / interpolation in SQL.
# Karwin §20 SQL Injection.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/07_data_integrity_security"
mkdir -p "$OUT_DIR"

require_cmd rg

{
  echo "# SQL injection surface — string concatenation/interpolation in SQL"
  echo "Generated: $(date -Iseconds)"
  echo
  echo "Каждый match требует ручной проверки: пользовательский ли input доходит до этого места?"
  echo
  echo "## JS/TS — template strings inside query/raw"
  echo '```'
  rg -nE '\$queryRaw|\$executeRaw|raw\(|sql`' --type ts --type js -g '!node_modules' . 2>/dev/null \
    | grep -E '\$\{' | head -100
  echo '```'

  echo
  echo "## JS/TS — string concat in SQL"
  echo '```'
  rg -nE '(SELECT|INSERT|UPDATE|DELETE|WHERE|FROM)[^"'"'"']*"\s*\+|"\s*\+\s*\w+\s*\+\s*"' \
     --type ts --type js -g '!node_modules' . 2>/dev/null | head -100
  echo '```'

  echo
  echo "## Python — f-strings in queries"
  echo '```'
  rg -nE '(execute|cursor|raw|text)\s*\(\s*f["\x27]' --type py 2>/dev/null | head -100
  echo '```'

  echo
  echo "## Python — % formatting in SQL"
  echo '```'
  rg -nE '(execute|cursor|raw|text)\s*\(["\x27].*%[sd].*["\x27]\s*%' --type py 2>/dev/null | head -100
  echo '```'

  echo
  echo "## Go — fmt.Sprintf in query"
  echo '```'
  rg -nE 'fmt\.Sprintf\([^)]*(SELECT|INSERT|UPDATE|DELETE)' --type go 2>/dev/null | head -100
  echo '```'

  echo
  echo "## PHP — interpolation in raw queries"
  echo '```'
  rg -nE 'DB::(select|raw|statement)\s*\(["\x27][^"\x27]*\$' --type php 2>/dev/null | head -100
  echo '```'

  echo
  echo "## Ruby — interpolation in queries"
  echo '```'
  rg -nE '\.(where|find_by_sql|execute)\s*\(["\x27][^"\x27]*#\{' --type ruby 2>/dev/null | head -100
  echo '```'

  echo
  echo "## Java — string concatenation in SQL"
  echo '```'
  rg -nE '(createQuery|createNativeQuery|prepareStatement)\s*\([^)]*"\s*\+' --type java 2>/dev/null | head -100
  echo '```'
} > "$OUT_DIR/sqli_surface.md"

ok "sqli_surface.md written"
