# Process-allocation PoC dataset audit

> Generated from raw Phase 3 responses; no API calls are made.

## Pairing

- Paired rows: **720**
- Unique questions: **60**
- Models: **4**
- Missing confidence rows: **6**
- Low/high budgets: **512 → 1024**

## Outcome distribution

| Model | n | Low acc. | High acc. | Benefit | Harm | Median prefix similarity |
|---|---:|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-158B | 180 | 63.3% | 81.1% | 18.3% | 0.6% | 0.016 |
| GLM-5.2-756B | 180 | 6.7% | 47.2% | 40.6% | 0.0% | 0.000 |
| GPT-OSS-120B | 180 | 27.8% | 68.3% | 40.6% | 0.0% | 0.023 |
| GPT-OSS-20B | 180 | 28.3% | 65.0% | 36.7% | 0.0% | 0.005 |

## Interpretation guardrails

- `benefit=1` means the independently generated low-budget answer was wrong and the high-budget answer was correct.
- Phase 3 did not resume the same generation. The gain is therefore an observational counterfactual proxy, not a causal continuation effect.
- `incremental_token_proxy` must not be presented as measured continuation cost.
- Process features use only the low-budget response.
- Cross-validation must group all rows sharing a question ID.

Class counts: no benefit=475, benefit=245.
