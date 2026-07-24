#!/usr/bin/env python3
"""Finish PM analysis for remaining 2 models with alignment timeout."""
import json, sys, os, warnings, signal
warnings.filterwarnings("ignore")
os.environ['PM4PY_SHOW_WARNINGS'] = '0'

sys.path.insert(0, '.')

import pm4py
import pandas as pd
from analysis_utils import count_alignment_deviations
from experiment_v2 import build_traces, build_event_log, compute_calibration_metrics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "results")

# Load existing data
with open(f"{OUTPUT_DIR}/raw_responses_v2.json") as f:
    all_results = json.load(f)

# Build traces and event log
print("Building traces and event log...")
all_traces = build_traces(all_results)
log, log_df = build_event_log(all_traces)
print(f"  {len(log)} cases, {len(log_df)} events")

accuracy_by_model = {m: sum(1 for t in ts if t["correct"])/len(ts) for m, ts in all_traces.items()}
ref_model = max(accuracy_by_model, key=accuracy_by_model.get)
print(f"Reference model: {ref_model} (accuracy={accuracy_by_model[ref_model]:.0%})")

# Load existing conformance
conf_file = f"{OUTPUT_DIR}/conformance_final.json"
with open(conf_file) as f:
    conformance_results = json.load(f)
print(f"Existing conformance: {list(conformance_results.keys())}")

# Discover reference Petri net
print(f"\nRediscovering reference Petri net ({ref_model})...")
ref_df = log_df[log_df["model"] == ref_model].copy()
ref_log = pm4py.convert_to_event_log(ref_df, case_id_key="case:concept:name")
ref_net, ref_im, ref_fm = pm4py.discover_petri_net_inductive(ref_log)
print("  Done.")

# Process remaining models
remaining = [m for m in all_traces.keys() if m not in conformance_results or conformance_results[m].get("avg_fitness") is None]
print(f"Remaining: {remaining}")

for model_name in remaining:
    print(f"\n  Processing {model_name}...")
    model_df = log_df[log_df["model"] == model_name].copy()
    model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
    
    # TBR (fast, always do this)
    fitness = pm4py.conformance_diagnostics_token_based_replay(model_log, ref_net, ref_im, ref_fm)
    avg_fitness = sum(t["trace_fitness"] for t in fitness) / len(fitness)
    print(f"    TBR fitness: {avg_fitness:.4f}")
    
    # Alignments with per-variant timeout
    print(f"    Running alignments ({len(model_log)} traces)...")
    try:
        # Use a simpler approach: set a signal alarm per variant
        # Actually pm4py doesn't support per-variant timeout easily
        # Let's just try alignments and if it takes too long, we'll use TBR only
        
        # Try with a 5-minute overall timeout using signal
        def handler(signum, frame):
            raise TimeoutError("Alignment took too long")
        
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(300)  # 5 minute timeout
        
        alignments = pm4py.conformance_diagnostics_alignments(model_log, ref_net, ref_im, ref_fm)
        
        signal.alarm(0)  # Cancel alarm
        
        total_dev = count_alignment_deviations(alignments)
        conformance_results[model_name] = {"avg_fitness": avg_fitness, "total_deviations": total_dev}
        print(f"    Alignment deviations: {total_dev}")
        
    except TimeoutError:
        signal.alarm(0)
        print(f"    Alignment timed out, using TBR fitness only")
        # Estimate deviations from TBR
        # TBR gives us fitness and number of missing/consumed/remaining tokens
        total_dev = sum(
            t.get("missing_tokens", 0) + t.get("remaining_tokens", 0)
            for t in fitness
        )
        conformance_results[model_name] = {"avg_fitness": avg_fitness, "total_deviations": total_dev, "alignment": "timeout"}
        print(f"    TBR-based deviations: {total_dev}")
    except Exception as e:
        signal.alarm(0)
        print(f"    Alignment failed: {e}")
        total_dev = sum(
            t.get("missing_tokens", 0) + t.get("remaining_tokens", 0)
            for t in fitness
        )
        conformance_results[model_name] = {"avg_fitness": avg_fitness, "total_deviations": total_dev, "alignment": "failed"}
        print(f"    TBR-based deviations: {total_dev}")
    
    # Save after each model
    with open(conf_file, "w") as f:
        json.dump(conformance_results, f, indent=2, default=str)
    print(f"    Saved.")

# Now generate the full summary
print("\n" + "=" * 130)
print("Full Summary")
print("-" * 130)

calibration = compute_calibration_metrics(all_results)

# Discovery: load from existing
with open(f"{OUTPUT_DIR}/discovery_final.json") as f:
    discovery_summary = json.load(f)

metrics = []
for model_name in all_traces.keys():
    traces = all_traces[model_name]
    avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
    avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
    verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
    avg_time = sum(t["elapsed"] for t in traces) / len(traces)
    avg_tokens = sum(t["total_tokens"] for t in traces) / len(traces)
    conf = conformance_results.get(model_name, {})
    disc = discovery_summary.get(model_name, {})
    cal = calibration.get(model_name, {})
    
    metrics.append({
        "Model": model_name,
        "Accuracy": f"{accuracy_by_model.get(model_name, 0):.0%}",
        "Avg_Steps": round(avg_steps, 1),
        "Avg_Loops": round(avg_loops, 2),
        "Verify": f"{verify_rate:.0%}",
        "Variants": disc.get("variants", "?"),
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
metrics_df.to_csv(f"{OUTPUT_DIR}/full_metrics_final.csv", index=False)

# Save traces and calibration too
with open(f"{OUTPUT_DIR}/traces_final.json", "w") as f:
    json.dump({k: [{kk: vv for kk, vv in v.items()} for v in vs] for k, vs in all_traces.items()}, f, indent=2)
with open(f"{OUTPUT_DIR}/calibration_final.json", "w") as f:
    json.dump(calibration, f, indent=2)

print(f"\nAll results saved to {OUTPUT_DIR}/")
print("Experiment v2 complete!")
