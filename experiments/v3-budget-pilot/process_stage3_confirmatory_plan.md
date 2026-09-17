# Stage 3: Visible-progress allocation confirmatory experiment

> Status: Planning; do not execute API calls from this document.
>
> Purpose: an independent, held-out confirmation of the **visible-only**
> allocation rule identified after Stage 2P.  This is not a search for a new
> confidence prompt or a post-hoc re-optimisation of the controller.

## 1. Why Stage 3 is needed

Stage 2P was an interventional pilot: all questions received a low-budget
prefix and a contextual continuation, making it possible to replay allocation
policies from the common action bank.  It found a positive Process-only versus
count-matched random difference in both models.  However, the original
Process-only rule continued both unfinished states and its realised token cost
was higher than count-matched random (about 8--14%).  It therefore did **not**
pass its pre-registered actual-cost-parity success condition.

The useful, but post-hoc, diagnostic was more specific:

| Stage 2P prefix state | DeepSeek continuation outcome | GPT continuation outcome | Interpretation |
|---|---:|---:|---|
| `complete` | no positive gains | no positive gains | stop |
| `visible_unfinished` | 4/5 beneficial | 9/11 beneficial | candidate continuation state |
| `empty_unfinished` | no cases | 6 unresolved / no benefit | candidate stop state |

Stage 3 tests this refined rule on questions that were never used to choose
it.  Its central question is:

> With the same **expected realised continuation-token cost**, does an
> observable visible-progress rule improve final accuracy over uninformed
> random allocation on new questions?

This is a causal policy comparison.  The confidence audit remains a
descriptive mechanism/limitation analysis and is not used by the Stage 3
controller.

## 2. Hypothesis and frozen controller

### 2.1 Primary hypothesis

For each model, let the policy observe the low-budget prefix output.  A
**Visible-progress policy** that continues only `visible_unfinished` prefixes
will have higher final accuracy than a no-signal random allocation with the
same expected realised continuation-token expenditure.

### 2.2 Frozen policy

The rule is fixed before the Stage 3 manifest is prepared and before any
Stage 3 model outcome is examined.

| Prefix state | Observable definition | Stage 3 action |
|---|---|---|
| `complete` | A parseable final answer is present in visible `content` | stop; retain prefix answer |
| `visible_unfinished` | No parseable final answer, but visible `content` is non-empty | contextual continuation |
| `empty_unfinished` | No parseable final answer and visible `content` is empty | stop; mark prefix result unresolved if it has no answer |

Important boundaries:

- `thinking` is recorded for auditing but is never used to classify a state.
- The brace-aware answer parser already adopted by the project is frozen for
  this experiment.
- No confidence score, question difficulty, answer agreement, or continuation
  result may alter the policy.
- If a selected continuation has no parseable final answer, retain a parseable
  prefix answer when available; otherwise score it incorrect (`unresolved`).

## 3. Data and collection design

### 3.1 New held-out question manifest

- Dataset: `HuggingFaceH4/MATH-500:test`.
- Formal sample: 60 new Level-3/Level-4 questions, stratified 30/30.
- Smoke sample: 4 additional new Level-3/Level-4 questions, stratified 2/2.
- Models: `GPT-OSS-120B` and `DeepSeek-V4-Flash-158B`.
- Temperature: 0.0; one recorded action pair per model-question unit.
- The future manifest preparer must exclude every question ID present in
  historical `data/` **and** `results/` JSON files, including all Stage 2P,
  Phase 3, Soft, prospective-confidence, Stage 1.x, Gate, and smoke records.
  It must write the ordered ID SHA-256 and the number of excluded IDs.

The 4 smoke questions only validate payload, state parsing, contextual history,
token accounting, checkpoint/retry, and schema.  Their outcomes never enter the
formal analysis and cannot change the frozen rule.

### 3.2 Action bank

For every formal model-question unit, collect both actions, even though a
deployed visible-progress controller would request the second action only when
the prefix is `visible_unfinished`.

| Action | `num_predict` | Prompt | Role |
|---|---:|---|---|
| `prefix` | 512 | concise reasoning, exactly one boxed final answer | determines observable state and low action |
| `continuation` | 512 | original prompt + visible prefix content + “continue; do not restart” | supplies the contextual high action |

This produces a complete counterfactual action bank for all policies:

- Smoke: 4 questions × 2 models × 2 actions = **16 calls**.
- Formal: 60 questions × 2 models × 2 actions = **240 calls**.

Collection of both actions is an evaluation instrument.  It must not be
described as the runtime cost of the deployed controller; deploy-time visible
progress requests a continuation only for selected cases.

### 3.3 Required per-action fields

Each record must retain: schema/prompt versions, model ID, question ID, action,
visible `content`, `thinking`, `done_reason`, parser output, correctness,
process state (for prefix only), prompt/completion/total tokens, elapsed time,
API error, and request metadata (`think`, temperature, `num_predict`).

`total_tokens` is the billed/request-level total used in cost calculations.  A
selected continuation adds its entire continuation-request total token count;
the prefix request is incurred for every question under every policy.

## 4. Policy evaluation from the common action bank

For question \(i\), model \(m\):

- \(y_i^L\): correctness after stopping at prefix.
- \(y_i^H\): correctness after contextual continuation with the fallback rule.
- \(g_i = y_i^H - y_i^L\): realised continuation gain.
- \(c_i^L\): prefix request total tokens.
- \(c_i^H\): continuation request total tokens.
- \(V_i = 1\) iff the prefix state is `visible_unfinished`.

The frozen visible-progress policy selects \(S_V = \{i: V_i=1\}\).  Its mean
accuracy and mean realised total tokens are:

\[
A_V = \frac{1}{N}\sum_i [V_i y_i^H + (1-V_i)y_i^L],
\]

\[
T_V = \frac{1}{N}\sum_i [c_i^L + V_i c_i^H].
\]

### 4.1 Primary comparator: cost-calibrated random expectation

The primary random comparator receives no process, confidence, question, or
outcome signal.  It independently selects each question with probability

\[
p = \frac{\sum_i V_i c_i^H}{\sum_i c_i^H}.
\]

Thus its **expected realised continuation-token expenditure** equals that of
the visible-progress policy exactly:

\[
E[\sum_i Z_i c_i^H] = p\sum_i c_i^H = \sum_i V_i c_i^H,
\quad Z_i \sim \mathrm{Bernoulli}(p).
\]

Its expected accuracy is evaluated without Monte-Carlo noise:

\[
A_R = \frac{1}{N}\sum_i [y_i^L + p(y_i^H-y_i^L)].
\]

The primary estimand is \(\Delta = A_V - A_R\).

This comparator is deliberately an **evaluation benchmark**, not a deployment
algorithm: its calibration uses realised continuation costs available only in
the fully collected action bank.  It answers the causal efficiency question
fairly, but does not claim an online random policy knows each future request
cost.  The report must state this boundary explicitly.

### 4.2 Secondary, operationally interpretable comparators

| Policy | Selection rule | Purpose |
|---|---|---|
| Fixed Low | never continue | low-cost anchor |
| Fixed Continue | continue every case | high-compute anchor |
| Random count-matched | uniform subset of size \(|S_V|\) | matches continuation count; continuity with Stage 2P |
| Random ledger replay | random order, continue while a pre-set token ledger remains | operational random sensitivity; report overshoot convention |
| Question-only | frozen manifest difficulty ranking, top \(|S_V|\) | simple non-process signal baseline |
| Oracle, count-matched | top \(|S_V|\) realised gains | retrospective count upper bound |
| Oracle, cost-constrained | maximise realised gain under \(\sum c_i^H\leq\sum_{i\in S_V}c_i^H\) | retrospective cost upper bound |

The two oracle policies are upper bounds only; neither is deployable and neither
may be treated as a method result.

For random-ledger replay, the ledger is the visible policy's realised aggregate
continuation cost within the evaluation data.  Randomly permute questions,
execute selected continuations in that order, and stop selecting after the
running cost reaches/exceeds the ledger; the final request may overshoot because
its future cost is unknowable.  Report its expected accuracy and the full
realised-cost distribution across at least 10,000 deterministic random seeds.
It is secondary because its ledger is still an evaluation-matched reference.

## 5. Inference, decision rules, and guardrails

### 5.1 Primary inference

- Resampling unit: `question_id` cluster.  When a question is sampled, retain
  both model observations.
- 10,000 paired question-clustered bootstrap replicates; percentile 95% CI.
- Recompute \(V_i\), \(p\), both policies, and \(\Delta\) in every bootstrap
  replicate, including duplicate sampled question occurrences.
- Report pooled result and model-specific diagnostics.  Do not pool confidence
  scores or use confidence in any policy.

### 5.2 Confirmatory success criteria

Stage 3 supports the method only if all conditions hold:

1. The pooled primary CI for \(A_V-A_R\) has lower bound above zero.
2. Both model-specific primary point estimates are positive.
3. Primary expected continuation-token matching is exact up to numeric rounding;
   report the equality check for each model and bootstrap implementation test.
4. The held-out manifest, raw action bank, parser audit, and no-error/no-duplicate
   validation all pass.
5. Each model has at least five `visible_unfinished` formal cases.  If not, that
   model is reported as **insufficient visible-state support**, not silently
   replaced with a broader unfinished rule.

Failure of any criterion is reported as a No-Go or inconclusive result; no
post-hoc change to include `empty_unfinished`, confidence, or a different
budget is permitted within Stage 3.

### 5.3 Planned descriptive checks

- State counts and state-specific continuation gains/losses.
- Prefix and continuation parse/error rates, with a parser audit sample.
- Actual token distributions for all policies, not only means.
- Accuracy--cost frontier with explicit distinction between actual policy points
  and retrospective benchmarks.
- Pre-specified robustness: count-matched random and ledger-replay random.
- Separate model results before any pooled narrative.

No p-value wording for bootstrap tail proportions.  The CI and effect size are
the primary evidence.

## 6. Implementation plan (after plan review)

The following code does **not** exist yet and should be written only after this
plan is approved.

1. `prepare_process_stage3_questions.py`
   - Builds and validates the new 4/60 manifest.
   - Scans all prior question IDs in both `data/` and `results/`.
   - Is deterministic from a frozen seed, emits ID hash and exclusion audit.
2. `run_process_stage3.py`
   - Reuses the Stage 2P safe checkpoint/retry pattern.
   - Supports `--stage smoke|formal`, dry-run by default, and requires
     `--execute` for API calls.
   - Rejects partial/formal model filters and non-manifest question lists.
3. `analyze_process_stage3.py`
   - Validates exactly 240 successful formal records before analysis.
   - Implements the equations above, including duplicate-safe paired bootstrap,
     cost-constrained oracle, and deterministic random-ledger sensitivity.
   - Produces machine-readable metrics, a human report, a parser/data audit,
     and an accuracy--cost figure.
4. Tests
   - Unit-test state classification/fallback, exact expected-cost identity,
     duplicate-aware bootstrap, random-seed determinism, oracle budget
     feasibility, manifest leakage rejection, retry/checkpoint behaviour, and
     raw-record schema validation.

## 7. Planned outputs

```text
data/process_stage3_questions.json
results/process_stage3_smoke.json
results/process_stage3_formal_raw.json
results/process_stage3_manifest_audit.md
results/process_stage3_parser_audit.json
results/process_stage3_analysis.json
results/process_stage3_report.md
results/process_stage3_accuracy_cost.png
```

## 8. Execution sequence

1. Review and freeze this plan.
2. Implement preparer, runner, analysis, and tests; review/push code only.
3. Run local tests and a no-API dry run.
4. Run the 16-call smoke test; inspect its raw records and audit.
5. If transport and schema pass, run the 240-call formal collection unchanged.
6. Run the frozen analysis and report all success criteria, including any No-Go.
7. Only then update the manuscript/main research narrative.
