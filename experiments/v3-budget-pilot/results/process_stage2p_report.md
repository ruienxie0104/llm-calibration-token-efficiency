# Stage 2P: Process-only formal interventional pilot report

> Generated from `/Users/ryan/Projects/llm-calibration-token-efficiency/experiments/v3-budget-pilot/analyze_process_stage2p.py`
> Bootstrap: 10000 replicates, question-clustered, 5% alpha

## Policy comparison (per model)

| Model | Policy | Accuracy | Mean total tokens | N correct | N total |
|---|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-15 | fixed_low                 | 0.0% | 206 | 0 | 2 |
| DeepSeek-V4-Flash-15 | fixed_continue            | 100.0% | 466 | 2 | 2 |
| DeepSeek-V4-Flash-15 | random_matched            | 100.0% | 466 | 2 | 2 |
| DeepSeek-V4-Flash-15 | question_only             | 50.0% | 330 | 1 | 2 |
| DeepSeek-V4-Flash-15 | process_only              | 100.0% | 466 | 2 | 2 |
| DeepSeek-V4-Flash-15 | process_only_inverse      | 0.0% | 206 | 0 | 2 |
| DeepSeek-V4-Flash-15 | oracle                    | 100.0% | 466 | 2 | 2 |

| GPT-OSS-120B | fixed_low                 | 50.0% | 476 | 1 | 2 |
| GPT-OSS-120B | fixed_continue            | 100.0% | 695 | 2 | 2 |
| GPT-OSS-120B | random_matched            | 50.0% | 586 | 1 | 2 |
| GPT-OSS-120B | question_only             | 50.0% | 586 | 1 | 2 |
| GPT-OSS-120B | process_only              | 100.0% | 586 | 2 | 2 |
| GPT-OSS-120B | process_only_inverse      | 50.0% | 586 | 1 | 2 |
| GPT-OSS-120B | oracle                    | 100.0% | 586 | 2 | 2 |

## Primary comparison: Process-only vs Random matched

| Model | K* | ΔAccuracy | 95% CI lower | 95% CI upper | p-value | Significant |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-15 | 2 | 0.0% | 0.0% | 0.0% | 1.0000 | False |
| GPT-OSS-120B | 1 | 50.0% | 0.0% | 100.0% | 0.2513 | False |

## State distribution per model

| Model | complete | visible_unfinished | empty_unfinished | K* |
|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-15 | 0 | 2 | 0 | 2 |
| GPT-OSS-120B | 1 | 1 | 0 | 1 |