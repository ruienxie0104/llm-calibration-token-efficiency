# Step 0：零成本診斷 — 執行計畫（v3）

> 2026-09-16
> 定位：免費診斷 + 產出「pilot 設計建議」
> 所有 oracle、random、fixed 策略都需做 question_id cluster bootstrap CI

---

## 目標

1. **收益矩陣** — 每題的準確率差、實際成本差
2. **Oracle 成本—準確率曲線** — 不同平均成本下理想分配能改善多少
3. **成本匹配的隨機 baseline** — 與 oracle 相同實際成本下的隨機升級
4. **訊號診斷** — prospective confidence vs token cost / correctness / gain
5. **Pilot 設計建議** — L/H 該怎麼設、需要多少題

---

## 分析項目

### 1. 定義實際成本

使用兩種成本：
- **completion/reasoning tokens**：模型真正生成了多少
- **total billed tokens**：若可取得，含 prompt input + output
- **confidence-call overhead**：confidence 呼叫增加的完整成本

### 2. 收益矩陣

每題計算（3 replicates 平均）：
- $P_L(x)$ = 256 下答對比例，$P_H(x)$ = 512 下答對比例
- $\Delta(x) = P_H(x) - P_L(x)$
- $C_L(x)$ = 256 下平均實際 token，$C_H(x)$ = 512 下平均
- $\Delta C(x) = C_H(x) - C_L(x)$

輸出散點圖：X = $\Delta C$, Y = $\Delta P$，顏色按 difficulty 分類

### 3. Oracle 策略

每題比較兩個設定的效用：

$$a^*(x)=\arg\max_{a\in\{L,H\}}[P_a(x)-\lambda C_a(x)]$$

- 選 L：效用 = $P_L(x) - \lambda C_L(x)$
- 選 H：效用 = $P_H(x) - \lambda C_H(x)$
- $\lambda$ 在驗證資料上選擇，畫出成本—準確率曲線

### 4. 固定策略基準

- **All-L**：全 Low
- **All-H**：全 High
- **Cost-matched random**：在與 oracle 相同平均實際成本下，隨機選一部分題目升級為 H，多次重複取平均與區間

### 5. Constant baseline

僅用於 correctness 預測，不適用於 gain：
- 從訓練分割估計平均正確率，套用到測試分割
- 比較 Brier、ECE、校準曲線
- 不能從測試資料直接取平均

### 6. 訊號評估

**Token 成本預測（連續值）：**
- prospective confidence vs actual tokens: Spearman r
- 最低信心 20% 的平均 token vs 最高信心 20%
- 控制題目長度後的偏相關

**Correctness 預測（二元）：**
- prospective confidence vs correctness: AUROC
- 跟 retrospective 比較
- 跟 constant baseline 比較

**Gain 預測：**
- 若收益變異不足（正/零/負收益各類數量過少），只呈現收益分布與 oracle headroom
- 不硬產出 predictor 成績

### 7. 信心成本 vs 效益

- 每次 confidence call 的平均 prompt + completion tokens
- 若用 confidence 做 allocation，net saving = 省下的 tokens − 詢問成本

### 8. Bootstrap

所有 oracle、random、fixed 策略的比較都需：
- 以 question_id 為 cluster
- 1000 reps bootstrap
- 報告 95% CI（特別是 `oracle − random` 的 CI）

### 9. Pilot 設計建議

綜合以上結果輸出：
- 目前 Soft 256/512 的實際成本差
- 若差距不足，建議 L/H 該如何調整
- 需要多少新題目才能產生足夠的 gain 變異
- 哪些訊號值得繼續測量

---

## 核心圖表

1. **每題 L/H 成本與收益散點圖** — X=ΔC, Y=ΔP, 顏色=difficulty
2. **實際成本—準確率曲線** — all-L / all-H / cost-matched random / oracle（含 95% CI）

---

## 輸出

| 項目 | 檔案 |
|------|------|
| 分析腳本 | `experiments/v3-budget-pilot/step0_diagnosis.py` |
| 數值結果 | `results/step0_diagnosis.json` |
| 圖表 | `results/step0_figures/` |
| 報告 | `results/step0_diagnosis.md` |

---

## 成功標準

| 指標 | 評估方式 | 解讀 |
|------|---------|------|
| Oracle headroom | 在相同成本下 oracle − random 的 pp 差（含 CI） | > 5 pp 很有希望；需 bootstrap |
| L/H 實際成本差 | 平均 token 差（含 CI） | < 100 tokens → 介入強度不足 |
| Conf-tok Spearman | r 值 | < −0.3 → 信心與成本有關 |
| Conf-correct AUROC | AUROC | > 0.6 → 信心有區分力 |
| Conf-call 成本 | tokens 數 | > 節省的 token → 淨效益為負 |