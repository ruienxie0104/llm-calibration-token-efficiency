#!/usr/bin/env python3
"""Re-run conformance checking with DeepSeek as reference model."""
import json, os, sys, time, signal
import pm4py

RESULTS_DIR = "experiments/v2-mmlu-arc/results"
TRACES_FILE = f"{RESULTS_DIR}/traces_final.json"

# Load traces
with open(TRACES_FILE) as f:
    all_traces = json.load(f)

MODELS = list(all_traces.keys())
REF_MODEL = "DeepSeek-V4-Flash-158B"

def traces_to_event_log(traces_list, model_name):
    """Convert trace data to pm4py event log."""
    import pandas as pd
    events = []
    for tr in traces_list:
        case_id = tr['case_id']
        for i, activity in enumerate(tr['trace']):
            events.append({
                'case:concept:name': case_id,
                'concept:name': activity,
                'time:timestamp': pd.Timestamp('2026-01-01') + pd.Timedelta(seconds=i),
                'org:resource': model_name,
            })
    df = pd.DataFrame(events)
    return pm4py.convert_to_event_log(df)

# Build event logs
print("Building event logs...")
event_logs = {}
for m in MODELS:
    event_logs[m] = traces_to_event_log(all_traces[m], m)
    print(f"  {m}: {len(event_logs[m])} events, {len(all_traces[m])} cases")

# Discover Petri net from DeepSeek (reference)
print(f"\nDiscovering Petri net from {REF_MODEL}...")
ref_log = event_logs[REF_MODEL]
net, im, fm = pm4py.discover_petri_net_inductive(ref_log)
print(f"  Discovered net: {len(net.places)} places, {len(net.transitions)} transitions")

# Also discover process tree
tree = pm4py.discover_process_tree_inductive(ref_log)
pm4py.save_vis_petri_net(net, im, fm, f"{RESULTS_DIR}/petri_net_ref_DeepSeek.png")
pm4py.save_vis_process_tree(tree, f"{RESULTS_DIR}/process_tree_ref_DeepSeek.png")
print("  Saved visualizations")

# Run conformance for each model against DeepSeek's net
results = {}
for m in MODELS:
    print(f"\n=== Conformance: {m} vs {REF_MODEL} (reference) ===")
    log = event_logs[m]
    
    # TBR (fast)
    print(f"  Running TBR...")
    tbr = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)
    avg_fitness = sum(t['trace_fitness'] for t in tbr) / len(tbr)
    
    # Count deviations from TBR
    tbr_deviations = 0
    for t in tbr:
        # TBR results may have different structures across pm4py versions
        if isinstance(t, dict):
            tbr_deviations += int(t.get('missing_tokens', 0) if isinstance(t.get('missing_tokens'), (int, dict)) else 0)
            tbr_deviations += int(t.get('consumed_tokens', 0) if isinstance(t.get('consumed_tokens'), (int, dict)) else 0)
            # Also check for produced but not consumed
            if 'produced_tokens' in t and isinstance(t['produced_tokens'], (int, dict)):
                pass  # produced is less relevant
        else:
            tbr_deviations += 1  # fallback
    
    print(f"  TBR fitness: {avg_fitness:.4f}")
    print(f"  TBR deviations: {tbr_deviations}")
    
    # Alignment (slower but more precise)
    print(f"  Running alignment...")
    try:
        signal.alarm(300)  # 5 min timeout
        aligned_traces = pm4py.conformance_diagnostics_alignments(log, net, im, fm)
        signal.alarm(0)
        
        total_dev = 0
        for at in aligned_traces:
            total_dev += at.get('deviation', 0)
        
        results[m] = {
            'reference_model': REF_MODEL,
            'avg_fitness': round(avg_fitness, 4),
            'tbr_deviations': tbr_deviations,
            'alignment_deviations': total_dev,
            'method': 'alignment',
        }
        print(f"  Alignment deviations: {total_dev}")
    except Exception as e:
        signal.alarm(0)
        print(f"  Alignment failed: {e}, using TBR only")
        results[m] = {
            'reference_model': REF_MODEL,
            'avg_fitness': round(avg_fitness, 4),
            'tbr_deviations': tbr_deviations,
            'alignment_deviations': None,
            'method': 'tbr_only',
        }

# Save
with open(f"{RESULTS_DIR}/conformance_deepseek_ref.json", 'w') as f:
    json.dump(results, f, indent=2)

print("\n=== Summary (DeepSeek reference) ===")
for m, r in results.items():
    dev = r['alignment_deviations'] if r['alignment_deviations'] is not None else f"TBR:{r['tbr_deviations']}"
    print(f"  {m}: fitness={r['avg_fitness']:.4f}, deviations={dev}")

# Also compare with GLM-5.2 reference
print("\n=== Comparison: GLM-5.2 ref vs DeepSeek ref ===")
try:
    with open(f"{RESULTS_DIR}/conformance_final.json") as f:
        glm_ref = json.load(f)
    for m in MODELS:
        glm_dev = glm_ref.get(m, {}).get('total_deviations', 'N/A')
        ds_dev = results[m]['alignment_deviations'] or results[m]['tbr_deviations']
        print(f"  {m}: GLM-5.2 ref={glm_dev} → DeepSeek ref={ds_dev}")
except:
    pass

print(f"\nSaved to {RESULTS_DIR}/conformance_deepseek_ref.json")