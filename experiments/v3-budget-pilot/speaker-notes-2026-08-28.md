# 講稿 — 最終版

> 對應 HTML：https://ruienxie0104.github.io/llm-calibration-token-efficiency/presentation.html
> 時間：25-30 分鐘

---

## 1 — 封面

老師好，今天報告從學姐 LCAE 框架延伸的研究——校準品質跟 Token 分配效率的關係。做了三階段實驗，今天有最新結果。

---

## 2 — 大綱

六部分：研究起源 → V1 → V2 → 文獻調查收斂方向 → V3 結果（核心）→ 下一步。

---

## 3 — 學姐 LCAE

學姐用 IRT Rasch Model 把模型能力和題目難度放在同一把尺，客觀算出每題的答錯機率。然後設計四種情境測自評校準——不給訊號的 QOQ、給難度訊號的 IDS 等等。

三個關鍵發現：能力強不等於自評準，GPT-5 最強但自評不是最好；IDS 最有效改善校準；改善校準不影響答題能力。她提到 reliability 跟 inference cost 有關聯，但沒深入驗證——這就是我的切入點。

---

## 4 — 我的問題

學姐：模型知道自己會不會？我進一步問：知道自己會不會，能不能知道自己需要想多久？

假設：校準好的模型不是總 token 更少，是分配更合理——簡單題少 token、困難題多 token。有限資源下準確率損失更小。

為了分析推理軌跡，引入 Process Mining。把 CoT 切成活動序列，用 pm4py 分析。比如「先理解→提取條件→計算→驗證→作答」這樣。可以看到推理結構——先理解還是直接算？有沒有驗證？這些只看 token 總數看不出來。

---

## 5 — V1

GSM8K 20 題小學數學，5 模型，無信心數據。

✅ PM 能區分推理風格——直覺型（DeepSeek）、系統型（120B）、掙扎型（20B）。三種風格跨 V1 V2 穩定出現。
❌ 題目太簡單（95-100%），零變異量。無信心數據，無法驗證校準。

V1 教訓：需要更難的題目、信心收集、更細的活動分類。

---

## 6 — V2

MMLU+ARC 100 題，4 模型（GLM-4.7 退休），加入信心收集和校準指標。

信心 prompt 有個教訓：最初無上下文問「你有多確定」→ DeepSeek 回傳 2%，完全失真。改成多輪對話式，根據完整推理過程問 → 99%。這本身就是一個 methodology finding。

---

## 7 — V2 Rebuild

執行中發現多個 bug。Conformance 讀錯欄位，alignment 全 0。Levenshtein 非對稱。JSD 標錯。Confidence 截斷文字。

修正後數據完全不同——GPT-20B 從 56% 跳到 98%，信心差距全部縮小到趨近於零。前一版「信心差距與準確率反相關」的核心發現被推翻。

V2 校準分析價值下降，但 PM pipeline 驗證成功。重要的是暴露了 prompt sensitivity、confidence scarcity 等問題，後續不會重複犯錯。

---

## 8 — 競爭者

7 月底做系統性調查，確認了這個領域的競爭狀況。

Think Just Enough（EACL 2026）：證明自評信心可做 stopping signal——但它們的信心沒經過校準。SelfBudgeter（ACL 2026）：模型預估 budget——但要訓練，不是 training-free。Capability Calibration（arXiv 2026）：校準→best-of-k 配置——但配置的是 sampling 次數，不是 reasoning length。Berti et al. 2025 已經用 PM 分析過 LLM reasoning trace。

結論：「校準→單一推理軌跡的 token 長度配置」這條因果鏈仍是空白，但不能再說「首次用 confidence 省 token」這種太寬的話。

---

## 9 — 定位收斂

核心問題：confidence 的校準品質本身，是否決定配置效果？

完整因果鏈：IRT 能力/難度 → LCAE 校準 → Token 預測 → 動態分配 → Frontier 改善 → PM 診斷。

跟競爭者的差異：IRT 校準不是 raw confidence、training-free、black-box、配置 reasoning length 不是 sampling 次數、有 IDS 因果驗證、有 PM 行為分析。

---

## 10 — 分階段設計

每個階段有 Go/No-Go，避免白做工。

Phase 1（✅ budget 可控）→ Phase 2（✅ 今天的重點）→ Phase 3（下一步：擴大）→ Phase 4-6（未來：分配評估 + PM 分析）

---

## 11 — Phase 2 設計

30 題 MATH-500（Level 3-5 各 10），2 模型（GPT-20B vs DeepSeek），4 個 budget（128/256/512/1024），每條件 2 次 replicate。480 次呼叫，約 11 分鐘。

Budget 根據 V2 自然用量設定——自然約 600-900，128 是極度壓縮 15%、256 是顯著壓縮 30%、512 是中等 60%、1024 接近無限制。保證看到從不足到充足的變化。

---

## 12 — 主要結果

128：兩者都 0%（題目夠難）。
**256：DeepSeek 15% vs GPT 3.3%——差了 5 倍。**
512：33% vs 20%。
1024：37% vs 32%（趨近）。

校準優勢在低 token 時最明顯——這是核心發現。token 無限時大家都差不多，但資源受限時校準好的模型更會把 token 用在對的地方。

---

## 13 — Level 分析

Level 4 最有趣。256 時 DeepSeek 35% vs GPT 10%（差很多）。但 1024 時 GPT 45% 反超 40%。GPT 需要更多 token 才能發揮實力，DeepSeek 低資源就用得很有效率。

Level 5 太難，連 1024 都只能做到 15-30%，但 DeepSeek 還是贏一倍。

---

## 14 — 逐題對決

30 題中 8 題 DeepSeek 比 GPT 省 token 就答對，只有 1 題反過來。最誇張的是 L4 Algebra——DeepSeek 256 答對，GPT 要到 1024。還有一題 L5 Algebra，DeepSeek 512 答對，GPT 連 1024 都做不到。

這些差異不能用模型大小完全解釋——簡單題如 L3 Algebra，DeepSeek 256 就夠，GPT 要 512。

---

## 15 — 結果可靠度

每條件 2 次 replicate。128 全部一致（0 分歧），256 僅 1 個分歧。低 budget 結果極穩定，而我們最關心的就是低 budget。

---

## 16 — 結論

✅ Budget sensitivity 存在、DeepSeek 全贏、校準優勢在低 token 最明顯
⚠️ 只有 2 模型（無法區分校準 vs 能力的 confound）、無信心收集

方向對了，還需要決定性實驗。

---

## 17 — Phase 3

加 GPT-120B 和 GLM-5.2（共 4 模型），60 題 L3+L4（剔除太難的），3 個 budget（256/512/1024，剔除 128），加入信心收集，3 次 replicate。預計 2160 次呼叫。

關鍵預測：GLM-5.2（校準最好）贏 DeepSeek、120B（中等）接近 20B → 校準是獨立變數。反過來 → 方向調整。

---

## 18 — 時間

近 1 週 Phase 3 → 近 2 週分析圖表 → 近 4 週 PM + 人工標註 → 10 月中論文初稿，目標 IEEE Big Data。

---

## 19 — 謝謝

謝謝老師，歡迎討論。
