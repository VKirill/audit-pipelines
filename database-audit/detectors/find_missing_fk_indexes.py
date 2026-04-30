#!/usr/bin/env python3
"""FK without index — with table-size-aware priority (v5).

Severity scale based on table row count (live mode evidence/live/top_tables_size.txt):
  - >1M rows  → critical
  - 100k-1M   → high
  - 10k-100k  → medium
  - <10k      → low

Static mode: defaults all to high (since size unknown).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence, evidence_path, get_paths


def parse_table_sizes(live_evidence_dir):
    """Parse evidence/live/top_tables_size.txt → {table: row_count}.
    Format expected: tab-separated 'schema.table\tsize\trow_count' or similar."""
    sizes = {}
    p = live_evidence_dir / 'top_tables_size.txt'
    if not p.exists():
        return sizes
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or 'table' in line.lower() and 'size' in line.lower():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        # Try to find a table name + a number (rows or bytes)
        table = parts[0].split('.')[-1]  # strip schema prefix
        nums = [p for p in parts[1:] if p.replace(',', '').replace('.', '').isdigit()]
        if nums:
            sizes[table] = int(nums[0].replace(',', '').split('.')[0])
    return sizes


def severity_by_size(table_name, table_sizes):
    """Map table size → severity."""
    n = table_sizes.get(table_name, 0)
    if n >= 1_000_000:
        return 'critical', f'{n:,} rows — full scan unacceptable'
    if n >= 100_000:
        return 'high', f'{n:,} rows — JOIN performance impact'
    if n >= 10_000:
        return 'medium', f'{n:,} rows — moderate impact'
    if n > 0:
        return 'low', f'{n:,} rows — small table, low impact'
    return 'high', 'table size unknown (static mode default)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='03')
    args = ap.parse_args()

    m = load_manifest()
    audit_dir, project_root, _, _, _ = get_paths()
    live_dir = audit_dir / 'evidence' / 'live'
    table_sizes = parse_table_sizes(live_dir)

    hinted = hints(m).get('missing_fk_indexes', []) or []
    findings_data = []

    if hinted:
        for h in hinted:
            findings_data.append({
                'table': h['table'], 'column': h['column'],
                'file': h['file'], 'lines': h['lines'],
                'ref': h.get('referenced_table', ''), 'source': 'manifest'
            })
    else:
        ss = evidence_path('01', 'schema_summary.json')
        if not ss.exists():
            print('schema_summary.json missing — run extract_schema first'); return 1
        data = json.loads(ss.read_text())
        for t in data.get('tables', []):
            fk_cols = set()
            for fk in t.get('fks', []):
                if fk.get('column'):
                    fk_cols.add(fk['column'])
                elif fk.get('raw'):
                    inner = re.search(r'fields:\s*\[([^\]]+)\]', fk['raw'])
                    if inner:
                        for c in inner.group(1).split(','):
                            fk_cols.add(c.strip().strip('"\''))
            idx_cols = set(t.get('pk', []))
            for ix in t.get('indexes', []):
                if ix.get('columns'):
                    idx_cols.add(ix['columns'][0])
            for col in (fk_cols - idx_cols):
                findings_data.append({
                    'table': t['name'], 'column': col,
                    'file': t['source_file'], 'lines': str(t['line']),
                    'ref': '', 'source': 'schema-derived'
                })

    md = ['# FK without index (v5: table-size-aware priority)', '',
          f'Live evidence: {"available" if table_sizes else "static-mode (size unknown)"}', '',
          '| Table | Column | Severity | Reason | File:Lines |',
          '|-------|--------|----------|--------|------------|']
    for f in findings_data:
        sev, reason = severity_by_size(f['table'], table_sizes)
        md.append(f"| {f['table']} | {f['column']} | {sev} | {reason} | {f['file']}:{f['lines']} |")

    write_evidence(args.phase, 'fk_without_index.md', '\n'.join(md))

    for f in findings_data:
        sev, reason = severity_by_size(f['table'], table_sizes)
        confidence = 'high' if (f['source'] == 'manifest' or table_sizes) else 'medium'
        finding = {
            'phase': args.phase,
            'category': 'index',
            'subcategory': 'fk-no-index',
            'severity': sev,
            'confidence': confidence,
            'title': f'FK без индекса: {f["table"]}.{f["column"]} [{reason}]',
            'location': {'file': f['file'], 'lines': f['lines'],
                         'symbol': f['table'], 'db_object': f"{f['table']}.{f['column']}"},
            'evidence': (f'Файл {f["file"]}:{f["lines"]}: FK на {f["table"]}.{f["column"]}, '
                         f'индекс не задекларирован. {reason}'),
            'confidence_rationale': (f'Schema-level analysis: колонка FK не входит в indexes. '
                                     f'PostgreSQL не создаёт индекс на FK автоматически. '
                                     f'Severity calibrated by row count: {reason}.'),
            'impact': ('JOIN seq scan на этой таблице. Каскадные DELETE долгие. '
                       f'{reason}.'),
            'recommendation': (f'CREATE INDEX CONCURRENTLY ON {f["table"]} ({f["column"]}); '
                               f'(в Prisma: добавить @@index([{f["column"]}]))'),
            'effort': 'S',
            'references': [
                "Winand, Use the Index, Luke, Ch. 4 The Join Operation",
                "Karwin, SQL Antipatterns §4 Keyless Entry"
            ],
        }
        if sev == 'critical':
            finding['exploit_proof'] = (
                f'Таблица {f["table"]} имеет {table_sizes.get(f["table"], "?")} строк. '
                f'Любой JOIN или DELETE через {f["column"]} → seq scan. '
                f'Под нагрузкой p99 latency растёт линейно от размера, '
                f'production deadlocks при каскадных DELETE.'
            )
        append_finding(finding)

    print(f'OK: fk-no-index — {len(findings_data)} findings, '
          f'sizes={"live" if table_sizes else "static"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
