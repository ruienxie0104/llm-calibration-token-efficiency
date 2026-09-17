# Stage 2P: Process-only formal interventional pilot

> Stage: gate0
> Generated from `/Users/ryan/Projects/llm-calibration-token-efficiency/experiments/v3-budget-pilot/analyze_process_stage2p.py`
> Bootstrap: 10000 replicates, question-clustered, 5% alpha
> Random baseline: analytical expectation at matched K* (not single draw)

## Policy comparison (per model)

### DeepSeek
- K* = 0 (0 visible + 0 empty)
- Prefix baseline: 100.0%

| Policy | Accuracy | Mean total tokens | K used |
|--------|------:|------:|------:|
| fixed_continue            | 100.0% | 746 | 2 |
| fixed_low                 | 100.0% | 219 | 0 |
| oracle                    | 100.0% | 219 | 0 |
| process_only              | 100.0% | 219 | 0 |
| process_only_inverse      | 100.0% | 219 | 0 |
| question_only             | 100.0% | 219 | 0 |
| random_expected           | 100.0% | 219 | 0 |

**Primary comparison: Process-only vs Random expected**
- ΔAccuracy = 0.0%
- 95% CI [0.0%, 0.0%]
- p = 1.0000
- Significant: False

**Outcome breakdown (for unfinished cases)**
- Benefit (prefix wrong → continuation right): 0
- Harm (prefix right → continuation wrong): 0
- Unchanged: 0
- Unresolved (continuation unparsed, no fallback): 0
- Oracle max benefit (continue-only-on-gain=1): 0

### GPT
- K* = 0 (0 visible + 0 empty)
- Prefix baseline: 100.0%

| Policy | Accuracy | Mean total tokens | K used |
|--------|------:|------:|------:|
| fixed_continue            | 100.0% | 1092 | 2 |
| fixed_low                 | 100.0% | 496 | 0 |
| oracle                    | 100.0% | 496 | 0 |
| process_only              | 100.0% | 496 | 0 |
| process_only_inverse      | 100.0% | 496 | 0 |
| question_only             | 100.0% | 496 | 0 |
| random_expected           | 100.0% | 496 | 0 |

**Primary comparison: Process-only vs Random expected**
- ΔAccuracy = 0.0%
- 95% CI [0.0%, 0.0%]
- p = 1.0000
- Significant: False

**Outcome breakdown (for unfinished cases)**
- Benefit (prefix wrong → continuation right): 0
- Harm (prefix right → continuation wrong): 0
- Unchanged: 0
- Unresolved (continuation unparsed, no fallback): 0
- Oracle max benefit (continue-only-on-gain=1): 0
