# 講稿 — LLM 校準 × Token Allocation × Process Mining

> 對應 HTML 簡報：https://ruienxie0104.github.io/llm-calibration-token-efficiency/presentation.html
> 對象：指導教授
> 預計時間：25-30 分鐘

---

## Slide 1 — 封面

老師好，今天要報告的是我從七月初到現在做的研究進展。主題是 LLM 校準品質跟 Token 分配效率的關係，中間引入了 Process Mining 來分析推理軌跡。從學姐的 LCAE 框架出發，經過三階段的實驗，今天會看到最新的結果。

---

## Slide 2 — 大綱

報告分六個部分。先講研究起源——學姐的 LCAE 框架跟我的研究問題。然後是 V1 和 V2 的初步實驗，學到了什麼、遇到了什麼問題。接著是我在七月底做的文獻調查，確認競爭者狀況和方向定位。最後是核心——V3 剛跑完的 Budget Sensitivity Pilot 結果，以及下一步規劃。

---

## Slide 3 — 學姐論文：LCAE 框架

學姐的論文是 Chen et al. IEEE IRI 2026，主題是 LLM 的自我評估校準。她用 IRT 的 Rasch Model，把模型能力和題目難度放在同一把尺上——公式就是 P(答對) = σ(模型能力 − 題目難度)。

階段一用它客觀算出每題的答錯機率。階段二設計四種自我評估情境，從完全不給訊號的 QOQ，到給難度訊號的 IDS。發現 IDS 最能改善校準，而且改善校準不會讓答題能力下降。階段三用 LCAE 指標比較模型自估跟 IRT 客觀估計的一致性。

三個關鍵發現：能力強不等於自評準——GPT-5 最強但自評不是最好，Llama 3 70B 反而最準。IDS 最有效。最重要的是她提到 reliability 跟 inference cost 有關聯，但沒有深入驗證。這就是我的切入點。

---

## Slide 4 — 從學姐到我的研究

學姐回答了「模型知不知道自己的實力」。我的問題更進一步——如果知道自己會不會，能不能知道自己需要思考多久？校準品質跟 Token 分配效率有沒有關係？

核心假設是：校準好的模型不一定總 token 更少，但分配更合理——簡單題少 token、困難題多 token。在有限資源下，準確率損失更小。

為了分析推理軌跡，我引入了 Process Mining。做法是把模型的 Chain-of-Thought 切成一段一段，每個段落標一個活動類型——understand、recall、calculate、verify、answer 等等。然後用 pm4py 做流程分析。這樣可以看到推理的結構：是先理解還是直接算？有沒有驗證？有沒有回頭修正？這些是只看 token 總數看不出來的。

---

## Slide 5 — V1：Process Mining 可行性驗證

V1 用的是 GSM8K，20 題小學數學，五個模型，沒有收集信心數據。

正向的發現是 Process Mining 確實能區分推理風格，而且三種風格跨 V1 V2 都穩定：DeepSeek 是直覺型，短軌跡、高 answer、不太思考。GPT-OSS-120B 是系統型，calculate 和 reason 均衡。GPT-OSS-20B 是掙扎型，長軌跡、高 reason 佔比、一直在推理但常答錯。

但限制也很明顯——題目太簡單，95-100% 準確率，沒有變異量能做任何相關分析。沒有信心數據，無法驗證校準假設。

---

## Slide 6 — V2：加入校準指標與 PM 分析

V2 做了大幅改進。題目換成 MMLU STEM 加 ARC Challenge，100 題。模型從五個變四個，因為 GLM-4.7 退休了。活動類型從八種擴大到九種，新增 evaluate。最重要的是加入了多輪對話式的信心自評，以及 Brier score 和信心差距這些校準指標。PM 分析也從只有 Petri net 擴大到熵分析加 JSD。

信心的 prompt 本身就是一個教訓。最初用無上下文的方式問「你回答了 D，有多確定？」結果 DeepSeek 回傳 2%，完全失真。改成多輪對話——給題目、模型完整推理、然後才根據推理過程問信心——數據才變成 99%。所以無上下文的信心 prompt 會產生完全失真的數據，這本身就是一個發現。

---

## Slide 7 — V2 Rebuild：Bug 修正與數據翻轉

V2 執行過程中發現了幾個重大 bug，所以做了完整的環境重建和數據重跑。

Conformance 讀取不存在的欄位，導致 alignment 偏離全部是 0。Levenshtein 距離 (A,B) 和 (B,A) 分別抽樣，結果是非對稱矩陣。JSD 存的其實是 distance 不是 divergence。Confidence 只傳 response 沒傳 thinking，還截斷成 500 字。

修正之後，數據完全不同——GPT-OSS-20B 從 56% 跳到 98%，信心差距從 +33~+81 變成 −0.8~+4.5。之前「信心差距與準確率反相關」的核心發現直接被推翻了。

這件事情的影響是：V2 作為校準分析的價值大幅下降，因為準確率變異消失了。但作為 PM pipeline 的驗證仍然很成功——暴露了 prompt sensitivity、confidence scarcity、Petri net flower model 等問題。這些經驗讓後續實驗不會重複犯錯。

---

## Slide 8 — 競爭者全景圖

七月底我花了一週做系統性的文獻調查，確認了競爭者的狀況。結論是這個領域很熱，但很多基本想法已經被別人做了。

Think Just Enough 已經證明了自評信心可以做推理的 stopping signal——但它們的信心沒有經過 IRT 校準。SelfBudgeter 讓模型預估 token budget 再優化——但它需要訓練、不是 training-free。Capability Calibration 連結了校準品質和 best-of-k 的配置效率——但它配置的是 sampling 次數，不是 reasoning length。Sonata 用 hidden state 預測 self-consistency——但它需要內部存取，不支援 black-box。

所以「Calibration → Single-Trajectory Reasoning-Length Allocation」的完整因果鏈仍然是空白，但我不能再說「首次用 confidence 省 token」這種太寬的話。

---

## Slide 9 — 論文定位收斂

新的定位是：現有研究已經證明 confidence 可以控制推理長度，但通常假設 confidence 本身夠可靠。我改問——真正決定配置效果的，是不是 confidence 的校準品質本身？

完整因果鏈是：IRT 難度跟能力 → LCAE 校準 → Token requirement 預測 → 動態分配 → Accuracy-token frontier 改善 → PM 機制診斷。

差異化很清楚：我用 IRT 校準不是 raw confidence，我是 training-free、black-box compatible、配置的是 reasoning length 不是 sampling 次數、有 IDS intervention 做因果驗證、還有 PM 做 activity-level 的行為分析。

---

## Slide 10 — V3 分階段實驗設計

V3 是分階段設計的，每個階段都有明確的 Go/No-Go 標準。Phase 1 確認了 Ollama API 的 num_predict 可以真正限制 reasoning tokens，不是事後截斷。Phase 2 就是今天要講的重點——confirm 題目難度適當、存在可測量的 budget sensitivity。兩個都通過了。Phase 3 是下一步，擴大模型跟題目數量，加入 confidence 收集。Phase 4 到 6 是後續的 Allocation 評估和 PM 分析。

---

## Slide 11 — 實驗設計

Phase 2 的設計：30 題 MATH-500，只取 Level 3 到 5，因為 Level 1 跟 2 太簡單。兩個模型——GPT-OSS-20B 跟 DeepSeek，校準差跟校準好的兩極端。四個 budget：128、256、512、1024 tokens。每個條件跑 2 次 replicate。用 temperature 0.0 控制隨機性。

Budget 的選擇是根據 V2 的自然 token 用量：這兩個模型平均用 600 到 900 tokens。所以 128 是大約 15% 的極度壓縮、256 是 30% 的顯著壓縮、512 是 60% 的中等壓縮、1024 是接近無限制的對照組。這樣可以保證看到從不足到充足的連續變化。

---

## Slide 12 — 主要結果

480 次 API 呼叫，約 11 分鐘完成。

結果非常清楚。128 的時候兩個模型都是 0%，代表題目夠難。最關鍵的是 256——DeepSeek 15%，GPT-OSS-20B 只有 3.3%，差了整整 5 倍。到 512 差距縮小到 1.7 倍，1024 只剩 1.2 倍。

這呼應了我們的核心假設——校準品質在資源受限時差異最大。當 token 無限時大家都差不多，但在低 budget 下，校準好的模型更會把有限的 token 用在對的地方。

---

## Slide 13 — 依難度 Level 分析

分難度看更有趣。Level 3 兩者差不多，DeepSeek 小贏。Level 4 是亮點——DeepSeek 在 256 時 35%，GPT 只有 10%，差非常多。但奇妙的是，GPT 在 1024 時反而 45% 反超 DeepSeek 的 40%。這代表 GPT 需要更多 token 才能發揮實力，DeepSeek 在低資源時就用得很有效率。Level 5 太難，1024 也只能做到 15-30%，但 DeepSeek 還是贏一倍。

---

## Slide 14 — 逐題對決：誰更省 token？

30 題當中，8 題 DeepSeek 比 GPT 省 token 就答對，只有 1 題反過來。最誇張的那題是 Level 4 Algebra——DeepSeek 256 就答對，GPT 要到 1024 才答對，差了 4 倍。還有一題 Level 5 Algebra，DeepSeek 512 就答對，GPT 連 1024 都做不到。

這些差異不能用模型大小完全解釋——有些簡單題像是 Level 3 Algebra，DeepSeek 256 就夠了，但 GPT 需要 512。如果只是模型大小的問題，簡單題應該兩者差不多才對。

---

## Slide 15 — 結果可靠度

每個條件跑 2 次 replicate 檢查一致性。128 的時候 0 個分歧——全部一致，因為根本沒人答對。256 也只有 1 個分歧。結果很可靠，特別是在我們最關心的低 budget 區間。

---

## Slide 16 — V3 Pilot 結論

總結三件事確認了：budget sensitivity 存在、DeepSeek 在所有 budget 贏、校準優勢在低 token 時最明顯。

但兩個限制也很清楚：只有兩個模型，而且它們不只校準不同，大小也不同——分不清差異是因為校準好還是因為模型強。另外沒有信心收集，還不能驗證校準跟 token requirement 的因果關係。

方向對了，但還需要一個決定性實驗才能確認校準的獨立價值。

---

## Slide 17 — Phase 3：區分校準 vs 模型能力的 Confound

所以下一步是加入 GPT-OSS-120B 和 GLM-5.2，這樣總共四個模型。60 題 MATH-500 只取 Level 3 跟 4，剔除太難的 Level 5。三個 budget，剔除 128 因為 0% 沒有資訊量。加入多輪對話式的信心收集。三次 replicate。

關鍵的預測是：如果 GLM-5.2（校準最好）在低 budget 勝過 DeepSeek，而且 GPT-120B（中等校準）接近 GPT-20B——那校準就是獨立的解釋變數。如果只是模型大小在排序——那方向就要調整了。

---

## Slide 18 — 時間規劃

近一週執行 Phase 3，近兩週做數據分析和圖表，近四週做 activity labeling 驗證和 PM 分析。十月中後開始寫論文初稿，目標是 IEEE Big Data 2026。

---

## Slide 19 — 謝謝

謝謝老師，歡迎討論。
