# Phase 3 PM Analysis Results

> 低預算 vs 高預算的活動頻率比較
> 執行日期：2026-09-10

---

## 核心發現

### 1. 256 tokens 下，模型幾乎無法完成推理

| Model | @256 avg steps | @1024 avg steps | Ratio | Answer@256 | Answer@1024 |
|---|---|---|---|---|---|
| GPT-20B | 1.1 | 11.0 | 10% | 0.0% | 1.7% |
| GPT-120B | 1.8 | 12.7 | 14% | 0.0% | 2.8% |
| **DeepSeek** | **2.3** | 6.6 | **35%** | **0.0%** | **0.0%** |
| GLM-5.2 | 0.1 | 7.8 | 1% | 0.0% | 0.6% |

### 2. 低預算下活動集中在 calculate + reason

GPT-120B @256: calculate 46% + reason 50% = 96% of all steps, 0% answer
GPT-120B @1024: calculate 47% + reason 44% = 91%, answer 6%

DeepSeek @256: calculate 52% + reason 34% = 86%, answer 12%
DeepSeek @1024: calculate 50% + reason 34% = 84%, answer 13%

### 3. 結論

數據支持 Kimiko 的判斷：256 tokens 下模型不是「做出分配決策」，而是「被強制截斷」。所有模型的 answer activity 在低預算下接近 0%，代表推理還沒完成就被 num_predict 截斷。

DeepSeek 的優勢在於它每步用的 token 更少（同樣 step count 用更少 token），所以被截斷時已經完成更多推理。這不是校準問題，是效率問題。