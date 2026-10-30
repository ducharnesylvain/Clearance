"""Publish an eval run: copy its report to docs/results/ and refresh the README results block.

Usage:
    python -m evals.report runs/<run-folder>            # publish and update README.md
    python -m evals.report runs/<run-folder> --check    # print what would change

The README block sits between <!-- results:start --> and <!-- results:end -->.
Only real runs can be published: a run made with the fake model is refused.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .run import labels_text, render_markdown

START, END = "<!-- results:start -->", "<!-- results:end -->"


def readme_block(summary: dict, report_path: str) -> str:
    table = render_markdown(summary).split("\n", 4)[4]  # drop title and context lines
    table = table.split("\nCitation validity checks")[0].strip()
    date = summary["date_utc"]
    when = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    return (
        f"{START}\n"
        f"Latest run: {when}, pack `{summary['pack']}`, split `{summary['split']}`, "
        f"{summary['cases']} cases ({labels_text(summary['label_status'])} labels). "
        f"Full report: [{report_path}]({report_path}).\n\n"
        f"{table}\n"
        f"{END}"
    )


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    run_dir = Path(argv[0])
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    if any(c["model"] == "fake" for c in summary["configs"]):
        print("Refusing to publish a dry run made with the fake model.", file=sys.stderr)
        return 2
    report_path = f"docs/results/{summary['run']}.md"
    block = readme_block(summary, report_path)
    readme = Path("README.md").read_text(encoding="utf-8")
    if START not in readme or END not in readme:
        print("README.md has no results markers.", file=sys.stderr)
        return 1
    before, rest = readme.split(START, 1)
    _, after = rest.split(END, 1)
    if "--check" in argv:
        print(block)
        return 0
    Path("docs/results").mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text((run_dir / "summary.md").read_text(encoding="utf-8"), encoding="utf-8")
    Path("README.md").write_text(before + block + after, encoding="utf-8")
    print(f"Published {report_path} and refreshed README.md. Update the status line and build log by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
