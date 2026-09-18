# Proposal 簡報內容規格書

## 以可觀察推理進度進行大型語言模型的動態測試時計算分配

> 文件用途：本文件是下一版研究 Proposal 簡報的內容依據。它先建立完整研究敘事、概念定義、研究問題、假設、方法與初步證據，再由這份內容轉換成投影片。這不是正式論文，也不是實驗歷程紀錄。
>
> 資料版本：專案 commit `0d0a54e`。現有數字只作為 preliminary evidence；後續簡報需清楚區分已完成證據、研究假設與下一步工作。

---

## 1. 為什麼應該重新安排簡報

目前研究已經形成一個可行方法，但 Proposal 報告的重點不應是一次展示所有實驗結果。老師首先需要理解四件事：

1. 為什麼有限的 test-time compute 會形成資源配置問題。
2. 現有研究如何配置推理資源，以及還缺少哪一種可部署訊號。
3. 我們提出的 visible progress 到底是什麼，為什麼可能預測追加運算的價值。
4. 我們如何用公平的成本比較，驗證這個方法真的改善 accuracy–cost trade-off。

因此，下一版簡報應由「研究問題」帶動「方法」，再用少量 preliminary evidence 說明方法具有可行性。結果的角色是支持 Proposal，而不是取代 Proposal。

### 1.1 建議比例

下一版建議使用約 24 頁，分配如下：

| 區塊 | 建議頁數 | 約占比 | 目的 |
|---|---:|---:|---|
| 封面與研究地圖 | 2 | 8% | 先讓聽眾知道報告將回答什麼 |
| 研究背景與動機 | 4 | 17% | 建立有限推理資源的實務問題 |
| 文獻回顧與缺口 | 5 | 21% | 說明既有方法、限制與本研究定位 |
| 研究問題與假設 | 3 | 13% | 把動機轉成可檢驗命題 |
| 研究方法 | 7 | 29% | 詳細解釋概念、流程、政策與評估 |
| Preliminary evidence | 2 | 8% | 證明方向可行，但不搶走 Proposal 主體 |
| 貢獻、限制與下一步 | 1 | 4% | 說明研究價值與需要老師確認的方向 |

這個比例刻意把背景、文獻、問題與方法合計提高到約 80%。結果只保留能回答研究假設的核心證據。

---

## 2. 一句話研究定位

> 本研究觀察模型在固定低預算推理後的可見進度，判斷哪些題目值得追加運算，並在相同 token 成本下檢驗這種動態配置是否能提高整體正確率。

更口語的版本是：

> 每題都先讓模型做一小段，再看它目前走到哪裡，把有限的額外 token 留給已經有進展但尚未完成的題目。

這兩句話必須成為整份簡報的主線。後續每一個概念都應該回到這個問題，不再同時開啟多條互相競爭的研究故事。

---

## 3. 完整研究敘事

## 3.1 研究背景：推理表現與推理成本同時增加

推理型大型語言模型可以透過更多 test-time compute 改善答案，例如：

- 產生更長的推理內容。
- 對既有答案進行續寫或修正。
- 產生多條推理路徑後進行選擇。
- 使用 verifier、search 或其他額外計算。

但這些方法都會增加 token、延遲或運算成本。當服務具有固定預算時，系統不可能無限制地增加每一題的推理量。

### 需要先定義的概念

**Test-time compute** 代表模型在收到問題之後、產生最終答案之前使用的推理資源。它可以用生成 token、模型呼叫次數、推理時間或 FLOPs 衡量。本研究主要使用 API 所記錄的 token 成本。

**Token budget** 代表系統允許一個推理階段使用的生成上限。預算提高不保證模型一定用完，也不保證正確率一定增加。

**固定配置** 代表每一題都接受相同推理資源，例如全部使用 512 tokens，或全部再追加一次 continuation。

**動態配置** 代表系統根據每題目前可取得的訊號，選擇停止或投入更多資源。

### 背景段落的核心訊息

更多推理資源有時有用，有時沒有用。真正的系統問題不是「是否應該增加整體運算」，而是「在總資源有限時，應該把額外運算分給哪些題目」。

## 3.2 問題動機：題目難度不等於追加運算的價值

資源配置容易被簡化成難度分類：簡單題少算、困難題多算。但「題目困難」與「多給資源會不會改善」並不相同。

可以把題目分成四種直觀情況：

| 題目狀態 | 低預算結果 | 增加運算後 | 資源配置含義 |
|---|---|---|---|
| 已足夠完成 | 已正確 | 通常不變 | 不需要追加 |
| 可被救回 | 尚未完成或錯誤 | 追加後正確 | 最值得追加 |
| 難但無法改善 | 錯誤 | 仍然錯誤 | 追加可能浪費 |
| 追加造成退步 | 正確 | 變成錯誤 | 追加可能有害 |

因此，我們真正想預測的是 **continuation value**，而不是抽象難度。

令第 (i) 題在停止時的正確性為 (y_i^L\in\{0,1\})，追加 continuation 後的正確性為 (y_i^H\in\{0,1\})，則：

\[
g_i=y_i^H-y_i^L.
\]

- (g_i=+1)：追加運算救回這一題。
- (g_i=0)：追加後結果沒有改變。
- (g_i=-1)：追加運算使原本正確的答案變錯。

研究方法的目標，就是在不知道未來 (g_i) 的情況下，利用當下可觀察訊號，把資源優先分配給較可能有 (g_i=+1) 的題目。

## 3.3 實務限制：黑箱 API 看不到模型內部狀態

許多 adaptive compute 方法可以使用 hidden representations、額外 verifier、訓練過的 reward model 或大量重複採樣。但一般 API 使用者可能只能看到：

- 原始問題。
- 模型目前輸出的可見文字。
- 是否已出現可解析的最終答案。
- 已使用的 token 與完成原因。

因此，本研究採用一個較嚴格、也較容易部署的設定：

> Controller 只使用 prefix 當下的 visible content，不依賴 hidden state、reference answer 或未來 continuation 結果。

這個限制形成研究價值。若簡單、免費、可觀察的輸出狀態已能改善資源配置，就不必先建置昂貴的 verifier 或取得模型內部存取權限。

---

## 4. 文獻回顧應如何組織

文獻回顧不應只是逐篇論文摘要，而應回答「目前有哪些配置訊號，為什麼還需要 visible progress」。建議分成四條研究路線。

## 4.1 Test-time scaling 與 compute-optimal allocation

Test-time scaling 文獻指出，增加推理時計算能改善模型表現，但不同題目與不同計算方法的收益不同。Snell et al. 顯示，依題目難度調整 search 或 revision 策略，可以比均勻配置更有效率。

這條文獻建立兩個前提：

1. 額外推理資源具有潛在價值。
2. 資源收益具有題目異質性，因此需要 adaptive allocation。

但題目層級難度通常在推理前估計，未必能反映模型已經進行一段推理後的即時狀態。

## 4.2 Budget-aware reasoning 與可控生成

Token-budget-aware reasoning 研究讓模型在指定預算下產生答案，重點通常是讓模型適應不同長度限制，或在較少 token 下完成推理。

這類方法處理「如何在給定預算內推理」，而本研究處理的是另一個決策：

> 在完成第一段推理後，系統是否應該再給這一題額外預算？

兩者可以互補。Budget-aware model 可以成為執行器，visible-progress controller 則決定哪一題獲得下一段預算。

## 4.3 Difficulty、confidence 與 learned routing

現有 adaptive allocation 常使用下列訊號：

- 題目特徵或預測難度。
- 模型信心或答案機率。
- 額外分類器預測適合的 budget。
- 從 oracle allocation 學習一個 routing policy。

近期 constrained policy optimization 類方法，會先從完整結果求得 oracle action，再訓練輕量分類器模仿該配置。這證明「在全域成本限制下學習每題配置」是一個重要且快速發展的方向。

相較之下，本研究不先訓練一個新 router，而是測試推理過程本身已免費產生的可觀察訊號。研究問題更接近：

> 在不新增模型與訓練成本的條件下，第一段輸出的進度狀態是否已足以支援有效配置？

## 4.4 Early stopping、hidden-state probes 與 reasoning trajectory

另一類研究觀察模型的推理軌跡，判斷何時已經收斂或何時可以停止。例如 Thought Calibration 使用 hidden representations 的 lightweight probes，判斷新增推理是否已經趨於飽和。

這些方法顯示 process-level signal 比單純題目難度更接近推理當下狀態。但 hidden-state probe 需要模型內部表示，未必適用於一般黑箱 API。

本研究的切入點是把 process signal 限定為外部可觀察資訊：

- 是否已出現 final answer。
- 是否仍有可見推理內容。
- 是否完全沒有可用的 visible progress。

## 4.5 目前研究缺口

綜合上述文獻，adaptive test-time compute 本身不是空白領域。較精確的研究缺口是：

> 對黑箱推理模型而言，目前仍需要一種不讀取 hidden state、不額外呼叫 verifier、能在第一段推理後即時運作，並且在實際 token 成本匹配下接受 policy-level 驗證的 allocation 方法。

本研究的具體定位是下列四項組合：

1. **Black-box compatible**：只讀 visible output 與 API metadata。
2. **Post-prefix decision**：不是只在看到題目前分配，而是在模型已執行一段推理後決策。
3. **Observable progress state**：訊號描述目前是否完成以及是否具有可見進展。
4. **Matched-cost policy evaluation**：在相同實際 token 成本下比較最終正確率。

這裡不應宣稱沒有人做過動態配置，而應主張這個具體設定與驗證組合值得研究。

### 主要參考文獻

- Snell, Lee, Xu, and Kumar. *Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters*. arXiv:2408.03314. <https://arxiv.org/abs/2408.03314>
- Han et al. *Token-Budget-Aware LLM Reasoning*. arXiv:2412.18547. <https://arxiv.org/abs/2412.18547>
- Wu, Zhou, Bates, and Jaakkola. *Thought Calibration: Efficient and Confident Test-Time Scaling*. EMNLP 2025. <https://aclanthology.org/2025.emnlp-main.722/>
- Alomrani et al. *Reasoning on a Budget: A Survey of Adaptive and Controllable Test-Time Compute in LLMs*. arXiv:2507.02076. <https://arxiv.org/abs/2507.02076>
- Zhai et al. *Adaptive Test-Time Compute Allocation for Reasoning LLMs via Constrained Policy Optimization*. arXiv:2604.14853. <https://arxiv.org/abs/2604.14853>

---

## 5. 研究目的、研究問題與假設

## 5.1 研究目的

本研究希望建立一個低額外成本、適用於黑箱 API 的動態推理資源配置方法。系統先給每題相同低預算，觀察模型輸出的進度狀態，再決定是否提供 continuation。最終目標是在固定資源條件下提高整體正確率，或在維持正確率的情況下降低 token 使用。

## 5.2 研究問題

### RQ1：可見推理進度是否與 continuation value 有關？

這個問題確認 visible progress 是否具有辨識力。重點不是它能否預測最終答對，而是不同狀態接受 continuation 後的邊際收益是否不同。

### RQ2：Visible-progress policy 是否能改善 matched-cost accuracy？

這是主要方法問題。若與不使用任何訊號、但具有相同預期 continuation token 成本的 random allocation 相比，visible-progress policy 具有更高正確率，才能說明訊號已轉化成有效的配置決策。

### RQ3：方法在什麼情況下最有價值？

方法價值可能受到模型、prefix budget 與資料難度影響。如果某模型大多數題目在 prefix 已完成，就沒有太多題目需要動態配置。因此研究還需分析：

- `visible_unfinished` 出現比例。
- 各狀態的 continuation benefit、harm 與 unresolved 比例。
- 方法相對 Fixed Low 與 Fixed Continue 的 accuracy–cost 位置。

## 5.3 研究假設

### H1：狀態異質性假設

`visible_unfinished` 的平均 continuation gain 高於 `complete` 與 `empty_unfinished`。

### H2：配置效益假設

在相同預期實際 continuation token 成本下，Visible-Progress Allocation 的正確率高於 no-signal random allocation。

### H3：計算效率假設

Visible-Progress Allocation 能以低於 Fixed Continue 的平均 token 使用，取得相近或更高的正確率。

### H4：適用邊界假設

方法效益取決於可分配狀態是否存在。當 `visible_unfinished` 幾乎不出現時，方法的改善空間會縮小。

H4 不是失敗條件，而是方法適用範圍的一部分。

---

## 6. 研究方法

## 6.1 整體框架

每題依序經過四個步驟：

```text
問題輸入
   ↓
固定低預算 prefix
   ↓
可見進度狀態判定
   ↓
stop 或 contextual continuation
   ↓
最終答案、正確性與實際 token 成本
```

Controller 不判斷答案是否真的正確，因為部署時沒有 reference answer。它只判斷目前是否存在可解析答案，以及未完成時是否已有可見推理內容。

## 6.2 Prefix 與 continuation

**Prefix** 是所有題目都會執行的第一段推理。它提供基本答案，也產生後續配置所需的 visible state。

**Contextual continuation** 是選擇性追加的第二次請求。它保留原始題目與 prefix 的可見內容，要求模型沿用現有工作繼續完成，而不是重新從頭解題。

本研究目前的 confirmatory 設定為：

- Prefix budget：512 `num_predict` tokens。
- Continuation budget：512 `num_predict` tokens。
- Temperature：0.0。
- 所有成本使用 API request 所記錄的 actual total tokens。

重要區分：512 是請求上限，不代表每次都實際使用 512 completion tokens；soft prompt 中提到的 budget 也不能直接視為 API 實際成本。

## 6.3 三種可觀察狀態

| 狀態 | 可觀察定義 | 方法中的解釋 | Policy action |
|---|---|---|---|
| `complete` | visible content 已有可解析 final answer | 模型已完成輸出 | Stop |
| `visible_unfinished` | 沒有可解析 final answer，但 visible content 非空 | 已有可利用的推理進度 | Continue |
| `empty_unfinished` | 沒有可解析 final answer，visible content 為空 | 沒有可供 continuation 延續的外顯軌跡 | Stop / unresolved |

狀態分類具有以下邊界：

- 只讀 visible `content`。
- 不讀 hidden `thinking`。
- 不使用 reference answer。
- 不使用 continuation 後結果。
- 使用事前固定的 brace-aware final-answer parser。

## 6.4 Visible-Progress Allocation policy

令 (V_i=1) 表示題目 (i) 的 prefix state 是 `visible_unfinished`。Policy 為：

\[
\pi_i=
\begin{cases}
\text{continue}, & V_i=1,\\
\text{stop}, & V_i=0.
\end{cases}
\]

最終正確性為：

\[
A_V=\frac{1}{N}\sum_i\left[V_i y_i^H+(1-V_i)y_i^L\right].
\]

平均實際 token 成本為：

\[
T_V=\frac{1}{N}\sum_i\left[c_i^L+V_i c_i^H\right],
\]

其中 (c_i^L) 是 prefix request 的 actual total tokens，(c_i^H) 是 continuation request 的 actual total tokens。

## 6.5 為什麼需要共同 action bank

若只執行 deployed policy，我們只能看到被選 action 的結果，無法知道停止的題目接受 continuation 後是否會改善，也無法公平重播其他 policy。

因此，研究評估階段對每一個 model-question unit 都收集：

1. Prefix action。
2. Contextual continuation action。

這形成共同 **action bank**。所有政策都使用同一組已記錄 outcome 進行 replay，避免不同政策因模型隨機性或題目差異而不可比較。

需要清楚說明：

- Action bank 是研究評估工具。
- 正式部署的 visible-progress policy 不會每題都呼叫 continuation。
- Counterfactual collection cost 不等於 deployed policy runtime cost。

## 6.6 比較政策

| Policy | 決策方式 | 研究用途 |
|---|---|---|
| Fixed Low | 全部停止 | 最低計算基線 |
| Fixed Continue | 全部續寫 | 高計算基線 |
| Question-only | 只使用題目難度 | 檢驗 process state 是否超過靜態題目訊號 |
| Random count-matched | 隨機選相同題數 | 匹配 continuation 數量 |
| Random cost-calibrated | 隨機配置，但匹配預期實際 continuation token 成本 | 主要公平比較 |
| Visible-Progress | 只續寫 `visible_unfinished` | 本研究方法 |
| Oracle | 使用事後真實 gain 選題 | 理想上界，不可部署 |

**Oracle** 的意思是評估者事後知道每題接受 continuation 是否有益，再選出最佳 action。它用來衡量理論改善空間，不能被當成實際方法，也不能拿來主張部署表現。

## 6.7 成本匹配的主要比較

只匹配 continuation 題數仍可能不公平，因為不同題目的 continuation request 使用不同 actual tokens。

Visible-Progress policy 的總 continuation 成本為：

\[
C_V=\sum_i V_i c_i^H.
\]

Cost-calibrated random 對每題使用相同選擇機率：

\[
p=\frac{C_V}{\sum_i c_i^H}.
\]

因此它的預期 continuation 成本為：

\[
E\left[\sum_i Z_i c_i^H\right]
=p\sum_i c_i^H
=C_V.
\]

主要 estimand 是：

\[
\Delta A=A_{\text{Visible-Progress}}-A_{\text{Random, cost-matched}}.
\]

這個比較回答：

> 當兩個政策預期花費相同 continuation tokens 時，使用 visible progress 選題，是否比沒有訊號的隨機配置得到更高正確率？

Random cost-calibrated 是 action-bank 下的 evaluation benchmark。因為它使用完整 action bank 中的 realised continuation cost 進行校準，所以不應描述成線上 random scheduler。

## 6.8 實驗設計

### 資料與模型

| 項目 | 設定 |
|---|---|
| Dataset | MATH-500 test |
| 正式題數 | 60 個未用於規則形成的新題目 |
| 難度分層 | 30 題 Level 3、30 題 Level 4 |
| 模型 | GPT-OSS-120B、DeepSeek-V4-Flash-158B |
| 每題 actions | Prefix、contextual continuation |
| Formal records | 60 題 × 2 模型 × 2 actions = 240 |

### Held-out 原則

Visible-only rule 必須在檢視 confirmatory sample 結果之前固定。新 manifest 排除歷史資料中已出現的題目，避免使用同一資料選擇規則又驗證規則。

### 記錄欄位

每筆 action record 應保留：

- Model ID、question ID、action。
- Visible content 與 thinking，thinking 只用於 audit。
- Done reason。
- Parser result 與 correctness。
- Prefix process state。
- Prompt、completion、total tokens。
- API metadata、elapsed time 與 error。

### 統計推論

主要推論使用 10,000 次 question-clustered bootstrap：

- 以 `question_id` 為重抽單位。
- 同一題在兩模型的觀測一起保留。
- 每次 replicate 重新計算 policy outcome、成本匹配機率與差異。
- 報告 effect size 與 percentile 95% confidence interval。

這個設計保留同一題跨模型觀測的依賴關係，也直接針對主要 estimand 建立不確定性區間。

## 6.9 評估指標

Proposal 簡報應優先呈現下列指標：

1. **Final accuracy**：政策執行後的最終正確率。
2. **Mean actual total tokens per question**：每題平均實際總 token。
3. **Matched-cost accuracy difference**：相同成本下的正確率差異。
4. **State support**：各模型有多少 `visible_unfinished` 案例。
5. **State-specific continuation outcome**：benefit、unchanged、harm、unresolved。

PR-AUC 可以作為訊號可行性的輔助證據，但不能取代 matched-budget policy evaluation。預測效果不等於資源配置效果。

---

## 7. Preliminary evidence 在 Proposal 中應如何呈現

結果只需要回答三個問題，不需要逐階段回顧所有實驗。

## 7.1 Visible progress 是否具有 continuation value？

Development evidence 顯示，`visible_unfinished` 是 continuation benefit 最集中的狀態：

- GPT-OSS-120B：11 個 visible cases 中有 9 個受益。
- DeepSeek：5 個 visible cases 中有 4 個受益。
- Complete cases 沒有正向 gain。
- GPT 的 empty unfinished cases 沒有形成穩定收益。

這組證據的用途是說明為什麼 confirmatory policy 固定成「只續寫 visible unfinished」。它不是主要結論頁。

## 7.2 Matched-cost policy 是否有效？

Held-out Stage 3 的主要結果：

| 指標 | GPT-OSS-120B | DeepSeek-V4-Flash-158B | Pooled |
|---|---:|---:|---:|
| Visible-Progress accuracy | 70.00% | 86.67% | — |
| Cost-calibrated random accuracy | 60.38% | 82.42% | — |
| Accuracy difference | +9.62pp | +4.25pp | +6.78pp |
| Pooled 95% bootstrap CI | — | — | [3.48, 10.22]pp |
| Visible cases | 12/60 | 4/60 | — |
| Cost identity error | 0.0 | 0.0 | 0.0 |

解讀方式：

- GPT 提供目前最清楚的 model-specific evidence。
- 兩模型 effect direction 一致。
- Pooled confidence interval 不含 0。
- DeepSeek 只有 4 個 visible cases，未達事前規劃的 5-case support threshold，因此應視為方向一致但事件數不足。
- 整體 study flag 為 false，原因是 DeepSeek support criterion 未通過，不應直接改寫成「所有確認條件都成功」。

## 7.3 Efficiency frontier

另一個對 Proposal 有價值的結果，是方法相對 Fixed Continue 的位置：

- GPT：Visible-Progress 70.00% accuracy、667.9 tokens；Fixed Continue 66.67%、1095.8 tokens。
- DeepSeek：Visible-Progress 與 Fixed Continue 都是 86.67%，但平均 tokens 為 381.8 對 733.2。

這支持 Visible-Progress 能避開不必要 continuation。但下一版簡報應避免堆疊太多 baseline，只需用一張 accuracy–cost 圖呈現主要位置。

---

## 8. 研究貢獻的建議表述

### 8.1 方法貢獻

提出一個黑箱 API 可用的 post-prefix controller，只根據 visible progress state 決定是否追加 contextual continuation。

### 8.2 評估貢獻

把訊號預測轉化成 policy-level evaluation，並在相同預期 actual continuation token 成本下比較最終正確率。

### 8.3 實證貢獻

在未參與規則形成的新 MATH-500 題目上，得到正向 matched-cost evidence，並辨識方法效益依賴 visible-state support 的適用條件。

### 8.4 工程與可重現性貢獻

建立 manifest exclusion、共同 action bank、parser audit、token ledger、checkpoint/retry 與 clustered bootstrap 的可 audit 實驗流程。

---

## 9. 方法限制與下一步研究

Proposal 不需要弱化方法，但應主動界定目前證據範圍。

### 9.1 現有範圍

- 單一推理資料集 MATH-500。
- Level 3 與 Level 4 題目。
- 兩個模型。
- 固定 512-token prefix 與 512-token continuation。
- 目前 action 只有 stop 與 continue。

### 9.2 下一步驗證

優先順序建議如下：

1. **跨資料集驗證**：加入不同形式的推理任務，檢驗 state definition 是否泛化。
2. **跨 budget 驗證**：改變 prefix 長度，觀察 visible-state support 與 allocation value 如何變化。
3. **線上全域 token ledger**：事前給定總預算，讓 policy 在不知道 future continuation cost 的情況下配置。
4. **更細緻的 progress features**：在維持 black-box 與低成本前提下，從可見輸出抽取進度、重複、停滯或答案形成等特徵。
5. **擴充 action space**：除了 continuation，加入 verifier、重新採樣或工具呼叫，形成多 action allocation。

### 9.3 Process mining 的合理位置

目前方法使用的是事前定義的 observable process states，還不是完整的 process mining 系統。未來若累積更長的 event log，可以使用流程探勘來：

- 發現不同推理路徑與常見停滯模式。
- 分析哪些 transition 最常帶來正向 continuation value。
- 將單一步驟 state classifier 擴充成 trajectory-aware controller。

簡報中應把這部分放在下一步，而不是把目前方法描述成已完成完整 process discovery。

### 9.4 Confidence 的合理位置

Confidence 可以保留為機制診斷或未來輔助特徵，用來研究模型主觀判斷何時與 visible progress 一致。但目前主方法不需要 confidence 才能運作，因此 Proposal 不應讓 confidence 與 visible progress 競爭主線。

---

## 10. 下一版簡報的 24 頁結構

以下每頁只處理一個主要問題。這能避免目前版本同一頁同時承擔背景、方法與結果。

### 第 1 頁：封面

**標題**：以可觀察推理進度進行大型語言模型的動態測試時計算分配  
**副標題**：Visible-Progress Allocation for Test-Time Compute  
**目的**：讓老師立即知道研究主體是 resource allocation，不再以 confidence calibration 作為主標題。

### 第 2 頁：研究問題地圖

**要回答的問題**：整份 Proposal 的邏輯是什麼？  
**內容**：有限預算 → 題目收益不同 → 需要 allocation signal → visible progress → matched-cost evaluation。  
**視覺**：單一路徑流程圖，不放結果數字。

### 第 3 頁：Test-time compute 的角色

**要回答的問題**：為什麼推理階段的計算值得研究？  
**內容**：更多推理、sampling、revision 或 verifier 能改善表現，但帶來成本。  
**概念**：test-time compute、token、latency。

### 第 4 頁：均勻配置的問題

**要回答的問題**：為什麼不能所有題目都給相同預算？  
**內容**：有些題目已完成，有些可救回，有些追加也無效。  
**視覺**：三到四個題目案例的資源需求差異。

### 第 5 頁：難度與 continuation value

**要回答的問題**：為什麼不是單純預測難題？  
**內容**：難度描述成功機率，continuation value 描述額外計算造成的邊際改變。  
**公式**：(g_i=y_i^H-y_i^L)。

### 第 6 頁：黑箱 API 的決策限制

**要回答的問題**：部署時 controller 真正看得到什麼？  
**內容**：問題、visible output、parser、token metadata。不可使用 reference answer 或 future outcome。

### 第 7 頁：文獻地圖

**要回答的問題**：相關工作有哪些主要路線？  
**內容**：test-time scaling、budget-aware reasoning、difficulty/confidence routing、trajectory/early stopping。  
**視覺**：四條路線放在同一張概念地圖。

### 第 8 頁：Compute-optimal allocation

**要回答的問題**：文獻已經證明了什麼？  
**內容**：資源收益依題目而異，adaptive allocation 比均勻配置更合理。  
**代表文獻**：Snell et al.、AdaCompute。

### 第 9 頁：Budget-aware 與 confidence-based 方法

**要回答的問題**：既有方法通常使用哪些訊號？  
**內容**：預算控制、題目難度、confidence、learned router。  
**重點**：這些方法與 visible progress 的差異，不做優劣式批評。

### 第 10 頁：Process-level 與 early stopping 方法

**要回答的問題**：為什麼研究推理過程而非只看題目？  
**內容**：模型執行後的 trajectory 提供即時資訊；部分方法需要 hidden states 或 probes。  
**代表文獻**：Thought Calibration。

### 第 11 頁：研究缺口與定位

**要回答的問題**：本研究新增的是什麼？  
**內容**：black-box compatible、post-prefix、observable state、matched-cost policy evaluation。  
**視覺**：相關工作比較表。

### 第 12 頁：研究目的與 RQ

**要回答的問題**：本研究具體要回答什麼？  
**內容**：RQ1 continuation value、RQ2 matched-cost policy、RQ3 applicability boundary。

### 第 13 頁：研究假設

**要回答的問題**：什麼結果會支持方法？  
**內容**：H1 狀態異質性、H2 matched-cost accuracy、H3 efficiency、H4 support boundary。

### 第 14 頁：Visible-Progress Allocation 整體框架

**要回答的問題**：方法從輸入到輸出如何運作？  
**內容**：question → prefix → state → stop/continue → final outcome。  
**視覺**：全簡報最重要的單一流程圖。

### 第 15 頁：Prefix 與 contextual continuation

**要回答的問題**：兩個 action 的內容與差異是什麼？  
**內容**：固定 prefix、保留 context 的 continuation、不可重新開始、實際 token 記錄方式。

### 第 16 頁：三種 observable states

**要回答的問題**：complete、visible unfinished、empty unfinished 如何判定？  
**內容**：定義、範例、policy action。  
**視覺**：三個真實輸出片段或簡化範例，比抽象表格更容易理解。

### 第 17 頁：Controller 的資訊邊界

**要回答的問題**：方法有沒有偷看答案或未來資訊？  
**內容**：可以使用與禁止使用的欄位。  
**目的**：讓老師理解方法可部署且沒有 leakage。

### 第 18 頁：Action bank 與 counterfactual evaluation

**要回答的問題**：怎麼公平知道不同 policy 的結果？  
**內容**：每題收集 low/high actions，再在同一 outcomes 上 replay policy。  
**重點**：研究收集成本與部署成本不同。

### 第 19 頁：Baseline 與 Oracle

**要回答的問題**：方法要跟誰比較？  
**內容**：Fixed Low、Fixed Continue、question-only、random、oracle。  
**重點**：Oracle 是事後理想上界，不是部署方法。

### 第 20 頁：Matched-cost evaluation

**要回答的問題**：如何確保比較不是因為方法花更多 token？  
**內容**：(C_V)、(p)、成本期望相等與主要 estimand。  
**視覺**：左邊 allocation，右邊相同 token ledger。

### 第 21 頁：Confirmatory experiment

**要回答的問題**：如何避免用同一資料選規則又驗證規則？  
**內容**：new manifest、60 題、兩模型、240 actions、question-clustered bootstrap。

### 第 22 頁：Preliminary evidence

**要回答的問題**：目前有什麼證據支持繼續研究？  
**內容**：一張 matched-cost 主要結果圖，GPT +9.62pp、DeepSeek +4.25pp、pooled +6.78pp。  
**限制**：DeepSeek 只有 4 個 visible cases。

### 第 23 頁：Accuracy–cost 與適用條件

**要回答的問題**：方法何時最有價值？  
**內容**：相對 Fixed Low、Fixed Continue 的位置，以及 visible-state support。  
**重點**：方法價值來自把 continuation 集中在 responsive minority。

### 第 24 頁：研究貢獻與下一步決策

**要回答的問題**：老師需要協助確認什麼？  
**內容**：

- 是否以 black-box visible-progress allocation 作為論文主軸。
- 下一輪先做跨資料集，還是跨 prefix budget。
- 投稿時將重點放在 controller、process signal，或 matched-cost evaluation design。

---

## 11. 製作下一版簡報時的內容規則

1. 一頁只回答一個主要問題。
2. 先解釋概念，再出現公式。
3. 每個公式旁邊一定要有口語解讀。
4. 結果只保留能回答 RQ 與 H 的數字。
5. 不逐一回顧研究過程中未形成主方法的路線。
6. Confidence 只放在文獻或未來機制分析，不放進主要 controller。
7. 不把目前方法稱為完整 process mining；使用 observable process state 或 process-aware allocation。
8. 清楚區分 API token cap、prompt 中的 soft budget 與實際 billed tokens。
9. 清楚區分 predictive signal 與 allocation policy evidence。
10. DeepSeek 結果保留 support limitation，不宣稱兩模型都完成獨立確認。

---

## 12. 最終 Proposal 應讓老師帶走的三個重點

1. **研究問題成立**：額外推理的價值因題目與當前進度而異，有限資源需要動態配置。
2. **方法容易理解且可部署**：只看 prefix 的 visible progress，選擇 stop 或 contextual continuation。
3. **已有初步方法證據，但仍有清楚研究空間**：matched-cost 結果支持方向，下一步需要擴大資料集、budget 與模型條件，確認外部泛化與適用邊界。

這三點比完整展示所有實驗歷程更適合 Proposal 報告，也能讓老師針對研究定位、方法嚴謹度與下一輪設計提出具體建議。
