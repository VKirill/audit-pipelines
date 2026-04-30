#!/usr/bin/env python3
"""Detect Prisma $queryRawUnsafe / $executeRawUnsafe usage — main SQLi vector.

Two-tier severity:
- Critical: Unsafe API + dynamic string interpolation visible nearby
- High:     Unsafe API with positional placeholders ($1, $2) — needs manual flow check

Reads from manifest hints.raw_sql_in_code if pre-populated, otherwise scans code.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, hints, append_finding, write_evidence, get_paths, iter_files


UNSAFE_API = re.compile(
    r'\b(\$queryRawUnsafe|\$executeRawUnsafe|prisma\.\$queryRawUnsafe|prisma\.\$executeRawUnsafe|sql\.unsafe)\s*\(',
    re.IGNORECASE,
)
TEMPLATE_INTERPOL = re.compile(r'\$\{[^}]+\}')
STRING_CONCAT_SQL = re.compile(r'["`\'][^"`\']*\+[^"`\']+\+[^"`\']*(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE)', re.IGNORECASE)


def scan_unsafe(rel_path, project_root):
    """Return list of (line, severity, evidence) tuples."""
    full = project_root / rel_path
    if not full.exists():
        return []
    try:
        text = full.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return []
    lines = text.splitlines()
    hits = []
    for i, ln in enumerate(lines):
        m = UNSAFE_API.search(ln)
        if not m:
            continue
        # Take 30 lines context above + 5 below
        ctx_start = max(0, i - 30)
        ctx_end = min(len(lines), i + 6)
        ctx = '\n'.join(lines[ctx_start:ctx_end])

        has_interp = bool(TEMPLATE_INTERPOL.search(ctx)) and 'sql' in ctx.lower()
        has_concat = bool(STRING_CONCAT_SQL.search(ctx))

        if has_interp or has_concat:
            severity = 'critical'
            confidence = 'high'
            note = 'Dynamic string interpolation/concat near Unsafe API'
        else:
            severity = 'high'
            confidence = 'medium'
            note = 'Unsafe API used; verify positional placeholders ($1, $2) cover ALL inputs'
        hits.append((i + 1, severity, confidence, note, ctx))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='07')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()

    qf = paths(m).get('query_files', {}) or {}
    code_globs = qf.get('code_globs', ['**/*.ts', '**/*.tsx', '**/*.js'])
    excludes = qf.get('excludes', ['node_modules', '.git', 'dist', 'build', '.next'])

    md = ['# Raw SQL Unsafe API surface', '',
          'Detects Prisma `$queryRawUnsafe`/`$executeRawUnsafe` and similar — main SQLi vectors.', '']

    all_hits = []
    files_scanned = 0
    for rel in iter_files(code_globs, excludes, project_root):
        files_scanned += 1
        for line, sev, conf, note, ctx in scan_unsafe(rel, project_root):
            all_hits.append({
                'file': str(rel), 'line': line,
                'severity': sev, 'confidence': conf, 'note': note,
                'ctx': ctx,
            })

    md.append(f'**Files scanned:** {files_scanned}')
    md.append(f'**Total hits:** {len(all_hits)}')
    md.append('')

    if all_hits:
        crit = [h for h in all_hits if h['severity'] == 'critical']
        high = [h for h in all_hits if h['severity'] == 'high']
        md.append(f'**Critical:** {len(crit)} (dynamic interpolation visible)')
        md.append(f'**High:** {len(high)} (Unsafe API with placeholders, needs manual flow check)')
        md.append('')
        for h in all_hits[:200]:
            md.append(f'## [{h["severity"]}] {h["file"]}:{h["line"]}')
            md.append(f'note: {h["note"]}')
            md.append('```')
            md.append(h['ctx'])
            md.append('```')
            md.append('')
    write_evidence(args.phase, 'raw_sql_unsafe.md', '\n'.join(md))

    # Emit findings — group by file (one finding per file with N hits)
    by_file = {}
    for h in all_hits:
        by_file.setdefault((h['file'], h['severity']), []).append(h)

    for (fpath, sev), grouped in by_file.items():
        first = grouped[0]
        finding = {
            'phase': args.phase,
            'category': 'security',
            'subcategory': 'sqli-raw-unsafe',
            'severity': sev,
            'confidence': first['confidence'],
            'title': f'$queryRawUnsafe usage в {fpath} ({len(grouped)} hit(s))',
            'location': {'file': fpath, 'lines': str(first['line']),
                         'symbol': 'multiple', 'db_object': f'{fpath}:Unsafe-SQL'},
            'evidence': (f'{len(grouped)} использование(й) Prisma Unsafe API в {fpath}. '
                         f'First hit at line {first["line"]}: {first["note"]}.'),
            'confidence_rationale': ('Найдено через regex на $queryRawUnsafe/$executeRawUnsafe API. '
                                     'Эти методы — Prisma\'s "escape hatch" — требуют ручной валидации '
                                     'каждого user input. Lines verified through file read.'),
            'impact': ('Если хоть один user input попадает в interpolation без параметризации — '
                       'полная компрометация БД (data exfiltration, schema enumeration, RCE).'),
            'recommendation': ('1) Заменить на $queryRaw (template literal с tagged interpolation — auto-escape). '
                               '2) Если структура запроса требует динамики (например ORDER BY column name) — '
                               'использовать allowlist валидацию входов перед interpolation. '
                               '3) Покрыть unit-тестами с adversarial inputs.'),
            'effort': 'M',
            'references': [
                'Karwin, SQL Antipatterns §20 SQL Injection',
                'OWASP SQL Injection Prevention Cheat Sheet',
                'Prisma docs: https://www.prisma.io/docs/orm/prisma-client/using-raw-sql/raw-queries#queryrawunsafe'
            ],
        }
        if sev == 'critical':
            finding['exploit_proof'] = (
                f'User отправляет специально crafted input в endpoint, который доходит до '
                f'{fpath}:{first["line"]}. Динамическая склейка/interpolation без allowlist '
                f'позволяет injection \'; DROP TABLE users; --. '
                f'Total {len(grouped)} hits в этом файле — surface area большая.'
            )
        append_finding(finding)

    print(f'OK: raw_sql_unsafe — {files_scanned} files, {len(all_hits)} hits, {len(by_file)} findings')
    return 0


if __name__ == '__main__':
    sys.exit(main())
