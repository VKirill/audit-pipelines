#!/usr/bin/env python3
"""Produce audit/_meta.json — machine summary."""
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sh(cmd, default=''):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return default


def main():
    audit = Path('audit')
    findings_path = audit / 'findings.jsonl'
    if not audit.exists() or not findings_path.exists():
        print('audit/ or findings.jsonl missing', file=sys.stderr)
        return 1

    findings = []
    for line in findings_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    sev = Counter(f.get('severity', 'unknown') for f in findings)
    cat = Counter(f.get('category', 'unknown') for f in findings)
    blockers = [f.get('id') for f in findings if f.get('severity') == 'critical']

    phases_done = []
    for p in sorted(audit.glob('*.md')):
        m = re.match(r'^(\d{2}[a-z]?)_', p.name)
        if m:
            phases_done.append(m.group(1))
    phases_done = sorted(set(phases_done))

    mode = 'static'
    size = 'M'
    mem = Path('.serena/memories/db_audit_phase_00.md')
    if not mem.exists():
        mem = Path('.serena/memories/db_audit_phase_00')
    if mem.exists():
        text = mem.read_text(errors='ignore')
        m = re.search(r'mode:\s*(\w+)', text)
        if m: mode = m.group(1)
        m = re.search(r'size:\s*([A-Z]+)', text)
        if m: size = m.group(1)

    stack_text = ''
    sp = Path('audit/evidence/00_setup/stack_detection.txt')
    if sp.exists():
        stack_text = sp.read_text(errors='ignore')
    orms = re.search(r'orms=([^\n]*)', stack_text)
    dbs = re.search(r'dbs=([^\n]*)', stack_text)
    orms = orms.group(1).split(',') if orms and orms.group(1) else []
    dbs = dbs.group(1).split(',') if dbs and dbs.group(1) else []

    if sev.get('critical', 0) > 0:
        verdict = 'fail'
    elif sev.get('high', 0) > 10:
        verdict = 'pass-with-conditions'
    else:
        verdict = 'pass'

    out = {
        'version': '1.0',
        'pipeline': 'database-audit',
        'pipeline_version': 'v1',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'project': {
            'path': os.getcwd(),
            'size': size,
            'git_head': sh('git rev-parse HEAD'),
            'branch': sh('git rev-parse --abbrev-ref HEAD'),
        },
        'stack': {
            'databases': [d for d in dbs if d],
            'orms': [o for o in orms if o],
        },
        'mode': mode,
        'phases_completed': phases_done,
        'findings_total': len(findings),
        'by_severity': dict(sev),
        'by_category': dict(cat),
        'verdict': verdict,
        'blockers': blockers,
    }
    Path('audit/_meta.json').write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
