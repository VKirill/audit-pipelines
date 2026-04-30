#!/usr/bin/env python3
"""Phase 10 — generate ROADMAP.md skeleton with auto-TL;DR + 10_synthesis.md report."""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths


SEVERITY_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}


def auto_tldr(findings, manifest):
    """Generate 5-7 bullet points covering the most critical issues + verdict."""
    by_sev = Counter(f.get('severity') for f in findings)
    by_cat = Counter(f.get('category') for f in findings)
    crits = [f for f in findings if f.get('severity') == 'critical']

    bullets = []
    if crits:
        bullets.append(f'**{len(crits)} critical findings** — приоритет №1: ' +
                       ', '.join(sorted(set(c.get('subcategory', '?') for c in crits))[:5]))

    # Money critical
    money_crits = [c for c in crits if c.get('category') in ('money', 'transaction')]
    if money_crits:
        bullets.append(f'**Money/transaction integrity нарушена в {len(money_crits)} местах** — '
                       f'fix перед любым деплоем money-features')

    # PII
    pii_unenc = [f for f in findings if f.get('category') == 'security' and 'pii' in f.get('subcategory', '')]
    if pii_unenc:
        bullets.append(f'**{len(pii_unenc)} PII колонок без шифрования** — GDPR risk')

    # Schema
    schema_high = sum(1 for f in findings if f.get('category') == 'schema' and f.get('severity') in ('critical', 'high'))
    if schema_high:
        bullets.append(f'**{schema_high} проблем в дизайне схемы** (типы/нормализация)')

    # Indexes
    fk_no_idx = sum(1 for f in findings if f.get('category') == 'index' and 'fk-no-index' in f.get('subcategory', ''))
    if fk_no_idx:
        bullets.append(f'**{fk_no_idx} FK без индекса** — причина медленных JOIN')

    # Migrations
    mig_dangerous = sum(1 for f in findings if f.get('category') == 'migration')
    if mig_dangerous:
        bullets.append(f'**{mig_dangerous} опасных миграций** — нужен multi-step deploy')

    # Mode
    mode = (manifest.get('mode', {}) or {}).get('type', 'static')
    if mode == 'static':
        bullets.append('**Static mode** — рекомендуется live-прогон с DATABASE_URL для подтверждения plan-related findings')

    return bullets[:7]


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
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.get('severity'), 9), f.get('id', '')))

    sev = Counter(f.get('severity') for f in findings)
    cat = Counter(f.get('category') for f in findings)

    if sev.get('critical', 0) > 0:
        verdict = 'fail'
    elif sev.get('high', 0) > 10:
        verdict = 'pass-with-conditions'
    else:
        verdict = 'pass'

    manifest = load_manifest()
    project = manifest.get('project', {}) or {}
    stack = manifest.get('stack', {}) or {}

    out = [
        f'# Database Audit ROADMAP',
        '',
        f'**Project:** {project.get("name", "?")}  |  '
        f'**Stack:** {stack.get("primary_db", "?")} + {stack.get("primary_orm", "?")}  |  '
        f'**Date:** {os.popen("date -u +%Y-%m-%d").read().strip()}  |  '
        f'**Mode:** {(manifest.get("mode", {}) or {}).get("type", "static")}',
        '',
        f'**Verdict:** `{verdict}`',
        '',
        f'**Findings:** {len(findings)} '
        f'(critical: {sev.get("critical", 0)}, high: {sev.get("high", 0)}, '
        f'medium: {sev.get("medium", 0)}, low: {sev.get("low", 0)})',
        '',
        '## TL;DR',
        '',
    ]
    for b in auto_tldr(findings, manifest):
        out.append(f'- {b}')
    out.append('')

    # 🔴 Now — critical + high with low effort
    out.append('## 🔴 Сейчас (Now)')
    out.append('')
    now_count = 0
    for f in findings:
        if f.get('severity') in ('critical', 'high') and f.get('effort', 'M') in ('S', 'M'):
            loc = f.get('location', {})
            out.append(f'### {f["id"]} — {f.get("title", "?")} [{f["severity"]}]')
            out.append(f'**Где:** `{loc.get("file", "?")}:{loc.get("lines", "?")}`')
            if loc.get('db_object'):
                out.append(f'**DB:** `{loc["db_object"]}`')
            out.append(f'**Почему сейчас:** {f.get("impact", "")}')
            out.append(f'**Как:** {f.get("recommendation", "")}')
            out.append(f'**Effort:** {f.get("effort", "?")}')
            out.append(f'**Источник:** {", ".join(f.get("references", []))}')
            out.append('')
            now_count += 1
            if now_count >= 15: break

    out.append('## 🟡 Дальше (Next)')
    out.append('')
    next_count = 0
    for f in findings:
        if f.get('severity') in ('high', 'medium') and f.get('effort', 'M') in ('M', 'L') and f not in findings[:now_count]:
            loc = f.get('location', {})
            out.append(f'### {f["id"]} — {f.get("title", "?")} [{f["severity"]}]')
            out.append(f'**Где:** `{loc.get("file", "?")}:{loc.get("lines", "?")}`')
            out.append(f'**Effort:** {f.get("effort", "?")}')
            out.append('')
            next_count += 1
            if next_count >= 15: break

    out.append('## 🟢 Потом (Later)')
    out.append('')
    out.append('Низкоприоритетный долг — мониторить, не срочно фиксить.')
    out.append('')
    later = [f for f in findings if f.get('severity') == 'low' or f.get('effort') in ('L', 'XL')]
    for f in later[:20]:
        out.append(f'- {f["id"]}: {f.get("title", "?")} [{f.get("severity", "?")}]')
    out.append('')

    out.append('## Карта по категориям')
    out.append('')
    out.append('| Category | Critical | High | Medium | Low |')
    out.append('|----------|----------|------|--------|-----|')
    cat_sev = defaultdict(lambda: defaultdict(int))
    for f in findings:
        cat_sev[f.get('category', '?')][f.get('severity', '?')] += 1
    for c in sorted(cat_sev):
        cs = cat_sev[c]
        out.append(f'| {c} | {cs.get("critical", 0)} | {cs.get("high", 0)} | '
                   f'{cs.get("medium", 0)} | {cs.get("low", 0)} |')

    out.append('')
    out.append('## Источники')
    out.append('')
    refs = set()
    for f in findings:
        for r in f.get('references', []):
            refs.add(r)
    for r in sorted(refs):
        out.append(f'- {r}')

    (audit_dir / 'ROADMAP.md').write_text('\n'.join(out))

    # Phase 10 report
    (audit_dir / '10_synthesis.md').write_text(
        f'# Phase 10 — Synthesis\n\n'
        f'**Source books:** Sadalage & Ambler — sequencing; SRE Book Ch. 26.\n'
        f'**Mode:** {(manifest.get("mode", {}) or {}).get("type", "static")}\n\n'
        f'## 1. Что сделано\n\n'
        f'- Auto-generated ROADMAP.md with TL;DR\n'
        f'- {len(findings)} findings prioritized by severity × effort\n'
        f'- Categorical map ({len(cat)} categories)\n'
        f'- Verdict: `{verdict}`\n\n'
        f'## 2. Сводка\n\n'
        f'| Severity | Count |\n|----------|-------|\n'
        + '\n'.join(f'| {k} | {v} |' for k, v in sev.most_common())
        + '\n\n## 3. Артефакты\n\n- `audit/ROADMAP.md`\n'
    )
    print(f'OK: ROADMAP.md + 10_synthesis.md ({len(findings)} findings)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
