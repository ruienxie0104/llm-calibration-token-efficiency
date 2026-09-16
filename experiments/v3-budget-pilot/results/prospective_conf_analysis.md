# Prospective vs Retrospective Confidence Analysis
> 360 paired calls, matched by model/question_id/budget/replicate

## 1. Parse / Missing Statistics
- GPT-OSS-120B @ 256: 89/90 parsed (98.9%)
- GPT-OSS-120B @ 512: 85/90 parsed (94.4%)
- DeepSeek-V4-Flash-158B @ 256: 90/90 parsed (100.0%)
- DeepSeek-V4-Flash-158B @ 512: 90/90 parsed (100.0%)

## 2. Prospective vs Retrospective Confidence (Paired)

| Model | Budget | Type | N | Mean | Brier | ECE | AUROC | Gap | Spearman |
|------|--------|------|---|------|-------|-----|-------|-----|----------|
| GPT-OSS-120B       |    256 | Prospective   |  89 |  86.8 | 0.2173 | 0.1824 | 0.4132  |  -2.4 | -0.134   |
| GPT-OSS-120B       |    256 | Retrospective |  89 |  95.3 | 0.2224 | 0.2134 | 0.5159  |   1.5 | 0.0272   |
| GPT-OSS-120B       |    512 | Prospective   |  85 |  86.6 | 0.2069 | 0.2186 | 0.2871  |  -4.5 | -0.3158  |
| GPT-OSS-120B       |    512 | Retrospective |  85 |  96.1 | 0.2102 | 0.2035 | 0.3824  |  -0.6 | -0.1862  |
| DeepSeek-V4-Flash-158B |    256 | Prospective   |  90 |  93.6 | 0.1930 | 0.1783 | 0.3603  |  -3.1 | -0.2111  |
| DeepSeek-V4-Flash-158B |    256 | Retrospective |  90 | 100.0 | 0.2000 | 0.2000 | 0.5     |   0.0 | nan      |
| DeepSeek-V4-Flash-158B |    512 | Prospective   |  90 |  93.8 | 0.1700 | 0.1461 | 0.4016  |  -2.2 | -0.1406  |
| DeepSeek-V4-Flash-158B |    512 | Retrospective |  90 |  99.9 | 0.1778 | 0.1772 | 0.4932  |  -0.1 | -0.0493  |

## 3. LCAE Comparison

| Model | Budget | Prospective LCAE | Retrospective LCAE | Hard LCAE |
|-------|--------|-----------------|-------------------|-----------|
| GPT-OSS-120B       |    256 | 0.2222          | 0.298             | 0.24692308093788887 |
| GPT-OSS-120B       |    512 | 0.2213          | 0.3063            | 0.24692308093788887 |
| DeepSeek-V4-Flash-158B |    256 | 0.2544          | 0.3099            | 0.3026138313331503 |
| DeepSeek-V4-Flash-158B |    512 | 0.2539          | 0.3095            | 0.3026138313331503 |

*Note: Prospective/Soft LCAE uses Phase 3 IRT parameters (anchored LCAE)*

## 4. Confidence vs Actual Tokens


**GPT-OSS-120B:**
- Budget 256: conf-tok Spearman r = -0.661
  - conf-correct Spearman r = -0.134
  - Low-conf (<70) mean tok: None (n=0)
  - High-conf (>=90) mean tok: 346.8 (n=54)
- Budget 512: conf-tok Spearman r = -0.7557
  - conf-correct Spearman r = -0.3158
  - Low-conf (<70) mean tok: 785.0 (n=2)
  - High-conf (>=90) mean tok: 348.2 (n=51)

**DeepSeek-V4-Flash-158B:**
- Budget 256: conf-tok Spearman r = -0.6013
  - conf-correct Spearman r = -0.2111
  - Low-conf (<70) mean tok: None (n=0)
  - High-conf (>=90) mean tok: 187.2 (n=70)
- Budget 512: conf-tok Spearman r = -0.6498
  - conf-correct Spearman r = -0.1406
  - Low-conf (<70) mean tok: None (n=0)
  - High-conf (>=90) mean tok: 220.2 (n=70)

## 5. Missing Data Note
GPT-OSS-120B had ~3% parse failures (6/180 calls). These were consistently on one hard counting_and_probability question
where `done_reason=length` cut the thinking process before confidence could be output. All failures excluded from analysis.

## 6. Limitations
- Anchored LCAE uses Phase 3 IRT params, not Soft-specific calibration
- Paired analysis only covers matched calls; unmatched calls excluded
- Small sample (n=90 per model×budget) limits AUROC reliability

## 7. Next Steps
- If prospective shows improvement → external budget controller
- If similar → compare with IRT difficulty, token entropy, hybrid signal
- If still overconfident → post-hoc scaling or percentile-based allocation
