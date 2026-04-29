#!/usr/bin/env bash
# run_external_tools.sh — orchestrator for deterministic data collectors.
#
# Запускается ПЕРЕД фазами 03/06/07 (или один раз на старте). Делает дешёвые,
# кэшируемые сборы данных так, чтобы агент всегда работал с готовыми артефактами,
# а не «не успел запустить gitleaks».
#
# Каждый шаг изолирован в своём подкоманде (run_*) и НИКОГДА не падает.
# Результаты в audit/evidence/<phase>/. Если инструмент отсутствует — печатается
# placeholder с инструкцией как установить.
#
# Usage:
#   ./scripts/run_external_tools.sh           # все шаги
#   ./scripts/run_external_tools.sh sca       # только npm/pip audit
#   ./scripts/run_external_tools.sh secrets   # только gitleaks/trufflehog
#   ./scripts/run_external_tools.sh coverage  # только vitest --coverage / pytest --cov
#   ./scripts/run_external_tools.sh inventory # cloc, find -size, git stats
#   ./scripts/run_external_tools.sh history   # secret history scan via git log
#
# Exit: 0 always (это сборщик, а не gate).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SCRIPT_DIR/lib/common.sh"
set +e  # никаких exit на ошибки одного инструмента

require_audit_dir
mkdir -p "$EVIDENCE_DIR"/{01_inventory,03_dependencies,06_security,07_tests}

placeholder() {
  local out="$1" tool="$2" install="$3"
  cat > "$out" <<EOF
# tool not available: $tool
# install: $install
# generated: $(date -Iseconds)
EOF
  warn "$tool unavailable — placeholder at $out"
}

# ------------------------------- INVENTORY ------------------------------------
run_inventory() {
  echo "==> inventory"
  local out_dir="$EVIDENCE_DIR/01_inventory"
  mkdir -p "$out_dir"

  if command -v cloc >/dev/null 2>&1; then
    cloc . \
      --exclude-dir=node_modules,dist,build,.git,vendor,target,.venv,venv,__pycache__,.next,.nuxt,.output,.turbo \
      --json > "$out_dir/cloc.json" 2>"$out_dir/cloc.err" || true
    ok "cloc → cloc.json"
  else
    placeholder "$out_dir/cloc.json" "cloc" "apt install cloc"
  fi

  # File counts as fallback
  {
    echo "# File counts (fallback) — $(date -Iseconds)"
    find . -type f \
      \( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.mjs' -o -name '*.cjs' \
         -o -name '*.py' -o -name '*.go' -o -name '*.rs' -o -name '*.java' -o -name '*.rb' \
         -o -name '*.php' -o -name '*.cs' -o -name '*.vue' -o -name '*.svelte' \) \
      -not -path '*/node_modules/*' -not -path '*/dist/*' -not -path '*/.git/*' \
      -not -path '*/build/*' -not -path '*/vendor/*' -not -path '*/.venv/*' -not -path '*/.next/*' \
      -not -path '*/.nuxt/*' -not -path '*/.output/*' -not -path '*/.turbo/*' \
      | awk -F. '{print $NF}' | sort | uniq -c | sort -rn
  } > "$out_dir/file_counts.txt"
  ok "file_counts.txt"

  # git stats
  if [[ -d .git ]]; then
    {
      echo "# Git stats — $(date -Iseconds)"
      echo "## HEAD"
      git rev-parse HEAD
      git rev-parse --abbrev-ref HEAD
      echo
      echo "## Activity"
      git log --format='%ci %an' | head -1
      git log --format='%ci %an' | tail -1
      echo "Commits total: $(git rev-list --count HEAD 2>/dev/null || echo ?)"
      echo "Commits 90d:   $(git log --since='90 days ago' --oneline 2>/dev/null | wc -l)"
      echo
      echo "## Authors"
      git shortlog -sne 2>/dev/null | head -20
      echo
      echo "## Repo size"
      git count-objects -vH 2>/dev/null
    } > "$out_dir/git_stats.txt"
    ok "git_stats.txt"
  fi
}

# ------------------------------- SCA ------------------------------------------
run_sca() {
  echo "==> SCA"
  local out_dir="$EVIDENCE_DIR/03_dependencies"
  mkdir -p "$out_dir"

  if [[ -f package.json ]] && command -v npm >/dev/null 2>&1; then
    # Don't pollute the project with installs; only audit and outdated.
    npm audit --json > "$out_dir/dep_audit.json" 2>"$out_dir/dep_audit.err" || true
    npm audit > "$out_dir/dep_audit.txt" 2>>"$out_dir/dep_audit.err" || true
    npm outdated --json > "$out_dir/outdated.json" 2>>"$out_dir/dep_audit.err" || true
    ok "npm audit / outdated → $out_dir"
  fi

  if [[ -f pyproject.toml || -f requirements.txt ]]; then
    if command -v pip-audit >/dev/null 2>&1; then
      pip-audit -f json > "$out_dir/dep_audit.json" 2>"$out_dir/dep_audit.err" || true
      pip-audit > "$out_dir/dep_audit.txt" 2>>"$out_dir/dep_audit.err" || true
      ok "pip-audit → $out_dir"
    elif command -v osv-scanner >/dev/null 2>&1; then
      osv-scanner --format json . > "$out_dir/dep_audit.json" 2>"$out_dir/dep_audit.err" || true
      ok "osv-scanner → dep_audit.json"
    else
      placeholder "$out_dir/dep_audit.txt" "pip-audit/osv-scanner" "pipx install pip-audit  OR  brew install osv-scanner"
    fi
  fi

  # manifest summary
  {
    echo "# Manifest summary — $(date -Iseconds)"
    for f in package.json pyproject.toml requirements.txt go.mod Cargo.toml composer.json Gemfile pom.xml; do
      [[ -f "$f" ]] && echo "- $f ($(wc -l <"$f") lines)"
    done
    echo
    echo "## Workspaces / monorepo"
    find . -maxdepth 4 -name 'package.json' -not -path '*/node_modules/*' 2>/dev/null | head -50
  } > "$out_dir/manifest_summary.md"
  ok "manifest_summary.md"
}

# ------------------------------- SECRETS --------------------------------------
run_secrets() {
  echo "==> secrets"
  local out_dir="$EVIDENCE_DIR/06_security"
  mkdir -p "$out_dir"

  if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --source . --no-banner --redact \
      --report-format json --report-path "$out_dir/gitleaks.json" \
      > "$out_dir/gitleaks.log" 2>&1 || true
    ok "gitleaks → gitleaks.json"
  else
    placeholder "$out_dir/gitleaks.json" "gitleaks" "brew install gitleaks  OR  https://github.com/gitleaks/gitleaks/releases"
  fi

  if command -v trufflehog >/dev/null 2>&1; then
    trufflehog filesystem . --json --no-update > "$out_dir/trufflehog.json" 2>"$out_dir/trufflehog.err" || true
    ok "trufflehog → trufflehog.json"
  fi

  # Always run grep-based fallback so secret_scan.txt is never empty
  {
    echo "# Secret grep scan — $(date -Iseconds)"
    echo "## Private keys"
    grep -rnE -- "-----BEGIN (RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----" \
      --include='*' --exclude-dir=node_modules --exclude-dir=.git \
      --exclude-dir=dist --exclude-dir=build --exclude-dir=vendor \
      --exclude-dir=.venv --exclude-dir=.next --exclude-dir=.nuxt \
      --exclude-dir=.output --exclude-dir=.turbo . 2>/dev/null | head -30
    echo
    echo "## Common API key prefixes"
    grep -rnE 'ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{30,}|xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+' \
      --include='*' --exclude-dir=node_modules --exclude-dir=.git \
      --exclude-dir=dist --exclude-dir=build --exclude-dir=vendor . 2>/dev/null | head -30
    echo
    echo "## Service-account JSON markers"
    grep -rnE '"type":\s*"service_account"|"private_key":\s*"-----BEGIN' \
      --include='*.json' --exclude-dir=node_modules --exclude-dir=.git . 2>/dev/null | head -20
    echo
    echo "## Generic patterns"
    grep -rniE "(api[-_]?key|apikey|secret|token|password|passwd|pwd)\\s*[:=]\\s*['\"][A-Za-z0-9_\\-/+=]{16,}['\"]" \
      --include='*.ts' --include='*.js' --include='*.py' --include='*.go' --include='*.rb' --include='*.php' \
      --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=build . 2>/dev/null | head -30
  } > "$out_dir/secret_scan.txt"
  ok "secret_scan.txt"
}

# --------------------------- SECRET HISTORY -----------------------------------
run_history() {
  echo "==> secret history"
  local out_dir="$EVIDENCE_DIR/06_security"
  mkdir -p "$out_dir"
  if [[ ! -d .git ]]; then
    placeholder "$out_dir/secret_history.txt" "git" "no .git directory"
    return
  fi
  if command -v gitleaks >/dev/null 2>&1; then
    gitleaks detect --source . --no-banner --redact --log-opts="--all" \
      --report-format json --report-path "$out_dir/gitleaks_history.json" \
      > "$out_dir/gitleaks_history.log" 2>&1 || true
    ok "gitleaks history → gitleaks_history.json"
  fi
  {
    echo "# Secret history grep — $(date -Iseconds)"
    echo "(grep on git log -p --all, may take a moment)"
    git log -p --all 2>/dev/null \
      | grep -E "(BEGIN .*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{30,}|xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+|github_pat_[A-Za-z0-9_]{60,})" \
      | head -100
  } > "$out_dir/secret_history.txt" 2>&1
  ok "secret_history.txt"
}

# ------------------------------- COVERAGE -------------------------------------
run_coverage() {
  echo "==> coverage"
  local out_dir="$EVIDENCE_DIR/07_tests"
  mkdir -p "$out_dir"

  if [[ -f package.json ]] && command -v npx >/dev/null 2>&1; then
    if grep -q 'vitest' package.json 2>/dev/null || \
       find . -maxdepth 3 -name 'vitest.config*' -not -path '*/node_modules/*' | grep -q .; then
      ( npx --no-install vitest run --coverage --coverage.reporter=json-summary \
          > "$out_dir/coverage.log" 2>&1 || true )
      [[ -f coverage/coverage-summary.json ]] && cp coverage/coverage-summary.json "$out_dir/" || true
      ok "vitest --coverage attempted"
    elif grep -q 'jest' package.json 2>/dev/null; then
      ( npx --no-install jest --coverage --coverageReporters=json-summary \
          > "$out_dir/coverage.log" 2>&1 || true )
      [[ -f coverage/coverage-summary.json ]] && cp coverage/coverage-summary.json "$out_dir/" || true
      ok "jest --coverage attempted"
    else
      placeholder "$out_dir/coverage-summary.json" "vitest/jest" "configure test runner with coverage reporter"
    fi
  elif [[ -f pyproject.toml || -f setup.py ]]; then
    if command -v pytest >/dev/null 2>&1 && pip show coverage >/dev/null 2>&1; then
      ( pytest --cov --cov-report=json:"$out_dir/coverage.json" > "$out_dir/coverage.log" 2>&1 || true )
      ok "pytest --cov attempted"
    else
      placeholder "$out_dir/coverage.json" "pytest+coverage" "pip install pytest pytest-cov"
    fi
  fi

  # Test inventory snapshot — runner-agnostic
  {
    echo "# Test files inventory — $(date -Iseconds)"
    find . -type f \
      \( -name '*.test.*' -o -name '*.spec.*' -o -name 'test_*.py' -o -name '*_test.go' \) \
      -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/dist/*' \
      | xargs -I{} sh -c 'echo "$(wc -l <"{}" | tr -d " ") {}"' 2>/dev/null \
      | sort -rn | head -100
  } > "$out_dir/test_files.txt"
  ok "test_files.txt"
}

# ------------------------------ DISPATCH --------------------------------------
case "${1:-all}" in
  all)        run_inventory; run_sca; run_secrets; run_history; run_coverage ;;
  inventory)  run_inventory ;;
  sca)        run_sca ;;
  secrets)    run_secrets ;;
  history)    run_history ;;
  coverage)   run_coverage ;;
  *)          echo "Usage: $0 [all|inventory|sca|secrets|history|coverage]" >&2; exit 2 ;;
esac

echo
ok "external tools sweep finished — review evidence files"
