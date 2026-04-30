#!/usr/bin/env python3
"""Phase 10a — emits skeleton _adversary_review.md and _known_unknowns.md.
Agent fills in narrative content."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import get_paths, load_manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='10a')
    args = ap.parse_args()

    audit_dir, _, _, _, _ = get_paths()
    m = load_manifest()
    mode = (m.get('mode', {}) or {}).get('type', 'static')

    adv = audit_dir / '_adversary_review.md'
    if not adv.exists():
        adv.write_text('# Adversary review\n\n_To be filled by agent._\n\n## Strong findings\n\n## Weaker findings\n\n## Systematic risks\n')

    ku = audit_dir / '_known_unknowns.md'
    if not ku.exists():
        content = '# Known unknowns\n\n'
        if mode == 'static':
            content += '## Static-mode limitations\n\n- [ ] EXPLAIN ANALYZE on top queries — requires DATABASE_URL\n- [ ] Real index usage from pg_stat_user_indexes\n- [ ] pg_stat_statements slow query ranking\n- [ ] Backup/restore drill verification\n\n'
        content += '## Follow-up checks\n\n- [ ] _To be filled by agent._\n'
        ku.write_text(content)

    skel = audit_dir / '10a_self_audit.md'
    if not skel.exists():
        skel.write_text('# Phase 10a — Self-Audit\n\n_To be filled by agent._\n')

    print('OK: 10a skeleton')
    return 0


if __name__ == '__main__':
    sys.exit(main())
