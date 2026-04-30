#!/usr/bin/env bash
# Heuristic N+1 detector: ORM calls inside for / while / map / forEach.
# Output: markdown report.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
set +e

OUT_DIR="${EVIDENCE_DIR}/04_query_patterns"
mkdir -p "$OUT_DIR"

require_cmd python3
require_cmd rg

python3 - <<'PY' > "$OUT_DIR/n_plus_one_suspects.md"
import os, re, sys, subprocess
from pathlib import Path

EXTS = {'.ts', '.tsx', '.js', '.mjs', '.cjs', '.py', '.go', '.java', '.kt', '.rb', '.php', '.rs'}
SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', 'vendor', '__pycache__', 'venv', '.venv', '.next'}

ORM_CALL = re.compile(
    r'\b(prisma|db|orm|repo|repository|session|cursor|conn|connection)\b\s*'
    r'(?:\.\w+)*\.(?:find|findOne|findById|findFirst|findUnique|findMany|findAll|'
    r'create|update|delete|insert|select|query|execute|run|fetch|get|save|'
    r'count|aggregate|raw|raw_sql|select_related|prefetch_related|load|'
    r'objects|filter|first|last|all|exists)\s*\(',
    re.IGNORECASE,
)

# Loop opens by language family
LOOP_OPENERS = [
    re.compile(r'^\s*for\s*\('),                          # JS/TS/Java/Go for(;;)
    re.compile(r'^\s*for\s+\w+\s+in\s+'),                  # Python/JS for...in/of
    re.compile(r'^\s*for\s+\w+\s+of\s+'),                  # JS for...of
    re.compile(r'^\s*while\s*\('),                         # while
    re.compile(r'^\s*while\s+'),                           # Python/Ruby while
    re.compile(r'\.forEach\s*\('),                          # JS .forEach
    re.compile(r'\.map\s*\(\s*(?:async\s*)?\(?\w*\)?\s*=>'), # JS .map(item =>
    re.compile(r'\.filter\s*\(\s*(?:async\s*)?\(?\w*\)?\s*=>'),
    re.compile(r'\.reduce\s*\('),
]

LOOP_CLOSER = re.compile(r'^\s*\}')

def in_loop(lines, i):
    """crude check: is line i inside an open loop within last 30 lines?"""
    depth = 0
    for j in range(max(0, i-30), i):
        for opener in LOOP_OPENERS:
            if opener.search(lines[j]):
                depth += 1
                break
    # not perfect but works as heuristic
    return depth > 0

results = []
project_root = Path('.')
files = []
for path in project_root.rglob('*'):
    if path.is_file() and path.suffix in EXTS:
        if any(p in path.parts for p in SKIP_DIRS): continue
        files.append(path)

for f in files:
    try:
        text = f.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if not ORM_CALL.search(ln): continue
        if in_loop(lines, i):
            ctx_start = max(0, i-5)
            ctx_end = min(len(lines), i+3)
            ctx = '\n'.join(lines[ctx_start:ctx_end])
            results.append((str(f), i+1, ctx))

print('# N+1 suspects (heuristic)')
print(f'Generated: {os.popen("date -Iseconds").read().strip()}')
print(f'Total suspects: {len(results)}')
print()
print('Каждый suspect требует ручной проверки. Heuristic ловит ORM-call в области, где выше по тексту есть открытый loop. Possible false positives — closure без захвата итеративной переменной, явный prefetch.')
print()

for f, line, ctx in results[:200]:
    print(f'## {f}:{line}')
    print()
    print('```')
    print(ctx)
    print('```')
    print()

if len(results) > 200:
    print(f'…truncated, {len(results) - 200} more')
PY

ok "n_plus_one_suspects.md written"
