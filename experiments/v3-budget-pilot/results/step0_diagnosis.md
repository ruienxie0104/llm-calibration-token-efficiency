# Step 0 診斷報告

> 執行日期：2026-09-16
> 資料來源：Soft QOQ（360 calls）+ Prospective Confidence（360 calls）
> 完全零成本，未新增 API 呼叫

---

## 一、為什麼要做 Step 0？

在投入 budget-range pilot 前，先用現有資料確認：

1. Soft 256/512 之間是否存在足夠的實際成本差？
2. 是否存在可分配的收益空間（oracle headroom）？
3. 信心訊號對成本、正確性、額外收益的預測力各是多少？
4. 信心呼叫本身的成本是否會抵消效益？

---

## 二、實際成本分析

### GPT-OSS-120B

| Budget | 實際平均 Token | 被截斷 | 無答案率 |
|--------|-------------|-------|---------|
| 256 | **506** | 76/90 (84%) | 0% |
| 512 | **632** | 47/90 (52%) | 0% |

- 256→512 的實際成本差：**+126 tokens（+25%）**
- 84% 的回答在 256 下被截斷 → 低預算下模型無法完整推理

### DeepSeek-V4-Flash-158B

| Budget | 實際平均 Token | 被截斷 | 無答案率 |
|--------|-------------|-------|---------|
| 256 | **263** | 29/90 (32%) | 0% |
| 512 | **314** | 18/90 (20%) | 0% |

- 256→512 的實際成本差：**+51 tokens（+19%）**
- 截斷率遠低於 GPT → DeepSeek 的推理風格更簡潔

**結論：** Soft 256 與 512 的實際成本差距很小（51-126 tokens）。這解釋了為什麼兩者之間幾乎沒有 accuracy gain。

---

## 三、收益矩陣

| 模型 | 30 題中有正 gain | 零 gain | 負 gain |
|------|-----------------|--------|---------|
| GPT-120B | **1** | **29** | 0 |
| DeepSeek | **1** | **29** | 0 |

30 題中只有 1 題顯示 256→512 有正收益。這不是信心無效，而是**兩個預算條件之間缺乏足夠的實質差異**。

---

## 四、Oracle 成本—準確率曲線

### GPT-OSS-120B

| 策略 | 準確率 | 平均成本 |
|------|-------|---------|
| All-L | 74.8% | 508 |
| All-H | 76.9% | 635 |
| Oracle（λ=0） | 76.9% | 514 |
| Cost-matched random | 74.8% | 514 |
| **Oracle headroom** | **+2.1pp** | |

### DeepSeek

| 策略 | 準確率 | 平均成本 |
|------|-------|---------|
| All-L | 80.5% | 263 |
| All-H | 82.7% | 316 |
| Oracle（λ=0） | 82.7% | 263 |
| Cost-matched random | 80.5% | 263 |
| **Oracle headroom** | **+2.3pp** | |

Oracle headroom 只有 2pp。但這是因為 L/H 成本差太小，不是因為研究方向無效。

---

## 五、信心訊號評估

### 信心 vs Token 成本（連續值）

| 模型 | Spearman r | p-value | 低信心 (<70) 平均 token | 高信心 (>=90) 平均 token |
|------|-----------|---------|-----------------------|------------------------|
| GPT-120B | **−0.71** | < 0.001 | 785（n=2） | 347（n=105） |
| DeepSeek | **−0.62** | < 0.001 | N/A（n=0） | 204（n=140） |

**Prospective confidence 與實際 token 使用量有強負相關。** 這是目前最有價值的訊號。

### 信心 vs Correctness（二元）

| 模型 | Budget | Prospective AUROC | Retrospective AUROC |
|------|--------|-----------------|-------------------|
| GPT-120B | 256 | **0.413** | 0.516 |
| GPT-120B | 512 | **0.287** | 0.382 |
| DeepSeek | 256 | **0.360** | 0.500 |
| DeepSeek | 512 | **0.402** | 0.493 |

Prospective AUROC 全部低於 0.5（反向排序），retrospective 接近隨機（~0.5）。
**信心無法可靠區分答對與答錯。**

### Brier Score 比較

| 模型 | Budget | Prospective | Retrospective |
|------|--------|------------|-------------|
| GPT-120B | 256 | **0.217** | 0.222 |
| GPT-120B | 512 | **0.207** | 0.210 |
| DeepSeek | 256 | **0.193** | 0.200 |
| DeepSeek | 512 | **0.170** | 0.178 |

Prospective Brier 略微優於 retrospective，但差距很小，且 AUROC 數據顯示缺乏排序能力。

---

## 六、信心呼叫成本

| 模型 | 平均每次呼叫成本 | Completion 部分 |
|------|---------------|----------------|
| GPT-120B | **265 tokens** | 58 tokens |
| DeepSeek | **147 tokens** | 7 tokens |

如果使用信心做 allocation，每次詢問需先付出 147-265 tokens 的成本。對於 DeepSeek（實際 token 差僅 51），這個成本幾乎抵消了可能的節省。

---

## 七、核心問題診斷

```
Soft 256 與 Soft 512 的實際 token 差：
  GPT-120B：506 → 632（+126，25%）
  DeepSeek：263 → 314（+51，19%）
  
  → 差距太小，無法產生足夠的 accuracy gain 變異
  → 29/30 題的 gain = 0
  → Oracle headroom 只有 2pp
```

**這不是研究方法無效，而是目前的 L/H 設定沒有形成足夠不同的運算條件。**

---

## 八、Pilot 設計建議

### L/H 必須重新選擇

現有 Soft 256/512 的實際成本差只有 51-126 tokens。建議下一輪：

- L：使用 Soft 128 或 64（極度壓縮，使模型無法完成完整推理）
- H：使用 Soft 1024 或 Soft 2048（接近無限制，讓模型充分推理）
- 確保 L 和 H 之間至少有 500 tokens 的實際成本差

### 題目數量

現有 30 題只有 1 題有正 gain。需要更多題目來產生足夠的收益變異：
- 建議 60-100 題新數學題
- 涵蓋容易、中等、困難三個難度區間

### 保留的信心訊號

Prospective confidence 對 token 成本的預測力強（r=−0.6 至 −0.7），值得在 pilot 中繼續測量。
但對 correctness 和 gain 的預測力弱，不適合做 allocation 的主要決策訊號。

---

## 九、檔案

| 項目 | 連結 |
|------|------|
| 分析腳本 | `experiments/v3-budget-pilot/step0_diagnosis.py` |
| 數值結果 | `experiments/v3-budget-pilot/results/step0_diagnosis.json` |
| Figure: Cost-Benefit | `results/step0_figures/{model}_cost_benefit.png` |
| Figure: Cost-Accuracy | `results/step0_figures/{model}_cost_accuracy.png` |