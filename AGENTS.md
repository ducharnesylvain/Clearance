# AGENTS.md

Rules for anyone working in this repository, human or AI agent (Claude Code, Cursor, Codex, Gemini CLI and others read this file).

## What this repo is

Clearance is an eval-first AI decision copilot: it checks a proposed business change against written policies, cites every claim, and escalates to a human when unsure. It is also a public portfolio piece read by recruiters and hiring managers. The product owner makes the product decisions; agents propose, build and verify.

## Rule 1: the README is the front page, keep it current

`README.md` is written for recruiters and hiring managers first, then for developers. It must always describe the real state of the project.

Every change that touches code, domain packs, evals or the demo must update `README.md` in the same pull request:

- **Status line and badges**: current phase, and whether evals have run.
- **Progress checklist**: tick what is done, never tick what is partial.
- **Results table**: real numbers only, with the date and the model versions. Never write a target as if it were a result.
- **Build log**: one dated line per meaningful change, written as an outcome ("Escalation recall measured at 0.92 on 40 cases"), not as an activity ("worked on evals").

CI fails a pull request that changes `src/`, `domains/`, `evals/` or `app/` without touching `README.md`. Use the `no-readme-change` label only for pure refactors with no visible effect.

Tone of the README: plain international English, short sentences, outcomes and evidence before features, no hype words ("revolutionary", "cutting-edge", "seamless").

## Rule 2: no personal or real data, ever

- All companies, people, policies, prices and figures are **fictional**. Do not paste real company documents, real names, real emails or real figures, even "just for testing".
- Fictional emails use `example.com`, `example.org` or `example.net`. Fictional bank details use the `XX00` prefix.
- Secrets live in environment variables or GitHub secrets, never in files. `.env` is ignored.
- The guard (`scripts/check_sensitive.py`) runs as a pre-commit hook and in CI. Do not bypass it. A true false positive can be allowed on its line with the marker `sensitive-ok` and a short reason.

## Rule 3: evals first, honest numbers

- No feature without a test case that shows it works and a case that shows how it fails.
- Keep a held-out split of the test set that is never used for tuning prompts or retrieval.
- Report model names and versions, dates, sample sizes and cost with every result.
- If a result is bad, report it. A documented failure is more useful than a hidden one.

## Rule 4: decisions are written down

Any non-trivial choice (architecture, model, threshold, scope cut) gets a short entry in `docs/decisions.md`: context, options, decision, evidence, trade-off. Product decisions are made by the product owner; agents present options with a recommendation.

## Rule 5: style

- No en-dash or em-dash characters in any file. Use a hyphen, a colon, a comma or parentheses.
- Straight quotes in code and data files.
- Lean by default: prefer editing an existing file over creating a new one.

## Commands

```bash
pip install pre-commit && pre-commit install   # enable the guard locally
python scripts/check_sensitive.py               # scan all tracked files
python scripts/validate_pack.py domains/commercial-policy --write-review   # check a pack, refresh its review sheet
```

Optional: put personal terms you never want committed (your name, address, phone) in a local `.sensitive-terms` file, one per line. It is git-ignored and read by the guard. In CI, the same list can be provided through the `SENSITIVE_TERMS` repository secret.
