#!/usr/bin/env python3
"""Find string status/type columns without CHECK constraint or enum."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, append_finding, write_evidence, evidence_path

ENUM_LIKE_NAMES = {'status', 'state', 'type', 'kind', 'category', 'mode'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='02')
    args = ap.parse_args()

    ss = evidence_path('01', 'schema_summary.json')
    if not ss.exists():
        return 0
    data = json.loads(ss.read_text())
    hits = []
    for t in data.get('tables', []):
        for c in t.get('columns', []):
            cname = c['name'].lower()
            ctype = c.get('type', '').lower()
            if any(x in cname for x in ENUM_LIKE_NAMES) and \
               ('string' in ctype or 'varchar' in ctype or 'text' in ctype):
                hits.append((t['name'], c['name'], t['source_file'], t['line']))

    md = ['# Status/Type без CHECK', '', f'Total: {len(hits)}', '']
    md.append('| Table | Column | Source |')
    md.append('|-------|--------|--------|')
    for t, c, f, ln in hits[:50]:
        md.append(f'| {t} | {c} | {f}:{ln} |')

    write_evidence(args.phase, 'status_without_check.md', '\n'.join(md))

    if hits:
        append_finding({
            'phase': args.phase,
            'category': 'schema',
            'subcategory': 'status-no-check',
            'severity': 'medium',
            'confidence': 'medium',
            'title': f'Status/type как строки без CHECK constraint в {len(hits)} полях',
            'location': {'file': hits[0][2], 'lines': str(hits[0][3])},
            'evidence': f'String status/type/kind колонки без enum/CHECK: {len(hits)}. Sample: {hits[:5]}',
            'impact': 'Возможны invalid значения, пропуск ошибок до runtime.',
            'recommendation': 'Использовать ENUM (PG) или CHECK constraint, либо lookup table (Karwin §10).',
            'effort': 'M',
            'references': ['Karwin §10 31 Flavors', 'Date §10 Constraints'],
        })

    print(f'OK: status-no-check — {len(hits)} hits')
    return 0


if __name__ == '__main__':
    sys.exit(main())
