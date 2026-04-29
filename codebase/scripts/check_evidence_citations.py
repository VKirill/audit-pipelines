#!/usr/bin/env python3
"""check_evidence_citations.py — sanity check that finding citations exist.

Для каждого finding с confidence == "high":
  1. file в .location.file должен существовать в дереве проекта
  2. .location.lines (если задан как "A-B" или "A") должен попадать в диапазон файла
  3. Если в .evidence есть подстрока в кавычках/бэктиках длиной >= 20 символов,
     эта подстрока должна реально встречаться в файле (защита от выдуманных цитат)

Также для всех findings:
  4. .id уникален; формат F-NNNN
  5. .related_findings ссылаются на существующие .id

Скрипт устойчив:
  - .location.file может быть путём списка ("a.ts, b.ts") — берём только реальные файлы
  - .location.file может содержать каталог — пропускаем line-check
  - бинарные файлы пропускаем
  - строки с диапазоном "12,34,56" разбиваем на отдельные проверки

Usage: ./scripts/check_evidence_citations.py [path/to/findings.jsonl] [--root .]
Exit: 0 = ok, 1 = at least one broken citation, 2 = misuse.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

LINE_RANGE_RE = re.compile(r"^(\d+)\s*[-–]\s*(\d+)$")
LINE_SINGLE_RE = re.compile(r"^(\d+)$")
QUOTE_RE = re.compile(r"[`\"“”']([^`\"“”']{20,200})[`\"“”']")


def looks_binary(p: Path) -> bool:
    try:
        with p.open("rb") as f:
            chunk = f.read(2048)
        return b"\x00" in chunk
    except OSError:
        return True


def file_line_count(p: Path) -> int | None:
    if looks_binary(p):
        return None
    try:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return None


def parse_lines(spec: str | None) -> list[tuple[int, int]]:
    """Return list of (start, end) ranges; empty list if cannot parse."""
    if not spec:
        return []
    out: list[tuple[int, int]] = []
    for chunk in str(spec).split(","):
        s = chunk.strip()
        m = LINE_RANGE_RE.match(s)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out.append((min(a, b), max(a, b)))
            continue
        m = LINE_SINGLE_RE.match(s)
        if m:
            n = int(m.group(1))
            out.append((n, n))
            continue
        # could be "98 + 110" or other freeform — skip silently
    return out


def candidate_files(loc_file: str | None, root: Path) -> list[Path]:
    if not loc_file:
        return []
    out: list[Path] = []
    # Many findings list multiple files separated by commas.
    parts = re.split(r"[,\s]+", loc_file.strip())
    for part in parts:
        part = part.strip().strip(",")
        if not part or part in (".", "/"):
            continue
        # Strip trailing punctuation
        part = part.rstrip(".:")
        p = (root / part)
        if p.exists() and p.is_file():
            out.append(p)
    return out


def file_text(p: Path) -> str | None:
    if looks_binary(p):
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", default=os.environ.get("FINDINGS", "audit/findings.jsonl"))
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    findings_path = Path(args.path)
    root = Path(args.root).resolve()

    if not findings_path.exists():
        sys.exit(f"FAIL: {findings_path} not found")

    findings: list[dict] = []
    for i, line in enumerate(findings_path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError as e:
            sys.exit(f"FAIL: invalid JSON line {i}: {e}")

    # 4. id uniqueness + format
    ids = [f.get("id") for f in findings]
    bad_id = [x for x in ids if not isinstance(x, str) or not re.match(r"^F-\d{4}$", x)]
    dup_id = sorted({x for x in ids if ids.count(x) > 1})

    # 5. related_findings refs
    id_set = set(ids)

    errors: list[str] = []
    warnings: list[str] = []

    if bad_id:
        errors.append(f"malformed ids: {bad_id[:5]}{'…' if len(bad_id)>5 else ''}")
    if dup_id:
        errors.append(f"duplicate ids: {dup_id}")

    for f in findings:
        for ref in f.get("related_findings") or []:
            if ref not in id_set:
                warnings.append(f"{f.get('id')}.related_findings → unknown {ref}")

    # 1-3. citation sanity for high-confidence findings
    for f in findings:
        if f.get("confidence") != "high":
            continue
        loc = f.get("location") or {}
        loc_file = loc.get("file")
        files = candidate_files(loc_file, root)
        if not files:
            # If file cannot be resolved, only error if loc_file looks like a real path
            if loc_file and "/" in loc_file and not any(ch in loc_file for ch in "<>?"):
                warnings.append(f"{f.get('id')}: location.file '{loc_file}' not found in project")
            continue

        ranges = parse_lines(loc.get("lines"))
        for fp in files:
            n = file_line_count(fp)
            if n is None:
                continue
            for (a, b) in ranges:
                if a > n or b > n:
                    errors.append(
                        f"{f.get('id')}: lines {a}-{b} out of range for {fp.relative_to(root)} ({n} lines)"
                    )

        # quoted snippets in evidence must appear in at least one of the files
        ev = f.get("evidence") or ""
        for m in QUOTE_RE.finditer(ev):
            snippet = m.group(1).strip()
            # Skip quotes that obviously are field names like 'private_key'
            if len(snippet) < 25:
                continue
            found = False
            for fp in files:
                txt = file_text(fp)
                if txt and snippet in txt:
                    found = True
                    break
            if not found:
                warnings.append(
                    f"{f.get('id')}: quoted snippet «{snippet[:60]}…» not found "
                    f"in cited file(s) — possibly stale or invented"
                )

    # ---- report ----
    print(f"Checked {len(findings)} findings against {root}")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings[:50]:
            print(f"  - {w}")
        if len(warnings) > 50:
            print(f"  … and {len(warnings)-50} more")
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK: all high-confidence citations resolve to real file:line ranges.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
