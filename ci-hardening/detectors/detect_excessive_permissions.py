#!/usr/bin/env python3
"""Workflows/jobs without explicit permissions or with write-all."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, iter_workflow_files
import yaml

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='03')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

issues = []
for f in iter_workflow_files(project_root):
    try: wf = yaml.safe_load(f.read_text()) or {}
    except: continue
    rel = str(f.relative_to(project_root))
    perms = wf.get('permissions')
    if perms is None:
        issues.append({'file': rel, 'scope': 'workflow', 'job': '', 'current': '(default — write-all)', 'severity': 'high'})
    elif perms == 'write-all':
        issues.append({'file': rel, 'scope': 'workflow', 'job': '', 'current': 'write-all', 'severity': 'high'})

    for jname, job in (wf.get('jobs') or {}).items():
        if not isinstance(job, dict): continue
        jperms = job.get('permissions')
        if perms is None and jperms is None:
            issues.append({'file': rel, 'scope': 'job', 'job': jname, 'current': '(inherits default)', 'severity': 'high'})

md = ['# Permissions audit', '', f'Total issues: {len(issues)}', '']
md.append('| File | Scope | Job | Current | Severity |')
md.append('|------|-------|-----|---------|----------|')
for i in issues:
    md.append(f'| {i["file"]} | {i["scope"]} | {i["job"]} | {i["current"]} | {i["severity"]} |')
write_evidence(args.phase, 'permissions_audit.md', '\n'.join(md))

for i in issues:
    if i['scope'] != 'workflow': continue  # one finding per file
    append_finding({
        'phase': args.phase, 'category': 'permissions',
        'subcategory': 'no-explicit-permissions',
        'severity': i['severity'], 'confidence': 'high',
        'title': f'No explicit permissions in {i["file"]} (default = write-all)',
        'location': {'file': i['file'], 'line': 1},
        'evidence': f'Workflow {i["file"]} has no `permissions:` block at workflow level. Default = write-all to all scopes.',
        'confidence_rationale': 'YAML parsed; permissions key absent. GitHub default if not specified — broad write access.',
        'impact': 'If any action gets compromised, attacker has full repo write/contents/issues/PRs/security-events access.',
        'recommendation': 'Add `permissions: contents: read` at workflow level. Per-job override only where needed (security-events: write для CodeQL, packages: write для publish).',
        'effort': 'S',
        'references': ['GitHub Docs: Secure use reference', 'OWASP top-10 for CI/CD']
    })

print(f'OK: {len(issues)} permissions issues')
