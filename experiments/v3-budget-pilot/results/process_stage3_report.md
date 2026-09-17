# Stage 3 visible-progress confirmatory experiment

## Primary result
Pooled Δ = 6.78pp; 95% CI [3.48, 10.22] pp.
Direction consistent=True; visible-state support pass=False; study success=False.

The random primary comparator is a cost-calibrated action-bank evaluation benchmark, not an online policy.

## GPT-OSS-120B
States: {'complete': 38, 'empty_unfinished': 10, 'visible_unfinished': 12}; visible support pass=True.
Primary Δ: 9.62pp; cost identity error=0.000000000.

| Policy | Accuracy | Mean total tokens |
|---|---:|---:|
| visible_progress | 70.00% | 667.9 |
| random_cost_calibrated | 60.38% | 667.9 |
| fixed_low | 58.33% | 528.7 |
| fixed_continue | 66.67% | 1095.8 |
| random_count_matched | 60.00% | 642.1 |
| question_only_count_matched | 66.67% | 652.5 |
| oracle_count_matched | 71.67% | 647.1 |
| random_ledger_replay | 60.48% | 673.0 |
| oracle_cost_constrained | 71.67% | 618.4 |

Continuation outcomes by prefix state: {'complete': {'unchanged': 35, 'harm': 3}, 'empty_unfinished': {'unresolved': 9, 'benefit': 1}, 'visible_unfinished': {'benefit': 7, 'unresolved': 4, 'unchanged': 1}}

## DeepSeek-V4-Flash-158B
States: {'complete': 56, 'visible_unfinished': 4}; visible support pass=False.
Primary Δ: 4.25pp; cost identity error=0.000000000.

| Policy | Accuracy | Mean total tokens |
|---|---:|---:|
| visible_progress | 86.67% | 381.8 |
| random_cost_calibrated | 82.42% | 381.8 |
| fixed_low | 81.67% | 320.0 |
| fixed_continue | 86.67% | 733.2 |
| random_count_matched | 82.00% | 347.5 |
| question_only_count_matched | 83.33% | 355.9 |
| oracle_count_matched | 86.67% | 368.7 |
| random_ledger_replay | 82.45% | 386.1 |
| oracle_cost_constrained | 86.67% | 362.7 |

Continuation outcomes by prefix state: {'complete': {'unchanged': 56}, 'visible_unfinished': {'benefit': 3, 'unresolved': 1}}
