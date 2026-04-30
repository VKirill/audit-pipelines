#!/usr/bin/env python3
"""Extract flat schema summary from manifest.paths.schema_files.
Multi-ORM: Prisma, SQLAlchemy, Django, TypeORM, Drizzle, Mongoose,
Sequelize, GORM, ActiveRecord, Hibernate, raw SQL.

Output: audit/evidence/01_*/schema_summary.json + models_list.md
"""
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
        name, body = m.group(1), m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('//'): continue
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
            if ln.startswith('@@'): continue
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
        name, body = m.group(1), m.group(2)
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
        name, body = m.group(1), m.group(2)
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


def parse_typeorm(text, source_file):
    tables = []
    for m in re.finditer(r'@Entity\([^)]*\)\s*\n.*?export\s+class\s+(\w+)', text, re.DOTALL):
        name = m.group(1)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for col_m in re.finditer(
                r'@(?:PrimaryGeneratedColumn|PrimaryColumn|Column|ManyToOne|OneToMany|ManyToMany|OneToOne|JoinColumn|Index|Unique)\([^)]*\)\s*\n\s*(\w+)',
                text):
            cname = col_m.group(1)
            cols.append({'name': cname, 'type': 'ts-inferred'})
            if '@PrimaryGeneratedColumn' in text[col_m.start():col_m.end()] or \
               '@PrimaryColumn' in text[col_m.start():col_m.end()]:
                pk.append(cname)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'typeorm', 'columns': cols, 'pk': pk, 'fks': fks, 'indexes': idx})
    return tables


def parse_drizzle(text, source_file):
    tables = []
    for m in re.finditer(
            r"export\s+const\s+(\w+)\s*=\s*(pgTable|mysqlTable|sqliteTable)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*\{([^}]+)\}",
            text):
        var_name, table_kind, table_name, body = m.group(1), m.group(2), m.group(3), m.group(4)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for col_m in re.finditer(r'(\w+)\s*:\s*(\w+)\(([^)]*)\)([^,]*)', body):
            cname, ctype, args, suffix = col_m.group(1), col_m.group(2), col_m.group(3), col_m.group(4)
            cols.append({'name': cname, 'type': ctype})
            if '.primaryKey()' in suffix: pk.append(cname)
            if '.unique()' in suffix: idx.append({'columns': [cname], 'unique': True})
            if '.references(' in suffix: fks.append({'column': cname, 'raw': suffix})
        tables.append({'name': table_name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'drizzle', 'columns': cols, 'pk': pk, 'fks': fks, 'indexes': idx})
    return tables


def parse_mongoose(text, source_file):
    """Parse Mongoose schemas: new mongoose.Schema({field: {type: ..., ...}})"""
    tables = []
    # Simple pattern: const NameSchema = new mongoose.Schema({...})
    for m in re.finditer(r'(?:const|let|var)\s+(\w+)Schema\s*=\s*new\s+(?:mongoose\.)?Schema\s*\(\s*\{', text):
        name = m.group(1)
        line = text[:m.start()].count('\n') + 1
        # find matching closing brace (rough)
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            i += 1
        body = text[start:i-1]
        cols = []
        # field: {type: X, ...} or field: X
        for fm in re.finditer(r'(\w+)\s*:\s*\{[^}]*type:\s*(\w+)([^,}]*)', body):
            fname, ftype = fm.group(1), fm.group(2)
            cols.append({'name': fname, 'type': ftype})
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'mongoose', 'columns': cols, 'pk': ['_id'],
                        'fks': [], 'indexes': []})
    return tables


def parse_sequelize(text, source_file):
    """Parse Sequelize: Model.init({fields}, {sequelize}) or sequelize.define('Name', {fields})"""
    tables = []
    # sequelize.define('Name', { ... })
    for m in re.finditer(r"sequelize\.define\s*\(\s*['\"](\w+)['\"]\s*,\s*\{", text):
        name = m.group(1)
        line = text[:m.start()].count('\n') + 1
        # rough body extraction
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            c = text[i]
            if c == '{': depth += 1
            elif c == '}': depth -= 1
            i += 1
        body = text[start:i-1]
        cols, pk, idx = [], [], []
        for fm in re.finditer(r'(\w+)\s*:\s*\{([^}]*)\}', body):
            fname, args = fm.group(1), fm.group(2)
            type_m = re.search(r'type:\s*(?:DataTypes\.|Sequelize\.)?(\w+)', args)
            if type_m:
                col = {'name': fname, 'type': type_m.group(1)}
                if 'primaryKey: true' in args: pk.append(fname)
                if 'unique: true' in args: idx.append({'columns': [fname], 'unique': True})
                cols.append(col)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'sequelize', 'columns': cols, 'pk': pk,
                        'fks': [], 'indexes': idx})

    # Model.init({...}, {sequelize, modelName: 'X'})
    for m in re.finditer(r'(\w+)\.init\s*\(\s*\{', text):
        cls = m.group(1)
        line = text[:m.start()].count('\n') + 1
        # Skip if already captured by sequelize.define
        if any(t['name'] == cls for t in tables): continue
        tables.append({'name': cls, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'sequelize', 'columns': [], 'pk': [],
                        'fks': [], 'indexes': []})
    return tables


def parse_gorm(text, source_file):
    """Parse GORM Go structs with `gorm:` tags."""
    tables = []
    # type X struct { ... }
    for m in re.finditer(r'type\s+(\w+)\s+struct\s*\{([^}]+)\}', text):
        name, body = m.group(1), m.group(2)
        line = text[:m.start()].count('\n') + 1
        # has gorm tags?
        if 'gorm:' not in body: continue
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('//'): continue
            mc = re.match(r'(\w+)\s+(\*?\w+)\s+`(.+)`', ln)
            if not mc: continue
            fname, ftype, tag = mc.group(1), mc.group(2), mc.group(3)
            col = {'name': fname, 'type': ftype}
            if 'primaryKey' in tag: pk.append(fname)
            if 'uniqueIndex' in tag or 'unique' in tag.lower():
                idx.append({'columns': [fname], 'unique': True})
            if 'index' in tag.lower(): idx.append({'columns': [fname], 'unique': False})
            if 'foreignKey' in tag: fks.append({'column': fname, 'raw': tag})
            cols.append(col)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'gorm', 'columns': cols, 'pk': pk,
                        'fks': fks, 'indexes': idx})
    return tables


def parse_activerecord(text, source_file):
    """Parse Rails schema.rb (ActiveRecord)."""
    tables = []
    # create_table "name" do |t| ... end
    for m in re.finditer(r'create_table\s+["\'](\w+)["\'].*?do\s+\|t\|(.+?)\n\s+end', text, re.DOTALL):
        name, body = m.group(1), m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], ['id'], [], []  # AR auto pk
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('#'): continue
            mc = re.match(r't\.(\w+)\s+["\'](\w+)["\']', ln)
            if mc:
                ftype, fname = mc.group(1), mc.group(2)
                cols.append({'name': fname, 'type': ftype, 'nullable': 'null: false' not in ln})
                if 'primary_key: true' in ln: pk.append(fname)
        # add_index outside create_table
        for im in re.finditer(rf'add_index\s+["\']?{re.escape(name)}["\']?\s*,\s*(?:\[)?\s*["\']?(\w+)["\']?', text):
            idx.append({'columns': [im.group(1)], 'unique': 'unique: true' in im.group(0)})
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'activerecord', 'columns': cols, 'pk': pk,
                        'fks': fks, 'indexes': idx})
    return tables


def parse_hibernate(text, source_file):
    """Parse Hibernate @Entity Java/Kotlin classes."""
    tables = []
    for m in re.finditer(r'@Entity[^\n]*\n(?:@\w+\([^)]*\)\s*\n)*\s*(?:public\s+)?(?:class|data\s+class)\s+(\w+)',
                         text):
        name = m.group(1)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        # Field annotations within class body — rough scan
        # Find @Column / @Id / @JoinColumn followed by field declaration
        for fm in re.finditer(r'@(Column|Id|JoinColumn|GeneratedValue|ManyToOne|OneToMany|OneToOne|ManyToMany|Index)([^;]*?)(?:private|public|protected|val|var)\s+(\w+)\s+(\w+)',
                              text[m.end():m.end()+5000]):
            anno, args, type_kw, fname = fm.group(1), fm.group(2), fm.group(3), fm.group(4)
            col = {'name': fname, 'type': type_kw}
            if anno == 'Id': pk.append(fname)
            if anno == 'JoinColumn': fks.append({'column': fname, 'raw': args})
            cols.append(col)
        tables.append({'name': name, 'source_file': str(source_file), 'line': line,
                        'source_orm': 'hibernate', 'columns': cols, 'pk': pk,
                        'fks': fks, 'indexes': idx})
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


def detect_and_parse(rel_path, project_root):
    """Choose parser based on file content/extension."""
    full = project_root / rel_path
    if not full.exists():
        return []
    ext = full.suffix
    try:
        text = full.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return []

    if ext == '.prisma':
        return parse_prisma(text, rel_path)
    if ext == '.py':
        out = []
        out += parse_sqlalchemy(text, rel_path)
        out += parse_django(text, rel_path)
        return out
    if ext in ('.ts', '.tsx', '.js', '.mjs', '.cjs'):
        out = []
        if 'mongoose' in text: out += parse_mongoose(text, rel_path)
        if 'sequelize.define' in text or '.init(' in text: out += parse_sequelize(text, rel_path)
        if '@Entity' in text: out += parse_typeorm(text, rel_path)
        if 'pgTable(' in text or 'mysqlTable(' in text or 'sqliteTable(' in text:
            out += parse_drizzle(text, rel_path)
        return out
    if ext == '.go':
        return parse_gorm(text, rel_path)
    if ext == '.rb':
        return parse_activerecord(text, rel_path)
    if ext in ('.java', '.kt'):
        return parse_hibernate(text, rel_path)
    if ext == '.sql':
        return parse_raw_sql(text, rel_path)
    return []


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
        all_tables.extend(detect_and_parse(f, project_root))

    summary = {'tables': all_tables, 'tables_count': len(all_tables)}
    p = write_evidence(args.phase, 'schema_summary.json',
                       json.dumps(summary, indent=2, ensure_ascii=False))
    print(f'OK: {p} ({len(all_tables)} tables)')

    md = ['# Models / Tables', '', f'Total: {len(all_tables)}', '',
          '| Table | ORM | Columns | PK | FKs | Indexes | Source |',
          '|-------|-----|---------|-----|------|---------|--------|']
    for t in sorted(all_tables, key=lambda x: x['name']):
        md.append(f"| {t['name']} | {t.get('source_orm','?')} | {len(t['columns'])} | "
                  f"{len(t['pk'])} | {len(t['fks'])} | {len(t['indexes'])} | "
                  f"{t['source_file']}:{t['line']} |")
    write_evidence(args.phase, 'models_list.md', '\n'.join(md))
    return 0


if __name__ == '__main__':
    sys.exit(main())
