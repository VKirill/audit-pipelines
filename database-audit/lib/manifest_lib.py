"""Shared library for detectors. Loads manifest, manages findings.jsonl."""
import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


def get_paths():
    """Return tuple (audit_dir, project_root, manifest_path, findings_path, evidence_dir)."""
    project_root = Path(os.environ.get('PROJECT_ROOT', os.getcwd()))
    audit_dir = Path(os.environ.get('AUDIT_DIR', str(project_root / 'audit')))
    manifest_path = Path(os.environ.get('MANIFEST', str(project_root / 'database-audit.manifest.yml')))
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
    """Return AUDIT_DIR/evidence/<NN_*>/filename. Creates dir."""
    audit_dir, _, _, _, evidence_dir = get_paths()
    # Find a directory matching NN_* or create NN_phase
    import re
    matches = [p for p in evidence_dir.iterdir() if p.is_dir() and re.match(rf'^{re.escape(phase)}_', p.name)]
    if matches:
        d = matches[0]
    else:
        d = evidence_dir / f'{phase}_phase'
    d.mkdir(exist_ok=True, parents=True)
    return d / filename


def next_finding_id(prefix='DB'):
    """Allocate next sequential ID by reading findings.jsonl."""
    _, _, _, fp, _ = get_paths()
    n = 0
    if fp.exists():
        for line in fp.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                fid = obj.get('id', '')
                if fid.startswith(f'{prefix}-'):
                    n = max(n, int(fid.split('-')[1]))
            except Exception:
                pass
    return f'{prefix}-{n+1:04d}'


def append_finding(finding):
    """Append finding to findings.jsonl. Auto-fills id if missing."""
    _, _, _, fp, _ = get_paths()
    if 'id' not in finding:
        finding['id'] = next_finding_id()
    if 'status' not in finding:
        finding['status'] = 'open'
    with fp.open('a', encoding='utf-8') as f:
        f.write(json.dumps(finding, ensure_ascii=False) + '\n')
    return finding['id']


def write_evidence(phase, filename, content):
    """Write text content to evidence file. Returns path."""
    p = evidence_path(phase, filename)
    p.write_text(content, encoding='utf-8')
    return p


def read_file_lines(rel_path, project_root=None):
    """Read project file. Returns list of lines (with trailing \n)."""
    if project_root is None:
        _, project_root, _, _, _ = get_paths()
    full = project_root / rel_path
    if not full.exists():
        return None
    return full.read_text(encoding='utf-8', errors='ignore').splitlines(keepends=True)


def file_line_range(rel_path, lines_spec, project_root=None):
    """Given lines_spec '40-60' or '42', return joined slice or None."""
    lines = read_file_lines(rel_path, project_root)
    if lines is None:
        return None
    if '-' in str(lines_spec):
        a, b = lines_spec.split('-', 1)
        a, b = int(a), int(b)
    else:
        a = b = int(lines_spec)
    return ''.join(lines[a-1:b])


def stack(manifest):
    return manifest.get('stack', {}) or {}


def hints(manifest):
    return manifest.get('hints', {}) or {}


def paths(manifest):
    return manifest.get('paths', {}) or {}


def phase_config(manifest, phase):
    return (manifest.get('phase_plan', {}) or {}).get(phase, {}) or {}


# Globs to project files for ripgrep-like operations using Python
def iter_files(globs, excludes=None, project_root=None):
    """Iterate project files matching any of globs, excluding excludes."""
    import fnmatch
    if project_root is None:
        _, project_root, _, _, _ = get_paths()
    excludes = set(excludes or [])
    for pattern in globs:
        for path in project_root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(project_root)
            if any(part in excludes for part in rel.parts):
                continue
            yield rel
