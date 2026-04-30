"""Category-based finding ID generator. Replaces global DB-NNNN with DB-CAT-NNN."""
import json
from pathlib import Path

CATEGORY_PREFIXES = {
    'inventory':   'INV',
    'schema':      'SCH',
    'index':       'IDX',
    'query':       'QRY',
    'transaction': 'TX',
    'money':       'MONEY',
    'migration':   'MIG',
    'security':    'SEC',
    'pii':         'PII',
    'performance': 'PERF',
    'ops':         'OPS',
    'meta':        'META',
}


def next_id(category, findings_path):
    """Allocate next sequential ID for given category."""
    prefix = CATEGORY_PREFIXES.get(category, 'GEN')
    n = 0
    if findings_path.exists():
        for line in findings_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                fid = obj.get('id', '')
                if fid.startswith(f'DB-{prefix}-'):
                    try:
                        n = max(n, int(fid.rsplit('-', 1)[1]))
                    except ValueError:
                        pass
            except Exception:
                pass
    return f'DB-{prefix}-{n+1:03d}'


def fingerprint(category, location):
    """Stable fingerprint for dedup. Same (category, file, db_object) -> same fp."""
    file = (location or {}).get('file', '')
    obj  = (location or {}).get('db_object', '')
    sym  = (location or {}).get('symbol', '')
    lines = (location or {}).get('lines', '')
    parts = [category, file, obj or sym, lines]
    return '|'.join(p or '' for p in parts)


def existing_fingerprints(findings_path):
    """Return set of fingerprints already present in findings.jsonl."""
    fps = set()
    if not findings_path.exists():
        return fps
    for line in findings_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            fps.add(fingerprint(obj.get('category', ''), obj.get('location', {})))
        except Exception:
            pass
    return fps
