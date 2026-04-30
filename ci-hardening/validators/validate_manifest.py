#!/usr/bin/env python3
"""Validate ci-hardening manifest.yml."""
import os, sys, argparse
from pathlib import Path
try:
    import yaml
except ImportError:
    print("PyYAML required", file=sys.stderr); sys.exit(2)

SCHEMA_PATH = Path(__file__).parent.parent / "manifest.schema.yml"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manifest', nargs='?', default='ci-hardening/manifest.yml')
    ap.add_argument('--strict', action='store_true')
    args = ap.parse_args()

    mp = Path(args.manifest)
    if not mp.exists():
        print(f"manifest not found: {mp}"); return 1
    try: m = yaml.safe_load(mp.read_text())
    except yaml.YAMLError as e:
        print(f"YAML parse error: {e}"); return 1

    errors = []
    warnings = []

    # Schema check (если jsonschema есть)
    try:
        import jsonschema
        schema = yaml.safe_load(SCHEMA_PATH.read_text())
        try: jsonschema.validate(instance=m, schema=schema)
        except jsonschema.ValidationError as e:
            errors.append(f"SCHEMA: {e.message}")
    except ImportError:
        warnings.append("jsonschema not installed — schema check skipped")

    # Sanity
    project_root = Path(m.get('project',{}).get('root', '.'))
    paths_obj = m.get('paths',{}) or {}
    for f in paths_obj.get('workflow_files', []) or []:
        if not (project_root / f).exists():
            errors.append(f"workflow_file not found: {f}")

    gh = m.get('github', {}) or {}
    if not gh.get('owner') or not gh.get('repo'):
        warnings.append("github.owner/repo not set — gh api detectors will skip")

    print(f"Manifest: {mp}")
    print(f"Project: {m.get('project',{}).get('name','?')}")
    print(f"Repo: {gh.get('owner','?')}/{gh.get('repo','?')}")
    print(f"Mode: {(m.get('mode',{}) or {}).get('type','?')}")
    print()
    for w in warnings: print(f"  [warn] {w}")
    for e in errors: print(f"  [err]  {e}")
    print()
    if errors:
        print(f"FAIL: {len(errors)} error(s)"); return 1
    if warnings and args.strict:
        print(f"FAIL (strict): {len(warnings)} warning(s)"); return 1
    print("OK: manifest valid")
    return 0

if __name__ == '__main__':
    sys.exit(main())
