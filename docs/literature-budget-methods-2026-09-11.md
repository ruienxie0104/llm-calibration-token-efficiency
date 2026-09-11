# Literature Survey: Token Budget Methods for LLM Reasoning

> 2026-09-11 update — Focus: hard vs soft constraint distinction
> Base: 7/28 Deep Research (1612 lines) + subsequent findings

---

## I. Taxonomy of Token Budget Methods

### Category 1: Hard Constraint (API-level truncation)

The model's output is forcibly truncated at N tokens. The model is **not aware** of the limit.

| Work | How they do it | Explicit about hard constraint? |
|------|---------------|-------------------------------|
| **Our V3 Phase 3** | `num_predict` (Ollama API) | ✅ Yes, documented |
| **TALE** (ACL 2025) | Unclear — likely `max_tokens` | ❌ Not discussed |
| **R³-Bench** (arXiv Aug 2026) | Unclear — "shared budgets" but mechanism unspecified | ❌ Not discussed |

**Known gap:** Almost no paper explicitly says they use hard truncation or discusses its implications.

### Category 2: Soft Constraint (Prompt instruction)

The model is **told** the budget in the prompt. It has agency to decide how to allocate.

| Work | Prompt example | Compliance verified? |
|------|---------------|-------------------|
| **TALE** (ACL 2025) | Prompt with estimated budget | Not reported |
| **Steering LLM Thinking with Budget Guidance** (ACL Findings 2026) | Budget instruction in prompt | Not reported |
| **SelfBudgeter** (ACL 2026) | Model predicts budget, then follows it (trained) | Training-based compliance |

**Known gap:** Even papers using soft constraint do not verify whether models actually follow budget instructions. Compliance is assumed, not measured.

### Category 3: Dynamic Stopping

The model or system decides when to stop during reasoning, not a fixed budget.

| Work | Mechanism |
|------|----------|
| **Think Just Enough** (EACL 2026) | Periodic confidence check → stop when confident enough |
| **Token-level entropy stopping** | Various works on uncertainty-based early stopping |
| **Self-consistency voting** | Multiple samples → stop when consistent |

**Not a budget constraint in the sense we are studying** — no fixed N, model decides adaptively.

### Category 4: Training-based Budget Control

The model learns during training to operate within a budget; at inference time it follows learned patterns.

| Work | Training method |
|------|---------------|
| **SelfBudgeter** (ACL 2026) | Budget prediction token + RL reward for compliance |
| **CAT** (ACL Industry 2026) | Confidence-weighted preference optimization (CWPO) |
| **ROI-Reasoning** (arXiv 2026) | Meta-cognitive fine-tuning + RL |
| **Sonata / Adaptive Thinking** (ICLR 2026) | Hidden-state adapter trained to predict self-consistency |

**Not directly comparable** — these require fine-tuning, ours is training-free.

### Category 5: Post-hoc Truncation

Model generates freely, then the output is cut to N tokens.

| Work | Method |
|------|--------|
| **Common practice** | Generate → slice to N chars/tokens |

**Problem:** The model still "thought" beyond N tokens; truncation is purely cosmetic. Worse than hard constraint because token cost is still incurred.

---

## II. Has Any Paper Discussed the Hard vs Soft Distinction?

**After searching all surveyed literature: No.**

- **TALE** (ACL 2025): Uses prompt-based budget ("You have N tokens") — this is soft. But they never discuss the distinction or why they chose this method.
- **R³-Bench** (arXiv Aug 2026): Evaluates models under "shared budgets" but the mechanism is unspecified. Could be either hard or soft, but they never clarify.
- **SelfBudgeter** (ACL 2026): Trains model to follow its own predicted budget — a different paradigm entirely.
- **Think Just Enough** (EACL 2026): Dynamic stopping — no fixed budget at all.
- **Steering LLM Thinking with Budget Guidance** (ACL Findings 2026): Uses budget prompt (soft) but doesn't discuss mechanism choice.

**Kimiko's assessment is confirmed: this is a genuine gap.**

---

## III. Is This Direction Worth Pursuing?

### Supporting arguments

1. **Genuine gap** — No prior work explicitly discusses hard vs soft distinction
2. **Practical importance** — Real-world deployment decisions (API costs) depend on whether budget limits work as intended
3. **Novel methodology** — PM-based behavioral comparison is unique
4. **Low cost** — Soft constraint pilot (~720 calls) is feasible
5. **Existing data reusable** — Phase 3 hard constraint data can serve as baseline

### Risks

1. **Finding may be negative** — If soft vs hard behavior is similar, the story weakens
2. **Compliance issue** — Models may not follow soft budget instructions, requiring a compliance verification step
3. **Novelty boundary** — The contribution is "methodological insight" rather than "new SOTA result"

### Verdict

**Worth doing, but the soft constraint pilot is the critical test.** If the PM comparison shows clear behavioral differences, the direction is solid. If not, the gap may be smaller than expected.

---

## IV. Summary of All Budget Methods Found

| Category | Examples | Mechanism | Model Awareness | Requires Training | In Our Survey? |
|----------|----------|-----------|----------------|------------------|---------------|
| **Hard constraint** | Ours, TALE (unclear), R³-Bench (unclear) | API-level `max_tokens` | ❌ No | ❌ | ✅ |
| **Soft constraint** | TALE, Steering LLM, ours (planned) | Prompt instruction | ✅ Yes | ❌ | ✅ |
| **Dynamic stopping** | Think Just Enough, entropy-based | Periodic confidence check | ✅ Yes | ❌ | ✅ |
| **Training-based budget** | SelfBudgeter, CAT, Sonata, ROI-Reasoning | Learned length control | ✅ Yes | ✅ | ✅ |
| **Post-hoc truncation** | Common baseline | Cut after generation | ❌ No | ❌ | ✅ |