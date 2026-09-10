# Research Progress Overview (2026-09-10)

> Design rationale, findings, and lessons from each experiment phase
> V1 → V2 → Deep Research → V3 Phase 2 → B+C → Phase 3 → IDS → PM Analysis

---

## I. Motivation and Research Questions

### 1.1 Where This Started

Chen et al. (IEEE IRI 2026) proposed the LCAE framework, using the IRT Rasch Model to place model ability and item difficulty on the same scale—σ(θ_m − β_i). Their three key findings were: capability does not equal calibration quality, providing difficulty signals (IDS) improves calibration most effectively, and improving calibration does not hurt answering ability.

Most importantly, they noted a correlation between reliability and inference cost, but did not validate it. That is my entry point.

### 1.2 My Research Question

The senior student asked: *Does the model know whether it knows?* I ask one step further: **If a model knows whether it knows, can it also know how long it needs to think? Can calibration quality predict token allocation efficiency?**

### 1.3 Core Hypothesis

A well-calibrated model does not necessarily use fewer total tokens, but it allocates them more rationally—fewer tokens for easy/high-confidence questions, more for difficult ones. Under resource constraints, accuracy degrades less.

---

## II. V1 Pilot — Validating the Tool

### Why This Design

At the July 4 meeting, my advisor suggested using Process Mining (PM) to analyze reasoning traces. But I had never used pm4py before, and I was not sure whether it would work on LLM Chain-of-Thought text—CoT is not a standard event log with clear step boundaries.

So V1 had a single goal: **use the simplest possible questions at minimal cost to confirm the PM pipeline works.**

I chose 20 GSM8K grade-school math questions, 5 models, 8 activity types. No confidence data—the goal was to validate the segmentation→labeling→analysis pipeline, not to test any hypothesis.

### What We Found

✅ PM can distinguish reasoning styles, and three styles are stable across V1 and V2:
- **Intuitive (DeepSeek):** short traces, high answer ratio, less deliberation
- **Systematic (GPT-120B):** balanced calculate+reason
- **Struggling (GPT-20B):** long traces, high reason ratio

❌ Clear limitations: questions too easy (95-100% acc, zero variance). No confidence data, cannot validate calibration.

### Lesson Learned

PM works, but we need harder questions and must collect confidence.

---

## III. V2 — Adding Calibration Metrics

### Why This Design

V1's limitations directly drove V2's changes:
- Questions: 20 GSM8K → 100 (MMLU STEM 50 + ARC 50), to create accuracy variance
- Confidence: added multi-turn self-assessment (0-100%)
- Activities: 8 → 9 types (added evaluate)
- PM: expanded from Petri net to entropy + JSD

### The Confidence Prompt Lesson

This was an important methodology finding. The initial version used a context-free prompt:

> User: You answered D. How confident are you?

DeepSeek returned 2%, GLM-5.2 returned 27%. Completely meaningless—the model had no context.

Switching to multi-turn:

> User: [question]
> Assistant: [full reasoning]
> User: Based on your reasoning above, how confident are you? Give ONLY a number 0-100.

Produced DeepSeek 99%, GLM-5.2 99%. **Context-free confidence prompts produce completely distorted data.**

### V2 Rebuild — Data Flip

After execution, several bugs were discovered:
- Conformance read a nonexistent field → alignment all 0
- Levenshtein sampled (A,B) and (B,A) separately → asymmetric matrix
- JSD stored distance as divergence
- Confidence only passed response without thinking, truncated to 500 chars

The July 24 rebuild fixed everything. After the fix, GPT-20B jumped from 56% to 98%, and the previous "confidence gap inversely correlates with accuracy" finding was overturned entirely.

### Lesson Learned

V2's value as a calibration analysis dropped significantly (accuracy variance disappeared). But the PM pipeline was validated, and we exposed prompt sensitivity, confidence scarcity, and Petri net flower-model problems that later experiments could avoid.

---

## IV. July 28 Deep Research — Literature Survey

### Why This Was Necessary

After V2's data was overturned, I realized I could not simply proceed with the original plan. I needed a systematic competitor analysis to confirm the direction still had novelty.

I spent a week writing a 1,612-line survey.

### Most Important Finding

The field had heated up rapidly in 2025-2026. Several basic ideas were already taken:

| Competitor | What They Did | Impact on Me |
|-----------|--------------|--------------|
| Think Just Enough (EACL 2026) | Self-assessed confidence as stopping signal | Cannot claim "first to use confidence for reasoning control" |
| SelfBudgeter (ACL 2026) | Model predicts token budget + RL | Need to emphasize training-free |
| Capability Calibration (arXiv 2026) | Calibration→best-of-k allocation | Need to shift to reasoning length |
| Sonata (ICLR 2026) | Hidden-state adapter for budget | Need to emphasize black-box |
| Berti et al. (TechRxiv 2025) | PM on LLM reasoning traces | PM downgraded to diagnosis |

### Repositioning

I can no longer claim "first to use confidence to save tokens" or "first to apply PM to LLM reasoning." The new positioning:

> **Can psychometrically calibrated (IRT/LCAE) self-assessment predict per-question reasoning token requirements?**

Differentiators:
- IRT calibration, not raw confidence
- Training-free, unlike SelfBudgeter
- Black-box compatible, unlike Sonata
- Reasoning-length allocation, unlike Capability Calibration
- IDS intervention for causal validation
- PM for mechanism diagnosis

---

## V. V3 Phase 2 — Budget Sensitivity Pilot

### Why This Design

After the literature survey, I needed to confirm the most basic assumption: **does a measurable token requirement actually exist?** If all questions are unsolvable at low budgets and solvable at high budgets, there is no budget sensitivity to study.

Phase 2 had a concrete goal: 2 extreme models (GPT-20B poorly calibrated vs DeepSeek well-calibrated) × 30 questions × 4 budgets (128/256/512/1024) to confirm difficulty and budget sensitivity exist.

MATH-500 was chosen because it is a standard benchmark (used by Think Just Enough, SelfBudgeter). Only Levels 3-5 since Levels 1-2 are too easy.

Budgets were based on V2 natural token usage (~600-900 average): 128 for extreme compression, 256 significant, 512 moderate, 1024 near-unlimited.

### Results

| Budget | GPT-20B | DeepSeek | Gap |
|--------|---------|----------|-----|
| 128 | 0.0% | 0.0% | — |
| **256** | 3.3% | **15.0%** | **5×** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

### Decision

✅ Budget sensitivity exists, MATH-500 difficulty is appropriate.
✅ DeepSeek wins at all budgets, calibration advantage most visible at low tokens.
⚠️ Only 2 models → cannot distinguish calibration vs ability confound.
⚠️ No confidence collection → cannot validate causal chain.

**Decision: proceed to Phase 3.**

---

## VI. B + C — Confidence Test + Activity Labeling

### B: Why Test Confidence First?

Phase 3 would add confidence collection, but the confidence prompt had already failed once (context-free distortion). I ran a small test first: 2 models × 10 questions × 2 budgets to confirm the mechanism works.

**Result:** GPT-20B 97 correct / 70 wrong (distinguishable ✅), DeepSeek 100 correct / 99 wrong (overconfident). Mechanism is fine for Phase 3.

### C: Why Export Activity Labels?

V1/V2 activity labeling is rule-based (keyword matching). My advisor mentioned reliability concerns. I exported 100 text samples for future human annotation.

---

## VII. V3 Phase 3 — Decisive Experiment

### Why This Design

Phase 2 confirmed budget sensitivity but left the "calibration vs ability" confound unresolved. Phase 3 aimed to answer it with 4 models.

Added GPT-120B (117B, moderate calibration) and GLM-5.2 (756B, unknown calibration):
- If GLM-5.2 (largest) performs best at low budgets → model size explains everything
- If GPT-120B (best calibrated) performs best → calibration is independent
- If DeepSeek still wins → reasoning style is the key

From Phase 2 experience:
- Removed 128 (0% everywhere, no information)
- Increased replicates to 3
- Only L3+L4 from MATH-500 (removed too-difficult L5)
- Added IRT + LCAE computation

Total: 4 × 60 × 3 × 3 × 2 = **4,320 API calls**.

### Key Findings

#### Finding 1: Ability θ and Calibration LCAE Are Independent Dimensions

| Model | Acc@1024 | Ability θ | LCAE |
|-------|---------|----------|------|
| DeepSeek | **66.1% 🏆** | **+0.65 🏆** | 0.303 |
| GPT-120B | 50.6% | +0.00 | **0.247 🏆** |
| GPT-20B | 48.3% | −0.09 | 0.341 |
| GLM-5.2 | 36.7% | −0.57 | 0.438 |

DeepSeek is strongest in ability but not best calibrated. GPT-120B is average in ability but best calibrated. **This confirms the senior student's finding: capability ≠ calibration.**

#### Finding 2: Brier vs LCAE Give Different Rankings

| Model | Brier Rank | LCAE Rank |
|-------|-----------|----------|
| DeepSeek | **1** | 2 |
| GPT-120B | 2 | **1** |

Which calibration metric you choose changes which model you think is most reliable. **LCAE captures information that Brier misses—the interaction between item difficulty and model ability.**

#### Finding 3: Confidence Gap as a Proxy Metric

GPT-120B (+25.5) > DeepSeek (+15.5) > GPT-20B (+7.3) > GLM-5.2 (+3.4). Consistent with LCAE ranking, negligible computation cost.

#### Finding 4: GLM-5.2 Is Largest but Worst

756B MoE GLM-5.2 has the lowest ability (θ=−0.57), worst calibration (LCAE=0.438), and 96% confidence when wrong. Model size does not equal math reasoning capability.

### At the Time

When Phase 3 results came in, I expected "better calibrated → better low-budget performance." The data said: DeepSeek wins at low budgets not because of calibration, but because of reasoning efficiency. My core hypothesis was only half right.

---

## VIII. Kimiko's Concerns and the IDS Intervention

### Kimiko's Diagnosis

My advisor's agent Kimiko reviewed my work and raised three concerns:

1. **Phase 3 does not support the core claim**: Best performer at low budget (DeepSeek) ≠ best calibrated (GPT-120B). The data shows "high ability → good performance," not "good calibration → good performance."
2. **IDS is the strongest differentiator but hasn't been run**: Without IDS, the paper can only say "we observed a phenomenon," not "we can manipulate it."
3. **Competitor R³-Bench (arXiv Aug 2026)** overlaps with budget sensitivity.

### IDS Experiment Design

IDS is the senior student's core method—adding one sentence to the prompt: "This problem is rated difficult/moderate/easy..." Difficulty levels come from Phase 3 IRT β values (5-level scale).

Design: 2 models (GPT-120B best-calibrated × DeepSeek highest-ability) × 2 conditions (QOQ no-IDS × IDS) × 2 budgets × 3 reps × 30 questions = **1,440 calls**.

Both QOQ and IDS were run fresh (not using Phase 3 as baseline) because intervention requires a clean paired comparison.

### IDS Results

| Effect | Result |
|--------|--------|
| Calibration improved? | ✅ GPT-120B Brier ↓, confidence_wrong ↓ |
| Accuracy improved? | ❌ No significant change |
| Causal chain? | ❌ Calibration improvement did not translate to accuracy |

---

## IX. PM Analysis — Why IDS Had No Effect

### Kimiko's Key Question

Kimiko asked a fundamental question: **At low budgets, is the model failing because it "does not know when to stop" (calibration problem) or because it "cannot solve it at all" (ability problem)?**

### PM Analysis Findings

Running PM analysis on Phase 3 data:

| Model | @256 Steps | @1024 Steps | Ratio | Answer@256 |
|-------|-----------|------------|-------|-----------|
| GPT-20B | 1.1 | 11.0 | 10% | 0.0% |
| GPT-120B | 1.8 | 12.7 | 14% | 0.0% |
| DeepSeek | **2.3** | 6.6 | **35%** | 0.0% |
| GLM-5.2 | 0.1 | 7.8 | 1% | 0.0% |

At 256 tokens, no model can produce an "answer" step. It is not an allocation problem—the output is **forcibly truncated by `num_predict`**.

### The Fundamental Design Issue

`num_predict` truncation removes the model's token allocation agency entirely. The model does not know there is a budget limit—it simply gets cut off mid-reasoning.

**This explains why IDS did not improve accuracy:** IDS can improve calibration, but the model has no opportunity to adjust its reasoning length. It has no agency.

This also explains DeepSeek's advantage: not better calibration, but fewer tokens per step, so it loses less when truncated.

---

## X. Current Status and Choices

### Kimiko's Conclusion

The experiment has a fundamental validity gap. `num_predict` truncation is not a minor detail to "honestly acknowledge" in the paper—it affects the validity of the entire Phase 3. The experiment measured "residual accuracy after forced truncation," not "token allocation efficiency."

### Two Options

| Option | Description | Pros | Cons |
|--------|------------|------|------|
| **A: Keep data** | RQ becomes "reasoning robustness under hard budget constraints" | Data exists, PM analysis supports | Different story than originally planned |
| **B: Redo experiments** | Prompt the budget limit, give model agency | Matches original RQ | Must redo everything |

Kimiko recommends Option A, but with a specific framing: describe the `num_predict` truncation in methodology as a deliberate choice to "control for prompt compliance variance and focus on reasoning content robustness." This turns the truncation from a "design flaw" into a "methodological choice."

### Timeline

IEEE Big Data deadline is not October, so time is not a constraint.

### Next Step

Meeting with my advisor tomorrow (2026-09-11) to discuss findings and decide direction.

---

## XI. Key Files

| File | Path |
|------|------|
| Phase 3 raw | `experiments/v3-budget-pilot/results/phase3_raw.json` |
| Budget sensitivity | `experiments/v3-budget-pilot/results/budget_sensitivity_phase3.json` |
| Calibration | `experiments/v3-budget-pilot/results/calibration_phase3.json` |
| IRT + LCAE | `experiments/v3-budget-pilot/results/irt_phase3.json` |
| IDS raw | `experiments/v3-budget-pilot/results/ids_raw.json` |
| PM analysis script | `experiments/v3-budget-pilot/run_pm_analysis_phase3.py` |
| PM summary | `experiments/v3-budget-pilot/pm_analysis_summary.md` |
| IDS design doc | `experiments/v3-budget-pilot/ids_experiment_design.md` |
| Literature survey | `docs/zh-TW/deep-research-*.md` |
| Research narrative | `docs/zh-TW/research-narrative-2026-09-11.md` |