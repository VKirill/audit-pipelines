#!/usr/bin/env python3
"""Compare audit results across multiple projects.

Usage:
  compare_projects.py /path/to/project-a /path/to/project-b [/path/to/project-c ...]

Each project must have database-audit/results/findings.jsonl + _meta.json.

Output: comparison report to stdout (markdown).
Useful for: monorepo with multiple sub-projects, multi-tenant platforms,
multi-team comparisons.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_project(path):
    p = Path(path)
    findings_file = p / 'database-audit' / 'results' / 'findings.jsonl'
    meta_file = p / 'database-audit' / 'results' / '_meta.json'

    if not findings_file.exists():
        return None, f'no findings.jsonl in {path}'

    findings = []
    for line in findings_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    meta = {}
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
        except Exception:
            pass

    return {'path': str(p), 'name': p.name, 'findings': findings, 'meta': meta}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('projects', nargs='+', help='Paths to project roots')
    ap.add_argument('--output', '-o', help='Output file (default: stdout)')
    args = ap.parse_args()

    if len(args.projects) < 2:
        print('Need at least 2 projects to compare', file=sys.stderr)
        return 1

    projects = []
    for path in args.projects:
        proj, err = load_project(path)
        if err:
            print(f'WARN: skipping {path}: {err}', file=sys.stderr)
            continue
        projects.append(proj)

    if len(projects) < 2:
        print('Less than 2 valid projects after loading', file=sys.stderr)
        return 1

    out = ['# Multi-Project Audit Comparison', '',
           f'Comparing {len(projects)} projects:', '']
    for p in projects:
        verdict = p['meta'].get('verdict', '?')
        total = len(p['findings'])
        out.append(f'- **{p["name"]}** — verdict: `{verdict}`, findings: {total}')
    out.append('')

    # Severity matrix
    out.append('## Severity matrix')
    out.append('')
    out.append('| Project | Critical | High | Medium | Low | Total |')
    out.append('|---------|---------:|-----:|-------:|----:|------:|')
    for p in projects:
        sev = Counter(f.get('severity') for f in p['findings'])
        out.append(f'| {p["name"]} | {sev.get("critical", 0)} | {sev.get("high", 0)} | '
                   f'{sev.get("medium", 0)} | {sev.get("low", 0)} | {len(p["findings"])} |')
    out.append('')

    # Category matrix
    out.append('## Category matrix')
    out.append('')
    all_cats = set()
    for p in projects:
        for f in p['findings']:
            all_cats.add(f.get('category', 'unknown'))
    all_cats = sorted(all_cats)

    header = '| Project | ' + ' | '.join(all_cats) + ' |'
    sep = '|---------|' + '|'.join(['------:'] * len(all_cats)) + '|'
    out.append(header)
    out.append(sep)
    for p in projects:
        cat = Counter(f.get('category') for f in p['findings'])
        row = f'| {p["name"]} | ' + ' | '.join(str(cat.get(c, 0)) for c in all_cats) + ' |'
        out.append(row)
    out.append('')

    # Common patterns
    out.append('## Common subcategories (issues across multiple projects)')
    out.append('')
    subcat_by_proj = defaultdict(set)
    for p in projects:
        for f in p['findings']:
            subcat_by_proj[f.get('subcategory', 'unknown')].add(p['name'])

    common = [(sc, projs) for sc, projs in subcat_by_proj.items() if len(projs) > 1]
    common.sort(key=lambda x: -len(x[1]))

    if common:
        out.append('| Subcategory | Found in |')
        out.append('|-------------|----------|')
        for sc, projs in common[:20]:
            out.append(f'| `{sc}` | {len(projs)} projects: {", ".join(sorted(projs))} |')
    else:
        out.append('_No common subcategories across projects._')
    out.append('')

    # Unique to each project
    out.append('## Unique findings (subcategories only in one project)')
    out.append('')
    for p in projects:
        unique = set()
        for f in p['findings']:
            sc = f.get('subcategory', 'unknown')
            if subcat_by_proj[sc] == {p['name']}:
                unique.add(sc)
        if unique:
            out.append(f'### {p["name"]}')
            for sc in sorted(unique):
                count = sum(1 for f in p['findings'] if f.get('subcategory') == sc)
                out.append(f'- `{sc}` × {count}')
            out.append('')

    # Worst offenders
    out.append('## Worst offenders (by total critical+high)')
    out.append('')
    ranked = []
    for p in projects:
        sev = Counter(f.get('severity') for f in p['findings'])
        score = sev.get('critical', 0) * 4 + sev.get('high', 0)
        ranked.append((p['name'], score, sev.get('critical', 0), sev.get('high', 0)))
    ranked.sort(key=lambda x: -x[1])

    out.append('| Rank | Project | Score (4×crit + high) | Crit | High |')
    out.append('|------|---------|----------------------:|-----:|-----:|')
    for i, (name, score, crit, hgh) in enumerate(ranked, 1):
        out.append(f'| {i} | {name} | {score} | {crit} | {hgh} |')
    out.append('')

    # Common money/security blockers
    out.append('## Critical money/security findings (cross-project)')
    out.append('')
    for p in projects:
        crits = [f for f in p['findings']
                 if f.get('severity') == 'critical'
                 and f.get('category') in ('money', 'security', 'transaction', 'pii')]
        if crits:
            out.append(f'### {p["name"]} ({len(crits)} critical)')
            for f in crits[:10]:
                loc = f.get('location', {})
                out.append(f'- `{f["id"]}` — {f.get("title", "?")}: '
                           f'`{loc.get("file","?")}:{loc.get("lines","?")}`')
            out.append('')

    text = '\n'.join(out)
    if args.output:
        Path(args.output).write_text(text)
        print(f'Wrote {args.output}')
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
