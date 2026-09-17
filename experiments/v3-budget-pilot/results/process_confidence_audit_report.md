# Process-conditioned confidence audit

## Scope and guardrails

- No API calls were made.
- Rows share a common schema but are analysed within source, confidence timing, model, and budget strata.
- This is a descriptive mechanism audit; it does not make a causal continuation claim.
- Prospective and retrospective confidence are not pooled because they answer different questions.

## Data inventory

| Source | Rows | Usable confidence | Missing confidence |
|---|---:|---:|---:|
| phase3_process_poc | 720 | 714 | 6 |
| soft_qoq | 720 | 714 | 6 |

## Overall confidence and answer-token association

These rows retain all process states within each experimental stratum; state-specific results follow below.

| Source | Timing | Model | Budget | n | Acc. | Mean conf. | Brier | ECE | Conf-token rho |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| phase3_process_poc | retrospective | DeepSeek-V4-Flash-158B | 512 | 180 | 0.633 | 88.1 | 0.231 | 0.237 | -0.490 |
| phase3_process_poc | retrospective | GLM-5.2-756B | 512 | 180 | 0.067 | 95.1 | 0.882 | 0.884 | -0.083 |
| phase3_process_poc | retrospective | GPT-OSS-120B | 512 | 180 | 0.278 | 64.3 | 0.302 | 0.365 | -0.656 |
| phase3_process_poc | retrospective | GPT-OSS-20B | 512 | 180 | 0.283 | 85.3 | 0.533 | 0.572 | -0.450 |
| soft_qoq | prospective | DeepSeek-V4-Flash-158B | 256 | 90 | 1.000 | 93.6 | 0.009 | 0.064 | -0.601 |
| soft_qoq | prospective | DeepSeek-V4-Flash-158B | 512 | 90 | 0.989 | 93.8 | 0.019 | 0.051 | -0.650 |
| soft_qoq | prospective | GPT-OSS-120B | 256 | 90 | 0.589 | 86.8 | 0.273 | 0.273 | -0.661 |
| soft_qoq | prospective | GPT-OSS-120B | 512 | 90 | 0.467 | 86.6 | 0.365 | 0.395 | -0.756 |
| soft_qoq | retrospective | DeepSeek-V4-Flash-158B | 256 | 90 | 1.000 | 100.0 | 0.000 | 0.000 | NA |
| soft_qoq | retrospective | DeepSeek-V4-Flash-158B | 512 | 90 | 0.989 | 99.9 | 0.011 | 0.011 | 0.006 |
| soft_qoq | retrospective | GPT-OSS-120B | 256 | 90 | 0.589 | 95.3 | 0.362 | 0.364 | -0.588 |
| soft_qoq | retrospective | GPT-OSS-120B | 512 | 90 | 0.467 | 96.1 | 0.482 | 0.494 | -0.646 |

## State-stratified descriptive summaries

| Source | Timing | Model | Budget | State | n | Acc. | Mean conf. | Brier | ECE | Mean answer tok. | Conf-token rho |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| phase3_process_poc | retrospective | DeepSeek-V4-Flash-158B | 512 | complete | 119 | 0.958 | 100.0 | 0.042 | 0.042 | 309.4 | NA |
| phase3_process_poc | retrospective | DeepSeek-V4-Flash-158B | 512 | empty_unfinished | 48 | 0.000 | 55.8 | 0.534 | 0.558 | 512.0 | NA |
| phase3_process_poc | retrospective | DeepSeek-V4-Flash-158B | 512 | visible_unfinished | 13 | 0.000 | 91.7 | 0.908 | 0.917 | 512.0 | NA |
| phase3_process_poc | retrospective | GLM-5.2-756B | 512 | complete | 12 | 1.000 | 100.0 | 0.000 | 0.000 | 447.5 | NA |
| phase3_process_poc | retrospective | GLM-5.2-756B | 512 | empty_unfinished | 112 | 0.000 | 93.1 | 0.927 | 0.931 | 512.0 | NA |
| phase3_process_poc | retrospective | GLM-5.2-756B | 512 | visible_unfinished | 56 | 0.000 | 98.2 | 0.981 | 0.982 | 512.0 | NA |
| phase3_process_poc | retrospective | GPT-OSS-120B | 512 | complete | 54 | 0.926 | 95.4 | 0.049 | 0.028 | 402.9 | -0.450 |
| phase3_process_poc | retrospective | GPT-OSS-120B | 512 | empty_unfinished | 54 | 0.000 | 47.4 | 0.397 | 0.474 | 512.0 | NA |
| phase3_process_poc | retrospective | GPT-OSS-120B | 512 | visible_unfinished | 72 | 0.000 | 53.6 | 0.421 | 0.536 | 512.0 | NA |
| phase3_process_poc | retrospective | GPT-OSS-20B | 512 | complete | 52 | 0.981 | 97.9 | 0.018 | 0.001 | 403.0 | -0.307 |
| phase3_process_poc | retrospective | GPT-OSS-20B | 512 | empty_unfinished | 73 | 0.000 | 74.7 | 0.691 | 0.747 | 512.0 | NA |
| phase3_process_poc | retrospective | GPT-OSS-20B | 512 | visible_unfinished | 55 | 0.000 | 87.4 | 0.804 | 0.874 | 512.0 | NA |
| soft_qoq | prospective | DeepSeek-V4-Flash-158B | 256 | complete | 90 | 1.000 | 93.6 | 0.009 | 0.064 | 263.3 | -0.601 |
| soft_qoq | prospective | DeepSeek-V4-Flash-158B | 512 | complete | 90 | 0.989 | 93.8 | 0.019 | 0.051 | 314.4 | -0.650 |
| soft_qoq | prospective | GPT-OSS-120B | 256 | complete | 57 | 0.930 | 90.9 | 0.064 | 0.023 | 336.9 | -0.514 |
| soft_qoq | prospective | GPT-OSS-120B | 256 | visible_unfinished | 33 | 0.000 | 79.7 | 0.644 | 0.797 | 801.5 | -0.308 |
| soft_qoq | prospective | GPT-OSS-120B | 512 | complete | 49 | 0.857 | 91.3 | 0.125 | 0.069 | 377.7 | -0.329 |
| soft_qoq | prospective | GPT-OSS-120B | 512 | visible_unfinished | 41 | 0.000 | 80.7 | 0.661 | 0.807 | 929.2 | -0.673 |
| soft_qoq | retrospective | DeepSeek-V4-Flash-158B | 256 | complete | 90 | 1.000 | 100.0 | 0.000 | 0.000 | 263.3 | NA |
| soft_qoq | retrospective | DeepSeek-V4-Flash-158B | 512 | complete | 90 | 0.989 | 99.9 | 0.011 | 0.011 | 314.4 | 0.006 |
| soft_qoq | retrospective | GPT-OSS-120B | 256 | complete | 57 | 0.930 | 96.3 | 0.063 | 0.033 | 336.9 | -0.408 |
| soft_qoq | retrospective | GPT-OSS-120B | 256 | visible_unfinished | 33 | 0.000 | 93.5 | 0.879 | 0.935 | 796.6 | 0.059 |
| soft_qoq | retrospective | GPT-OSS-120B | 512 | complete | 49 | 0.857 | 96.9 | 0.130 | 0.112 | 382.3 | -0.324 |
| soft_qoq | retrospective | GPT-OSS-120B | 512 | visible_unfinished | 41 | 0.000 | 95.0 | 0.903 | 0.950 | 929.5 | -0.497 |

## Confidence contrast: complete minus unfinished

Positive values mean complete cases report higher confidence. CIs resample question IDs.

| Source | Timing | Model | Budget | Contrast | Estimate | 95% CI |
|---|---|---|---:|---|---:|---:|
| phase3_process_poc | retrospective | DeepSeek-V4-Flash-158B | 512 | complete_minus_visible_unfinished | 8.3 | [0.0, 25.8] |
| phase3_process_poc | retrospective | DeepSeek-V4-Flash-158B | 512 | complete_minus_empty_unfinished | 44.2 | [28.1, 60.0] |
| phase3_process_poc | retrospective | GLM-5.2-756B | 512 | complete_minus_visible_unfinished | 1.8 | [0.0, 5.9] |
| phase3_process_poc | retrospective | GLM-5.2-756B | 512 | complete_minus_empty_unfinished | 6.9 | [3.1, 11.8] |
| phase3_process_poc | retrospective | GPT-OSS-120B | 512 | complete_minus_visible_unfinished | 41.8 | [30.2, 52.8] |
| phase3_process_poc | retrospective | GPT-OSS-120B | 512 | complete_minus_empty_unfinished | 47.9 | [34.7, 60.0] |
| phase3_process_poc | retrospective | GPT-OSS-20B | 512 | complete_minus_visible_unfinished | 10.6 | [5.4, 17.3] |
| phase3_process_poc | retrospective | GPT-OSS-20B | 512 | complete_minus_empty_unfinished | 23.2 | [16.5, 30.4] |
| soft_qoq | prospective | GPT-OSS-120B | 256 | complete_minus_visible_unfinished | 11.2 | [4.8, 17.1] |
| soft_qoq | prospective | GPT-OSS-120B | 512 | complete_minus_visible_unfinished | 10.6 | [5.9, 15.5] |
| soft_qoq | retrospective | GPT-OSS-120B | 256 | complete_minus_visible_unfinished | 2.7 | [1.0, 5.2] |
| soft_qoq | retrospective | GPT-OSS-120B | 512 | complete_minus_visible_unfinished | 1.9 | [1.2, 2.6] |

## Relation to the Stage 1.6 allocation result

Existing grouped OOF incremental-benefit contrast, P3 state interaction minus P0 process-only: estimate=-0.002, CI=[-0.009, 0.004].
This audit explains alignment and mismatch patterns; it does not reinterpret a non-positive incremental allocation contrast as operational value.

## Interpretation boundary

A confidence–state association is not evidence that confidence should control token allocation. The deployable method remains visible-progress allocation; this audit documents when self-reported confidence agrees with observable progress and when it does not.
