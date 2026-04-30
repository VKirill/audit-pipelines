#!/usr/bin/env python3
"""SELECT * usage. Karwin §18."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, append_finding, write_evidence, get_paths, iter_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='04')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    qf = paths(m).get('query_files', {}) or {}
    code_globs = qf.get('code_globs', ['**/*.ts', '**/*.py', '**/*.go'])
    sql_globs = qf.get('raw_sql_globs', ['**/*.sql'])
    excludes = qf.get('excludes', ['node_modules', '.git', 'dist', 'build'])

    pat = re.compile(r'SELECT\s+\*\s+FROM', re.IGNORECASE)
    findings = []
    for rel in list(iter_files(code_globs + sql_globs, excludes, project_root)):
        full = project_root / rel
        try:
            for ln_idx, ln in enumerate(full.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
                if pat.search(ln):
                    findings.append((str(rel), ln_idx, ln.strip()))
        except Exception:
            continue

    md = ['# SELECT * usage (Karwin §18)', '', f'Total: {len(findings)}', '']
    md.append('| File | Line | Snippet |')
    md.append('|------|------|---------|')
    for f, ln, snippet in findings[:100]:
        md.append(f'| {f} | {ln} | `{snippet[:120]}` |')

    write_evidence(args.phase, 'select_star.md', '\n'.join(md))

    if findings:
        # One aggregate finding
        sample_files = sorted(set(f for f, _, _ in findings))[:10]
        append_finding({
            'phase': args.phase,
            'category': 'query',
            'subcategory': 'select-star',
            'severity': 'low' if len(findings) < 5 else 'medium',
            'confidence': 'high',
            'title': f'SELECT * usage в {len(findings)} местах',
            'location': {'file': sample_files[0] if sample_files else 'unknown',
                         'lines': str(findings[0][1]) if findings else '1',
                         'db_object': f'multiple ({len(findings)} sites)'},
            'evidence': f'SELECT * найдено в {len(findings)} местах. Sample files: {", ".join(sample_files[:5])}',
            'confidence_rationale': 'Регулярное выражение по проектным файлам; результаты в evidence/select_star.md.',
            'impact': ('Лишние данные, ломкость к ALTER TABLE с добавлением колонок (особенно BLOB), '
                       'неявная связь с ORM relations.'),
            'recommendation': 'Заменить SELECT * на явный список колонок. Karwin §18.',
            'effort': 'S',
            'references': ['Karwin, SQL Antipatterns §18 Implicit Columns'],
        })

    print(f'OK: SELECT * — {len(findings)} hits')
    return 0


if __name__ == '__main__':
    sys.exit(main())
