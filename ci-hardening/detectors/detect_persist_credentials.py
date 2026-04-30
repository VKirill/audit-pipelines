#!/usr/bin/env python3
"""actions/checkout без persist-credentials: false (token остаётся в .git/config)."""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence, iter_workflow_files

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='03')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

issues = []
for f in iter_workflow_files(project_root):
    text = f.read_text()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not re.search(r'uses:\s*actions/checkout', line):
            continue
        # Look in next 15 lines for `with:` block
        next_block = '\n'.join(lines[i:i+15])
        if 'persist-credentials: false' not in next_block:
            issues.append({'file': str(f.relative_to(project_root)), 'line': i+1})

md = ['# persist-credentials check', '', f'Total: {len(issues)}', '']
for i in issues:
    md.append(f'- {i["file"]}:{i["line"]} — actions/checkout без `persist-credentials: false`')
write_evidence(args.phase, 'persist_credentials.md', '\n'.join(md))

for i in issues:
    append_finding({
        'phase': args.phase, 'category': 'permissions',
        'subcategory': 'persist-credentials-default',
        'severity': 'medium', 'confidence': 'high',
        'title': f'actions/checkout без `persist-credentials: false`',
        'location': {'file': i['file'], 'line': i['line']},
        'evidence': f'{i["file"]}:{i["line"]} — actions/checkout call. Default persist-credentials=true → GITHUB_TOKEN сохраняется в .git/config.',
        'confidence_rationale': 'Lines verified through file read; persist-credentials option absent in nearby `with:` block.',
        'impact': 'GITHUB_TOKEN остаётся в `.git/config` после checkout. Любой subsequent step (тест, build) может прочитать его и leak в logs/artifacts.',
        'recommendation': '''Добавить в `with:` блок checkout:
```yaml
- uses: actions/checkout@<sha>
  with:
    persist-credentials: false
```
Если нужен push в этот же repo — оставить, но изолировать в отдельный job.''',
        'effort': 'S',
        'references': ['actions/checkout README']
    })

print(f'OK: {len(issues)} persist-credentials issues')
