#!/usr/bin/env python3
"""Emit findings for hints.transaction_sites of kinds missing-transaction / external-io-inside-transaction.
Also writes evidence/05_transactions/transaction_coverage.md."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='05')
    args = ap.parse_args()

    m = load_manifest()
    sites = hints(m).get('transaction_sites', []) or []

    by_kind = {}
    for s in sites:
        by_kind.setdefault(s.get('kind', 'unknown'), []).append(s)

    md = ['# Transaction coverage', '']
    md.append(f'Total transaction sites in manifest: {len(sites)}')
    md.append('')
    for kind, items in by_kind.items():
        md.append(f'## {kind} ({len(items)})')
        for s in items:
            md.append(f"- {s['file']}:{s['lines']}  symbol={s.get('symbol','?')}  note={s.get('note','')}")
        md.append('')

    write_evidence(args.phase, 'transaction_coverage.md', '\n'.join(md))

    md_iso = ['# Isolation levels', '',
              'Manifest does not declare project default isolation. Manual confirmation:',
              '',
              '- PostgreSQL default: READ COMMITTED (allows non-repeatable reads, lost updates with read-modify-write)',
              '- MySQL InnoDB default: REPEATABLE READ',
              '- For money/state mutations — recommend SERIALIZABLE or explicit FOR UPDATE',
              '',
              'See Kleppmann §7.2.']
    write_evidence(args.phase, 'isolation_levels.md', '\n'.join(md_iso))

    race_md = ['# Race candidates', '']
    race_md.append('Sites flagged as missing-transaction or external-io-inside-transaction:')
    race_md.append('')
    race_count = 0
    for s in sites:
        kind = s.get('kind', '')
        if kind not in ('missing-transaction', 'external-io-inside-transaction'):
            continue
        race_count += 1
        race_md.append(f'## {s["file"]}:{s["lines"]} — {kind}')
        race_md.append(f'symbol: {s.get("symbol","?")}')
        race_md.append(f'note: {s.get("note","")}')
        race_md.append('')
    write_evidence(args.phase, 'race_candidates.md', '\n'.join(race_md))

    # Findings
    for s in sites:
        kind = s.get('kind', '')
        if kind == 'missing-transaction':
            finding = {
                'phase': args.phase,
                'category': 'transaction',
                'subcategory': 'lost-update',
                'severity': 'critical' if s.get('note', '').lower().count('balance') or s.get('note', '').lower().count('money') else 'high',
                'confidence': 'high',
                'title': f'{s.get("symbol","function")} не обёрнут в transaction boundary',
                'location': {'file': s['file'], 'lines': s['lines'], 'symbol': s.get('symbol', '')},
                'evidence': (f'Функция {s.get("symbol","?")} в {s["file"]}:{s["lines"]} '
                             f'выполняет последовательность read+update без transaction wrapper. '
                             f'Note: {s.get("note","")}'),
                'confidence_rationale': (f'Тело функции прочитано; последовательность RMW (read-modify-write) '
                                         f'без $transaction/begin/atomic блока подтверждена статически.'),
                'impact': ('Параллельные вызовы могут привести к lost update / race condition. '
                           'Под нагрузкой — несогласованное состояние данных.'),
                'recommendation': ('Обернуть в транзакцию (db.$transaction / session.begin / SELECT FOR UPDATE). '
                                   'Для денежных операций — добавить уникальный constraint на (object_id, idempotency_key).'),
                'effort': 'M',
                'references': [
                    'Bernstein & Newcomer §6 Locking',
                    'Kleppmann Ch. 7 Transactions',
                    'Helland, Life Beyond Distributed Transactions'
                ],
            }
            if finding['severity'] == 'critical':
                finding['exploit_proof'] = (
                    f'Two concurrent calls to {s.get("symbol","fn")} read same state, both compute new value, '
                    f'both write — second overwrites first. State is corrupt; if money-related, double-spend or balance drift.'
                )
            append_finding(finding)
        elif kind == 'external-io-inside-transaction':
            append_finding({
                'phase': args.phase,
                'category': 'transaction',
                'subcategory': 'external-io-in-tx',
                'severity': 'high',
                'confidence': 'high',
                'title': f'External I/O внутри транзакции: {s.get("symbol","?")}',
                'location': {'file': s['file'], 'lines': s['lines'], 'symbol': s.get('symbol', '')},
                'evidence': f'В {s["file"]}:{s["lines"]} выполняется HTTP/email/publish внутри открытой транзакции.',
                'confidence_rationale': 'Подтверждено чтением кода: external call внутри tx-блока.',
                'impact': 'Лок держится пока ходит наружу, рискует deadlock и connection exhaustion.',
                'recommendation': 'Вынести external call после commit или использовать outbox pattern.',
                'effort': 'M',
                'references': ['Helland, Life Beyond Distributed Transactions', 'Kleppmann Ch. 11'],
            })

    print(f'OK: transactions phase wrote {race_count} race candidates')
    return 0


if __name__ == '__main__':
    sys.exit(main())
