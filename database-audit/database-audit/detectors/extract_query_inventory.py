#!/usr/bin/env python3
"""Inventory raw SQL files + ORM call sites using globs from manifest.paths.query_files."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, write_evidence, get_paths, iter_files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='01')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    qf = paths(m).get('query_files', {}) or {}
    code_globs = qf.get('code_globs', ['**/*.ts', '**/*.py', '**/*.go'])
    sql_globs = qf.get('raw_sql_globs', ['**/*.sql'])
    excludes = qf.get('excludes', ['node_modules', '.git', 'dist', 'build', '.venv'])

    out = ['# Query Inventory (manifest-driven)', '']

    sql_files = sorted(set(iter_files(sql_globs, excludes, project_root)))
    out.append('## 1. Raw SQL files')
    out.append('```')
    out.extend(str(p) for p in sql_files)
    out.append('```')

    out.append('\n## 2. Raw SQL embedded in code (samples)')
    import re
    patterns = [
        (r'\$queryRaw|\$executeRaw|sql`', 'Prisma raw'),
        (r'\.execute\(|\.query\(|\.run\(', 'generic execute'),
        (r'createNativeQuery|createQuery', 'JPA/Hibernate'),
        (r'cursor\.execute|session\.execute', 'Python DB'),
    ]
    code_files = list(iter_files(code_globs, excludes, project_root))
    samples = {label: [] for _, label in patterns}
    for rel in code_files:
        full = project_root / rel
        try:
            text = full.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for pat, label in patterns:
            for ln_idx, ln in enumerate(text.splitlines(), 1):
                if re.search(pat, ln):
                    samples[label].append(f'{rel}:{ln_idx}: {ln.strip()[:160]}')
                    if len(samples[label]) >= 50:
                        break

    for label, items in samples.items():
        out.append(f'\n### {label} ({len(items)})')
        out.append('```')
        out.extend(items[:50])
        out.append('```')

    p = write_evidence(args.phase, 'queries_inventory.md', '\n'.join(out))
    print(f'OK: {p} (sql_files={len(sql_files)})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
