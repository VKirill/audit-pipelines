#!/usr/bin/env python3
"""Detect mixed snake_case/camelCase in tables/columns."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, append_finding, write_evidence, evidence_path


def style_of(name):
    if '_' in name and name.lower() == name:
        return 'snake_case'
    if re.match(r'^[a-z][a-zA-Z0-9]*$', name) and re.search(r'[A-Z]', name):
        return 'camelCase'
    if re.match(r'^[A-Z]', name):
        return 'PascalCase'
    return 'lowercase'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='02')
    args = ap.parse_args()

    ss = evidence_path('01', 'schema_summary.json')
    if not ss.exists():
        write_evidence(args.phase, 'naming_inconsistency.md',
                       '# Naming\n\nschema_summary.json missing — run extract_schema first.\n')
        return 0

    data = json.loads(ss.read_text())
    table_styles = {}
    column_styles = {}
    for t in data.get('tables', []):
        ts = style_of(t['name'])
        table_styles[ts] = table_styles.get(ts, 0) + 1
        for c in t.get('columns', []):
            cs = style_of(c['name'])
            column_styles[cs] = column_styles.get(cs, 0) + 1

    md = ['# Naming convention audit (Celko §1)', '']
    md.append('## Tables')
    for s, c in sorted(table_styles.items(), key=lambda x: -x[1]):
        md.append(f'- {s}: {c}')
    md.append('\n## Columns')
    for s, c in sorted(column_styles.items(), key=lambda x: -x[1]):
        md.append(f'- {s}: {c}')

    write_evidence(args.phase, 'naming_inconsistency.md', '\n'.join(md))

    # finding if mixed
    if len(table_styles) > 1 or len(column_styles) > 1:
        append_finding({
            'phase': args.phase,
            'category': 'schema',
            'subcategory': 'naming-inconsistency',
            'severity': 'low',
            'confidence': 'high',
            'title': 'Mixed naming conventions в schema',
            'location': {'file': 'multiple', 'lines': '1', 'db_object': 'whole schema'},
            'evidence': f'Table styles: {table_styles}; Column styles: {column_styles}.',
            'confidence_rationale': 'Style derived from schema_summary.json by automatic classifier.',
            'impact': 'Затрудняет ручной написание SQL и review кода. Индикатор отсутствия style guide.',
            'recommendation': 'Зафиксировать convention в DB style guide. Постепенная миграция к единому стилю (Sadalage Part II — rename column refactoring).',
            'effort': 'L',
            'references': ['Celko, SQL Programming Style §1 Naming Data Elements'],
        })

    print('OK: naming audit')
    return 0


if __name__ == '__main__':
    sys.exit(main())
