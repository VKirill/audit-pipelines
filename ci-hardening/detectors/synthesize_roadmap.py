#!/usr/bin/env python3
"""Phase 09 — generate ROADMAP.md + auto-TL;DR for ci-hardening."""
import argparse, json, os, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths

SEV_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='09')
args = ap.parse_args()

audit_dir, _, _, fp, _ = get_paths()
if not fp.exists():
    print('No findings.'); sys.exit(0)

findings = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
findings.sort(key=lambda f: (SEV_ORDER.get(f.get('severity'), 9), f.get('id','')))

sev = Counter(f.get('severity') for f in findings)
cat = Counter(f.get('category') for f in findings)
verdict = 'fail' if sev.get('critical', 0) > 0 else ('pass-with-conditions' if sev.get('high', 0) > 5 else 'pass')

m = load_manifest()
gh = m.get('github', {})
out = [f'# 🔒 CI Hardening ROADMAP', '',
       f'**Repo:** {gh.get("owner","?")}/{gh.get("repo","?")}',
       f'**Default branch:** {gh.get("default_branch","main")}',
       f'**Visibility:** {gh.get("visibility","unknown")}',
       f'**Mode:** {(m.get("mode",{}) or {}).get("type","static")}',
       f'**Date:** {os.popen("date -u +%Y-%m-%d").read().strip()}',
       '',
       f'**Verdict:** `{verdict}`',
       f'**Findings:** {len(findings)} (critical: {sev.get("critical",0)}, high: {sev.get("high",0)}, medium: {sev.get("medium",0)}, low: {sev.get("low",0)})',
       '', '## TL;DR', '']

if sev.get('critical', 0):
    out.append(f'- **{sev["critical"]} critical** — supply-chain / script injection / branch-protection недостатки. Должны быть pofiксены до production deploy.')

cat_supply = sum(1 for f in findings if f.get('category') == 'supply-chain')
if cat_supply:
    out.append(f'- **{cat_supply} unpinned actions** — главный supply-chain риск (tj-actions, trivy-action style)')

cat_perm = sum(1 for f in findings if f.get('category') == 'permissions')
if cat_perm:
    out.append(f'- **{cat_perm} permission issues** — workflows без explicit `contents: read` дефолта')

cat_brn = sum(1 for f in findings if f.get('category') == 'branch-protection')
if cat_brn:
    out.append(f'- **Branch protection issues** — default branch недостаточно защищён')

cat_set = sum(1 for f in findings if f.get('category') == 'settings')
if cat_set:
    out.append(f'- **{cat_set} GitHub security features** — Dependabot/Secret scanning/Code scanning отключено')

out.append('')

# Phase 0 — Foundation
out.append('## Phase 0 — Foundation (полдня)')
out.append('')
out.append('Базовый CI без блокировок процессов.')
out.append('')
ph0 = [f for f in findings if f.get('severity') in ('critical', 'high') and f.get('category') in ('supply-chain', 'permissions')]
for f in ph0[:10]:
    loc = f.get('location', {})
    out.append(f'- **{f["id"]}** [{f["severity"]}] — {f["title"]} · `{loc.get("file","?")}:{loc.get("line","?")}`')
out.append('')

# Phase 1 — Safety net
out.append('## Phase 1 — Safety Net (1-3 дня)')
out.append('')
ph1 = [f for f in findings if f.get('category') in ('settings', 'workflow', 'sast')]
for f in ph1[:10]:
    out.append(f'- **{f["id"]}** [{f["severity"]}] — {f["title"]}')
out.append('')

# Phase 2 — Quality gates
out.append('## Phase 2 — Quality Gates (неделя)')
out.append('')
ph2 = [f for f in findings if f.get('category') in ('branch-protection', 'dependencies', 'secrets')]
for f in ph2[:10]:
    out.append(f'- **{f["id"]}** [{f["severity"]}] — {f["title"]}')
out.append('')

# Phase 3 — Advanced
out.append('## Phase 3 — Advanced (по необходимости)')
out.append('')
out.append('- OpenSSF Scorecard (для public repo)')
out.append('- SBOM + signing (cosign)')
out.append('- Harden-Runner block mode (после 2 недель audit)')
out.append('- Reusable workflows для multi-repo')
out.append('')

out.append('## Карта по категориям')
out.append('')
cat_sev = defaultdict(lambda: defaultdict(int))
for f in findings:
    cat_sev[f.get('category','?')][f.get('severity','?')] += 1
out.append('| Category | Critical | High | Medium | Low |')
out.append('|----------|---------:|-----:|-------:|----:|')
for c in sorted(cat_sev):
    cs = cat_sev[c]
    out.append(f'| {c} | {cs.get("critical",0)} | {cs.get("high",0)} | {cs.get("medium",0)} | {cs.get("low",0)} |')

out.append('')
out.append('## Применить proposed changes')
out.append('')
out.append('Готовые правки в `ci-hardening/results/proposed-changes/` (если сгенерированы).')
out.append('')
out.append('```bash')
out.append('cp -r ci-hardening/results/proposed-changes/.github/* .github/')
out.append('git checkout -b ci/harden')
out.append('git add .github/')
out.append('git commit -m "ci: harden workflows (audit findings)"')
out.append('git push -u origin ci/harden')
out.append('gh pr create --title "ci: harden" --body-file ci-hardening/results/proposed-changes/README.md')
out.append('```')

(audit_dir / 'ROADMAP.md').write_text('\n'.join(out))

# Phase report
(audit_dir / '09_synthesis.md').write_text(
    f'# Phase 09 — Synthesis\n\n{len(findings)} findings, verdict: `{verdict}`.\n'
    f'See ROADMAP.md for prioritized output.\n'
)
print(f'OK: ROADMAP.md ({len(findings)} findings)')
