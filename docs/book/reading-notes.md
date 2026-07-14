# Reading Notes: Process Mining — Data Science in Action

**Author:** Wil M.P. van der Aalst  
**Publisher:** Springer, 2016  
**Status:** Completed (key chapters 1–12; chapters 13–16 browsed for key ideas)

---

## Book Structure (from Table of Contents)

The book is organized into six parts across 16 chapters (477 pages):

- **Part I: Introduction**
  - Ch 1: Data Science in Action (pp. 20–40)
  - Ch 2: Process Mining: The Missing Link (pp. 41–68)
- **Part II: Preliminaries**
  - Ch 3: Process Modeling and Analysis (pp. 71–104)
  - Ch 4: Data Mining (pp. 105–137)
- **Part III: From Event Data to Process Models**
  - Ch 5: Getting the Data (pp. 140–177)
  - Ch 6: Process Discovery: An Introduction (pp. 178–209)
  - Ch 7: Advanced Process Discovery Techniques (pp. 210–255)
- **Part IV: Conformance Checking**
  - Ch 8: Conformance Checking (pp. 258–289)
- **Part V: Process Mining Beyond Control Flow**
  - Ch 9: Mining Additional Perspectives (pp. 290–315)
  - Ch 10: Operational Support (pp. 316–336)
- **Part VI: Process Mining in Practice**
  - Ch 11: Process Mining Software (pp. 339–366)
  - Ch 12: Process Mining in the Large (pp. 367–390)
  - Ch 13: Analyzing "Lasagna" Processes (pp. 391–406)
  - Ch 14: Analyzing "Spaghetti" Processes (pp. 407–422)
  - Ch 15: Process Cartography (pp. 423–446)
  - Ch 16: Epilogue (pp. 447–458)

---

## Chapter Summaries

### Chapter 1: Data Science in Action

The chapter frames data science as the intersection of process science and data science. The "Internet of Events" — the growing availability of event data from RFID, GPS, sensors, transaction logs, etc. — is a key enabler. Van der Aalst identifies a gap: data science approaches tend to be process-agnostic, while process science focuses on modeling without leveraging data. Process mining bridges this gap.

**Key concepts:**
- **Data science vs. process science**: Data science is data-centric; process science is model-centric. Process mining is both.
- **Four V's of Big Data**: Volume, Velocity, Variety, Veracity — all relevant to event data.
- **Process mining definition**: Using event data to discover, conformance-check, and enhance process models.
- **Three types of process mining**: Discovery (build model from data), Conformance (compare model vs. data), Enhancement (extend model with data).
- **Yin-yang of data and process**: Data-driven and process-centric forces need to be balanced.

**Research relevance:** The framing of PM as a bridge between data science and process science maps directly to our research — we're bridging ML/LLM analysis (data-driven) with structured process analysis (process-centric). LLM reasoning traces are "event data" waiting to be process-mined.

### Chapter 2: Process Mining: The Missing Link

Introduces the core PM framework. Uses a running example (handling complaints at a municipal authority) to illustrate event logs, process models, and the Play-In / Play-Out / Replay triad.

**Key concepts:**
- **Play-In**: From example behavior → process model (discovery).
- **Play-Out**: From process model → example behavior (simulation/execution).
- **Replay**: Both model + log → analysis (conformance checking, bottleneck analysis).
- **Event log structure**: Each event has a case ID, activity name, timestamp, and optionally resource, cost, etc.
- **Orthogonal perspectives**: Control-flow ("How?"), Organizational ("Who?"), Case/Data ("What?"), Time ("When?").
- **Positioning vs. related fields**: BPM, data mining, BI, Lean Six Sigma, BPR, CEP, GRC, ABPD, Big Data — PM is distinct from all of these but overlaps with each.
- **De jure vs. de facto models**: Normative (should-be) vs. descriptive (as-is) models.

**Research relevance:** Play-In/Play-Out/Replay maps to our research: Play-In = discover reasoning patterns from CoT traces; Replay = compare expected reasoning protocol against actual traces; Play-Out = generate expected reasoning paths for a given question type. The multi-perspective framing (How/Who/What/When) suggests we can analyze not just "what steps" but "what token budget per step", "what error type", etc.

### Chapter 3: Process Modeling and Analysis

Surveys modeling notations: transition systems, Petri nets, Workflow nets (WF-nets), YAWL, BPMN, EPCs, Causal Nets, Process Trees. Also covers model-based analysis (verification, soundness, invariants).

**Key concepts:**
- **Transition systems**: Simplest formal model — states and transitions. Basis for many discovery algorithms.
- **Petri nets and WF-nets**: Token-based formalism with places, transitions, arcs. WF-nets have a single source and sink place. **Soundness** property: every case can complete, no dead transitions, no tokens left.
- **BPMN**: De facto standard for process modeling; has gateways (AND, XOR, OR), events, activities.
- **Process Trees**: Recursive structure (operator + children): seq(→), choice(×), parallel(∧), loop(↺). Always sound by construction. Key for inductive mining.
- **Causal Nets (C-nets)**: Activity-based model with input/output bindings; allows expressing non-local dependencies.
- **Workflow patterns**: 40+ control-flow patterns (sequence, parallel split, synchronization, exclusive choice, etc.) — a vocabulary for representational bias.
- **Model-based analysis**: Invariants, deadlocks, soundness checking. LTL-based verification.

**Research relevance:** Process trees are particularly interesting for modeling LLM reasoning patterns — their recursive structure (seq, choice, parallel, loop) maps naturally to reasoning operations. E.g., a reasoning trace might be seq(decompose, parallel(solve_sub1, solve_sub2), combine). The soundness property could be adapted to define "valid" reasoning traces. BPMN gateways (AND/XOR/OR) could model branching in reasoning strategies.

### Chapter 4: Data Mining

Covers classical data mining techniques: classification, clustering, association rule learning, sequence mining. Explains why traditional data mining alone is insufficient for process mining (it ignores the ordering/behavioral aspect).

**Key concepts:**
- **Classification**: Decision trees, k-NN, SVM, neural networks. Maps features → labels.
- **Clustering**: k-means, hierarchical clustering, SOM. Groups similar instances.
- **Association rule learning**: Apriori algorithm, support, confidence. Finds "if X then Y" rules.
- **Sequence mining**: GSP, SPADE, PrefixSpan. Mines sequential patterns from sequences.
- **Frequent episodes**: Mining partial orders using a sliding window.
- **Limitations for PM**: Data mining works on "flat" tables; loses the process/event notion. Cannot discover end-to-end process models. Cannot do conformance checking. No notion of cases, ordering, or concurrency.

**Research relevance:** Clustering (trace clustering) is directly applicable: group similar LLM reasoning traces to find distinct reasoning strategies. Decision tree learning can be used for decision mining — what features predict correct vs. incorrect answers. Sequence mining can discover common reasoning patterns. But the key insight is the same as van der Aalst's: these techniques lose the process structure. PM provides the framework to preserve it.

### Chapter 5: Getting the Data

Covers data sources, event log extraction, the XES standard, data quality, and preprocessing. This is the "data engineering" chapter.

**Key concepts:**
- **Event log requirements**: Each event needs at minimum: case ID, activity, timestamp. Resource, cost, and other attributes are optional.
- **Correlation**: Events must be correlated to cases — this is non-trivial. Requires domain knowledge.
- **Transactional lifecycle**: Events have types (start, complete, suspend, resume, abort, etc.). An activity instance may generate multiple events.
- **XES standard**: IEEE standard for event log exchange. Extensible: attributes can be added freely. Uses classifiers to map events to activities.
- **Data quality issues**: Incompleteness (missing events), noise (infrequent/exceptional behavior), volatility (process changes over time — concept drift), cross-organization.
- **Concept drift**: The process changes while you're observing it. Must detect and handle.
- **Dotted chart**: Visual analytics tool — events as dots in 2D (time × class), color/shape encode attributes. Provides a "helicopter view" before formal analysis.

**Research relevance:** The event log mapping is critical. For LLM reasoning traces:
- **Case ID** = question ID (or question + model ID)
- **Activity** = reasoning step type (e.g., "decompose", "compute", "verify", "answer")
- **Timestamp** = token position or generation order (note: this is tricky — LLM reasoning is sequential, not wall-clock)
- **Resource** = model name / parameter count
- **Attributes** = token count per step, confidence score, error type, prompt length

Data quality issues also apply: incomplete traces (truncated CoT), noise (unusual reasoning paths), concept drift (model updates). The dotted chart idea could be adapted to visualize reasoning traces — x-axis = token position, y-axis = question ID, color = step type.

### Chapter 6: Process Discovery: An Introduction

Introduces process discovery through the α-algorithm. Defines the core problem and quality dimensions.

**Key concepts:**
- **α-algorithm**: First PM discovery algorithm. Builds a Petri net from the "directly-follows" relation (>L) in the event log. Works for a restricted class of WF-nets.
- **Four quality dimensions**:
  - **Fitness**: Can the log be replayed by the model? (proportion of observed behavior the model allows)
  - **Precision**: Does the model not allow too much? (no underfitting — model shouldn't permit unseen behavior)
  - **Generalization**: Does the model generalize beyond the log? (no overfitting — new traces should fit)
  - **Simplicity**: Is the model simple? (Occam's razor — fewer nodes/arcs)
- **Directly-follows relation**: a >L b iff there's a case where a is immediately followed by b.
- **Limitations of α-algorithm**: Cannot handle short loops, duplicate activities, non-free-choice constructs, noise. Despite limitations, it illustrates the core ideas.
- **Noise definition**: Infrequent or exceptional behavior. The 80/20 model: 80% of behavior explained by a simple model; the remaining 20% accounts for most variability.
- **Causalities in α-algorithm**: a →L b (a causes b), a #L b (a and b never follow each other), a ||L b (a and b can be in any order = parallel).

**Research relevance:** The four quality dimensions are directly applicable to evaluating discovered reasoning trace models:
- **Fitness**: Does the discovered reasoning model explain the observed CoT traces?
- **Precision**: Does the model avoid permitting impossible reasoning sequences?
- **Generalization**: Does the model generalize to new questions (not just memorized ones)?
- **Simplicity**: Is the reasoning pattern simple (efficient)?

The α-algorithm's directly-follows relation could be used to discover "which reasoning step typically follows which" from CoT traces. The 80/20 principle is relevant — most reasoning traces likely follow common patterns, with a long tail of exceptional traces.

### Chapter 7: Advanced Process Discovery Techniques

Surveys the main families of discovery algorithms beyond α-miner. Discusses their strengths, weaknesses, and representational biases.

**Key concepts:**
- **Representational bias**: The class of models an algorithm can discover. Determines the search space. Limitations include inability to represent concurrency, loops, silent actions, duplicate actions, OR-splits, non-free-choice constructs, hierarchy.
- **Four families of approaches**:
  1. **Direct algorithmic** (α-algorithm, language-based regions): Extract footprint → construct model directly.
  2. **Two-phase** (transition system + state-based regions): Build low-level model → convert to high-level model.
  3. **Divide-and-conquer** (inductive miner): Recursively split the log → structured process tree.
  4. **Computational intelligence** (genetic mining, ant colony optimization): Evolutionary approach — iteratively improve candidate models.
  5. **Partial approaches** (frequent episodes, declarative mining): Focus on patterns/rules rather than end-to-end models.
- **Heuristic mining**: Uses a dependency graph with frequencies. Handles noise by thresholding. Produces heuristic nets. More robust than α-algorithm.
- **Genetic process mining**: Population of candidate models evolves via crossover/mutation. Fitness = how well model replays log. Handles noise and incompleteness. Slow.
- **Region-based mining**:
  - **State-based regions**: Build transition system from log → synthesize Petri net via region theory.
  - **Language-based regions**: Convert log to inequation system → solve for Petri net places. ILP-based.
- **Inductive miner (IM)**: Recursively finds cuts (seq, choice, parallel, loop) in the log → splits log → recurses. Always produces sound models. Scalable. Variants: IMF (handles infrequent), IMC (handles concurrency), IMD (directly-follows graph based).
- **Fuzzy miner**: For unstructured processes. Groups related low-frequency activities into subprocesses. Produces hierarchical models.

**Research relevance:** 
- **Inductive miner** is most promising for our research: it produces sound, structured process trees, handles noise, and is scalable. Reasoning patterns naturally decompose into seq/choice/parallel/loop — exactly what process trees express.
- **Heuristic mining** with frequency thresholds could identify "common" reasoning patterns vs. rare deviations.
- **Genetic mining** could explore the space of possible reasoning protocols.
- The representational bias discussion is crucial: we need to choose a representation that can express the reasoning patterns we expect (loops for iterative refinement, choices for strategy selection, parallel for concurrent sub-problems).

### Chapter 8: Conformance Checking

Covers techniques to compare a process model against an event log. Introduces token replay and alignments — the two main approaches.

**Key concepts:**
- **Conformance checking purpose**: Business alignment (does reality match the model?) and auditing (are rules being followed?).
- **Token replay**: Replay the log on the Petri net, count missing/remaining/consumed/produced tokens.
  - **Fitness metric**: (consumed + produced) / (consumed + produced + missing + remaining). Range [0, 1].
  - Simple but has limitations: cannot handle non-unique activity labels, may produce misleading diagnostics.
- **Alignments**: Optimal matching of log trace to model path. Minimizes edit distance (move in log, move in model, synchronous move).
  - Provides precise diagnostics: exact location and type of deviation.
  - Computationally expensive (requires solving optimization problems).
- **Four quality dimensions revisited**:
  - Fitness ≈ proportion of log behavior the model can explain.
  - Precision ≈ how much extra behavior the model allows (behavioral appropriateness).
  - Generalization ≈ ability to handle unseen traces (related to model simplicity vs. fitness trade-off).
  - Simplicity ≈ model size / complexity.
- **Model repair**: Using conformance diagnostics to fix the model (add/remove/modify edges).
- **Footprint comparison**: Compare >L relations of log and model. Coarse but fast for model-to-model comparison.
- **Squeezing reality into the model**: Even non-fitting cases are mapped to model paths, enabling performance analysis (bottleneck, waiting time) on the full log.

**Research relevance:** Conformance checking is a core technique for our research:
- **Token replay** could compare an expected reasoning protocol (model) against actual CoT traces (log). Deviations = reasoning errors or unexpected strategies.
- **Alignments** provide precise diagnostics: which reasoning step was skipped, added, or replaced. This could identify specific types of reasoning failures.
- **Footprint comparison** could quickly compare two reasoning models (e.g., expected vs. discovered, or model A vs. model B).
- **Squeezing reality into the model** is relevant for analyzing performance (token efficiency) even when traces don't perfectly match the expected protocol.
- Conformance metrics (fitness, precision) could be used to evaluate how well a given LLM follows a reasoning protocol.

### Chapter 9: Mining Additional Perspectives

Covers organizational mining, time perspective analysis (bottlenecks, service levels), and case/data perspective (decision mining).

**Key concepts:**
- **Organizational mining**:
  - **Social network analysis**: Build networks from event logs. Mining metrics:
    - **Handover of work**: How often does resource A's activity get followed by resource B's activity?
    - **Working together**: Do A and B work on the same case simultaneously?
    - **Similar task**: Do A and B perform similar sets of activities?
  - **Role discovery**: Cluster resources based on activity profiles → discover organizational roles.
  - **Organizational structure**: Discover hierarchical relationships.
- **Time perspective**:
  - **Bottleneck analysis**: Identify activities with long waiting/processing times. Replay log on model, compute sojourn times per activity.
  - **Service levels**: Measure time between request and completion per activity.
  - **Resource utilization**: How busy is each resource over time?
  - **Flow time analysis**: Decompose into waiting time, processing time, and transfer time.
- **Decision mining**:
  - At XOR-splits, discover decision rules using classification (decision tree learning).
  - Features = case attributes at decision point; label = which branch was taken.
  - Produces guards: "if amount > 1000 then thorough examination, else casual examination."
- **Integrated model**: Combine control-flow + organizational + time + data into a single simulation model. Enables "what-if" analysis.
- **Dotted chart revisited**: Events as dots, 2D = time × class, color/shape = attributes. Visual analytics before formal analysis.

**Research relevance:**
- **Organizational mining → "Resource" perspective for LLM**: If we tag resource = model name, social network analysis could reveal "which models produce similar reasoning patterns" or "which reasoning steps tend to follow each other across models." Handover of work = transition between reasoning phases.
- **Decision mining → "Strategy selection"**: At choice points in reasoning, what features predict which branch is taken? E.g., "if problem type = math then use decompose-then-solve, else use direct reasoning." Decision trees on case attributes (question type, difficulty, prompt length) → predict reasoning strategy.
- **Time perspective → "Token efficiency"**: Bottleneck analysis directly maps to token efficiency — which reasoning steps consume the most tokens? Waiting/processing time analog → token budget per step. Flow time = total token count.
- **Integrated model → "Comprehensive reasoning model"**: A combined model could express control-flow (reasoning steps) + time (token cost) + data (problem features) + organizational (model identity). This is exactly what we need for a complete analysis.

### Chapter 10: Operational Support

Extends PM from offline analysis to online/real-time support. Introduces the refined PM framework with pre mortem / post mortem data and de jure / de facto models.

**Key concepts:**
- **Refined PM framework**: 10 activities grouped into Cartography (discover, enhance, diagnose), Auditing (detect, check, compare, promote), and Navigation (explore, predict, recommend).
- **Pre mortem vs. post mortem data**: Pre mortem = running cases (can still be influenced); post mortem = completed cases (for analysis only).
- **De jure vs. de facto models**: Normative (should-be) vs. descriptive (as-is). De facto models are discovered; de jure models are designed.
- **Detect**: Compare partial trace against normative model → alert on violations in real-time.
- **Predict**: Use historic data + current partial trace → predict remaining flow time, probability of success, etc.
  - approaches: annotation-based (features from partial trace → regression), state-based (similar completed cases), model-based (replay + simulation).
- **Recommend**: Based on predictions, suggest next action to optimize outcome (minimize time, maximize success).
- **Partial traces**: Running cases produce partial traces σp = ⟨a, b, ...⟩. The future is unknown.
- **Business process provenance**: Systematic, reliable, trustworthy recording of events. Essential for reliable analysis.

**Research relevance:**
- **Detect → "Reasoning deviation detection"**: During generation, check if partial CoT trace deviates from expected protocol. Could enable real-time intervention (e.g., trigger re-prompting).
- **Predict → "Outcome prediction from partial reasoning"**: Given a partial CoT trace, predict whether the final answer will be correct, and estimate remaining token cost. This is highly relevant — early detection of doomed reasoning chains could save tokens.
- **Recommend → "Next-step recommendation"**: Suggest the optimal next reasoning step to maximize correctness or minimize tokens. This connects to the token efficiency research goal.
- **Pre mortem data** = during generation (streaming tokens); **post mortem data** = completed reasoning traces. The distinction is important: we can analyze completed traces offline, but real-time detection/prediction during generation requires pre mortem analysis.

### Chapter 11: Process Mining Software

Surveys PM tools: ProM (open-source, 1500+ plug-ins), and 11 commercial tools (Celonis, Disco, etc.). Discusses strengths and weaknesses.

**Key concepts:**
- **ProM**: Leading open-source platform. Supports discovery, conformance, organizational mining, decision mining, operational support. 1500+ plug-ins. Steep learning curve.
- **Commercial tools**: Easier to use, better scalability, but limited functionality (especially no proper concurrency discovery, limited conformance checking, no decision mining).
- **Three types of use cases**: Type 1 (ad-hoc, flexible), Type 2 (repeated, semi-configured), Type 3 (standard, fixed dashboards).
- **Key weaknesses of commercial tools**:
  - Limited support for concurrency (parallel activities often shown as loops)
  - Limited conformance checking (no alignments, only rule-based filtering)
  - No data-aware models (no decision mining)
  - No automatic clustering
  - Limited operational support
- **RapidProM**: Extension of RapidMiner with ProM plug-ins. Enables analysis workflows. Good for large-scale experiments.

**Research relevance:** For our research, ProM is the most suitable tool — it supports all the techniques we need (inductive miner, alignments, decision mining, trace clustering). RapidProM could be used for automating experiments. The identified gaps in commercial tools (no concurrency, no conformance, no decision mining) are also gaps in current LLM reasoning analysis tools — our research could help fill this gap.

### Chapter 12: Process Mining in the Large

Covers scalability: Big Event Data, MapReduce, decomposition strategies (case-based and activity-based), streaming PM, and process cubes.

**Key concepts:**
- **Big Event Data**: Event logs can have billions of events. Scalability depends on log characteristics, not just size.
- **Event log metrics**: #cases, average trace length, #distinct activities, #distinct cases, #events, #direct successions, #start/end activities, set-based non-overlap of traces. These metrics determine complexity.
- **Case-based decomposition (vertical partitioning)**: Split log by cases → distribute to compute nodes → merge results. Works for algorithms based on counting local patterns (α-algorithm, heuristic miner, inductive miner based on directly-follows graph).
- **Activity-based decomposition (horizontal partitioning)**: Split log by activity sets → each sublog is a projection onto a subset of activities → analyze sublogs independently → merge models. Works for algorithms that are exponential in the number of activities.
- **MapReduce for PM**: Map function emits (direct succession, 1) pairs; Reduce function sums per key. Directly-follows graph can be computed in a single MapReduce pass.
- **Streaming PM**: Process events as they arrive (not storing all). Sliding window approaches. Relevant for real-time monitoring.
- **Process cubes**: OLAP-style multidimensional analysis of event data. Dimensions = case attributes (time, region, product type, etc.). Enables slicing and dicing the event log.
- **Bonferroni's principle**: In large datasets, rare events appear frequently by chance. Be cautious of false positives when searching for patterns in massive logs.

**Research relevance:**
- **Scalability**: Our LLM reasoning trace datasets could be large (thousands of questions × hundreds of traces each). Case-based decomposition is directly applicable — each question's reasoning trace is independent.
- **MapReduce**: Computing directly-follows graphs for reasoning traces can be done with MapReduce. Map = emit (step_i → step_i+1, 1) per trace; Reduce = sum frequencies.
- **Event log metrics** are useful for characterizing our reasoning trace datasets: #questions (cases), average reasoning length (trace length), #distinct step types (activities), #distinct traces (unique reasoning paths), set-based non-overlap (diversity of reasoning strategies).
- **Process cubes**: Could enable multi-dimensional analysis of reasoning traces — dimensions = question type, difficulty, model, prompt strategy, etc. Slice and dice to compare reasoning patterns across dimensions.
- **Bonferroni's principle**: When searching for common reasoning patterns in large trace datasets, be cautious of spurious patterns.

### Chapters 13–14: Lasagna vs. Spaghetti Processes (Browsed)

- **Lasagna processes**: Highly structured, predictable, well-organized. Few distinct paths. Easy to model and analyze. Most processes in controlled environments (manufacturing, administrative workflows).
- **Spaghetti processes**: Unstructured, highly variable, many distinct paths. Difficult to model — discovered models are "spaghetti-like." Common in healthcare, knowledge work, creative processes.
- **Key insight**: The more unstructured a process, the more important it is to use decomposition, clustering, and abstraction techniques.
- **For Spaghetti**: Use trace clustering to group similar cases, discover multiple simple models instead of one complex one. Fuzzy miner for hierarchical abstraction.

**Research relevance:** LLM reasoning traces are likely **Spaghetti** — highly variable, many distinct paths, unstructured. This means:
- We should use trace clustering first (group similar reasoning traces) before discovery.
- Fuzzy miner or inductive miner with abstraction is more appropriate than α-algorithm.
- Multiple simple models (one per cluster) will be more useful than one complex model.
- The Lasagna/Spaghetti distinction gives us a vocabulary: "Is LLM reasoning a Lasagna or Spaghetti process?" (Likely Spaghetti, but may become more Lasagna-like with structured prompting.)

### Chapters 15–16: Process Cartography & Epilogue (Browsed)

- **Process cartography**: Analogy to geographic maps — process models are maps of organizational behavior. Different scales, resolutions, and perspectives for different stakeholders.
- **Epilogue**: PM is maturing. Growing adoption in industry. Future directions: streaming PM, PM for ML/AI, combining PM with simulation.
- Van der Aalst explicitly mentions the potential of PM for analyzing "non-business processes" including software processes and AI systems.

---

## Key Concepts for Our Research

### Concepts directly relevant to LLM reasoning trace analysis

1. **Event log as the universal interface**: PM requires events with (case ID, activity, timestamp, + optional attributes). LLM reasoning traces can be formatted as event logs with:
   - Case ID = (question_id, model_id)
   - Activity = reasoning step type
   - Timestamp = token position (sequential ordering)
   - Resource = model name
   - Attributes = token count, confidence, error type

2. **Three types of PM → Three types of reasoning analysis**:
   - **Discovery**: Discover reasoning patterns from CoT traces
   - **Conformance**: Check if actual reasoning follows expected protocol
   - **Enhancement**: Extend reasoning models with token cost, error analysis, performance metrics

3. **Four quality dimensions for reasoning models**:
   - Fitness: Does the model explain observed traces?
   - Precision: Does the model avoid permitting invalid reasoning?
   - Generalization: Does the model generalize to new questions?
   - Simplicity: Is the reasoning pattern efficient?

4. **Multi-perspective analysis**: PM's orthogonal perspectives map to reasoning analysis:
   - Control-flow: What reasoning steps and in what order?
   - Organizational: Which model/configuration produces which patterns?
   - Time (token): How many tokens per step? Total? Bottlenecks?
   - Case/Data: What question features predict which reasoning strategy?

5. **Conformance checking for reasoning validation**: Alignments can precisely identify where and how a reasoning trace deviates from the expected protocol. This enables fine-grained error analysis.

6. **Operational support for real-time reasoning monitoring**: Detect deviations during generation, predict outcome from partial traces, recommend optimal next steps.

7. **Lasagna vs. Spaghetti**: LLM reasoning is likely Spaghetti — trace clustering and abstraction are essential before model discovery.

### Process Discovery methods we can use

1. **Inductive Miner (IM, IMF, IMD)**: Best overall choice.
   - Produces sound process trees (seq, choice, parallel, loop) — natural for reasoning.
   - Handles noise and incompleteness.
   - Scalable; can handle large trace datasets.
   - Variants: IMF for filtering infrequent paths, IMD for directly-follows graph based (fastest).

2. **Heuristic Miner**: Good for preliminary analysis.
   - Frequency-based dependency graph → identifies common reasoning transitions.
   - Handles noise via thresholding.
   - Fast and simple.

3. **Fuzzy Miner**: For unstructured reasoning (Spaghetti).
   - Groups related low-frequency activities into subprocesses.
   - Hierarchical abstraction helps manage complexity.
   - Good for initial exploration.

4. **Trace Clustering (preprocessing)**: Essential for Spaghetti reasoning.
   - k-means, SOM, or distance-based clustering on trace features.
   - Discover multiple simple models (one per cluster) instead of one complex model.
   - Clusters themselves may reveal distinct reasoning strategies.

5. **α-algorithm**: Pedagogical value only. Too limited for real reasoning traces (no loops, no noise, no concurrency).

### Conformance Checking methods we can use

1. **Token replay**: Fast fitness check.
   - Replay reasoning traces on the expected protocol model.
   - Count missing/remaining tokens → fitness score.
   - Good for quick conformance assessment.

2. **Alignments**: Precise deviation diagnostics.
   - Optimal matching of trace to model path.
   - Identifies exactly which steps are skipped, added, or substituted.
   - Essential for detailed error analysis.
   - Computationally expensive — use for detailed case studies, not large-scale screening.

3. **Footprint comparison**: Fast model-to-model comparison.
   - Compare directly-follows relations of expected vs. discovered models.
   - Quick sanity check; less precise than alignments.

### Potential mapping: LLM reasoning → PM event log

| PM Concept | LLM Reasoning Trace Equivalent | Notes |
|---|---|---|
| **Case ID** | (question_id, model_id, run_id) | Each reasoning attempt is a case |
| **Activity** | Reasoning step type | E.g., "decompose", "compute", "verify", "answer", "reflect" |
| **Timestamp** | Token position / generation order | Sequential, not wall-clock. Use index as proxy timestamp. |
| **Resource** | Model name + config | E.g., "gpt-4-turbo, temp=0.7" |
| **Trace** | Complete reasoning trace | Ordered sequence of reasoning steps for one question |
| **Event log** | Collection of reasoning traces | Multiple questions × multiple models × multiple runs |
| **Process model** | Reasoning protocol / strategy | E.g., "decompose → solve sub-problems → combine → verify → answer" |
| **Conformance** | Protocol adherence | Does the actual reasoning follow the expected protocol? |
| **Fitness** | Protocol coverage | What fraction of traces follow the protocol? |
| **Precision** | Protocol specificity | Does the model avoid permitting invalid reasoning? |
| **Bottleneck** | Token-heavy step | Which reasoning step consumes the most tokens? |
| **Concept drift** | Model update / prompt change | Process changes when model or prompt changes |
| **Noise** | Atypical reasoning | Infrequent/exceptional reasoning paths |
| **De jure model** | Designed reasoning protocol | E.g., chain-of-thought, tree-of-thought, reAct |
| **De facto model** | Discovered reasoning pattern | What the model actually does, not what it's told to do |
| **Pre mortem data** | Partial reasoning trace | During generation — for real-time monitoring |
| **Post mortem data** | Completed reasoning trace | After generation — for offline analysis |

**Important caveats:**
- **Timestamp mapping is imperfect**: PM assumes real time; reasoning traces are sequentially ordered but not time-stamped. Token position is a reasonable proxy, but PM's time analysis (waiting time, processing time) doesn't directly translate. Instead, "time" = token count.
- **Concurrency is rare**: LLM reasoning is mostly sequential. Parallel reasoning (e.g., tree-of-thought, multi-path exploration) can be modeled as concurrency, but it's less common. The discovery algorithms' ability to handle concurrency is less critical than for business processes.
- **Activity labeling is non-trivial**: Reasoning steps don't have natural labels. We need to define a taxonomy of reasoning step types (annotation scheme). This is a key preprocessing challenge — similar to PM's challenge of mapping low-level events to business-level activities.
- **Loops are important**: Reasoning often involves iteration (try → check → revise). The process tree's loop construct (↺) is essential. Inductive miner handles this well.
- **Case correlation is simpler**: Each reasoning trace is naturally a complete case — no need to correlate events from multiple sources. But grouping traces by question (for cross-model comparison) is an additional layer.

---

## Open Questions / Research Inspirations

1. **Reasoning step taxonomy**: What is the right set of "activities" for reasoning traces? Too fine-grained = Spaghetti; too coarse = Lasagna. Need a principled taxonomy. Could use PM's dotted chart for initial exploration, then cluster low-level steps into higher-level activities (analogous to PM's event abstraction).

2. **De jure vs. de facto reasoning models**: Given a prompting strategy (CoT, ToT, ReAct), the expected protocol is the de jure model. The discovered pattern from actual traces is the de facto model. The gap between them is a key research finding — how much do LLMs actually follow the intended reasoning protocol?

3. **Token efficiency as a "time" perspective**: PM's time perspective (bottleneck analysis, flow time) maps directly to token efficiency. Which reasoning steps are "bottlenecks" (consume disproportionate tokens)? Can we "optimize" the reasoning process by identifying and shortening high-token steps?

4. **Reasoning pattern discovery across models**: Discover process models for different LLMs and compare them. Do different models have different "reasoning styles" (different de facto models)? This is analogous to comparing processes across organizations.

5. **Predicting answer correctness from partial traces**: Using PM's operational support techniques (prediction on pre mortem data), can we predict whether a reasoning trace will produce the correct answer before it's complete? This would enable early termination of doomed reasoning chains — a direct token saving.

6. **Conformance checking for reasoning errors**: Use alignments to classify reasoning errors. Are errors mostly "missing steps" (skipped verification), "extra steps" (unnecessary computation), or "wrong order" (premature answering)? This taxonomy of errors could inform prompt design.

7. **Decision mining for strategy selection**: At choice points in reasoning, what question features predict which branch is taken? Decision trees on question features → predict reasoning strategy. Could we recommend the optimal strategy for each question type?

8. **Concept drift in LLM reasoning**: As models are updated (fine-tuned, RLHF'd), their reasoning patterns change. Can we detect "concept drift" in reasoning traces across model versions? This is analogous to PM's concept drift detection in business processes.

9. **Reasoning as Spaghetti → clustering first**: Since LLM reasoning is likely Spaghetti, trace clustering before discovery is essential. What features to cluster on? Raw step sequences? Token distributions? Error patterns? The clusters themselves may reveal distinct reasoning strategies.

10. **Process cubes for multi-dimensional reasoning analysis**: Treat the reasoning trace dataset as a process cube. Dimensions: question type, difficulty, model, prompt strategy, temperature. Slice and dice to find how reasoning patterns vary across dimensions. E.g., "Do harder questions trigger more verification steps?"

11. **"N = All" for reasoning analysis**: Unlike business processes where sampling is common, we can potentially analyze ALL reasoning traces from a model on a benchmark. This enables exhaustive conformance checking — check every trace, not just a sample. But beware Bonferroni's principle: spurious patterns will appear in large datasets by chance.

12. **Reasoning model repair**: If conformance checking reveals systematic deviations (e.g., a model consistently skips verification), can we "repair" the protocol (update the prompt) to fix this? This is PM's model repair applied to prompting strategy.

13. **Streaming PM for real-time reasoning monitoring**: During generation, apply streaming PM techniques to monitor reasoning in real-time. Detect deviations, predict outcomes, recommend next steps. This could enable dynamic token budget allocation — stop early if prediction is confident, continue if uncertain.

14. **MapReduce for large-scale reasoning analysis**: For datasets with millions of reasoning traces, use MapReduce to compute directly-follows graphs. Map = emit (step_i → step_i+1) per trace; Reduce = sum frequencies. This is embarrassingly parallel.

15. **Process tree as a compact representation of reasoning**: Process trees (seq, choice, parallel, loop) are a compact, interpretable representation of reasoning patterns. They could serve as a "summary" of a model's reasoning behavior — more informative than aggregate accuracy metrics.

---

## TODO: Chapters still to read

- [ ] Chapter 13: Analyzing "Lasagna" Processes (pp. 391–406) — browsed only
- [ ] Chapter 14: Analyzing "Spaghetti" Processes (pp. 407–422) — browsed only  
- [ ] Chapter 15: Process Cartography (pp. 423–446) — browsed only
- [ ] Chapter 16: Epilogue (pp. 447–458) — browsed only

These chapters are more about practical application and future directions. The key technical content for our research is in chapters 1–12. Chapters 13–14 provide useful vocabulary (Lasagna/Spaghetti) but no new techniques. Chapter 15's cartography metaphor is useful for framing but not technical. Chapter 16's epilogue mentions PM for AI as a future direction — directly relevant to our research agenda.