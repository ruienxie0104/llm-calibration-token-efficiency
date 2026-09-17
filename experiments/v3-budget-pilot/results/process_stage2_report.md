# Stage 2 evidence-allocation report

> Generated only from raw action logs. Gate results are feasibility diagnostics, not final causal claims.

## Gate 0: visible-contextual continuation

| Model | n | Prefix acc. | Continuation acc. | Fresh-high acc. | Continuation parse | Continuation errors |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-158B | 10 | 80.0% | 90.0% | 90.0% | 90.0% | 0.0% |
| GPT-OSS-120B | 10 | 70.0% | 80.0% | 80.0% | 80.0% | 0.0% |

## Gate 1: answer-consistency on empty unfinished cases

| Model | n | Pair parse | Agree n / rate | Consensus correct given agree | Continue correct given agree | Continue correct given disagree |
|---|---:|---:|---:|---:|---:|---:|
| GPT-OSS-120B | 5 | 0.0% | 0 / NA | NA | NA | NA |

## Interpretation guardrails

- Continuation replays visible assistant content only; it cannot restore hidden reasoning state.
- Agreement is not correctness. Report both agreement and gold-answer accuracy.
- Do not enter the formal policy comparison unless the pre-specified Gate 0/Gate 1 criteria in `process_stage2_evidence_allocation_plan.md` are reviewed.
