#!/usr/bin/env python3
"""Validate database-audit.manifest.yml.

Checks:
- JSON Schema conformance (if jsonschema installed; else falls back to lightweight checks).
- Sanity thresholds (Prisma -> schema_files non-empty; money words in code -> money_columns non-empty).
- All file paths in hints actually resolve.
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SCHEMA_PATH = Path(__file__).parent.parent / "manifest.schema.yml"


def load_yaml(p):
    with open(p) as f:
        return yaml.safe_load(f)


def load_schema():
    return load_yaml(SCHEMA_PATH)


def check_schema(manifest, schema):
    try:
        import jsonschema
    except ImportError:
        return ["WARN: jsonschema not installed — skipping strict schema check"]

    try:
        jsonschema.validate(instance=manifest, schema=schema)
        return []
    except jsonschema.ValidationError as e:
        return [f"SCHEMA: {e.message} at {'.'.join(map(str, e.absolute_path))}"]


def check_paths_resolve(manifest, root):
    errors = []
    paths = manifest.get('paths', {}) or {}
    hints = manifest.get('hints', {}) or {}

    def check_file(field, p):
        if not p:
            return
        full = root / p
        if not full.exists():
            errors.append(f"PATH: {field}: file not found: {p}")

    for f in paths.get('schema_files', []) or []:
        check_file('paths.schema_files', f)
    for f in paths.get('pool_config_files', []) or []:
        check_file('paths.pool_config_files', f)
    for f in (paths.get('migration_files', {}) or {}).get('files', []) or []:
        check_file('paths.migration_files.files', f)

    def for_each_hint(group, fields):
        for i, item in enumerate(hints.get(group, []) or []):
            for k in fields:
                v = item.get(k)
                if v:
                    check_file(f"hints.{group}[{i}].{k}", v)

    for_each_hint('money_columns', ['file'])
    for_each_hint('transaction_sites', ['file'])
    for_each_hint('raw_sql_in_code', ['file'])
    for_each_hint('pii_candidates', ['file'])
    for_each_hint('money_endpoints', ['file'])
    for_each_hint('n_plus_one_candidates', ['file'])
    for_each_hint('missing_fk_indexes', ['file'])
    for_each_hint('dangerous_migrations', ['file'])

    pool = (hints.get('pool_settings') or {}).get('file')
    if pool:
        check_file('hints.pool_settings.file', pool)

    return errors


def check_sanity_thresholds(manifest, root):
    """Detector failures most often manifest as empty hints. Catch obvious gaps."""
    warnings = []
    stack = manifest.get('stack', {}) or {}
    paths = manifest.get('paths', {}) or {}
    hints = manifest.get('hints', {}) or {}

    if stack.get('primary_orm') == 'prisma' and not paths.get('schema_files'):
        warnings.append("SANITY: primary_orm=prisma but paths.schema_files is empty — "
                        "did you check for *.prisma files across all workspaces?")

    if stack.get('primary_orm') in ('sqlalchemy', 'django-orm') and not paths.get('schema_files'):
        warnings.append("SANITY: ORM declared but no schema_files listed — review models discovery")

    has_money_words = False
    try:
        out = subprocess.run(
            ['rg', '-c', '-iE', r'\b(payment|wallet|balance|invoice|charge|deduct|topup|payout)\b',
             '-g', '!node_modules', '-g', '!.git', '-g', '!*.lock', str(root)],
            capture_output=True, text=True, timeout=30
        )
        if out.stdout.strip():
            has_money_words = True
    except Exception:
        pass

    if has_money_words and not hints.get('money_columns'):
        warnings.append("SANITY: 'payment/wallet/balance/charge' words present in code but "
                        "hints.money_columns is empty. Re-check models — this is the #1 "
                        "source of missed critical findings.")

    if not paths.get('migration_files', {}).get('files') and \
       not paths.get('migration_files', {}).get('dirs'):
        warnings.append("SANITY: no migration files or dirs declared. Either explicitly set "
                        "tool=declarative/none, or re-discover migrations.")

    if manifest.get('mode', {}).get('type') == 'live' and \
       not manifest.get('mode', {}).get('read_only_role_required'):
        warnings.append("SANITY: live mode without read_only_role_required=true is unsafe")

    return warnings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest', nargs='?', default='database-audit/manifest.yml')
    ap.add_argument('--strict', action='store_true',
                    help='Treat sanity warnings as errors')
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = load_yaml(manifest_path)
    except yaml.YAMLError as e:
        print(f"YAML parse error: {e}", file=sys.stderr)
        sys.exit(1)

    schema = load_schema()
    project_root = Path(manifest.get('project', {}).get('root', '.'))

    errors = []
    errors += check_schema(manifest, schema)
    errors += check_paths_resolve(manifest, project_root)

    warnings = check_sanity_thresholds(manifest, project_root)

    print(f"Manifest: {manifest_path}")
    print(f"Project: {manifest.get('project',{}).get('name','?')} ({manifest.get('project',{}).get('type','?')})")
    print(f"Stack: {manifest.get('stack',{}).get('primary_db','?')} + {manifest.get('stack',{}).get('primary_orm','?')}")
    print(f"Mode: {manifest.get('mode',{}).get('type','?')}")
    print()

    for w in warnings:
        print(f"  [warn] {w}")

    for e in errors:
        print(f"  [err]  {e}")

    print()
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        sys.exit(1)
    if warnings and args.strict:
        print(f"FAIL (strict): {len(warnings)} warning(s)")
        sys.exit(1)

    print("OK: manifest valid")
    return 0


if __name__ == '__main__':
    sys.exit(main())
