#!/usr/bin/env python3
"""Generate ROADMAP.md skeleton from findings.jsonl. Agent fills in narrative."""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='10')
    args = ap.parse_args()

    audit_dir, _, _, fp, _ = get_paths()
    if not fp.exists():
        print('No findings.')
        return 0

    findings = [json.loads(l) for l in fp.read_text().splitlines() if l.strip()]
    findings.sort(key=lambda f: ({'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(f.get('severity'), 9), f.get('id', '')))

    sev = Counter(f.get('severity') for f in findings)
    cat = Counter(f.get('category') for f in findings)

    if sev.get('critical', 0) > 0:
        verdict = 'fail'
    elif sev.get('high', 0) > 10:
        verdict = 'pass-with-conditions'
    else:
        verdict = 'pass'

    out = [f'# Database Audit ROADMAP', '',
           f'**Verdict:** `{verdict}`', '',
           f'**Findings:** {len(findings)} '
           f'(critical: {sev.get("critical",0)}, high: {sev.get("high",0)}, '
           f'medium: {sev.get("medium",0)}, low: {sev.get("low",0)})', '',
           '## TL;DR', '',
           '_Заполняется агентом — 5-7 пунктов главного._', '',
           '## 🔴 Сейчас (Now)', '']
    for f in findings:
        if f.get('severity') in ('critical', 'high'):
            loc = f.get('location', {})
            out.append(f'### {f["id"]} — {f.get("title","?")} [{f["severity"]}]')
            out.append(f'**Где:** `{loc.get("file","?")}:{loc.get("lines","?")}`')
            out.append(f'**Как:** {f.get("recommendation","")}')
            out.append(f'**Effort:** {f.get("effort","?")}')
            out.append(f'**Источник:** {", ".join(f.get("references",[]))}')
            out.append('')
        if len([x for x in findings if x.get("severity") in ("critical","high")]) > 0 and f == findings[5]:
            break

    out.append('## 🟡 Дальше (Next)')
    out.append('_Medium-severity и подбираемые из high._')
    out.append('')
    out.append('## 🟢 Потом (Later)')
    out.append('_Долг и оптимизации._')
    out.append('')
    out.append('## Карта по категориям')
    out.append('| Category | Count |')
    out.append('|----------|-------|')
    for c, n in cat.most_common():
        out.append(f'| {c} | {n} |')

    (audit_dir / 'ROADMAP.md').write_text('\n'.join(out))
    print(f'OK: ROADMAP.md skeleton written ({len(findings)} findings)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
