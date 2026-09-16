# Step 0：零成本診斷 — 執行計畫（v2）

> 2026-09-16
> 定位：免費的可行性／資料品質診斷，產出「pilot 設計建議」
> 不是最終 go/no-go；現有 30 題的 oracle headroom 小，可能只是 L/H 設定不適當

---

## 目標

1. **計算現有條件的收益矩陣** — 每題的準確率差、實際成本差
2. **建立 oracle 成本—準確率曲線** — 在不同平均成本限制下，理想分配能改善多少
3. **比較固定策略基準** — all-L / all-H / random
4. **評估訊號** — prospective confidence vs token cost / correctness / gain
5. **輸出 pilot 設計建議** — L/H 該怎麼設、需要多少題

---

## 分析項目

### 1. 定義實際成本

不使用 prompt 內的名義 256/512，改用實際 completion tokens。

對 Soft QOQ 計算：
- 每模型 × 每 budget 的實際 token 分布
- 256 和 512 的實際 token 差距是否真的夠大
- 如果差距很小 → 現有條件沒有形成足夠不同的運算量

### 2. 收益矩陣

每題計算：
- $P_L(x)$ = 256 下答對比例
- $P_H(x)$ = 512 下答對比例
- $\Delta(x) = P_H(x) - P_L(x)$
- $C_L(x)$ = 256 下平均實際 token
- $C_H(x)$ = 512 下平均實際 token
- $\Delta C(x) = C_H(x) - C_L(x)$

### 3. Oracle 曲線

在不同平均成本限制下，模擬理想分配：
- 選每題 $U(x) = \Delta(x) - \lambda \cdot \Delta C(x)$ 最高的設定
- 畫出 oracle 成本—準確率曲線
- 跟 all-L / all-H / random 比較

如果 oracle 在相同成本下準確率提升 5%，就代表有足夠改善空間。

### 4. 訊號評估

**Token 成本預測（連續值）：**
- prospective confidence vs actual tokens: Spearman r
- 最低信心 20% 的 token 平均 vs 最高信心 20%
- 控制題目長度後的偏相關
- 不使用 AUROC（不適用連續值）

**Correctness 預測（二元）：**
- prospective confidence vs correctness: AUROC
- 跟 retrospective 比較
- 跟 constant baseline 比較

**Gain 預測：**
- 只有當正 gain 題目 > 5 題時才分析
- 否則只報告「gain 變異不足，無法評估」

### 5. 信心成本 vs 效益

- 每次 prospective confidence call 的平均 token 成本
- 若用 confidence 做 allocation，省下的 token 是否超過詢問成本

### 6. Pilot 設計建議

綜合以上結果，輸出：
- 目前 Soft 256/512 的實際成本差是多少
- 若差距不足，建議 L/H 該如何調整
- 需要多少新題目才能產生足夠的 gain 變異
- 哪些訊號值得在 pilot 中繼續測量

---

## 輸出

| 項目 | 檔案 |
|------|------|
| 分析腳本 | `experiments/v3-budget-pilot/step0_diagnosis.py` |
| 數值結果 | `results/step0_diagnosis.json` |
| 報告 | `results/step0_diagnosis.md` |

---

## 成功標準

| 指標 | 評估方式 | 解讀 |
|------|---------|------|
| Oracle headroom | 成本曲線下面積差 | 若 > 5%，有改善空間 |
| L/H 實際成本差 | 平均 token 差 | 若 < 100 tokens，介入強度不足 |
| Conf-tok Spearman | r 值 | 若 < −0.3，信心與成本有關 |
| Conf-correct AUROC | AUROC | 若 > 0.6，信心有區分力 |
| Conf-call 成本 | tokens 數 | 若 > 節省的 token，淨效益為負 |