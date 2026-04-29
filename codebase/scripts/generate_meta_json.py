#!/usr/bin/env python3
"""generate_meta_json.py — write audit/_meta.json with machine-readable summary.

Включает:
  * version, started_at/finished_at (best effort из git timestamps audit/)
  * baseline commit, branch, project size
  * findings totals, distributions
  * per-phase status (report present, lines, evidence count, quota_met)
  * tools_used / tools_skipped (на основании присутствия evidence-файлов)
  * violations (вызывает validate_confidence.py + check_evidence_citations.py + validate_phase.sh)

Usage: ./scripts/generate_meta_json.py [--project-root .]
Exit:  0 always (это генератор, не gate). Печатает путь к _meta.json.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PHASE_NUMBERS = ["00", "01", "02", "02b", "03", "04", "05", "06", "06b",
                 "07", "08", "09", "10", "10a", "11"]


def sh(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        return (out.stdout or "").strip()
    except Exception:
        return ""


def load_findings(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def detect_size(memory_dir: Path) -> str:
    for name in ("audit_phase_00.md", "audit_phase_00"):
        f = memory_dir / name
        if f.exists():
            m = re.search(r"size:\s*([A-Z]+)", f.read_text(encoding="utf-8", errors="replace"))
            if m:
                return m.group(1)
    return "M"


def find_phase_artifacts(audit_dir: Path, phase: str) -> dict:
    reports = sorted(audit_dir.glob(f"{phase}_*.md"))
    ev_dirs = sorted((audit_dir / "evidence").glob(f"{phase}_*"))
    rep = reports[0] if reports else None
    ev_files = []
    if ev_dirs:
        for d in ev_dirs:
            ev_files.extend([f for f in d.iterdir() if f.is_file()])
    return {
        "report_file": str(rep.relative_to(audit_dir.parent)) if rep else None,
        "report_lines": (sum(1 for _ in rep.open(encoding="utf-8", errors="replace")) if rep else 0),
        "evidence_files": [str(f.relative_to(audit_dir.parent)) for f in ev_files],
        "evidence_count": len(ev_files),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--output", default=None, help="default: <root>/audit/_meta.json")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    audit_dir = root / os.environ.get("AUDIT_DIR_BASENAME", "audit")
    if not audit_dir.exists():
        sys.exit(f"FAIL: {audit_dir} not found")
    out_path = Path(args.output) if args.output else (audit_dir / "_meta.json")

    findings_path = audit_dir / "findings.jsonl"
    findings = load_findings(findings_path)

    # Per-phase aggregate
    by_phase = {}
    for f in findings:
        p = str(f.get("phase"))
        by_phase.setdefault(p, []).append(f)

    phases_summary = {}
    for p in PHASE_NUMBERS:
        art = find_phase_artifacts(audit_dir, p)
        n_findings = len(by_phase.get(str(int(p)) if p.isdigit() else p, []))
        # numeric phases
        if p.isdigit():
            n_findings = len(by_phase.get(int(p), []))
        phases_summary[p] = {
            **art,
            "findings_count": n_findings,
        }

    # Tool detection
    ev = audit_dir / "evidence"
    tools_used = []
    tools_skipped = []

    def add_tool(name: str, present: bool):
        (tools_used if present else tools_skipped).append(name)

    add_tool("cloc", (ev / "01_inventory" / "cloc.json").exists())
    add_tool("npm_audit", (ev / "03_dependencies" / "dep_audit.json").exists())
    add_tool("gitleaks", (ev / "06_security" / "gitleaks.json").exists())
    add_tool("gitleaks_history", (ev / "06_security" / "gitleaks_history.json").exists())
    add_tool("trufflehog", (ev / "06_security" / "trufflehog.json").exists())
    add_tool("coverage", any((ev / "07_tests").glob("coverage*.json")))
    # Distinguish placeholder vs real
    for t in tools_used[:]:
        candidate = {
            "cloc": ev / "01_inventory" / "cloc.json",
            "npm_audit": ev / "03_dependencies" / "dep_audit.json",
            "gitleaks": ev / "06_security" / "gitleaks.json",
            "gitleaks_history": ev / "06_security" / "gitleaks_history.json",
            "trufflehog": ev / "06_security" / "trufflehog.json",
        }.get(t)
        if candidate and candidate.exists():
            head = candidate.read_text(encoding="utf-8", errors="replace")[:200]
            if head.startswith("# tool not available"):
                tools_used.remove(t); tools_skipped.append(t + " (placeholder)")

    # Validators (best-effort)
    violations: list[str] = []
    scripts_dir = Path(__file__).resolve().parent

    # validate_confidence
    try:
        r = subprocess.run(
            [sys.executable, str(scripts_dir / "validate_confidence.py"), str(findings_path)],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            for line in r.stdout.splitlines():
                if line.strip().startswith("- "):
                    violations.append("confidence: " + line.strip()[2:])
    except Exception as e:
        violations.append(f"confidence: validator failed to run: {e}")

    # check_evidence_citations
    try:
        r = subprocess.run(
            [sys.executable, str(scripts_dir / "check_evidence_citations.py"),
             str(findings_path), "--root", str(root)],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            in_err = False
            for line in r.stdout.splitlines():
                if line.startswith("ERRORS"):
                    in_err = True; continue
                if in_err and line.strip().startswith("- "):
                    violations.append("citation: " + line.strip()[2:])
    except Exception as e:
        violations.append(f"citation: validator failed to run: {e}")

    # validate_phase per-phase
    phase_validator = scripts_dir / "validate_phase.sh"
    if phase_validator.exists():
        for p in [pp for pp in PHASE_NUMBERS if (audit_dir / "evidence" / "").parent.exists()]:
            if not phases_summary[p]["report_file"]:
                continue
            try:
                r = subprocess.run(
                    ["bash", str(phase_validator), p],
                    capture_output=True, text=True, timeout=60, cwd=root
                )
                if r.returncode != 0:
                    msg = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "FAIL"
                    violations.append(f"phase {p}: {msg}")
            except Exception as e:
                violations.append(f"phase {p}: validator failed: {e}")

    # Git
    branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    head = sh(["git", "rev-parse", "HEAD"], cwd=root)
    last_commit_dt = sh(["git", "log", "-1", "--format=%cI"], cwd=root)

    # Started/finished — best-effort from audit/ mtimes
    audit_files = list(audit_dir.glob("*.md"))
    started_at = (
        datetime.fromtimestamp(min(f.stat().st_mtime for f in audit_files), timezone.utc).isoformat()
        if audit_files else None
    )
    finished_at = (
        datetime.fromtimestamp(max(f.stat().st_mtime for f in audit_files), timezone.utc).isoformat()
        if audit_files else None
    )

    meta = {
        "version": "v3",
        "schema": "audit_pipeline/_meta.json/v3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "root": str(root),
            "branch": branch,
            "baseline_commit": head,
            "last_commit_at": last_commit_dt,
            "size": detect_size(root / ".serena" / "memories"),
        },
        "audit": {
            "started_at": started_at,
            "finished_at": finished_at,
        },
        "findings": {
            "total": len(findings),
            "by_confidence": dict(Counter(f.get("confidence") for f in findings)),
            "by_severity":   dict(Counter(f.get("severity") for f in findings)),
            "by_category":   dict(Counter(f.get("category") for f in findings)),
            "by_phase":      {str(k): v for k, v in dict(Counter(f.get("phase") for f in findings)).items()},
            "critical_ids":  [f.get("id") for f in findings if f.get("severity") == "critical"],
            "high_ids":      [f.get("id") for f in findings if f.get("severity") == "high"],
        },
        "phases": phases_summary,
        "tools_used": sorted(set(tools_used)),
        "tools_skipped": sorted(set(tools_skipped)),
        "violations": violations,
        "verdict": "pass" if not violations else "fail",
    }

    out_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
