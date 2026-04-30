#!/usr/bin/env python3
"""Phase 11 — Auto-populates deep_dive sections using GitNexus when available.

Auto-fills:
  Section 1: Trace — via gitnexus context
  Section 3: Blast radius — via gitnexus impact upstream

Agent fills (creative):
  Section 2: Exploit reproduction (initial draft from finding.exploit_proof)
  Section 4: Fix variants (3 levels)
  Section 5: Test strategy
  Section 6: Recommended next step
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import get_paths, load_manifest


def gitnexus_available():
    return shutil.which('gitnexus') is not None or shutil.which('npx') is not None


def run_gitnexus(args, timeout=20):
    """Run gitnexus CLI; return stdout or None."""
    if not gitnexus_available():
        return None
    cmd = ['gitnexus'] + args if shutil.which('gitnexus') else ['npx', 'gitnexus'] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def gitnexus_impact(symbol, depth=3):
    out = run_gitnexus(['impact', '--direction', 'upstream', '--depth', str(depth), symbol])
    return out or '_GitNexus impact unavailable — agent should fill manually_'


def gitnexus_context(symbol):
    out = run_gitnexus(['context', symbol])
    return out or '_GitNexus context unavailable — agent should fill manually_'


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
        if not line: continue
        try:
            f = json.loads(line)
            if f.get('severity') == 'critical':
                crits.append(f)
        except Exception:
            pass

    if not crits:
        print('No critical findings — phase 11 skip')
        return 0

    out = ['# Phase 11 — Deep Dive', '', f'**Critical findings:** {len(crits)}',
           '', '> Sections 1 and 3 are auto-populated via GitNexus (impact/context).',
           '> Agent must fill sections 2/4/5/6 with creative reasoning.', '']

    for f in crits:
        loc = f.get('location') or {}
        symbol = loc.get('symbol') or loc.get('db_object') or '?'
        file = loc.get('file', '?')
        lines = loc.get('lines', '?')

        out += [f'## {f["id"]}: {f.get("title","?")}', '', '### 1. Trace', '']

        if symbol and symbol != '?' and symbol != 'multiple':
            ctx = gitnexus_context(symbol)
            out += ['**GitNexus context:**', '```', ctx[:3000].rstrip(), '```', '']
        out += [f'- Code path: `{file}:{lines}`',
                f'- Affected DB objects: `{loc.get("db_object","?")}`',
                '']

        out += ['### 2. Exploit reproduction', '',
                f'_Initial draft from finding.exploit_proof:_',
                '',
                f'> {f.get("exploit_proof", "_(missing — agent must add)_")}',
                '',
                '**Agent: expand into step-by-step reproducible scenario.**', '']

        out += ['### 3. Blast radius (auto-populated via GitNexus)', '']
        if symbol and symbol != '?' and symbol != 'multiple':
            impact = gitnexus_impact(symbol)
            out += ['**GitNexus impact upstream (depth=3):**', '```', impact[:5000].rstrip(), '```', '']
        out += ['**Agent: enrich with business impact estimation (rows affected, $ at risk).**', '']

        out += ['### 4. Fix variants', '',
                '**Variant A (quick mitigation, effort: S):** _agent fills_',
                '**Variant B (proper fix, effort: M):** _agent fills_',
                '**Variant C (architectural, effort: L-XL):** _agent fills_',
                '',
                '### 5. Test strategy', '_agent fills: regression test, property test, integration test_',
                '',
                '### 6. Recommended next step', '_agent fills with rationale_',
                '', '---', '']

    (audit_dir / '11_deep_dive.md').write_text('\n'.join(out))
    print(f'OK: 11_deep_dive.md — {len(crits)} criticals, sections 1/3 auto-populated via GitNexus')
    return 0


if __name__ == '__main__':
    sys.exit(main())
