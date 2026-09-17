# Stage 2P: Process-only formal interventional pilot (gate0)
N_BOOTSTRAP=10000 alpha=0.05 cost_tol=0.05
significant = ci_lower > 0 (not tail_prob < 0.05)

## Study-level primary result
Pooled question-clustered Δ=0.0% CI [0.0, 0.0] significant=False
Cross-model direction consistent=False; cost ratio=1.0; study success=False

### DeepSeek-V4-Flash-158B
K* = 0 ({'complete': 2, 'visible': 0, 'empty': 0}), prefix baseline = 100.0%
| Policy | Acc% | Mean tok | K |
|---|---:|---:|---:|
| fixed_continue | 100.0 | 645.0 | 2 |
| fixed_low | 100.0 | 236.0 | 0 |
| oracle | 100.0 | 236.0 | 0 |
| process_only | 100.0 | 236.0 | 0 |
| process_only_inverse | 100.0 | 236.0 | 0 |
| question_only | 100.0 | 236.0 | 0 |
| random_expected | 100.0 | 236.0 | 0 |

**Primary: Δ=0.0% CI [0.0,0.0] tail=1.0 significant=False**
Cost ratio: 1.0 parity=True pareto=False
Overall success: False
Outcomes: {'complete_stop': 2}
All continuation outcomes by prefix state: {'complete': {'benefit': 0, 'harm': 0, 'unchanged': 2, 'unresolved': 0}}
Oracle max benefit: 0/0

### GPT-OSS-120B
K* = 0 ({'complete': 2, 'visible': 0, 'empty': 0}), prefix baseline = 100.0%
| Policy | Acc% | Mean tok | K |
|---|---:|---:|---:|
| fixed_continue | 100.0 | 1037.0 | 2 |
| fixed_low | 100.0 | 482.5 | 0 |
| oracle | 100.0 | 482.5 | 0 |
| process_only | 100.0 | 482.5 | 0 |
| process_only_inverse | 100.0 | 482.5 | 0 |
| question_only | 100.0 | 482.5 | 0 |
| random_expected | 100.0 | 482.5 | 0 |

**Primary: Δ=0.0% CI [0.0,0.0] tail=1.0 significant=False**
Cost ratio: 1.0 parity=True pareto=False
Overall success: False
Outcomes: {'complete_stop': 2}
All continuation outcomes by prefix state: {'complete': {'benefit': 0, 'harm': 0, 'unchanged': 2, 'unresolved': 0}}
Oracle max benefit: 0/0
