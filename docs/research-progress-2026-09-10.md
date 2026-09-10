# Research Progress Overview (2026-09-11 Updated)

> Core narrative: We attempted to validate the causal chain "calibration → token allocation efficiency," but the experiment design itself revealed a more fundamental problem—hard constraint and soft constraint budget mechanisms affect model behavior in fundamentally different ways, a distinction rarely discussed in the literature.
> V1 → V2 → Deep Research → V3 Phase 2 → B+C → Phase 3 → IDS → PM Analysis

---

## I. Motivation, Research Questions, and Hypotheses

### 1.1 Background

LLM reasoning consumes large amounts of tokens; every API call has a cost. Existing adaptive reasoning work (e.g., Think Just Enough) assumes model confidence can serve as a control signal for reasoning depth, but the foundation of this assumption—the calibration quality of model confidence—is rarely examined.

More importantly, existing budget sensitivity research (including 2026 work such as R³-Bench) generally does not distinguish between **hard constraints (API-level truncation)** and **soft constraints (prompt instructions)** as budget mechanisms. Models behave fundamentally differently under these two settings, yet this distinction is almost never explicitly discussed in the literature.

### 1.2 Research Questions

**Original RQ:** Can calibration quality predict and improve token allocation efficiency?

This question presupposes that the model has allocation agency. During the experiment, we discovered that the actual budget mechanism (hard truncation) removes this agency. Therefore, the RQ is revised to:

- **RQ1 (descriptive):** Under hard budget constraints, is model reasoning robustness related to calibration quality?
- **RQ2 (mechanistic):** Do hard and soft budget constraints fundamentally differ in their effects on model reasoning behavior?

### 1.3 Hypothesis Evolution

**Original hypothesis:** Well-calibrated models do not necessarily use fewer total tokens, but allocate more rationally—fewer tokens for easy questions, more for difficult ones.

**Key realization:** This hypothesis cannot be tested under a hard constraint design—the model has no agency to make allocation decisions; its output is simply truncated. This is not "hypothesis rejected" but "hypothesis not yet tested" (Kimiko, 2026-09-10).

**Revised hypotheses:**

- **H1:** Calibration quality (LCAE) and reasoning robustness (residual accuracy under hard constraints) are independent dimensions
- **H2:** Model behavior sequences differ fundamentally between hard and soft constraints

### 1.4 Methods

| Method | Purpose | Status |
|--------|---------|--------|
| Brier Score | Traditional calibration metric (baseline) | ✅ Done |
| LCAE (IRT-based) | Calibration quality measurement (advisor lab method) | ✅ Done |
| Controlled Budget Sweep | Fixed token budget comparison (**hard constraint design**) | ✅ Done |
| Process Mining | Diagnose reasoning trace behavior mechanisms | ✅ Done (core findings) |
| Soft Constraint Comparison | Prompt-based budget instruction, giving model agency | 📝 Planned (top priority) |

> **Methodological note:** The Controlled Budget Sweep uses hard constraints (`num_predict` truncation) rather than soft constraints (prompt instructions), to control for model variance in following budget instructions and focus on the robustness of reasoning content itself. This limitation is honestly acknowledged in the discussion.

---

## II. V1 Pilot — Validating the Tool

### Why This Design

At the July 4 meeting, my advisor suggested using Process Mining (PM) to analyze reasoning traces. But I had never used pm4py and was unsure whether it would work on LLM Chain-of-Thought text—CoT is not a standard event log with clear step boundaries.

V1 had a single goal: **confirm the PM pipeline works using the simplest possible questions at minimal cost.**

20 GSM8K questions, 5 models, 8 activity types. No confidence data—the goal was pipeline validation, not hypothesis testing.

### Findings

✅ PM can distinguish reasoning styles, stable across V1 and V2:
- **Intuitive (DeepSeek):** short traces, high answer ratio
- **Systematic (GPT-120B):** balanced calculate+reason
- **Struggling (GPT-20B):** long traces, high reason ratio

❌ Questions too easy (95-100% acc), zero variance. No confidence data.

### Lesson

PM works, but we need harder questions and must collect confidence.

---

## III. V2 — Adding Calibration Metrics

### Why This Design

V1's limitations drove V2's changes: harder questions (100 MMLU+ARC), multi-turn confidence self-assessment, 9 activity types, expanded PM analysis.

### The Confidence Prompt Lesson

Context-free prompt ("You answered D. How confident are you?") produced DeepSeek 2%, GLM-5.2 27%—meaningless. Multi-turn with full reasoning context produced 99%. **Context-free confidence prompts produce completely distorted data.**

### V2 Rebuild — Data Flip

Several bugs discovered (conformance field, asymmetric Levenshtein, JSD mislabeling, truncated thinking). After the July 24 rebuild, GPT-20B jumped from 56% to 98%, overturning the previous core finding.

### Lesson

V2's calibration value dropped, but the PM pipeline was validated and we exposed prompt sensitivity, confidence scarcity, and Petri net flower-model problems.

---

## IV. July 28 Deep Research — Literature Survey

### Most Important Finding

| Competitor | What They Did | Impact on Me |
|-----------|--------------|--------------|
| Think Just Enough (EACL 2026) | Confidence as stopping signal | Cannot claim "first to use confidence for reasoning control" |
| SelfBudgeter (ACL 2026) | Predicts token budget + RL | Emphasize training-free |
| Capability Calibration (arXiv 2026) | Calibration→best-of-k | Shift to reasoning length |
| Sonata (ICLR 2026) | Hidden-state adapter | Emphasize black-box |
| Berti et al. (TechRxiv 2025) | PM on LLM reasoning | PM downgraded to diagnosis |
| **R³-Bench (arXiv 2026-08)** | Resource-rational reasoning under shared budgets | Does not distinguish hard/soft constraints |

### Repositioning

Differentiators: IRT calibration, training-free, black-box, reasoning-length allocation, IDS causal validation, PM mechanism diagnosis.

---

## V. V3 Phase 2 — Budget Sensitivity Pilot

### Why This Design

Needed to confirm token requirement measurability existed before investing in large experiments.

2 extreme models (GPT-20B poorly calibrated vs DeepSeek well-calibrated) × 30 questions × 4 budgets = 480 calls.

### Results

| Budget | GPT-20B | DeepSeek | Gap |
|--------|---------|----------|-----|
| 128 | 0.0% | 0.0% | — |
| **256** | 3.3% | **15.0%** | **5×** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

### Decision

Budget sensitivity exists; DeepSeek wins everywhere. But only 2 models → cannot resolve calibration vs ability confound. **Proceed to Phase 3.**

---

## VI. B + C — Confidence Test + Activity Labeling

**B:** 2 models × 10 questions × 2 budgets to verify confidence mechanism. GPT-20B 97/70 (distinguishable ✅), DeepSeek 100/99 (overconfident). Mechanism works.

**C:** Exported 100 activity-label samples for future human annotation.

---

## VII. V3 Phase 3 — Decisive Experiment

### Why This Design

4 models (added GPT-120B, GLM-5.2) to resolve the calibration vs ability confound. Removed 128 budget, 3 replicates, L3+L4 only, added IRT + LCAE.

Total: 4 × 60 × 3 × 3 × 2 = **4,320 API calls**.

### Key Findings

#### Finding 1: Ability θ and Calibration LCAE Are Independent Dimensions

| Model | Acc@1024 | Ability θ | LCAE |
|-------|---------|----------|------|
| DeepSeek | **66.1% 🏆** | **+0.65 🏆** | 0.303 |
| GPT-120B | 50.6% | +0.00 | **0.247 🏆** |
| GPT-20B | 48.3% | −0.09 | 0.341 |
| GLM-5.2 | 36.7% | −0.57 | 0.438 |

#### Finding 2: Brier vs LCAE Give Different Rankings

Which metric you choose changes which model you judge most reliable. LCAE captures difficulty×ability interaction that Brier misses.

#### Finding 3: Confidence Gap as Proxy

GPT-120B (+25.5) > DeepSeek (+15.5) > GPT-20B (+7.3) > GLM-5.2 (+3.4). Consistent with LCAE.

#### Finding 4: GLM-5.2 Largest but Worst

θ=−0.57, LCAE=0.438, 96% confidence when wrong. Model size ≠ math reasoning capability.

### At the Time

I expected "better calibrated → better low-budget performance." The data showed DeepSeek wins due to reasoning efficiency, not calibration. My core hypothesis was only half right.

---

## VIII. Kimiko's Concerns and the IDS Intervention

### Kimiko's Diagnosis

1. Phase 3 does not support the core claim (best low-budget performer ≠ best calibrated)
2. IDS is the strongest differentiator but not yet run
3. R³-Bench (arXiv Aug 2026) overlaps with budget sensitivity

### IDS Results

| Effect | Result |
|--------|--------|
| Calibration improved? | ✅ Brier ↓, confidence_wrong ↓ |
| Accuracy improved? | ❌ No significant change |
| Causal chain? | ❌ Calibration improvement did not translate to accuracy |

---

## IX. PM Analysis — Behavioral Diagnosis of Truncation (Core Finding)

### Kimiko's Key Question

At low budgets, is the model failing because it "does not know when to stop" (calibration) or because it "cannot solve at all" (ability)?

### PM Findings

| Model | @256 Steps | @1024 Steps | Ratio | Answer@256 |
|-------|-----------|------------|-------|-----------|
| GPT-20B | 1.1 | 11.0 | 10% | 0.0% |
| GPT-120B | 1.8 | 12.7 | 14% | 0.0% |
| DeepSeek | **2.3** | 6.6 | **35%** | 0.0% |
| GLM-5.2 | 0.1 | 7.8 | 1% | 0.0% |

### Core Finding (Finding 5: Truncation Mechanism Diagnosis)

1. **At 256 tokens, models produce only 1-2 steps with 0% answer activity**—not an allocation decision, but forced truncation by `num_predict`
2. **Activity distribution proportions are essentially identical between 256 and 1024**—the model does the same front-half reasoning, just never reaches answer/verify
3. **DeepSeek's advantage is concise reasoning style (fewer tokens per step), not calibration**
4. **This explains why IDS did not improve accuracy**—the model has no allocation agency for calibration signals to act upon

### The Fundamental Design Issue

`num_predict` truncation removes the model's allocation agency. Phase 3 measured "residual accuracy after forced truncation," not "token allocation efficiency."

---

## X. Soft vs Hard Constraint — Next Core Experiment

### Kimiko's Key Insight

Existing adaptive reasoning research does not distinguish soft vs hard budget constraints. This is a real gap with a real contribution.

### Comparison Experiment Design (Top Priority)

| Parameter | Setting |
|-----------|---------|
| Models | GPT-120B + DeepSeek (same as IDS) |
| Questions | 30 MATH-500 L3+L4 (same batch) |
| Budgets | 256, 512 |
| Prompt | "Please complete your reasoning within approximately N tokens." |
| Replicates | 3 |
| Scale | ~720 calls |

### Comparison After Running

PM analysis across three conditions:
1. **Hard constraint** (existing) — truncated, no agency
2. **Soft constraint** (new) — model decides allocation
3. **Unconstrained @1024** (existing) — control

If soft shows notably more answer/evaluate activities than hard, the paper's core claim gains empirical support: **the two constraint mechanisms are fundamentally different.**

### Compliance Verification Needed

Models may not accurately follow "within N tokens"—need to document how compliance is verified (output length distribution).

---

## XI. Research Contributions (Rewritten)

1. **New research question:** First to distinguish hard vs soft constraint budget mechanisms, highlighting the missing distinction in the literature
2. **New findings:** Calibration quality and reasoning robustness are independent dimensions; DeepSeek's low-budget advantage comes from concise reasoning style, not calibration
3. **New methodological contribution:** Using Process Mining to directly diagnose reasoning truncation behavior mechanisms
4. **Honest negative result:** IDS improves calibration but not accuracy, revealing where the causal chain breaks

---

## XII. Next Steps

| Priority | Item | Description |
|----------|------|-------------|
| **Top** | Soft constraint comparison experiment | Establish hard vs soft behavioral contrast, support core claim |
| High | Advisor meeting | Present findings from Phase 3 through PM analysis |
| High | Paper draft | Narrative: "experiment design revealed a more fundamental problem" |
| Medium | Activity labeling validation | Human annotation of 100 samples |

---

## XIII. Key Files

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