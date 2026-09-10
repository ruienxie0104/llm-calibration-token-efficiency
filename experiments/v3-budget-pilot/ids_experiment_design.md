# IDS Intervention Experiment — 完整設計文件

> 給 Kimiko 審視用
> 最後更新：2026-09-10

---

## 一、實驗動機

### 1.1 Kimiko 的疑慮

在 Phase 3 的結果中，我們發現：

- 低預算下表現最好的是 **DeepSeek**（256 tokens 有 18.3%）
- 校準最好的是 **GPT-120B**（LCAE = 0.247）
- 這兩個不是同一個模型

這個結果呈現的是「能力強 + 推理效率高 → 低預算表現好」，而不是「校準好 → 低預算表現好」。兩者之間存在一個因果鏈上的 gap。

### 1.2 Phase 3 的本質

Phase 3 是 **correlational（相關性）研究**——我們觀察到校準品質和 token 效率之間有關聯，但無法宣稱「改善校準就能改善效率」。

### 1.3 IDS 實驗的定位

IDS（Item Difficulty Signal）實驗是 **interventional（因果性）研究**——透過操控「是否給模型難度訊號」這個變數，我們可以驗證校準改善是否能因果性地導致 token 分配效率改善。

這是跟所有競爭者最明顯的差異化，也是學姐論文最直接的延伸。

---

## 二、IDS 的概念說明

### 2.1 什麼是 IDS？

IDS 全名是 **Item Difficulty Signal（題目難度訊號）**，由 Chen et al.（IEEE IRI 2026）提出。

在原本的實驗中，模型收到的 prompt 只有題目本身：

```
User: Solve the math problem step by step...
[題目]
```

IDS 的做法是在 prompt 中額外提供題目的難度資訊：

```
User: This problem is rated difficulty 4 (difficult).
Solve the math problem step by step...
[題目]
```

### 2.2 IDS 的理論基礎

學姐論文已經證明：

1. IRT 可以客觀計算每題對每個模型的難度（β）
2. 提供難度訊號（IDS）可以改善模型的信心校準（LCAE）
3. 改善校準不影響模型原始答題能力

### 2.3 本研究的延伸

我們想驗證的是：**IDS 改善校準之後，token 分配效率是否跟著改善？**

---

## 三、實驗設計

### 3.1 Overview

| 參數 | 設定 | 說明 |
|------|------|------|
| 模型 | GPT-OSS-120B, DeepSeek-V4-Flash-158B | 選校準最好 vs 能力最強 |
| 條件 | QOQ（無 IDS）, IDS（有 IDS） | 這是唯一的操控變數 |
| Token 預算 | 256, 512 | 低預算區間 |
| 題目 | 30 題 MATH-500（L3 + L4） | 跟 Phase 3 同樣的難度區間 |
| 重複 | 3 次 | 控制隨機波動 |
| 信心收集 | 每次答完立刻問 | 所有條件都一樣 |

### 3.2 為什麼選這兩個模型？

| 模型 | 理由 |
|------|------|
| **GPT-OSS-120B** | 校準最好（LCAE=0.247）——看校準已經很好的模型，IDS 還有沒有改善空間 |
| **DeepSeek** | 能力最強（θ=+0.65）——看 IDS 能不能改善它的 overconfidence（答錯時仍給 99-100% 信心） |

兩個模型在 Phase 3 的表現完全不同，可以互為對照。

### 3.3 為什麼選 256 和 512？

- **128** 在 Phase 2-3 中幾乎所有人都 0%，沒有資訊量 → 排除
- **256**——Phase 3 中 DeepSeek 18%、其他模型 0%，是最有區分力的預算
- **512**——Phase 3 中 DeepSeek 50%、GPT-120B 17%，能看到中度預算下的差異
- **1024**——接近無限制，差異最小化 → 對 IDS 的檢驗力較低

### 3.4 為什麼選 QOQ 和 IDS 兩種條件都要跑（不直接用 Phase 3 數據當對照）？

因為 intervention 實驗需要乾淨的 **paired comparison**：

- 同一模型、同一題目、同一 budget
- 唯一變數是「有沒有給難度訊號」
- 如果用 Phase 3 的數據當 QOQ，題目不同、模型 run 不同，無法做 paired test

### 3.5 實驗規模

2 模型 × 2 條件 × 2 budgets × 3 reps × 30 題 × 2（answer + confidence） = **1440 次 API 呼叫**

### 3.6 預期時間

約 20-30 分鐘（含 API latency）。

---

## 四、難度分級方法

### 4.1 β 的來源

Phase 3 已經算出 60 題 MATH-500 L3+L4 的 IRT 題目難度 β（使用 Rasch Model 估計）。

### 4.2 β → 難度等級

β 是連續值，需要轉換成模型能理解的語言。目前使用數學題目本身的 Level 作為簡易代理：

| MATH Level | β proxy | 難度文字 |
|-----------|---------|---------|
| 3 | 0 | moderate |
| 4 | 1 | difficult |

未來的正式版本可以用 Phase 3 實際算出的 β 進行更精細的 5 級分級（very easy / easy / moderate / difficult / very difficult）。

### 4.3 Prompt 範例

**QOQ（對照組）：**

```
User: Solve the math problem step by step, then give the final answer in \boxed{}.

If $f(x) = \frac{3x-2}{x-2}$, what is the value of $f(-2)+f(-1)+f(0)$? Express your answer as a common fraction.
```

**IDS（實驗組）：**

```
User: This problem is rated difficulty 4 (difficult).
Solve the math problem step by step, then give the final answer in \boxed{}.

If $f(x) = \frac{3x-2}{x-2}$, what is the value of $f(-2)+f(-1)+f(0)$? Express your answer as a common fraction.
```

---

## 五、分析計畫

### 5.1 主要分析

跑完後比較 QOQ vs IDS 在以下指標的差異：

**A. 準確率變化**
- IDS 組的準確率是否顯著高於 QOQ 組？
- 特別關注 @256：IDS 能否讓原本 0% 的模型答對一些題目？

**B. 信心校準變化**
- IDS 組的 Brier 和 LCAE 是否低於 QOQ 組？
- IDS 組的信心差距（答對−答錯）是否更大？

**C. 信心與實際對錯的對應**
- DeepSeek 答錯時給 100% 的現象在 IDS 條件下是否改善？
- GPT-120B 的信心分佈是否變得更有區分力？

### 5.2 可能結果與判讀

| QOQ vs IDS | 準確率 ↑ | 準確率不變 |
|-----------|---------|-----------|
| **LCAE 改善** | ✅ 因果鏈成立 | 校準改善但未轉換成效率 → 需調整故事 |
| **LCAE 不變** | IDS 直接影響了行為（非透過校準） | IDS 對這些模型無效 |

### 5.3 成功條件

因果鏈成立的最強證據組合：
1. IDS 組 LCAE 顯著低於 QOQ 組（校準改善 ✅）
2. IDS 組低預算準確率顯著高於 QOQ 組（效率改善 ✅）
3. LCAE 改善幅度與準確率改善幅度正相關（因果中介 ✅）

---

## 六、與 Phase 3 的比較

| 面向 | Phase 3 | IDS Experiment |
|------|---------|----------------|
| 研究類型 | Correlational（觀察性） | Interventional（因果性） |
| 核心問題 | 校準好的模型表現如何？ | 改善校準能否改善表現？ |
| 操控變數 | 無 | IDS（給不給難度訊號） |
| 模型 | 4 個 | 2 個（120B + DeepSeek） |
| 題目 | 60 題 | 30 題 |
| Budgets | 3 個（256/512/1024） | 2 個（256/512） |
| 總呼叫 | 4320 | 1440 |

---

## 七、程式架構

```
run_ids.py
├── load_questions()         — 從 MATH-500 載入 30 題
├── compute_difficulty()     — 計算/載入每題難度 β
├── call_ollama()            — API 呼叫（含 budget 限制）
├── extract_boxed()          — 從 \boxed{} 取出答案
├── is_correct()             — 比對正確答案
├── parse_confidence()       — 從文字中解析信心數字 0-100
├── make_ids_prompt()        — 產生含 IDS 的 prompt
├── make_answer_prompt()     — 產生答題 prompt（QOQ/IDS）
└── main()                   — 四層迴圈執行 + 即時分析
```

**Checkpoint 機制：** 每 50 次呼叫存一次 `results/ids_raw.json`。中斷後重跑會跳過已完成的部分。

**輸出：** `results/ids_raw.json`（所有 1440 次回應 + 即時摘要）
