#!/usr/bin/env python3
"""${{ github.event.* }} interpolated в run: blocks — script injection."""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, iter_workflow_files

DANGEROUS_EXPR = re.compile(r'\$\{\{\s*github\.event\.(?:pull_request|issue|comment|review|push)\.[^}]+\}\}', re.IGNORECASE)
DANGEROUS_HEAD_REF = re.compile(r'\$\{\{\s*github\.head_ref\s*\}\}')

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='03')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

hits = []
for f in iter_workflow_files(project_root):
    text = f.read_text()
    in_run_block = False
    for i, line in enumerate(text.splitlines(), 1):
        # Track run: blocks (heuristic — single-line "run: |" or "run: <single>")
        if re.search(r'^\s*run:\s*[|>]?\s*$', line):
            in_run_block = True
            continue
        if in_run_block and not line.startswith((' ', '\t')) and line.strip():
            in_run_block = False
        # Check for dangerous interpolations in any line (broader detection)
        if DANGEROUS_EXPR.search(line) or DANGEROUS_HEAD_REF.search(line):
            expr = DANGEROUS_EXPR.search(line) or DANGEROUS_HEAD_REF.search(line)
            hits.append({'file': str(f.relative_to(project_root)), 'line': i,
                         'expression': expr.group(0), 'in_run': in_run_block})

md = ['# Script injection risks', '', f'Total: {len(hits)}', '']
for h in hits:
    md.append(f'- {h["file"]}:{h["line"]} — `{h["expression"]}` (in run: {h["in_run"]})')
write_evidence(args.phase, 'script_injection.md', '\n'.join(md))

for h in hits:
    sev = 'critical' if h['in_run'] else 'high'
    append_finding({
        'phase': args.phase, 'category': 'workflow',
        'subcategory': 'script-injection',
        'severity': sev, 'confidence': 'high' if h['in_run'] else 'medium',
        'title': f'Script injection risk: {h["expression"]}',
        'location': {'file': h['file'], 'line': h['line']},
        'evidence': f'{h["file"]}:{h["line"]} — interpolation `{h["expression"]}` ' + ('inside `run:` block' if h['in_run'] else 'in workflow context'),
        'confidence_rationale': 'Direct interpolation of user-controllable github.event.* fields. PR title/body/comments — attacker-controlled.',
        'impact': 'Attacker creates PR with malicious title/body containing shell metacharacters → arbitrary code execution в runner с access к secrets.',
        'recommendation': '''1) Передать через env var:
```yaml
env:
  PR_TITLE: ${{ github.event.pull_request.title }}
run: |
  echo "$PR_TITLE"   # double quotes prevent injection
```
2) Использовать zizmor lint в CI.''',
        'effort': 'S',
        'references': ['zizmor docs', 'GitHub Docs: Hardening with security best practices'],
        'exploit_proof': (f'Attacker creates PR with title `; rm -rf / # `. When workflow runs `echo "PR title: {h["expression"]}"`, '
                          f'shell receives `echo "PR title: "; rm -rf / # "` → arbitrary code execution.') if sev == 'critical' else None
    })
    
print(f'OK: {len(hits)} script-injection risks')
