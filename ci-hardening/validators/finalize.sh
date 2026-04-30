#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$PIPELINE_DIR/lib/env.sh"

require_cmd jq
require_cmd python3

errors=0
echo "==> finalize.sh — final gate"

# Required artefacts
for f in ROADMAP.md _adversary_review.md _known_unknowns.md; do
  [[ -f "$AUDIT_DIR/$f" ]] || { c_red "missing $AUDIT_DIR/$f"; errors=$((errors+1)); }
done

# Generate _meta.json
python3 - <<PYEOF
import json, os, yaml
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

audit_dir = Path('$AUDIT_DIR')
findings = []
fp = audit_dir / 'findings.jsonl'
if fp.exists():
    for line in fp.read_text().splitlines():
        line = line.strip()
        if not line: continue
        try: findings.append(json.loads(line))
        except: pass

sev = Counter(f.get('severity') for f in findings)
cat = Counter(f.get('category') for f in findings)
verdict = 'fail' if sev.get('critical',0) > 0 else ('pass-with-conditions' if sev.get('high',0) > 5 else 'pass')

manifest_path = Path('$MANIFEST')
m = {}
if manifest_path.exists():
    m = yaml.safe_load(manifest_path.read_text()) or {}

out = {
    'version': '1.0',
    'pipeline': 'ci-hardening',
    'pipeline_version': 'v2',
    'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'project': m.get('project', {}),
    'github': m.get('github', {}),
    'mode': (m.get('mode',{}) or {}).get('type', 'static'),
    'findings_total': len(findings),
    'by_severity': dict(sev),
    'by_category': dict(cat),
    'verdict': verdict,
    'blockers': [f['id'] for f in findings if f.get('severity') == 'critical']
}
(audit_dir / '_meta.json').write_text(json.dumps(out, indent=2, ensure_ascii=False))
print(f"OK: _meta.json — verdict={verdict}, findings={len(findings)}")
PYEOF

if (( errors > 0 )); then
  c_red "FAIL: $errors error(s)"; exit 1
fi
c_green "PASS: pipeline complete"
