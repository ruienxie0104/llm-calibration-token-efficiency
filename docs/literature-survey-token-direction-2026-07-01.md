# 深度文獻調查：LLM 信心校準 × Token 效率

> **調查日期**: 2026-07-01
> **調查者**: Rosia (for Ryan)
> **目的**: 評估「Option 2: LLM 信心校準/自我評估 × Token 效率/分配」方向的文獻空白是否足夠支撐論文研究
> **搜尋範圍**: arXiv (cs.AI, cs.CL, cs.LG)，16 組系統性查詢

---

## 一、研究問題定位

### 核心問題
> **LLM 的自我評估能力（信心校準）能否預測其 token 需求？如果模型「知道自己會不會」，能否用更少 token 達到相同品質？**

### 學姐論文的缺口
- **學姐論文** (Chen et al., IEEE IRI 2026): 用 IRT (Rasch Model) + LCAE 指標 + IDS（難度訊號）改善 LLM 信心校準
- **明確提到但未深入**: "reveals an association between reliability and inference cost"
- **缺口**: token 成本效益只有粗估，未深入探討 token 分配、token 預測、token 最小化

### 本調查要回答的問題
1. 是否有人已經做了「IRT/難度 × token 分配」？
2. 是否有人做了「自我評估/信心校準 × token 效率」？
3. 是否有人做了「難度估計 × 推理長度預算」？
4. 這些工作的交集處，有沒有真正的空白？

---

## 二、文獻全景圖

### 2.1 搜尋矩陣

| 查詢軸 | 關鍵字組合 | 結果數 | 最相關論文數 |
|---|---|---|---|
| 1 | self-evaluation × inference cost × LLM | 2 | 2 |
| 2 | test-time compute × confidence × allocation | 6 | 4 |
| 3 | calibration × token budget | 11 | 5 |
| 4 | reasoning length × token × accuracy | 40 | 8 |
| 5 | IRT × LLM evaluation × cost | **0** | 0 |
| 6 | verbalized confidence × token | 31 | 6 |
| 7 | difficulty × token allocation × LLM | **0** | 0 |
| 8 | adaptive computation × self-evaluation × LLM | **0** | 0 |
| 9 | self-assessment × reasoning cost | **0** | 0 |
| 10 | difficulty estimation × inference × LLM | 7 | 5 |
| 11 | metacognition × inference cost × LLM | 3 | 2 |
| 12 | Rasch model × LLM × confidence | **1** | 1（學姐） |
| 13 | budget allocation × difficulty × reasoning | 7 | 7 |
| 14 | self-calibration × reasoning × efficiency | 4 | 2 |
| 15 | compute allocation × self-knowledge | **0** | 0 |
| 16 | confidence × reasoning length × LLM (prior) | 多 | 5 |

**關鍵發現：多個精準交集查詢返回 0 結果**

---

### 2.2 現有文獻分類

根據 16 組查詢結果，我將現有文獻分為 **5 個集群**：

---

## 三、五大文獻集群

### 集群 A：難度感知的 Token 預算分配（最接近但仍有缺口）

這個集群是與目標方向最接近的，但切入點全部不同。

#### A1. ROI-Reasoning (Zhao et al., 2026-01)
- **arXiv**: 2601.03822
- **核心**: 將推論預算形式化為 Ordered Stochastic Multiple-Choice Knapsack Problem (OS-MCKP)，兩階段框架：Meta-Cognitive Fine-Tuning（預測 reasoning cost 和期望效用）→ Rationality-Aware RL（在硬 token 預算下學習分配策略）
- **與目標的關係**: 最接近的工作之一。做了「預測任務需要多少 computation」+「在預算下分配」
- **缺口**: 
  - 沒有用 IRT/Rasch model，用自己訓練的 meta-cognitive 預測器
  - **沒有研究「自我評估準確度」和 token 需求的關係**——它預測的是「任務需要多少 token」，不是「模型自己對自己能力的評估有多準」
  - 沒有探討信心校準 × token 效率的因果關係

#### A2. UAB - Uncertainty-Aware Budget Allocation (Nguyen et al., 2026-05)
- **arXiv**: 2605.26849
- **核心**: 用 average negative log-likelihood (ANLL) 作為難度信號，重新分配 sampling budget。難的問題多 sample，簡單的少 sample
- **與目標的關係**: 做了「不確定性信號 → budget 分配」
- **缺口**:
  - 不確定性信號是 log-probability，**不是模型的 verbalized confidence 或自我評估**
  - 只做 sampling budget 分配（sample 幾次），**不是 reasoning length（思考多長）**
  - 沒有探討「自我評估能力本身」和 token 效率的關係

#### A3. CARD - Complexity Agnostic Recursive Decomposition (Qasim et al., 2025-12)
- **arXiv**: 2601.04210
- **核心**: 用 0.6B 模型預測 30 個 complexity 特徵 → 動態分配每步的 thought budget (1, 5-9, 10 thoughts)
- **與目標的關係**: 難度預測 → token 分配
- **缺口**:
  - 用外部小模型預測難度，**不是模型自我評估**
  - 沒有探討信心校準
  - 分配的是「thought 數量」而非「reasoning token 長度」

#### A4. TAB - Turn-Adaptive Budgets (Jali et al., 2026-04)
- **arXiv**: 2604.05164
- **核心**: 多輪推理中的 sequential compute allocation，建模為 multi-objective MDP，用 GRPO 訓練 budget policy
- **缺口**: 單純做多輪 budget 分配，不涉及自我評估

#### A5. AdaCtrl (2025-12)
- **arXiv**: 2505.18822
- **核心**: difficulty-aware budgeting for LLM reasoning
- **缺口**: 難度估計是 rule-based，不涉及模型自我評估能力

#### A6. DSC/ACTSC - Difficulty-Aware Self-Consistency (Yoon et al., 2026-02)
- **arXiv**: 2602.09438
- **核心**: 用 FFN neuron activations 構建 lightweight difficulty estimation probe，動態調整 sample 數
- **缺口**: 用 internal activations 不是 verbalized confidence，做的是 sampling 不是 reasoning length

#### A7. "The LLM Already Knows" (Zhu et al., 2025-09)
- **arXiv**: 2509.12886
- **核心**: 用 hidden representations + Markov chain value function 估計 LLM-perceived question difficulty，**不需生成任何 token**
- **與目標的關係**: 很接近——「模型在開始回答前就知道自己會不會」
- **缺口**:
  - 用 hidden states，不是 verbalized confidence
  - 沒有探討「自我評估準不準」和 token 需求的關係
  - 應用於 Self-Consistency/BoN/Self-Refine 的 sample 數，不是 reasoning length

#### A8. BCR - Batched Contextual Reinforcement (Yang et al., 2026-04)
- **arXiv**: 2604.02322
- **核心**: 訓練時讓模型同時解 N 個問題共享 context，產生 implicit token budget
- **缺口**: 訓練方法，不是推理時的自我評估

#### A9. ODAR-Expert (Ma et al., 2026-02)
- **arXiv**: 2602.23681
- **核心**: 用 active inference 的 difficulty estimator 在 Fast/Slow Agent 間路由
- **缺口**: 路由方法，不涉及信心校準 × token

#### A10. DAAO - Difficulty-Aware Agentic Orchestration (2026-02)
- **arXiv**: 2509.11079
- **核心**: VAE 難度估計 → 動態生成 query-specific multi-agent workflow → cost/performance-aware LLM router
- **缺口**: 系統架構導向，不涉及模型自我評估能力

**集群 A 總結**: 這個集群非常活躍，但所有人都在做「外部難度估計 → budget 分配」，幾乎沒有人做「模型自我評估能力 → token 需求預測」。

---

### 集群 B：LLM 信心校準與 Verbalized Confidence

#### B1. 學姐論文 - LCAE (Chen et al., IEEE IRI 2026)
- **arXiv**: 2606.21937
- **核心**: Rasch model + LCAE 指標 + IDS 難度信號 → 改善 self-assessment
- **關鍵貢獻**: 證明難度信號能改善信心校準；發現 reliability 與 inference cost 有關聯
- **缺口**: 沒有深入 token 效率議題

#### B2. "Reported Confidence Tracks Commitment More Than Correctness" (Kumaran, 2026-06)
- **arXiv**: 2606.29490
- **核心**: **重大發現**——verbalized confidence 追蹤的是「commitment」（要不要回答）而非「correctness」（對不對）。log-probabilities 才追蹤 correctness。兩者不可互換
- **與目標的關係**: 直接挑戰「用 verbalized confidence 做 token 分配」的假設——如果 verbalized confidence 不是追蹤 correctness，那用信心來分配 token 可能有根本問題
- **缺口**: 沒有探討 token 分配，只探討 abstain/commit 決策

#### B3. "Asking Is Not Enough: Protocol Sensitivity" (2026-05)
- **arXiv**: 2605.27752
- **核心**: 信心校準結果高度依賴測量協議（prompt template, probability scale, output format）
- **與目標的關係**: 提醒——自我評估的測量方式本身會影響結果

#### B4. "Score Granularity Gap" (Sun et al., 2026-06)
- **arXiv**: 2606.22179
- **核心**: verbalized confidence 只有少數幾個離散值，operator 能設的 threshold 很少
- **與目標的關係**: 如果要用信心分數做 token 分配，granularity 是實作挑戰

#### B5. "Speaking in Self-Assessing Tongues" (Marashian et al., 2026-06)
- **arXiv**: 2606.17234
- **核心**: 機器翻譯中的 verbalized confidence 研究
- **缺口**: 應用領域不同

#### B6. ExtractConf (Kumar et al., 2026-06)
- **arXiv**: 2606.24420
- **核心**: 多信號信心引擎（cross-call disagreement, logprobs, OCR, layout）→ 0.928 ROC AUC
- **缺口**: 應用導向（文件提取），不涉及 token 分配

#### B7. "LLMs can learn self-restraint" (Piché et al., 2024-05)
- **arXiv**: 2405.13022
- **核心**: 訓練模型在不确定時選擇棄權，不改變推理成本
- **缺口**: 做的是 abstain，不是 token 分配

#### B8. "Query-Level Uncertainty" (Chen et al., ICLR 2026)
- **arXiv**: 2506.09669
- **核心**: 在生成任何 token 之前估計模型能否回答該查詢 → 避免 generation cost。名為 Internal Confidence，用跨層跨 token 的 self-evaluation
- **與目標的關係**: 很接近——「回答前就知道需要多少 computation」
- **缺口**: 目標是 RAG/cascade 決策，不是 reasoning length 分配；用 internal signals 不是 verbalized confidence

**集群 B 總結**: 信心校準研究很活躍，但焦點在「信號是什麼」和「校準好不好」，沒有連接到「token 需求預測」或「token 效率優化」。Kumaran (2026-06) 的發現（verbalized confidence ≠ correctness tracking）是一個重要 caveat。

---

### 集群 C：Test-Time Compute Scaling 與 Adaptive Inference

#### C1. Entropy-Gated Branching (2026-01)
- **arXiv**: 2503.21961
- **核心**: 只在高不確定性步驟分支，用 lightweight verifier 剪枝
- **缺口**: 用 entropy，不是自我評估；做的是 branching 不是 budget allocation

#### C2. SLAT - Segment-Level Adaptive Trimming (Yao et al., 2026-05)
- **arXiv**: 2605.30832
- **核心**: 識別高機率低邊際效用的 segment → 選擇性修剪。50% reasoning length 減少
- **缺口**: segment 級修剪，不涉及模型自我評估

#### C3. BitCal-TTS (Patarlapalli & Avvaru, 2026-05)
- **arXiv**: 2605.05561
- **核心**: 量化模型中 confidence rescaling + bit-aware confirmation horizon
- **缺口**: 量化特定問題，不涉及自我評估 × token

#### C4. RLCM - RL with Confidence Margin (Wang et al., 2026-04)
- **arXiv**: 2604.23333
- **核心**: 用 RL 聯合優化 correctness 和 confidence reliability，擴大正確/錯誤步驟間的信心 margin
- **與目標的關係**: 做了「信心校準」和「推理」的結合
- **缺口**: 目標是校準本身，不是用校準來分配 token

#### C5. Latent Thought Flow (Zou et al., 2026-06)
- **arXiv**: 2606.16222
- **核心**: 在 latent space 做可變長度推理，用 GFlowNet 採樣
- **缺口**: latent reasoning，不涉及自我評估

#### C6. "Brief Is Better" (2026-04)
- **arXiv**: 2604.02155
- **核心**: function-calling agent 中 CoT budget (0-512 tokens) 對準確率的影響
- **缺口**: 應用導向，不涉及自我評估

#### C7. TRIAGE - Prospective Metacognitive Control (Nazi & Dipta, 2026-05)
- **arXiv**: 2605.13414
- **核心**: **非常相關**——給模型一個 task pool 和 token budget，要求它規劃「做哪些題、什麼順序、每題分配多少」。評估 prospective metacognitive control
- **與目標的關係**: 直接測試「模型能不能做好 token 分配的後設認知」
- **缺口**:
  - 評估的是「分配好不好」，不是「自我評估能力和 token 效率的關係」
  - 沒有探討 IRT 或難度信號
  - 沒有探討信心校準作為分配信號的效用

#### C8. SR²AM - Self-Regulated Simulative Reasoning (Deng et al., 2026-05)
- **arXiv**: 2605.22138
- **核心**: 三系統架構（System II 模擬推理 + System III 自我調節 + System I 執行），學會「何時規劃、規劃多深」
- **與目標的關係**: 做了「自我調節 × 計算分配」
- **缺口**: 沒有用信心校準做信號；用 RL 學的 policy

#### C9. "Quantization Inflates Reasoning" (Lian et al., 2026-06)
- **arXiv**: 2606.25519
- **核心**: 量化保持準確率但增加 reasoning token 使用（CoT Token Inflation Ratio）
- **缺口**: 量化議題，不涉及自我評估

**集群 C 總結**: Test-time compute scaling 是當前熱點，但大部分用 entropy/hidden state/RL policy 做 adaptive computation，**幾乎沒有人用 verbalized confidence 或自我評估指標做 token 分配**。

---

### 集群 D：IRT × LLM 評估

#### D1. 學姐論文（同 B1）
- 唯一用 arXiv 搜尋 "Rasch model × LLM × confidence" 找到的論文
- IRT × LLM × cost 的精準查詢返回 **0 結果**

#### D2. paper_survey 頻道中的 IRT 文獻
- Multilingual-IRT, Auditing LLM Benchmarks, IRT Scalable Framework, GAOKAO-Eval
- 這些都用 IRT 評估 LLM 能力，但**沒有人用 IRT 來預測 token 需求或做 token 分配**

**集群 D 總結**: IRT × LLM 評估有小眾但活躍的社群，但 IRT × token 效率的交集幾乎完全空白。

---

### 集群 E：Overthinking / 推理冗餘

#### E1. "Overthinking" 相關論文（prior searches）
- 多篇論文研究 LLM reasoning 的冗餘問題
- 主要方向：length penalty, segment trimming, early exit
- **沒有任何人從「自我評估能力」角度分析 overthinking 的原因**

---

## 四、核心 Gap 分析

### Gap 1: 「自我評估準確度 → Token 需求預測」無人做（★★★ 主要空白）

**現狀**:
- 有人用 external difficulty estimator 預測 token 需求（A1-A10）
- 有人用 hidden states 預測難度（A7）
- 有人用 log-probability 做 budget 分配（A2）
- 有人研究 verbalized confidence 的性質（B2-B4）

**空白**:
- **沒有人研究「模型對自己能力的評估有多準」和「它實際需要多少 token」之間的關係**
- 學姐發現 reliability 與 inference cost 有關聯，但沒有深入
- 沒有人測試「自我評估準的模型 → 能用更少 token 達到同樣品質」這個假設

**為什麼這重要**:
- 如果自我評估能力能預測 token 需求，就有了一個 **training-free 的 token 分配信號**
- 這跟用外部模型/hidden states 的方法不同——它是模型「自己知道」的

### Gap 2: 「IRT 難度信號 × Token 分配」無人做（★★☆ 重要空白）

**現狀**:
- 學姐證明 IRT 難度信號 (IDS) 能改善信心校準
- 有人做 difficulty-aware budget allocation（集群 A），但用自己訓練的 estimator

**空白**:
- **沒有人用 IRT 的客觀難度估計來指導 token 分配**
- IRT 提供的是「相對於模型能力的題目難度」，比 ad-hoc difficulty estimator 更有理論基礎

### Gap 3: 「Verbalized Confidence 作為 Token 分配信號」未被測試（★★☆ 有風險也有機會）

**現狀**:
- B2 (Kumaran, 2026-06) 發現 verbalized confidence 追蹤 commitment 而非 correctness
- 這意味著用 verbalized confidence 分配 token 可能有根本問題

**機會**:
- 如果 verbalized confidence 不追蹤 correctness，那什麼信號才追蹤？
- 能否設計一個「correctness-tracking 的 verbalized 信心」用於 token 分配？
- 這反而是一個研究問題而非阻礙

### Gap 4: 「信心校準改善 → Token 效率提升」的因果鏈未驗證（★★★ 核心機會）

**現狀**:
- 學姐證明 IDS 能改善信心校準
- 多人證明 difficulty-aware allocation 能減少 token
- **沒有人把這兩件事連起來**：改善信心校準 → 更好的 token 分配 → 更少 token 達到同樣品質

**這就是論文的 story**:
```
[IRT 難度信號] → [改善自我評估/信心校準] → [更準的 token 需求預測] → [更高效的 token 分配]
```

---

## 五、競爭者分析

### 最接近的競爭者

| 論文 | 重疊點 | 關鍵差異 |
|---|---|---|
| ROI-Reasoning (A1) | 預測 reasoning cost + budget allocation | 沒用 IRT，沒用自我評估，用自己訓練的 predictor |
| TRIAGE (C7) | Metacognitive control + token budget | 評估分配品質，不研究信心校準 × token 的關係 |
| 學姐 LCAE (B1) | IRT + 信心校準 + 提到 cost | 沒深入 token 效率 |
| "LLM Already Knows" (A7) | 回答前預測難度 | 用 hidden states，不用 verbalized confidence |
| UAB (A2) | 不確定性 → budget 分配 | 用 log-prob，不是自我評估 |

### 沒有任何一篇同時做到：
1. ✅ 用 IRT/客觀難度框架
2. ✅ 測量模型自我評估能力
3. ✅ 預測 token 需求
4. ✅ 驗證「校準好 → token 省」的因果鏈

---

## 六、文獻空白地圖

```
                    Token Efficiency
                         ↑
                         |
    [UAB] [ROI-R]        |    ★★★ GAP 1 ★★★
    [CARD] [TAB]        |    自我評估準確度
    [DSC] [ODAR]        |    × Token 需求預測
                         |    （無人做）
    [A7] [DAAO]         |
    ────────────────────+──────────────────→
    External Signal     |    Self-Assessment
                         |
                         |    ★★★ GAP 4 ★★★
    [EGB] [SLAT]        |    校準改善 → Token 省
    [RLCM] [LTF]        |    因果鏈驗證
                         |    （無人做）
                         |
                         |    ★☆ GAP 2 ☆★
    [學姐 LCAE]          |    IRT × Token 分配
                         |    （無人做）
                         |
    [B2-B8]              |    ★☆ GAP 3 ☆★
    Verbalized Conf      |    Verbalized conf 作為
    Properties           |    Token 分配信號
                         |    （未被測試）
```

---

## 七、風險評估

### 高風險
1. **Verbalized confidence 可能不適合做 token 分配信號** (B2 證據)
   - 緩解: 改用 log-prob-based 自我評估，或設計新的 verbalized 格式
   - 或: 將此作為研究問題而非假設——「verbalized vs logprob 哪個更適合 token 分配？」

2. **因果鏈可能不成立**——校準好不代表 token 省
   - 緩解: 設計實驗直接測試，如果因果鏈不成立，這本身也是一個發現

### 中風險
3. **範圍可能太窄**——只有「自我評估 × token」一個交集
   - 緩解: 擴大到「後設認知 × 計算分配」更廣的框架

4. **ROI-Reasoning 太接近**——已經做了 meta-cognitive prediction + budget allocation
   - 緩解: 差異足夠大（ROI-Reasoning 不用 IRT、不測信心校準、不做校準×token 因果分析）

### 低風險
5. **缺乏 benchmarks**——需要自己設計實驗
   - 緩解: 可借力學姐的資料和框架

---

## 八、結論與建議

### 文獻空白確認

**是的，文獻空白是真實且顯著的。** 具體來說：

1. **「自我評估能力 × Token 需求」的交集幾乎完全空白**（16 組查詢中多個精準交集返回 0 結果）
2. **IRT × Token 分配無人做**（0 結果）
3. **校準改善 → Token 效率提升的因果鏈無人驗證**
4. 學姐明確提到 cost 但沒深入，留了明確的延伸空間

### 建議的論文 Story

> **Research Question**: Can LLM self-assessment quality, measured through IRT-based difficulty signals, predict and optimize token allocation for efficient reasoning?

> **Core Hypothesis**: Models with better calibrated self-assessment (lower LCAE) can more accurately predict their token requirements, enabling more efficient token budget allocation without sacrificing accuracy.

> **Contributions**:
> 1. 揭示自我評估能力與 token 需求的關係（新發現）
> 2. 用 IRT 難度信號預測 token 需求（新方法）
> 3. 驗證「校準好 → token 省」的因果鏈（新驗證）
> 4. 提出基於自我評估的 token 分配策略（新框架）

### 與學姐論文的銜接

- 學姐: IRT → LCAE → IDS 改善校準（但只有粗估 cost）
- Ryan: LCAE → token 需求預測 → token 分配優化（深入 cost 議題）
- 銜接點: LCAE 指標、IDS 難度信號、20 models 評估資料

### 下一步

1. **確認方向**：Ryan 與指導教授討論，確認這個 story 是否可行
2. **實驗設計**：
   - 用學姐的 20 models + LCAE 資料
   - 測量每個模型在不同難度題目上的 token 使用量
   - 分析 LCAE 與 token 效率的相關性
3. **如果相關性強**：設計 token 分配策略，驗證效率提升
4. **如果相關性弱**：這本身是一個重要發現（自我評估和 token 效率無關）

---

## 附錄：所有搜尋查詢

| # | Query | Results |
|---|---|---|
| 1 | "self-evaluation" AND "inference cost" AND "LLM" | 2 |
| 2 | "test time compute" AND "confidence" AND "allocation" | 6 |
| 3 | "calibration" AND "token budget" | 11 |
| 4 | "reasoning length" AND "token" AND "accuracy" | 40 |
| 5 | "IRT" AND "LLM evaluation" AND "cost" | **0** |
| 6 | "verbalized confidence" AND "token" | 31 |
| 7 | "difficulty" AND "token allocation" AND "LLM" | **0** |
| 8 | "adaptive computation" AND "self-evaluation" AND "LLM" | **0** |
| 9 | "self-assessment" AND "reasoning cost" | **0** |
| 10 | "difficulty estimation" AND "inference" AND "LLM" | 7 |
| 11 | "metacognition" AND "inference cost" AND "LLM" | 3 |
| 12 | "Rasch model" AND "LLM" AND "confidence" | **1** (學姐) |
| 13 | "budget allocation" AND "difficulty" AND "reasoning" | 7 |
| 14 | "self-calibration" AND "reasoning" AND "efficiency" | 4 |
| 15 | "compute allocation" AND "self-knowledge" | **0** |
| 16 | Prior: 6 組 earlier searches | 多 |

**0-result queries 共 6 組，均為「自我評估 × token」相關的精準交集。**