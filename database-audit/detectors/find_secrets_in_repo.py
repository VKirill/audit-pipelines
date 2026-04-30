#!/usr/bin/env python3
"""Stub detector for find_secrets_in_repo. Produces evidence placeholder; agent fills in phase report."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import write_evidence

ap = argparse.ArgumentParser()
ap.add_argument('--manifest', required=True)
ap.add_argument('--phase', default='07')
args = ap.parse_args()

write_evidence(args.phase, 'secret_scan.txt',
               '# find_secrets_in_repo\n\n_This evidence file requires manual review by the agent.\n'
               'Phase 07 instruction in prompts/phase_07_*.md describes what to check._\n')
print('OK: find_secrets_in_repo placeholder written')
