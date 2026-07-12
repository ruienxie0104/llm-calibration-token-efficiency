# Process Mining × LLM: Key Papers Summary

> Curated literature review for the Process Mining × LLM Token Efficiency research direction.
> 7 papers covering agentic process mining, trace de-linearization, workflow crystallization, cached RL, and clinical process mining.

---

## Paper 1: Re-Thinking Process Mining in the AI-Based Agents Era
- **arXiv ID:** 2408.07720
- **Authors:** Alessandro Berti et al.
- **Year:** 2024
- **URL:** https://arxiv.org/abs/2408.07720

### Core Problem
LLMs show promise for process mining (PM) tasks but struggle with complex scenarios requiring advanced reasoning. Existing approaches—textual insights from process abstractions or LLM-generated code on original artifacts—have limitations in handling complexity.

### Method
The paper proposes the AI-Based Agents Workflow (AgWf) paradigm for PM tasks. Key design principles: (1) decompose complex PM tasks into simpler sub-tasks forming a workflow, (2) integrate deterministic PM tools with LLM domain knowledge rather than relying on LLMs alone, (3) use the CrewAI framework for implementation. The approach treats LLMs as orchestrators that call specialized PM tools rather than trying to solve everything end-to-end.

### Key Findings
AgWf significantly improves PM effectiveness over direct LLM approaches by leveraging workflow decomposition and deterministic tool integration. The paper demonstrates that combining LLM reasoning with established PM tools (rather than replacing them) yields better results. The CrewAI implementation provides a concrete framework for building such multi-step PM pipelines.

### Relevance to Our Research
Directly relevant—establishes the paradigm of decomposing PM tasks into LLM-orchestrated workflows with deterministic tools. This is the foundation upon which frameworks like PMAx build. The AgWf paradigm implies that token efficiency gains come from proper task decomposition (simpler sub-tasks need fewer reasoning tokens) and tool reuse (deterministic execution avoids repeated LLM inference).

### Transferable Techniques
- Workflow decomposition as a token-efficiency strategy (complex → simple sub-tasks)
- Deterministic tool integration to reduce LLM reasoning overhead
- CrewAI framework for multi-agent PM orchestration
- Separation of LLM orchestration from PM computation

---

## Paper 2: PMAx: An Agentic Framework for AI-Driven Process Mining
- **arXiv ID:** 2603.15351
- **Authors:** Anton Antonov et al.
- **Year:** 2026
- **URL:** https://arxiv.org/abs/2603.15351

### Core Problem
Process mining requires expertise in specialized query languages and data science tools, limiting accessibility. Using LLMs as direct analytical engines over raw event logs introduces hallucination risks and privacy concerns when sending sensitive logs to external AI services.

### Method
PMAx employs a privacy-preserving multi-agent architecture with two specialized agents: (1) An **Engineer agent** that analyzes event-log metadata and autonomously generates local scripts to run established PM algorithms, compute exact metrics, and produce artifacts (process models, summary tables, visualizations); (2) An **Analyst agent** that interprets these artifacts to compile comprehensive reports. All computation runs locally, ensuring mathematical accuracy and data privacy. LLMs handle interpretation, not computation.

### Key Findings
By separating computation from interpretation, PMAx ensures mathematical accuracy while enabling non-technical users to transform high-level business questions into reliable process insights. Local execution eliminates privacy concerns. The framework demonstrates that LLMs are better used as interpreters of PM results than as direct analytical engines.

### Relevance to Our Research
PMAx's compute-interpret separation is a key token-efficiency pattern: LLMs generate code (few tokens) that runs deterministically (zero LLM tokens), then interpret results (moderate tokens) rather than trying to reason over raw event logs (many tokens with hallucination risk). The privacy-preserving local execution model is also relevant for sensitive domain applications.

### Transferable Techniques
- **Compute-interpret separation**: LLM generates code → code runs → LLM interprets results
- **Local script generation**: LLM writes PM analysis scripts instead of doing PM directly
- **Multi-agent architecture**: Engineer (code generation) + Analyst (interpretation)
- **Privacy-preserving execution**: All sensitive data stays local, only metadata shared with LLM
- **Artifact-based communication**: Agents exchange structured artifacts (tables, models, viz) rather than raw data

---

## Paper 3: De-Linearizing Agent Traces: Bayesian Inference of Latent Partial Orders for Efficient Execution (BPOP)
- **arXiv ID:** 2602.02806
- **Authors:** Dongqing Li, Zheqiao Cheng, Geoff K. Nicholls, Quyu Kong
- **Year:** 2026
- **URL:** https://arxiv.org/abs/2602.02806

### Core Problem
AI agents execute procedural workflows as sequential action traces, which obscures latent concurrency and induces repeated step-by-step reasoning. This linearization is inefficient—many steps could run in parallel if the underlying dependency structure were known, but it's hidden by the sequential trace format.

### Method
BPOP (Bayesian Partial Order from traces) is a Bayesian framework that infers a latent dependency partial order from noisy linearized traces. It models traces as stochastic linear extensions of an underlying graph and performs efficient MCMC inference via a tractable frontier-softmax likelihood that avoids #P-hard marginalization over linear extensions. Evaluated on Cloud-IaC-6 (a suite of cloud provisioning tasks with heterogeneous LLM-generated traces) and WFCommons scientific workflows.

### Key Findings
BPOP recovers dependency structure more accurately than trace-only and process-mining baselines. The inferred graphs support a compiled executor that prunes irrelevant context, yielding substantial reductions in token usage and execution time. This demonstrates that de-linearizing agent traces is a viable strategy for improving agent efficiency.

### Relevance to Our Research
Highly relevant—BPOP directly addresses token efficiency by inferring latent concurrency from agent traces and pruning unnecessary context. The process-mining connection is explicit: BPOP applies PM-style dependency discovery to LLM agent traces. The "compiled executor" concept (deterministic execution of inferred workflow) aligns with the crystallization pattern. Token reduction comes from context pruning based on dependency structure.

### Transferable Techniques
- **Bayesian trace de-linearization**: Infer latent partial orders from sequential agent traces
- **Frontier-softmax likelihood**: Tractable approximation avoiding #P-hard computation
- **Context pruning via dependency graphs**: Reduce token usage by identifying which context is irrelevant for each step
- **Compiled executor**: Convert inferred dependency graph into a deterministic execution plan
- **Cloud-IaC-6 benchmark**: Open-sourced cloud provisioning task suite for evaluation
- **MCMC inference for workflow discovery**: Probabilistic approach to process model discovery

---

## Paper 4: On the Potential of Large Language Models to Solve Semantics-Aware Process Mining Tasks
- **arXiv ID:** 2504.21074
- **Authors:** Adrian Rebmann, Fabian David Schmidt, Goran Glavaš, Han van der Aa
- **Year:** 2025
- **URL:** https://arxiv.org/abs/2504.21074

### Core Problem
Process mining tasks increasingly require understanding the semantic meaning of activities and their relationships (e.g., inferring dependencies from activity names, recognizing anomalous behavior from semantics). Can LLMs leverage their semantic understanding to solve these semantics-aware PM tasks?

### Method
The paper systematically explores LLM capabilities for five semantics-aware PM tasks through both in-context learning and supervised fine-tuning. The authors define five tasks requiring semantic understanding (including process discovery, anomaly detection) and provide extensive benchmarking datasets. They evaluate LLMs in their default state, with in-context examples, and after fine-tuning, across a broad range of process types and industries.

### Key Findings
LLMs struggle with challenging PM tasks when used out-of-the-box or with minimal in-context examples. However, they achieve strong performance when fine-tuned for these tasks across diverse process types and industries. This reveals a key tension: LLMs have semantic understanding potential, but it requires task-specific training to unlock. The five-task benchmark provides a standardized evaluation framework.

### Relevance to Our Research
Directly relevant to the token efficiency question: fine-tuning (high upfront cost, low inference cost) vs. in-context learning (zero upfront cost, high inference cost with many examples). The five-task taxonomy helps us understand which PM tasks benefit from LLM semantic understanding and which require deterministic tools. The benchmark datasets enable evaluation of token-efficiency approaches.

### Transferable Techniques
- **Five semantics-aware PM tasks**: Standardized task taxonomy for evaluating LLM-based PM
- **Fine-tuning vs. in-context learning trade-off**: Upfront cost vs. inference cost analysis
- **Benchmarking datasets**: Extensive datasets for PM task evaluation across industries
- **Semantic understanding taxonomy**: Classification of which PM tasks benefit from LLM semantics
- **Task difficulty calibration**: Matching LLM capability to PM task complexity

---

## Paper 5: Progressive Crystallization: Turning Agent Exploration into Deterministic, Lower-Cost Workflows in Production
- **arXiv ID:** 2607.07052
- **Authors:** Arun Malik
- **Year:** 2026
- **URL:** https://arxiv.org/abs/2607.07052

### Core Problem
AI agents deployed for IT operations are permanent cost centers—every execution requires full LLM inference, even for previously solved problems. This makes agent-based approaches economically unsustainable at scale.

### Method
Progressive crystallization defines a three-stage execution taxonomy: (1) fully agent-orchestrated, (2) hybrid, (3) fully deterministic workflows. An evidence-based promotion mechanism converts repeatedly validated agent behaviors into cheaper, more reproducible deterministic workflows, while automatically demoting workflows that regress. The system was evaluated on a production cloud networking AIOps system processing tens of thousands of incidents per month over eight months.

### Key Findings
The approach increased deterministic execution from 0% to 45% over eight months, reduced per-incident agent costs by more than 70% despite doubling incident volume, and improved safety through greater reproducibility and auditability. The promotion/demotion mechanism ensures that crystallized workflows remain correct as systems evolve. The economic model demonstrates that progressive crystallization is a viable strategy for making agent-based systems cost-effective at production scale.

### Relevance to Our Research
Core paper for our token efficiency direction—crystallization is essentially a token cost amortization strategy. Initial exploration (high token cost) is amortized over many subsequent deterministic executions (near-zero token cost). The three-stage taxonomy (agent → hybrid → deterministic) maps directly to a token efficiency spectrum. The 70% cost reduction provides a strong empirical baseline for expected gains.

### Transferable Techniques
- **Three-stage execution taxonomy**: Agent → hybrid → deterministic (token cost spectrum)
- **Evidence-based promotion**: Convert validated agent behaviors to deterministic workflows
- **Automatic demotion**: Revert to agent execution when deterministic workflow regresses
- **Trace extraction methodology**: Extract workflow patterns from agent execution traces
- **Economic model**: Cost comparison between agent and deterministic execution
- **Safety through reproducibility**: Deterministic workflows are auditable and repeatable
- **70% cost reduction benchmark**: Empirical target for token efficiency approaches

---

## Paper 6: CacheRL: Multi-Turn Tool-Calling Agents via Cached Rollouts and Hybrid Reward
- **arXiv ID:** 2606.14179
- **Authors:** Md Amirul Islam, Sumiran Thakur, Huancheng Chen, Su Min Park, Jiayun Wang, Gyuhak Kim
- **Year:** 2026
- **URL:** https://arxiv.org/abs/2606.14179

### Core Problem
Training small agent models for multi-step tool-calling tasks faces three challenges: (1) transferring tool-calling knowledge from large models at scale, (2) enabling reinforcement learning without costly live tool execution, (3) learning robustly from noisy cached environments.

### Method
CacheRL introduces three innovations: (1) A **hybrid thinking trajectory pipeline** that augments agent trajectories with LLM-generated reasoning traces, teaching models not only what tools to call but also why; (2) **CacheAgentLoop** that eliminates live execution costs through a three-tier fuzzy cache while preserving trajectory fidelity via token-level masking; (3) **Cache-tier-aware reward** that dynamically adjusts answer-quality weights to avoid penalizing models for cache-induced limitations. Training uses iterative SFT and GRPO on Qwen3-4B-Thinking.

### Key Findings
CacheRL achieves 92% process accuracy on multi-step tool-calling tasks, approaching GPT-5's 94% while requiring 100× less compute. Improves Qwen3-4B-Thinking's validation reward from 0.43 to 0.78. Ablation shows: removing knowledge transfer reduces performance by 41%, cache-aware rewards contribute 17% improvement. Notably, RL improves training stability but yields limited gains beyond strong SFT, suggesting data quality and reward design matter more than complex optimization.

### Relevance to Our Research
CacheRL directly addresses token efficiency in agent training and execution. The three-tier fuzzy cache eliminates redundant tool execution (similar to crystallization but at the tool-call level). The 100× compute reduction vs. frontier models demonstrates that small models with good training can match much larger ones for structured tasks. The finding that SFT > RL for practical gains is important for cost-effective training strategies.

### Transferable Techniques
- **Three-tier fuzzy cache**: Eliminate redundant tool execution at different granularity levels
- **Hybrid thinking trajectories**: Augment traces with reasoning ("why" not just "what")
- **Token-level masking**: Preserve trajectory fidelity when using cached results
- **Cache-tier-aware reward**: Adjust quality metrics based on cache reliability
- **SFT > RL insight**: Strong supervised fine-tuning may be more cost-effective than complex RL
- **Small model competitiveness**: 4B model matching frontier models with proper training
- **Process accuracy metric**: Standardized evaluation for multi-step tool-calling

---

## Paper 7: Improving Hospital Process Management through Process Mining: A Case Study on COVID-19 Clinical Pathways
- **arXiv ID:** 2606.00041
- **Authors:** Pasquale Ardimento, Mario Luca Bernardi, Marta Cimitile, Samuele Latorre
- **Year:** 2026
- **URL:** https://arxiv.org/abs/2606.00041

### Core Problem
Hospital processes, particularly for complex conditions like COVID-19, involve heterogeneous clinical data that is difficult to analyze. There is a need for transparent, reproducible pipelines that transform clinical data into process-mining-ready event logs for actionable insights.

### Method
The study uses the COVID Data for Shared Learning dataset and builds a transparent, reproducible pipeline that transforms heterogeneous clinical tables into a process-mining-ready event log. It applies discovery, declarative conformance checking, and outcome analysis to reconstruct COVID-19 care pathways and analyze variability and outcomes.

### Key Findings
The reconstructed pathways highlight the monitoring backbone of inpatient care, variability at the Emergency department-admission interface, and outcome differences driven by age and ICU exposure. These insights support triage standardization, capacity planning, and step-down coordination from ICU to lower-acuity wards. The work demonstrates how PM can inform evidence-based hospital governance.

### Relevance to Our Research
This paper provides a concrete application domain for PM techniques. While not LLM-focused, it shows the complexity of real-world event logs and the value of PM insights. For our token efficiency research, this represents the type of domain where LLM-assisted PM could democratize analysis (as envisioned by PMAx). The heterogeneous data transformation pipeline is a candidate for LLM-orchestrated automation.

### Transferable Techniques
- **Heterogeneous data → event log pipeline**: Template for transforming raw domain data into PM-ready format
- **Declarative conformance checking**: Complement to discovery for compliance analysis
- **Clinical pathway analysis**: Domain-specific PM application pattern
- **Outcome-based process analysis**: Link process variants to outcomes (age, ICU exposure)
- **Hospital governance insights**: How PM translates to actionable healthcare management
- **Reproducible pipeline design**: Transparent, auditable PM pipeline architecture

---

## Synthesis: What These 7 Papers Tell Us

### The Big Picture

These seven papers converge on a fundamental insight: **the future of process mining with LLMs is not about replacing PM tools with LLMs, but about orchestrating LLMs to generate, execute, and interpret PM workflows efficiently.** The key patterns that emerge across the literature are:

1. **Compute-Interpret Separation** (PMAx, Berti): LLMs should generate code and interpret results, not compute directly. This reduces hallucination risk and token consumption by letting deterministic tools handle computation.

2. **Trace-to-Workflow Conversion** (BPOP, Progressive Crystallization): Agent execution traces can be analyzed to discover latent dependency structures, which are then converted into deterministic workflows—reducing future token costs by 70%+.

3. **Small Model Competitiveness** (CacheRL): Properly trained small models (4B parameters) can match frontier models on structured PM tasks with 100× less compute, especially when supported by caching and SFT.

4. **Semantic Understanding Gap** (Rebmann et al.): LLMs have latent semantic understanding of process activities, but unlocking it requires fine-tuning. Out-of-the-box performance is insufficient for complex PM tasks.

5. **Domain Applications Validate the Approach** (Ardimento et al.): Real-world clinical pathway analysis demonstrates the value and complexity of PM, motivating LLM-assisted democratization of PM tools.

### Largest Research Gap

The most significant gap is **the absence of a unified framework that connects trace analysis, workflow crystallization, and token cost optimization in a single system.** Each paper addresses a piece:

- BPOP discovers latent dependencies but doesn't connect to progressive crystallization
- Progressive Crystallization converts traces to workflows but doesn't use PM techniques for discovery
- CacheRL reduces tool-call costs but doesn't leverage PM for workflow analysis
- PMAx separates compute from interpretation but doesn't crystallize repeated patterns
- Rebmann et al. explores LLM semantics but doesn't address cost/efficiency

**No paper combines process mining (as an analytical method on agent traces) with LLM token efficiency (as an optimization target).** This is the intersection where our research can position.

Specifically, there is no work that:
- Uses PM techniques to analyze LLM agent execution traces for efficiency patterns
- Measures token cost as a first-class metric in PM-driven workflow optimization
- Applies the crystallization lifecycle with PM-based promotion criteria
- Evaluates the trade-off between LLM reasoning quality and token cost across different PM task decomposition strategies

### Our Positioning Strategy

We should position our research at the intersection of three streams:

1. **Process Mining for Agent Traces**: Apply PM techniques (discovery, conformance checking, enhancement) to LLM agent execution traces—treating agent traces as event logs. This is methodologically novel: most PM work analyzes business processes, not AI agent behavior.

2. **Token Efficiency as PM Optimization Target**: Define token cost as a process performance indicator and use PM-based analysis to identify inefficiencies (redundant reasoning, unnecessary context, repeatable sub-tasks). This bridges the gap between PM (process optimization) and LLM efficiency (token optimization).

3. **Progressive Crystallization with PM-based Promotion**: Use PM-derived metrics (conformance, frequency, success rate) as evidence for promoting agent behaviors to deterministic workflows. This grounds the crystallization decision in objective process analysis rather than ad-hoc thresholds.

Our contribution: a PM-driven framework for LLM agent token efficiency that (a) discovers workflows from agent traces using PM techniques, (b) measures token cost per workflow pattern, and (c) progressively crystallizes high-frequency, high-cost patterns into deterministic execution—reducing token consumption while maintaining task quality.