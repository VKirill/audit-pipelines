#!/usr/bin/env python3
"""Extract a flat schema summary by reading manifest.paths.schema_files.
Writes evidence/01_inventory/schema_summary.json + models_list.md.
Pure manifest-driven; no path heuristics."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, write_evidence, get_paths


def parse_prisma(text, source_file):
    tables = []
    for m in re.finditer(r'model\s+(\w+)\s*\{([^}]+)\}', text):
        name = m.group(1)
        body = m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('//'):
                continue
            if ln.startswith('@@id'):
                inner = re.search(r'\[([^\]]+)\]', ln)
                if inner: pk = [c.strip() for c in inner.group(1).split(',')]
                continue
            if ln.startswith('@@index') or ln.startswith('@@unique'):
                inner = re.search(r'\[([^\]]+)\]', ln)
                if inner:
                    idx.append({'columns': [c.strip() for c in inner.group(1).split(',')],
                                'unique': ln.startswith('@@unique')})
                continue
            if ln.startswith('@@'):
                continue
            mc = re.match(r'(\w+)\s+(\S+)(.*)$', ln)
            if not mc: continue
            cname, ctype, rest = mc.group(1), mc.group(2), mc.group(3)
            col = {'name': cname, 'type': ctype, 'nullable': '?' in ctype}
            if '@id' in rest: pk.append(cname)
            if '@unique' in rest: idx.append({'columns': [cname], 'unique': True})
            if '@default' in rest:
                d = re.search(r'@default\(([^)]+)\)', rest)
                if d: col['default'] = d.group(1)
            r = re.search(r'@relation\(([^)]+)\)', rest)
            if r:
                fk_cols = re.search(r'fields:\s*\[([^\]]+)\]', r.group(1))
                if fk_cols:
                    for c in fk_cols.group(1).split(','):
                        fks.append({'column': c.strip()})
                else:
                    fks.append({'column': cname, 'raw': r.group(1)})
            cols.append(col)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'prisma', 'columns': cols, 'pk': pk, 'fks': fks, 'indexes': idx})
    return tables


def parse_sqlalchemy(text, source_file):
    tables = []
    for m in re.finditer(r'class\s+(\w+)\s*\([^)]*Base[^)]*\)\s*:\s*\n((?:    .+\n)+)', text):
        name = m.group(1)
        body = m.group(2)
        line = text[:m.start()].count('\n') + 1
        tn = re.search(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]", body)
        tbl = tn.group(1) if tn else name
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            mc = re.search(r'(\w+)\s*[:=]\s*(?:Mapped\[[^\]]*\]\s*=\s*)?(?:mapped_column|Column)\s*\(([^)]+)\)', ln)
            if not mc: continue
            cname, args = mc.group(1), mc.group(2)
            col = {'name': cname, 'type': args.split(',')[0].strip(),
                    'nullable': 'nullable=False' not in args}
            if 'primary_key=True' in args: pk.append(cname)
            if 'unique=True' in args: idx.append({'columns': [cname], 'unique': True})
            if 'index=True' in args: idx.append({'columns': [cname], 'unique': False})
            fk = re.search(r"ForeignKey\(['\"]([^'\"]+)['\"]", args)
            if fk: fks.append({'column': cname, 'ref': fk.group(1)})
            cols.append(col)
        tables.append({'name': tbl, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'sqlalchemy', 'columns': cols, 'pk': pk, 'fks': fks, 'indexes': idx})
    return tables


def parse_django(text, source_file):
    tables = []
    for m in re.finditer(r'class\s+(\w+)\s*\([^)]*models\.Model[^)]*\)\s*:\s*\n((?:    .+\n)+)', text):
        name = m.group(1)
        body = m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            mc = re.search(r'(\w+)\s*=\s*models\.(\w+Field)\s*\(([^)]*)\)', ln)
            if not mc: continue
            cname, ftype, args = mc.group(1), mc.group(2), mc.group(3)
            col = {'name': cname, 'type': ftype, 'nullable': 'null=True' in args}
            if ftype == 'ForeignKey':
                fks.append({'column': cname, 'raw': args})
            if 'primary_key=True' in args: pk.append(cname)
            if 'unique=True' in args: idx.append({'columns': [cname], 'unique': True})
            if 'db_index=True' in args: idx.append({'columns': [cname], 'unique': False})
            cols.append(col)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'django', 'columns': cols, 'pk': pk, 'fks': fks, 'indexes': idx})
    return tables


def parse_raw_sql(text, source_file):
    tables = []
    for m in re.finditer(r'CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+["`]?(\w+)["`]?\s*\(([^;]+?)\)\s*;',
                         text, re.IGNORECASE | re.DOTALL):
        name, body = m.group(1), m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for ln in body.split(','):
            ln = ln.strip()
            if not ln: continue
            up = ln.upper()
            if up.startswith('PRIMARY KEY'):
                inner = re.search(r'\(([^)]+)\)', ln)
                if inner: pk = [c.strip().strip('"`') for c in inner.group(1).split(',')]
            elif up.startswith('FOREIGN KEY'):
                fks.append({'raw': ln})
            elif up.startswith('UNIQUE'):
                inner = re.search(r'\(([^)]+)\)', ln)
                if inner: idx.append({'columns': [c.strip().strip('"`') for c in inner.group(1).split(',')], 'unique': True})
            else:
                m2 = re.match(r'["`]?(\w+)["`]?\s+(\w+(?:\([^)]*\))?)(.*)$', ln)
                if m2:
                    cname, ctype, rest = m2.group(1), m2.group(2), m2.group(3)
                    cols.append({'name': cname, 'type': ctype, 'nullable': 'NOT NULL' not in rest.upper()})
                    if 'PRIMARY KEY' in rest.upper(): pk.append(cname)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'raw-sql', 'columns': cols, 'pk': pk, 'fks': fks, 'indexes': idx})
    return tables


PARSERS = {
    '.prisma': parse_prisma,
    '.py': lambda t, s: parse_sqlalchemy(t, s) + parse_django(t, s),
    '.sql': parse_raw_sql,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='01')
    args = ap.parse_args()

    m = load_manifest()
    audit_dir, project_root, _, _, _ = get_paths()

    schema_files = paths(m).get('schema_files', []) or []
    if not schema_files:
        print('No schema_files in manifest — skipping')
        return 0

    all_tables = []
    for f in schema_files:
        full = project_root / f
        if not full.exists():
            print(f'  WARN: {f} not found')
            continue
        ext = full.suffix
        parser = PARSERS.get(ext)
        if not parser:
            print(f'  WARN: no parser for {ext}, skipping {f}')
            continue
        text = full.read_text(encoding='utf-8', errors='ignore')
        all_tables.extend(parser(text, f))

    summary = {'tables': all_tables, 'tables_count': len(all_tables)}
    p = write_evidence(args.phase, 'schema_summary.json',
                       json.dumps(summary, indent=2, ensure_ascii=False))
    print(f'OK: {p} ({len(all_tables)} tables)')

    md = ['# Models / Tables', '', '| Table | ORM | Columns | PK | FKs | Indexes | Source |',
          '|-------|-----|---------|-----|------|---------|--------|']
    for t in sorted(all_tables, key=lambda x: x['name']):
        md.append(f"| {t['name']} | {t.get('source_orm','?')} | {len(t['columns'])} | "
                  f"{len(t['pk'])} | {len(t['fks'])} | {len(t['indexes'])} | "
                  f"{t['source_file']}:{t['line']} |")
    write_evidence(args.phase, 'models_list.md', '\n'.join(md))
    return 0


if __name__ == '__main__':
    sys.exit(main())
