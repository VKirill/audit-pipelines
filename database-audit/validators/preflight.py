#!/usr/bin/env python3
"""Preflight check for live mode — verifies DATABASE_URL is set,
DB client available, role is read-only.
Run by run.sh before any live-mode phase."""
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr); sys.exit(2)


def main():
    manifest_path = Path(os.environ.get('MANIFEST', 'database-audit/manifest.yml'))
    if not manifest_path.exists():
        print('manifest not found'); return 1

    m = yaml.safe_load(manifest_path.read_text())
    mode = (m.get('mode', {}) or {}).get('type', 'static')

    if mode != 'live':
        print(f'mode={mode} — preflight skipped')
        return 0

    env_var = (m.get('mode', {}) or {}).get('live_db_url_env', 'DATABASE_URL')
    dsn = os.environ.get(env_var)
    if not dsn:
        print(f'FAIL: {env_var} env var not set, but mode=live'); return 1

    # Detect DB type
    if dsn.startswith('postgres'):
        kind = 'postgres'
        client = 'psql'
    elif dsn.startswith('mysql') or dsn.startswith('mariadb'):
        kind = 'mysql'
        client = 'mysql'
    elif dsn.startswith('mongodb'):
        kind = 'mongo'
        client = 'mongosh'
    else:
        print(f'FAIL: unknown DSN scheme'); return 1

    try:
        subprocess.run([client, '--version'], capture_output=True, check=True, timeout=5)
    except Exception as e:
        print(f'FAIL: {client} not installed: {e}'); return 1

    # Read-only role check (PG only for now)
    if kind == 'postgres':
        try:
            r = subprocess.run(
                [client, dsn, '-t', '-c',
                 "SELECT current_user, current_setting('default_transaction_read_only', true)"],
                capture_output=True, text=True, timeout=10)
            out = r.stdout.strip()
            print(f'PG handshake: {out}')
            if r.returncode != 0:
                print('FAIL: connection failed')
                print(r.stderr); return 1
            if 'on' not in out.lower():
                print('WARN: default_transaction_read_only is not "on" — '
                      'role may not be enforced read-only.')
                # Not fatal but requires manifest.read_only_role_required check
                if (m.get('mode', {}) or {}).get('read_only_role_required'):
                    print('FAIL: manifest requires read-only role')
                    return 1
        except Exception as e:
            print(f'FAIL: PG preflight: {e}'); return 1

    print('OK: live preflight passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
