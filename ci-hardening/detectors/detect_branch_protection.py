#!/usr/bin/env python3
"""Branch protection audit via gh api. Phase 05."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, hints, github

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='05')
args = ap.parse_args()

m = load_manifest()
bp = hints(m).get('branch_protection', {}) or {}
gh_meta = github(m)
default_branch = gh_meta.get('default_branch', 'main')
visibility = gh_meta.get('visibility', 'unknown')

md = ['# Branch protection audit', '']
md.append(f'**Default branch:** {default_branch}')
md.append(f'**Visibility:** {visibility}')
md.append('')
for k in ['enabled', 'require_pr', 'required_status_checks', 'require_signed_commits',
          'require_linear_history', 'required_approvals', 'dismiss_stale_reviews', 'enforce_admins']:
    md.append(f'- {k}: `{bp.get(k, "?")}`')
write_evidence(args.phase, 'branch_protection.md', '\n'.join(md))

# Findings
findings_to_add = []
if not bp.get('enabled'):
    findings_to_add.append(('critical', 'no-protection', f'Default branch `{default_branch}` без protection',
                            f'Anyone with write access pushes directly to {default_branch} без PR/review.',
                            f'gh api PUT /repos/$OWNER/$REPO/branches/{default_branch}/protection -F required_pull_request_reviews.required_approving_review_count=1'))
elif not bp.get('require_pr'):
    findings_to_add.append(('high', 'no-pr-required', 'Branch protection enabled, но не требует PR',
                            'Direct pushes still allowed для admin/maintainer.',
                            'Enable "Require pull request before merging" в Branch protection rules.'))

if visibility != 'private' and not bp.get('required_status_checks'):
    findings_to_add.append(('medium', 'no-status-checks', 'Нет required status checks',
                            'PR можно мёржить даже если CI красный.',
                            'Add required status checks (например `CI Success`) в branch protection.'))

if not bp.get('enforce_admins'):
    findings_to_add.append(('medium', 'admins-bypass', 'Admins могут bypass protection',
                            'Соло-проект — норма; для команды — risk.',
                            'Если команда > 2 — enable "Do not allow bypassing the above settings".'))

for sev, sub, title, evidence, rec in findings_to_add:
    append_finding({
        'phase': args.phase, 'category': 'branch-protection',
        'subcategory': sub, 'severity': sev, 'confidence': 'high',
        'title': title,
        'location': {'file': f'(github settings: branch protection / {default_branch})', 'line': 1},
        'evidence': evidence,
        'confidence_rationale': f'Verified through gh api repos/$OWNER/$REPO/branches/{default_branch}/protection.',
        'impact': 'Force-pushes / direct merges без review possible. Compromise одного коллаборатора → unaudited push.',
        'recommendation': rec, 'effort': 'S',
        'references': ['GitHub Docs: Branch protection']
    })

print(f'OK: branch_protection — {len(findings_to_add)} findings')
