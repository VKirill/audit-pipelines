#!/usr/bin/env python3
"""Detect custom DB-access wrappers (dbExec, dbQuery, executeQuery, runQuery).
These are common in projects mixing Prisma + raw pg.Pool — easily missed by ORM-specific detectors.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, append_finding, write_evidence, get_paths, iter_files

WRAPPER_DEF = re.compile(
    r'(?:export\s+)?(?:async\s+)?(?:function\s+)?(\b(?:dbExec|dbQuery|executeQuery|runQuery|safeQuery|sqlExec|sqlQuery)\b)\s*[:=]?\s*[(<]',
    re.IGNORECASE,
)
WRAPPER_USE = re.compile(r'\bawait\s+(dbExec|dbQuery|executeQuery|runQuery|safeQuery|sqlExec|sqlQuery)\s*\(', re.IGNORECASE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='04')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    qf = paths(m).get('query_files', {}) or {}
    code_globs = qf.get('code_globs', ['**/*.ts', '**/*.js'])
    excludes = qf.get('excludes', ['node_modules', '.git', 'dist', 'build'])

    defs, uses = [], []
    for rel in iter_files(code_globs, excludes, project_root):
        full = project_root / rel
        try:
            text = full.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for i, ln in enumerate(text.splitlines(), 1):
            for m_def in WRAPPER_DEF.finditer(ln):
                defs.append((str(rel), i, m_def.group(1), ln.strip()[:160]))
            for m_use in WRAPPER_USE.finditer(ln):
                uses.append((str(rel), i, m_use.group(1), ln.strip()[:160]))

    md = ['# ORM custom wrappers (raw SQL surface)', '']
    md.append(f'**Definitions found:** {len(defs)}')
    md.append(f'**Use sites found:** {len(uses)}')
    md.append('')
    md.append('## Definitions')
    for f, ln, name, ctx in defs[:30]:
        md.append(f'- {f}:{ln} — `{name}` — `{ctx}`')
    md.append('')
    md.append('## Top use sites (first 100)')
    for f, ln, name, ctx in uses[:100]:
        md.append(f'- {f}:{ln} — `{name}(...)`')

    write_evidence(args.phase, 'orm_wrappers.md', '\n'.join(md))

    if uses and defs:
        # Aggregate finding — wrapper exists, all uses need review
        first_def = defs[0]
        append_finding({
            'phase': args.phase,
            'category': 'security',
            'subcategory': 'sqli-via-wrapper',
            'severity': 'high',
            'confidence': 'medium',
            'title': f'Custom raw-SQL wrappers ({len(uses)} use sites need review)',
            'location': {'file': first_def[0], 'lines': str(first_def[1]),
                         'symbol': first_def[2], 'db_object': 'custom-wrapper'},
            'evidence': (f'{len(defs)} wrapper definitions and {len(uses)} use sites. '
                         f'These wrappers (dbExec/dbQuery) bypass ORM safety; each use site '
                         f'requires manual SQLi review.'),
            'confidence_rationale': ('Wrapper detected via regex pattern `(dbExec|dbQuery|...)\\s*\\(`. '
                                     'Confidence medium because not every use is unsafe — depends on '
                                     'parameterization. Manual review needed for each.'),
            'impact': 'Custom wrappers usually accept (sql, params) but not all callers parameterize correctly.',
            'recommendation': ('Audit каждое use site вручную. Заменить на parameterized API, либо '
                               'обернуть wrapper в helper с автоматической параметризацией.'),
            'effort': 'L',
            'references': [
                'Karwin, SQL Antipatterns §20',
                'OWASP SQL Injection Prevention Cheat Sheet'
            ],
        })

    print(f'OK: orm_wrappers — {len(defs)} defs, {len(uses)} uses')
    return 0


if __name__ == '__main__':
    sys.exit(main())
