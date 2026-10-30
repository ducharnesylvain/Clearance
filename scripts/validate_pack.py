#!/usr/bin/env python3
"""Validate a domain pack: corpus metadata, clause numbering, and labelled cases.

Usage:
    python scripts/validate_pack.py domains/commercial-policy
    python scripts/validate_pack.py domains/commercial-policy --write-review

Checks
  corpus: front matter present, one current version per document id,
          superseded versions point to an existing version, clauses unique
  cases:  required fields, unique ids, valid verdicts, escalation reason only
          on escalations, every must_cite points to an existing clause of the
          CURRENT version, case mix matches pack.yaml
With --write-review, regenerates cases/REVIEW.md for the human reviewer.
Exit code 1 on any error. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

VERDICTS = {"clear", "clear_with_conditions", "blocked", "escalate"}
REASONS = {"missing_rule", "conflicting_rules", "out_of_scope", "low_confidence"}
REQUIRED = [
    "id", "split", "category", "request", "context", "expected_verdict",
    "expected_escalation_reason", "must_cite", "must_not_claim", "expected_facts",
    "rationale", "label_status",
]
CLAUSE = re.compile(r"^\*\*(\d+\.\d+)\*\*\s+(.+)$")


def front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    head, _, body = text[4:].partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            meta[key.strip()] = value.strip().strip('"')
    return meta, body


def load_case_mix(pack_yaml: str) -> dict[str, dict[str, int]]:
    """Read the case_mix block of pack.yaml without a YAML dependency."""
    mix: dict[str, dict[str, int]] = {}
    in_mix, split = False, None
    for raw in pack_yaml.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if line.startswith("case_mix:"):
            in_mix = True
            continue
        if in_mix and not line.startswith(" "):
            break
        if in_mix and line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            split = line.strip()[:-1]
            mix[split] = {}
        elif in_mix and split and line.startswith("    "):
            key, _, val = line.strip().partition(":")
            mix[split][key.strip()] = int(val)
    return mix


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    pack = Path(argv[0])
    errors: list[str] = []

    # ---- corpus ----
    docs: dict[tuple[str, str], dict] = {}
    current: dict[str, str] = {}
    for path in sorted((pack / "corpus").glob("*.md")):
        meta, body = front_matter(path.read_text(encoding="utf-8"))
        for key in ("id", "title", "version", "status"):
            if key not in meta:
                errors.append(f"{path.name}: missing front matter '{key}'")
        if not {"id", "version", "status"} <= meta.keys():
            continue
        clauses: dict[str, str] = {}
        for line in body.splitlines():
            m = CLAUSE.match(line.strip())
            if m:
                if m.group(1) in clauses:
                    errors.append(f"{path.name}: duplicate clause {m.group(1)}")
                clauses[m.group(1)] = m.group(2)
        if not clauses:
            errors.append(f"{path.name}: no numbered clauses found")
        key = (meta["id"], meta["version"])
        if key in docs:
            errors.append(f"{path.name}: duplicate {key}")
        docs[key] = {"meta": meta, "clauses": clauses, "file": path.name}
        if meta["status"] == "current":
            if meta["id"] in current:
                errors.append(f"{meta['id']}: more than one current version")
            current[meta["id"]] = meta["version"]
        elif meta["status"] != "superseded":
            errors.append(f"{path.name}: status must be current or superseded")
    for (doc_id, version), d in docs.items():
        nxt = d["meta"].get("superseded_by")
        if d["meta"]["status"] == "superseded" and (doc_id, nxt) not in docs:
            errors.append(f"{d['file']}: superseded_by {nxt} not found")

    # ---- cases ----
    cases = []
    for split in ("dev", "holdout"):
        path = pack / "cases" / f"{split}.jsonl"
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{n}: invalid JSON ({exc})")
                continue
            case["_file_split"] = split
            cases.append(case)

    seen = set()
    mix = Counter()
    status = Counter()
    for case in cases:
        cid = case.get("id", "?")
        for field in REQUIRED:
            if field not in case:
                errors.append(f"{cid}: missing field '{field}'")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        if case.get("split") != case["_file_split"]:
            errors.append(f"{cid}: split field does not match file")
        verdict = case.get("expected_verdict")
        reason = case.get("expected_escalation_reason")
        if verdict not in VERDICTS:
            errors.append(f"{cid}: invalid verdict {verdict}")
        if verdict == "escalate" and reason not in REASONS:
            errors.append(f"{cid}: escalation needs a valid reason")
        if verdict != "escalate" and reason is not None:
            errors.append(f"{cid}: reason set on a non-escalation")
        for cite in case.get("must_cite", []):
            doc_id, section = cite.get("doc_id"), cite.get("section")
            version = current.get(doc_id)
            if version is None:
                errors.append(f"{cid}: cites unknown document {doc_id}")
            elif section not in docs[(doc_id, version)]["clauses"]:
                errors.append(f"{cid}: {doc_id} v{version} has no clause {section}")
        mix[(case["_file_split"], case.get("category"))] += 1
        status[case.get("label_status")] += 1

    expected = load_case_mix((pack / "pack.yaml").read_text(encoding="utf-8"))
    for split, cats in expected.items():
        for cat, count in cats.items():
            if mix[(split, cat)] != count:
                errors.append(f"case mix: {split}/{cat} has {mix[(split, cat)]}, expected {count}")
        extra = {c for (s, c) in mix if s == split} - set(cats)
        for cat in sorted(extra):
            errors.append(f"case mix: unexpected category {split}/{cat}")

    if "--write-review" in argv:
        write_review(pack, cases, docs, current)

    print(f"Corpus: {len(docs)} documents, {len(current)} current, "
          f"{sum(len(d['clauses']) for d in docs.values())} clauses")
    print(f"Cases: {len(cases)} ({mix_total(mix, 'dev')} dev, {mix_total(mix, 'holdout')} holdout); "
          f"labels: {status.get('validated', 0)} validated, {status.get('draft', 0)} draft")
    if errors:
        print("\nErrors:\n" + "\n".join(f"  - {e}" for e in errors))
        return 1
    print("Pack is valid.")
    return 0


def mix_total(mix: Counter, split: str) -> int:
    return sum(v for (s, _), v in mix.items() if s == split)


def write_review(pack: Path, cases: list[dict], docs: dict, current: dict) -> None:
    def cite_text(c: dict) -> str:
        return ", ".join(f"{x['doc_id']} {x['section']}" for x in c["must_cite"]) or "none"

    lines = [
        "# Label review sheet",
        "",
        "Generated by `scripts/validate_pack.py --write-review`. Do not edit by hand: change the cases, then regenerate.",
        "",
        "For each case, check the request, the expected verdict and the citations. "
        "Reply with the case id and either OK or the correction.",
        "",
    ]
    order = ["clearly_allowed", "clearly_blocked", "allowed_with_conditions", "conflicting_rules",
             "superseded_version", "missing_rule", "out_of_scope", "prompt_injection", "needs_calculation"]
    by_cat = defaultdict(list)
    for c in cases:
        by_cat[c["category"]].append(c)
    for cat in order:
        if not by_cat.get(cat):
            continue
        lines += [f"## {cat.replace('_', ' ').capitalize()}", "",
                  "| Id | Split | Request | Expected | Must cite | Why | Status |",
                  "|---|---|---|---|---|---|---|"]
        for c in sorted(by_cat[cat], key=lambda x: x["id"]):
            verdict = c["expected_verdict"]
            if c["expected_escalation_reason"]:
                verdict += f" ({c['expected_escalation_reason']})"
            req = c["request"] + (f" *Context: {c['context']}*" if c["context"] else "")
            why = c["rationale"]
            if c["expected_facts"]:
                why += " Must state: " + "; ".join(c["expected_facts"]) + "."
            if c["must_not_claim"]:
                why += " Must not claim: " + "; ".join(c["must_not_claim"]) + "."
            row = [c["id"], c["split"], req, f"`{verdict}`", cite_text(c), why, c["label_status"]]
            lines.append("| " + " | ".join(x.replace("|", "/") for x in row) + " |")
        lines.append("")
    (pack / "cases" / "REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
