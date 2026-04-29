#!/usr/bin/env python3
"""validate_confidence.py — global confidence-distribution gate (v3).

Реализует §4.2 Orchestrator с механической проверкой:
  * total >= 20 findings: high% must be in [30, 60], low% must be >= 5
  * total >= 10:          high% must be <= 70
  * any phase: NO bucket may be 100% if phase has >= 4 findings
  * any phase: NO single severity may be 100% if phase has >= 4 findings

Также печатает таблицу распределения, чтобы агент видел картину при правках.

Usage: ./scripts/validate_confidence.py [path/to/findings.jsonl]
Exit:  0 = ok, 1 = violation (with explanation), 2 = misuse.
"""
from __future__ import annotations
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_PATH = Path(os.environ.get("FINDINGS", "audit/findings.jsonl"))


def load(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"FAIL: {path} not found")
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f"FAIL: line {i} of {path}: {e}")
    return out


def pct(n: int, total: int) -> float:
    return 100.0 * n / total if total else 0.0


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    findings = load(path)
    total = len(findings)
    if total == 0:
        print("WARN: no findings to validate")
        return 0

    conf = Counter(f.get("confidence", "?") for f in findings)
    sev = Counter(f.get("severity", "?") for f in findings)
    by_phase: dict[int, list[dict]] = defaultdict(list)
    for f in findings:
        by_phase[f.get("phase", -1)].append(f)

    # ---- print summary ----
    print(f"Total findings: {total}")
    print("Confidence:", {k: f"{v} ({pct(v,total):.0f}%)" for k, v in conf.items()})
    print("Severity:  ", {k: f"{v} ({pct(v,total):.0f}%)" for k, v in sev.items()})
    print("By phase:")
    for p in sorted(by_phase):
        c = Counter(f.get("confidence") for f in by_phase[p])
        s = Counter(f.get("severity") for f in by_phase[p])
        print(f"  phase {p}: n={len(by_phase[p])}  conf={dict(c)}  sev={dict(s)}")

    violations: list[str] = []

    # ---- global confidence gates ----
    high_pct = pct(conf.get("high", 0), total)
    low_pct = pct(conf.get("low", 0), total)
    med_pct = pct(conf.get("medium", 0), total)

    if total >= 20:
        if high_pct > 60:
            violations.append(
                f"global high% = {high_pct:.0f}% > 60% — пересмотри §3.3 ORCHESTRATOR. "
                "Убедись что каждый high имеет цитату строк и не зависит от рантайма."
            )
        if high_pct < 30:
            violations.append(
                f"global high% = {high_pct:.0f}% < 30% — слишком мало уверенных находок; "
                "возможно ты пропустил очевидное."
            )
        if low_pct < 5:
            violations.append(
                f"global low% = {low_pct:.0f}% < 5% — нет ни одной grep-эвристики? "
                "Маловероятно для проекта 20+ findings."
            )

    elif total >= 10:
        if high_pct > 70:
            violations.append(
                f"global high% = {high_pct:.0f}% > 70% — для {total} findings слишком уверенно."
            )

    # ---- per-phase monoculture ----
    for p, items in by_phase.items():
        n = len(items)
        if n >= 4:
            c_buckets = {k: v for k, v in Counter(f.get("confidence") for f in items).items()}
            if any(v == n for v in c_buckets.values()):
                bucket = next(k for k, v in c_buckets.items() if v == n)
                violations.append(
                    f"phase {p}: all {n} findings have confidence={bucket} — under-calibrated"
                )
            s_buckets = {k: v for k, v in Counter(f.get("severity") for f in items).items()}
            if any(v == n for v in s_buckets.values()):
                bucket = next(k for k, v in s_buckets.items() if v == n)
                violations.append(
                    f"phase {p}: all {n} findings have severity={bucket} — likely batched without thought"
                )

    # ---- critical severity needs exploit_proof ----
    bad_crit = [
        f for f in findings
        if f.get("severity") == "critical" and len((f.get("exploit_proof") or "")) < 40
    ]
    for f in bad_crit:
        violations.append(
            f"finding {f.get('id')} severity=critical without exploit_proof (>=40 chars)"
        )

    # ---- high confidence needs rationale + lines ----
    bad_high = [
        f for f in findings
        if f.get("confidence") == "high"
        and (
            len((f.get("confidence_rationale") or "")) < 40
            or (f.get("location") or {}).get("lines") in (None, "", "null")
        )
    ]
    for f in bad_high:
        violations.append(
            f"finding {f.get('id')} confidence=high without confidence_rationale (>=40 chars) "
            f"or with empty location.lines"
        )

    print()
    if violations:
        print("VIOLATIONS:")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("OK: confidence distribution within v3 bounds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
