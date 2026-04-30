#!/usr/bin/env python3
"""pull_request_target / workflow_run на untrusted code."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, iter_workflow_files
import yaml

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='06')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

issues = []
for f in iter_workflow_files(project_root):
    try: wf = yaml.safe_load(f.read_text()) or {}
    except: continue
    triggers = wf.get('on') or wf.get(True)
    if not triggers: continue
    keys = list(triggers.keys()) if isinstance(triggers, dict) else (triggers if isinstance(triggers, list) else [str(triggers)])
    rel = str(f.relative_to(project_root))
    if 'pull_request_target' in keys:
        issues.append({'file': rel, 'trigger': 'pull_request_target', 'risk': 'high'})
    if 'workflow_run' in keys:
        issues.append({'file': rel, 'trigger': 'workflow_run', 'risk': 'high'})

md = ['# Dangerous triggers', '', f'Total: {len(issues)}', '']
for i in issues:
    md.append(f'- {i["file"]} — `{i["trigger"]}` ({i["risk"]})')
write_evidence(args.phase, 'dangerous_triggers.md', '\n'.join(md))

for i in issues:
    append_finding({
        'phase': args.phase, 'category': 'workflow',
        'subcategory': f'dangerous-trigger-{i["trigger"].replace("_","-")}',
        'severity': 'high', 'confidence': 'high',
        'title': f'{i["trigger"]} trigger в {i["file"]}',
        'location': {'file': i['file'], 'line': 1},
        'evidence': f'Workflow uses `{i["trigger"]}` trigger — runs with **base repo permissions and secrets** на untrusted PR code.',
        'confidence_rationale': 'YAML parsed; trigger key confirmed. This is the #1 OSS supply-chain attack vector.',
        'impact': 'Attacker submits malicious PR. workflow_run/pull_request_target runs WITH repo secrets → exfiltration.',
        'recommendation': ('1) Если можно — заменить на `pull_request` (без _target). '
                           '2) Если нужен — в job явно ставь `permissions: contents: read` + не делать `actions/checkout` с PR head SHA до approval. '
                           '3) Использовать `if: github.event.pull_request.head.repo.full_name == github.repository` для skip forks.'),
        'effort': 'M',
        'references': ['GitHub Security Lab: Keeping your workflow secure',
                       'Adnan Khan, How to attack GitHub via pull_request_target']
    })

print(f'OK: {len(issues)} dangerous triggers')
