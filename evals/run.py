"""Run labelled cases through architectures and models, score them, write a report.

Examples:
    python -m evals.run --pack domains/commercial-policy --split dev --arch A B --models claude-small
    python -m evals.run --pack domains/commercial-policy --split dev --arch B --models fake   # offline dry run
    python -m evals.run --pack domains/commercial-policy --split holdout --arch B --models claude-small \
        --repeats 3 --confirm-holdout

Outputs go to runs/<timestamp>_<split>/: results.jsonl (one row per case), summary.json, summary.md.
The holdout split only runs with --confirm-holdout (SPEC 9.5: once per milestone).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

from clearance.engine import run as run_engine
from clearance.models import FakeModel, ModelSpec, build_model, load_specs
from clearance.pack import load_pack

from .metrics import TARGETS, aggregate, latency_stats, met, score_case

FAKE_ANSWER = json.dumps({
    "verdict": "escalate", "summary": "Offline dry run: no model was called.",
    "conditions": [], "required_actions": [], "risks": [], "open_questions": [],
    "citations": [], "confidence": 0.0, "escalation_reason": "low_confidence",
})


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pack", required=True)
    p.add_argument("--split", choices=["dev", "holdout"], default="dev")
    p.add_argument("--arch", nargs="+", default=["B"], choices=["A", "B"])
    p.add_argument("--models", nargs="+", default=["claude-small"])
    p.add_argument("--models-file", default="evals/models.yaml")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--limit", type=int, default=None, help="only the first N cases (smoke runs)")
    p.add_argument("--confirm-holdout", action="store_true")
    p.add_argument("--out", default="runs")
    return p.parse_args(argv)


def make_model(name: str, specs: dict[str, ModelSpec]):
    if name == "fake":
        return FakeModel(lambda s, u: FAKE_ANSWER), ModelSpec("fake", "fake", "fake")
    spec = specs[name]
    return build_model(spec), spec


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.split == "holdout" and not args.confirm_holdout:
        print("Refusing to run the holdout split without --confirm-holdout (SPEC 9.5).", file=sys.stderr)
        return 2

    pack = load_pack(args.pack)
    cases = pack.cases(args.split)[: args.limit]
    specs = load_specs(args.models_file) if any(m != "fake" for m in args.models) else {}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out) / f"{stamp}_{pack.name}_{args.split}"
    out_dir.mkdir(parents=True, exist_ok=True)

    configs = []
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as rows:
        for model_name in args.models:
            model, spec = make_model(model_name, specs)
            for arch in args.arch:
                per_repeat, latencies, tok_in, tok_out = [], [], 0, 0
                for rep in range(args.repeats):
                    scores = []
                    for case in cases:
                        result = run_engine(pack, model, arch, case["request"], case.get("context", ""))
                        score = score_case(case, result.decision, pack)
                        scores.append(score)
                        c = result.completion
                        latencies.append(c.latency_s)
                        tok_in, tok_out = tok_in + c.input_tokens, tok_out + c.output_tokens
                        rows.write(json.dumps({
                            "arch": arch, "model": model_name, "model_id": spec.model_id, "repeat": rep,
                            "case_id": case["id"], "error": result.error, "raw": result.raw_text,
                            "decision": result.decision.model_dump() if result.decision else None,
                            "score": score.to_dict(), "input_tokens": c.input_tokens,
                            "output_tokens": c.output_tokens, "latency_s": round(c.latency_s, 3),
                        }, ensure_ascii=False) + "\n")
                        print(f"{model_name:>12} {arch} r{rep} {case['id']}: expected {score.expected:<22} "
                              f"got {score.predicted or 'INVALID'}")
                    per_repeat.append(aggregate(scores))
                calls = len(cases) * args.repeats
                cost = spec.cost(tok_in, tok_out)
                configs.append({
                    "arch": arch, "model": model_name, "model_id": spec.model_id,
                    "metrics": _combine(per_repeat),
                    "latency": latency_stats(latencies),
                    "tokens": {"input": tok_in, "output": tok_out},
                    "cost_usd_total": None if cost is None else round(cost, 4),
                    "cost_usd_per_decision": None if cost is None else round(cost / calls, 5),
                })

    summary = {"run": out_dir.name, "date_utc": stamp, "pack": pack.name, "split": args.split,
               "cases": len(cases), "repeats": args.repeats, "label_status": _label_status(cases),
               "configs": configs}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    print(f"\nWrote {out_dir}")
    return 0


def _combine(per_repeat: list[dict]) -> dict:
    """Mean over repeats, with min and max when there is more than one."""
    if len(per_repeat) == 1:
        return per_repeat[0]
    combined = {"repeats": len(per_repeat)}
    for key, value in per_repeat[0].items():
        if key == "targets":
            continue
        values = [r[key] for r in per_repeat if r[key] is not None]
        if not values:
            combined[key] = None
        else:
            combined[key] = round(statistics.mean(values), 4)
            combined[f"{key}_range"] = [min(values), max(values)]
    combined["targets"] = {name: {"target": t, "direction": d, "met": met(combined.get(name), t, d)}
                           for name, (t, d) in TARGETS.items()}
    return combined


def _label_status(cases: list[dict]) -> dict:
    out: dict[str, int] = {}
    for c in cases:
        out[c.get("label_status", "unknown")] = out.get(c.get("label_status", "unknown"), 0) + 1
    return out


ROWS = [
    ("valid_output_rate", "Valid JSON decisions"),
    ("verdict_accuracy", "Verdict accuracy"),
    ("escalation_recall", "Escalation recall"),
    ("escalation_precision", "Escalation precision"),
    ("citation_recall", "Citation recall"),
    ("citation_validity", "Citation validity (precision proxy)"),
    ("quote_validity", "Exact quote validity"),
    ("unsupported_claim_rate", "Unsupported claim rate"),
    ("injection_resistance", "Injection resistance"),
    ("superseded_reliance_rate", "Relied on a superseded rule"),
    ("facts_recall", "Expected facts stated"),
]


def labels_text(status: dict) -> str:
    return ", ".join(f"{n} {k}" for k, n in sorted(status.items()))


def _fmt(value) -> str:
    return "n/a" if value is None else f"{value:.0%}" if isinstance(value, float) else str(value)


def render_markdown(summary: dict) -> str:
    cfgs = summary["configs"]
    head = "| Metric | Target | " + " | ".join(f"{c['arch']} / {c['model_id'] or c['model']}" for c in cfgs) + " |"
    lines = [
        f"# Eval run {summary['run']}",
        "",
        f"Pack `{summary['pack']}`, split `{summary['split']}`, {summary['cases']} cases, "
        f"{summary['repeats']} repeat(s). Labels: {labels_text(summary['label_status'])}.",
        "",
        head,
        "|" + "---|" * (2 + len(cfgs)),
    ]
    for key, label in ROWS:
        target = TARGETS.get(key)
        t = "" if not target else (f">= {target[0]:.0%}" if target[1] == "min" else f"<= {target[0]:.0%}")
        cells = []
        for c in cfgs:
            v = c["metrics"].get(key)
            met = c["metrics"].get("targets", {}).get(key, {}).get("met")
            mark = "" if met is None else (" (met)" if met else " (missed)")
            cells.append(_fmt(v) + mark)
        lines.append(f"| {label} | {t} | " + " | ".join(cells) + " |")
    lines.append("| Latency p50 / p95 | p95 < 20 s (demo model) | " + " | ".join(
        f"{c['latency']['p50_s']} s / {c['latency']['p95_s']} s" for c in cfgs) + " |")
    lines.append("| Cost per decision | reported | " + " | ".join(
        "not priced" if c["cost_usd_per_decision"] is None else f"${c['cost_usd_per_decision']}" for c in cfgs) + " |")
    lines += ["", "Citation validity checks that a citation points to a real clause of a current policy and quotes "
              "it word for word. Whether it supports its claim is judged from M4 on."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
