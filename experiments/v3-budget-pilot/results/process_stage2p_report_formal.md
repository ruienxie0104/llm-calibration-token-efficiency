# Stage 2P: Process-only formal interventional pilot (formal)
N_BOOTSTRAP=10000 alpha=0.05 cost_tol=0.05
significant = ci_lower > 0 (not tail_prob < 0.05)

## Study-level primary result
Pooled question-clustered Δ=8.7% CI [4.6, 12.3] significant=True
Cross-model direction consistent=True; cost ratio=1.102; study success=False

### DeepSeek-V4-Flash-158B
K* = 5 ({'complete': 55, 'visible': 5, 'empty': 0}), prefix baseline = 86.7%
| Policy | Acc% | Mean tok | K |
|---|---:|---:|---:|
| fixed_continue | 93.3 | 643.4 | 60 |
| fixed_low | 86.7 | 276.2 | 0 |
| oracle | 93.3 | 342.1 | 5 |
| process_only | 93.3 | 349.2 | 5 |
| process_only_inverse | 86.7 | 306.5 | 5 |
| question_only | 88.3 | 307.4 | 5 |
| random_expected | 87.2 | 306.8 | 5 |

**Primary: Δ=6.1% CI [1.6,11.6] tail=0.0157 significant=True**
Cost ratio: 1.138 parity=False pareto=False
Overall success: False
Outcomes: {'complete_stop': 55, 'benefit': 4, 'unchanged': 1}
All continuation outcomes by prefix state: {'complete': {'benefit': 0, 'harm': 0, 'unchanged': 55, 'unresolved': 0}, 'visible_unfinished': {'benefit': 4, 'harm': 0, 'unchanged': 1, 'unresolved': 0}}
Oracle max benefit: 4/5

### GPT-OSS-120B
K* = 17 ({'complete': 43, 'visible': 11, 'empty': 6}), prefix baseline = 68.3%
| Policy | Acc% | Mean tok | K |
|---|---:|---:|---:|
| fixed_continue | 81.7 | 962.5 | 60 |
| fixed_low | 68.3 | 444.9 | 0 |
| oracle | 83.3 | 616.7 | 17 |
| process_only | 83.3 | 640.6 | 17 |
| process_only_inverse | 68.3 | 581.9 | 17 |
| question_only | 71.7 | 596.5 | 17 |
| random_expected | 72.1 | 591.5 | 17 |

**Primary: Δ=11.2% CI [5.4,16.5] tail=0.0 significant=True**
Cost ratio: 1.083 parity=False pareto=False
Overall success: False
Outcomes: {'complete_stop': 43, 'benefit': 9, 'unresolved_fallback': 8}
All continuation outcomes by prefix state: {'complete': {'benefit': 0, 'harm': 1, 'unchanged': 41, 'unresolved': 1}, 'visible_unfinished': {'benefit': 9, 'harm': 0, 'unchanged': 0, 'unresolved': 2}, 'empty_unfinished': {'benefit': 0, 'harm': 0, 'unchanged': 0, 'unresolved': 6}}
Oracle max benefit: 9/17
