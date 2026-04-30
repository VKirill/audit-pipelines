#!/usr/bin/env python3
"""Check CodeQL setup. Phase 07."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, iter_workflow_files
import yaml

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='07')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

has_codeql = False
for f in iter_workflow_files(project_root):
    text = f.read_text()
    if 'github/codeql-action' in text:
        has_codeql = True
        break

md = ['# CodeQL setup', '', f'CodeQL workflow: {"✅ found" if has_codeql else "❌ not found"}', '']
write_evidence(args.phase, 'codeql_setup.md', '\n'.join(md))

if not has_codeql:
    append_finding({
        'phase': args.phase, 'category': 'sast',
        'subcategory': 'no-codeql',
        'severity': 'medium', 'confidence': 'high',
        'title': 'CodeQL не настроен',
        'location': {'file': '(.github/workflows/codeql.yml)', 'line': 1},
        'evidence': 'No workflow uses `github/codeql-action`.',
        'confidence_rationale': 'Grep through all workflow files.',
        'impact': 'No SAST на коде. Известные CVE-паттерны не детектятся (SQLi, XSS, hardcoded creds).',
        'recommendation': 'Скопировать `ci-hardening/templates/workflows/codeql.yml` с релевантными languages в matrix. Альтернатива — Settings → Code security → Default setup для CodeQL.',
        'effort': 'S',
        'references': ['GitHub Docs: About code scanning with CodeQL']
    })

print(f'OK: codeql_setup — present={has_codeql}')
