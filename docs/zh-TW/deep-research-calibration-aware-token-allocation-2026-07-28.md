# Deep Research：LLM 自我評估校準 × Token Allocation × Process Mining

> **研究主題：** LLM 自我評估的校準品質，能否預測並優化 token 分配效率？  
> **研究脈絡：** 延續 Latent Confidence Alignment Error（LCAE）框架，加入
> Item Response Theory（IRT）難度訊號與 Process Mining 推理軌跡分析。  
> **線上查核截止日：** 2026-07-28  
> **文件用途：** 研究方向判斷、與指導教授討論、proposal／related work 草稿、
> 後續正式實驗設計依據。

---

## 摘要

本文件針對「LLM 自我評估校準能否改善推理 token 分配」進行研究地景查核，
涵蓋四條主要文獻線：

1. LLM verbalized confidence、自我評估與 confidence calibration；
2. test-time compute scaling、reasoning-length control 與 token allocation；
3. IRT／Rasch model／LCAE 在 LLM 自我評估中的應用；
4. Process Mining 對 LLM reasoning traces 的分析與干預。

查核結果顯示，這個研究方向具有高度實用價值，而且 2025–2026 年已快速升溫。
不過，「使用 confidence 動態控制 reasoning length」或「讓模型自己預估 token
budget」本身已不再是空白。Think Just Enough、SelfBudgeter、CAT、Sonata、
ROI-Reasoning、TRIAGE、Capability Calibration 等工作，已分別涵蓋
confidence-based stopping、self-predicted budgets、hidden-state routing、
metacognitive allocation，以及 calibrated confidence 對 best-of-\(k\) allocation
的效益。

另一方面，本次 targeted search 尚未找到一項工作完整驗證以下鏈條：

```text
IRT 題目難度／模型能力
        ↓
LCAE 自我評估校準
        ↓
逐題 reasoning-token requirement 預測
        ↓
單一 reasoning trajectory 的動態 token allocation
        ↓
Accuracy–token frontier 改善
        ↓
Process Mining 對效率機制與失敗模式的診斷
```

因此，本研究仍值得進行，但需要從寬泛的「confidence-based token allocation」
收斂為：

> **Psychometrically calibrated、training-free 的 reasoning-token allocation：
> 驗證校準品質本身是否能對逐題 token requirement 預測與 allocation efficiency
> 產生額外且具因果意義的價值。**

Process Mining 不宜再被定位為「首次分析 LLM reasoning traces」的主要創新，
而應作為 **allocation mechanism diagnosis**：解釋節省的 token 移除了哪些
冗餘活動、額外 budget 是否增加有效驗證，以及 under-allocation 如何破壞推理
流程。

---

## 1. 研究問題與原始主軸

### 1.1 核心研究動機

學姐的 LCAE 框架主要回答：

> LLM 是否知道自己會不會？其自我評估能否反映模型能力與題目難度所隱含的
> 客觀錯誤機率？

本研究希望進一步回答：

> 如果 LLM 確實知道自己會不會，它能否進一步判斷自己需要多少推理資源，
> 並將有限 token 分配得更有效率？

更精確地說，校準好的模型不一定使用更少的總 token，而應該：

- 在簡單題或高把握題上避免 overthinking；
- 在困難題或低把握題上保留足夠的 reasoning budget；
- 在相同準確率下減少平均 token 成本；
- 或在相同 token 預算下提高準確率；
- 避免因過度壓縮而移除必要的 verification、backtracking 或 correction。

### 1.2 建議的正式核心問題

> **Does psychometrically calibrated LLM self-assessment improve the prediction
> and allocation of query-level reasoning-token requirements?**

繁體中文表述：

> **以 IRT／LCAE 校準的 LLM 自我評估，能否更準確預測逐題推理 token
> 需求，並改善準確率與推論成本之間的權衡？**

### 1.3 需要避免的過寬表述

以下表述已不足以構成穩固的新穎性：

- 使用 confidence 減少 reasoning tokens；
- 讓模型自己預估 token budget；
- 依題目難度分配更多或更少 token；
- 把 Chain-of-Thought 當成 event log；
- 使用 Process Mining 區分不同模型的 reasoning style；
- 以某個 teacher／reference model 做 reasoning conformance checking。

這些元素多數已有直接或鄰近研究。真正可防守的價值在於：

1. 將 **calibration quality** 本身作為研究變數；
2. 使用 IRT 同時建模模型能力與題目難度；
3. 以 IDS intervention 改善校準，而非只觀察不同模型；
4. 驗證 calibration improvement 是否造成 allocation improvement；
5. 將配置對象明確限定為單一 reasoning trajectory 的 token length；
6. 用 PM 解釋配置干預造成的 observable reasoning behavior 變化。

---

## 2. 查核方法與範圍

### 2.1 搜尋來源

本次查核優先使用論文與官方出版頁面，包括：

- arXiv；
- ACL Anthology；
- OpenReview／ICLR；
- Springer／Process Science；
- Apple Machine Learning Research；
- Process Mining 研究團隊公開 preprint。

### 2.2 搜尋概念

搜尋組合涵蓋：

- LLM calibrated self-assessment；
- verbalized confidence；
- capability calibration；
- confidence-adaptive reasoning；
- token budget allocation；
- adaptive test-time compute；
- reasoning-length control；
- metacognitive resource allocation；
- Item Response Theory／Rasch model；
- LCAE；
- Process Mining × LLM reasoning traces；
- conformance checking × Chain-of-Thought；
- process-aware reward／GRPO。

### 2.3 證據限制

本文件屬於 **targeted deep research**，不是完整的 PRISMA systematic review。
因此：

- 可以用來辨識主要競爭者與研究地景；
- 可以支持「本次搜尋尚未找到完整交集」；
- 不宜直接支持「世界首次」或「完全沒有人做過」；
- 投稿前仍應進行正式的 backward／forward citation tracing；
- 2026 年相關研究更新速度極快，proposal 與投稿前皆需重新查核。

### 2.4 文獻狀態標記

本文區分：

- **Peer-reviewed／conference publication**：已出現在 ACL、EACL、ICLR、
  Springer 等正式會議或出版品；
- **Preprint**：arXiv／TechRxiv，尚未必經正式同儕審查；
- **Official research page**：研究機構官方發布，但仍需確認對應論文版本。

---

## 3. 最新研究地景總覽

### 3.1 直接競爭者與鄰近研究

| 工作 | 年份／狀態 | 核心方法 | 與本研究的重疊 | 尚未涵蓋的部分 |
|---|---|---|---|---|
| Token-Budget-Aware LLM Reasoning（TALE） | ACL Findings 2025 | 依問題複雜度預估 budget，透過 prompt 控制長度 | Difficulty-aware reasoning budget | 不研究 calibration、IRT、LCAE 或 PM |
| SelfBudgeter | ACL Findings 2026 | 預估 token budget + budget-guided GRPO | 模型自行預測所需 token | 需要訓練；不研究校準品質與 IRT |
| Think Just Enough | EACL Findings 2026 | 推理中詢問自評信心，高信心時提前停止 | Verbalized confidence 控制 reasoning length | 信心未精確校準；無 IRT／LCAE；無因果鏈 |
| CAT | ACL Industry 2026 | Self-certainty + preference optimization | Confidence-adaptive reasoning | 需 token distribution 與微調；非 black-box |
| Adaptive Thinking／Sonata | ICLR 2026／官方研究頁 | Hidden-state adapter 預測 self-consistency | 逐題 thinking budget allocation | 需 hidden states 與訓練；非 verbalized／IRT |
| Capability Calibration | arXiv 2026 | Capability-calibrated confidence 指導 best-of-\(k\) | 直接連結 calibration 與 allocation | 配置 sampling 次數，不是單一 trace 的 reasoning length |
| TRIAGE | arXiv 2026 | 有限總 budget 下預先選題、排序與配置 | Prospective metacognitive control | 評估框架，不是 LCAE allocation method |
| ROI-Reasoning | arXiv 2026 | Meta-cognitive fine-tuning + RL | 預估 reasoning cost 並全域配置 | 需要訓練；無 psychometric calibration |
| CLEAR | arXiv 2026 | Shadow price／marginal utility 全域配置 | Accuracy–cost Pareto optimization | 不研究模型自我評估校準 |
| Configuring LRMs using PM | TechRxiv preprint 2025 | 分類 reasoning type/effect 並調整 prompt | PM 分析 LRM reasoning traces | 不研究 token allocation 或 LCAE |
| PM4GRPO | arXiv preprint 2025 | PM conformance reward + GRPO | PM 分析／引導 reasoning process | 以 teacher alignment 訓練，不研究 allocation calibration |

### 3.2 整體趨勢

2025–2026 年的研究趨勢已由：

```text
增加 test-time compute 是否提高準確率？
```

轉為：

```text
哪一道題值得增加 compute？
應在什麼時候停止？
有限的全域 budget 應如何分配？
模型是否具備預測自身資源需求的 metacognitive control？
```

這代表本研究的問題具有高度時效性與實用性，但也代表投稿門檻上升：

- 不能只和 fixed budget 比較；
- 不能只報平均 token reduction；
- 不能把 raw confidence 直接等同 calibrated confidence；
- 必須納入強力的 difficulty、hidden-state、self-consistency 或 oracle baseline；
- 必須明確區分 sampling budget 與 reasoning-length budget。

---

## 4. Confidence-Based Reasoning Control

### 4.1 Think Just Enough

**論文：** Junyeob Kim, Sang-goo Lee, Taeuk Kim.  
**出版：** Findings of EACL 2026。  
**連結：** [ACL Anthology](https://aclanthology.org/2026.findings-eacl.263/)

#### 核心方法

Think Just Enough 在模型推理過程中，於 `Wait`、`Alternatively` 或
`</think>` 等反思點暫停生成，要求模型輸出十級 verbalized confidence。
當信心達到 `Almost certain` 門檻時，系統結束 reasoning 並生成答案；若未達
門檻，則以 `Wait` 提示模型繼續推理。

研究涵蓋：

- MATH-500；
- AIME 2024；
- AIME 2025；
- AMC 2023；
- GPQA Diamond；
- QwQ-32B、Qwen3-32B、R1-Distill-Qwen-32B。

論文顯示，自評信心可使多個模型減少 reasoning tokens，且平均準確率大致不受
損害。

#### 與本研究最重要的關係

它已直接證明：

> Verbalized self-assessment 可以在 inference time 作為 reasoning stopping
> signal。

因此，本研究不能再把「使用自評信心停止推理」當成主要創新。

#### 它留下的研究缺口

1. 自評信心大量集中於高信心區間；
2. 作者比較 verbalized confidence 與 log-prob proxy，只得到約
   \(r=0.33\) 的關聯；
3. 作者明確指出該關聯不應被解讀為精確 calibration；
4. 觸發機制依賴模型特定 reflective markers；
5. periodic confidence probing 會產生顯著額外成本；
6. 對 instruction-tuned model 的泛化較弱；
7. 沒有 IRT-based difficulty；
8. 沒有測量 LCAE；
9. 沒有比較 raw confidence 與 calibrated confidence 的 allocation 效果；
10. 沒有建立 calibration improvement → token efficiency improvement 的
    因果鏈；
11. 沒有分析被停止後移除的是冗餘 reasoning，還是必要 verification。

#### 對本研究的直接啟示

Think Just Enough 應成為正式實驗的必要 baseline：

```text
Raw confidence stopping
vs.
IRT/LCAE-calibrated confidence allocation
```

本研究要證明的不是 confidence 有沒有用，而是：

> **經 psychometric calibration 後，confidence 是否能更安全、更穩定地控制
> reasoning length？**

### 4.2 CAT：Confidence-Adaptive Thinking

**論文：** Qizhi Jiang et al.  
**出版：** ACL 2026 Industry Track。  
**連結：** [ACL Anthology](https://aclanthology.org/2026.acl-industry.152/)

#### 核心方法

CAT 使用完整 token distribution 計算 trajectory-level self-certainty，再依：

- trajectory correctness；
- reasoning length；
- self-certainty；

建立 conciseness／deliberation preference pairs，並以
Confidence-Weighted Preference Optimization（CWPO）微調模型。

#### 與本研究的關係

CAT 已涵蓋「高信心時壓縮、低信心時保留推理」的核心直覺，但：

- 需要存取 token distribution；
- 需要預先產生多條 reasoning trajectories；
- 需要 preference optimization；
- 不適用多數 closed-source API models；
- 它的 `calibration ratio` 是 self-certainty／length 的最佳化量，不等同於
  IRT／LCAE 所定義的 confidence calibration；
- 沒有分離 model ability 與 item difficulty。

#### 本研究相對優勢

本研究可定位為：

> **Training-free、black-box-compatible、psychometrically grounded**
> confidence-aware inference control。

### 4.3 Confidence-Aware Reasoning 與 Entropy-Based Early Stopping

其他鄰近研究也使用：

- token-level entropy；
- log-probability；
- provisional answer confidence；
- semantic coherence；
- sequence-level self-consistency；

進行 early stopping 或 adaptive inference。這類研究支持 uncertainty signal
對 inference efficiency 的價值，但也代表 verbalized confidence 必須與更便宜、
更穩定的 internal signal baseline 比較。

對 closed-source model 而言，verbalized confidence 的可存取性仍是優勢；但其
額外 prompt token、confidence generation token 與 latency 必須全部列入成本。

---

## 5. Self-Predicted Token Budgets

### 5.1 SelfBudgeter

**論文：** Zheng Li et al.  
**出版：** Findings of ACL 2026。  
**連結：** [ACL PDF](https://aclanthology.org/2026.findings-acl.1063.pdf)

#### 核心方法

SelfBudgeter 分為兩階段：

1. Cold-start：學習在 `<budget>` 標記中輸出預估 token budget；
2. RL：以 budget penalty 與 precise budget control reward，同時鼓勵：
   - 輸出正確；
   - budget 較小；
   - 實際長度符合模型預測的 budget。

論文報告平均 response length compression 約 61%，同時維持準確率。

#### 對本研究構成的挑戰

SelfBudgeter 已經做出：

> 「模型先預測所需 token，再依該 budget 生成答案。」

因此，如果本研究只讓模型先回答「我需要 512 tokens」，新穎性不足。

#### 可防守差異

本研究應強調：

| SelfBudgeter | 本研究 |
|---|---|
| 需要 SFT／RL | Training-free inference-time method |
| 預測 budget 本身 | 研究校準品質是否使預測可信 |
| 依訓練 reward 學習 length | 由受控 budget sweep 建立 requirement ground truth |
| 主要為 open-weight model | 可應用 closed-source API model |
| 無 IRT ability/difficulty decomposition | 使用 Rasch／IRT latent reference |
| 無 PM mechanism diagnosis | 分析配置干預後的 reasoning behavior |

### 5.2 Token-Budget-Aware LLM Reasoning（TALE）

**出版：** Findings of ACL 2025。  
**連結：** [ACL Anthology](https://aclanthology.org/2025.findings-acl.1274/)

TALE 已證明，透過 prompt 提供合理 token budget 可以壓縮 CoT，而 budget
選擇會影響壓縮與準確率。其方法依問題 reasoning complexity 動態估計 budget。

因此，本研究不能只把「difficulty-aware budget」當成創新，而應測試：

> IRT-based difficulty 是否比一般 complexity estimator 更有理論與實證價值？

### 5.3 ROI-Reasoning

**論文：** Rational Optimization for Inference via Pre-Computation
Meta-Cognition。  
**狀態：** arXiv preprint，2026。  
**連結：** [arXiv](https://arxiv.org/abs/2601.03822)

ROI-Reasoning：

1. 先以 Meta-Cognitive Fine-Tuning 教模型預測 reasoning cost 與 expected utility；
2. 再用 RL 學習在有限全域 token 預算下做 solve／skip 與資源配置。

它證明 pre-computation metacognition 是可被訓練的 allocation signal。

本研究的差異仍在：

- 不訓練模型；
- 不只研究 cost prediction；
- 研究自評信號是否 calibrated；
- 使用外部 IRT reference；
- 驗證 IDS 是否改善 allocation。

---

## 6. Calibration 與 Allocation 的直接交集

### 6.1 On Calibration of Large Language Models: From Response to Capability

**作者：** Sin-Han Yang et al.  
**狀態：** arXiv preprint，2026。  
**連結：** [arXiv](https://arxiv.org/abs/2602.13540)

#### 核心概念

該研究區分：

- **Response calibration**：估計目前這一個 sampled response 是否正確；
- **Capability calibration**：估計模型對該 query 的整體成功機率。

在 stochastic decoding 下，一次答對或答錯不一定能代表模型對該 query 的
真實 capability。研究使用多次 sampling 建立 query-level expected accuracy，
並比較 verbalized confidence、response consistency 與 hidden-state probes。

#### Allocation 實驗

該研究將 capability-calibrated confidence 用於 best-of-\(k\) allocation：

- 總 sampling budget 固定；
- 每道題分配不同數量的 samples；
- 根據預估成功機率的 marginal gain，將額外 sample 分配給預期回報較高的題目。

研究結果顯示：

- 更好的 capability calibration 可以改善 allocation；
- verbalized confidence 與 trained probe 都可優於 uniform allocation；
- confidence estimator 的 Brier score 越低，allocation 通常越好。

#### 為何這篇是最重要的概念競爭者

它已非常接近證明：

```text
Calibration quality → Allocation quality
```

因此，本研究不能把這個抽象命題當成完全沒有人做過。

#### 仍存在的重要差異

該研究的 allocation unit 是：

```text
每題抽樣幾次（best-of-k）
```

本研究的 allocation unit 是：

```text
單一 reasoning trajectory 可使用多少 reasoning tokens
```

兩者不可混為一談：

- sampling budget 增加的是獨立候選答案數；
- reasoning-length budget 增加的是單一推理過程的深度或長度；
- 前者的理論可用 \(1-(1-p_i)^{k_i}\) 表示；
- 後者的 success curve 未必單調，也可能因 overthinking 而下降。

該研究也沒有：

- IRT／Rasch model；
- LCAE；
- IDS intervention；
- minimum effective reasoning budget；
- Process Mining；
- reasoning path mechanism analysis。

#### 本研究必須如何回應

1. 在 related work 中明確引用 capability calibration；
2. 清楚聲明研究對象是 **reasoning-length allocation**；
3. 將 capability-calibrated confidence／Brier-calibrated confidence 納入 baseline；
4. 不只證明 correlation，而要做 IDS intervention；
5. 比較 LCAE 是否比一般 Brier／ECE 更能預測 allocation utility。

### 6.2 Adaptive Thinking／Sonata

**出版：** ICLR 2026；Apple Machine Learning Research 官方頁。  
**連結：** [Apple ML Research](https://machinelearning.apple.com/research/adaptive-thinking)

Sonata 使用 query prefill 階段的最後一層 hidden representation，訓練 adapter
直接預測 self-consistency，並根據預測結果配置 thinking budget。官方摘要報告
在維持相同準確率下，可減少約 20–80% thinking tokens。

這證明：

- Query-level budget allocation 是可行且重要的；
- Self-consistency 是強力的 token requirement proxy；
- Hidden-state probes 是本研究不可忽略的強基線。

本研究相對優勢：

- 不需 hidden states；
- 可作用於 closed API model；
- self-assessment 對人類可解釋；
- IRT 能將難度相對於模型能力定義；
- 可研究跨模型 calibration quality。

本研究相對劣勢：

- Verbalized assessment 可能比 hidden-state probe 昂貴；
- IRT 需要先建立 item bank 與模型 response matrix；
- 若 verbalized confidence 效果不如 hidden-state probe，實際部署價值會降低。

---

## 7. Metacognitive Resource Allocation

### 7.1 TRIAGE

**論文：** Evaluating Prospective Metacognitive Control in LLMs under
Resource Constraints。  
**狀態：** arXiv preprint，2026。  
**連結：** [arXiv](https://arxiv.org/abs/2605.13414)

TRIAGE 給模型一組待解題目與有限 token budget，要求模型在執行前一次決定：

- 哪些題目要做；
- 題目順序；
- 每題分配多少 token；
- 哪些題目應放棄。

模型配置結果與具有完整 solvability／cost 資訊的 oracle 比較，形成 triage
efficiency ratio。

#### 對本研究的價值

TRIAGE 顯示：

- Prospective metacognitive control 是獨立且重要的 LLM 能力；
- 現有模型在有限資源下仍無法有效預測自身 solvability 與 cost；
- 單純具備高準確率不代表能合理配置 compute。

這與 LCAE 的核心發現高度一致：

> 能力強不等於自評準；自評準也不等於已能把資源配置好。

#### 可整合方式

TRIAGE 的 oracle／regret 概念可以引入本研究：

- Oracle requirement：由 budget sweep 建立；
- Allocation regret：實際 policy 與 oracle 的成本／效益差距；
- Rational abandonment：在極低全域預算下，部分題目可能不值得追加 token；
- Global allocation：除了 per-query budget，亦可研究整批題目的總預算配置。

### 7.2 CLEAR

**論文：** The Shadow Price of Reasoning。  
**狀態：** arXiv preprint，2026。  
**連結：** [arXiv](https://arxiv.org/abs/2606.03092)

CLEAR 將全域 inference budget 視為受限制的經濟資源，以 marginal utility 與
shadow price 決定：

- 哪些 query 值得追加資源；
- 哪些 query 應放棄；
- 如何改善總 token cost 與平均準確率的 Pareto frontier。

#### 對本研究的啟示

最終 allocator 不應只做固定閾值分類。正式版可考慮：

\[
\max_{\{b_i\}}\sum_i U_i(b_i)
\quad \text{s.t.}\quad \sum_i b_i \le B
\]

其中：

- \(b_i\)：分配給第 \(i\) 題的 reasoning budget；
- \(U_i(b_i)\)：該題在 budget \(b_i\) 下的預期 utility；
- LCAE／IRT-calibrated self-assessment 用來估計 \(U_i\) 或 minimum required
  budget。

但第一篇研究不必直接追求複雜經濟最佳化。優先證明校準訊號有增量預測價值，
再發展 global allocator。

---

## 8. IRT／LCAE 研究線

### 8.1 Latent Confidence Alignment for LLM Self-Assessment

**作者：** Ting-Yu Chen et al.  
**會議：** IEEE IRI 2026。  
**連結：** [arXiv](https://arxiv.org/abs/2606.21937)

#### 問題設定

傳統 calibration metrics 通常比較：

\[
\text{Predicted confidence} \quad \text{vs.} \quad \text{Observed correctness}
\]

但單一 observed correctness 是離散且高噪音的結果，也沒有顯式控制：

- 模型能力；
- 題目難度；
- 模型與題目的相對位置。

LCAE 使用 Rasch model：

\[
P(X_{mi}=1\mid \theta_m,\beta_i)
=
\sigma(\theta_m-\beta_i)
\]

其中：

- \(\theta_m\)：模型 \(m\) 的 latent ability；
- \(\beta_i\)：題目 \(i\) 的 latent difficulty；
- \(\sigma\)：logistic function。

由此得到模型在每題的 latent expected error probability，並與模型自評錯誤機率
比較，形成 Latent Confidence Alignment Error。

#### 核心貢獻

- 將能力與自評品質拆開；
- 將題目難度顯式納入 calibration；
- 使用 IDS 提供外部 difficulty information；
- 研究顯示 IDS 可改善 self-assessment alignment；
- 改善 self-assessment 不必改變模型原始答題能力；
- 報告 reliability 與 inference cost 的關聯，但未做 token allocation。

### 8.2 為何 LCAE 是本研究的主要差異化

現有 adaptive reasoning 方法常使用：

- raw verbalized confidence；
- token entropy；
- self-consistency；
- hidden-state probe；
- embedding-based difficulty；
- external reward／verifier。

這些訊號通常不回答：

> 模型的 confidence 是否相對於其能力與該題難度而正確？

LCAE／IRT 可提供以下分解：

```text
模型能力高？
題目本身簡單？
模型只是普遍過度自信？
還是模型真的知道這題對自己而言容易／困難？
```

這使本研究能檢驗：

1. LCAE 較低的模型是否更準確預測 token requirement；
2. 在同一模型上，IDS 是否先改善 LCAE，再改善 allocation；
3. LCAE 是否比 Brier、ECE、raw confidence 更能預測 allocation regret；
4. IRT-only 與 model self-assessment 是否具有互補資訊；
5. 高能力但低 LCAE 的模型，是否會出現系統性 under-allocation；
6. 低能力但高 LCAE 的模型，是否能透過合理放棄或擴充 budget 提高資源效益。

### 8.3 LCAE 路線的風險

1. Rasch model 的 unidimensionality 可能不適合混合數學、科學、程式等多領域；
2. 只有少量模型時，IRT item parameter 可能不穩；
3. 模型版本更新會改變 \(\theta_m\) 與 response matrix；
4. Public benchmark contamination 可能扭曲 item difficulty；
5. LCAE 可能只反映 confidence calibration，未必額外預測 reasoning length；
6. IDS 可能直接提供 difficulty，而非透過 calibration 間接改善 allocation；
7. IRT-only policy 可能已和 LCAE-aware policy 一樣好。

因此需加入：

- Rasch vs 2PL sensitivity analysis；
- domain-specific IRT 或 multidimensional IRT 的穩健性檢查；
- bootstrap parameter uncertainty；
- held-out item validation；
- IRT-only baseline；
- mediation／causal pathway 分析。

---

## 9. Process Mining × LLM Reasoning

### 9.1 Configuring Large Reasoning Models using Process Mining

**作者：** Alessandro Berti, Humam Kourani, Gyunam Park, Wil van der Aalst。  
**狀態：** TechRxiv preprint，2025。  
**連結：** [Preprint PDF](https://d197for5662m48.cloudfront.net/documents/publicationstatus/260570/preprint_pdf/8710e5c6f0a1c02cd7f1ac69a2104256.pdf)

該工作已經：

- 取得 LRM textual reasoning traces；
- 將 reasoning 分割成 steps；
- 使用 LLM-as-a-Judge 標註 reasoning type；
- 分類 deduction、induction、abduction、validation、backtracking、
  hypothesis generation 等活動；
- 標註每步對答案的 effect：positive、indifferent、negative；
- 比較不同模型的 reasoning profile；
- 透過 system prompt 調整某些 reasoning type frequency。

因此，不宜再宣稱：

> 首次使用 Process Mining 分析 LLM reasoning traces。

### 9.2 PM4GRPO

**論文：** Reasoning-Aware GRPO using Process Mining。  
**狀態：** arXiv preprint，2025。  
**連結：** [arXiv](https://arxiv.org/abs/2510.25065)

PM4GRPO：

- 將 policy model reasoning trace 轉換成 process model；
- 使用 Inductive Miner／conformance checking；
- 比較 policy 與 teacher reasoning；
- 將 process conformance 納入 GRPO reward；
- 在多個數學推理 benchmark 上改善 post-training performance。

因此，以下也不是安全的新穎性主張：

- 使用 teacher reasoning 作為 reference；
- 使用 conformance score 評估 reasoning；
- 將 PM-derived signal 用於 reasoning optimization。

### 9.3 PM 在本研究中的最佳定位

建議將 PM 定位為：

> **Allocation mechanism diagnosis，而不是主要 allocator 或主要 novelty。**

PM 應回答：

1. 校準式 allocation 節省的是哪些 activity？
2. Easy item 被壓縮後，是否主要減少重複 reason／calculate？
3. Hard item 獲得更多 budget 後，是否增加有效 verify／reconsider？
4. Under-allocation 的錯誤是否伴隨缺少關鍵 reasoning transition？
5. Raw-confidence policy 是否會因 overconfidence 過早切斷 verification？
6. IDS-calibrated policy 是否能在相同 token 下保留更完整的成功路徑？
7. Allocation improvement 是否只來自輸出格式變短，而非推理結構改善？

### 9.4 不建議以單一 Petri Net 作為「理想推理」

現有 V2 已顯示：

- 每模型可有 80–100 個 trace variants；
- Inductive Miner 容易產生近似 flower model；
- fitness 可能接近 1 而沒有區分力；
- reference model 選擇會改變 conformance 解讀；
- 長 trace 自然產生更多 model moves／deviations。

因此正式研究應優先使用：

- activity-frequency distribution；
- transition／bigram distribution；
- Jensen–Shannon divergence；
- trace entropy；
- loop／reconsider／verify rate；
- within-item paired trace comparison；
- correctness-conditioned comparison；
- budget-conditioned process drift；
- event-level survival／transition analysis。

Conformance checking 可保留為輔助分析，但不宜單獨定義 path quality。

### 9.5 CoT Faithfulness 限制

公開文字 reasoning 不一定忠實反映模型內部 latent computation。因此論文應使用：

- observable reasoning trace；
- generated reasoning behavior；
- surface reasoning structure；

而避免直接宣稱：

- 真實內部思考；
- 模型認知流程；
- 完整還原 reasoning mechanism。

PM 的價值是分析可觀察的生成行為，而非證明 textual CoT 必然忠實。

---

## 10. 研究缺口矩陣

| 研究問題 | 現有研究覆蓋程度 | 本研究可貢獻的部分 |
|---|---|---|
| Confidence 能否控制 reasoning length？ | 已有直接證據 | 比較 raw 與 calibrated confidence |
| 模型能否預測所需 token？ | SelfBudgeter 已做 | Training-free、black-box、IRT-grounded |
| Difficulty 能否指導 token budget？ | 已有多篇 | 使用相對於模型能力的 IRT difficulty |
| Calibration 能否改善 allocation？ | Capability Calibration 已在 best-of-\(k\) 初步證明 | 單一 trajectory reasoning-length allocation |
| IDS 是否有 downstream allocation value？ | 尚未找到直接實證 | 隨機 intervention，建立因果鏈 |
| LCAE 是否預測 token requirement？ | 尚未找到 | 直接測量最低有效 budget |
| LCAE 是否優於 Brier／ECE？ | 尚未用 allocation outcome 比較 | 以 allocation regret／frontier 驗證 |
| PM 能否分析 LLM reasoning？ | 已有人做 | 研究 allocation intervention 的行為機制 |
| PM 能否改善 LLM reasoning？ | PM4GRPO 已做 | 不以 teacher alignment 為主，改做 allocation diagnosis |
| 校準、allocation、PM 是否被完整串接？ | 本次搜尋未找到 | 本研究的整合性貢獻 |

---

## 11. 建議的論文定位

### 11.1 不建議的定位

> We are the first to use confidence to allocate reasoning tokens.

原因：Think Just Enough、CAT、SelfBudgeter、Sonata 等已直接涵蓋。

> We are the first to apply process mining to LLM reasoning traces.

原因：Berti et al. 與 PM4GRPO 已涵蓋。

> Better calibrated models use fewer tokens.

原因：

- 總 token 少不等於配置合理；
- 高能力模型可能自然用較少 token；
- 模型預設 verbosity 是混淆因素；
- 跨模型四個點不足以支持穩健關聯；
- correlation 不是 causality。

### 11.2 建議定位

> Existing studies show that confidence can guide adaptive reasoning, but they
> generally assume that confidence is a reliable proxy for query difficulty or
> reasoning sufficiency. We instead ask whether the *quality of calibration
> itself* determines allocation effectiveness. Extending LCAE, we use IRT-based
> latent difficulty and ability to calibrate self-assessment, test its causal
> impact on reasoning-token allocation, and analyze the resulting observable
> reasoning changes through process mining.

繁體中文版：

> 現有研究顯示 confidence 可用於 adaptive reasoning，但通常直接假設
> confidence 足以反映題目難度或推理充分性。本研究改問：真正決定配置效果的，
> 是否是 confidence 的校準品質？我們延伸 LCAE，利用 IRT 能力／難度建立
> latent reference，以受控實驗驗證 calibration 對 reasoning-token allocation
> 的因果效益，並透過 Process Mining 分析配置干預造成的可觀察推理行為變化。

### 11.3 建議題目

#### 偏實證與穩健

**Does Calibrated Self-Assessment Improve Token Allocation in LLM Reasoning?**

#### 強調 IRT／LCAE

**From Knowing to Budgeting: IRT-Calibrated Self-Assessment for Efficient LLM
Reasoning**

#### 強調完整方法

**Calibration-Aware Token Allocation for LLM Reasoning with Process-Level
Diagnostics**

#### 強調 training-free

**Training-Free Reasoning Budget Allocation through Psychometrically Calibrated
LLM Self-Assessment**

---

## 12. 建議研究問題與假設

### RQ1：Token Requirement Prediction

> 經 IRT／LCAE 校準的 LLM 自我評估，能否預測逐題最低有效 reasoning budget？

#### H1

較低 LCAE 應對應：

- 較低 token-requirement MAE；
- 較高 predicted vs observed requirement correlation；
- 較低 under-allocation rate；
- 較低 allocation regret。

### RQ2：Allocation Utility

> 使用 calibrated self-assessment 進行動態 token allocation，能否改善
> accuracy–token frontier？

#### H2

在 held-out items 上，LCAE-aware allocator 應：

- 在相同準確率下使用較少總 token；
- 或在相同總 token 下取得較高準確率；
- 優於 fixed、random、IRT-only 與 raw-confidence policy。

### RQ3：Causal Effect of Calibration Improvement

> 提供 IRT-based difficulty signal（IDS）是否能透過改善 self-assessment
> calibration，因果性地改善 token allocation？

#### H3

相較 QOQ：

```text
IDS
→ LCAE 改善
→ Requirement prediction error 降低
→ Allocation regret 降低
→ Accuracy–token frontier 改善
```

### RQ4：Signal Comparison

> Verbalized confidence、log-prob、self-consistency、IRT-only 與融合訊號中，
> 哪一種最適合 reasoning-length allocation？

### RQ5：Process-Level Mechanism

> Calibration-aware allocation 如何改變 observable reasoning traces？

#### H5

有效 allocator 應：

- 在 easy/correct cases 減少 indifferent／repetitive reasoning；
- 在 hard cases 保留必要 verification／backtracking；
- 降低無效 loop；
- 不會只因 truncation 機械性地降低步數；
- 在 matched accuracy 下呈現較低 process redundancy。

---

## 13. 正式實驗設計

### 13.1 先定義 Token Requirement

目前 V2 測得的是 unconstrained token usage：

> 模型自然用了多少 token。

這不等於：

> 模型維持正確答案實際需要多少 token。

同一題即使自然生成 900 tokens，可能 256 tokens 就足以答對；反之，某次只用
300 tokens 答對，也可能只是 stochastic lucky sample。

因此需對每個 `model × item` 做 budget sweep，例如：

```text
128, 256, 512, 1024, 2048 reasoning tokens
```

每個 budget 執行多個 seeds／replicates。

### 13.2 Minimum Effective Budget

簡化 MVP 定義：

> 三次生成中至少兩次答對的最小 budget。

較正式的定義：

\[
T^*_{mi}
=
\min \left\{
b:
\widehat{P}(Y_{mi}=1\mid b)\ge \tau
\right\}
\]

其中：

- \(m\)：模型；
- \(i\)：題目；
- \(b\)：reasoning token budget；
- \(\tau\)：可靠成功門檻，例如 0.67 或 0.80。

由於 accuracy 對 budget 未必單調，可使用：

- isotonic regression；
- monotonic smoothing；
- Bayesian success curve；
- bootstrap uncertainty interval。

### 13.3 預先自我評估

在正式 reasoning 前，以短格式收集：

- predicted correctness probability；
- perceived difficulty；
- predicted required token budget；
- 可選擇的 fast／slow reasoning mode。

必須：

- 限制 assessment 輸出長度；
- 記錄 assessment prompt/output tokens；
- 將 assessment overhead 計入總成本；
- 避免自評 call 先進行大量隱性 reasoning；
- 固定格式，例如 JSON；
- 區分 prospective confidence 與 post-answer confidence。

### 13.4 實驗條件

建議至少包含：

| 條件 | 提供資訊 |
|---|---|
| QOQ | 僅題目，不提供 IRT 訊號 |
| IDS | 提供 IRT item difficulty |
| DPR | 允許 fast／slow mode routing |
| Combined | IDS + DPR |

第一階段可只做 QOQ vs IDS，以降低實驗規模並保留最清楚的 intervention。

### 13.5 Allocation Policies

正式比較：

| Policy | 說明 |
|---|---|
| Fixed | 每題相同 budget |
| Random | 使用相同 budget distribution，但隨機分配 |
| Length prior | 依題目或模型歷史平均長度 |
| IRT-only | 只根據 \(\theta_m-\beta_i\) 分配 |
| Raw confidence | 未校準 verbalized confidence |
| Brier/ECE calibrated | 一般 calibration baseline |
| LCAE-aware | 本研究主要方法 |
| Self-consistency | 多次 sample／proxy baseline |
| Hidden-state probe | 只對可存取 open model |
| Oracle | 直接使用 \(T^*_{mi}\) 或 empirical success curve |

### 13.6 簡單透明的 Allocator

第一版不必使用複雜 neural allocator。可先採：

```text
預測容易／高成功率 → 128 或 256
中等 → 512
預測困難／低成功率 → 1024 或 2048
```

threshold 只能在 development set 決定，不能在 test set 調整。

後續才考慮：

- ordinal regression；
- constrained optimization；
- marginal utility；
- global budget allocation；
- solve／skip／abstain policy。

### 13.7 主要 Outcome

#### Requirement Prediction

- MAE／RMSE of predicted \(T^*\)；
- Spearman／Kendall correlation；
- ordinal budget accuracy；
- under-allocation rate；
- over-allocation amount。

#### Allocation Performance

- Accuracy at matched token cost；
- Token cost at matched accuracy；
- Accuracy–token frontier；
- Frontier AUC；
- regret relative to oracle；
- excess allocation；
- assessment overhead；
- wall-clock latency；
- API monetary cost。

#### Calibration

- LCAE；
- Brier score；
- ECE／adaptive ECE；
- AUROC／AUPRC for failure prediction；
- calibration slope/intercept；
- confidence resolution／sharpness。

#### Process Mining

- trace length；
- activity distribution；
- transition／bigram distribution；
- JSD；
- trace entropy；
- loop count；
- verify／reconsider rate；
- process drift across budgets；
- correctness-conditioned differences。

---

## 14. 統計與因果分析

### 14.1 分析單位

不能只用「四個模型」做 correlation。主要觀測單位應是：

```text
model × item × condition × budget × replicate
```

### 14.2 建議模型

- Mixed-effects logistic regression for correctness；
- Mixed-effects ordinal／linear model for budget requirement；
- Model and item random effects；
- Fixed effects for condition、difficulty、ability、signal；
- Interaction：condition × difficulty；
- Bootstrap by item；
- Cluster-robust standard errors；
- Held-out item／domain evaluation。

### 14.3 Causal Path

若要主張 IDS 透過 calibration 改善 allocation，可測：

1. First stage：IDS 是否改善 LCAE；
2. Second stage：LCAE improvement 是否預測 requirement error 降低；
3. Outcome：allocation frontier 是否改善；
4. Mediation：IDS 的 allocation effect 有多少可由 LCAE improvement 解釋。

仍需避免過度因果主張：

- IDS 也可能直接提供 difficulty，繞過 self-assessment；
- 可比較 IDS-only deterministic policy 與 IDS-informed self-assessment；
- 若兩者效果相同，就不能聲稱 self-assessment calibration 是必要中介。

### 14.4 Preregistration

建議預先固定：

- primary outcome；
- budget grid；
- success threshold；
- dataset split；
- allocator threshold learning procedure；
- exclusion criteria；
- answer parsing；
- missing/error handling；
- statistical model；
- go/no-go criteria。

---

## 15. 分階段研究路線

### Phase 0：整理 V2

1. 修正 ARC 原始數字 label 與 prompt A–D label 不一致；
2. 將 V2 報告明確標記為 PM feasibility pilot；
3. 移除或封存已被最新重跑推翻的舊結論；
4. 說明 V2 不測 token requirement／allocation；
5. 保留 trace extraction 與 PM pipeline；
6. 完成人工 activity-label reliability。

### Phase 1：Budget-Control Feasibility

先確認 API／model backend 能：

- 真正限制 reasoning/output tokens；
- 一致回報 token accounting；
- 區分 prompt、reasoning、answer、assessment tokens；
- 對 truncated answer 做正確判定；
- 固定 temperature／seed 或記錄不可控 stochasticity。

如果供應商的 `max_tokens` 只截斷 final answer，卻不能控制 reasoning tokens，
則需更換可控 backend 或 open-weight reasoning model。

### Phase 2：Budget Sensitivity Pilot

建議規模：

```text
3 models × 30 items × 5 budgets × 2 replicates
= 900 generations
```

通過條件：

- 題目不能在最低 budget 即接近全對；
- 至少一部分 item 會隨 budget 改變成功率；
- \(T^*\) 不能集中在單一 budget；
- answer parsing error 接近零；
- budget instruction 或 hard cap 確實生效。

### Phase 3：Requirement Ground Truth

建議規模：

```text
3–4 models × 150–300 items × 5 budgets × 3 replicates
```

資料依：

- IRT difficulty；
- domain；
- baseline solvability；

分層抽樣，並切成 calibration／development／locked test。

### Phase 4：Signal Evaluation

先回答：

- Raw confidence 能否預測 \(T^*\)？
- LCAE 是否比 Brier／ECE 更有增量價值？
- IRT-only 是否已足夠？
- Self-assessment overhead 是否合理？

只有 signal 在 held-out data 上有效，才進入 allocator evaluation。

### Phase 5：Allocation Evaluation

比較所有 policy 的 accuracy–token frontier，並以：

- matched accuracy；
- matched cost；
- oracle regret；

作為主要結論。

### Phase 6：PM Mechanism Analysis

只在確認 allocator 產生實際效益後，分析：

- fixed vs adaptive；
- raw vs calibrated；
- over- vs appropriate vs under-allocation；
- within-item／within-model paired traces。

PM 若無穩健效果，降為 exploratory appendix，不應反過來成為主結論。

---

## 16. Go／No-Go 標準

### Gate 0：Budget 可控性

**Go：**

- API hard cap 確實控制 reasoning；
- token accounting 可重現。

**No-Go／改 backend：**

- 只能事後截斷文字；
- reasoning tokens 不可觀察也不可限制；
- 模型忽略 budget prompt。

### Gate 1：Requirement 可識別性

**Go：**

- 有足夠 budget-sensitive items；
- \(T^*\) 有跨題變異；
- 成功曲線可估計。

**No-Go／換題：**

- 所有模型在最小 budget 已接近飽和；
- 所有題目都需要最大 budget；
- 公開 benchmark contamination 導致無難度區分。

### Gate 2：Signal 有增量價值

**Go：**

- LCAE-aware signal 在 held-out items 優於 model identity、IRT-only 或 raw
  confidence；
- requirement prediction error 有實質下降。

**No-Go／改題目：**

- LCAE 只重述 item difficulty；
- IRT-only 已達同等效果；
- confidence overhead 大於節省量。

### Gate 3：Allocator 有實際效益

**Go：**

- 在 matched accuracy 下穩定節省 token；
- 或 matched token 下提高 accuracy；
- bootstrap CI 排除零效果；
- 跨模型／領域至少部分泛化。

**No-Go／負結果：**

- allocation 無法勝過 fixed／random；
- 改善僅來自少數模型；
- under-allocation failure 抵消節省；
- assessment cost 使總成本更高。

### Gate 4：PM 有解釋力

**Go：**

- PM 指標在人工標註與不同 segmentation 下可重現；
- paired trace analysis 顯示有意義的活動保留／移除。

**降級為 exploratory：**

- 差異只由 trace length 機械性造成；
- activity labeling reliability 不足；
- conformance 結果對 reference／miner 高度敏感。

---

## 17. 本專案的可防守優勢

### 17.1 自然且可信的研究延伸

本研究不是把 IRT 臨時加入 token allocation，而是延續 LCAE：

```text
LCAE：模型知道自己會不會嗎？
  ↓
本研究：知道自己會不會，能否知道自己需要思考多久？
```

### 17.2 Ability、Difficulty 與 Calibration 可分離

IRT 使研究可以區分：

- 能力高；
- 題目簡單；
- 模型普遍過度自信；
- 模型真的知道這一題對自己困難；
- 模型是否能把這個 knowledge 轉化為資源決策。

### 17.3 具備 Calibration Intervention

QOQ vs IDS 可在同一模型、同一題目上進行 intervention，比跨模型 correlation
更接近因果驗證。

### 17.4 Training-Free 與 Black-Box Compatibility

相較 SelfBudgeter、CAT、Sonata、ROI-Reasoning：

- 不需要微調；
- 不需要 hidden states；
- 不需要完整 logits；
- 可使用 verbalized confidence；
- 可套用 API-only models。

### 17.5 已有可重跑 PM Pipeline

本專案已具備：

- API response collection；
- confidence collection；
- trace segmentation；
- activity labeling；
- process discovery；
- conformance；
- entropy／JSD／transition analysis；
- result artifact validation。

更重要的是，V2 已暴露：

- Prompt sensitivity；
- label mismatch；
- confidence wrong-sample scarcity；
- Petri net flower-model problem；
- reference model ambiguity；
- rule-based labeling reliability；
- unconstrained usage 不等於 requirement。

這些方法學經驗可以使 V3 避免重複犯錯。

### 17.6 不只回答「省多少」，也回答「為什麼」

如果實驗成功，本研究可同時提供：

1. Predictive evidence：校準是否預測 requirement；
2. Interventional evidence：IDS 是否改善 allocation；
3. Utility evidence：accuracy–token frontier 是否改善；
4. Mechanistic evidence：哪些 reasoning behaviors 被保留或移除。

這會比只報 token compression 更完整。

---

## 18. 主要風險與緩解

| 風險 | 影響 | 緩解方式 |
|---|---|---|
| Confidence allocation 已有大量研究 | 新穎性下降 | 主打 calibration quality、IRT、causal intervention |
| PM reasoning analysis 已有人做 | 無法宣稱首次 | 定位為 allocation mechanism diagnosis |
| Benchmark 太簡單 | 無錯誤與 budget sensitivity | 先做 30 題 gate pilot |
| Public benchmark contamination | 難度失真 | 使用更新、私有或可生成驗證題；記錄 revision |
| Verbal assessment 成本過高 | 無實用節省 | 限制 assessment 長度，納入 total cost |
| LCAE 不優於 IRT-only | 核心假設受挫 | 預先接受負結果，改為 difficulty signal sufficiency |
| LCAE 不優於 Brier | 方法貢獻降低 | 比較 allocation-specific predictive utility |
| IRT 參數不穩 | 結論不可靠 | 增加模型數、bootstrap、2PL／domain sensitivity |
| CoT 不忠實 | PM 過度解釋 | 只宣稱 observable surface behavior |
| Budget–accuracy 非單調 | \(T^*\) 不穩 | Replicates、isotonic/Bayesian smoothing |
| 模型版本漂移 | 難以重現 | 鎖定 model ID、date、API params、artifacts |
| PM 差異只是長度效果 | 機制結論無效 | matched-length、matched-accuracy、paired controls |

---

## 19. 最終價值判斷

### 19.1 為何值得研究

1. Test-time compute allocation 是 2025–2026 的高熱度研究問題；
2. 現有研究已證明 adaptive allocation 可能大幅改善 token efficiency；
3. 現有模型仍缺乏可靠的 prospective metacognitive control；
4. Confidence-based methods 的核心弱點正是 calibration 不可靠；
5. LCAE 提供一個少見的 psychometric reference；
6. IDS 使 calibration 可以被 intervention，而非只被觀察；
7. 單一 trace reasoning-length allocation 尚未被 LCAE／IRT 完整研究；
8. PM 可提供 process-level failure diagnosis。

### 19.2 為何具有風險

1. 「Confidence 控制 token」的基本想法已不新；
2. Capability Calibration 已直接連結 calibration 與 best-of-\(k\) allocation；
3. Hidden-state/self-consistency 方法可能更便宜、更準；
4. IRT／LCAE 的增量價值尚未被證明；
5. Verbalized confidence 可能過度集中且 prompt-sensitive；
6. PM 的獨立 novelty 已降低。

### 19.3 綜合評分

| 面向 | 評估 |
|---|---|
| 實用重要性 | 高 |
| 研究熱度 | 高 |
| 寬泛題目新穎性 | 中低 |
| 收斂後題目新穎性 | 中高 |
| 方法可執行性 | 中 |
| 實驗成本 | 中高 |
| 失敗風險 | 中高 |
| 值得投入 | 約 7.5／10 |

### 19.4 最終建議

**值得繼續，但必須收斂題目。**

最適合的核心故事不是：

> Confidence 可以用來省 token。

而是：

> 現有研究已證明 confidence 可以控制推理長度，但通常假設 confidence 足夠
> 可靠。本研究檢驗 calibration quality 是否真正決定 allocation quality；
> 透過 IRT／LCAE 與 IDS intervention，建立 calibration → requirement
> prediction → allocation efficiency 的因果證據，並以 Process Mining 診斷
> allocation 改變了哪些可觀察推理行為。

---

## 20. 建議下一步

### 立即

1. 將 V2 正式標記為 PM feasibility pilot；
2. 修正 ARC label mapping；
3. 更新舊報告與 canonical results 的矛盾；
4. 建立 `experiments/v3-budget-allocation/`；
5. 驗證 Ollama／其他 backend 是否能 hard-control reasoning tokens；
6. 寫下 V3 preregistration 草稿。

### 第一個決定性實驗

```text
3 models
× 30 difficulty-stratified items
× 5 token budgets
× 2 replicates
= 900 generations
```

此實驗只回答：

> 是否存在可穩定測量、跨題有變異的 reasoning-token requirement？

若答案為否，暫停 LCAE allocator，不進行昂貴擴展。

### 第二個決定性實驗

在 requirement 可識別後，加入 QOQ vs IDS：

> IDS 是否改善 LCAE？改善後是否更能預測 \(T^*\)？

只有兩者皆成立，才進入完整 allocation 與 PM analysis。

---

## 參考文獻與主要連結

1. Chen, T.-Y. et al. (2026). **Latent Confidence Alignment for LLM
   Self-Assessment.** IEEE IRI 2026.  
   <https://arxiv.org/abs/2606.21937>

2. Kim, J., Lee, S.-G., & Kim, T. (2026). **Think Just Enough: Leveraging
   Self-Assessed Confidence for Adaptive Reasoning in Language Models.**
   Findings of EACL 2026.  
   <https://aclanthology.org/2026.findings-eacl.263/>

3. Li, Z. et al. (2026). **SelfBudgeter: Adaptive Token Allocation for
   Efficient LLM Reasoning.** Findings of ACL 2026.  
   <https://aclanthology.org/2026.findings-acl.1063.pdf>

4. Jiang, Q. et al. (2026). **CAT: Confidence-Adaptive Thinking for Efficient
   Reasoning of Large Reasoning Models.** ACL 2026 Industry Track.  
   <https://aclanthology.org/2026.acl-industry.152/>

5. Yang, S.-H. et al. (2026). **On Calibration of Large Language Models:
   From Response To Capability.**  
   <https://arxiv.org/abs/2602.13540>

6. Han, T. et al. (2025). **Token-Budget-Aware LLM Reasoning.** Findings of
   ACL 2025.  
   <https://aclanthology.org/2025.findings-acl.1274/>

7. Li, P. et al. (2026). **Adaptive Thinking: Large Language Models Know When
   to Think in Latent Space.** ICLR 2026／Apple Machine Learning Research.  
   <https://machinelearning.apple.com/research/adaptive-thinking>

8. Al Nazi, Z. & Roy Dipta, S. (2026). **TRIAGE: Evaluating Prospective
   Metacognitive Control in LLMs under Resource Constraints.**  
   <https://arxiv.org/abs/2605.13414>

9. Zhao, M., Qi, Q., & Sun, H. (2026). **ROI-Reasoning: Rational Optimization
   for Inference via Pre-Computation Meta-Cognition.**  
   <https://arxiv.org/abs/2601.03822>

10. Wan, X. et al. (2026). **The Shadow Price of Reasoning: Economic
    Perspective on Optimal Budget Allocation for LLMs.**  
    <https://arxiv.org/abs/2606.03092>

11. Li, J. et al. (2026). **Steering LLM Thinking with Budget Guidance.**
    Findings of ACL 2026.  
    <https://aclanthology.org/2026.findings-acl.1866/>

12. Oladri, R., Jawahar, N., & Mohamed, A. (2026). **Token Budget Saturation
    and Mechanistic Early Detection of Reasoning Non-Convergence in
    Chain-of-Thought Models.**  
    <https://arxiv.org/abs/2607.21433>

13. Berti, A., Kourani, H., Park, G., & van der Aalst, W. (2025).
    **Configuring Large Reasoning Models using Process Mining: A Benchmark and
    a Case Study.** TechRxiv preprint.  
    <https://d197for5662m48.cloudfront.net/documents/publicationstatus/260570/preprint_pdf/8710e5c6f0a1c02cd7f1ac69a2104256.pdf>

14. Park, T., Lee, Y., & Bae, H. (2025). **Reasoning-Aware GRPO using Process
    Mining.**  
    <https://arxiv.org/abs/2510.25065>

15. Berti, A., Kourani, H., & van der Aalst, W. (2025).
    **PM-LLM-Benchmark: Evaluating Large Language Models on Process Mining
    Tasks.**  
    <https://link.springer.com/chapter/10.1007/978-3-031-82225-4_45>

16. Lee, I., Liaw, S., & Yogatama, D. (2026). **FOL-Traces: Verified
    First-Order Logic Reasoning Traces at Scale.** Findings of EACL 2026.  
    <https://aclanthology.org/2026.findings-eacl.115/>

---

## 附錄 A：一句話研究定位

> **從「模型是否知道自己會不會」延伸到「模型是否知道自己需要思考多久」：
> 以 IRT／LCAE 校準自我評估、用受控 budget sweep 驗證 token requirement，
> 再以 Process Mining 解釋 calibration-aware allocation 的行為機制。**

## 附錄 B：投稿前必須重新確認的 Novelty Claims

投稿前不得直接使用以下用語，除非完成更新版 systematic search：

- first；
- 최초／首次；
- no prior work；
- entirely unexplored；
- completely novel intersection。

較安全的表述：

- To the best of our knowledge, after reviewing work on ...；
- Existing work has studied A and B separately, while the causal role of
  psychometric calibration in reasoning-length allocation remains
  underexplored；
- We focus on a distinct setting: training-free, single-trajectory
  reasoning-token allocation with IRT-grounded calibration；
- We use process mining as a diagnostic lens for allocation interventions,
  rather than as a generic analysis of LLM reasoning traces.
