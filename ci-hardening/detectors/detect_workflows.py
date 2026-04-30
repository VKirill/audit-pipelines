#!/usr/bin/env python3
"""Inventory all .github/workflows/*.yml. Phase 01."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, write_evidence, iter_workflow_files
import yaml

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='01')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

md = ['# Workflows inventory', '']
files = list(iter_workflow_files(project_root))
md.append(f'**Total workflows:** {len(files)}'); md.append('')
md.append('| File | Name | Triggers | Jobs | Permissions |')
md.append('|------|------|----------|------|-------------|')

for f in files:
    try:
        wf = yaml.safe_load(f.read_text()) or {}
    except Exception as e:
        md.append(f'| {f.relative_to(project_root)} | _parse_error: {e}_ | | | |'); continue
    name = wf.get('name', '?')
    triggers_obj = wf.get('on') or wf.get(True)  # YAML quirk: on may parse as True
    if isinstance(triggers_obj, dict):
        triggers = ','.join(triggers_obj.keys())
    elif isinstance(triggers_obj, list):
        triggers = ','.join(str(t) for t in triggers_obj)
    else:
        triggers = str(triggers_obj)
    jobs = list((wf.get('jobs') or {}).keys())
    perms = wf.get('permissions', '(default)')
    md.append(f'| {f.relative_to(project_root)} | {name} | {triggers} | {len(jobs)} ({", ".join(jobs[:3])}) | {perms} |')

write_evidence(args.phase, 'workflows_inventory.md', '\n'.join(md))
print(f'OK: {len(files)} workflows inventoried')
