#!/usr/bin/env python3
"""Verify that every finding's location.file:lines resolves to a real file with given line range.
Skips db_object-only findings (e.g. live-mode pg_stat_*).
"""
import json
import sys
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    args = ap.parse_args()

    root = Path(args.root)
    p = root / 'audit/findings.jsonl'
    if not p.exists():
        print('audit/findings.jsonl missing')
        return 1

    errors = 0
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            f = json.loads(line)
        except json.JSONDecodeError:
            continue

        loc = f.get('location') or {}
        fpath = loc.get('file', '')
        flines = loc.get('lines', '')
        if not fpath:
            continue
        full = root / fpath
        if not full.exists():
            print(f'  ERR {f.get("id","?")}: file not found: {fpath}')
            errors += 1
            continue
        if not flines:
            continue
        try:
            if '-' in flines:
                a, b = flines.split('-', 1)
                a, b = int(a), int(b)
            else:
                a = b = int(flines)
        except ValueError:
            print(f'  ERR {f.get("id","?")}: bad lines format: {flines}')
            errors += 1
            continue
        try:
            total = sum(1 for _ in full.open('r', encoding='utf-8', errors='ignore'))
        except Exception as e:
            print(f'  ERR {f.get("id","?")}: cannot read {fpath}: {e}')
            errors += 1
            continue
        if a < 1 or b > total:
            print(f'  ERR {f.get("id","?")}: lines {flines} out of range (file has {total} lines): {fpath}')
            errors += 1

    if errors:
        print(f'FAIL: {errors} unresolved citation(s)')
        return 1
    print('OK: all citations resolve')
    return 0


if __name__ == '__main__':
    sys.exit(main())
