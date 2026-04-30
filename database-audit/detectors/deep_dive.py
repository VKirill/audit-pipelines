#!/usr/bin/env python3
"""Phase 11 — generates skeleton 11_deep_dive.md with one section per critical finding."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import get_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='11')
    args = ap.parse_args()

    audit_dir, _, _, fp, _ = get_paths()
    if not fp.exists():
        return 0

    crits = []
    for line in fp.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            f = json.loads(line)
            if f.get('severity') == 'critical':
                crits.append(f)
        except Exception:
            pass

    if not crits:
        print('No critical findings — skip phase 11')
        return 0

    out = ['# Phase 11 — Deep Dive', '', f'Critical findings: {len(crits)}', '']
    for f in crits:
        loc = f.get('location', {})
        out += [f'## {f["id"]}: {f.get("title","?")}', '',
                '### 1. Trace', f'- Entry points: _agent fills_',
                f'- Code path: `{loc.get("file","?")}:{loc.get("lines","?")}`',
                '- Affected DB objects: _agent fills_', '',
                '### 2. Exploit reproduction', f'_Already in finding.exploit_proof: {f.get("exploit_proof","")[:200]}_', '',
                '### 3. Blast radius', '_agent fills_', '',
                '### 4. Fix variants',
                '- Variant A (quick): _agent fills_ — effort S',
                '- Variant B (proper): _agent fills_ — effort M',
                '- Variant C (architectural): _agent fills_ — effort L', '',
                '### 5. Test strategy', '_agent fills_', '',
                '### 6. Recommended next step', '_agent fills_', '', '---', '']

    (audit_dir / '11_deep_dive.md').write_text('\n'.join(out))
    print(f'OK: 11_deep_dive.md skeleton ({len(crits)} criticals)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
