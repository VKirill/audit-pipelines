#!/usr/bin/env bash
# Extract a flat schema summary across multiple ORMs.
# Output: JSON to stdout (one object with `tables` array).
# Each table: { name, source_file, line, columns: [...], pk: [...], fks: [...], indexes: [...] }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"

require_cmd python3

OUT_DIR="${EVIDENCE_DIR}/01_inventory"
mkdir -p "$OUT_DIR"

python3 - <<'PY' > "$OUT_DIR/schema_summary.json"
import os, re, json, sys
from pathlib import Path

root = Path('.')
tables = []

def add_table(name, source_file, line, columns=None, pk=None, fks=None, indexes=None, source_orm=None):
    tables.append({
        "name": name,
        "source_file": str(source_file),
        "line": line,
        "source_orm": source_orm,
        "columns": columns or [],
        "pk": pk or [],
        "fks": fks or [],
        "indexes": indexes or [],
    })

# 1. Prisma schema.prisma
for p in root.rglob('schema.prisma'):
    if any(x in p.parts for x in ('node_modules', '.git', 'dist', 'build')): continue
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    # Find blocks: model X { ... }
    for m in re.finditer(r'model\s+(\w+)\s*\{([^}]+)\}', text):
        name = m.group(1)
        body = m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('//') or ln.startswith('@@'):
                # Block-level: @@id, @@unique, @@index, @@map
                if ln.startswith('@@id'):
                    inner = re.search(r'\[([^\]]+)\]', ln)
                    if inner: pk = [c.strip() for c in inner.group(1).split(',')]
                elif ln.startswith('@@index') or ln.startswith('@@unique'):
                    inner = re.search(r'\[([^\]]+)\]', ln)
                    if inner:
                        idx.append({"columns": [c.strip() for c in inner.group(1).split(',')],
                                    "unique": ln.startswith('@@unique')})
                continue
            mc = re.match(r'(\w+)\s+(\S+)(.*)$', ln)
            if not mc: continue
            cname, ctype, rest = mc.group(1), mc.group(2), mc.group(3)
            col = {"name": cname, "type": ctype, "nullable": '?' in ctype}
            if '@id' in rest: pk.append(cname)
            if '@unique' in rest:
                idx.append({"columns": [cname], "unique": True})
            if '@default' in rest:
                d = re.search(r'@default\(([^)]+)\)', rest)
                if d: col['default'] = d.group(1)
            r = re.search(r'@relation\(([^)]+)\)', rest)
            if r:
                fks.append({"column": cname, "raw": r.group(1)})
            cols.append(col)
        add_table(name, p, line, cols, pk, fks, idx, source_orm='prisma')

# 2. SQLAlchemy declarative
for p in root.rglob('*.py'):
    if any(x in p.parts for x in ('venv', '.venv', 'site-packages', '__pycache__', '.git')): continue
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    if 'declarative_base' not in text and 'DeclarativeBase' not in text and 'sqlalchemy' not in text:
        continue
    # class X(Base): ... __tablename__ = 'x'
    for m in re.finditer(r'class\s+(\w+)\s*\([^)]*Base[^)]*\)\s*:\s*\n((?:    .+\n)+)', text):
        name = m.group(1)
        body = m.group(2)
        line = text[:m.start()].count('\n') + 1
        tbl_name = name
        tn = re.search(r"__tablename__\s*=\s*['\"]([^'\"]+)['\"]", body)
        if tn: tbl_name = tn.group(1)
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            mc = re.search(r'(\w+)\s*[:=]\s*(?:Mapped\[[^\]]*\]\s*=\s*)?(?:mapped_column|Column)\s*\(([^)]+)\)', ln)
            if not mc: continue
            cname, args = mc.group(1), mc.group(2)
            col = {"name": cname, "type": args.split(',')[0].strip(), "nullable": 'nullable=True' in args or 'nullable' not in args}
            if 'primary_key=True' in args: pk.append(cname)
            if 'unique=True' in args: idx.append({"columns": [cname], "unique": True})
            if 'index=True' in args: idx.append({"columns": [cname], "unique": False})
            fk = re.search(r"ForeignKey\(['\"]([^'\"]+)['\"]", args)
            if fk:
                fks.append({"column": cname, "ref": fk.group(1)})
            cols.append(col)
        add_table(tbl_name, p, line, cols, pk, fks, idx, source_orm='sqlalchemy')

# 3. Django models
for p in root.rglob('models.py'):
    if any(x in p.parts for x in ('venv', '.venv', 'site-packages', '__pycache__', '.git')): continue
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    for m in re.finditer(r'class\s+(\w+)\s*\([^)]*models\.Model[^)]*\)\s*:\s*\n((?:    .+\n)+)', text):
        name = m.group(1)
        body = m.group(2)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for ln in body.splitlines():
            mc = re.search(r'(\w+)\s*=\s*models\.(\w+Field)\s*\(([^)]*)\)', ln)
            if not mc: continue
            cname, ftype, args = mc.group(1), mc.group(2), mc.group(3)
            col = {"name": cname, "type": ftype, "nullable": 'null=True' in args}
            if ftype == 'ForeignKey':
                fks.append({"column": cname, "raw": args})
            if 'primary_key=True' in args: pk.append(cname)
            if 'unique=True' in args: idx.append({"columns": [cname], "unique": True})
            if 'db_index=True' in args: idx.append({"columns": [cname], "unique": False})
            cols.append(col)
        add_table(name, p, line, cols, pk, fks, idx, source_orm='django')

# 4. TypeORM entities
for p in list(root.rglob('*.entity.ts')) + list(root.rglob('*.model.ts')):
    if any(x in p.parts for x in ('node_modules', '.git', 'dist', 'build')): continue
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    for m in re.finditer(r'@Entity\([^)]*\)\s*\n.*?export\s+class\s+(\w+)', text, re.DOTALL):
        name = m.group(1)
        line = text[:m.start()].count('\n') + 1
        # crude column extraction
        cols, pk, fks, idx = [], [], [], []
        for col_m in re.finditer(r'@(?:PrimaryGeneratedColumn|PrimaryColumn|Column|ManyToOne|OneToMany|ManyToMany|OneToOne|JoinColumn|Index|Unique)\([^)]*\)\s*\n\s*(\w+)', text):
            cname = col_m.group(1)
            col = {"name": cname, "type": "ts-inferred"}
            cols.append(col)
            if '@PrimaryGeneratedColumn' in text[col_m.start():col_m.end()] or '@PrimaryColumn' in text[col_m.start():col_m.end()]:
                pk.append(cname)
        add_table(name, p, line, cols, pk, fks, idx, source_orm='typeorm')

# 5. Drizzle (pgTable / mysqlTable / sqliteTable)
for p in root.rglob('*.ts'):
    if any(x in p.parts for x in ('node_modules', '.git', 'dist', 'build')): continue
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    if 'drizzle-orm' not in text and 'pgTable' not in text and 'mysqlTable' not in text and 'sqliteTable' not in text:
        continue
    for m in re.finditer(r"export\s+const\s+(\w+)\s*=\s*(pgTable|mysqlTable|sqliteTable)\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*\{([^}]+)\}", text):
        var_name, table_kind, table_name, body = m.group(1), m.group(2), m.group(3), m.group(4)
        line = text[:m.start()].count('\n') + 1
        cols, pk, fks, idx = [], [], [], []
        for col_m in re.finditer(r'(\w+)\s*:\s*(\w+)\(([^)]*)\)([^,]*)', body):
            cname, ctype, args, suffix = col_m.group(1), col_m.group(2), col_m.group(3), col_m.group(4)
            col = {"name": cname, "type": ctype}
            if '.primaryKey()' in suffix: pk.append(cname)
            if '.unique()' in suffix: idx.append({"columns": [cname], "unique": True})
            if '.references(' in suffix: fks.append({"column": cname, "raw": suffix})
            cols.append(col)
        add_table(table_name, p, line, cols, pk, fks, idx, source_orm='drizzle')

# 6. Raw SQL CREATE TABLE in *.sql files
for p in root.rglob('*.sql'):
    if any(x in p.parts for x in ('node_modules', '.git')): continue
    try:
        text = p.read_text(encoding='utf-8', errors='ignore')
    except Exception: continue
    for m in re.finditer(r'CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+["`]?(\w+)["`]?\s*\(([^;]+?)\)\s*;', text, re.IGNORECASE | re.DOTALL):
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
                fks.append({"raw": ln})
            elif up.startswith('UNIQUE'):
                inner = re.search(r'\(([^)]+)\)', ln)
                if inner:
                    idx.append({"columns": [c.strip().strip('"`') for c in inner.group(1).split(',')], "unique": True})
            else:
                m2 = re.match(r'["`]?(\w+)["`]?\s+(\w+(?:\([^)]*\))?)(.*)$', ln)
                if m2:
                    cname, ctype, rest = m2.group(1), m2.group(2), m2.group(3)
                    cols.append({"name": cname, "type": ctype, "nullable": 'NOT NULL' not in rest.upper()})
                    if 'PRIMARY KEY' in rest.upper(): pk.append(cname)
        add_table(name, p, line, cols, pk, fks, idx, source_orm='raw-sql')

print(json.dumps({"tables": tables, "tables_count": len(tables)}, indent=2))
PY

ok "schema_summary.json written ($OUT_DIR/schema_summary.json)"

# Render markdown summary
python3 - <<'PY' > "$OUT_DIR/models_list.md"
import json
data = json.load(open('audit/evidence/01_inventory/schema_summary.json'))
print('# Models / Tables')
print()
print('| Table | ORM | Columns | PK | FKs | Indexes | Source |')
print('|-------|-----|---------|-----|------|---------|--------|')
for t in sorted(data['tables'], key=lambda x: x['name']):
    print(f"| {t['name']} | {t.get('source_orm','?')} | {len(t['columns'])} | {len(t['pk'])} | {len(t['fks'])} | {len(t['indexes'])} | {t['source_file']}:{t['line']} |")
PY

ok "models_list.md written"
