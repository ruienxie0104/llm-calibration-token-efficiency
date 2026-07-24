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
├── ...                                    # Literature surveys and research notes
experiments/
├── v1-pilot/                              # GSM8K pilot and generated report
└── v2-mmlu-arc/                           # MMLU STEM + ARC Challenge experiment
scripts/
└── check_environment.py                   # Local environment validation
```

## Environment Setup

### Requirements

- Python 3.12 or 3.13
- Graphviz (`dot`) for PM4Py Petri net and process-tree rendering

On macOS, install Graphviz with:

```bash
brew install graphviz
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Configure API access only when running experiments that call Ollama:

```bash
cp .env.example .env
# Edit .env and set a newly rotated OLLAMA_API_KEY.
set -a
source .env
set +a
```

Do not reuse the key that previously appeared in repository history.

Validate the environment:

```bash
python scripts/check_environment.py
python scripts/check_v2_results.py
python -m compileall -q experiments scripts
pytest -q
```

The dependency versions are defined in `pyproject.toml`. Runtime-only installation
is also available through `requirements.txt`.

## Agent Handoff

Before continuing maintenance or rerunning V2, read the current
[project handoff document](docs/zh-TW/agent-handoff-2026-07-24.md). It records
the uncommitted environment and High-priority fixes, known-invalid legacy
results, blockers, and acceptance criteria for the next steps.

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
