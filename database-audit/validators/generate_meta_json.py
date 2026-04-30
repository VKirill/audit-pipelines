#!/usr/bin/env python3
"""Generate AUDIT_DIR/_meta.json — machine summary. Reads manifest for stack details."""
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def sh(cmd, default=''):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return default


def main():
    audit_dir = Path(os.environ.get('AUDIT_DIR', 'audit'))
    manifest_path = Path(os.environ.get('MANIFEST', 'database-audit/manifest.yml'))
    findings_path = audit_dir / 'findings.jsonl'

    if not audit_dir.exists() or not findings_path.exists():
        print(f'{audit_dir}/ or findings.jsonl missing', file=sys.stderr)
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

    phases_done = set()
    for p in sorted(audit_dir.glob('*.md')):
        m = re.match(r'^(\d{2}[a-z]?)_', p.name)
        if m:
            phases_done.add(m.group(1))
    phases_done = sorted(phases_done)

    manifest = {}
    if manifest_path.exists() and yaml is not None:
        try:
            manifest = yaml.safe_load(manifest_path.read_text()) or {}
        except Exception:
            pass

    project = manifest.get('project', {}) or {}
    stack = manifest.get('stack', {}) or {}
    mode = manifest.get('mode', {}) or {}

    if sev.get('critical', 0) > 0:
        verdict = 'fail'
    elif sev.get('high', 0) > 10:
        verdict = 'pass-with-conditions'
    else:
        verdict = 'pass'

    out = {
        'version': '1.0',
        'pipeline': 'database-audit',
        'pipeline_version': 'v4',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'project': {
            'path': project.get('root') or os.getcwd(),
            'name': project.get('name'),
            'type': project.get('type'),
            'size': project.get('size', 'M'),
            'git_head': project.get('git_head') or sh('git rev-parse HEAD'),
            'branch': project.get('git_branch') or sh('git rev-parse --abbrev-ref HEAD'),
        },
        'stack': {
            'primary_db': stack.get('primary_db'),
            'primary_orm': stack.get('primary_orm'),
            'also_used_dbs': stack.get('also_used_dbs', []),
            'also_used_orms': stack.get('also_used_orms', []),
        },
        'mode': mode.get('type', 'static'),
        'phases_completed': phases_done,
        'findings_total': len(findings),
        'by_severity': dict(sev),
        'by_category': dict(cat),
        'verdict': verdict,
        'blockers': blockers,
    }
    (audit_dir / '_meta.json').write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps(out, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
