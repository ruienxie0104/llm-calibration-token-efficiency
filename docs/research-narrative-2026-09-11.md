# LLM Self-Assessment Calibration and Token Allocation Efficiency

> **Complete narrative: from research motivation to latest findings**
> Last updated: 2026-09-15 (with Soft Constraint Pilot results)

---

## I. Research Motivation

### Background

LLM reasoning consumes large amounts of tokens. Existing adaptive reasoning work (e.g., Think Just Enough) assumes model confidence can serve as a control signal for reasoning depth. However, this assumption rests on an untested premise—whether model calibration quality is reliable enough.

More fundamentally, existing budget constraint studies **do not distinguish between hard constraint (API-level truncation) and soft constraint (prompt instructions)**. If these two mechanisms produce fundamentally different behavior, all conclusions based on "model performance under budget constraints" need re-examination.

### Research Questions

- **RQ1 (methodological):** Do hard and soft budget constraints produce fundamentally different reasoning behaviors? Does this gap in the literature affect existing conclusions?
- **RQ2 (calibration vs efficiency):** Under soft constraint (model has agency), what is the relationship between calibration quality and token efficiency? Does the calibration signal that adaptive reasoning relies on remain valid?

### Core Finding

After the soft constraint pilot, we identified a more fundamental problem than originally hypothesized:

> **Under soft constraint, models achieve significantly higher accuracy but simultaneously lose their calibration ability—they can no longer distinguish when they are right or wrong. The signal that adaptive reasoning research depends on disappears precisely in the scenario where it would be most useful.**

---

## II. Related Work

### Budget Mechanisms in the Literature

| Category | Example Papers | Mechanism | Explicitly Discussed? |
|----------|---------------|-----------|----------------------|
| Hard constraint | R³-Bench (2026), TALE (2025) | API truncation (assumed) | ❌ Not specified |
| Soft constraint | TALE (2025), Steering LLM (2026) | Prompt instruction | ❌ Not specified |
| Dynamic stopping | Think Just Enough (2026) | No fixed budget | ✅ N/A |
| Training-based | SelfBudgeter (2026), CAT (2026) | Learned control | ✅ Different paradigm |
| Post-hoc truncation | Common baseline | Cut after generation | ❌ Not specified |

**Key observation:** Even papers using soft constraint never verify whether models actually follow budget instructions. Compliance is assumed, not measured.

---

## III. Methods

- **Brier Score:** Standard calibration baseline
- **LCAE (IRT-based):** Incorporates item difficulty and model ability
- **Controlled Budget Sweep:** Fixed token budget comparison (hard constraint)
- **Soft Constraint Prompt:** "Complete within N tokens" instruction (new comparison)
- **Process Mining:** Activity sequence analysis for behavioral diagnosis

---

## IV. Key Findings

### 4.1 Phase 3: Four Findings Under Hard Constraint

**Finding 1:** Ability θ and calibration LCAE are independent dimensions.
**Finding 2:** Brier and LCAE give different model rankings.
**Finding 3:** Confidence gap serves as a calibration proxy.
**Finding 4:** IDS improves calibration but not accuracy.

### 4.2 PM Analysis: Models Are Truncated Under Hard Constraint

At 256 tokens, models produce 1-2 steps on average with 0% answer activity. This explains why IDS had no effect—the model has no allocation agency.

### 4.3 Soft Constraint Pilot: Two Mechanisms Are Fundamentally Different (Core Finding)

**Accuracy:**

| Model | Budget | Hard Accuracy | **Soft Accuracy** | Δ |
|-------|--------|-------------|----------------|---|---|
| **GPT-120B** | **256** | **0.0%** | **74.4%** | **+74%** |
| DeepSeek | 256 | 18.3% | 80.0% | +62% |

**Calibration Disappears Under Soft Constraint:**

| Model | Budget | Hard Gap | **Soft Gap** |
|-------|--------|---------|-------------|
| GPT-120B | 256 | −52.2 | **+1.5** |
| GPT-120B | 512 | +39.7 | **−0.5** |
| DeepSeek | 256 | +23.6 | **0.0** |
| DeepSeek | 512 | +23.9 | **−0.1** |

### Five-Dimension Comparison

| Dimension | Hard Constraint | Soft Constraint |
|-----------|---------------|----------------|
| Acc @256 | 0-18% | **74-80%** |
| Calibration | **✅ Good** | ❌ Poor (gap near 0) |
| Model agency | ❌ None (truncated) | ✅ Yes |
| Best model | DeepSeek wins | Both models similar |
| IDS effect | Improves calibration only | 📝 To be tested |

---

## V. Contributions

1. **Methodological insight:** First to distinguish hard vs soft budget constraints and prove they produce fundamentally different behaviors—a gap never discussed in the literature
2. **Calibration-efficiency trade-off:** Under soft constraint, accuracy rises but calibration disappears, directly challenging the core assumption of adaptive reasoning
3. **Novel methodology:** Process Mining for diagnosing reasoning truncation behavior
4. **Honest negative result:** IDS improves calibration but not accuracy under hard constraint, revealing model agency as the causal bottleneck

---

## VI. Next Steps

| Priority | Item | Description |
|----------|------|-------------|
| **Top** | Soft + IDS experiment | With model agency, can IDS improve token allocation? |
| High | Paper draft | Core narrative: calibration-efficiency trade-off + hard/soft distinction |
| Medium | Activity labeling | Human annotation of 100 samples |
| Low | Post-hoc simulation | Free from existing 1024 data |