#!/usr/bin/env python3
"""Phase 09a — auto-draft adversary review."""
import argparse, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import get_paths, load_manifest

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='09a')
args = ap.parse_args()

audit_dir, _, _, fp, _ = get_paths()
m = load_manifest()
findings = []
if fp.exists():
    for line in fp.read_text().splitlines():
        line = line.strip()
        if not line: continue
        try: findings.append(json.loads(line))
        except: pass

sev = Counter(f.get('severity') for f in findings)
conf = Counter(f.get('confidence') for f in findings)

out = ['# Adversary review (Phase 09a)', '', '## Summary stats', '',
       f'- Total findings: {len(findings)}',
       f'- by severity: {dict(sev)}',
       f'- by confidence: {dict(conf)}', '']

out += ['## Strong findings (защищены evidence)', '']
for f in findings[:15]:
    if f.get('severity') in ('critical', 'high'):
        out.append(f'- **{f["id"]}** [{f["severity"]}] — {f["title"]}')

out += ['', '## Severity calibration', '',
        '_Agent: пройди по каждому high-severity finding и проверь — есть ли независимый контр-аргумент._',
        '']

if (m.get('mode',{}) or {}).get('type') == 'static':
    out += ['## Systematic risks', '',
            '- **Static mode** — no `gh api` calls. Branch protection / security features findings basis: missing config.',
            '- gh CLI not authenticated → `branch_protection`, `security_features` помечены `confidence: low`.',
            '']
else:
    out += ['## Systematic risks', '',
            '- API rate limit may have prevented full enumeration of secrets/environments.',
            '- Some private workflows may not be visible without admin access.',
            '']

(audit_dir / '_adversary_review.md').write_text('\n'.join(out))
(audit_dir / '_known_unknowns.md').write_text(
    '# Known unknowns\n\n## Static-mode limitations (если applicable)\n\n'
    '- [ ] Branch protection — requires `gh auth`\n'
    '- [ ] Settings → Code security — requires `gh auth`\n'
    '- [ ] Secrets list — requires `gh auth` + admin\n'
    '- [ ] Environments — requires `gh auth`\n\n'
    '## Detector limitations\n\n'
    '- [ ] Script injection: regex-based, может промахиваться на сложных interpolations\n'
    '- [ ] OIDC opportunities: detected via secret name patterns\n'
)
(audit_dir / '09a_self_audit.md').write_text(
    '# Phase 09a — Self-Audit\n\nSee `_adversary_review.md` для bias-check.\n'
)

print(f'OK: adversary_review draft ({len(findings)} findings)')
