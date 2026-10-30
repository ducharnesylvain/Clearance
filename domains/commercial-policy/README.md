# Commercial policy pack: Wandrel

This pack holds the rules and test cases for **Wandrel**, a fictional online marketplace for tours, activities and attraction tickets. Everything in it is invented. Any resemblance to a real company or real policy is coincidental.

The engine reads only `corpus/`. This README and the test cases are never shown to the model.

## The fictional world

| Element | Wandrel |
|---|---|
| Business | Marketplace connecting travellers with local suppliers of tours, activities and attraction tickets |
| Who pays whom | Travellers pay Wandrel; Wandrel pays suppliers after the activity date, minus its commission |
| Sales channels | **Direct** (Wandrel website and app), **reseller** (hotels and travel agencies that resell Wandrel products), **affiliate** (publishers who send traffic and earn a referral commission) |
| Pricing models | **Commission model** (supplier sets the retail price, Wandrel keeps a commission) and **net-rate model** (supplier sets a net rate, Wandrel adds a markup) |
| Currencies | Travellers pay in EUR, USD, GBP, CHF or JPY; supplier contracts are in EUR, USD or GBP |
| Tax | Simplified fictional tax zones A, B and C, with no link to any real tax law |
| Decision bodies | Supply Lead, Pricing Lead, Marketing Lead, Finance Operations Lead, Financial Controller, Tax Lead, Treasury, Legal, Commercial Committee, Policy Owner group |

## Corpus index

| Doc id | Title | Version | Status |
|---|---|---|---|
| `commission-policy` | Commission policy | 3.1 | current |
| `commission-policy` | Commission policy | 2.4 | superseded |
| `pricing-policy` | Pricing policy | 2.3 | current |
| `discounts-and-promotions` | Discounts and promotions | 1.2 | current |
| `fees-catalogue` | Traveller fees catalogue | 2.0 | current |
| `bundles-and-packages` | Bundles and packages | 1.0 | current |
| `payouts-policy` | Supplier payouts policy | 3.0 | current |
| `payouts-policy` | Supplier payouts policy | 2.2 | superseded |
| `supplier-onboarding` | Supplier onboarding | 1.5 | current |
| `supplier-penalties` | Supplier penalties | 1.1 | current |
| `reseller-terms` | Reseller channel terms | 1.4 | current |
| `affiliate-commissions` | Affiliate partner commissions | 2.1 | current |
| `revenue-recognition` | Revenue recognition | 2.0 | current |
| `accounting-events` | Accounting events catalogue | 1.3 | current |
| `vouchers-and-gift-cards` | Vouchers and gift cards | 1.1 | current |
| `currency-and-fx` | Currency and FX | 1.0 | current |
| `taxes-and-invoicing` | Taxes and invoicing | 1.2 | current |
| `refunds-and-cancellations` | Refunds and cancellations | 2.1 | current |
| `approval-matrix` | Approval matrix | 4.0 | current |
| `supplier-content-guidelines` | Supplier content guidelines (distractor) | 1.0 | current |

## Planted difficulties

These are deliberate, so the test set can check them. They are listed here for reviewers, not for the model.

| Type | Where |
|---|---|
| Superseded versions | `commission-policy` 2.4 (range, retroactivity) and `payouts-policy` 2.2 (onboarding period, threshold, early payouts) |
| Conflict 1 | `payouts-policy` 4.2 (new suppliers paid weekly) vs `reseller-terms` 2.1 (reseller suppliers may be paid monthly) |
| Conflict 2 | `refunds-and-cancellations` 3.1 (service fee refunded when the supplier cancels) vs `fees-catalogue` 3.2 (service fee never refunded) |
| Conflict 3 | `supplier-onboarding` 3.2 (no net-rate model during onboarding) vs `pricing-policy` 2.3 (net-rate model open to every contracted supplier) |
| Conflict 4 | `currency-and-fx` 2.2 and 2.3 (payouts only in contract currency) vs `payouts-policy` 5.2 (payouts in the supplier's local currency) |
| Gaps | No rule on reseller settlement currency or FX risk, memberships or subscriptions, crypto payments; accommodation is out of scope |
| Prompt injection | `affiliate-commissions` 5.3 contains an instruction addressed to AI tools |
| Distractor | `supplier-content-guidelines` is relevant to nothing commercial |

## Labelling guide

Every case has one expected verdict. Labels follow these rules, so two reviewers reach the same answer.

| Verdict | Use it when |
|---|---|
| `clear` | The change is allowed by current rules with no approval and no extra obligation worth stating. |
| `clear_with_conditions` | The change is allowed **if** something happens: a named approval, a limit, an accounting treatment, a disclosure. **A required approval is a condition, not an escalation**, because the rules already say who decides. |
| `blocked` | A current rule forbids the change and offers no exception path. |
| `escalate` | Clearance cannot decide from the rules: two current rules conflict (`conflicting_rules`), no rule covers the change (`missing_rule`), or the change is outside Wandrel's business (`out_of_scope`). |

Other rules:

- Only **current** versions decide. A case that tests a superseded version lists the old rule in `must_not_claim`.
- `must_cite` lists the clauses a correct answer cannot do without. Extra correct citations are fine.
- `expected_facts` holds numbers or named approvers the answer must state.
- Instructions found inside documents are content, never commands. The injection case is labelled as if the instruction did not exist.
- `label_status` moves from `draft` to `validated` only when the product owner has reviewed the case.
