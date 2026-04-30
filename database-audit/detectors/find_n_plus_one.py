#!/usr/bin/env python3
"""N+1 detection. Uses manifest.hints.n_plus_one_candidates as primary source.
Adds heuristic scan as fallback. Writes to evidence/04_query_patterns/n_plus_one_suspects.md."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, hints, write_evidence, get_paths, iter_files

ORM_CALL = re.compile(
    r'\b(prisma|db|orm|repo|repository|session|cursor|conn|connection)\b\s*'
    r'(?:\.\w+)*\.(?:find|findOne|findById|findFirst|findUnique|findMany|findAll|'
    r'create|update|delete|insert|select|query|execute|run|fetch|get|save|'
    r'count|aggregate|raw|raw_sql|select_related|prefetch_related|load|'
    r'objects|filter|first|last|all|exists)\s*\(',
    re.IGNORECASE,
)
LOOP_OPENERS = [
    re.compile(r'^\s*for\s*\('),
    re.compile(r'^\s*for\s+\w+\s+in\s+'),
    re.compile(r'^\s*for\s+\w+\s+of\s+'),
    re.compile(r'^\s*while\s*[\(\s]'),
    re.compile(r'\.forEach\s*\('),
    re.compile(r'\.map\s*\(\s*(?:async\s*)?\(?\w*\)?\s*=>'),
]


def in_loop(lines, i):
    for j in range(max(0, i-30), i):
        for op in LOOP_OPENERS:
            if op.search(lines[j]):
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='04')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    hinted = hints(m).get('n_plus_one_candidates', []) or []

    qf = paths(m).get('query_files', {}) or {}
    code_globs = qf.get('code_globs', ['**/*.ts', '**/*.tsx', '**/*.py', '**/*.go'])
    excludes = qf.get('excludes', ['node_modules', '.git', 'dist', 'build', '.venv'])

    suspects = []
    seen = set()

    # 1) From manifest hints (high-priority, pre-validated by AI)
    for h in hinted:
        f = h.get('file', '')
        ln = h.get('lines', '')
        seen.add((f, ln))
        suspects.append({'file': f, 'lines': ln, 'source': 'manifest',
                          'symbol': h.get('symbol', ''), 'context': ''})

    # 2) Heuristic scan (best-effort)
    for rel in iter_files(code_globs, excludes, project_root):
        full = project_root / rel
        try:
            text = full.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if not ORM_CALL.search(ln): continue
            if not in_loop(lines, i): continue
            ctx_start = max(0, i-3)
            ctx_end = min(len(lines), i+2)
            ctx = '\n'.join(lines[ctx_start:ctx_end])
            key = (str(rel), f'{i+1}')
            if key in seen: continue
            seen.add(key)
            suspects.append({'file': str(rel), 'lines': str(i+1), 'source': 'heuristic',
                             'symbol': '', 'context': ctx})

    out = ['# N+1 suspects', '',
           f'Total: {len(suspects)} (manifest-hinted: {sum(1 for s in suspects if s["source"]=="manifest")})',
           '']
    for s in suspects[:300]:
        out.append(f'## {s["file"]}:{s["lines"]} [{s["source"]}]')
        if s['symbol']:
            out.append(f'symbol: {s["symbol"]}')
        if s['context']:
            out.append('```')
            out.append(s['context'])
            out.append('```')
        out.append('')

    p = write_evidence(args.phase, 'n_plus_one_suspects.md', '\n'.join(out))
    print(f'OK: {p} ({len(suspects)} suspects)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
