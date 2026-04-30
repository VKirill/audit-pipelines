# TOOLS — versions and security guarantees

Single source of truth для всех зависимостей пайплайна. Обновляется при каждом upgrade.

---

## Required (hard dependencies)

### Python 3.10+

```bash
python3 --version  # must be >= 3.10 (для walrus, match-case в lib/ если нужно)
```

Tested: 3.10, 3.11, 3.12, 3.13.

### Python packages

| Package | Min version | Why |
|---------|-------------|-----|
| `PyYAML` | `>=6.0,<7.0` | Manifest parsing. 6.0+ — actively maintained branch |
| `jsonschema` | `>=4.23.0,<5.0` | Manifest validation. **<4.18 has CVE-2023-22102 (DoS)**. >=4.23 stable |

Установка:
```bash
pip install -r database-audit/requirements.txt
```

Проверка:
```bash
python3 -c "import yaml, jsonschema; print('yaml:', yaml.__version__); print('jsonschema:', jsonschema.__version__)"
```

### CLI tools

| Tool | Min version | Why | Latest as of 2026 |
|------|-------------|-----|---------|
| `git` | `>=2.30` | Repository introspection | 2.46+ |
| `jq` | `>=1.6` | JSON processing in bash | `1.7.x` |
| `rg` (ripgrep) | `>=13.0` | Fast regex search; `-g` glob support | `14.1+` |
| `find` | POSIX | Universal file traversal | — |

Установка:
```bash
sudo apt install jq ripgrep git python3 python3-pip
pip install -r database-audit/requirements.txt
```

---

## Optional (live mode + extended detectors)

### Database access (live mode)

В priority order — пайплайн пытается live mode через эти источники:

| Tool | When | Preferred? |
|------|------|------------|
| **MCP postgres server** (Claude Code MCP) | live mode + Postgres + Claude Code with MCP | ⭐ **preferred** — DSN-free, read-only enforced |
| `psql` (PostgreSQL client) | live mode + Postgres + DSN из env | стандартный путь |
| `mysql` | live mode + MySQL/MariaDB + DSN | для MySQL/MariaDB проектов |
| `mongosh` (MongoDB Shell) | live mode + Mongo + DSN | для Mongo проектов |

**MCP postgres setup** (preferred):
```bash
# Если используешь Claude Code и есть MCP postgres сервер настроенный —
# пайплайн автоматически использует его для live mode (без DSN)
# Setup: см. https://github.com/modelcontextprotocol/servers/tree/main/src/postgres
```

**CLI clients** (fallback):
```bash
sudo apt install postgresql-client mysql-client
# mongosh: https://www.mongodb.com/try/download/shell
```

### Live mode decision tree

```
Stage 0.5 — DSN/mode auto-detection:
  1. Check MCP postgres available? → use it (live mode, DSN-free)
  2. Else: scan env files (.env, .env.local, monorepo workspaces)
  3. Else: scan config files (database.yml, settings.py via Serena)
  4. Found DSN? → verify read-only role → live mode
  5. No DSN OR write-rights user → static mode (with note)
```

### MCP servers

| Tool | When needed |
|------|-------------|
| **Serena** | Symbol-level navigation (deep discovery) — `00f_discover_serena_deep.md` |
| **GitNexus** | Knowledge graph + cypher queries — `00g_discover_gitnexus_graph.md` |

```bash
# Serena — installs via uv
uv tool install -p 3.13 serena-agent@latest --prerelease=allow
claude mcp add serena -- serena start-mcp-server --context ide-assistant

# GitNexus — installs via npm
npm install -g gitnexus
gitnexus setup        # configures MCP for Claude Code
gitnexus analyze      # index repository (run in project root)
```

### Security tools

| Tool | When needed |
|------|-------------|
| `gitleaks` | Secrets scanning (auto-falls back to grep если отсутствует) |
| `osv-scanner` | Vulnerability scanning lock-files |

```bash
# gitleaks
curl -sSfL https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.21.1_linux_x64.tar.gz \
  | tar -xz -C /usr/local/bin gitleaks

# osv-scanner
go install github.com/google/osv-scanner/cmd/osv-scanner@v1
```

### YAML editor (for manifest manual fixes)

```bash
# yq — Python wrapper или Go binary, оба ОК
pip install yq                                  # Python version
# OR
sudo wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
sudo chmod +x /usr/local/bin/yq
```

---

## Compatibility matrix

| Component | Tested with | Known issues |
|-----------|-------------|--------------|
| Python 3.10 | ✅ | none |
| Python 3.11 | ✅ | none |
| Python 3.12 | ✅ | jsonschema deprecates `__version__` (use importlib.metadata) |
| Python 3.13 | ✅ | none |
| jsonschema 4.10.x | ⚠️ vulnerable | CVE-2023-22102 (DoS) — **upgrade to 4.23+** |
| jsonschema 4.18+ | ✅ | none |
| ripgrep <13 | ⚠️ | `-g` glob syntax limited |
| jq <1.6 | ❌ | `--arg` and pipeline ops missing |

---

## Update cadence

- **Critical security CVE** — апгрейд в течение 24h. Pinned diff в `requirements.txt`.
- **Minor versions** — раз в квартал, batch-upgrade всего стека.
- **Major versions** — review breaking changes сначала, отдельный PR.

---

## Verification commands

```bash
# Python deps
python3 -c "
import yaml, jsonschema, sys
print(f'Python:     {sys.version.split()[0]}')
print(f'PyYAML:     {yaml.__version__}')
print(f'jsonschema: {jsonschema.__version__}')
"

# CLI tools
echo "=== Required ==="
git --version | head -1
jq --version
rg --version | head -1

echo "=== Optional ==="
psql --version 2>/dev/null || echo 'psql: not installed'
mysql --version 2>/dev/null || echo 'mysql: not installed'
mongosh --version 2>/dev/null || echo 'mongosh: not installed'
gitleaks version 2>/dev/null || echo 'gitleaks: not installed'
gitnexus --version 2>/dev/null || echo 'gitnexus: not installed'
```

---

## Why not Docker?

Считаемые плюсы Docker (одно окружение, точная версия):
1. **Pipeline read-only** — нет state, нет смысла в контейнере
2. **MCP integration** — Serena/GitNexus уже на хосте, контейнер всё ломает
3. **Скорость** — pip install + apt install уже быстрее docker pull

Если очень хочется — `Dockerfile` тривиален, добавить можно позже.
