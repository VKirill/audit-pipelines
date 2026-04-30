#!/usr/bin/env python3
"""FK without index. Primary source: hints.missing_fk_indexes.
Fallback: parse schema_summary.json from extract_schema."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence, evidence_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='03')
    args = ap.parse_args()

    m = load_manifest()
    hinted = hints(m).get('missing_fk_indexes', []) or []

    findings_data = []

    if hinted:
        for h in hinted:
            findings_data.append({
                'table': h['table'],
                'column': h['column'],
                'file': h['file'],
                'lines': h['lines'],
                'ref': h.get('referenced_table', ''),
                'source': 'manifest'
            })
    else:
        # Fallback: parse schema_summary.json
        ss = evidence_path('01', 'schema_summary.json')
        if not ss.exists():
            print('schema_summary.json not found — run extract_schema first')
            return 1
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
            missing = fk_cols - idx_cols
            for col in missing:
                findings_data.append({
                    'table': t['name'], 'column': col,
                    'file': t['source_file'], 'lines': str(t['line']),
                    'ref': '', 'source': 'schema-derived'
                })

    md = ['# FK without index', '']
    if not findings_data:
        md.append('No FK-without-index detected (declared schema).')
        md.append('Live verification through pg_indexes recommended in live mode.')
    else:
        md.append('| Table | Column | Source | File:Lines |')
        md.append('|-------|--------|--------|-------------|')
        for f in findings_data:
            md.append(f"| {f['table']} | {f['column']} | {f['source']} | {f['file']}:{f['lines']} |")

    write_evidence(args.phase, 'fk_without_index.md', '\n'.join(md))

    for f in findings_data:
        finding = {
            'phase': args.phase,
            'category': 'index',
            'subcategory': 'fk-no-index',
            'severity': 'high',
            'confidence': 'high' if f['source'] == 'manifest' else 'medium',
            'title': f'FK без индекса: {f["table"]}.{f["column"]}',
            'location': {'file': f['file'], 'lines': f['lines'],
                         'symbol': f['table'], 'db_object': f"{f['table']}.{f['column']}"},
            'evidence': (f'В файле {f["file"]}:{f["lines"]} объявлен FK на '
                         f'{f["table"]}.{f["column"]}, но соответствующий индекс на этой колонке '
                         f'не задекларирован. Source: {f["source"]}.'),
            'confidence_rationale': (f'Schema-level analysis показывает: колонка является FK, '
                                     f'но не входит в список indexes таблицы. PostgreSQL не создаёт '
                                     f'индекс на FK автоматически (в отличие от MySQL InnoDB), что '
                                     f'делает JOIN на этой колонке seq scan.'),
            'impact': ('JOIN и каскадные удаления требуют seq scan по таблице. Под нагрузкой — '
                       'p99 latency и блокировки.'),
            'recommendation': (f'Добавить индекс на {f["table"]}.{f["column"]}. В PostgreSQL — '
                               f'CREATE INDEX CONCURRENTLY для production без блокировки.'),
            'effort': 'S',
            'references': [
                "Winand, Use the Index, Luke, Ch. 4 The Join Operation",
                "Karwin, SQL Antipatterns §4 Keyless Entry"
            ],
        }
        append_finding(finding)

    print(f'OK: {len(findings_data)} FK-no-index findings')
    return 0


if __name__ == '__main__':
    sys.exit(main())
