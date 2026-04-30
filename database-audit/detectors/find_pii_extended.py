#!/usr/bin/env python3
"""Extended PII discovery — session tokens, OAuth, webhook secrets, payment data.
Reads schema_summary.json + manifest hints.pii_candidates."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence, evidence_path

# Patterns by severity classification
PII_PATTERNS = {
    'credentials': [
        r'\b(password|password_hash|hashed_password|api_key|apikey|secret|access_token|refresh_token|oauth_token|webhook_secret|stripe_key|sendgrid_key|aws_secret|signing_secret)\b',
    ],
    'payment-card': [
        r'\b(card_number|cardnumber|cvv|cvc|iban|swift|bank_account|routing_number)\b',
    ],
    'sensitive': [
        r'\b(ssn|social_security|tax_id|national_id|passport|drivers_license|date_of_birth)\b',
    ],
    'special-category': [
        r'\b(health|medical|diagnosis|biometric|fingerprint|race|religion|political_affiliation|sexual_orientation)\b',
    ],
    'non-sensitive': [
        r'\b(email|phone|address|name|firstName|lastName|surname|zip|postal_code)\b',
    ],
}

# Severity mapping
SEVERITY_MAP = {
    'credentials': 'critical',
    'payment-card': 'critical',
    'sensitive': 'high',
    'special-category': 'high',
    'non-sensitive': 'medium',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='07')
    args = ap.parse_args()

    m = load_manifest()
    ss = evidence_path('01', 'schema_summary.json')
    if not ss.exists():
        print('schema_summary.json missing'); return 0
    data = json.loads(ss.read_text())

    md = ['# Extended PII coverage', '']
    md.append('| Table | Column | Type | Classification | Source |')
    md.append('|-------|--------|------|----------------|--------|')

    # Fast lookup of already-known PII from manifest
    known = {(p['table'], p['column']): p for p in (hints(m).get('pii_candidates', []) or [])}

    new_pii = []
    for t in data.get('tables', []):
        for c in t.get('columns', []):
            cname = c.get('name', '')
            for cls, patterns in PII_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, cname, re.IGNORECASE):
                        key = (t['name'], cname)
                        if key in known:
                            continue
                        new_pii.append({
                            'table': t['name'],
                            'column': cname,
                            'type': c.get('type', '?'),
                            'classification': cls,
                            'file': t['source_file'],
                            'lines': str(t['line']),
                            'encrypted_at_rest': False,  # default, verify manually
                        })
                        md.append(f'| {t["name"]} | {cname} | {c.get("type", "?")} | {cls} | '
                                  f'{t["source_file"]}:{t["line"]} (auto-detected) |')
                        break
                else:
                    continue
                break

    write_evidence(args.phase, 'pii_extended.md', '\n'.join(md))

    for p in new_pii:
        cls = p['classification']
        if cls == 'non-sensitive':
            sev = 'medium'
        elif cls in ('sensitive', 'special-category'):
            sev = 'high'
        else:
            sev = 'critical'

        finding = {
            'phase': args.phase,
            'category': 'pii',
            'subcategory': f'pii-extended-{cls}',
            'severity': sev,
            'confidence': 'high',
            'title': f'PII column ({cls}): {p["table"]}.{p["column"]}',
            'location': {'file': p['file'], 'lines': p['lines'],
                         'db_object': f"{p['table']}.{p['column']}"},
            'evidence': (f'Колонка {p["table"]}.{p["column"]} в {p["file"]}:{p["lines"]} '
                         f'имеет имя соответствующее PII pattern класса {cls}. '
                         f'Тип: {p["type"]}. Encryption status: needs manual verification.'),
            'confidence_rationale': ('Auto-detected by name pattern. Manual review needed to confirm '
                                     'classification and encryption-at-rest status. '
                                     'Если column реально хранит PII и не encrypted — finding valid.'),
            'impact': 'Утечка sensitive данных при breach. GDPR Art. 32 нарушен если plain.',
            'recommendation': ('1) Verify реальное использование колонки. '
                               '2) Если хранит PII в plain — encryption-at-rest (pgcrypto / app-side AES). '
                               '3) Обновить manifest.hints.pii_candidates.'),
            'effort': 'M',
            'references': [
                'NIST SP 800-218 (replaces SP 800-122)',
                'GDPR Art. 32 (Security of processing)',
                'OWASP Database Security Cheat Sheet'
            ],
        }
        if sev == 'critical':
            finding['exploit_proof'] = (
                f'Любой имеющий read-доступ к таблице {p["table"]} (DBA, replica, backup, leak) '
                f'получает {cls} в plain text. {p["column"]} — credentials/payment-card pattern.'
            )
        append_finding(finding)

    print(f'OK: pii_extended — {len(new_pii)} new PII findings')
    return 0


if __name__ == '__main__':
    sys.exit(main())
