#!/usr/bin/env python3
"""Long-lived cloud credentials → recommend OIDC. Phase 04."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, hints

OIDC_REC = {
    'aws': 'aws-actions/configure-aws-credentials@<sha> + role-to-assume + permissions: id-token: write',
    'gcp': 'google-github-actions/auth@<sha> + workload_identity_provider',
    'azure': 'azure/login@<sha> + federated identity credentials',
    'npm': 'npm publish --provenance + OIDC trust on npmjs.com',
    'pypi': 'PyPI Trusted Publisher (no API token needed)',
    'dockerhub': 'docker/login-action@<sha> + OIDC token (если supported)',
}

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='04')
args = ap.parse_args()

m = load_manifest()
items = hints(m).get('long_lived_credentials', []) or []

md = ['# Long-lived credentials → OIDC opportunities', '']
md.append(f'Total: {len(items)}')
md.append('')
for i in items:
    md.append(f'- `{i["secret_name"]}` — files: {i.get("usage_files", [])} → {i.get("target_cloud", "?")}')
write_evidence(args.phase, 'oidc_opportunities.md', '\n'.join(md))

for i in items:
    cloud = i.get('target_cloud', 'other')
    rec = OIDC_REC.get(cloud, 'Migrate to OIDC if cloud supports it')
    append_finding({
        'phase': args.phase, 'category': 'secrets',
        'subcategory': 'long-lived-credentials',
        'severity': 'high', 'confidence': 'high',
        'title': f'Long-lived secret `{i["secret_name"]}` → migrate to OIDC',
        'location': {'file': i.get('usage_files', ['?'])[0], 'line': 1, 'symbol': i['secret_name']},
        'evidence': f'Secret `{i["secret_name"]}` — long-lived credential для {cloud}. OIDC доступен для этой cloud.',
        'confidence_rationale': 'Secret name pattern matches cloud-credential format. Workflow uses through `${{ secrets.* }}`.',
        'impact': 'Long-lived secret = высокий blast radius если leaked. OIDC ротирует токен per-job (~10 min lifetime).',
        'recommendation': f'Migrate to OIDC: {rec}',
        'effort': 'M',
        'references': ['GitHub Docs: Configuring OpenID Connect']
    })

print(f'OK: {len(items)} long-lived credentials → OIDC findings')
