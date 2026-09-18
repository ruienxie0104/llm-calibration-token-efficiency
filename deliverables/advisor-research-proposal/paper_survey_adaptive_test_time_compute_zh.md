# Paper Survey：Adaptive Test-Time Compute 與本研究的真實創新空間

> 調查日期：2026-09-18  
> 目的：判斷「利用可觀察推理進度分配 test-time compute」是不是值得處理的研究問題，以及目前 Visible-Progress Allocation 是否已有足夠方法創新。  
> 調查範圍：以 2022–2026 年的 test-time scaling、adaptive compute allocation、early stopping、prefix pruning、confidence routing、global budget allocation 與 evaluation/reproducibility 文獻為核心。本文是針對研究問題的系統性代表文獻盤點，不宣稱涵蓋網路上每一篇相關文章。

---

## 1. 先講結論

### 1.1 這個問題是真的，而且仍然需要處理

「有限 test-time compute 應該分給哪些問題、哪些推理路徑或哪些階段」已經被多篇研究確認為重要問題。固定配置會同時造成簡單題 overthinking 與困難題 underthinking；不同題目接受額外計算後的邊際收益也不相同。近期工作甚至把它正式建模成 constrained optimization、bandit learning、risk control 與 online scheduling 問題。

因此，**問題本身不是假問題，也不是只為了你們的實驗而創造的問題**。

### 1.2 但「做 test-time compute 資源配置」已經不是研究缺口

這個廣義方向非常擁擠。現有方法已經涵蓋：

- 依題目難度配置 token 或 sampling budget。
- 依 confidence、answer agreement 或 entropy 決定停止。
- 使用 hidden states 預測需要多少推理。
- 在 prefix 後判斷哪些 reasoning paths 應繼續。
- 在全域 budget 下用 bandit 或 constrained optimization 分配資源。
- 使用 process/reward model 對中間狀態進行 pruning。
- 直接學習 stop/continue 或多層 budget policy。

所以不能把貢獻寫成「我們首次發現每題不該使用相同 token」或「我們首次提出動態 test-time compute allocation」。這兩種主張都不成立。

### 1.3 目前 Visible-Progress 方法本身的創新強度有限

目前方法使用三個人工定義的 surface states：

- `complete`
- `visible_unfinished`
- `empty_unfinished`

再以固定規則只續寫 `visible_unfinished`。從最新 prefix-pruning taxonomy 來看，這會被歸類成 **external、non-learnable surface heuristic**。這類方法的優點是便宜、透明、黑箱可用，但演算法新穎性不高。

Stage 3 的 matched-cost結果是重要證據，證明這個簡單訊號確實可能有效；但它更像是：

> 一個很好的 baseline、可行性證明或設計原則，而不是目前文獻中明顯領先的新 allocation algorithm。

### 1.4 最合理的決策不是放棄，而是把研究問題縮得更精確

建議把主題從廣義的：

> 使用流程狀態分配 test-time compute。

收斂成：

> 在無法取得 logits、hidden states、reward model 或 ground-truth verifier 的黑箱 API 環境中，如何利用 post-prefix 可觀察事件，預測 continuation 的邊際效用，並在事前給定的全域 token ledger 下做線上資源配置？

這個問題仍有研究空間，因為它同時加入：

1. 黑箱 API 限制。
2. Post-prefix 而非 pre-query 決策。
3. 預測 continuation value，而非單純預測 difficulty 或 correctness。
4. 事前給定的全域 budget，而非事後 action-bank cost matching。
5. 真正線上 stop/continue 或多 action policy。

如果不加入上述至少兩到三項，現有方法很容易被審稿人視為簡單 heuristic。

---

## 2. 文獻問題地圖

相關研究可以沿五個軸理解。

| 軸 | 主要選項 | 本研究目前位置 |
|---|---|---|
| 決策時間 | 推理前、推理中、prefix 後、跨多輪 | 固定 prefix 後 |
| 決策訊號 | 題目、confidence、agreement、hidden state、visible trace、verifier | visible trace 的粗粒度狀態 |
| 分配資源 | token 長度、sample 數量、search depth、model size、continuation、verifier calls | 一次 contextual continuation |
| 預算範圍 | 每題獨立 budget、batch/global budget、latency SLO | action-bank 中的平均/總 token 比較 |
| 評估方式 | 固定 budget、matched count、matched FLOPs、matched actual token、online ledger | matched expected actual continuation tokens |

你們的真正差異不在「有 allocation」，而在這五個軸的具體組合。

---

## 3. 第一類文獻：Test-time scaling 的基礎

### 3.1 Chain-of-Thought Prompting

Wei et al. 證明生成中間推理步驟能改善 arithmetic、commonsense 與 symbolic reasoning。它建立了增加 sequential reasoning compute 的基礎。

- Paper：[Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903)
- 與本研究關係：解釋為什麼額外推理可能有價值，但沒有處理有限資源下的動態配置。

### 3.2 Self-Consistency

Wang et al. 以多條 reasoning paths 與答案投票改善正確率，建立 parallel test-time scaling 的經典設定。

- Paper：[Self-Consistency Improves Chain of Thought Reasoning in Language Models](https://arxiv.org/abs/2203.11171)
- 與本研究關係：主要資源是 sample 數量；你們主要資源是單一路徑的 contextual continuation。

### 3.3 Compute-optimal test-time scaling

Snell et al. 顯示不同題目難度適合不同的 search/revision 配置，並報告 compute-optimal 策略可比 best-of-N 更有效率。

- Paper：[Scaling LLM Test-Time Compute Optimally can be More Effective than Scaling Model Parameters](https://arxiv.org/abs/2408.03314)
- 與本研究關係：已明確提出 per-prompt adaptive allocation，因此你們不能以「不同題目需要不同 compute」作為新穎主張。

### 3.4 Budget forcing

s1 以終止 reasoning 或反覆加入 “Wait” 延長 reasoning，展示簡單控制就能改變 test-time scaling。

- Paper：[s1: Simple Test-Time Scaling](https://arxiv.org/abs/2501.19393)
- 與本研究關係：證明 continue/stop intervention 本身不新；你們必須證明如何選擇 intervention 才是貢獻。

### 判斷

Test-time compute 能改善表現、均勻配置可能浪費資源，這兩件事已是領域共識，不再構成研究缺口。

---

## 4. 第二類文獻：固定預算、budget-aware reasoning 與效率評估

### 4.1 Reasoning in Token Economies

Wang et al. 指出，複雜 reasoning strategy 的優勢有時只是因為使用更多 compute，因此必須在 budget-aware 條件下評估。

- Paper：[Reasoning in Token Economies](https://aclanthology.org/2024.emnlp-main.1112/)
- 與本研究關係：直接支持你們堅持 matched-cost evaluation 的必要性。

### 4.2 Token-Budget-Aware LLM Reasoning / TALE

Han et al. 根據 reasoning complexity 動態選擇 prompt token budget，以降低冗長 reasoning。

- Paper：[Token-Budget-Aware LLM Reasoning](https://aclanthology.org/2025.findings-acl.1274/)
- 與本研究關係：同樣關心 per-problem budget，但主要在推理前設定 soft budget；你們是在 prefix 後決定是否續寫。

### 4.3 Plan-and-Budget

Plan-and-Budget 將問題拆成 sub-questions，再依不確定性或複雜度分配局部 token budget。

- Paper：[Plan and Budget](https://proceedings.iclr.cc/paper_files/paper/2026/hash/ae8d4084f418bb51575c2ca6c658a05b-Abstract-Conference.html)
- 與本研究關係：已是 model-agnostic adaptive scheduling 方法，且有理論與跨任務結果。你們的簡單 state rule 在方法複雜度與實驗規模上都較弱，但黑箱 API 與低 overhead 仍是差異。

### 4.4 Reasoning on a Budget survey

Alomrani et al. 將方法分為固定限制下的 controllability 與依難度或信心動態調整的 adaptiveness，並整理 sequential 與 parallel compute。

- Survey：[Reasoning on a Budget](https://arxiv.org/pdf/2507.02076)
- 關鍵含義：2025 年時 adaptive TTC 已有大量 prompting、SFT 與 RL 方法。廣義方向已成熟，不宜再以「缺乏 adaptive compute」作為唯一缺口。

### 判斷

你們在成本核算上是對的，而且 matched actual token 是優點；但「考慮 token efficiency」本身也不是創新。

---

## 5. 第三類文獻：依題目或 batch 分配資源

這類工作與你們的「把有限資源分給最值得的題目」最直接競爭。

### 5.1 DynaThink

DynaThink 根據模型對問題複雜度與信心的判斷，在 fast 與 slow reasoning 路徑之間選擇。

- Paper：[DynaThink](https://arxiv.org/abs/2407.01009)
- 決策時間：推理前或非常早期。
- 訊號：模型自評複雜度與信心。
- 差異：你們使用已產生的 prefix state，不依賴 verbal confidence。

### 5.2 Dynasor / Certaindex

Dynasor 是 serving system，依統計 certainty 追蹤 reasoning progress，動態排程與終止 query。

- Paper：[Efficiently Serving LLM Reasoning Programs with Certaindex](https://arxiv.org/abs/2412.20993)
- 決策範圍：同時考慮 batch scheduling、accuracy、latency 與 cost。
- 對你們的威脅：它已使用 progress proxy 做線上 allocation，且具有系統層級實驗。
- 可區分點：你們關注單一黑箱 sequential continuation，而不是多 sample reasoning program serving。

### 5.3 Strategic Scaling of Test-Time Compute

Zuo and Zhu 把跨 query 的計算分配建模成 bandit learning，在總 budget 下邊採樣、邊估計題目難度與可解性。

- Paper：[Strategic Scaling of Test-Time Compute: A Bandit Learning Approach](https://proceedings.iclr.cc/paper_files/paper/2026/hash/d8d2c5f79c53a2a685dbdf93f78c5695-Abstract-Conference.html)
- 優勢：正式全域 budget、理論分析、MATH/AIME/LiveCodeBench。
- 限制：主要採 Best-of-N，並假設 reward oracle 或可近似 verifier。
- 對你們的含義：如果你們想主張「跨題分配有限資源」，一定要比較或清楚區分此工作。

### 5.4 Predictive Scheduling

Predictive Scheduling 用 raw question 或 intermediate hidden states 預測 optimal reasoning length，再用 greedy batch allocator 分配固定總 token budget。

- Paper：[Predictive Scheduling](https://arxiv.org/abs/2602.01237)
- 優勢：明確 matched total token、全域 allocator、學習式 predictor。
- 限制：需要 hidden states 或訓練 classifier，且主要在完整 generation 前預測。
- 你們可能的差異：不需模型內部存取，且在 prefix 後利用實際執行狀態。

### 5.5 AdaCompute

AdaCompute 先用 Lagrangian oracle 求解各題最佳 action，再用 cheap input features 訓練分類器模仿 oracle policy。

- Paper：[Adaptive Test-Time Compute Allocation via Constrained Policy Optimization](https://arxiv.org/abs/2604.14853)
- 優勢：constrained optimization、精確 budget targeting、regret bound、三模型與兩資料集。
- 對你們的威脅：研究目標幾乎相同，而且方法與理論更完整。
- 主要差異：AdaCompute 主要從 input features 預測；你們可轉向 post-prefix observable event features 與 black-box action space。

### 5.6 Sonata / Adaptive Thinking

Sonata 使用 prefilling 階段 hidden representation 預測 self-consistency，進而配置 thinking budget。

- Paper：[Adaptive Thinking](https://machinelearning.apple.com/research/adaptive-thinking)
- 報告在多模型、多 benchmark 下節省 thinking tokens 或提高同成本 accuracy。
- 差異：需要 hidden representations 與 offline adapter；你們只需 visible API output。

### 5.7 Thinking Hard, Not Smart

這項 2026 年研究建立 exam-style global budget framework，發現多個模型無法在多題間依難度與分數有效分配共享 token budget。

- Paper：[Thinking Hard, Not Smart](https://arxiv.org/abs/2608.07968)
- 重要性：直接證明 global allocation 是獨立且尚未解決的能力問題。
- 對你們的機會：把 visible progress controller 放進真正的共享 ledger，而不是只做 action-bank expected-cost matching。

### 判斷

跨題資源配置是重要問題，但已有很強的理論與方法工作。你們若仍停在固定三狀態 heuristic，難以在這個子領域主張方法領先。

---

## 6. 第四類文獻：Adaptive sampling 與 agreement stopping

### 6.1 Adaptive-Consistency

Adaptive-Consistency 根據目前 samples 的多數答案穩定程度，決定是否繼續生成更多 samples。

- Paper：[Let’s Sample Step by Step](https://arxiv.org/abs/2305.11860)
- 結果：大幅減少 samples，平均 accuracy drop 很小。
- 差異：它需要多條完整或逐次 samples；你們只用單一 prefix。

### 6.2 Early-Stopping Self-Consistency

ESC 在 sampling answers 趨於一致時提前停止。

- Paper：[Escape Sky-high Cost](https://arxiv.org/abs/2401.10480)
- 差異：agreement 是跨 paths 的訊號；你們使用單一 path 的可見完成狀態。

### 6.3 Answer Convergence

Liu and Wang 在 reasoning chunks 間重複抽取答案，當答案收斂時停止；也測試 learn-to-stop 的 internal activation classifier。

- Paper：[Answer Convergence as a Signal for Early Stopping in Reasoning](https://aclanthology.org/2025.emnlp-main.904/)
- 對你們的威脅：同樣是 process-time observation 與 stop decision，而且是 training-free 的 output-based 方法之一。
- 差異：它偵測已經收斂並提早結束；你們在硬 prefix 截點後決定是否重新續寫。

### 6.4 TRACE

TRACE 聚合多步 answer consistency 與 confidence trajectory，避免依賴單一步驟信號。

- Paper：[Efficient Test-Time Scaling via Temporal Reasoning Aggregation](https://arxiv.org/abs/2604.17304)
- 對你們的含義：文獻已開始從單一 snapshot 轉向 trajectory evidence。三狀態 snapshot 會被質疑是否太粗。

### 判斷

你們先前的 agreement route 因 API 與成本限制不可行，這在工程上合理；但文獻已證明 agreement/trajectory 是重要 baseline。論文不能略過，只能說明黑箱 API 條件與額外呼叫成本使問題設定不同。

---

## 7. 第五類文獻：Prefix pruning、process state 與 early stopping

這是與 Visible-Progress Allocation 最接近的一群。

### 7.1 Knowing Before Saying

Afzal et al. 使用 LLM hidden representations 預測 CoT 成功，並顯示早期 representation 已包含大量結果資訊。

- Paper：[Knowing Before Saying](https://aclanthology.org/2025.findings-acl.662/)
- 差異：hidden-state classifier 對黑箱 API 不可用；你們需要證明 visible output 在缺少 hidden states 時仍有價值。

### 7.2 Thought Calibration

Wu et al. 使用 hidden-representation probes 判斷新增 reasoning 是否已進入 plateau，動態終止推理。

- Paper：[Thought Calibration](https://aclanthology.org/2025.emnlp-main.722/)
- 優勢：process-aware、正式 calibration、跨模型與資料集。
- 差異：需要 internal representation；你們是 output-only black-box controller。

### 7.3 STOP / Cut Your Losses

STOP 在多條 reasoning paths 的固定 prefix 長度暫停，讀取 KV cache，學習哪些 prefixes 值得繼續完成。

- Paper：[Cut Your Losses! Learning to Prune Paths Early](https://arxiv.org/abs/2604.16029)
- 它提出的 taxonomy：
  - External + non-learnable：surface heuristic。
  - External + learnable：外部 judge。
  - Internal + non-learnable：raw confidence。
  - Internal + learnable：STOP 類模組。
- 你們目前位置：external + non-learnable。
- 對你們的最大威脅：它已直接做「prefix 後選擇是否 resume」，只是場景為 parallel path pruning。
- 可區分點：你們只需要黑箱 visible content，不需 KV cache、LoRA、head 或多條 parallel paths。

### 7.4 REFRAIN

REFRAIN 用 stop discriminator 與 sliding-window bandit threshold，偵測反思但冗餘的 reasoning，training-free 地決定停止。

- Paper：[Stop When Enough](https://aclanthology.org/2026.acl-long.1256/)
- 結果：多 benchmark、兩模型，減少 token 並維持或提升 accuracy。
- 對你們的威脅：同樣強調 training-free 與 when-to-stop，方法比單一 state rule 更細緻。

### 7.5 Conformal Thinking

Conformal Thinking 將停止規則轉成 risk control，同時停止高信心答案與預估無法解決的案例。

- Paper：[Conformal Thinking](https://machinelearning.apple.com/research/conformal-thinking-risk-control)
- 對你們的含義：現有方法不只追求平均 efficiency，也開始提供 user-specified risk guarantee。這是你們可以借鑑的方法升級方向。

### 7.6 MUR

MUR 使用 step-wise uncertainty 的 momentum，動態配置關鍵 reasoning steps 的 budget。

- Paper：[Momentum Uncertainty Guided Reasoning](https://aclanthology.org/2026.acl-long.1058/)
- 差異：需要 step-wise uncertainty；你們的 API setting 可能取得不到。

### 判斷

「先跑 prefix，再決定是否繼續」本身也已有直接文獻。你們剩下的空間主要是 **black-box、single-trajectory、output-only、actual-cost global allocation** 的組合，而不是 prefix decision 這個動作本身。

---

## 8. 第六類文獻：評估、protocol 與 reproducibility

### 8.1 Test-Time Scaling in Reasoning LLMs

Hariri et al. 將 TTS 分成 single-trajectory sequential、leaf-level aggregation 與 prefix-level scaling，並強調評估整個 inference system、區分 end-to-end performance 與 candidate-bank diagnostics。

- Paper：[Test-Time Scaling in Reasoning LLMs](https://arxiv.org/abs/2608.04001)
- 與本研究關係：你們的 action-bank replay 很接近它所說的 candidate-bank diagnostic。若要宣稱 deployable policy，還需補真正 online execution 或 protocol-matched ledger evaluation。

### 8.2 ARISE

ARISE 強調 test-time scaling evaluation 要考慮 sample-level negative scaling 與 token instability。

- Paper：[ARISE](https://aclanthology.org/2026.findings-acl.289/)
- 與本研究關係：你們已記錄 benefit、harm 與 unresolved，這是好的基礎；可以進一步把 negative scaling 納入 policy objective。

### 8.3 最新評估共識

較可信的 adaptive compute paper 通常需要：

- 明確說明 inference regime。
- 匹配實際 compute，而非只匹配 requests 或 nominal cap。
- 區分收集 counterfactual action bank 的成本與 deploy-time cost。
- 使用 held-out rule confirmation。
- 報告 uncertainty 與 per-model support。
- 進行跨 dataset、model、budget 的穩健性測試。

你們目前在前五項做得比許多早期工作更嚴謹，但外部廣度仍不足。

---

## 9. 最接近本研究的競爭矩陣

| Work | 決策時點 | 訊號 | 需要內部狀態/額外模型 | 全域 budget | 與你們重疊程度 |
|---|---|---|---|---:|---:|
| TALE | 推理前 | 題目複雜度 | 否 | 否 | 中 |
| DynaThink | 推理前 | 複雜度、信心 | 否/自評 | 否 | 中 |
| Predictive Scheduling | 推理前 | 題目或 hidden state | 是或另訓分類器 | 是 | 高 |
| Strategic Scaling | 推理過程中跨 samples | reward feedback | verifier/oracle | 是 | 高 |
| AdaCompute | 推理前 | cheap input features | 需訓 classifier | 是 | 很高 |
| Dynasor | reasoning program 執行中 | certainty/progress | 需要統計代理訊號 | 是 | 高 |
| Answer Convergence | reasoning chunks 間 | 答案一致性 | 多次 extraction | 否 | 高 |
| Thought Calibration | reasoning 過程中 | hidden state trajectory | 是 | 否 | 高 |
| STOP | 固定 prefix 後 | KV-cache learned score | 是 | 固定 retention quota | 很高 |
| REFRAIN | reasoning 過程中 | redundancy + bandit threshold | scorer | 否 | 高 |
| TRACE | 多 reasoning steps | agreement + confidence trajectory | 需要多步訊號 | 否 | 高 |
| Visible-Progress | 固定 prefix 後 | visible completion/progress state | 否 | 目前為事後 matched cost | 本研究 |

### 矩陣帶來的結論

Visible-Progress 仍有一個明確工程定位：

> 它是目前矩陣中 overhead 最低、最適合 opaque API 的方法之一。

但 overhead 低不自動等於方法創新。要形成研究貢獻，必須證明這項限制導致現有方法無法直接使用，並在這個限制下提出比固定 surface rule 更一般化的 allocation method。

---

## 10. 對目前實驗證據的重新評價

## 10.1 值得保留的部分

### A. 研究目標從 correctness prediction 轉向 continuation value

這是正確方向。真正 allocation target 應是額外計算的邊際收益，而不是題目是否困難或當前答案是否正確。

### B. Action bank 與 matched actual token evaluation

你們沒有把高 PR-AUC 直接當成 allocation 成功，而是比較 policy outcome；這符合最新 evaluation 文獻的要求。

### C. Held-out confirmatory rule

Stage 3 在新題目上固定 visible-only rule，避免同資料選規則與驗證規則。這比 post-hoc heuristic analysis 更可信。

### D. 黑箱 API 可部署性

不需要 hidden state、KV cache、logits、reward model 或 fine-tuning，這是實際優勢。

## 10.2 目前證據不足的部分

### A. 演算法過於簡單

三狀態規則只用了「有答案／有文字／沒有文字」。審稿人可能把它視為 sanity baseline，而不是主要方法。

### B. 只有單一 dataset 與單一 budget pair

MATH-500 Level 3/4、512+512 的結果不足以支持一般化主張。Visible-state frequency 對 budget 非常敏感。

### C. 兩模型中只有一個具有足夠 allocation events

GPT 有 12 個 visible cases，DeepSeek 只有 4 個。Pooled CI 雖為正，但 Stage 3 事前的 per-model support criterion 未完全通過。

### D. 主要 random comparator 仍是 action-bank evaluation benchmark

Cost-calibrated random 使用完整 action bank 中的 realised costs 進行期望匹配。它適合公平離線比較，但不等同事前給定 budget 的線上 allocator。

### E. 缺少強競爭 baseline

若投稿，至少應比較：

- Pre-query difficulty allocator。
- Observable-feature learned allocator。
- Online random ledger。
- Answer-convergence 或 confidence-based baseline，在 API 可行時。
- AdaCompute-style oracle imitation baseline。

---

## 11. 目前可以主張什麼，不能主張什麼

## 11.1 可以主張

1. 在目前 MATH-500 與兩個模型設定中，post-prefix visible state 與 continuation value 有關。
2. 一個低 overhead、output-only policy 在 matched expected continuation token cost 下，優於 no-signal random allocation。
3. 黑箱 API 的可見進度是一個值得納入 allocation controller 的訊號。
4. Allocation value 依賴模型與 budget 下是否產生足夠 `visible_unfinished` 事件。

## 11.2 不能主張

1. 首次提出 adaptive test-time compute allocation。
2. 首次使用 reasoning progress 決定停止或繼續。
3. Visible progress 普遍優於 confidence、difficulty 或 hidden-state methods。
4. 已經在多模型上完成獨立確認。
5. 現有 policy 是目前最先進的方法。
6. Process mining 已經構成主要方法；目前只有 process-state classification。

---

## 12. 三種可行的研究升級路線

## 路線 A：Black-box Post-Prefix Value Allocation

### 核心問題

不再只判斷 `visible_unfinished`，而是從 visible prefix 預測：

\[
U_i(a)=E[\text{accuracy gain}\mid x_i,\text{visible prefix}_i,a]
-\lambda E[\text{token cost}\mid x_i,\text{visible prefix}_i,a].
\]

Controller 在 stop、continue、resample、verify 等 actions 中選擇效用最高者。

### 可用的黑箱 features

- 是否已有 final answer。
- Visible token length。
- 是否正在形成方程式或結論。
- 重複與停滯程度。
- 自我修正或回溯語句。
- 目前可解析的 candidate answer 數量。
- Parser status 與 done reason。
- 題目特徵。
- 若成本允許，低頻率 confidence 或 verifier feature。

### 方法貢獻

訓練一個 **Observable Continuation Value Model**，直接預測 benefit、harm 與 cost，而不是只預測 correctness。再用全域 token ledger 做 constrained selection。

### 優點

- 延續你們現有 action bank。
- 與 AdaCompute 的 input-only allocator 明確不同。
- 與 STOP 的 hidden-state prefix scorer明確不同。
- Visible-only rule 可作最重要 baseline。

### 風險

- 需要更多 action-bank data。
- 容易 overfit，需要跨 dataset held-out validation。

### 評價

這是最平衡、最推薦的主線。

## 路線 B：Online Global Token Ledger

### 核心問題

給定一批問題與事前固定總 token budget，controller 每次看到 prefix 後，必須決定是否花下一筆 continuation cost；未來成本未知。

### 方法形式

- Contextual bandit。
- Knapsack under uncertain costs。
- Online primal-dual policy。
- Conformal/risk-controlled threshold。

### 必須比較

- Uniform budget。
- Random ledger。
- Difficulty-based policy。
- Strategic Scaling 類 bandit。
- AdaCompute 類 oracle imitation。
- Visible-state heuristic。

### 優點

- 解決目前 action-bank matched expectation 與真實部署的差距。
- 可直接連結 Thinking Hard, Not Smart 提出的 global rationing 問題。

### 風險

- 與 Strategic Scaling、Predictive Scheduling、AdaCompute 高度競爭。
- 必須提出清楚的新 signal 或演算法，不能只把 visible state 放進現有 knapsack。

### 評價

適合作為路線 A 的 policy layer，而不是單獨貢獻。

## 路線 C：Trajectory / Process-Mining Allocation

### 核心問題

把多個可觀察事件組成 trajectory，例如：

```text
problem_received
→ partial_equation
→ correction
→ repeated_attempt
→ candidate_answer
→ final_answer
```

使用流程探勘或 sequence model 找出哪些 process variants 最常從不同 actions 受益。

### 方法貢獻

- 發現 process variants。
- 計算 state-transition-specific continuation value。
- 將 allocation 從單一 snapshot 擴充成 history-dependent policy。

### 優點

- 更接近你最初的「流程 + 資源配置」研究構想。
- 與只做 difficulty routing 的文獻有較明顯差異。
- 可延伸到 tool-use agents 與 multi-step workflows。

### 風險

- 目前只有單一 prefix checkpoint，還不足以做真正 process mining。
- 需要多 checkpoint event logs，API 成本與 parser 複雜度上升。
- TRACE、REFRAIN、STOP 已在 trajectory/prefix 領域競爭。

### 評價

創新潛力最高，但工作量也最大。適合作為下一階段或博士級延伸。

---

## 13. 最推薦的新研究定位

### 建議題目

**Black-Box Post-Prefix Compute Allocation from Observable Continuation Value**

中文可寫成：

**基於可觀察續算價值的黑箱大型語言模型動態推理資源配置**

### 核心方法

1. 所有題目先取得固定 prefix。
2. 從 visible output 抽取可觀察 process features。
3. 預測每個 action 的 expected benefit、harm 與 actual token cost。
4. 在事前給定 global token ledger 下選擇 actions。
5. 以 online execution 驗證 accuracy–cost improvement。

### Visible-Progress rule 的新角色

現有三狀態 rule 不丟掉，而是變成：

- 最簡單且可解釋的 baseline。
- 新 value model 的高層 process feature。
- 驗證「更複雜方法是否真的超越簡單規則」的必要對照。

### Confidence 的新角色

Confidence 不必回到主 controller，但可以作為候選 feature 或診斷變數，檢驗它是否在特定 process state 中增加 continuation-value information。若沒有增量價值，就保留為機制限制，而不勉強進入 policy。

---

## 14. 下一個實驗應回答什麼

下一個實驗不應再問「visible-only 是否比 random 好」，因為 Stage 3 已經回答過一次。它應回答：

> 一個由 observable prefix features 學得的 continuation-value policy，能否在新的資料集、模型與事前固定 token ledger 下，穩定超越 visible-only heuristic、difficulty routing 與 random allocation？

### 最低可行設計

1. 至少兩個 reasoning datasets，不只 MATH-500。
2. 至少三個 prefix budgets，改變 state support。
3. 建立 train/development/held-out test 分割。
4. 收集 stop 與 continuation action bank。
5. 訓練 observable value model。
6. 用事前固定 ledger 做真正 online replay 或執行。
7. 比較 visible-only、question-only、random、learned value 與 oracle。
8. 報告 per-model、per-dataset、per-budget 結果與 clustered CI。

### Go/No-Go 標準

新方法至少應做到：

- 在大多數 model–dataset–budget strata 中方向一致。
- 相對 visible-only heuristic 的 paired CI 不含 0，或在預先規劃的 pooled analysis 中成立。
- 保持 exact 或可解釋的 ledger compliance。
- 不依賴測試期 reference answer 或 future cost。
- 在跨 dataset 測試仍有增量價值。

---

## 15. 最終判斷

### 這是不是需要處理的問題？

**是。** 文獻非常一致地指出固定 test-time compute 不經濟，而且全域 rationing、prefix pruning、risk-controlled stopping 與黑箱 serving 仍是活躍問題。

### 目前的廣義研究問題是不是缺口？

**不是。** Adaptive test-time compute allocation 已有大量工作，包含理論、系統、hidden-state、confidence、bandit 與 prefix-pruning 方法。

### 目前 Visible-Progress Allocation 是不是足夠新的方法？

**以主流方法論論文標準來看，目前還不夠。** 它的主要價值是極低 overhead、黑箱 API 相容與嚴謹 matched-cost evidence，但三狀態規則本身接近 surface heuristic。

### 研究還值得繼續嗎？

**值得，但必須升級問題定義。** 最有希望的方向不是再證明「流程狀態有用」，而是建立：

> 一個只使用黑箱可觀察 prefix、直接預測 continuation value、在事前全域 token ledger 下執行的 allocation method。

這樣現有成果會成為扎實的第一層方法與 baseline，而不是被推翻；同時新研究也有機會在擁擠文獻中形成清楚差異。

---

## 16. 建議優先閱讀的 12 篇

若時間有限，建議按以下順序閱讀：

1. [Reasoning on a Budget: Survey](https://arxiv.org/pdf/2507.02076)
2. [Scaling LLM Test-Time Compute Optimally](https://arxiv.org/abs/2408.03314)
3. [Strategic Scaling: Bandit Learning](https://proceedings.iclr.cc/paper_files/paper/2026/hash/d8d2c5f79c53a2a685dbdf93f78c5695-Abstract-Conference.html)
4. [AdaCompute](https://arxiv.org/abs/2604.14853)
5. [Predictive Scheduling](https://arxiv.org/abs/2602.01237)
6. [Cut Your Losses / STOP](https://arxiv.org/abs/2604.16029)
7. [Thought Calibration](https://aclanthology.org/2025.emnlp-main.722/)
8. [Answer Convergence](https://aclanthology.org/2025.emnlp-main.904/)
9. [Stop When Enough / REFRAIN](https://aclanthology.org/2026.acl-long.1256/)
10. [Adaptive Thinking / Sonata](https://machinelearning.apple.com/research/adaptive-thinking)
11. [Thinking Hard, Not Smart](https://arxiv.org/abs/2608.07968)
12. [Test-Time Scaling: Inference Regimes, Evaluation, and Reproducibility](https://arxiv.org/abs/2608.04001)
