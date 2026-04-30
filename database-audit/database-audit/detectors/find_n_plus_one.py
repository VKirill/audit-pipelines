#!/usr/bin/env python3
"""N+1 detection with confidence ranking.

Sources:
- manifest.hints.n_plus_one_candidates (high-priority, AI-vetted)
- heuristic scan over query_files.code_globs (lower confidence)

Confidence levels (lib/stack_aware.py):
  high   — ORM call in explicit for-loop with iterator-dependent arg
  medium — Promise.all(map()) or async iterator
  low    — ORM call in loop without iterator dependency (likely false positive)
"""
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

PROMISE_ALL_MAP = re.compile(r'Promise\.all\s*\(\s*\w+\.map\s*\(', re.IGNORECASE)
EXPLICIT_FOR_LOOP = re.compile(r'^\s*(?:for\s*\(|for\s+\w+\s+(?:of|in)\s+|while\s*[\(\s])')
FOREACH = re.compile(r'\.forEach\s*\(')
ARRAY_MAP_ARROW = re.compile(r'\.map\s*\(\s*(?:async\s*)?\(?(\w+)\)?\s*=>')


def rank_confidence(lines, idx, ln):
    """Determine confidence level for an ORM call at line idx."""
    # Look at last 30 lines for loop opener
    window = lines[max(0, idx-30):idx]
    window_str = '\n'.join(window)

    # Highest signal: Promise.all(arr.map(...)) above
    if PROMISE_ALL_MAP.search(window_str):
        return 'medium', 'parallel-n-plus-one (Promise.all + map)'

    # Look for `.map(item =>` and check if `item` (or single-arg name) is used in current line
    arrow_matches = list(ARRAY_MAP_ARROW.finditer(window_str))
    if arrow_matches:
        last_var = arrow_matches[-1].group(1)
        if last_var and last_var in ln:
            return 'high', f'orm call in .map(({last_var}) => ...) using iterator var'
        return 'medium', 'orm call in .map() but iterator var unclear'

    # Explicit for / while loop
    has_explicit_loop = any(EXPLICIT_FOR_LOOP.match(w) for w in window)
    if has_explicit_loop:
        # Look for variable from `for (var ... of arr)`
        for w in reversed(window):
            for_m = re.match(r'^\s*for\s+(?:const|let|var)?\s*(\w+)\s+(?:of|in)\s+(\w+)', w)
            if for_m:
                iter_var = for_m.group(1)
                if iter_var and iter_var in ln:
                    return 'high', f'orm call in for...of using iterator var "{iter_var}"'
                return 'low', 'orm call in for-loop without iterator dependency'
        return 'medium', 'orm call inside loop scope'

    # forEach
    if FOREACH.search(window_str):
        return 'medium', 'orm call in .forEach()'

    return None, None  # not in any loop


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

    # 1) Manifest hints (treated as 'high' confidence)
    for h in hinted:
        f = h.get('file', '')
        ln = h.get('lines', '')
        seen.add((f, ln))
        suspects.append({
            'file': f, 'lines': ln, 'source': 'manifest',
            'symbol': h.get('symbol', ''), 'confidence': h.get('confidence_hint', 'high'),
            'reason': 'manifest-vetted',
            'context': '',
        })

    # 2) Heuristic scan with confidence ranking
    for rel in iter_files(code_globs, excludes, project_root):
        full = project_root / rel
        try:
            text = full.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if not ORM_CALL.search(ln):
                continue
            confidence, reason = rank_confidence(lines, i, ln)
            if not confidence:
                continue
            key = (str(rel), str(i+1))
            if key in seen: continue
            seen.add(key)
            ctx_start = max(0, i-3); ctx_end = min(len(lines), i+2)
            suspects.append({
                'file': str(rel), 'lines': str(i+1), 'source': 'heuristic',
                'symbol': '', 'confidence': confidence, 'reason': reason,
                'context': '\n'.join(lines[ctx_start:ctx_end]),
            })

    # Sort by confidence (high→medium→low)
    order = {'high': 0, 'medium': 1, 'low': 2}
    suspects.sort(key=lambda s: order.get(s['confidence'], 9))

    out = ['# N+1 suspects (with confidence ranking)', '',
           f'Total: {len(suspects)} '
           f'(high: {sum(1 for s in suspects if s["confidence"]=="high")}, '
           f'medium: {sum(1 for s in suspects if s["confidence"]=="medium")}, '
           f'low: {sum(1 for s in suspects if s["confidence"]=="low")})', '']
    for s in suspects[:300]:
        out.append(f'## [{s["confidence"]}] {s["file"]}:{s["lines"]} ({s["source"]})')
        if s.get('symbol'): out.append(f'symbol: {s["symbol"]}')
        out.append(f'reason: {s["reason"]}')
        if s.get('context'):
            out.append('```')
            out.append(s['context'])
            out.append('```')
        out.append('')
    p = write_evidence(args.phase, 'n_plus_one_suspects.md', '\n'.join(out))
    print(f'OK: {p} ({len(suspects)} suspects)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
