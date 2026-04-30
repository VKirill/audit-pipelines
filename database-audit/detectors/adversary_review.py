#!/usr/bin/env python3
"""Phase 10a — Auto-draft adversary review based on confidence distribution + finding patterns.

Generates initial _adversary_review.md the agent must enrich.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import get_paths, load_manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='10a')
    args = ap.parse_args()

    audit_dir, _, _, fp, _ = get_paths()
    m = load_manifest()
    mode = (m.get('mode', {}) or {}).get('type', 'static')

    findings = []
    if fp.exists():
        for line in fp.read_text().splitlines():
            line = line.strip()
            if not line: continue
            try:
                findings.append(json.loads(line))
            except Exception:
                pass

    sev = Counter(f.get('severity') for f in findings)
    conf = Counter(f.get('confidence') for f in findings)
    by_cat_sev = defaultdict(lambda: defaultdict(int))
    for f in findings:
        by_cat_sev[f.get('category')][f.get('severity')] += 1

    # Auto-classify findings by potential weakness
    weak = []  # likely false-positives
    strong = []
    for f in findings:
        if f.get('severity') in ('critical', 'high') and f.get('confidence') == 'low':
            weak.append((f.get('id'), f.get('title'), 'low confidence на high/critical — пересмотреть'))
        elif f.get('confidence') == 'medium' and 'static' in str(f.get('evidence', '')).lower():
            weak.append((f.get('id'), f.get('title'), 'medium confidence + static-mode → требует EXPLAIN'))
        else:
            strong.append((f.get('id'), f.get('title'), f.get('severity')))

    # Detect "money critical inflation" — if >7 critical в money категории, часть может быть logging-only
    money_crit = by_cat_sev.get('money', {}).get('critical', 0)
    money_inflation_warning = money_crit > 5

    out = ['# Adversary review (Phase 10a — auto-draft + agent enrichment)', '',
           '> Auto-generated initial draft. Agent must enrich each section with reasoning.', '',
           '## Summary stats', '',
           f'- Total findings: {len(findings)}',
           f'- by severity: {dict(sev)}',
           f'- by confidence: {dict(conf)}',
           '']

    if money_inflation_warning:
        out += ['## ⚠️ Severity inflation warning', '',
                f'**Money critical = {money_crit}.** Часть может быть logging-only '
                '(e.g. `costUsd` для AI-токенов — не критическая транзакция, drift < $0.01). '
                'Calibrate: business_critical=true только для customer-facing balances.', '',
                'Agent: пройди по money critical findings и пометь `business_critical: false` '
                'для logging/AI-cost полей. Для них severity → high (не critical).', '']

    out += ['## Strong findings (защищены evidence)', '']
    for fid, title, sev in strong[:20]:
        out.append(f'- **{fid}** [{sev}]: {title}')
    out += ['', '> Agent: подтверди каждую — есть ли независимый контр-аргумент?', '']

    out += ['## Weaker findings (требуют пересмотра)', '']
    if weak:
        for fid, title, reason in weak[:20]:
            out.append(f'- **{fid}**: {title} — _{reason}_')
    else:
        out.append('_(none auto-detected; agent should still review every high+medium)_')
    out += ['', '> Agent: для каждого — переоценить confidence, либо понизить severity, либо confirm.', '']

    out += ['## Systematic risks of this audit', '']
    if mode == 'static':
        out.append('- **Static mode** — N findings помечены требующими EXPLAIN. '
                   'Live mode прогон может изменить severity (как up, так и down).')
    out += [
        '- **Detector heuristics** — N+1 detection через regex может промахиваться на async-await chains.',
        '- **Manifest gaps** — sections помеченные "needs review" в `_known_unknowns.md` — это известные пробелы.',
        '- **Time-bound** — schema может измениться через неделю, manifest нужно `--refresh`.',
        '',
        '> Agent: добавь project-specific systematic risks.', ''
    ]

    out += ['## Cognitive bias self-check (Kahneman)', '',
            '- **Anchoring (§11):** не повлияла ли первая фаза на восприятие остальных?',
            '- **Overconfidence (§24):** доля high confidence > 50%? (текущий показатель: '
            f'{conf.get("high", 0)/max(len(findings),1):.0%})',
            '- **Availability heuristic:** сколько findings по «модной» теме (SQLi, money) vs реально проверенным?',
            '',
            '> Agent: ответь на каждый вопрос явно.',
            '']

    (audit_dir / '_adversary_review.md').write_text('\n'.join(out))

    # _known_unknowns
    ku_path = audit_dir / '_known_unknowns.md'
    if not ku_path.exists() or ku_path.stat().st_size < 100:
        ku_lines = ['# Known unknowns', '']
        if mode == 'static':
            ku_lines += ['## Static-mode limitations', '',
                         '- [ ] EXPLAIN ANALYZE on top queries — requires DATABASE_URL',
                         '- [ ] Real index usage from pg_stat_user_indexes',
                         '- [ ] pg_stat_statements slow query ranking',
                         '- [ ] Backup/restore drill verification',
                         '- [ ] Live read-only role check',
                         '']
        ku_lines += ['## Detector limitations', '',
                     '- [ ] N+1 heuristic: false positive rate ~30% — needs manual triage of suspects',
                     '- [ ] Multi-tenant verification: cypher-based check может промахиваться на nested calls',
                     '- [ ] PII auto-detect: based on column name patterns; real semantics needs review',
                     '',
                     '## Follow-up checks', '',
                     '- [ ] _Agent fills with project-specific items_', '']
        ku_path.write_text('\n'.join(ku_lines))

    # Skeleton 10a report
    skel_path = audit_dir / '10a_self_audit.md'
    if not skel_path.exists() or skel_path.stat().st_size < 100:
        skel_path.write_text(
            '# Phase 10a — Self-Audit\n\n'
            '_Agent fills based on _adversary_review.md results._\n\n'
            '## 1. What was reviewed\n\n'
            '## 2. Findings reclassified\n\n'
            '## 3. Manifest amendments\n\n'
            '## 4. Verdict on overall audit quality\n'
        )

    print(f'OK: _adversary_review.md auto-draft ({len(strong)} strong, {len(weak)} weak)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
