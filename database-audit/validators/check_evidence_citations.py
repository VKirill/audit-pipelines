#!/usr/bin/env python3
"""Verify each finding's location.file:lines resolves to an existing file with given line range.
Honors AUDIT_DIR + PROJECT_ROOT env vars."""
import json
import os
import sys
from pathlib import Path


def main():
    audit_dir = Path(os.environ.get('AUDIT_DIR', 'audit'))
    project_root = Path(os.environ.get('PROJECT_ROOT', '.'))
    findings_path = audit_dir / 'findings.jsonl'
    if not findings_path.exists():
        print(f'{findings_path} missing')
        return 1

    errors = 0
    for i, line in enumerate(findings_path.read_text().splitlines(), 1):
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
        full = project_root / fpath
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
