#!/usr/bin/env python3
"""Connection pool audit. Reads hints.pool_settings."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='08')
    args = ap.parse_args()

    m = load_manifest()
    p = hints(m).get('pool_settings', {}) or {}

    if not p:
        write_evidence(args.phase, 'pool_settings.md',
                       '# Pool settings\n\nNo pool_settings hint in manifest. Manual review required.\n')
        write_evidence(args.phase, 'cache_strategy.md',
                       '# Cache strategy\n\nNo automated detection — manual review of Redis/Memcached usage.\n')
        return 0

    md = ['# Pool settings audit', '']
    md.append(f'- File: {p.get("file","?")}:{p.get("lines","?")}')
    md.append(f'- max_connections: {p.get("max_connections","?")}')
    md.append(f'- idle_timeout_ms: {p.get("idle_timeout_ms","?")}')
    md.append(f'- shared_across_processes: {p.get("shared_across_processes","?")}')
    md.append(f'- notes: {p.get("notes","")}')
    write_evidence(args.phase, 'pool_settings.md', '\n'.join(md))
    write_evidence(args.phase, 'cache_strategy.md',
                   '# Cache strategy\n\n(manual review of cache layer required — see phase 08 instructions)\n')

    procs = p.get('shared_across_processes', 0) or 0
    max_conn = p.get('max_connections', 0) or 0
    if procs > 1 and max_conn > 0:
        total = procs * max_conn
        sev = 'high' if total > 100 else 'medium'
        append_finding({
            'phase': args.phase,
            'category': 'performance',
            'subcategory': 'pool-multiplication',
            'severity': sev,
            'confidence': 'high',
            'title': f'Connection pool max={max_conn} умножается на {procs} процессов = {total}',
            'location': {'file': p.get('file', ''), 'lines': p.get('lines', '')},
            'evidence': (f'Pool config {p.get("file","?")} задаёт max_connections={max_conn}, '
                         f'manifest указывает {procs} процессов. Итого {total} соединений к БД.'),
            'confidence_rationale': 'Pool config прочитан; число процессов задокументировано в manifest.',
            'impact': ('При высокой нагрузке полный pool может выжрать max_connections СУБД. '
                       'Каскадный отказ.'),
            'recommendation': ('Использовать transaction-mode pooler (PgBouncer/ProxySQL) перед app pool. '
                               'Или централизованный pool через worker. Mihalcea Ch. 3.'),
            'effort': 'M',
            'references': ['Mihalcea, High Performance Java Persistence Ch. 3',
                           'Schwartz, High Performance MySQL Ch. 11'],
        })

    print('OK: pool settings audited')
    return 0


if __name__ == '__main__':
    sys.exit(main())
