#!/usr/bin/env python3
"""GitHub Code security settings audit. Phase 07."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, hints, github

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='07')
args = ap.parse_args()

m = load_manifest()
sf = hints(m).get('security_features', {}) or {}
gh_meta = github(m)
visibility = gh_meta.get('visibility', 'unknown')

md = ['# Security features', '']
for k, v in sf.items():
    md.append(f'- {k}: `{v}`')
write_evidence(args.phase, 'security_features.md', '\n'.join(md))

# Findings
checks = [
    ('dependabot_alerts', 'high', 'Dependabot alerts disabled', 'Settings → Code security → Dependabot alerts: Enable'),
    ('secret_scanning', 'high' if visibility == 'public' else 'medium',
     'Secret scanning disabled', 'Settings → Code security → Secret scanning: Enable (free for public)'),
    ('secret_scanning_push_protection', 'medium', 'Push protection disabled',
     'Settings → Code security → Push protection: Enable (предотвращает commit secrets)'),
    ('code_scanning', 'medium', 'Code scanning не настроен',
     'Settings → Code security → Code scanning: Set up CodeQL (default или advanced)'),
    ('dependabot_security_updates', 'medium', 'Dependabot security updates disabled',
     'Settings → Code security → Dependabot security updates: Enable'),
]

for key, sev, title, rec in checks:
    if sf.get(key) is False:
        append_finding({
            'phase': args.phase, 'category': 'settings',
            'subcategory': key.replace('_', '-'),
            'severity': sev, 'confidence': 'high',
            'title': title,
            'location': {'file': '(github settings: code security)', 'line': 1},
            'evidence': f'gh api repos/$OWNER/$REPO --jq .security_and_analysis: {key} = disabled.',
            'confidence_rationale': 'Verified via GitHub API.',
            'impact': 'Без этой защиты vulnerable dependencies / secrets могут попасть в codebase без alert.',
            'recommendation': rec, 'effort': 'S',
            'references': ['GitHub Docs: Configuring security features']
        })

print(f'OK: security_features — checked {len(checks)}')
