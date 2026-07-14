#!/usr/bin/env python3
"""
Pilot: Process Mining × LLM Reasoning Traces

Phase 0: Simulated CoT traces to validate the PM pipeline
Phase 1: Real API calls to collect actual CoT traces (future)

This script:
1. Generates simulated CoT traces for 3 "models" × 30 questions
2. Segments traces into semantic steps
3. Builds PM event log
4. Runs process discovery (inductive miner)
5. Runs conformance checking
6. Compares path quality metrics across models
"""

import pm4py
import pandas as pd
import random
import json
import os
from collections import Counter, defaultdict

random.seed(42)

# ============================================================
# Step 1: Define Activity Types (Step Labels)
# ============================================================

ACTIVITIES = [
    "understand",    # Understanding the question
    "recall",        # Recalling relevant knowledge
    "plan",          # Planning approach
    "calculate",     # Performing calculation
    "reason",        # Logical reasoning
    "verify",        # Checking intermediate results
    "reconsider",    # Re-doing a step (loop indicator)
    "answer",        # Producing final answer
]

# ============================================================
# Step 2: Generate Simulated CoT Traces
# ============================================================

# Three "models" with different calibration profiles
# Model A: High LCAE, high accuracy → clean, efficient paths
# Model B: Medium LCAE, medium accuracy → some loops, some verification
# Model C: Low LCAE, low accuracy → many loops, overthinking or underthinking

MODEL_PROFILES = {
    "ModelA_HighLCAE": {
        "lcae": 0.85,
        "accuracy": 0.90,
        "step_probabilities": {
            "understand": 1.0,    # Always starts with understanding
            "recall": 0.8,        # Usually recalls knowledge
            "plan": 0.7,          # Often plans
            "calculate": 0.6,     # Calculates when needed
            "reason": 0.9,        # Almost always reasons
            "verify": 0.85,       # High verification rate
            "reconsider": 0.05,   # Rarely reconsiders (low overthinking)
            "answer": 1.0,        # Always ends with answer
        },
        "avg_steps": 5.5,
    },
    "ModelB_MedLCAE": {
        "lcae": 0.62,
        "accuracy": 0.70,
        "step_probabilities": {
            "understand": 1.0,
            "recall": 0.6,
            "plan": 0.4,
            "calculate": 0.7,
            "reason": 0.85,
            "verify": 0.5,        # Moderate verification
            "reconsider": 0.25,   # Some reconsideration
            "answer": 1.0,
        },
        "avg_steps": 6.5,
    },
    "ModelC_LowLCAE": {
        "lcae": 0.38,
        "accuracy": 0.50,
        "step_probabilities": {
            "understand": 1.0,
            "recall": 0.4,        # Often skips recall
            "plan": 0.2,          # Rarely plans
            "calculate": 0.8,     # Jumps to calculation
            "reason": 0.7,
            "verify": 0.2,        # Rarely verifies (underthinking)
            "reconsider": 0.45,  # High reconsideration (overthinking on some)
            "answer": 1.0,
        },
        "avg_steps": 7.5,
    },
}

def generate_trace(model_name, question_id, difficulty="medium"):
    """Generate a simulated CoT trace for one question."""
    profile = MODEL_PROFILES[model_name]
    probs = profile["step_probabilities"]
    
    trace = ["understand"]  # Always starts with understanding
    
    # Knowledge recall
    if random.random() < probs["recall"]:
        trace.append("recall")
    
    # Planning
    if random.random() < probs["plan"]:
        trace.append("plan")
    
    # Main reasoning phase
    num_reasoning_steps = random.randint(1, 3)
    for _ in range(num_reasoning_steps):
        if random.random() < probs["calculate"]:
            trace.append("calculate")
        if random.random() < probs["reason"]:
            trace.append("reason")
    
    # Verification (may loop back)
    if random.random() < probs["verify"]:
        trace.append("verify")
    
    # Reconsideration (loop back to reasoning)
    num_reconsiders = 0
    if random.random() < probs["reconsider"]:
        num_reconsiders = random.randint(1, 2)
        for _ in range(num_reconsiders):
            trace.append("reconsider")
            trace.append("reason")
            if random.random() < 0.3:
                trace.append("calculate")
            if random.random() < 0.2:
                trace.append("verify")
    
    # Final answer
    trace.append("answer")
    
    return trace

# Generate all traces
NUM_QUESTIONS = 30
all_traces = {}

for model_name in MODEL_PROFILES:
    all_traces[model_name] = []
    for q_id in range(1, NUM_QUESTIONS + 1):
        trace = generate_trace(model_name, q_id)
        all_traces[model_name].append({
            "case_id": f"{model_name}_Q{q_id}",
            "model": model_name,
            "question_id": q_id,
            "trace": trace,
            "num_steps": len(trace),
            "num_loops": trace.count("reconsider"),
            "has_verify": "verify" in trace,
        })

# ============================================================
# Step 3: Build PM Event Log
# ============================================================

def build_event_log(traces_data):
    """Convert traces to PM4Py event log format."""
    events = []
    for model_traces in traces_data.values():
        for case in model_traces:
            for idx, activity in enumerate(case["trace"]):
                events.append({
                    "case:concept:name": case["case_id"],
                    "concept:name": activity,
                    "time:timestamp": pd.Timestamp(f"2026-01-01 00:00:{idx:02d}"),
                    "model": case["model"],
                    "question_id": str(case["question_id"]),
                    "step_order": idx,
                })
    
    df = pd.DataFrame(events)
    # Ensure correct types
    df["case:concept:name"] = df["case:concept:name"].astype(str)
    df["concept:name"] = df["concept:name"].astype(str)
    df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
    
    # Convert to PM4Py event log
    log = pm4py.convert_to_event_log(df, case_id_key="case:concept:name")
    return log, df

log, log_df = build_event_log(all_traces)

print(f"Event log created: {len(log)} cases, {len(log_df)} events")
print(f"Activities: {sorted(log_df['concept:name'].unique())}")
print()

# ============================================================
# Step 4: Process Discovery (per model)
# ============================================================

discovery_results = {}

for model_name in MODEL_PROFILES:
    # Filter events for this model
    model_df = log_df[log_df["model"] == model_name].copy()
    model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
    
    # Discover process model using inductive miner
    net, im, fm = pm4py.discover_petri_net_inductive(model_log)
    
    # Also get process tree (more readable)
    tree = pm4py.discover_process_tree_inductive(model_log)
    
    discovery_results[model_name] = {
        "net": net,
        "im": im,
        "fm": fm,
        "tree": tree,
    }
    
    # Get variants
    variants = pm4py.get_variants(model_log)
    
    # Stats
    num_variants = len(variants)
    avg_steps = sum(c["num_steps"] for c in all_traces[model_name]) / len(all_traces[model_name])
    avg_loops = sum(c["num_loops"] for c in all_traces[model_name]) / len(all_traces[model_name])
    verify_rate = sum(1 for c in all_traces[model_name] if c["has_verify"]) / len(all_traces[model_name])
    
    print(f"=== {model_name} (LCAE={MODEL_PROFILES[model_name]['lcae']}) ===")
    print(f"  Cases: {NUM_QUESTIONS}")
    print(f"  Variants: {num_variants}")
    print(f"  Avg steps: {avg_steps:.2f}")
    print(f"  Avg loops (reconsider): {avg_loops:.2f}")
    print(f"  Verification rate: {verify_rate:.2%}")
    print(f"  Top 3 variants:")
    sorted_variants = sorted(variants.items(), key=lambda x: -len(x[1]))
    for var, cases in sorted_variants[:3]:
        print(f"    {var} → {len(cases)} cases")
    print()

# ============================================================
# Step 5: Conformance Checking
# ============================================================

# Use Model A (high LCAE) as reference model
ref_model = "ModelA_HighLCAE"
ref_net = discovery_results[ref_model]["net"]
ref_im = discovery_results[ref_model]["im"]
ref_fm = discovery_results[ref_model]["fm"]

print(f"=== Conformance Checking (Reference: {ref_model}) ===\n")

conformance_results = {}

for model_name in MODEL_PROFILES:
    model_df = log_df[log_df["model"] == model_name].copy()
    model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
    
    # Token-based replay
    fitness = pm4py.conformance_diagnostics_token_based_replay(
        model_log, ref_net, ref_im, fm
    )
    
    # Alignment-based diagnostics
    alignments = pm4py.conformance_diagnostics_alignments(
        model_log, ref_net, ref_im, ref_fm
    )
    
    # Aggregate
    avg_fitness = sum(t["trace_fitness"] for t in fitness) / len(fitness)
    
    # Count deviations from alignments
    total_log_moves = 0  # log has, model doesn't (unexpected steps)
    total_model_moves = 0  # model has, log doesn't (missing steps)
    
    for a in alignments:
        for move in a["alignment"]:
            if move[0] != ">>" and move[1] == ">>":
                total_log_moves += 1
            elif move[0] == ">>" and move[1] != ">>":
                total_model_moves += 1
    
    conformance_results[model_name] = {
        "avg_fitness": avg_fitness,
        "log_moves": total_log_moves,
        "model_moves": total_model_moves,
        "total_deviations": total_log_moves + total_model_moves,
    }
    
    print(f"{model_name}:")
    print(f"  Fitness: {avg_fitness:.4f}")
    print(f"  Log moves (unexpected steps): {total_log_moves}")
    print(f"  Model moves (missing steps): {total_model_moves}")
    print(f"  Total deviations: {total_log_moves + total_model_moves}")
    print()

# ============================================================
# Step 6: Path Quality Metrics Comparison
# ============================================================

print("=== Path Quality Metrics Summary ===\n")

metrics_df = []
for model_name in MODEL_PROFILES:
    traces = all_traces[model_name]
    profile = MODEL_PROFILES[model_name]
    conf = conformance_results[model_name]
    
    avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
    avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
    verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
    variants = pm4py.get_variants(pm4py.convert_to_event_log(
        log_df[log_df["model"] == model_name], case_id_key="case:concept:name"
    ))
    
    metrics_df.append({
        "Model": model_name,
        "LCAE": profile["lcae"],
        "Accuracy": profile["accuracy"],
        "Avg_Steps": round(avg_steps, 2),
        "Avg_Loops": round(avg_loops, 2),
        "Verify_Rate": f"{verify_rate:.0%}",
        "Variants": len(variants),
        "Fitness_vs_Ref": round(conf["avg_fitness"], 4),
        "Deviations": conf["total_deviations"],
        "Log_Moves": conf["log_moves"],
        "Model_Moves": conf["model_moves"],
    })

metrics_table = pd.DataFrame(metrics_df)
print(metrics_table.to_string(index=False))
print()

# ============================================================
# Step 7: Save Results
# ============================================================

output_dir = "pilot_results"
os.makedirs(output_dir, exist_ok=True)

# Save metrics table
metrics_table.to_csv(f"{output_dir}/path_quality_metrics.csv", index=False)

# Save traces
with open(f"{output_dir}/traces.json", "w") as f:
    json.dump(all_traces, f, indent=2)

# Save conformance results
conf_summary = {k: {kk: vv for kk, vv in v.items() if kk != "net"} 
                for k, v in conformance_results.items()}
with open(f"{output_dir}/conformance.json", "w") as f:
    json.dump(conf_summary, f, indent=2)

# Save discovered models as PNG (if graphviz available)
try:
    for model_name, result in discovery_results.items():
        safe_name = model_name.replace(" ", "_")
        pm4py.save_vis_petri_net(result["net"], result["im"], result["fm"],
                                  f"{output_dir}/petri_net_{safe_name}.png")
        pm4py.save_vis_process_tree(result["tree"],
                                     f"{output_dir}/process_tree_{safe_name}.png")
        print(f"Saved visualizations for {model_name}")
except Exception as e:
    print(f"Visualization skipped: {e}")

print(f"\nResults saved to {output_dir}/")
print("\nPilot complete!")