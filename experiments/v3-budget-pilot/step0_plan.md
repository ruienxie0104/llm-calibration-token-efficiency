# Step 0：零成本診斷 — 執行計畫

> 2026-09-16
> 完全使用現有資料，不新增 API 呼叫

---

## 目標

在投入新實驗前，先用現有資料回答六個問題：

1. **Constant baseline 是否已接近最佳？** — 只用整體平均正確率當信心，會不會比逐題信心更好？
2. **信心對 correctness / token / gain 的預測力各是多少？** — 三個目標要分開看
3. **現有題目有沒有足夠的 oracle headroom？** — 如果連理想分配都無法改善，就不值得繼續
4. **Prospective vs retrospective 的差異在 bootstrap 下是否顯著？** — 不是只看 point estimate
5. **信心呼叫成本佔總成本多少？** — 如果詢問信心本身就要花 token，淨收益可能為負
6. **IRT difficulty 對 accuracy gain 的預測力 vs confidence 的預測力？**

---

## 分析項目

### 1. Constant-confidence baseline

計算每個模型 × budget × condition 的整體平均正確率：

```
constant = avg_accuracy
confidence_i = constant  for all questions i
```

然後計算這個常數 baseline 的 Brier 和 AUROC，跟 prospective / retrospective 比較。

如果常數 baseline 的 Brier 已經接近或甚至優於模型信心，就代表模型的逐題信心沒有提供額外資訊。

### 2. 信心 vs 三個目標的分離分析

對 prospective 和 retrospective 分別計算：

**目標 A — correctness：**
- AUROC、Brier、Spearman r（信心 vs 正確/錯誤）
- 信心差距（答對平均−答錯平均）
- reliability curve（10 bins）

**目標 B — token cost：**
- Spearman r（信心 vs actual completion tokens）
- low-confidence（<70）平均 token vs high-confidence（>=90）平均 token
- 控制題目長度後的偏相關

**目標 C — accuracy gain（256→512）：**
- Spearman r（信心 vs accuracy gain）
- 跟 IRT difficulty 對 gain 的預測力比較
- 注意：現有 30 題只有 1 題有正 gain，這個分析的統計力非常有限

### 3. Oracle headroom 分析

計算「如果我們知道每題的真實最佳預算選擇，能改善多少？」：

```
oracle = sum(max(acc_low_i, acc_high_i)) / N - actual_accuracy
```

比較：
- All Low 的總準確率
- All High 的總準確率
- Oracle 選擇（每題選最好的）
- 隨機分配（相同比例 High）

如果 oracle 只比 fixed 好 1-2%，就代表現有題目/預算沒有足夠 headroom。

### 4. Bootstrap 信心區間

用 question_id 為 cluster 做 1000 reps bootstrap：
- Prospective Brier 的 95% CI
- Retrospective Brier 的 95% CI
- 兩者差異的 95% CI
- Prospective AUROC 的 95% CI

如果兩者的 CI 大量重疊，就不能說 prospective「顯著優於」retrospective。

### 5. 信心成本 vs 效益

從現有資料計算：
- 每次 confidence call 平均花費多少 token（prompt + completion）
- 如果用 prospective confidence 做 allocation，多花的成本 vs 省下的 token

### 6. IRT difficulty vs confidence vs gain

對每題：
- IRT beta（從 Phase 3）
- Prospective confidence（新資料）
- Accuracy gain（256→512）
- Token increase（256→512）

計算兩兩 Spearman correlation，看 IRT 和 confidence 對 gain 的預測力是否不同。

---

## 輸出

| 項目 | 檔案 |
|------|------|
| Step 0 分析腳本 | `experiments/v3-budget-pilot/step0_diagnosis.py` |
| 數值結果 | `results/step0_diagnosis.json` |
| 報告 | `results/step0_diagnosis.md` |

### 報告結構

1. 資料概況（使用哪些資料、多少 calls、多少 paired）
2. Constant-confidence baseline
3. 三個目標的分離分析（表格 + bootstrap CI）
4. Oracle headroom
5. 信心成本 vs 效益
6. IRT vs confidence vs gain 比較
7. 總結：是否進入 Step 1（budget-range pilot）？

---

## Go/No-Go 條件

| 條件 | 如果成立 | 決策 |
|------|---------|------|
| Constant baseline Brier 優於或接近模型信心 | 逐題信心無額外資訊 | ❌ 不建議繼續 |
| Oracle headroom < 2% | 沒有足夠改善空間 | ❌ 不建議繼續 |
| Prospective 和 Retrospective 的 CI 大量重疊 | 兩者無實質差異 | ⚠️ 需重新設計 |
| Confidence call 成本 > 節省的 token | 淨效益為負 | ❌ 不建議繼續 |
| 以上全部不成立 | 有足夠 headroom | ✅ 進入 Step 1 |