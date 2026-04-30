#!/usr/bin/env python3
"""Find third-party actions used without SHA pinning. Phase 02 — main supply-chain check."""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, iter_workflow_files

USES_RE = re.compile(r'^\s*-?\s*uses:\s*([^\s#]+)', re.MULTILINE)
SHA_RE = re.compile(r'^[0-9a-f]{40}$')

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='02')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

unpinned = []
for f in iter_workflow_files(project_root):
    text = f.read_text()
    for line_num, line in enumerate(text.splitlines(), 1):
        match = re.match(r'\s*-?\s*uses:\s*([^\s#]+)', line)
        if not match: continue
        ref_str = match.group(1).strip().strip('"\'')
        if '@' not in ref_str: continue
        action, ref = ref_str.rsplit('@', 1)
        # Skip official GitHub actions and same-repo refs
        if action.startswith('./'): continue
        is_pinned = bool(SHA_RE.match(ref))
        if not is_pinned:
            unpinned.append({
                'action': action, 'ref': ref,
                'file': str(f.relative_to(project_root)), 'line': line_num,
                'is_branch': ref in ('main', 'master', 'develop') or '/' in ref,
            })

md = ['# Unpinned actions (supply-chain risk)', '']
md.append(f'Total unpinned: {len(unpinned)}')
md.append('')
md.append('| Action | Ref | Risk | File:Line |')
md.append('|--------|-----|------|-----------|')
for u in unpinned:
    risk = 'CRITICAL (branch)' if u['is_branch'] else 'HIGH (tag)'
    md.append(f'| `{u["action"]}` | `{u["ref"]}` | {risk} | {u["file"]}:{u["line"]} |')

write_evidence(args.phase, 'unpinned_actions.md', '\n'.join(md))

# Emit findings — group by (action, file)
by_action = {}
for u in unpinned:
    by_action.setdefault(u['action'], []).append(u)

for action, items in by_action.items():
    first = items[0]
    is_branch = first['is_branch']
    sev = 'critical' if is_branch else 'high'
    finding = {
        'phase': args.phase,
        'category': 'supply-chain',
        'subcategory': 'unpinned-action-branch' if is_branch else 'unpinned-action-tag',
        'severity': sev,
        'confidence': 'high',
        'title': f'Unpinned action: {action}@{first["ref"]} ({len(items)} usage(s))',
        'location': {'file': first['file'], 'line': first['line'], 'action': action},
        'evidence': (f'Action `{action}` used with mutable ref `@{first["ref"]}` in '
                     f'{len(items)} place(s). First: {first["file"]}:{first["line"]}.'),
        'confidence_rationale': (f'Ref `{first["ref"]}` is not a 40-char SHA. '
                                 f'{"Branch refs (main/master) — worst case." if is_branch else "Tag refs vulnerable to retag attacks (tj-actions/changed-files March 2025)."}'),
        'impact': (f'Supply-chain attack vector. Если действие скомпрометировано (как tj-actions/changed-files в марте 2025), '
                   f'все workflows с {action}@{first["ref"]} запустят compromised код с access к secrets.'),
        'recommendation': (f'1) Run `pinact run` для resolve SHA. '
                           f'2) Заменить `{action}@{first["ref"]}` на `{action}@<40-char-sha> # {first["ref"]}` '
                           f'во всех {len(items)} местах. '
                           f'3) Renovate/Dependabot для auto-update SHA.'),
        'effort': 'S',
        'references': [
            'GitHub Docs: Security hardening for Actions',
            'tj-actions/changed-files incident (March 2025)',
            'pinact: https://github.com/suzuki-shunsuke/pinact'
        ],
    }
    if sev == 'critical':
        finding['exploit_proof'] = (
            f'Attacker pushes malicious commit to {action} branch `{first["ref"]}`. '
            f'Next workflow run downloads new code → exfiltrates GITHUB_TOKEN, secrets via logs '
            f'(пример atlasta tj-actions: ~23 000 repos compromised, secrets leaked в workflow logs).'
        )
    append_finding(finding)

print(f'OK: {len(unpinned)} unpinned actions, {len(by_action)} unique')
