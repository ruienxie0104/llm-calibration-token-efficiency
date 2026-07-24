#!/usr/bin/env python3
"""Generate full summary from saved results."""
import json, sys, os, warnings
warnings.filterwarnings("ignore")
os.environ['PM4PY_SHOW_WARNINGS'] = '0'

sys.path.insert(0, '.')

import pandas as pd
from experiment_v2 import build_traces, compute_calibration_metrics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "results")

with open(f"{OUTPUT_DIR}/raw_responses_v2.json") as f:
    all_results = json.load(f)
with open(f"{OUTPUT_DIR}/conformance_final.json") as f:
    conformance_results = json.load(f)

all_traces = build_traces(all_results)
accuracy_by_model = {m: sum(1 for t in ts if t["correct"])/len(ts) for m, ts in all_traces.items()}
calibration = compute_calibration_metrics(all_results)

# Count variants per model
import pm4py
from experiment_v2 import build_event_log
log, log_df = build_event_log(all_traces)

variant_counts = {}
for m in all_traces.keys():
    model_df = log_df[log_df["model"] == m].copy()
    model_log = pm4py.convert_to_event_log(model_df, case_id_key="case:concept:name")
    variants = pm4py.get_variants(model_log)
    variant_counts[m] = len(variants)

metrics = []
for model_name in all_traces.keys():
    traces = all_traces[model_name]
    avg_steps = sum(t["num_steps"] for t in traces) / len(traces)
    avg_loops = sum(t["num_loops"] for t in traces) / len(traces)
    verify_rate = sum(1 for t in traces if t["has_verify"]) / len(traces)
    avg_time = sum(t["elapsed"] for t in traces) / len(traces)
    avg_tokens = sum(t["total_tokens"] for t in traces) / len(traces)
    conf = conformance_results.get(model_name, {})
    cal = calibration.get(model_name, {})
    
    metrics.append({
        "Model": model_name,
        "Accuracy": f"{accuracy_by_model.get(model_name, 0):.0%}",
        "Avg_Steps": round(avg_steps, 1),
        "Avg_Loops": round(avg_loops, 2),
        "Verify": f"{verify_rate:.0%}",
        "Variants": variant_counts.get(model_name, "?"),
        "Avg_Time_s": round(avg_time, 1),
        "Avg_Tokens": round(avg_tokens, 0),
        "Tok/Step": round(avg_tokens / avg_steps, 1) if avg_steps > 0 else 0,
        "Brier": round(cal.get("brier_score", 0), 4) if cal.get("brier_score") else "N/A",
        "Avg_Conf": f"{cal.get('avg_confidence', 0):.0f}%" if cal.get("avg_confidence") else "N/A",
        "Conf_Gap": round(cal.get("confidence_gap", 0), 1) if cal.get("confidence_gap") else "N/A",
        "Fitness": round(conf.get("avg_fitness", 0), 4) if conf.get("avg_fitness") else "N/A",
        "Deviations": conf.get("total_deviations", "N/A"),
        "Align_Method": conf.get("alignment", "alignment"),
    })

metrics_df = pd.DataFrame(metrics)
print("=" * 150)
print("Experiment v2 — Full Results Summary")
print("=" * 150)
print(metrics_df.to_string(index=False))
metrics_df.to_csv(f"{OUTPUT_DIR}/full_metrics_final.csv", index=False)

# Also save traces and calibration
with open(f"{OUTPUT_DIR}/traces_final.json", "w") as f:
    json.dump({k: [{kk: vv for kk, vv in v.items()} for v in vs] for k, vs in all_traces.items()}, f, indent=2)
with open(f"{OUTPUT_DIR}/calibration_final.json", "w") as f:
    json.dump(calibration, f, indent=2)

# Save discovery summary
with open(f"{OUTPUT_DIR}/discovery_final.json", "w") as f:
    json.dump(variant_counts, f, indent=2)

print(f"\nAll results saved to {OUTPUT_DIR}/")
print("\nFiles:")
for fn in sorted(os.listdir(OUTPUT_DIR)):
    size = os.path.getsize(f"{OUTPUT_DIR}/{fn}")
    print(f"  {fn} ({size:,} bytes)")
print("\nExperiment v2 complete!")
