"""Shared library for ci-hardening detectors."""
import json, os, sys
from pathlib import Path
try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr); sys.exit(2)


def get_paths():
    project_root = Path(os.environ.get('PROJECT_ROOT', os.getcwd()))
    pipeline_dir = Path(os.environ.get('PIPELINE_DIR', str(project_root / 'ci-hardening')))
    audit_dir = Path(os.environ.get('AUDIT_DIR', str(pipeline_dir / 'results')))
    manifest_path = Path(os.environ.get('MANIFEST', str(pipeline_dir / 'manifest.yml')))
    findings_path = audit_dir / 'findings.jsonl'
    evidence_dir = audit_dir / 'evidence'
    audit_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    findings_path.touch(exist_ok=True)
    return audit_dir, project_root, manifest_path, findings_path, evidence_dir


def load_manifest():
    _, _, mp, _, _ = get_paths()
    if not mp.exists():
        print(f"Manifest not found: {mp}. Run init.sh first.", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(mp.read_text())


def evidence_path(phase, filename):
    audit_dir, _, _, _, evidence_dir = get_paths()
    import re
    matches = [p for p in evidence_dir.iterdir() if p.is_dir() and re.match(rf'^{re.escape(phase)}_', p.name)]
    if matches: d = matches[0]
    else:       d = evidence_dir / f'{phase}_phase'
    d.mkdir(exist_ok=True, parents=True)
    return d / filename


def write_evidence(phase, filename, content):
    p = evidence_path(phase, filename)
    p.write_text(content, encoding='utf-8')
    return p


CATEGORY_PREFIXES = {
    'supply-chain': 'PIN',  'permissions': 'PERM', 'secrets': 'SEC',
    'branch-protection': 'BRN', 'settings': 'SET', 'workflow': 'WF',
    'dependencies': 'DEP', 'sast': 'SAST', 'meta': 'META',
}


def next_id(category, findings_path):
    prefix = CATEGORY_PREFIXES.get(category, 'GEN')
    n = 0
    if findings_path.exists():
        for line in findings_path.read_text().splitlines():
            line = line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
                fid = obj.get('id', '')
                if fid.startswith(f'CI-{prefix}-'):
                    try: n = max(n, int(fid.rsplit('-', 1)[1]))
                    except: pass
            except: pass
    return f'CI-{prefix}-{n+1:03d}'


def fingerprint(category, location):
    file = (location or {}).get('file', '')
    obj  = (location or {}).get('action', '') or (location or {}).get('symbol', '')
    line = (location or {}).get('line', '')
    return '|'.join(str(p) for p in [category, file, obj, line])


def existing_fingerprints(findings_path):
    fps = set()
    if not findings_path.exists(): return fps
    for line in findings_path.read_text().splitlines():
        line = line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
            fps.add(fingerprint(obj.get('category',''), obj.get('location',{})))
        except: pass
    return fps


def append_finding(finding, dedup=True):
    _, _, _, fp, _ = get_paths()
    cat = finding.get('category', 'meta')
    if dedup:
        fps = existing_fingerprints(fp)
        fpr = fingerprint(cat, finding.get('location', {}))
        if fpr in fps: return None
    if 'id' not in finding: finding['id'] = next_id(cat, fp)
    if 'status' not in finding: finding['status'] = 'open'
    with fp.open('a', encoding='utf-8') as f:
        f.write(json.dumps(finding, ensure_ascii=False) + '\n')
    return finding['id']


def hints(manifest): return manifest.get('hints', {}) or {}
def github(manifest): return manifest.get('github', {}) or {}
def paths(manifest): return manifest.get('paths', {}) or {}


def iter_workflow_files(project_root=None):
    if project_root is None:
        _, project_root, _, _, _ = get_paths()
    wf_dir = project_root / '.github' / 'workflows'
    if not wf_dir.exists(): return
    for f in wf_dir.iterdir():
        if f.suffix in ('.yml', '.yaml') and f.is_file():
            yield f
