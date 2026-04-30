#!/usr/bin/env python3
"""Find foreign keys without index (declared in schema).

Reads `audit/evidence/01_inventory/schema_summary.json` produced by extract_schema_summary.sh.
Outputs markdown to stdout.

Heuristic: a column referenced by an FK that does NOT appear in any index for that table -> suspect.

Note: in MySQL InnoDB, FKs auto-create an index. In PostgreSQL — they do NOT. In Mongo — no FKs at all.
This script reports "declared" missing indexes; live mode in run_external_tools.sh adds reality check.
"""
import json
import sys
import argparse
import re
from pathlib import Path


def fk_columns(t):
    cols = set()
    for fk in t.get('fks', []):
        if 'column' in fk:
            cols.add(fk['column'])
        elif 'raw' in fk:
            m = re.search(r'fields:\s*\[([^\]]+)\]', fk['raw'])
            if m:
                for c in m.group(1).split(','):
                    cols.add(c.strip().strip('"\''))
    return cols


def indexed_columns(t):
    cols = set()
    for c in t.get('pk', []):
        cols.add(c)
    for idx in t.get('indexes', []):
        if idx.get('columns'):
            cols.add(idx['columns'][0])
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--schema', default='audit/evidence/01_inventory/schema_summary.json')
    args = ap.parse_args()

    p = Path(args.schema)
    if not p.exists():
        print(f"# FK missing index — schema_summary.json not found ({p})")
        return 0
    data = json.loads(p.read_text())

    findings = []
    for t in data.get('tables', []):
        fks = fk_columns(t)
        idx = indexed_columns(t)
        missing = fks - idx
        if missing:
            findings.append({
                'table': t['name'],
                'missing': sorted(missing),
                'source_file': t['source_file'],
                'line': t['line'],
                'orm': t.get('source_orm', '?'),
            })

    print('# Missing indexes on foreign keys (declared)')
    print()
    print(f'Total tables analyzed: {len(data.get("tables", []))}')
    print(f'Tables with missing FK indexes: {len(findings)}')
    print()
    if not findings:
        print('No declared FK missing index detected. Live-mode verification (pg_indexes / INFORMATION_SCHEMA) recommended for confirmation.')
        return 0

    print('| Table | FK columns without index | Source | ORM | Note |')
    print('|-------|--------------------------|--------|-----|------|')
    for f in findings:
        note = ''
        if f['orm'] == 'sqlalchemy':
            note = 'SQLAlchemy: index=True missing on ForeignKey()'
        elif f['orm'] == 'prisma':
            note = 'Prisma: add @@index([col]) or @relation(... onDelete...)'
        elif f['orm'] == 'django':
            note = 'Django: ForeignKey indexes by default; check db_index in Meta'
        elif f['orm'] == 'typeorm':
            note = 'TypeORM: add @Index() on column or @JoinColumn'
        print(f"| {f['table']} | {', '.join(f['missing'])} | {f['source_file']}:{f['line']} | {f['orm']} | {note} |")

    return 0


if __name__ == '__main__':
    sys.exit(main())
