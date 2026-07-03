# 講稿：Calibration-Aware Token Efficiency

> **用途：** 2026-07-04（週五）與指導教授開會  
> **投影片：** `slides.html`（21 頁）  
> **建議節奏：** 每頁約 1-2 分分鐘，總計約 25-30 分鐘

---

## Slide 1 — Title

老師好，今天要跟您討論的是延續學姐論文的後續研究方向。論文標題是 Calibration-Aware Token Efficiency——探討更好的 LLM 自我評估能否帶來更有效率的推理。學姐證明了 IRT 難度信號能改善 LLM 的信心校準，也提到 reliability 跟 inference cost 有關聯，但沒有深入。我的研究想填補這個缺口：驗證校準好的模型是否有更好的 token 分配品質——不一定總 token 更少，但分配更合理。接下來我會從學姐的框架開始，帶到文獻調查結果、研究問題、實驗設計，最後有幾個問題想跟老師討論。

---

## Slide 2 — Outline

今天的討論分十個部分。先回顧學姐的論文和缺口，再講老師建議的 token 方向，然後是我做的深度文獻調查、四個核心缺口、研究問題、貢獻設計、實驗規劃，最後是風險評估和給老師的問題。

---

## Slide 3 — 學姐論文回顧

學姐的論文分三個階段。第一階段用 Rasch Model 把模型能力和題目難度放在同一把尺上，可以客觀算出答錯機率。第二階段設計了四種自我評估情境，從完全不給訊號的 QOQ，到給難度訊號的 IDS，到給能力位置的 DPR，到全給的 Combined。第三階段用 LCAE 指標比較模型自估和 IRT 客觀估的一致性，搭配成本效益做模型選擇。

三個關鍵發現：能力強不等於自評準，GPT-5 能力最強但 LCAE 不是最好，Llama 3 70B 自評最準；IDS 最有效，給難度訊號是改善校準最有效的元素；校準不傷能力。但 cost 只有粗估，token 議題完全沒驗證。

---

## Slide 4 — 學姐論文的四個缺口

老師之前指出了學姐論文的四個缺口。前三個是用更精細的 IRT 模型像 2PL/3PL、解決 IDS 難度訊號來自同組模型的循環依賴、跟把成本估計做得更精確。但第四個最重要，也是老師給我的方向：token 使用量跟答題品質和自評準確度的關係完全沒驗證。

老師建議我延續這個方向，設計簡單跟複雜任務的場景，看 token 使用量和品質的關係，目標是用更少 token 達到同等品質。

---

## Slide 5 — 研究核心直覺

學姐證明了給難度信號能改善校準，但留下了三個沒回答的問題。第一，改善校準之後模型的 token 分配品質是否更好？第二，如果模型知道自己會不會，它是否能把 token 分配得更合理？第三，自我評估準確度和 token 分配品質有沒有關係？這三個問題就是我的研究主軸。

注意一個重要的區別：校準好的模型不一定總 token 量更少，但分配可能更合理——簡單題少 token、難題多 token。底部的深藍色條是整個研究的邏輯：從學姐觀察到的關聯，到本研究要驗證的因果，再到最終的 token 分配品質提升。

---

## Slide 6 — 文獻調查規模

我做了 16 組系統性的 arXiv 搜尋，覆蓋自我評估、校準、token 效率、IRT 等關鍵字。最關鍵的發現是左邊列的六組精準交集查詢全部返回零結果。比如 difficulty 乘 token allocation 乘 LLM、IRT 乘 LLM evaluation 乘 cost、self-assessment 乘 reasoning cost，這些都是零。

右邊是現有文獻分成五個集群。集群 A 有大約十篇做難度感知的 token 分配但全用外部信號，集群 B 有八篇做信心校準但不碰 token，集群 C 有九篇做 test-time compute 但用 entropy 或 RL，集群 D 只有學姐一篇用 IRT，集群 E 分析冗餘但不是從自我評估角度。底部的重點是：這五個集群彼此不交集，沒有人把自我評估加 IRT 加 token 分配品質連起來。

---

## Slide 7 — 文獻空白地圖

這張圖是文獻空白地圖。縱軸是 token 效率，橫軸從左邊的外部信號到右邊的自我評估。左邊是集群 A 的論文，全用外部信號做 token 分配。右邊是集群 B 的論文，做信心校準但不碰 token。中間偏上是 test-time compute 集群。

四個紅色和黃色的框就是四個 gap。Gap 1 和 Gap 4 是三星級的主要空白：自我評估準確度能不能預測 token 分配品質、校準改善能不能導致更好的 token allocation，都沒人做。Gap 2 和 3 是二星級：IRT 乘 token 和 verbalized confidence 做信號，也沒人測過。重點是這五個集群彼此不交集，我們的貢獻就是把它們連起來。

---

## Slide 8 — 四個核心缺口

四個核心缺口。Gap 1 是最主要的：沒有人研究模型自我評估有多準跟它 token 分配品質好不好之間的關係。如果這成立，我們就有了一個 training-free 的 token 分配信號，因為模型是自己知道的，不需要額外訓練 predictor。注意這裡講的是 allocation quality，不只是總 token 量。

Gap 2 是 IRT 的客觀難度可以用來做 token 分配，也沒人做。IRT 提供的是相對於模型能力的題目難度，比 ad-hoc 的 difficulty estimator 更有理論基礎。Gap 3 是 verbalized confidence 能不能做 token 分配信號，Kumaran 發現它追蹤 commitment 不是 correctness，這是風險也是研究問題。Gap 4 是核心機會：校準改善到 token 分配品質提升的因果鏈沒人驗證過。學姐證明了 IDS 改善校準，有人證明了 difficulty-aware allocation 減少 token，但沒有人把這兩件事連起來。更好的校準可能不減少總 token，但能讓分配更合理。

---

## Slide 9 — 研究問題與假設

研究問題收斂成三個。RQ1 是 LCAE 能不能預測 token inefficiency，也就是 excess token usage——控制 ability、difficulty、correctness 之後，校準好的模型是否浪費更少 token。RQ2 是 IDS 能不能改善 token allocation quality，不只是看減少 token，而是看分配合理性。RQ3 是校準改善到 allocation quality 的因果鏈成不成立，同時把 verbalized 和 log-prob 的比較併進來——原來的 RQ4 併入 RQ3。

三個假設。H1 是 LCAE 能預測 excess token usage，信心中高。H2 是 IDS 能改善 allocation quality，信心中高。H3 是因果鏈成立，中等信心——校準好的模型可能不降總 token 但分配更合理。特別強調：如果因果鏈不成立，這本身也是一個重要發現。

---

## Slide 10 — 論文 Story

這是整個論文的故事。四個方塊從左到右是一條因果鏈。前兩步學姐已經證明了：IRT 難度信號能改善自我評估。後兩步是本研究要驗證的：更準的自我評估能不能預測 token 需求、能不能做到更好的 token 分配品質。

底下是一句話版本的故事：校準好的模型可能總 token 不降，但分配更合理——簡單題少 token、難題多 token。如果成立，這提供了一個 training-free 的 token 優化方法，不需要額外訓練，只需要讓模型更了解自己。這是跟 ROI-Reasoning、SelfBudgeter 等競爭者最大的差別——他們需要訓練 predictor 或微調模型，我們用模型本身的自我評估。

---

## Slide 11 — 四個貢獻

四個貢獻涵蓋發現、方法、驗證、框架四個層面。C1 是新發現：揭示 LCAE 和 excess token usage 的關係。C2 是新方法：用 IRT 難度信號預測 token 需求。C3 是新驗證：驗證校準好到 allocation quality 好的因果鏈。C4 是新框架：提出基於自我評估的 token 分配策略，但 C4 標為延後/bonus。

重點是：Phase 1+2 的 C1+C2+C3 三個貢獻已經足以寫一篇完整論文。C4 是 bonus，有時間再做。

---

## Slide 12 — 競爭者比較

七個最接近的競爭者。ROI-Reasoning 做了 meta-cognitive 預測加 budget 分配，但不用 IRT 也不用自我評估，是自訓 predictor。SelfBudgeter 讓模型先估 token budget 再生成，但它是 training-based 的，需要微調，不是 diagnostic/training-free 的。TALE 用 length-aware fine-tuning 達到 token-efficient reasoning，也是 training-based，不涉及自我評估。TRIAGE 測 metacognitive budget 但不研究校準和 token 的關係。學姐有 IRT 加校準但沒深入 token。UAB 用 log-prob 不是自我評估。LLM Already Knows 用 hidden states 不是 verbalized confidence。

底部深藍色條的重點是：沒有任何一篇同時做到四件事——IRT 框架、自我評估測量、token 預測、因果驗證。SelfBudgeter 和 TALE 是 training-based 的，跟我們的 diagnostic/training-free 路線不同。

---

## Slide 13 — 實驗設計總覽

實驗分三個階段。Phase 1 用學姐的模型資料，在同一 benchmark 上測量每個模型的 token 使用量，分析 LCAE 和 token 分配品質的相關性。Phase 2 做因果鏈驗證：學姐已經證明 IDS 能改善 LCAE，我在有無 IDS 的情況下測量 token 變化，如果 IDS 同時改善了 allocation quality 而且改善幅度跟 LCAE 改善幅度正相關，就支持因果鏈。Phase 3 設計分配策略，但這是延後/bonus 的部分。

底下列的是從學姐那裡可以直接重用的資源：模型 IRT 估計、題目難度參數、LCAE 計算方法、四種自我評估情境、prompt templates、benchmark 資料。

---

## Slide 14 — Phase 1 詳細

Phase 1 的詳細設計。左邊是測量變量：LCAE、能力、難度都從學姐資料來，token 使用量是新增的。下面是新設計的精細指標——從粗略到精細：Token efficiency 是 accuracy 除以 token usage，這是粗略的基礎指標。Excess Token Usage 是實際 token 減去同 difficulty/ability 下的預期 token，控制了難度和能力後的浪費量。Overthinking Rate 是簡單且答對但 token 遠高於中位數的比例。Underthinking Rate 是困難且答錯但 token 很少的比例。Allocation-Difficulty Correlation 是 token usage 跟 effective difficulty 的相關，正值代表分配合理。

右邊是四個步驟：跑模型測 token、算 LCAE 和 excess token usage 的相關性（控制 ability/difficulty/correctness）、按難度分層分析 overthinking 和 underthinking、看校準好的模型是否有較高的 Allocation-Difficulty Correlation。

預期結果有兩種：H1 成立就是 LCAE 能預測 excess token usage，校準好的模型 excess token 較少、分配更合理；如果不成立，自我評估和 token 分配品質無關本身也是重要發現。注意：校準好的模型可能總 token 不降，但 Allocation-Difficulty Correlation 更高。

---

## Slide 15 — Phase 2 詳細

Phase 2 是因果鏈驗證。利用學姐已經證明的結果：IDS 能改善 LCAE，四種情境的 LCAE 好壞順序是已知的——QOQ 最差、IDS 比較好、DPR 中等、Combined 最好。如果 IDS 組同時也改善了 token allocation quality，而且改善幅度跟 LCAE 改善幅度正相關，就支持因果鏈。

進一步分析包括按難度分層看 IDS 在哪個範圍影響最大、IDS 組是否表現出適應性分配、是否減少了簡單題的 overthinking、是否避免了困難題的 underthinking。

新的設計是 Budget Curve 分析：不只一個 budget，設五個 budget level——64、128、256、512、1024 tokens，畫每組的 Accuracy-Token Pareto curve。看校準好的組的曲線是否更接近 Oracle，哪個 budget level 下校準的效益最大。

---

## Slide 16 — Phase 3 詳細（延後 / Bonus）

Phase 3 是分配策略，但這是延後/bonus 的部分。Phase 1+2 已經有 C1+C2+C3 三個貢獻，足以寫一篇完整論文。Phase 3 的 C4 是 bonus，視時間和結果決定是否執行。

Pipeline 是：模型收到題目、做自我評估、根據信心分配 token 預算、在預算內生成回答。對照組有五個：Uniform 做基線，Oracle 做上限，verbalized 和 log-prob 兩種自我評估測 RQ3，IDS-based 結合學姐框架。

評估指標包括 Excess Token Usage、Token efficiency、Budget utilization、Allocation quality、Allocation-Difficulty Correlation 和 Regret。

---

## Slide 17 — 與學姐論文的銜接

左邊是從學姐那裡直接重用的：模型 IRT 估計、題目難度參數、LCAE 計算方法、四種自我評估情境、prompt templates、benchmark 資料。這些都不需要重新做。右邊是本研究新增的：token 精確測量、精細指標定義（excess token usage、overthinking rate 等）、因果實驗、分配策略、verbalized vs log-prob 比較、overthinking 分析。

底部的敘事銜接：學姐的故事是 IRT 到 LCAE 到 IDS 改善校準到提到 cost 關聯，我的故事是 LCAE 到 token 分配品質到驗證因果鏈。把學姐提到的 cost 關聯變成深入驗證的因果鏈。

---

## Slide 18 — 風險評估

五個風險。兩個高風險：第一是 verbalized confidence 可能不適合做 token 分配信號，Kumaran 發現它追蹤 commitment 不是 correctness。緩解是同時測 verbalized 和 log-prob，把它當研究問題而非假設，而且 IDS 不依賴 verbalized confidence。第二是因果鏈可能不成立，校準好不代表 token 省。緩解是不成立本身也是發現，而且要區分 allocation quality 和總量——使用 Excess Token Usage 和 Allocation-Difficulty Correlation 等精細指標。

兩個中風險：範圍太窄可以擴大到後設認知乘計算分配；學姐資料可能沒有 token 記錄需要重跑。一個低風險是 ROI-Reasoning 太接近但差異足夠大。

---

## Slide 19 — 時程規劃

六週時程。第一週確認學姐資料格式和模型清單。第二週跑 Phase 1 收集 token 資料。第三週 Phase 1 分析加 Phase 2 實驗。第四週 Phase 2 分析加 Phase 3。第五週分析和寫初稿。第六週修改定稿。

降級方案有四級。Level 0 是全部做完四個貢獻。Level 1 是 Phase 1+2，Phase 3 延後——這是主打方案，已有 C1+C2+C3。Level 2 只做 Phase 1+2 不做 Phase 3。Level 3 只做 Phase 1。即使 Level 3 也還是有貢獻的——首次揭示 LCAE 和 token 分配品質的關係，可以寫 short paper 或 workshop paper。

模型選擇策略：建議先跑 5-8 個代表性模型——高能力高校準、高能力低校準、中能力高校準、中能力低校準、加 1-2 個小模型。有趨勢再擴到 20 個。

---

## Slide 20 — 給老師的問題

八個問題想跟老師討論。最重要的幾個：

Q1 方向是否可行——這個自我評估到 token 分配品質到分配優化的 story 行不行。

Q2 學姐資料有沒有 token 記錄——如果沒有我需要重跑，老師能不能幫忙取得學姐的實驗資料和 benchmark 細節。

Q3 投 IEEE Big Data 還是做更深再投其他場所。

Q4 時間不夠砍哪個 Phase——Phase 1 是基礎、Phase 2 是核心論點、Phase 3 是 bonus。

Q5 benchmark 選擇。Q6 verbalized confidence 的風險還是機會。Q7 要不要跟 nhri 記憶衝突研究結合。Q8 先跑 5-8 個代表性模型再擴到 20 個的策略好不好。

---

## Slide 21 — Summary

總結六個重點。學姐證明了 IRT 改善校準、提到了 cost 關聯但沒深入。16 組搜尋確認沒有人把校準和 token 分配品質連起來。本研究驗證因果鏈、提出分配策略、三個核心貢獻加一個 bonus。重點是校準好可能不降總 token，但 allocation quality 更好——簡單題少 token、難題多 token。最大賣點是 training-free：不需要額外訓練，只需要讓模型更了解自己。謝謝老師，歡迎討論。

---

> **講稿文件位置：** `speaker-notes.md`  
> **投影片位置：** `slides.html`  
> **完整提案文件：** `docs/advisor-meeting-2026-07-04.md`