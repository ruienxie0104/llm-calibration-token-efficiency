#!/usr/bin/env python3
"""Run PM analysis one model at a time with incremental saving."""
import json, sys, os, warnings
warnings.filterwarnings("ignore")
os.environ['PM4PY_SHOW_WARNINGS'] = '0'

sys.path.insert(0, '.')

import pm4py
import pandas as pd
from experiment_v2 import build_traces, build_event_log, compute_calibration_metrics, run_pm_analysis

OUTPUT_DIR = "experiment_v2_results"

# Load existing data
with open(f"{OUTPUT_DIR}/raw_responses.json") as f:
    all_results = json.load(f)

# Build traces
print("Building traces...")
all_traces = build_traces(all_results)

# Build event log
print("Building event log...")
log, log_df = build_event_log(all_traces)
print(f"  {len(log)} cases, {len(log_df)} events")

# Accuracy
accuracy_by_model = {m: sum(1 for t in ts if t["correct"])/len(ts) for m, ts in all_traces.items()}
ref_model = max(accuracy_by_model, key=accuracy_by_model.get)
print(f"Reference model: {ref_model} (accuracy={accuracy_by_model[ref_model]:.0%})")

# Discover reference model's Petri net
print(f"\nDiscovering Petri net for {ref_model}...")
ref_df = log_df[log_df["model"] == ref_model].copy()
ref_log = pm4py.convert_to_event_log(ref_df, case_id_key="case:concept:name")
ref_net, ref_im, ref_fm = pm4py.discover_petri_net_inductive(ref_log)
ref_tree = pm4py.discover_process_tree_inductive(ref_log)
ref_variants = pm4py.get_variants(ref_log)
print(f"  {len(ref_variants)} variants")

# Save reference model visualization
safe_ref = ref_model.replace(" ", "_").replace("/", "_")
pm4py.save_vis_petri_net(ref_net, ref_im, ref_fm, f"{OUTPUT_DIR}/petri_net_{safe_ref}.png")
pm4py.save_vis_process_tree(ref_tree, f"{OUTPUT_DIR}/process_tree_{safe_ref}.png")
print(f"  Saved: {safe_ref}.png")

# Discover all models' Petri nets
discovery_results = {ref_model: {"net": ref_net, "im": ref_im, "fm": ref_fm, "tree": ref_tree, "variants": len(ref_variants)}}
for model_name in all_traces.keys():
    if model_name == ref_model:
        continue
    print(f"\nDiscovering Petri net for {model_name}...")
    model_df = log_df[log_df["model"] == model_name].copy()
    model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
    try:
        net, im, fm = pm4py.discover_petri_net_inductive(model_log)
        tree = pm4py.discover_process_tree_inductive(model_log)
        variants = pm4py.get_variants(model_log)
        discovery_results[model_name] = {"net": net, "im": im, "fm": fm, "tree": tree, "variants": len(variants)}
        safe = model_name.replace(" ", "_").replace("/", "_")
        pm4py.save_vis_petri_net(net, im, fm, f"{OUTPUT_DIR}/petri_net_{safe}.png")
        pm4py.save_vis_process_tree(tree, f"{OUTPUT_DIR}/process_tree_{safe}.png")
        print(f"  {len(variants)} variants, saved {safe}.png")
    except Exception as e:
        print(f"  FAILED: {e}")
        discovery_results[model_name] = None

# Now run conformance one model at a time, saving after each
conformance_results = {}

# Try to load existing partial conformance
conf_file = f"{OUTPUT_DIR}/conformance.json"
if os.path.exists(conf_file):
    with open(conf_file) as f:
        conformance_results = json.load(f)
    print(f"\nLoaded existing conformance for: {list(conformance_results.keys())}")

for model_name in all_traces.keys():
    if model_name in conformance_results and conformance_results[model_name].get("avg_fitness") is not None:
        print(f"\n  {model_name}: already done (fitness={conformance_results[model_name]['avg_fitness']:.4f})")
        continue
    
    print(f"\n  Conformance for {model_name}...")
    model_df = log_df[log_df["model"] == model_name].copy()
    model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
    
    try:
        # Token-based replay (fast)
        fitness = pm4py.conformance_diagnostics_token_based_replay(model_log, ref_net, ref_im, ref_fm)
        avg_fitness = sum(t["trace_fitness"] for t in fitness) / len(fitness)
        print(f"    TBR fitness: {avg_fitness:.4f}")
        
        # Alignments (slow) - this is the bottleneck
        print(f"    Running alignments ({len(model_log)} traces)...")
        alignments = pm4py.conformance_diagnostics_alignments(model_log, ref_net, ref_im, ref_fm)
        total_dev = sum(
            1 for a in alignments for move in a["alignment"]
            if (move[0] != ">>" and move[1] == ">>") or (move[0] == ">>" and move[1] != ">>")
        )
        
        conformance_results[model_name] = {"avg_fitness": avg_fitness, "total_deviations": total_dev}
        print(f"    Alignment deviations: {total_dev}")
        
    except Exception as e:
        print(f"    FAILED: {e}")
        conformance_results[model_name] = {"avg_fitness": None, "total_deviations": None, "error": str(e)}
    
    # Save after each model
    with open(conf_file, "w") as f:
        json.dump(conformance_results, f, indent=2, default=str)
    print(f"    Saved to {conf_file}")

# Save discovery summary
discovery_summary = {}
for m, r in discovery_results.items():
    discovery_summary[m] = {"variants": r["variants"] if r else None}
with open(f"{OUTPUT_DIR}/discovery.json", "w") as f:
    json.dump(discovery_summary, f, indent=2)

# Generate full summary
print("\n" + "=" * 130)
print("Full Summary")
print("-" * 130)

calibration = compute_calibration_metrics(all_results)

metrics = []
for model_name in all_traces.keys():
    traces = all_traces[model_name]
    avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
    avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
    verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
    avg_time = sum(t["elapsed"] for t in traces) / len(traces)
    avg_tokens = sum(t["total_tokens"] for t in traces) / len(traces)
    conf = conformance_results.get(model_name, {})
    disc = discovery_results.get(model_name, {})
    cal = calibration.get(model_name, {})
    
    metrics.append({
        "Model": model_name,
        "Accuracy": f"{accuracy_by_model.get(model_name, 0):.0%}",
        "Avg_Steps": round(avg_steps, 1),
        "Avg_Loops": round(avg_loops, 2),
        "Verify": f"{verify_rate:.0%}",
        "Variants": disc.get("variants", "?") if disc else "?",
        "Avg_Time_s": round(avg_time, 1),
        "Avg_Tokens": round(avg_tokens, 0),
        "Tok/Step": round(avg_tokens / avg_steps, 1) if avg_steps > 0 else 0,
        "Brier": round(cal.get("brier_score", 0), 4) if cal.get("brier_score") else "N/A",
        "Avg_Conf": f"{cal.get('avg_confidence', 0):.0f}%" if cal.get("avg_confidence") else "N/A",
        "Conf_Gap": round(cal.get("confidence_gap", 0), 1) if cal.get("confidence_gap") else "N/A",
        "Fitness": round(conf.get("avg_fitness", 0), 4) if conf.get("avg_fitness") else "N/A",
        "Deviations": conf.get("total_deviations", "N/A"),
    })

metrics_df = pd.DataFrame(metrics)
print(metrics_df.to_string(index=False))
metrics_df.to_csv(f"{OUTPUT_DIR}/full_metrics.csv", index=False)

# Save traces
with open(f"{OUTPUT_DIR}/traces.json", "w") as f:
    json.dump({k: [{kk: vv for kk, vv in v.items()} for v in vs] for k, vs in all_traces.items()}, f, indent=2)

with open(f"{OUTPUT_DIR}/calibration.json", "w") as f:
    json.dump(calibration, f, indent=2)

print(f"\nAll results saved to {OUTPUT_DIR}/")
print("Experiment v2 complete!")