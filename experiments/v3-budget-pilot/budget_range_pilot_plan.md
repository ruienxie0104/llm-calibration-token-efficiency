# Budget-Range Pilot 規劃（v2）

> 2026-09-16
> 目的：掃描 Soft budget 是否真的能形成實際成本差與收益變異

---

## 實驗定位

這輪只回答一個問題：**Soft prompt 是否能可靠地控制推理 token 成本？**

- 不測試 confidence（留到 Phase B）
- 不預測 gain（只檢查收益分布）
- 所有 L/H 組合都分析（15 對）

---

## 實驗設計

### 模型

GPT-OSS-120B 優先（Soft 遵從度低、token 範圍廣，對成本差更敏感）

### 題目

30 題 MATH-500 Level 3+4（與 Phase 3 相同，便於比較）

### Budgets

64 / 128 / 256 / 512 / 1024 / 2048

### 規模

```
1 模型 × 30 題 × 6 budgets × 2 reps = 360 calls
（不含 confidence calls — 待選定有效 L/H 後再測）
```

---

## 分析

對每個 budget 計算：
- 實際 completion tokens（平均、分佈、中位數）
- 準確率
- `over_soft_budget_rate`：超過 prompt 建議預算的比例
- `answer_parse_rate`：可解析答案的比例
- `api_length_stop_rate`：有 stop reason 時才報告

對所有 15 對 L/H 組合計算：
- 實際 token 差（中位數、CI）
- 平均 accuracy gain（H − L）
- 逐題 gain 分布（正 / 零 / 負比例）
- 答案可解析率差異

---

## L/H 選擇條件

同時滿足以下四項才選用：

1. **成本可分離**：H 的實際 token 明顯高於 L，bootstrap CI 不大量重疊
2. **答案有效**：L 不會出現大量無法解析或無最終答案
3. **收益有變異**：逐題 L→H gain 有正、零兩類以上
4. **成本與收益有取捨**：不是 H 對所有題都同時更準、更便宜

---

## Go/No-Go

若掃完 64-2048 後仍發現：
- 不同 Soft budget 的實際 token 幾乎重疊
- 或模型頻繁超過所有 Soft budget
- 或成本有差但逐題 gain 幾乎全為零

→ **Soft prompt 不是可靠的成本控制介面**，改用 hard cap 或 sampling-based compute。

---

## 文件註記

> 本輪 30 題僅用於設定選擇。選出的 L/H 必須在新的、未使用題目上進行正式評估。