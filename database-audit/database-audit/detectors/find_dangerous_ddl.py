#!/usr/bin/env python3
"""Emit findings for dangerous DDL listed in hints.dangerous_migrations."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence

KIND_INFO = {
    'drop-table':            ('high', 'DROP TABLE может разрушить данные. Multi-step: pre-drop reads/writes → wait → drop'),
    'drop-column':           ('high', 'DROP COLUMN: сначала перестать использовать в коде, выждать N деплоев, затем drop'),
    'rename-column':         ('high', 'RENAME COLUMN ломает rolling deploy. Использовать add+backfill+switch+drop'),
    'alter-column-type':     ('high', 'ALTER COLUMN TYPE переписывает таблицу. Использовать new column + backfill'),
    'add-not-null-default':  ('medium', 'PG <11: ADD COLUMN NOT NULL DEFAULT переписывает таблицу. Add nullable → backfill → SET NOT NULL'),
    'create-index-blocking': ('high', 'CREATE INDEX без CONCURRENTLY блокирует записи. Использовать CONCURRENTLY'),
    'add-constraint-validating': ('medium', 'ADD CONSTRAINT валидирует синхронно. Использовать NOT VALID + VALIDATE CONSTRAINT'),
    'truncate':              ('high', 'TRUNCATE необратим. Сначала backup verify'),
    'update-without-where':  ('high', 'UPDATE без WHERE затрагивает всю таблицу. Использовать batched UPDATE с LIMIT'),
    'large-tx-wrap':         ('medium', 'Большой UPDATE/миграция в одной транзакции блокирует таблицу. Дробить по batch'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='06')
    args = ap.parse_args()

    m = load_manifest()
    items = hints(m).get('dangerous_migrations', []) or []

    md = ['# Dangerous DDL (Sadalage & Ambler)', '']
    md.append('| File | Lines | Kind | Severity |')
    md.append('|------|-------|------|----------|')
    for h in items:
        kind = h.get('kind', 'unknown')
        sev, _ = KIND_INFO.get(kind, ('medium', ''))
        md.append(f"| {h['file']} | {h['lines']} | {kind} | {sev} |")

    write_evidence(args.phase, 'dangerous_ddl.md', '\n'.join(md))

    for h in items:
        kind = h.get('kind', 'unknown')
        sev, fix_strategy = KIND_INFO.get(kind, ('medium', 'Manual review required'))
        finding = {
            'phase': args.phase,
            'category': 'migration',
            'subcategory': kind,
            'severity': sev,
            'confidence': 'high',
            'title': f'Опасная DDL операция: {kind}',
            'location': {'file': h['file'], 'lines': h['lines']},
            'evidence': f'В миграции {h["file"]}:{h["lines"]} обнаружена операция типа {kind}.',
            'confidence_rationale': (f'Файл миграции {h["file"]} прочитан; на строках {h["lines"]} '
                                     f'присутствует DDL паттерн {kind}, который имеет известные риски '
                                     f'при выполнении на production-нагрузке.'),
            'impact': ('Блокировки таблицы, потеря данных при rolling deploy, или necессарность downtime.'),
            'recommendation': fix_strategy + '. См. Sadalage & Ambler, Refactoring Databases Part II.',
            'effort': 'M',
            'references': [
                'Sadalage & Ambler, Refactoring Databases Part II',
                'PostgreSQL docs: ALTER TABLE'
            ],
        }
        append_finding(finding)

    print(f'OK: {len(items)} dangerous-ddl findings')
    return 0


if __name__ == '__main__':
    sys.exit(main())
