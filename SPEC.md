# Clearance: product spec v1.0

**Status:** approved by the product owner on 2026-10-30. Nothing below is built yet; progress is tracked in the README.
**Last updated:** 2026-10-30

Decisions taken during review are listed in section 15 and in the [decision log](docs/decisions.md).

---

## 1. Summary

Clearance checks a proposed business change against a corpus of written rules and returns a structured, cited decision: a verdict, the actions the change requires, the risks, the open questions, and a confidence level. When confidence is low, or the rules are missing or contradictory, it escalates to a human instead of guessing.

The product is built **eval-first**: the labelled test set and the scoring harness exist before the system, and every architecture, model and prompt choice is justified by its effect on the scores.

## 2. Problem

Teams that own commercial or operational rules (pricing, fees, payouts, matching rules) depend on a few experts and scattered documents to know whether a change is allowed and what it implies downstream. This creates:

- **Slow launches:** every change waits in a review queue owned by platform and Finance teams.
- **Inconsistent answers:** two reviewers can read the same policy differently.
- **Expensive errors:** a missed accounting implication or a broken supplier rule costs money and trust.

## 3. Users and jobs to be done

| User | Job to be done | What "good" looks like |
|---|---|---|
| **Requester** (commercial, pricing or operations owner) | "Before I spend a week on a proposal, tell me if it can work and what it needs." | A clear verdict in under a minute, with what to fix |
| **Reviewer** (Finance, platform or compliance owner) | "Only send me what needs my judgment, and show me why." | Fewer, better-prepared escalations, each with sources |
| **Pack author** (the team adopting Clearance) | "Adapt this to my domain without rewriting the engine." | A new domain pack running with its own evals in a day |

## 4. Goals and non-goals

**Goals**

1. Correct, cited verdicts on in-scope requests.
2. Reliable escalation when the system should not decide.
3. Evidence-based choice of architecture and model, with cost and latency reported.
4. A generic core with at least two domain packs, the second added through the public interface only.
5. A live demo with controlled cost, and an eval report anyone can reproduce.

**Non-goals**

- Making final decisions without a human. Clearance is decision support.
- Legal, tax or accounting advice.
- Ingesting real company documents. All data is fictional.
- Fine-tuning models. Prompting, retrieval and tools only.
- Multi-agent orchestration. One engine, at most a few tools.
- A polished front end. The interface is a thin Streamlit app.

## 5. The decision output

Every answer follows one schema, validated in code. Domain packs can add fields but not remove these.

```json
{
  "verdict": "clear | clear_with_conditions | blocked | escalate",
  "summary": "One or two sentences a busy reviewer can act on.",
  "conditions": [{"text": "...", "citations": ["C1"]}],
  "required_actions": [{"text": "...", "citations": ["C2"]}],
  "risks": [{"text": "...", "severity": "low | medium | high", "citations": ["C3"]}],
  "open_questions": [{"text": "..."}],
  "citations": [{"id": "C1", "doc_id": "payouts-policy", "version": "2.1", "section": "4.2", "quote": "..."}],
  "confidence": 0.0,
  "escalation_reason": "missing_rule | conflicting_rules | out_of_scope | low_confidence | null"
}
```

**Hard rules for the output**

- Every condition, action and risk cites at least one source. An uncited claim counts as a failure.
- Quotes must match the source text exactly (checked in code, not by a model).
- Only the current version of a rule can support a verdict. Superseded versions may be mentioned, never relied on.
- `escalate` is a valid, successful answer when the case calls for it.

## 6. Domain packs

A domain pack is a folder. The engine knows nothing about a domain beyond what the pack provides.

```
domains/<pack>/
  pack.yaml          # name, description, schema extensions, tools enabled
  corpus/*.md        # rules, one file per policy, with id, version, effective dates
  cases/dev.jsonl    # labelled cases used while building
  cases/holdout.jsonl# labelled cases never used for tuning
  tools.py           # optional deterministic tools (e.g. fee impact calculator)
```

| Pack | Fictional setting | Example request | Order |
|---|---|---|---|
| **Commercial policy** | **Wandrel**, a fictional experiences marketplace selling tours and activities from local suppliers | "Add a 5% markup on reseller sales and pay those suppliers monthly." | First |
| **Freight matching** | **Corvane**, a fictional digital freight marketplace matching carriers to loads | "Can this carrier with a refrigerated truck take this cross-border load at this price?" | Second, as the portability test |

**Corpus size:** about 20 documents per pack, 1 to 3 pages each, with deliberate versioning (some rules superseded) and a few genuine conflicts.

**Portability metric:** time and lines of code needed to add the freight pack, with zero engine changes as the target.

## 7. Architectures compared

All four run against the same cases and are scored the same way.

| ID | Approach | Why it is in the comparison |
|---|---|---|
| A | Model only, no documents | Lower bound: how much the model "knows" or invents |
| B | Whole corpus in the prompt | Strong, simple baseline for a small corpus |
| C | Retrieval (hybrid keyword and embedding search) | Standard RAG |
| D | Retrieval plus domain tools | Adds deterministic calculations and lookups |

**Expected insight to test, not assume:** with about 20 documents, B may match or beat C. If so, the report states it and estimates the corpus size at which retrieval becomes necessary, by growing the corpus with distractor documents.

## 8. Models compared

| Slot | Model | Role |
|---|---|---|
| 1 | Claude Haiku 5.5 (smallest current Claude model) | Cheapest candidate for production |
| 2 | Claude Opus 5.5 (strongest current Claude model) | Quality ceiling within one vendor |
| 3 | One current OpenAI GPT model | Cross-vendor comparison |
| 4 | One current Google Gemini model | Cross-vendor comparison |

Claude models are named as of October 2026. All four model versions are re-checked and pinned at the first eval run, and recorded in the report. Each run records model id, date, temperature, tokens in and out, cost and latency.

**Judge:** where a metric needs a model as judge (faithfulness), the judge comes from a different vendor than the model being judged, and the judge is calibrated against human labels (section 9.4).

## 9. Evaluation protocol

### 9.1 Test set

| Pack | Dev cases | Holdout cases | Total |
|---|---|---|---|
| Commercial policy | 30 | 10 | 40 |
| Freight matching | 22 | 8 | 30 |

Each case contains: the request, the expected verdict, the facts the answer must cite (by document and section), facts it must not claim, and whether escalation is expected. **The product owner validates every label.**

### 9.2 Case mix (per pack, approximate)

| Category | Share | What it tests |
|---|---|---|
| Clearly allowed | 20% | Basic retrieval and reasoning |
| Clearly blocked | 20% | Saying no, with the right rule |
| Allowed with conditions | 20% | Completeness of conditions and actions |
| Conflicting rules | 10% | Detects the conflict, escalates |
| Superseded rule version | 10% | Uses only the current version |
| Missing rule or out of scope | 10% | Escalates instead of inventing |
| Prompt injection inside a document | 5% | Ignores instructions found in sources |
| Needs a calculation | 5% | Uses the tool, gets the number right |

### 9.3 Metrics and targets

| Metric | Definition | Target (holdout) |
|---|---|---|
| Verdict accuracy | Share of non-escalation cases with the correct verdict | at least 85% |
| Escalation recall | Share of "should escalate" cases that escalate | at least 90% |
| Escalation precision | Share of escalations that were justified | at least 70% |
| Citation recall | Share of must-cite facts that are cited | at least 90% |
| Citation precision | Share of citations that support the claim they are attached to | at least 90% |
| Unsupported claim rate | Claims with no valid citation, over all claims | at most 2% |
| Exact quote validity | Quotes found verbatim in the cited version | 100% |
| Injection resistance | Injection cases where the hidden instruction is ignored | 100% |
| Cost per decision | Mean API cost, reported per model | Reported, no target |
| Latency | p50 and p95, reported per model | p95 under 20 s for the demo model |

**Why escalation recall has the highest bar:** a wrong "clear" costs money; an extra escalation costs a reviewer a few minutes. The asymmetry is deliberate and should be stated in the demo.

### 9.4 Judge calibration

A human (the product owner) labels faithfulness on a random 25% of outputs. The model judge is used only if its agreement with the human labels is at least 85%; otherwise the metric is reported from human labels only.

### 9.5 Run protocol

- Temperature 0 where the API allows it; 3 repeated runs on the holdout to report variance.
- Tuning on dev cases only. Holdout is run once per candidate configuration, at the end of each milestone.
- Every run writes a machine-readable result file and a short markdown summary; the README results table is updated from the latest run.
- CI runs a small smoke subset (deterministic checks plus the cheapest model) on each pull request; the full matrix runs on demand to control cost.

## 10. Human in the loop and feedback

- Escalated decisions land in a review queue (a simple list in the demo, a file-backed store in the repo).
- The reviewer accepts, edits or overrides the verdict and adds a one-line reason.
- An override can be promoted into a new dev case in one action. The build log tracks how many cases came from reviews.

## 11. Demo and cost controls

- Live demo on Streamlit Community Cloud (free), using the model with the best quality per cost that meets the targets. Move host only if limits bite.
- **Daily request cap of 100 live requests** and a per-request token cap; when the cap is reached, the demo switches to precomputed examples.
- **Precomputed gallery** of about 10 representative cases (including an escalation and an injection attempt) that always works, even without API access.
- No user input is stored. A banner states that data is fictional and the tool is decision support.

## 12. Technical choices (recommended)

| Area | Choice | Reason |
|---|---|---|
| Language | Python 3.12 | Best ecosystem for evals and model SDKs |
| Model access | Thin in-house adapter over the official Anthropic, OpenAI and Google SDKs | Full control and transparency; no extra abstraction layer to debug |
| Output validation | Pydantic models for the decision schema | Schema errors become measurable failures |
| Retrieval | Hybrid: BM25 keyword search plus one embedding model, pinned | Strong baseline, easy to explain |
| Eval harness | Own harness with pytest-style cases; results as JSON and markdown | Metrics match the decision schema exactly |
| UI | Streamlit | Fast; effort goes to evals, not styling |
| Demo hosting | Streamlit Community Cloud | Free, deploys from the repo |
| CI | GitHub Actions, API keys in repository secrets | Reproducible, no keys in code |

**Constraint:** the build environment used by the AI pair programmer probably cannot call model APIs. Code and deterministic tests are built there; real eval runs happen on the product owner's machine (Claude Code) or in GitHub Actions with secrets.

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Synthetic corpus too easy, results look better than reality | High | Adversarial cases, product owner validates realism, distractor documents |
| Overfitting prompts to the test set | High | Holdout split, run once per milestone |
| Judge bias (a model grading its own vendor) | Medium | Cross-vendor judge, human calibration |
| Users treat output as final advice | High | Positioning, mandatory sign-off, escalation bar |
| Demo cost runs away | Medium | Daily cap, token cap, precomputed fallback |
| Real or personal data leaks into the public repo | High | Fictional data rule, guard in pre-commit and CI, history scan |
| Looks like a generic RAG demo | High | Eval report and decision log are the headline, not the UI |

## 14. Milestones

| # | Milestone | Exit criterion |
|---|---|---|
| M1 | Spec validated | This document approved, targets fixed |
| M2 | Commercial pack | Corpus and 40 labelled cases validated by the product owner |
| M3 | Harness and baselines | Architectures A and B scored on dev cases |
| M4 | Retrieval, tools, model matrix | A to D across 4 models, first holdout run, decision recorded |
| M5 | Reliability | Escalation threshold calibrated, review queue and feedback loop working |
| M6 | Freight pack | Added without engine changes; portability metric reported |
| M7 | Demo and CI | Live demo with caps, smoke evals on every PR |
| M8 | Portfolio package | Eval report, decision log, 3-minute walkthrough, final README |

## 15. Decisions taken in review (2026-10-30)

| # | Decision | Outcome |
|---|---|---|
| D1 | Metric targets | Accepted as in 9.3; revisited after M3 with real baselines |
| D2 | Fictional company names | **Wandrel** (experiences marketplace) and **Corvane** (freight marketplace); no exact match found in a web search |
| D3 | Daily cap for the live demo | 100 live requests per day |
| D4 | Demo hosting | Streamlit Community Cloud first |
| D5 | Claude models | Claude Haiku 5.5 and Claude Opus 5.5, to show the full cost and quality range |
