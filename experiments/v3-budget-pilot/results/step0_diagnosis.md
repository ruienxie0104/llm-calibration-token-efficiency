# Step 0 診斷報告 v2（修正版）

**修正項目：** Soft 截斷判定、Cost-matched random 實作、Bootstrap CI、分 budget 訊號評估


## GPT-OSS-120B

### 1. 實際成本分析
  Budget 256: n=90, avg_tok=506, over_budget=59/90 (66%)
  Budget 512: n=90, avg_tok=632, over_budget=35/90 (39%)

### 2. 收益矩陣
  Positive gain (>0.05): 1/30
  Zero gain: 29/30

### 3. Oracle 策略（含 Bootstrap CI）
  λ=  0: Oracle=76.8% cost=512 | Random=74.8% cost=512 | Headroom=2.0pp 95%CI=[0.0,5.9]
  λ=  1: Oracle=76.8% cost=494 | Random=74.6% cost=507 | Headroom=2.2pp 95%CI=[0.0,6.7]
  λ=  2: Oracle=76.5% cost=495 | Random=74.3% cost=506 | Headroom=2.2pp 95%CI=[0.0,6.7]
  λ=  5: Oracle=74.6% cost=486 | Random=74.6% cost=503 | Headroom=0.0pp 95%CI=[-0.0,0.0]
  λ= 10: Oracle=74.5% cost=490 | Random=74.5% cost=506 | Headroom=-0.0pp 95%CI=[-0.0,0.0]

### 4. 信心訊號評估

**Confidence vs Token Cost (per budget):**
  Budget 256: conf-tok Spearman r=-0.6610 | Top 20% tok=337 Bot 20% tok=833
  Budget 512: conf-tok Spearman r=-0.7557 | Top 20% tok=323 Bot 20% tok=1163

**Confidence vs Correctness (AUROC, paired):**
  Budget 256: Pros Brier=0.2173 AUROC=0.4132 | Retro Brier=0.2224 AUROC=0.5159
  Budget 512: Pros Brier=0.2069 AUROC=0.2871 | Retro Brier=0.2102 AUROC=0.3824

### 5. 信心呼叫成本
  Budget 256: avg_call_cost=265tok (completion=62)
  Budget 512: avg_call_cost=257tok (completion=55)

## DeepSeek-V4-Flash-158B

### 1. 實際成本分析
  Budget 256: n=90, avg_tok=263, over_budget=16/90 (18%)
  Budget 512: n=90, avg_tok=314, over_budget=13/90 (14%)

### 2. 收益矩陣
  Positive gain (>0.05): 1/30
  Zero gain: 29/30

### 3. Oracle 策略（含 Bootstrap CI）
  λ=  0: Oracle=82.6% cost=263 | Random=80.3% cost=263 | Headroom=2.3pp 95%CI=[0.0,6.6]
  λ=  1: Oracle=82.1% cost=256 | Random=80.0% cost=262 | Headroom=2.2pp 95%CI=[0.0,6.7]
  λ=  2: Oracle=82.1% cost=257 | Random=79.9% cost=264 | Headroom=2.2pp 95%CI=[0.0,6.7]
  λ=  5: Oracle=82.7% cost=254 | Random=80.3% cost=261 | Headroom=2.4pp 95%CI=[0.0,6.7]
  λ= 10: Oracle=82.3% cost=258 | Random=80.0% cost=264 | Headroom=2.3pp 95%CI=[0.0,8.9]

### 4. 信心訊號評估

**Confidence vs Token Cost (per budget):**
  Budget 256: conf-tok Spearman r=-0.6013 | Top 20% tok=142 Bot 20% tok=545
  Budget 512: conf-tok Spearman r=-0.6498 | Top 20% tok=132 Bot 20% tok=636

**Confidence vs Correctness (AUROC, paired):**
  Budget 256: Pros Brier=0.1930 AUROC=0.3603 | Retro Brier=0.2000 AUROC=0.5000
  Budget 512: Pros Brier=0.1700 AUROC=0.4016 | Retro Brier=0.1778 AUROC=0.4932

### 5. 信心呼叫成本
  Budget 256: avg_call_cost=147tok (completion=7)
  Budget 512: avg_call_cost=147tok (completion=7)

## 總結
1. Soft 256/512 的實際 token 差距有限 — budget-range pilot 需要重新選擇 L/H
2. 30 題中幾乎無 visibility gain — 需更多題目
3. Prospective confidence 與 token 成本有負相關（分 budget Spearman r ≈ −0.5 至 −0.7）
4. 信心對 correctness 無正向區分力（AUROC < 0.5）
5. 信心呼叫本身需 150-270 tokens，需計入總成本