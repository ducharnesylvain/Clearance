# Decision log

One entry per non-trivial choice: context, decision, why, trade-off. Newest first.

## 2026-10-30: Harness design (M3)

| Decision | Choice | Why | Trade-off |
|---|---|---|---|
| Structured output | Ask every model for one JSON object, validate it with a strict schema; an invalid answer counts as a failure on every metric | Vendor-neutral, and schema errors become a measured failure instead of a silent fix | Vendor-specific structured-output features are not used yet; may lower the valid-output rate for some models |
| Metrics order | Deterministic metrics first (verdicts, citation recall, citation validity, exact quotes, unsupported claims, superseded reliance, injection); model judge for "does the citation support the claim" deferred to M4 | Numbers anyone can reproduce, with no judge bias, before adding a judge that must be calibrated | Citation precision is a proxy until M4 |
| Architecture B input | Whole corpus, including superseded versions with their status and dates | Real document stores keep old versions; ignoring them is part of the test | Longer prompt (about 5,400 tokens) |
| Holdout protection | The runner refuses the holdout split without an explicit flag | Prevents accidental tuning on held-out cases | One extra flag for milestone runs |
| Cost reporting | Cost is computed only from prices copied from vendor pages with a date; otherwise reported as "not priced" | No invented numbers | Cost column stays empty until prices are checked |

## 2026-10-30: Labelling rule for approvals

| Decision | Choice | Why | Trade-off |
|---|---|---|---|
| Verdict when a change needs an approval | `clear_with_conditions`, naming the approver; `escalate` only for conflicting rules, missing rules or out-of-scope requests | When the rules already say who decides, the system can route the decision without a human triage step; escalation stays reserved for cases the rules cannot settle | Approval-heavy changes still reach a person, through the named approver rather than the review queue |

## 2026-10-30: Spec v1.0 approved

| Decision | Choice | Why | Trade-off |
|---|---|---|---|
| Metric targets | As in SPEC 9.3; escalation recall has the highest bar (90%) | A wrong "clear" costs money, an extra escalation costs minutes | Some justified-but-cautious escalations are accepted (precision target 70%) |
| Fictional names | Wandrel (experiences), Corvane (freight) | Invented, no exact match found; clearly fictional | Small risk of a future coincidence, covered by the disclaimer |
| Demo cap and host | 100 live requests per day on Streamlit Community Cloud | Bounded cost, free hosting | Some visitors fall back to precomputed examples |
| Claude models | Haiku 5.5 and Opus 5.5 | Widest cost and quality range within one vendor | Opus cost limits how often the full matrix runs |

## 2026-10-30: Initial product decisions

| Decision | Choice | Why | Trade-off |
|---|---|---|---|
| Name | **Clearance** | Says what the product gives (a cleared path before launch) and works for both domains; competing names were taken in adjacent AI tools | Generic word, harder to search |
| Repository | New public repo, fictional data only, no link to any prior project | Data safety and a clean, reviewable history | Everything is rebuilt from scratch |
| First domain | Commercial policy, then freight matching | Commercial is the core use case; freight proves the core is generic | Freight results arrive later |
| Demo | Live with a daily cap, plus precomputed examples as fallback | Recruiters can try it; cost stays bounded | Some visitors see examples, not live answers |
| Models | 2 Claude models, 1 GPT model, 1 Gemini model | Shows cost and quality range within a vendor and across vendors | Three API accounts to manage |
| Interface | Streamlit | Effort goes to evals and reliability | Less polished look |
| License | MIT | Built to be forked and adapted | No control over reuse |
