# 講稿 — 簡化版

> 對應 HTML：https://ruienxie0104.github.io/llm-calibration-token-efficiency/presentation.html

---

## 1 — 封面

老師好，報告從學姐 LCAE 延伸的研究：校準品質跟 Token 分配效率的關係。經過三階段實驗，今天有最新的結果。

---

## 2 — 大綱

分六部分：研究起源 → V1 → V2 → 文獻調查 → V3 結果 → 下一步。

---

## 3 — 學姐 LCAE

學姐用 IRT Rasch Model 把模型能力和題目難度放同一把尺，客觀算出答錯機率。四種情境測自評校準。三個發現：能力強≠自評準、IDS 給難度訊號最有效、提到 cost 關聯但沒驗證。這就是我的切入點。

---

## 4 — 我的問題

學姐：模型知道自己會不會？我：知道自己會不會，能否知道自己需要想多久？

假設：校準好的模型不是總 token 更少，是分配更合理。簡單題少 token、困難題多 token。

引入 Process Mining：把 CoT 切成活動序列（understand→recall→calculate→verify→answer），用 pm4py 分析推理結構。

---

## 5 — V1

GSM8K 20 題，5 模型，無信心數據。

✅ PM 能區分推理風格——直覺型（DeepSeek）、系統型（120B）、掙扎型（20B）
❌ 題目太簡單（95-100%）、無信心數據

---

## 6 — V2

MMLU+ARC 100 題，4 模型，加入信心收集和校準指標。

信心 prompt 教訓：無上下文問「多確定」→ DeepSeek 回 2%。改成多輪對話 → 99%。

---

## 7 — V2 Rebuild

發現多個 bug——conformance 全 0、Levenshtein 不對稱、JSD 標錯。

Rebuild 後數據翻轉：GPT-20B 從 56% 跳到 98%，信心差距全消失。前一版核心發現被推翻。

教訓：V2 校準分析價值下降，但 PM pipeline 驗證成功，也暴露了問題。

---

## 8 — 競爭者

Think Just Enough（信心可做 stopping signal）、SelfBudgeter（預估 budget）、Capability Calibration（校準→best-of-k）。很多基本想法已有人做。

「Calibration → Reasoning-Length Allocation」因果鏈仍是空白，但題目要收斂。

---

## 9 — 定位

核心問題：confidence 的校準品質本身，是否決定配置效果？
差異：IRT 校準、training-free、black-box、配置 reasoning length 不是 sampling 次數、有 IDS intervention。

---

## 10 — 分階段設計

Phase 1（budget 可控 ✅）→ Phase 2（sensitivity ✅ 今天重點）→ Phase 3（擴大實驗）→ Phase 4-6（分配評估）。

---

## 11 — Phase 2 設計

30 題 MATH-500（L3-5）、GPT-20B vs DeepSeek、4 個 budget（128/256/512/1024）、2 reps、480 calls。

---

## 12 — 主要結果

128：兩者都 0%。**256：DeepSeek 15% vs GPT 3.3%，差 5 倍。** 512：33% vs 20%。1024：37% vs 32%。

校準優勢在低 token 時最明顯——這是核心發現。

---

## 13 — Level 分析

L4 最有趣。256 時 DeepSeek 35% vs GPT 10%。但 1024 時 GPT 45% 反超 40%。GPT 要更多 token 才發揮，DeepSeek 低資源就用得有效率。

---

## 14 — 逐題對決

8 題 DeepSeek 比 GPT 省 token，1 題反過來。最大差距：L4 Algebra，DeepSeek 256 答對，GPT 要到 1024。

---

## 15 — 結論

✅ Budget sensitivity 存在、DeepSeek 全贏、校準優勢在低 token 最明顯
⚠️ 只有 2 模型（confound 未解）、無信心收集

方向對了，還需要決定性實驗。

---

## 16 — Phase 3

加 GPT-120B 和 GLM-5.2（4 模型），60 題 L3+L4，3 budgets，加信心收集。預計 2160 次呼叫。

關鍵：GLM-5.2 贏 DeepSeek、120B 接近 20B → 校準獨立。反過來 → 調整方向。

---

## 17 — 時間

近 1 週 Phase 3 → 近 2 週分析 → 近 4 週 PM + 標註 → 10 月中論文初稿，目標 IEEE Big Data。

---

## 18 — 謝謝
