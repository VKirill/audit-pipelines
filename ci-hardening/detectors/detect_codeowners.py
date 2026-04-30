#!/usr/bin/env python3
"""Check CODEOWNERS + SECURITY.md. Phase 08."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='08')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

required = {
    'CODEOWNERS': ['.github/CODEOWNERS', 'CODEOWNERS', 'docs/CODEOWNERS'],
    'SECURITY.md': ['.github/SECURITY.md', 'SECURITY.md'],
    'pull_request_template.md': ['.github/pull_request_template.md', '.github/PULL_REQUEST_TEMPLATE.md'],
}

found, missing = {}, []
for label, candidates in required.items():
    for c in candidates:
        if (project_root / c).exists():
            found[label] = c
            break
    else:
        missing.append(label)

md = ['# Repo metadata files', '']
md.append('## Found')
for k, v in found.items():
    md.append(f'- ✅ {k}: `{v}`')
md.append('\n## Missing')
for k in missing:
    md.append(f'- ❌ {k}')
write_evidence(args.phase, 'codeowners_check.md', '\n'.join(md))
write_evidence(args.phase, 'security_md_check.md', '\n'.join(md))

severities = {'CODEOWNERS': 'low', 'SECURITY.md': 'medium', 'pull_request_template.md': 'low'}
recs = {
    'CODEOWNERS': 'Создать `.github/CODEOWNERS`. Pattern: `* @maintainer` или domain ownership.',
    'SECURITY.md': 'Скопировать template из `ci-hardening/templates/SECURITY.md`. GitHub использует для Security tab.',
    'pull_request_template.md': 'Скопировать template из `ci-hardening/templates/pull_request_template.md`.'
}
for k in missing:
    append_finding({
        'phase': args.phase, 'category': 'workflow',
        'subcategory': f'missing-{k.lower().replace(".md","").replace("_","-")}',
        'severity': severities[k], 'confidence': 'high',
        'title': f'Missing {k}',
        'location': {'file': '(repo root)', 'line': 1},
        'evidence': f'Файл {k} отсутствует в стандартных локациях ({", ".join(required[k])}).',
        'confidence_rationale': f'File system check: {k} not found.',
        'impact': f'{k} расширяет автоматизацию и signaling для contributors / GitHub UI.',
        'recommendation': recs[k], 'effort': 'S',
        'references': ['GitHub Docs: About community profiles']
    })

print(f'OK: codeowners_check — {len(missing)} missing')
