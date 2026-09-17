# Stage 2P: Process-only formal interventional pilot plan

> Date: 2026-09-17
> Status: Planning; pre-execution

## 1. Motivation

Stage 1.5 confirmed observable process state (complete / visible_unfinished / empty_unfinished) is the strongest offline predictor of marginal continuation value (PR-AUC 0.795). Stage 1.6 and Stage 2 Gate 1/1R2 ruled out verbal confidence and short-branch agreement as cost-effective allocation signals.

Stage 2P moves from offline prediction to **real intervention**: does a process-only allocation policy achieve higher final accuracy than uniform random matched-allocation at the same continuation quota \(K^*\), under contextual continuation?

## 2. Design

### 2.1 Questions

- 60 held-out MATH-500 questions, already prepared in `data/process_stage2_questions.json` (split=formal)
- Repeat count: 1 replicate per question (deterministic; temperature 0.0)
- Model: GPT-OSS-120B and DeepSeek-V4-Flash-158B
- Total units: 60 × 2 = 120

### 2.2 Per-unit calls

| Action | Budget | Temp | Purpose |
|--------|------:|:----:|---------|
| `prefix` | 512 | 0.0 | Observable state + low-budget outcome |
| `continuation` | 512 | 0.0 | High-budget outcome under contextual continuation |

Call count: 120 × 2 = 240 calls total.

### 2.3 Process state definition (pre-registered)

Deterministic, based solely on prefix output:

| State | Definition |
|-------|------------|
| `complete` | Prefix has a parseable boxed answer |
| `visible_unfinished` | No parseable answer, but non-empty observable content |
| `empty_unfinished` | No parseable answer and observable content is empty |

The `thinking` field is ignored for state classification; only visible `content` is used.

### 2.4 Continuation quota \(K^*\)

- \(K^*\) = number of unfinished prefix cases in the 60 formal questions for a given model, computed *before* examining any correctness outcomes.
- Unfinished = `visible_unfinished` + `empty_unfinished`.
- This is determined once, from the raw prefix output.

### 2.5 Policy definitions (applied to shared raw data)

| Policy | Rule | Continuations |
|--------|------|---------------|
| **Fixed Low** | Always stop at prefix | 0 |
| **Fixed Continue** | Always use continuation | all 60 |
| **Random matched** | Uniform random with *exactly* \(K^*\) continuations | \(K^*\) |
| **Question-only** | Continue if question level ≥ 4 | depends on level |
| **Process-only** | State rule below | \(K^*\) |
| **Process-only (inverse)** | Reverse of Process-only | \(K^*\) |
| **Oracle** | Continue if prefix is **incorrect**; stop if correct | \(K^*\) |

#### Process-only rule

| State | Action |
|-------|--------|
| `complete` | **stop**, use prefix answer |
| `visible_unfinished` | **continue**, use continuation answer |
| `empty_unfinished` | **continue**, use continuation answer |

Priority for secondary quota curve: `visible_unfinished` > `empty_unfinished` > `complete`.

#### Process-only (inverse)

| State | Action |
|-------|--------|
| `complete` | **continue** |
| `visible_unfinished` | **stop** |
| `empty_unfinished` | **stop** |

This tests whether the *direction* of the process signal is meaningful, not just whether any allocation has an effect.

#### Oracle

Uses same \(K^*\) as Process-only. Select questions with lowest prefix accuracy (i.e., where continuation is most likely to help). If multiple questions are tied, prioritise unfinished states. After selecting \(K^*\) questions, assign continuation to those.

#### Question-only

Trained and frozen on old data (Phase 3 60 questions from any model). The rule: "continue if question level ≥ 4; otherwise stop". This is determined once and never updated from formal 60 outcomes.

### 2.6 Answer selection fallback

When continuation fails to produce a parseable answer:
- If prefix has a parseable answer → **keep the prefix answer**.
- Otherwise → **unresolved** (treated as incorrect).

### 2.7 Primary comparison

```
ΔAccuracy = Process-only accuracy − Random matched accuracy
```

- At the same continuation quota \(K^*\).
- 95% question-clustered bootstrap CI (10,000 replicates).
- Success: CI does not contain zero, both models show non-contradictory direction.

### 2.8 Secondary comparisons

| Comparison | Purpose |
|------------|---------|
| Process-only vs Fixed Low | Does allocation beat always-stopping? |
| Process-only vs Fixed Continue | Does allocation beat always-continuing? |
| Process-only vs Question-only | Does process state beat simple difficulty? |
| Process-only (inverse) vs Process-only | Is the *direction* of progress meaningful? |
| Oracle upper bound | How much gap remains? |
| Process-only vs Random at varying quotas | Quota–accuracy curve (secondary) |
| PR-AUC (offline) | Diagnostic only (not primary success criterion) |

### 2.9 Success criteria

All three must hold:

1. **Primary:** ΔAccuracy CI for Process-only vs Random matched does not contain zero.
2. **Consistency:** Both models show the same direction (positive Δ); or any contradiction has a clear explanation.
3. **Cost parity:** Actual mean total tokens per question for Process-only and Random matched are within ±5% (or Process-only is Pareto-improving: higher accuracy at similar or lower average cost).

## 3. Bootstrapping procedure

- Resampling unit: `question_id` (not call, not model)
- 10,000 bootstrap replicates
- For each replicate: resample 60 questions with replacement, apply all policies, compute per-policy accuracy, compute Δ for each pair
- CI: percentile method (2.5%–97.5%)
- p-value: proportion of 10,000 replicates where Δ ≤ 0
- Reported **separately per model**

## 4. Smoke test (before formal execution)

- 2 Gate 0 questions × 2 models = 4 units
- Collect prefix + continuation = 8 calls
- Verify: payload structure, process state classification, continuation context, answer parsing, cost recording
- Must pass before proceeding to 240 formal calls

## 5. Required outputs

```
results/process_stage2p_smoke.json       — smoke test raw data
results/process_stage2p_raw.json         — 240 action records
results/process_stage2p_analysis.json    — per-model policy metrics
results/process_stage2p_report.md        — human-readable report
results/process_stage2p_figure.png       — accuracy-cost Pareto
```

## 6. Execution order

1. Build `run_process_stage2p.py` + `analyze_process_stage2p.py`
2. Offline tests pass
3. Smoke test: 2 questions × 2 models (8 calls)
4. If smoke test clean → formal 60 questions × 2 models (240 calls)
5. Analyse and report