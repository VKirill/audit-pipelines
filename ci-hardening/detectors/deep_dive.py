#!/usr/bin/env python3
"""Phase 10 — deep_dive skeleton for critical findings."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import get_paths

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='10')
args = ap.parse_args()

audit_dir, _, _, fp, _ = get_paths()
if not fp.exists(): sys.exit(0)

crits = []
for line in fp.read_text().splitlines():
    line = line.strip()
    if not line: continue
    try:
        f = json.loads(line)
        if f.get('severity') == 'critical': crits.append(f)
    except: pass

if not crits:
    print('No critical findings — skip phase 10'); sys.exit(0)

out = ['# Phase 10 — Deep Dive', '', f'**Critical findings:** {len(crits)}', '',
       '> Sections 4 (Fix variants) обязательно заполняется агентом. Pipeline-генерируемая часть = sections 1-3 на основе finding metadata.', '']

for f in crits:
    loc = f.get('location', {})
    out += [f'## {f["id"]}: {f.get("title","?")}', '',
            '### 1. Trace', f'- File: `{loc.get("file","?")}:{loc.get("line","?")}`',
            f'- Action: `{loc.get("action","?")}`' if loc.get('action') else '',
            f'- Symbol: `{loc.get("symbol","?")}`' if loc.get('symbol') else '',
            '',
            '### 2. Exploit reproduction',
            f'> {f.get("exploit_proof", "_(missing — agent must add)_")}',
            '',
            '**Agent: expand into step-by-step scenario.**', '',
            '### 3. Blast radius',
            f'_Impact: {f.get("impact", "?")}_',
            'Agent: укажи affected workflows, secrets exposed, время до detection.', '',
            '### 4. Fix variants',
            '**Variant A (immediate, S):** _agent fills_',
            '**Variant B (proper, M):** _agent fills_',
            '**Variant C (architectural, L):** _agent fills_', '',
            '### 5. Verification',
            'Agent: как проверить что fix работает. (`zizmor` lint? `pinact run`? PR check?)', '',
            '### 6. Recommended next step',
            '_agent fills_', '',
            '---', '']

(audit_dir / '10_deep_dive.md').write_text('\n'.join(out))
print(f'OK: 10_deep_dive.md ({len(crits)} criticals)')
