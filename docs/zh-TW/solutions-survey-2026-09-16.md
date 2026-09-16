---
> **歷史文件** — 已被 docs/zh-TW/research-narrative-2026-09-11.md 取代。保留僅供參考。

# 解決 Soft 下校準消失的可能方法 — 文獻調查

> 2026-09-16 更新
> 核心問題：Soft constraint 下準確率高（74-80%）但校準能力消失（差距趨近 0）

---

## 相關文獻與可能方法

### 方法一：CABStop — 校準感知的停止規則

**論文：** Calibration Drift Under Reasoning（arXiv 2606.11211, Apr 2026）

**核心發現：** 推理預算增加時，校準先改善後惡化（非單調），他們稱為 CDUR（Calibration Drift Under Reasoning）。

**他們的解決方案（CABStop）：** 在推理過程中監控信心與 auxiliary accuracy estimate 的差距，當兩者分歧時停止推理。

**與我們的關係：** 這篇論文直接相關——他們的 Hypothesis Lock-In model 解釋了為什麼模型在自由推理時會變得 overconfident。CABStop 提供了一個可能的解決方向。

**可採取的行動：** 在 soft constraint 的情境下，實作一個類似 CABStop 的機制——在推理過程中定期問信心，當信心不再下降時停止推理。這可以用 PM 分析來驗證是否有效。

---

### 方法二：Think Just Enough — 動態信心停止（但加上校準）

**論文：** Think Just Enough（EACL 2026）

**原有方法：** 推理中定期問信心 → 信心夠高就停止。

**我們的問題：** Soft 下校準消失，所以「信心夠高就停」的策略會失效——因為模型對錯題也給 100% 信心。

**可能的改良：** 結合 LCAE 校準後的信心，而不是 raw confidence。如果我們用 IRT 把模型信心校準過，再做 stopping decision 呢？

**這可以連結學姐的 IRT 方法和我們的硬/軟實驗。**

---

### 方法三：Prospective vs Retrospective Confidence

**靈感來源：** 行為經濟學的預測校準研究（forecasting calibration）

**核心想法：** 區分「推理前的預期信心」和「推理後的評估信心」。兩者的差距可能本身就是一個校準訊號——如果事前事後差距大，代表推理過程改變了模型對題目的看法。

**方法：** 
1. 給模型題目和 budget 指示 → 先問：「你預期自己答對的機率？」
2. 模型推理 → 再問：「你現在覺得自己答對的機率？」
3. 比較兩種信心的差距

如果事前事後差距與答對/答錯相關聯，這個差距本身就能作為校準代理指標。

---

### 方法四：VL-Calibration 風格的信心分解

**論文：** VL-Calibration（arXiv 2604.09529, Apr 2026）

**方法：** 把信心分解成「知覺信心」和「推理信心」。對我們來說可以改為「預算遵從信心」和「答題信心」。

**想法：** Soft 下模型可能對「自己有沒有遵守預算」和「答案對不對」有兩種不同的信心。分別問這兩種信心，可能能恢復校準。

---

### 方法五：Log-Probability 替代 Verbalized Confidence

**靈感來源：** Capability Calibration（Yang et al., arXiv 2026）

**方法：** 不用模型「說出來」的信心，而用模型生成答案時第一個 token 的 log-probability。這個內部信號可能比 verbalized 更有區分力。

**風險：** 需要確認 Ollama API 是否支援 log-prob 回傳。

---

### 方法六：Multi-Sample Self-Consistency

**靈感來源：** Self-consistency（Wang et al., ICLR 2023）

**方法：** 對同一題用 temperature > 0 生成多個答案，看答案間的一致性。如果答案一致但錯的，那就是 overconfident。

**缺點：** 需要多次 API 呼叫，成本較高。

---

## 建議優先級

| 方法 | 創新性 | 成本 | 連結現有數據 | 建議 |
|------|--------|------|-------------|------|
| **CABStop 風格（方法一）** | **高**（結合 PM 分析） | 中（需新實驗） | 可用現有 soft 數據當 baseline | 🔴 最推薦 |
| **Prospective vs Retrospective（方法三）** | 中高 | **低**（~360 calls） | 直接從 Soft QOQ 擴展 | 🟡 可以先做 |
| **Think Just Enough + LCAE（方法二）** | 中 | 高（需新實作） | 與學姐方法最直接銜接 | 🟡 論文定位強 |
| **信心分解（方法四）** | 高（新方法） | 低（改 prompt） | 可直接測試 | 🟢 低成本 |
| **Log-prob（方法五）** | 中 | 低（改 API 呼叫） | 依賴 API 支援 | 🟢 先確認可行性 |
| **Self-consistency（方法六）** | 低（已有論文） | 高 | 無 | 不建議 |

---

## 推薦的實驗設計

結合方法一和方法三：**Prospective CABStop-style mechanism**

1. 題目 + soft budget prompt
2. 問 prospective confidence（事前預估）
3. 模型開始推理
4. 定期問 retrospective confidence（事後評估）
5. 比較兩種信心 → 差距大時標記為「可能需要檢查」
6. PM 分析差距與 activity sequence 的關係

這樣既連結了現有數據（soft QOQ），又加入了新的洞察（事前 vs 事後），而且可以用 PM 分析機制。要開始規劃這個實驗嗎？