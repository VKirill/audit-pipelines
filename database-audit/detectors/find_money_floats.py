#!/usr/bin/env python3
"""Find money columns stored in float-like types. Reads hints.money_columns.
Emits findings directly. CRITICAL detector — quality of phase 02/05b depends on it."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence

FLOAT_TYPES = {'float', 'double', 'real', 'double precision', 'float8', 'float4'}


def is_float_type(t):
    if not t: return False
    return any(ft in t.lower() for ft in FLOAT_TYPES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='02')
    args = ap.parse_args()

    m = load_manifest()
    money_cols = hints(m).get('money_columns', []) or []

    hits = []
    md = ['# Money columns audit', '']
    md.append('| Table | Columns | Type | Classification | Float? | Source |')
    md.append('|-------|---------|------|----------------|--------|--------|')

    for h in money_cols:
        is_float = is_float_type(h.get('type', ''))
        md.append(f"| {h.get('table','?')} | {','.join(h.get('columns',[]))} | "
                  f"{h.get('type','?')} | {h.get('classification','?')} | "
                  f"{'YES' if is_float else 'no'} | {h.get('file','?')}:{h.get('lines','?')} |")
        if is_float:
            hits.append(h)

    md.append('')
    md.append(f'**Float money columns: {len(hits)}**')

    write_evidence(args.phase, 'money_columns.md', '\n'.join(md))
    write_evidence(args.phase, 'money_floats.md', '\n'.join(md))

    # Emit one finding per Float money column
    for h in hits:
        cols = ', '.join(h.get('columns', []))
        is_balance_or_payout = h.get('classification') in ('balance', 'payout')
        # v4: business_critical=false demotes severity (e.g., logging-only AI cost)
        is_business_critical = h.get('business_critical', True)
        # exchange-rate is not money — should be high not critical
        is_exchange_rate = h.get('classification') == 'exchange-rate'
        if is_exchange_rate or not is_business_critical:
            severity = 'high'
        else:
            severity = 'critical' if is_balance_or_payout else 'high'

        finding = {
            'phase': args.phase,
            'category': 'money' if args.phase == '05b' else 'schema',
            'subcategory': 'money-type',
            'severity': severity,
            'confidence': 'high',
            'title': f'Денежная колонка {h["table"]}.{cols} объявлена как {h.get("type","?")}',
            'location': {
                'file': h.get('file', ''),
                'lines': h.get('lines', ''),
                'symbol': h.get('symbol', ''),
                'db_object': f"{h.get('table','')}.{cols}"
            },
            'evidence': (f'Schema {h.get("file","?")}:{h.get("lines","?")} declares column(s) '
                         f'{cols} of table {h.get("table","?")} as {h.get("type","?")}. '
                         f'Classification: {h.get("classification","?")}.'),
            'confidence_rationale': (f'Поле {h.get("file","?")}:{h.get("lines","?")} прочитано '
                                     f'непосредственно из схемы; тип объявлен как {h.get("type","?")}, '
                                     f'что является binary-float и не подходит для денежных значений (Karwin §9).'),
            'impact': ('Накопление ошибки округления при операциях. Несовпадение между сохранённым '
                       'остатком и точной арифметикой в копейках/центах. Финансовая отчётность теряет точность.'),
            'recommendation': ('Перевести на DECIMAL(p,s) или integer-копейки/центы. Multi-step миграция '
                               '(Sadalage Part II): добавить новую колонку → backfill → переключить чтение '
                               '→ переключить запись → удалить старую.'),
            'effort': 'M',
            'references': [
                'Karwin, SQL Antipatterns §9 Rounding Errors',
                'Celko, SQL Programming Style §4 Scales and Measurements',
                'Sadalage & Ambler, Refactoring Databases Part II'
            ],
        }
        if severity == 'critical':
            finding['exploit_proof'] = (
                f'Серия частичных списаний с дробными суммами в {h.get("table","?")}.{cols}: '
                f'два параллельных расчёта дают разное накопленное округление, '
                f'итоговый баланс не равен ожидаемому ledger-сумме. На {len(hits)} колонках '
                f'отклонения масштабируются.'
            )
        append_finding(finding)

    print(f'OK: {len(hits)} float-money findings emitted')
    return 0


if __name__ == '__main__':
    sys.exit(main())
