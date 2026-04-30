#!/usr/bin/env python3
"""Detect Json/JSONB columns that look like they should be normalized tables (Karwin §5 EAV)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, append_finding, write_evidence, evidence_path

JSON_TYPES = {'json', 'jsonb', 'json?', 'jsonb?', 'json[]'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='02')
    args = ap.parse_args()

    ss = evidence_path('01', 'schema_summary.json')
    if not ss.exists():
        write_evidence(args.phase, 'json_overuse.md', '# JSON overuse\n\nschema_summary.json missing.\n')
        return 0

    data = json.loads(ss.read_text())
    hits = []
    for t in data.get('tables', []):
        for c in t.get('columns', []):
            if c.get('type', '').lower().rstrip('?[]') in {x.rstrip('?[]') for x in JSON_TYPES}:
                hits.append((t['name'], c['name'], t['source_file'], t['line']))

    md = ['# JSON overuse audit (Karwin §5 EAV)', '', f'Total: {len(hits)}', '']
    md.append('| Table | Column | Source |')
    md.append('|-------|--------|--------|')
    for t, c, f, ln in hits:
        md.append(f'| {t} | {c} | {f}:{ln} |')

    write_evidence(args.phase, 'json_overuse.md', '\n'.join(md))

    if len(hits) >= 3:
        append_finding({
            'phase': args.phase,
            'category': 'schema',
            'subcategory': 'json-overuse',
            'severity': 'medium',
            'confidence': 'medium',
            'title': f'JSON columns в {len(hits)} полях — потенциальный EAV/business-state-in-blob',
            'location': {'file': hits[0][2], 'lines': str(hits[0][3])},
            'evidence': f'Json/JSONB колонки найдены в {len(hits)} местах. Sample: {hits[:5]}',
            'impact': 'Невозможность DB-level constraints, query indexing требует expression-индексов.',
            'recommendation': ('Для полей, по которым делаются WHERE/JOIN — выделить в отдельные колонки '
                               'с CHECK/FK constraints. JSON оставить только для структурно-переменных данных.'),
            'effort': 'L',
            'references': ['Karwin §5 Entity-Attribute-Value', 'Date §3 Predicates'],
        })
    print(f'OK: json overuse — {len(hits)} hits')
    return 0


if __name__ == '__main__':
    sys.exit(main())
