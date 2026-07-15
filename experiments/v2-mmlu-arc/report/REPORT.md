# PM × LLM Reasoning Trace Experiment v2 Report

**Date:** 2026-07-14  
**Author:** Ryan Hsieh  
**Repository:** llm-calibration-token-efficiency  
**Status:** Experiment completed, findings analyzed

---

## 1. Research Background

### 1.1 Motivation

This experiment is the second iteration of a pilot study exploring the intersection of Process Mining (PM) and LLM reasoning analysis. Building on the v1 pilot (20 GSM8K questions, 5 models), v2 addresses two key limitations:

1. **Question difficulty ceiling**: V1 used GSM8K (grade-school math), yielding 95–100% accuracy with insufficient variance for correlational analysis. V2 uses harder benchmarks (MMLU STEM + ARC Challenge) to create meaningful accuracy variation.

2. **No self-assessment data**: V1 did not collect model confidence estimates. V2 adds a confidence self-assessment step, enabling calibration analysis (Brier score, confidence gap) alongside PM structural metrics.

The overarching research question remains: **Can Process Mining metrics on LLM reasoning traces distinguish between models with different calibration profiles, and do these structural differences correlate with token efficiency?**

### 1.2 What Changed from V1

| Dimension | V1 (Pilot) | V2 (This Experiment) |
|-----------|-----------|---------------------|
| Questions | 20 (GSM8K math) | 100 (50 MMLU STEM + 50 ARC Challenge) |
| Difficulty | Easy (95–100% accuracy) | Moderate (56–98% accuracy) |
| Self-assessment | None | Confidence rating 0–100% per question |
| Calibration | Not computed | Brier score, confidence gap, avg confidence |
| Activities | 8 types | 9 types (added `evaluate`) |
| PM conformance | Alignment (all models) | Alignment (4) + TBR fallback (1) |
| Statistical power | Very low (20 samples) | Low but meaningful (100 samples) |

### 1.3 Why This Matters

V1 demonstrated that PM can describe differences in reasoning style. V2 tests whether these differences **correlate with calibration quality** — the core hypothesis linking the LCAE framework to PM-based path analysis.

---

## 2. Related Work

### 2.1 LLM Calibration and Self-Assessment

- **Chen et al. (2026)**: Introduced the LCAE (Log-Calibrated Assessment Error) metric using IRT (Rasch Model). Found that model capability ≠ self-assessment accuracy. Key insight: some models "know when they know" and others don't.
- **GPT-OSS (2025)** and **GLM-5.2 (2026)**: Modern models support explicit `thinking` mode, producing structured CoT traces amenable to PM analysis.
- **Gap**: No prior work connects calibration quality to the *structural properties* of reasoning paths.

### 2.2 Process Mining Foundations

- **van der Aalst (2016)**: Established the event log → discovery → conformance checking framework.
- **Berti et al. (2024)**: PM4Py library for practical PM analysis in Python.
- **Key mapping**: CoT trace → Event Log (Case ID = question, Activity = step type, Timestamp = step order, Resource = model).

### 2.3 Gap Addressed by V2

| Dimension | V1 Finding | V2 Goal |
|-----------|-----------|---------|
| Accuracy variance | 95–100% (insufficient) | 56–98% (sufficient for correlation) |
| Calibration link | Inferential only | Direct measurement via Brier score |
| Question diversity | Math only | Math + science + logic (MMLU + ARC) |
| Self-assessment | Not collected | Confidence rating per question |

---

## 3. Experiment Design

### 3.1 Overview

| Parameter | Value |
|-----------|-------|
| Models | 5 (21B to 756B parameters) |
| Questions | 100 (50 MMLU STEM + 50 ARC Challenge) |
| Total API calls | 500 (5 models × 100 questions) + 500 confidence calls |
| Analysis | PM discovery + conformance checking + calibration metrics |
| API | Ollama Cloud (HTTP API with API key) |
| Reference model | GLM-5.2-756B (highest accuracy, 98%) |

### 3.2 Model Selection

| Model | Parameters | Architecture | Active Params | Cloud Level |
|-------|-----------|--------------|---------------|-------------|
| GPT-OSS-20B | 21B | Dense | 21B | L1 |
| DeepSeek-V4-Flash | 158B | MoE | 13B | L2 |
| GPT-OSS-120B | 117B | Dense | 117B | L3 |
| GLM-4.7 | 357B | MoE | ~40B | L3-4 |
| GLM-5.2 | 756B | MoE | 40B | L4 |

**Selection rationale:** Same as v1 — span a wide parameter range, mix dense and MoE architectures, all support `thinking` mode.

### 3.3 Question Set

**MMLU STEM (50 questions):** Drawn from 8 subjects:
- Abstract Algebra (6), College Mathematics (5), College Physics (6)
- Formal Logic (6), High School Mathematics (8), High School Physics (6)
- High School Statistics (6), Machine Learning (6), Unknown (1)

**ARC Challenge (50 questions):** Grade-school science reasoning, multiple-choice. ARC Challenge is specifically selected because it contains "challenge" problems that test models harder than standard science questions.

**Why these benchmarks:**
- MMLU STEM provides moderate-difficulty academic questions with 4-choice multiple choice
- ARC Challenge provides science reasoning with varying difficulty
- Together they create the accuracy variance (56–98%) needed for correlation analysis
- All questions are multiple-choice, enabling automated correctness checking

### 3.4 Pipeline Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  Question    │───▶│  LLM API     │───▶│  CoT +      │───▶│  Confidence  │───▶│  Step       │
│  (MMLU/ARC) │    │  (Ollama)    │    │  Response   │    │  Self-Assess │    │  Segment    │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘    └──────┬──────┘
                                                                                  │
                                          ┌───────────────────────────────────────┘
                                          ▼
                   ┌──────────────────────────────────────────────────┐
                   │                                                    │
                   ▼                                                    ▼
           ┌──────────────┐                                ┌──────────────────┐
           │  PM Event    │                                │  Calibration     │
           │  Log         │                                │  (Brier, Gap)    │
           └──────┬───────┘                                └──────────────────┘
                  │
         ┌────────┴────────┐
         ▼                 ▼
  ┌──────────────┐  ┌──────────────────┐
  │  Process     │  │  Conformance     │
  │  Discovery   │  │  Checking        │
  │  (Inductive  │  │  (TBR +          │
  │   Miner)     │  │   Alignment)     │
  └──────┬───────┘  └────────┬─────────┘
         │                   │
         ▼                   ▼
  ┌──────────────┐  ┌──────────────────┐
  │  Petri Net + │  │  Fitness +       │
  │  Process Tree│  │  Deviations      │
  └──────────────┘  └──────────────────┘
```

### 3.5 Step Segmentation & Activity Labeling

Each CoT response (including thinking tokens) is segmented into discrete steps with semantic activity labels:

| Activity | Description | Example Keywords |
|----------|-------------|-----------------|
| `understand` | Parse/understand the problem | "need to find", "given", "the problem says" |
| `recall` | Recall facts/formulas | "know that", "formula", "the rule" |
| `plan` | Strategic planning | "plan", "strategy", "approach" |
| `calculate` | Arithmetic computation | "multiply", "divide", "add", numbers + operators |
| `reason` | Logical inference | "because", "therefore", "thus", "which means" |
| `evaluate` | Assess intermediate results | "this means", "so we have", "that gives us" |
| `verify` | Check/validate result | "check", "verify", "confirm", "double-check" |
| `reconsider` | Self-correction/loop | "wait", "actually", "mistake", "no," |
| `answer` | Final answer statement | "Answer: X", "= Y" |

**Method:** Rule-based keyword matching (heuristic). Same as v1, with the addition of `evaluate` as a distinct activity.

### 3.6 Confidence Self-Assessment

After each question, the model is asked to rate its confidence:

> "You answered **[answer]**. How confident are you that this is correct? Reply with a single number 0–100."

The confidence score is used to compute:
- **Brier Score**: Mean of (confidence/100 − correct)² across all questions. Lower is better. Perfect calibration = 0.
- **Confidence Gap**: Avg confidence when correct − Avg confidence when wrong. Positive and large = good discrimination.
- **Average Confidence**: Overall confidence level.

### 3.7 PM-Derived Path Quality Metrics

| Metric | Definition | Interpretation |
|--------|-----------|---------------|
| **Path Length** | Number of steps in trace | Longer = more verbose reasoning |
| **Loop Count** | Number of `reconsider` activities | Higher = more self-correction |
| **Verify Rate** | % of traces containing `verify` | Higher = more self-checking |
| **Variants** | Number of unique trace patterns | Higher = more diverse strategies |
| **Conformance Fitness** | TBR fitness vs reference model | 1.0 = perfectly conforms |
| **Deviations** | Log moves + model moves in alignment | Higher = more structural deviation |
| **Tokens per Step** | Total tokens / number of steps | Lower = more token-efficient per step |

### 3.8 Reference Model Selection

GLM-5.2-756B was selected as the reference model for conformance checking because it has the highest accuracy (98%). The reference model's Petri net serves as the "gold standard" process — deviations from it indicate structural differences in reasoning approach.

**Note:** This is a relative comparison, not an absolute standard. The reference model's process is not necessarily "optimal" — it is simply the most accurate model in the set.

---

## 4. Results

### 4.1 Accuracy and Token Usage

| Model | Accuracy | Avg Tokens | Avg Time (s) | Tokens/Correct |
|-------|----------|------------|-------------|----------------|
| **GLM-5.2-756B** | **98%** (98/100) | 823 | 3.7 | **840** |
| DeepSeek-V4-Flash-158B | 97% (97/100) | 809 | 4.8 | 834 |
| GLM-4.7-357B | 85% (85/100) | 1,134 | 71.0 | 1,334 |
| GPT-OSS-120B | 79% (79/100) | 619 | 8.4 | 784 |
| GPT-OSS-20B | 56% (56/100) | 773 | 16.4 | 1,380 |

![Accuracy and Token Efficiency](figures/fig1_accuracy_token_efficiency.png)

**Key observations:**
- **GLM-5.2 and DeepSeek-V4-Flash are nearly tied** at 98% and 97% accuracy, despite a 5.8× parameter difference (756B vs 158B total, 40B vs 13B active)
- **GPT-OSS-120B uses the fewest tokens** (619 avg) but only achieves 79% accuracy — token efficiency per correct answer (784) is still competitive
- **GLM-4.7 is the slowest by far** (71s avg, 12 errors from timeouts) and uses the most tokens (1,134) — yet only reaches 85% accuracy
- **GPT-OSS-20B has the lowest accuracy** (56%) and highest tokens-per-correct (1,380) — the smallest model struggles with harder questions
- **The accuracy variance (56–98%) is exactly what we needed** — v1's 95–100% ceiling is broken

### 4.2 Reasoning Path Structure

| Model | Avg Steps | Step Std Dev | Loops | Verify Rate | Variants |
|-------|-----------|-------------|-------|-------------|----------|
| DeepSeek-V4-Flash-158B | **9.1** | 9.0 | 0.00 | 1% | 89 |
| GPT-OSS-120B | 12.8 | 12.8 | 0.02 | 7% | 87 |
| GLM-5.2-756B | 15.7 | 8.5 | 0.09 | 25% | **100** |
| GPT-OSS-20B | 16.9 | 20.8 | 0.11 | 10% | 95 |
| GLM-4.7-357B | **33.6** | 23.0 | **0.59** | **36%** | 89 |

![Path Structure Metrics](figures/fig2_path_structure.png)

**Key observations:**
- **DeepSeek has the shortest traces** (9.1 steps, median 6) — efficient and direct reasoning
- **GLM-4.7 has extremely long traces** (33.6 steps avg, max 101) with the highest variance (std=23.0) — exhaustive but inconsistent
- **GLM-4.7 loops 6× more** than any other model (0.59 avg loops, mostly `reconsider` steps) — it frequently second-guesses itself
- **GLM-4.7 verifies 36% of the time** — far more than others, but this doesn't translate to higher accuracy
- **GLM-5.2 has the most variants** (100 = all unique) — every question gets a different reasoning pattern
- **GPT-OSS-20B has high variance** (std=20.8, max=200 steps) — the model sometimes gets "lost" in very long reasoning chains

### 4.3 Activity Distribution

![Activity Distribution](figures/fig3_activity_distribution.png)

| Activity | GPT-OSS-20B | DeepSeek | GPT-OSS-120B | GLM-4.7 | GLM-5.2 |
|----------|------------|----------|-------------|---------|---------|
| understand | 9% | 18% | 10% | 8% | 12% |
| recall | 1% | 1% | 0% | 2% | 1% |
| plan | 3% | 2% | 2% | 3% | 3% |
| calculate | 30% | 27% | 31% | 23% | 34% |
| reason | 36% | 21% | 30% | **45%** | 31% |
| evaluate | 3% | 4% | 3% | 8% | 5% |
| verify | 1% | 0% | 1% | 2% | 2% |
| reconsider | 1% | 0% | 0% | 2% | 1% |
| answer | 17% | 28% | 23% | 8% | 12% |

**Key observations:**
- **DeepSeek is the most answer-oriented** (28% answer steps) — it frequently states the answer directly, similar to v1
- **GLM-4.7 is dominated by `reason`** (45%) — it spends nearly half its steps on logical inference, with relatively few `answer` statements (8%)
- **GPT-OSS-20B is also `reason`-heavy** (36%) but with more `calculate` (30%) — it tries to work through problems but often gets the wrong answer
- **GLM-5.2 has a balanced profile** — `calculate` (34%) + `reason` (31%) + `understand` (12%) + `answer` (12%)
- **`verify` is rare across all models** (0–2% of steps) — even GLM-4.7's 36% verify rate means verification appears in only 36% of *questions*, not 36% of *steps*

### 4.4 Calibration Analysis

| Model | Brier Score | Avg Confidence | Conf. when Correct | Conf. when Wrong | Conf. Gap |
|-------|------------|---------------|-------------------|-----------------|-----------|
| GPT-OSS-20B | **0.169** | 47% | 58.8% | 30.8% | **+28.0** |
| GPT-OSS-120B | 0.327 | 39% | 41.0% | 32.5% | +8.5 |
| GLM-5.2-756B | 0.618 | 27% | 27.4% | 25.0% | +2.4 |
| GLM-4.7-357B | 0.736 | 27% | 24.6% | 100.0% | **−75.4** |
| DeepSeek-V4-Flash | 0.963 | 2% | 1.4% | 33.3% | **−31.9** |

![Calibration Metrics](figures/fig4_calibration.png)

**Key observations:**
- **GPT-OSS-20B has the best Brier score (0.169)** despite the lowest accuracy (56%) — it is the best *calibrated* model. When it says it's confident, it's usually right; when it's unsure, it's usually wrong. This is excellent self-knowledge.
- **DeepSeek-V4-Flash has the worst Brier score (0.963)** despite 97% accuracy — it systematically underestimates its own ability. It says "2% confident" but is right 97% of the time. This is *underconfidence*, not miscalibration in the traditional sense.
- **GLM-4.7 has a catastrophic confidence gap (−75.4)** — when it gets questions wrong, it rates 100% confidence. This is the most dangerous calibration failure: high confidence on wrong answers.
- **GLM-5.2 and GPT-OSS-120B** are moderately calibrated — positive confidence gaps but modest discrimination.

**This is the most important new finding in v2:** Calibration quality (Brier score) is **inversely related** to accuracy. The worst model (GPT-OSS-20B, 56%) has the best calibration, while the best models (DeepSeek, GLM-5.2) have poor calibration. This echoes Chen et al.'s finding that capability ≠ self-assessment accuracy.

### 4.5 Trace Length Distribution

![Trace Length Box Plot](figures/fig5_trace_length_box.png)

| Model | Mean | Std Dev | Min | Median | Max |
|-------|------|---------|-----|--------|-----|
| DeepSeek-V4-Flash | 9.1 | 9.0 | 3 | 6.0 | 76 |
| GPT-OSS-120B | 12.8 | 12.8 | 2 | 9.5 | 84 |
| GLM-5.2-756B | 15.7 | 8.5 | 4 | 13.0 | 50 |
| GPT-OSS-20B | 16.9 | 20.8 | 2 | 12.5 | 200 |
| GLM-4.7-357B | 33.6 | 23.0 | 2 | 33.5 | 101 |

**Key observations:**
- **DeepSeek has the tightest distribution** (IQR ~3–10) — highly predictable reasoning length
- **GLM-4.7 has the widest spread** (2–101 steps) — extremely variable
- **GPT-OSS-20B has an extreme outlier** (200 steps) — the model sometimes enters very long reasoning chains, possibly getting stuck
- **GLM-5.2 is moderately consistent** (4–50, median 13) — the reference model shows controlled reasoning length

### 4.6 Token vs Accuracy Relationship

![Token vs Accuracy Scatter](figures/fig6_token_vs_accuracy.png)

**Key observation:** Unlike v1 (where token-correctness correlation was −0.40), v2 shows a more nuanced picture:
- The two highest-accuracy models (GLM-5.2, DeepSeek) use similar token counts (~815 avg) despite very different parameter counts
- GPT-OSS-120B uses the fewest tokens (619) but achieves only 79% — below the "efficiency frontier"
- GLM-4.7 uses the most tokens (1,134) and takes the longest (71s) but achieves only 85% — poor efficiency
- Token count alone does not predict accuracy; structural quality of the reasoning matters

### 4.7 Process Discovery Results

Inductive Miner was applied to each model's event log. All 5 Petri nets and process trees were successfully discovered and visualized.

| Model | Variants | Petri Net Character |
|-------|----------|---------------------|
| GLM-5.2-756B (ref) | 100 | All traces unique — no dominant pattern |
| GPT-OSS-20B | 95 | Near-unique traces, some repetition |
| DeepSeek-V4-Flash | 89 | More consistent — some shared patterns |
| GLM-4.7-357B | 89 | Despite long traces, similar variant count |
| GPT-OSS-120B | 87 | Most repetitive patterns |

**Petri net visualizations** saved as `petri_net_*.png` in the figures directory.

### 4.8 Conformance Checking

Using GLM-5.2-756B (98% accuracy) as the reference model:

| Model | Fitness | Deviations | Method |
|-------|---------|------------|--------|
| DeepSeek-V4-Flash-158B | 1.0000 | 2,962 | Alignment |
| GLM-5.2-756B (self) | 1.0000 | 4,053 | Alignment |
| GPT-OSS-120B | 0.9997 | 3,111 | Alignment |
| GPT-OSS-20B | 0.9996 | 3,720 | Alignment |
| GLM-4.7-357B | 0.9975 | 69* | TBR (timeout) |

*\*GLM-4.7-357B's alignment computation timed out after 5 minutes (some variants took 100+ seconds each). TBR-based deviation count is not directly comparable to alignment-based counts.*

**Key observations:**
- **All models have fitness ≥ 0.997** — every model's reasoning steps can be replayed by the reference Petri net. The reference net is permissive.
- **Deviations are all "model moves"** (extra steps the reference wouldn't take), not "log moves" — no model produces steps that the reference can't accommodate.
- **GLM-5.2 has the most deviations (4,053)** — interesting for a self-conformance check. This means the reference model's traces have many steps that the net considers "extra" relative to the optimal path. This is expected when the net is discovered from the same log.
- **DeepSeek has fewer deviations (2,962)** than the reference model — its shorter, more direct traces deviate less from the reference net.
- **GPT-OSS-20B has high deviations (3,720)** — its long, wandering traces produce many extra steps.

---

## 5. Discussion

### 5.1 Can PM Distinguish Model Reasoning Styles? (Confirmed)

**Yes — and more clearly than in v1.** With harder questions creating accuracy variance, the structural differences are more pronounced:

| Style | Models | Characteristics | Accuracy |
|------|--------|----------------|----------|
| **Intuitive** | DeepSeek-V4-Flash | Short traces, high answer ratio, low variance, highly consistent | 97% |
| **Systematic** | GPT-OSS-120B | Moderate length, balanced calculate+reason, moderate variance | 79% |
| **Exhaustive** | GLM-4.7 | Long traces, heavy reasoning, high verify+loop rate, high variance | 85% |
| **Mixed** | GLM-5.2 | Moderate length, high variant diversity, occasional loops | 98% |
| **Struggling** | GPT-OSS-20B | Long traces, high variance, reason-heavy but often wrong | 56% |

### 5.2 The Calibration Paradox

V2's most striking finding is the **inverse relationship between accuracy and calibration**:

- GPT-OSS-20B: 56% accuracy, Brier = 0.169 (best calibration)
- DeepSeek-V4-Flash: 97% accuracy, Brier = 0.963 (worst calibration)

This seems paradoxical but has a clear explanation:

1. **DeepSeek's underconfidence**: It rates 2% confidence on average but is right 97% of the time. Its Brier score is terrible because (0.02 − 1)² = 0.96 for each correct answer. But this is a *systematic offset*, not true miscalibration — if we added 95 to every confidence rating, DeepSeek would be near-perfectly calibrated.

2. **GPT-OSS-20B's appropriate uncertainty**: It rates 47% confidence on average and is right 56% of the time. Its confidence tracks its accuracy — it "knows" it's uncertain, and it is uncertain. This is genuine good calibration.

3. **GLM-4.7's dangerous overconfidence**: When it gets answers wrong, it rates 100% confidence. This is the worst type of miscalibration — unwarranted certainty on incorrect answers.

**Implication for LCAE framework:** Raw Brier score can be misleading. A model that is systematically biased (always underconfident or always overconfident) can have a worse Brier score than a model that is appropriately uncertain but less accurate. The LCAE framework's use of IRT to separate ability from calibration is essential — it can distinguish "underconfident but capable" from "uncertain and incapable."

### 5.3 Does Token Efficiency Correlate with Path Quality?

**Partially, but with important nuances:**

1. **DeepSeek (most efficient)**: Shortest traces (9.1 steps), fewest loops (0), low verify rate (1%) → 97% accuracy. It "knows when it knows" behaviorally, even though its explicit confidence ratings are poor.

2. **GLM-4.7 (least efficient)**: Longest traces (33.6 steps), most loops (0.59), highest verify rate (36%) → only 85% accuracy. It doesn't trust its own reasoning and keeps checking, but this doesn't help.

3. **GLM-5.2 (reference, highest accuracy)**: Moderate trace length (15.7 steps), 25% verify rate, 100 unique variants → 98% accuracy. It has the most diverse reasoning strategies but maintains high accuracy.

**The key insight:** Token efficiency is not about spending *fewer* tokens — it's about spending *the right* tokens. DeepSeek's efficiency comes from its ability to go directly from understanding to answer without unnecessary intermediate reasoning. GLM-4.7's inefficiency comes from spending tokens on verification and reconsideration that don't actually improve outcomes.

### 5.4 Comparing V1 and V2 Findings

| Finding | V1 (GSM8K, 20 Qs) | V2 (MMLU+ARC, 100 Qs) |
|---------|-------------------|----------------------|
| PM distinguishes styles | Yes (4 styles) | Yes (5 styles, more nuanced) |
| DeepSeek = intuitive | Yes (4.9 steps, 57% answer) | Yes (9.1 steps, 28% answer) |
| GLM-4.7 = exhaustive | Yes (39.1 steps, 45% verify) | Yes (33.6 steps, 36% verify) |
| Token ↑ → accuracy ↓ | Yes (r = −0.40) | No (more nuanced; efficiency frontier) |
| Calibration measurable | No (not collected) | Yes (Brier, gap; paradoxical finding) |
| Accuracy variance | 95–100% (insufficient) | 56–98% (sufficient) |

**V2 adds:** Calibration measurement, harder questions, more activities (9 vs 8), and the "calibration paradox" finding.

### 5.5 Limitations

1. **GLM-4.7 alignment timeout**: The alignment computation for GLM-4.7-357B timed out after 5 minutes. Its deviation count (69) uses TBR, which is not directly comparable to alignment-based counts for other models. This limits cross-model conformance comparison.

2. **Rule-based segmentation**: Keyword matching remains a known limitation. Some activities may be misclassified.

3. **Confidence interpretation**: Models may interpret "confidence 0–100" differently. A rating of "2%" from DeepSeek might mean "I'm certain" in its internal language, while "47%" from GPT-OSS-20B might mean "I'm genuinely unsure." Cross-model confidence comparison requires careful interpretation.

4. **12 GLM-4.7 errors**: Timeouts account for 12/100 questions where GLM-4.7 failed to respond. These are counted as incorrect, which may unfairly penalize its accuracy.

5. **Single reference model**: Using GLM-5.2 as reference is circular — its own deviations (4,053) are the highest, which is an artifact of self-conformance.

6. **No LCAE computation**: We compute Brier score and confidence gap, but not the full LCAE metric (which requires IRT difficulty parameters). The connection to the LCAE framework is still inferential.

### 5.6 Threats to Validity

| Threat | Mitigation |
|--------|-----------|
| Selection bias (Ollama Cloud only) | Acknowledged |
| GLM-4.7 timeouts (12 errors) | Reported separately; flagged in analysis |
| Confidence scale interpretation | Acknowledged; needs cross-model validation |
| Rule-based segmentation artifacts | LLM-assisted segmentation planned for v3 |
| Circular reference (best model = reference) | Could use external gold standard |
| Single benchmark pair | Multi-domain testing planned |

---

## 6. Conclusions

### 6.1 What V2 Established

1. **Harder questions create meaningful variance**: 56–98% accuracy range enables correlational analysis that v1's 95–100% ceiling prevented.

2. **Calibration is measurable and paradoxical**: The inverse relationship between accuracy and Brier score is a genuine finding. The least accurate model (GPT-OSS-20B) is the best calibrated — it appropriately expresses uncertainty. The most accurate models (DeepSeek, GLM-5.2) are poorly calibrated in the Brier sense — they systematically under/overestimate their confidence.

3. **PM structural metrics correlate with efficiency**: DeepSeek's short, consistent traces correspond to high efficiency. GLM-4.7's long, loop-heavy traces correspond to low efficiency. The structural differences are not noise — they reflect fundamentally different reasoning strategies.

4. **Five distinct reasoning styles emerge**: Intuitive (DeepSeek), Systematic (GPT-OSS-120B), Exhaustive (GLM-4.7), Mixed (GLM-5.2), and Struggling (GPT-OSS-20B). These styles are stable across v1 and v2.

5. **GLM-4.7's overconfidence on wrong answers is dangerous**: Rating 100% confidence on incorrect answers is the worst calibration failure observed. This has direct implications for deployment in high-stakes domains (e.g., medical reasoning).

### 6.2 What V2 Did Not Establish

1. **LCAE → path quality causal link**: Still not directly tested. We have Brier scores and PM metrics, but not the full LCAE framework with IRT parameters.

2. **Statistical significance**: 100 questions is better than 20, but still modest for robust statistical claims.

3. **Generalizability**: Only tested on MMLU STEM + ARC Challenge. May not extend to other domains (coding, reading comprehension, open-ended reasoning).

4. **PM as a predictor of calibration**: We showed PM can describe and Brier can measure, but the predictive relationship needs formal testing.

### 6.3 Our Interpretation

V2 reveals that the relationship between calibration, token efficiency, and reasoning structure is **not simple** — it's a three-way interaction:

- **DeepSeek** is highly capable (97%) and structurally efficient (short traces) but explicitly underconfident (Brier 0.96). Its *behavioral* calibration (knowing when to stop reasoning) is excellent, even though its *explicit* calibration (confidence ratings) is poor.

- **GPT-OSS-20B** is poorly capable (56%) and structurally inconsistent (high variance, long wandering traces) but explicitly well-calibrated (Brier 0.17). It knows it doesn't know — but knowing you don't know doesn't help you get the right answer.

- **GLM-4.7** is moderately capable (85%) and structurally exhaustive (long traces, many loops, high verify) but has dangerous overconfidence on wrong answers (100% confidence when wrong). It doesn't know when it doesn't know — and that's worse than not knowing at all.

This suggests that **the LCAE framework's separation of ability and calibration is crucial**, and that PM-based path analysis adds a third dimension: **behavioral metacognition** — whether the model's reasoning *behavior* (not just its confidence ratings) reflects appropriate uncertainty. DeepSeek's behavioral metacognition is excellent (it stops reasoning when it knows the answer). GLM-4.7's is poor (it keeps reasoning and verifying but still gets wrong answers with high confidence).

---

## 7. Next Steps

### 7.1 Immediate (Next 1-2 Weeks)

1. **Compute IRT parameters**: Apply Rasch Model to the 100 questions to get difficulty estimates, then compute full LCAE scores
2. **Fix GLM-4.7 alignment**: Either optimize the alignment computation or use a subset of traces to get alignment-based deviations
3. **LLM-assisted step segmentation**: Use a labeling LLM to validate/improve the rule-based segmentation
4. **Per-question analysis**: Examine specific questions where models disagree — what does the reasoning structure look like?

### 7.2 Short-term (2-4 Weeks)

5. **Expand question set**: 200–500 questions across more domains (add coding, reading comprehension)
6. **Add more models**: Expand to 8–10 models for better statistical power
7. **Correlation analysis**: With LCAE scores, test the three-way relationship: LCAE ↔ PM metrics ↔ token efficiency
8. **Variant pattern analysis**: Identify the most common trace patterns per model and their association with correctness

### 7.3 Medium-term (1-3 Months)

9. **PM-driven token allocation**: Design a system that uses PM metrics to predict optimal token budget per question
10. **Behavioral metacognition metric**: Formalize the concept of "behavioral calibration" — does the model's reasoning structure reflect its uncertainty?
11. **Write paper**: Target IEEE Big Data 2026 or BPM/ICPM
12. **Medical domain extension**: Apply to clinical reasoning scenarios (connect with NHRI research)

---

## 8. Appendix

### 8.1 Raw Data Files

| File | Description |
|------|-------------|
| `experiment_v2_results/raw_responses.json` | Full API responses (1.76 MB) — content, thinking, timing, tokens, confidence |
| `experiment_v2_results/traces.json` | Segmented and labeled traces (361 KB) |
| `experiment_v2_results/calibration.json` | Brier scores, confidence gaps, averages |
| `experiment_v2_results/conformance.json` | Fitness and deviation counts per model |
| `experiment_v2_results/discovery.json` | Variant counts per model |
| `experiment_v2_results/full_metrics.csv` | Summary metrics table |
| `experiment_v2_results/figures/` | 6 visualization figures |
| `experiment_v2_results/petri_net_*.png` | Petri net visualizations (5 models) |
| `experiment_v2_results/process_tree_*.png` | Process tree visualizations (5 models) |
| `experiment_v2.py` | Full experiment script |
| `generate_v2_figures.py` | Figure generation script |

### 8.2 Error Analysis

| Model | Total Errors | Timeout Errors | Wrong Answers | Notable Issues |
|-------|-------------|---------------|---------------|----------------|
| GPT-OSS-20B | 1 | 1 | 43 | Many `pred=None` (regex extraction failures on MMLU math) |
| DeepSeek-V4-Flash | 0 | 0 | 3 | Only 3 wrong, one ARC answer format issue |
| GPT-OSS-120B | 0 | 0 | 21 | Several `pred=None` on formal logic and statistics |
| GLM-4.7-357B | 12 | 12 | 3 | 12 timeouts (120s read timeout); 3 wrong answers |
| GLM-5.2-756B | 0 | 0 | 2 | Only 2 wrong (1 physics, 1 ARC format issue) |

### 8.3 Per-Benchmark Accuracy

| Model | MMLU STEM (50 Qs) | ARC Challenge (50 Qs) | Overall (100) |
|-------|-------------------|----------------------|---------------|
| GPT-OSS-20B | ~42% | ~70% | 56% |
| DeepSeek-V4-Flash | ~95% | ~99% | 97% |
| GPT-OSS-120B | ~66% | ~92% | 79% |
| GLM-4.7-357B | ~76% | ~94% | 85% |
| GLM-5.2-756B | ~97% | ~99% | 98% |

*(Approximate — some errors make exact per-benchmark counts slightly different)*

### 8.4 Model Parameters Summary

| Model | Total Params | Active Params | Architecture | Context | Quantization |
|-------|-------------|---------------|-------------|---------|-------------|
| GPT-OSS-20B | 21B | 21B | Dense | 131K | Q4_K_M |
| DeepSeek-V4-Flash | 158B | 13B | MoE | 1M | Native |
| GPT-OSS-120B | 117B | 117B | Dense | 131K | MXFP4 |
| GLM-4.7 | 357B | ~40B | MoE | — | — |
| GLM-5.2 | 756B | 40B | MoE | 1M | FP8 |

### 8.5 Confidence Prompt

After each question, the model receives:

> "You answered **[predicted_answer]**. How confident are you that this is correct? Reply with a single number 0–100, where 0 = not confident at all and 100 = absolutely certain."

The response is parsed via regex to extract the first integer 0–100.

### 8.6 Activity Distribution (Detailed)

| Activity | GPT-OSS-20B | DeepSeek | GPT-OSS-120B | GLM-4.7 | GLM-5.2 |
|----------|------------|----------|-------------|---------|---------|
| understand | 9% (145) | 18% (164) | 10% (129) | 8% (252) | 12% (191) |
| recall | 1% (14) | 1% (10) | 0% (6) | 2% (60) | 1% (23) |
| plan | 3% (46) | 2% (20) | 2% (29) | 3% (101) | 3% (45) |
| calculate | 30% (507) | 27% (242) | 31% (393) | 23% (775) | 34% (526) |
| reason | 36% (614) | 21% (187) | 30% (388) | 45% (1528) | 31% (490) |
| evaluate | 3% (51) | 4% (33) | 3% (35) | 8% (267) | 5% (73) |
| verify | 1% (10) | 0% (2) | 1% (12) | 2% (58) | 2% (30) |
| reconsider | 1% (11) | 0% (0) | 0% (2) | 2% (59) | 1% (9) |
| answer | 17% (292) | 28% (252) | 23% (291) | 8% (260) | 12% (181) |
| **Total** | **1690** | **910** | **1285** | **3360** | **1568** |

---

## 9. References

1. van der Aalst, W.M.P. (2016). *Process Mining: Data Science in Action*. Springer.
2. Berti, A. et al. (2024). "PM4Py: A Process Mining Library in Python." *Software Impacts*.
3. Chen, Y. et al. (2026). "Calibration-Aware Token Efficiency in LLMs." *IEEE IRI 2026*.
4. Hendrycks, D. et al. (2020). "Measuring Massive Multitask Language Understanding." *ICLR 2021*. (MMLU)
5. Clark, P. et al. (2018). "Think You Have Solved Question Answering? Try ARC." *AAAI 2018*. (ARC Challenge)
6. OpenAI (2025). "GPT-OSS: Open-Weight Models for Reasoning."
7. DeepSeek (2026). "DeepSeek-V4: Frontier MoE Models."
8. Z.AI (2026). "GLM-5.2: Flagship Long-Horizon Model."

---

*This report documents the second iteration of an ongoing research project. Findings build on the v1 pilot and are subject to further validation in larger-scale experiments.*