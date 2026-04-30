#!/usr/bin/env python3
"""Migration inventory + reversibility check. Pure manifest-driven."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, paths, write_evidence, get_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='06')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    mig = paths(m).get('migration_files', {}) or {}

    files = list(mig.get('files', []) or [])
    dirs = list(mig.get('dirs', []) or [])
    tool = mig.get('tool', 'unknown')

    if not files and dirs:
        for d in dirs:
            full = project_root / d
            if full.exists():
                for sub in full.rglob('*'):
                    if sub.is_file() and sub.suffix in ('.sql', '.ts', '.py', '.rb', '.js'):
                        files.append(str(sub.relative_to(project_root)))

    files = sorted(set(files))

    inv = ['# Migration inventory', '',
           f'Tool: {tool}',
           f'Total files: {len(files)}',
           '',
           '| File | Size (lines) | Has down? |',
           '|------|--------------|-----------|']

    rev_md = ['# Reversibility audit', '']
    no_down = 0
    for f in files[:200]:
        full = project_root / f
        try:
            text = full.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        lines = text.count('\n')
        has_down = bool(re.search(r'(def\s+down|exports\.down|down:|async\s+down|\bdown\(|--\s*Down|-- DOWN)',
                                   text))
        if not has_down:
            no_down += 1
        inv.append(f'| {f} | {lines} | {"yes" if has_down else "no"} |')

    rev_md.append(f'Total: {len(files)}, без down: {no_down}')
    rev_md.append('')
    if tool == 'prisma-migrate':
        rev_md.append('Note: Prisma не поддерживает down-migrations by design. '
                      'Forward-only — валидный подход, требует documented rollback.')

    write_evidence(args.phase, 'migrations_inventory.md', '\n'.join(inv))
    write_evidence(args.phase, 'reversibility_audit.md', '\n'.join(rev_md))

    # also satisfy phase 01's migrations_list.md
    write_evidence('01', 'migrations_list.md', '\n'.join(inv))

    print(f'OK: migrations — {len(files)} files, {no_down} without down')
    return 0


if __name__ == '__main__':
    sys.exit(main())
