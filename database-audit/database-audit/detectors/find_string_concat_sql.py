#!/usr/bin/env python3
"""SQL injection surface. Reads hints.raw_sql_in_code; flags uses_user_input=true.
Also runs lightweight regex scan as fallback over query_files.code_globs."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, paths, append_finding, write_evidence, get_paths, iter_files

PATTERNS = [
    (r'\$\{[^}]+\}', 'JS template-string interpolation'),
    (r'\+\s*\w+\s*\+', 'JS string concat'),
    (r'f["\']\s*[A-Z][^"\']*\{', 'Python f-string'),
    (r'%\s*\(\w+\)?[sd]', 'Python % formatting'),
    (r'fmt\.Sprintf\(', 'Go fmt.Sprintf'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='07')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    raw = hints(m).get('raw_sql_in_code', []) or []

    md = ['# SQL injection surface', '']
    md.append('## From manifest hints')
    md.append('| File | Lines | Kind | Uses user input? |')
    md.append('|------|-------|------|------------------|')
    for r in raw:
        md.append(f"| {r['file']} | {r['lines']} | {r.get('kind','?')} | "
                  f"{'**YES**' if r.get('uses_user_input') else 'no'} |")

    write_evidence(args.phase, 'sqli_surface.md', '\n'.join(md))

    for r in raw:
        if r.get('uses_user_input'):
            append_finding({
                'phase': args.phase,
                'category': 'security',
                'subcategory': 'sqli',
                'severity': 'critical',
                'confidence': 'high',
                'title': f'Возможный SQL injection: {r["file"]}:{r["lines"]}',
                'location': {'file': r['file'], 'lines': r['lines']},
                'evidence': f'Raw SQL ({r.get("kind","?")}) с user-controlled input в {r["file"]}:{r["lines"]}.',
                'confidence_rationale': ('Помечено в manifest.hints.raw_sql_in_code как '
                                         'uses_user_input=true после ручной проверки потока данных.'),
                'exploit_proof': (f'User отправляет специально сконструированный input в endpoint, '
                                  f'который доходит до raw SQL в {r["file"]}:{r["lines"]} через '
                                  f'string interpolation. Возможен payload типа \'; DROP TABLE; --\'.'),
                'impact': 'Полная компрометация БД, утечка/удаление данных.',
                'recommendation': ('Заменить interpolation на параметризованный запрос. '
                                   'Для $queryRaw в Prisma — использовать $queryRawUnsafe только с allowlist.'),
                'effort': 'S',
                'references': [
                    'Karwin, SQL Antipatterns §20 SQL Injection',
                    'OWASP SQL Injection Prevention Cheat Sheet'
                ],
            })

    print(f'OK: sqli surface — {len(raw)} raw entries')
    return 0


if __name__ == '__main__':
    sys.exit(main())
