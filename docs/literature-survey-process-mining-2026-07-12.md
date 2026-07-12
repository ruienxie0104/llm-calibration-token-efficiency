# Literature Survey: Process Mining × LLM Agent × Token Efficiency

**Date:** 2026-07-12
**Purpose:** Map the intersection of Process Mining (PM), LLM agents, and token efficiency to identify research gaps for Ryan's new research direction.

---

## Search Summary

- **Sources:** arXiv (16 keyword queries + 6 phrase searches via web interface)
- **Date range:** 2024–2026 (focused on recent work)
- **Total relevant papers found:** ~25 (after dedup and relevance filtering)

---

## Cluster A: Process Mining × LLM (Core Intersection)

### A1. LLM as Process Mining Tool/Interface

| Paper | arXiv ID | Year | Key Contribution |
|-------|----------|------|-----------------|
| Re-Thinking Process Mining in the AI-Based Agents Era | 2408.07720 | 2024 | Proposes AgWf (Agent Workflow) paradigm for PM tasks; decomposes complex PM into simpler workflows with deterministic tools + LLM domain knowledge |
| PMAx: An Agentic Framework for AI-Driven Process Mining | 2603.15351 | 2026 | Multi-agent framework: Engineer agent generates local scripts for PM algorithms, Analyst agent interprets results. Privacy-preserving, local execution. By van der Aalst's group |
| On the Potential of LLMs to Solve Semantics-Aware PM Tasks | 2504.??? | 2025 | Rebmann et al. — evaluates LLMs on semantics-aware PM tasks (abstraction, matching) |
| Evaluating the Ability of LLMs to Solve Semantics-Aware PM Tasks | 2407.??? | 2024 | Earlier version of above — establishes benchmark for LLM PM capabilities |
| Exploring LLM Features in Predictive Process Monitoring | 2501.??? | 2026 | Padella et al. — LLM features for predictive PM on small-scale event logs |

**Key insight:** This cluster uses LLM to *do* process mining better (democratize PM, automate analysis). The direction is PM → LLM, not LLM → PM.

### A2. Process Mining for Analyzing LLM/Agent Behavior

| Paper | arXiv ID | Year | Key Contribution |
|-------|----------|------|-----------------|
| De-Linearizing Agent Traces: Bayesian Inference of Latent Partial Orders | 2602.??? | 2026 | BPOP framework — infers latent dependency partial order from noisy linearized agent traces. Models traces as stochastic linear extensions of underlying graph. **Directly relevant: PM techniques applied to agent traces** |
| M2-PALE: Process Mining + LLMs for Explaining MCTS Agents | 2604.??? | 2026 | Uses PM and LLMs to explain MCTS agent behavior — process mining for agent explainability |
| AlphaMemo: Structured Search-Process Memory for Self-Evolving Alpha Mining Agents | 2505.??? | 2026 | LLM agent with structured memory for alpha mining (quantitative finance). Memory of search processes |
| Progressive Crystallization: Turning Agent Exploration into Deterministic Workflows | 2512.??? | 2025 | Converts agentic exploration traces into deterministic workflows — essentially process discovery from agent traces |

**Key insight:** This cluster applies PM *to* LLM agent behavior. Very small cluster — this is the frontier.

---

## Cluster B: Clinical Pathway Process Mining (Medical Application)

| Paper | arXiv ID | Year | Key Contribution |
|-------|----------|------|-----------------|
| Improving Hospital Process Management through PM: COVID-19 Clinical Pathways | 2606.??? | 2026 | Ardimento et al. — PM on COVID-19 care pathways, transparent reproducible pipeline |
| From Data Lifting to Continuous Risk Estimation: Process-Aware Pipeline for Clinical Pathways | 2605.??? | 2026 | Same group — predictive monitoring of clinical pathways |
| Adaptive Identification and Modeling of Clinical Pathways with PM | 2512.??? | 2025 | Adaptive clinical pathway modeling |
| Discovering Care Pathways for Multi-Morbid Patients Using Event Graphs | 2110.??? | 2021 | Event graphs for multi-morbid patient pathways |
| Simulation of Patient Flow Using PM and Data Mining | 1702.??? | 2017 | ACS patient flow simulation |

**Key insight:** Clinical pathway PM is mature but has NOT been combined with LLM/agent reasoning. This is a gap.

---

## Cluster C: Agent Workflow Optimization & Trace Analysis

| Paper | arXiv ID | Year | Key Contribution |
|-------|----------|------|-----------------|
| Multi-View Encoders for Performance Prediction in LLM-Based Agentic Workflows | 2512.??? | 2025 | Predicts performance of LLM-based agentic workflows |
| CacheRL: Multi-Turn Tool-Calling Agents via Cached Rollouts | 2606.??? | 2026 | 92% process accuracy on multi-step tool-calling, 100x less compute than GPT-5. **Process accuracy = step-level quality** |
| LLM Agents for Interactive Workflow Provenance | 2512.??? | 2025 | Agent workflow provenance tracking |
| Trace2Policy: From Expert Behavior Traces to Self-Evolving Decision Agents | 2606.??? | 2026 | Extracts policies from expert traces — rule quality > model capability |
| Executable Agentic Memory for GUI Agent | 2505.??? | 2026 | GUI agent memory for procedural workflows |

**Key insight:** "Process accuracy" (step-level correctness) is emerging as a metric, but nobody uses PM techniques to measure it.

---

## Cluster D: Token Efficiency & Reasoning Quality (from previous survey)

Already covered in `literature-survey-token-direction-2026-07-01.md`. Key papers:
- ROI-Reasoning, TRIAGE, SelfBudgeter, UAB, "LLM Already Knows"

---

## Cluster E: Reasoning Trace Quality Evaluation

| Paper | arXiv ID | Year | Key Contribution |
|-------|----------|------|-----------------|
| Reasoning Quality Emerges Early: Data Curation for Reasoning Models | 2606.??? | 2026 | Jin et al. — data quality determines reasoning quality; small high-quality SFT data sufficient |
| How Do Answer Tokens Read Reasoning Traces? Self-Reading Patterns in Thinking LLMs | 2604.??? | 2026 | Analyzes how answer tokens attend to reasoning traces |
| Think-with-Rubrics: From External Evaluator to Internal Reasoning Guidance | 2605.??? | 2026 | Rubrics as internal reasoning guidance, not just external evaluation |

**Key insight:** Reasoning trace quality is being studied, but not through PM lens. The connection is missing.

---

## Research Gap Map

### Gap PM-1 (★★★): PM techniques applied to LLM reasoning traces
- **What's missing:** Nobody applies process discovery/conformance checking to LLM reasoning traces (CoT steps as events, reasoning traces as event logs)
- **Why it matters:** PM gives formal tools to analyze *why* a reasoning path was inefficient, not just *that* it was inefficient
- **Connection to Ryan's work:** Overthinking = conformance deviation; efficient reasoning = optimal process path

### Gap PM-2 (★★★): Token allocation quality through PM lens
- **What's missing:** Current token efficiency metrics (excess token usage, overthinking rate) measure quantity, not process quality. PM can measure path-level quality
- **Why it matters:** "Model used too many tokens" → PM can answer "because the reasoning path looped at step 3" or "took a detour through unnecessary sub-goals"
- **Connection to Ryan's work:** Directly extends LCAE/token allocation research with process-level analysis

### Gap PM-3 (★★☆): Clinical pathway PM × LLM agent reasoning
- **What's missing:** Clinical pathway PM is mature but hasn't been combined with LLM agents that reason about patient care
- **Why it matters:** Medical AI agents that follow optimal clinical pathways = safer, more efficient care
- **Connection to Ryan's work:** Medical scenario as application domain (connects to NHRI kidney agent background)

### Gap PM-4 (★★☆): Causal chain: calibration → process quality → token efficiency
- **What's missing:** Does better self-assessment (LCAE) lead to better reasoning paths (PM quality), which leads to better token allocation?
- **Why it matters:** Validates the causal story from calibration to efficiency through process quality as mediator
- **Connection to Ryan's work:** This is the unification of the token efficiency direction and the PM direction

---

## Key Papers to Read in Detail

1. **Berti et al. (2024)** — 2408.07720 — "Re-Thinking Process Mining in the AI-Based Agents Era" (foundational, by van der Aalst's group)
2. **PMAx (2026)** — 2603.15351 — Agentic framework for PM (latest from same group)
3. **BPOP / De-Linearizing Agent Traces (2026)** — Bayesian inference of latent partial orders from agent traces
4. **Rebmann et al. (2025)** — LLMs for semantics-aware PM tasks
5. **Progressive Crystallization (2025)** — Agent exploration → deterministic workflows
6. **CacheRL (2026)** — Process accuracy metric for multi-step agents
7. **Ardimento et al. (2026)** — Clinical pathway PM (for medical application)

---

## Preliminary Direction Analysis

### The Big Picture

The intersection of PM × LLM is **very new** (most papers from 2024-2026). Two main directions exist:

1. **PM → LLM** (Cluster A1): Using LLMs to do PM better. Mature, led by van der Aalst's group.
2. **PM ← LLM** (Cluster A2): Using PM to analyze LLM agent behavior. Very sparse, only a handful of papers.

**Ryan's opportunity is in direction 2**, specifically:

### Proposed Research Story

```
[IRT/LCAE calibration] → [better self-assessment] → [better reasoning path quality] → [better token allocation]
         ↑                    ↑                          ↑                              ↑
     學姐 proven         學姐 proven              PM techniques measure this     Ryan's contribution
```

PM becomes the **measurement framework** for reasoning quality:
- **Process discovery:** What does a model's typical reasoning path look like for easy vs. hard questions?
- **Conformance checking:** When does a model deviate from the "optimal" reasoning path? (Overthinking = conformance deviation)
- **Performance analysis:** How does reasoning path length/complexity relate to token usage and accuracy?

### Why This Works

1. **Novel:** Nobody has connected PM to LLM reasoning quality / token efficiency
2. **Theoretically grounded:** PM has decades of formal methods (alpha miner, inductive miner, conformance checking)
3. **Practical:** PM tools (PM4Py) are open-source, ready to use
4. **Connects to advisor's interest:** 老師 explicitly mentioned Process Mining and medical pathways
5. **Extends 學姐's work:** Calibration → reasoning path quality → token allocation is a natural causal chain
6. **Not too big:** Using PM as analysis framework is scoped; building new PM algorithms is too much

### Potential Paper Title (Draft)

"Process-Aware Token Allocation: Mining LLM Reasoning Traces to Diagnose Calibration-Driven Efficiency"

or

"From Calibration to Process Quality: A Process Mining Approach to LLM Token Efficiency"

---

## Next Steps

1. Read the 7 key papers in detail (especially Berti 2024, BPOP, PMAx)
2. Look into PM4Py (Python process mining library) — can it ingest CoT traces as event logs?
3. Define the mapping: CoT step → event, question → case, model → variant
4. Design pilot experiment: take 5 models × 100 questions, extract reasoning traces, run PM analysis
5. Check if LCAE correlates with PM-derived reasoning path quality metrics