#!/usr/bin/env python3
"""PII classification from hints.pii_candidates. Emit findings for unencrypted credentials."""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from manifest_lib import load_manifest, hints, append_finding, write_evidence, get_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--phase', default='07')
    args = ap.parse_args()

    m = load_manifest()
    _, project_root, _, _, _ = get_paths()
    pii = hints(m).get('pii_candidates', []) or []

    md = ['# PII classification', '']
    md.append('| Table | Column | Classification | Encrypted? | File:Lines |')
    md.append('|-------|--------|----------------|------------|------------|')
    for p in pii:
        md.append(f"| {p['table']} | {p['column']} | {p.get('classification','?')} | "
                  f"{'yes' if p.get('encrypted_at_rest') else '**NO**'} | {p['file']}:{p['lines']} |")

    write_evidence(args.phase, 'pii_classification.md', '\n'.join(md))

    # Secret scan placeholder (gitleaks if available)
    secret_evidence = []
    try:
        r = subprocess.run(['gitleaks', 'detect', '--no-banner', '--no-git', '--source', str(project_root),
                            '--report-format', 'json'],
                           capture_output=True, text=True, timeout=60)
        secret_evidence.append(r.stdout[:5000] if r.stdout else 'gitleaks: no secrets found')
    except (FileNotFoundError, subprocess.TimeoutExpired):
        secret_evidence.append('gitleaks not available — fallback grep')
        try:
            grep = subprocess.run(['rg', '-nE',
                                   r'sk_live_|sk_test_|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|postgres(ql)?://[^:]+:[^@]+@',
                                   '-g', '!node_modules', '-g', '!.git', str(project_root)],
                                  capture_output=True, text=True, timeout=30)
            secret_evidence.append(grep.stdout[:5000])
        except Exception:
            pass
    write_evidence(args.phase, 'secret_scan.txt', '\n'.join(secret_evidence))

    for p in pii:
        cls = p.get('classification', '')
        if cls in ('sensitive', 'payment-card', 'biometric', 'credentials') and not p.get('encrypted_at_rest'):
            sev = 'critical' if cls in ('credentials', 'payment-card') else 'high'
            finding = {
                'phase': args.phase,
                'category': 'security',
                'subcategory': f'pii-unencrypted-{cls}',
                'severity': sev,
                'confidence': 'high',
                'title': f'{cls} PII хранится без шифрования: {p["table"]}.{p["column"]}',
                'location': {'file': p['file'], 'lines': p['lines'],
                             'db_object': f"{p['table']}.{p['column']}"},
                'evidence': (f'Колонка {p["table"]}.{p["column"]} в {p["file"]}:{p["lines"]} '
                             f'хранит {cls} PII в plain text (encrypted_at_rest=false).'),
                'confidence_rationale': ('Manifest подтверждает классификацию и отсутствие encryption. '
                                         'Тип/имя колонки указывают на sensitive данные.'),
                'impact': 'Утечка sensitive PII при breach. GDPR Art. 32 нарушен.',
                'recommendation': ('Перенести в secret manager (Vault, AWS Secrets Manager) либо '
                                   'application-level encryption (pgcrypto / AES-GCM). Закрыть в логах.'),
                'effort': 'M',
                'references': [
                    'OWASP Database Security Cheat Sheet',
                    'NIST SP 800-122',
                    'GDPR Article 32'
                ],
            }
            if sev == 'critical':
                finding['exploit_proof'] = (
                    f'Любой имеющий read-доступ к таблице {p["table"]} (DBA, replica, backup, leak) '
                    f'получает {cls} в plain text. Подтверждено: encrypted_at_rest=false в manifest.'
                )
            append_finding(finding)

    print(f'OK: pii — {len(pii)} candidates')
    return 0


if __name__ == '__main__':
    sys.exit(main())
