#!/usr/bin/env python3
"""Global confidence/severity sanity check.

Rules:
- All `high` confidence findings must have confidence_rationale >= 40 chars and non-empty location.lines.
- All `critical` severity findings must have exploit_proof >= 40 chars.
- Distribution sanity: critical > 10% of total -> suspicious.
- Distribution sanity: high > 50% of total -> suspicious (likely overconfidence bias).
"""
import json
import sys
from pathlib import Path
from collections import Counter


def main():
    p = Path('audit/findings.jsonl')
    if not p.exists():
        print('audit/findings.jsonl missing')
        return 1

    findings = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f'line {i}: invalid JSON: {e}')
            return 1

    n = len(findings)
    if n == 0:
        print('no findings (probably bug — empty audit?)')
        return 1

    sev = Counter(f.get('severity', 'unknown') for f in findings)
    conf = Counter(f.get('confidence', 'unknown') for f in findings)

    print(f'Total findings: {n}')
    print(f'  by severity: {dict(sev)}')
    print(f'  by confidence: {dict(conf)}')

    errors = 0

    for f in findings:
        if f.get('confidence') == 'high':
            rat = f.get('confidence_rationale', '') or ''
            if len(rat) < 40:
                print(f'  ERR {f.get("id","?")}: high without rationale (len {len(rat)})')
                errors += 1
            loc = (f.get('location') or {}).get('lines', '')
            if not loc:
                print(f'  ERR {f.get("id","?")}: high without location.lines')
                errors += 1
        if f.get('severity') == 'critical':
            ex = f.get('exploit_proof', '') or ''
            if len(ex) < 40:
                print(f'  ERR {f.get("id","?")}: critical without exploit_proof (len {len(ex)})')
                errors += 1

    crit_pct = sev.get('critical', 0) / n
    high_pct = conf.get('high', 0) / n
    if crit_pct > 0.10:
        print(f'  WARN critical share = {crit_pct:.1%} (>10%) — review for over-classification')
    if high_pct > 0.50:
        print(f'  WARN high-confidence share = {high_pct:.1%} (>50%) — possible overconfidence (Kahneman §24)')

    if errors:
        print(f'FAIL: {errors} error(s)')
        return 1
    print('OK: confidence/severity rules pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
