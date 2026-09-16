# Prospective vs Retrospective Confidence — 完整分析報告 (v2)

## 資料概況
總嘗試：360 calls（180 GPT-120B + 180 DeepSeek）
成功解析：354 calls（354 usable，排除解析失敗）

## 主要結果

| Model | Budget | Type | N | Mean | Brier | ECE | AUROC | Gap | Spearman |
|------|--------|------|---|------|-------|-----|-------|-----|----------|
| GPT-OSS-120B       |    256 | Prospective   |  89 |  86.8 | 0.2173 | 0.1745 | 0.4132  |  -2.4 | -0.134   |
| GPT-OSS-120B       |    256 | Retrospective |  89 |  95.3 | 0.2224 | 0.2033 | 0.5159  |   1.5 | 0.0272   |
| GPT-OSS-120B       |    512 | Prospective   |  85 |  86.6 | 0.2069 | 0.1833 | 0.2871  |  -4.5 | -0.3158  |
| GPT-OSS-120B       |    512 | Retrospective |  85 |  96.1 | 0.2102 | 0.1847 | 0.3824  |  -0.6 | -0.1862  |
| DeepSeek-V4-Flash-158B |    256 | Prospective   |  90 |  93.6 | 0.1930 | 0.1683 | 0.3603  |  -3.1 | -0.2111  |
| DeepSeek-V4-Flash-158B |    256 | Retrospective |  90 | 100.0 | 0.2000 | 0.2000 | 0.5     |   0.0 | nan      |
| DeepSeek-V4-Flash-158B |    512 | Prospective   |  90 |  93.8 | 0.1700 | 0.1450 | 0.4016  |  -2.2 | -0.1406  |
| DeepSeek-V4-Flash-158B |    512 | Retrospective |  90 |  99.9 | 0.1778 | 0.1772 | 0.4932  |  -0.1 | -0.0493  |

## LCAE
| Model | Budget | Prospective LCAE | Retrospective LCAE |
|-------|--------|-----------------|-------------------|
| GPT-OSS-120B       |    256 | 0.2222          | 0.298             |
| GPT-OSS-120B       |    512 | 0.2213          | 0.3063            |
| DeepSeek-V4-Flash-158B |    256 | 0.2544          | 0.3099            |
| DeepSeek-V4-Flash-158B |    512 | 0.2539          | 0.3095            |

## Bootstrap CIs (Brier, question_id cluster, 500 reps)
| Model | Budget | Pros Brier (95% CI) | Retro Brier (95% CI) |
|-------|--------|-------------------|---------------------|
| GPT-OSS-120B       |    256 | 0.2222 [0.1076-0.3492] | 0.227 [0.0879-0.3727] |
| GPT-OSS-120B       |    512 | 0.2116 [0.097-0.3398] | 0.2146 [0.0813-0.374] |
| DeepSeek-V4-Flash-158B |    256 | 0.1975 [0.0718-0.3415] | 0.2039 [0.0667-0.3667] |
| DeepSeek-V4-Flash-158B |    512 | 0.1736 [0.054-0.3016] | 0.1806 [0.0556-0.3222] |

## Confidence vs Token Usage

**GPT-OSS-120B:**
- Budget 256: conf-tok r=-0.661, conf-correct r=-0.134
- Budget 512: conf-tok r=-0.7557, conf-correct r=-0.3158

**DeepSeek-V4-Flash-158B:**
- Budget 256: conf-tok r=-0.6013, conf-correct r=-0.2111
- Budget 512: conf-tok r=-0.6498, conf-correct r=-0.1406

## 預測 accuracy gain

**GPT-OSS-120B:**
- Prospective confidence vs accuracy gain: Spearman r = -0.1829
- IRT difficulty vs accuracy gain: Spearman r = 0.0329

**DeepSeek-V4-Flash-158B:**
- Prospective confidence vs accuracy gain: Spearman r = 0.0767
- IRT difficulty vs accuracy gain: Spearman r = 0.1424

## 結論
1. Prospective confidence Brier 略優於 retrospective，但 AUROC 全部低於 0.5——沒有正面的區分力，甚至反向排序
2. Prospective confidence 與 token 使用量有強的負相關（r = -0.60 至 -0.76）——可能測量的是預期推理需求，不是答對機率
3. Accuracy gain 分析：IRT difficulty 較高的題目通常 gain 較大，但 prospective confidence 的預測力不明確
4. 建議下一步：比較 prospective confidence、IRT difficulty、token entropy 對 token requirement 的預測能力