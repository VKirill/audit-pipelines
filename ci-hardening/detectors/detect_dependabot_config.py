#!/usr/bin/env python3
"""Check .github/dependabot.yml exists and is configured. Phase 06."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, get_paths, append_finding, write_evidence
import yaml

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='06')
args = ap.parse_args()

m = load_manifest()
_, project_root, _, _, _ = get_paths()

dep_path = project_root / '.github' / 'dependabot.yml'
ren_path = project_root / 'renovate.json'

md = ['# Dependency management config', '']
config_present = False
if dep_path.exists():
    config_present = True
    md.append(f'✅ Dependabot: {dep_path}')
    try:
        cfg = yaml.safe_load(dep_path.read_text())
        ecosystems = [u.get('package-ecosystem') for u in (cfg.get('updates') or [])]
        md.append(f'  Ecosystems: {ecosystems}')
        if 'github-actions' not in ecosystems:
            md.append('  ⚠️ github-actions ecosystem не настроен')
    except Exception as e:
        md.append(f'  ⚠️ parse error: {e}')
if ren_path.exists():
    config_present = True
    md.append(f'✅ Renovate: {ren_path}')
if not config_present:
    md.append('❌ Ни Dependabot ни Renovate не настроены')

write_evidence(args.phase, 'dependabot_config.md', '\n'.join(md))

if not config_present:
    append_finding({
        'phase': args.phase, 'category': 'dependencies',
        'subcategory': 'no-dep-update-tool',
        'severity': 'high', 'confidence': 'high',
        'title': 'Ни Dependabot ни Renovate не настроены',
        'location': {'file': '(.github/dependabot.yml or renovate.json)', 'line': 1},
        'evidence': 'Файлы `.github/dependabot.yml` и `renovate.json` отсутствуют.',
        'confidence_rationale': 'File system check.',
        'impact': 'Зависимости и actions не обновляются автоматически. Без этого SHA-пины устаревают, vulnerable versions остаются.',
        'recommendation': 'Скопировать `ci-hardening/templates/dependabot.yml` (с github-actions + npm/pip/etc ecosystems и группированием PR) ИЛИ `ci-hardening/templates/renovate.json` (с cooldown 7 дней).',
        'effort': 'S',
        'references': ['GitHub Docs: Dependabot version updates', 'Renovate docs']
    })

print(f'OK: dependabot_config — present={config_present}')
