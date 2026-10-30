#!/usr/bin/env python3
"""Block personal data and secrets before they reach the repository.

Usage:
    python scripts/check_sensitive.py              # scan all tracked files
    python scripts/check_sensitive.py FILE [...]   # scan given files (pre-commit)

Checks every text file for:
  - email addresses outside reserved example domains
  - phone numbers in international format
  - IBAN-like bank account numbers (fictional ones must start with XX00)
  - API keys and private keys
  - an optional personal deny-list: a local, git-ignored `.sensitive-terms`
    file and/or the SENSITIVE_TERMS environment variable (one term per line)

A line can be allowed with the marker `sensitive-ok` plus a short reason.
Exit code 1 if anything is found.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOW_MARKER = "sensitive-ok"
MAX_BYTES = 2_000_000

ALLOWED_EMAIL_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "users.noreply.github.com",
}

PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})"),
    "phone": re.compile(r"(?<![\w.])\+\d{1,3}(?:[ \-]?\d){7,12}(?![\d.%])"),
    "iban": re.compile(r"\b(?!XX00)[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}(?: ?[A-Z0-9]{1,3})?\b"),
    "anthropic_key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}"),
    "google_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "github_token": re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".whl", ".lock"}


def load_terms() -> list[str]:
    terms: list[str] = []
    local = ROOT / ".sensitive-terms"
    if local.exists():
        terms += local.read_text(encoding="utf-8").splitlines()
    terms += os.environ.get("SENSITIVE_TERMS", "").splitlines()
    return [t.strip().lower() for t in terms if t.strip() and not t.strip().startswith("#")]


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    return [ROOT / p for p in out.split("\0") if p]


def is_text(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
        return False
    if path.stat().st_size > MAX_BYTES:
        return False
    with path.open("rb") as fh:
        return b"\0" not in fh.read(4096)


def scan_file(path: Path, terms: list[str]) -> list[str]:
    findings: list[str] = []
    rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    if rel.as_posix() in {".sensitive-terms", "scripts/check_sensitive.py"}:
        return findings
    text = path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                if name == "email" and match.group(1).lower() in ALLOWED_EMAIL_DOMAINS:
                    continue
                findings.append(f"{rel}:{lineno}: {name}: {mask(match.group(0))}")
        lowered = line.lower()
        for term in terms:
            if term in lowered:
                findings.append(f"{rel}:{lineno}: personal term from deny-list")
    return findings


def mask(value: str) -> str:
    if len(value) <= 6:
        return "***"
    return value[:3] + "***" + value[-2:]


def main(argv: list[str]) -> int:
    terms = load_terms()
    files = [Path(a).resolve() for a in argv] if argv else tracked_files()
    findings: list[str] = []
    for path in files:
        if is_text(path):
            findings += scan_file(path, terms)
    if findings:
        print("Sensitive data guard: blocked.\n")
        print("\n".join(findings))
        print(
            "\nRemove the data, use fictional values (example.com emails, XX00 bank numbers),"
            f"\nor mark a true false positive with '{ALLOW_MARKER}' and a reason."
        )
        return 1
    print(f"Sensitive data guard: {len(files)} file(s) checked, nothing found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
