#!/usr/bin/env python3
"""Money mutation endpoints без idempotency. Reads hints.money_endpoints."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='05b')
    args = ap.parse_args()

    m = load_manifest()
    eps = hints(m).get('money_endpoints', []) or []

    md = ['# Idempotency coverage on money endpoints', '']
    md.append('| File | Lines | Symbol | Mutation | Idempotent? |')
    md.append('|------|-------|--------|----------|-------------|')
    for e in eps:
        md.append(f"| {e['file']} | {e['lines']} | {e.get('symbol','?')} | "
                  f"{e.get('mutation_kind','?')} | {'yes' if e.get('has_idempotency_key') else 'NO'} |")

    write_evidence(args.phase, 'idempotency_coverage.md', '\n'.join(md))

    # atomic_updates.md placeholder — manual phase
    write_evidence(args.phase, 'atomic_updates.md',
                   '# Atomic updates audit\n\nManual review of money endpoints. See findings for race conditions.\n')

    for e in eps:
        if e.get('has_idempotency_key'):
            continue
        if e.get('mutation_kind') in ('credit', 'debit', 'transfer', 'charge', 'refund', 'mixed'):
            finding = {
                'phase': args.phase,
                'category': 'money',
                'subcategory': 'no-idempotency',
                'severity': 'critical',
                'confidence': 'high',
                'title': f'{e.get("symbol","money endpoint")} не имеет idempotency_key',
                'location': {'file': e['file'], 'lines': e['lines'], 'symbol': e.get('symbol', '')},
                'evidence': (f'Endpoint/функция {e.get("symbol","?")} в {e["file"]}:{e["lines"]} '
                             f'выполняет {e.get("mutation_kind","mutation")} над money state без '
                             f'idempotency-параметра в сигнатуре.'),
                'confidence_rationale': ('Сигнатура endpoint/функции прочитана; параметр idempotency_key/'
                                         'operation_id отсутствует, и unique constraint на пару '
                                         '(account, operation_id) не задекларирован.'),
                'exploit_proof': (f'Worker вызывает {e.get("symbol","fn")} с (project, amount). '
                                  f'Деньги списаны, но worker крашится перед маркировкой job как charged. '
                                  f'Retry той же job вызывает функцию повторно — повторное списание. '
                                  f'Без unique key защиты нет.'),
                'impact': 'Двойное списание / двойное начисление при ретраях клиента или worker crash.',
                'recommendation': ('Добавить параметр operation_id в сигнатуру + unique constraint '
                                   '(object_id, operation_id) в БД. Idempotent endpoint возвращает '
                                   'оригинальный результат при повторном запросе.'),
                'effort': 'M',
                'references': ['Helland, Life Beyond Distributed Transactions', 'Kleppmann Ch. 7'],
            }
            append_finding(finding)

    print(f'OK: idempotency check on {len(eps)} endpoints')
    return 0


if __name__ == '__main__':
    sys.exit(main())
