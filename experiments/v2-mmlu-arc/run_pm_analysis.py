#!/usr/bin/env python3
"""Run PM analysis (Step 4) separately with progress saving."""
import json, sys, os, warnings
warnings.filterwarnings("ignore")
os.environ['PM4PY_SHOW_WARNINGS'] = '0'

sys.path.insert(0, '.')
from experiment_v2 import build_traces, build_event_log, run_pm_analysis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "results")

# Load existing data
with open(f"{OUTPUT_DIR}/raw_responses_v2.json") as f:
    all_results = json.load(f)

# Build traces
print("Building traces...")
all_traces = build_traces(all_results)
print(f"  {len(all_traces)} models")

# Build event log
print("Building event log...")
log, log_df = build_event_log(all_traces)
print(f"  {len(log)} cases, {len(log_df)} events")

# Run PM analysis
print("Running PM analysis (discovery + conformance)...")
print("  This may take 10-20 minutes for alignment...")
try:
    discovery_results, conformance_results, accuracy = run_pm_analysis(all_traces, log_df)
    
    # Save conformance results
    with open(f"{OUTPUT_DIR}/conformance_final.json", "w") as f:
        json.dump({k: v for k, v in conformance_results.items()}, f, indent=2, default=str)
    
    # Save discovery variant counts
    discovery_summary = {}
    for m, r in discovery_results.items():
        if r:
            discovery_summary[m] = {"variants": r["variants"]}
        else:
            discovery_summary[m] = {"variants": None}
    with open(f"{OUTPUT_DIR}/discovery_final.json", "w") as f:
        json.dump(discovery_summary, f, indent=2)
    
    # Save visualizations
    import pm4py
    for model_name, result in discovery_results.items():
        if result:
            safe = model_name.replace(" ", "_").replace("/", "_")
            try:
                pm4py.save_vis_petri_net(result["net"], result["im"], result["fm"], f"{OUTPUT_DIR}/petri_net_{safe}.png")
                pm4py.save_vis_process_tree(result["tree"], f"{OUTPUT_DIR}/process_tree_{safe}.png")
                print(f"  Saved: {safe}.png")
            except Exception as e:
                print(f"  Viz failed for {model_name}: {e}")
    
    print("\nPM analysis complete!")
    print(f"\nConformance results:")
    for m, r in conformance_results.items():
        print(f"  {m}: fitness={r.get('avg_fitness')}, deviations={r.get('total_deviations')}")
    
    # Now generate the full summary
    import pandas as pd
    from experiment_v2 import compute_calibration_metrics
    
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
            "Accuracy": f"{accuracy.get(model_name, 0):.0%}",
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
    print("\n" + "="*130)
    print(metrics_df.to_string(index=False))
    metrics_df.to_csv(f"{OUTPUT_DIR}/full_metrics_final.csv", index=False)
    print(f"\nResults saved to {OUTPUT_DIR}/")
    print("Experiment v2 complete!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
