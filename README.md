# LLM Calibration × Token Efficiency

> **Can LLM self-assessment quality, measured through IRT-based difficulty signals, predict and optimize token allocation for efficient reasoning?**

## Overview

This project extends the LCAE framework (Chen et al., IEEE IRI 2026) by investigating the relationship between LLM self-assessment calibration and token efficiency.

**Core hypothesis:** Models with better calibrated self-assessment can more accurately predict their token requirements, enabling more efficient token budget allocation without sacrificing accuracy.

## Research Questions

- **RQ1:** Can LLM self-assessment accuracy (LCAE) predict token requirements?
- **RQ2:** Can IRT difficulty signals (IDS) serve as effective token allocation signals?
- **RQ3:** Does calibration improvement causally lead to token efficiency gains?
- **RQ4:** Which confidence signal (verbalized vs log-prob) is better for token allocation?

## Project Structure

```
docs/
├── advisor-meeting-2026-07-04.md          # Research proposal for advisor meeting
└── literature-survey-token-direction-2026-07-01.md  # Deep literature survey (16 arXiv queries)
```

## Key References

- Chen et al. (IEEE IRI 2026) — LCAE framework (學姐論文)
- ROI-Reasoning (arXiv:2601.03822) — Nearest competitor
- TRIAGE (arXiv:2605.13414) — Metacognitive token budget
- Kumaran (arXiv:2606.29490) — Verbalized confidence ≠ correctness

## Status

- [x] Literature survey complete (16 systematic arXiv searches)
- [x] Research proposal drafted
- [ ] Phase 1: LCAE × Token correlation analysis
- [ ] Phase 2: Causal chain validation
- [ ] Phase 3: Token allocation strategy

## Target Venue

IEEE Big Data 2026 (August deadline)