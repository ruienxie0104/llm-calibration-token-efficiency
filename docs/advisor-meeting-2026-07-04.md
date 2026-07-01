# 研究提案：LLM 信心校準 × Token 效率

> **日期：** 2026-07-04（週五）與指導教授開會討論  
> **撰寫日期：** 2026-07-01  
> **學生：** Ryan (謝瑞恩)  
> **延續：** 學姐論文 (Chen et al., IEEE IRI 2026) 的後續研究方向  
> **老師建議方向：** Token 最小使用議題

---

## 目錄

1. 前情提要：學姐論文回顧與缺口
2. 老師建議的方向：Token 最小使用
3. 深度文獻調查結果
4. 四個核心文獻缺口
5. 研究問題與假設
6. 論文 Story 與貢獻設計
7. 實驗設計（Phase 1–3）
8. 與學姐論文的銜接
9. 風險評估與緩解策略
10. 時程規劃
11. 給老師的問題清單

---

## 一、前情提要：學姐論文回顧與缺口

### 1.1 學姐論文摘要 (Chen et al., IEEE IRI 2026)

**論文標題方向：** IRT-Based Self-Assessment Calibration Framework for LLMs

**三階段框架：**

```
Stage 1: 能力估計          Stage 2: 自我評估          Stage 3: 模型選擇
━━━━━━━━━━━━━━━━━━━━━    ━━━━━━━━━━━━━━━━━━━━━    ━━━━━━━━━━━━━━━━━━━━━
Rasch Model 把模型       四種自我評估情境：           LCAE 指標比較
能力和題目難度放在         • QOQ（不給任何訊號）       「模型自估」vs
同一把尺 → 客觀算         • IDS（給難度訊號）         「IRT 客觀估」的
答錯機率                  • DPR（給能力位置）          一致性 →
                          • Combined（全給）           搭配成本效益做
                                                     模型選擇
```

**關鍵發現：**
- **能力強 ≠ 自評準**：GPT-5 能力最強但 LCAE 不是最好；Llama 3 70B 自評最準
- **IDS 最有效**：給難度訊號是改善信心校準最有效的元素
- **校準不傷能力**：方法改善信心不會導致答題能力下降
- **Cost 提及但未深入**：論文提到 "reveals an association between reliability and inference cost"，但 token 成本效益只有粗估

### 1.2 老師指出的四個缺口

| 缺口 | 說明 |
|---|---|
| 只有 Rasch Model | 未計算鑑別度（可引入 2PL/3PL） |
| 難度訊號偏差 | IDS 的難度訊號來自同組受評模型，有循環依賴 |
| 成本估計簡化 | 未應用於實際場景，只有粗略 cost 估計 |
| **Token 未驗證** | **token 使用量與答題品質/自評準確度的關係完全未驗證** |

### 1.3 老師給 Ryan 的方向

> 延續學姐框架中 **token 的最小使用** 議題。設計簡單 vs 複雜任務場景，驗證 token 使用量與答題品質/自評準確度的關係。目標：用更少 token 達到同等品質的自我評估。

---

## 二、老師建議的方向：Token 最小使用

### 2.1 核心直覺

學姐證明了「給難度訊號 (IDS) 能改善信心校準」，但沒有回答：

- **改善信心校準之後，模型能不能更有效率地使用 token？**
- **如果模型「知道自己會不會」，能不能用更少 token 達到同樣品質？**
- **自我評估準確度（LCAE）和 token 使用效率之間有沒有關係？**

這三個問題構成了本研究的主軸。

### 2.2 從學姐的 Cost 提及到 Ryan 的深入探討

學姐論文在討論中提到 reliability 與 inference cost 有關聯，但只有粗估。本研究的目標是：

1. **精確測量** token 使用量（不只是粗估 cost）
2. **建立因果鏈**：校準改善 → token 需求預測 → token 分配優化
3. **驗證假設**：校準好的模型能用更少 token 達到同樣品質

---

## 三、深度文獻調查結果

### 3.1 調查規模

執行了 **16 組系統性 arXiv API 搜尋**，覆蓋以下關鍵字組合：

- self-evaluation × inference cost × LLM
- test-time compute × confidence × allocation
- calibration × token budget
- reasoning length × token × accuracy
- IRT × LLM evaluation × cost
- verbalized confidence × token
- difficulty × token allocation × LLM
- adaptive computation × self-evaluation × LLM
- self-assessment × reasoning cost
- difficulty estimation × inference × LLM
- metacognition × inference cost × LLM
- Rasch model × LLM × confidence
- budget allocation × difficulty × reasoning
- self-calibration × reasoning × efficiency
- compute allocation × self-knowledge
- confidence × reasoning length × LLM

### 3.2 關鍵發現：6 組精準交集查詢返回 0 結果

| 查詢 | 結果 |
|---|---|
| "difficulty" × "token allocation" × "LLM" | **0** |
| "adaptive computation" × "self-evaluation" × "LLM" | **0** |
| "IRT" × "LLM evaluation" × "cost" | **0** |
| "self-assessment" × "reasoning cost" | **0** |
| "compute allocation" × "self-knowledge" | **0** |
| "self-calibration" × "reasoning" × "efficiency" | 4（但不相關） |

### 3.3 現有文獻五大集群（彼此不交集）

#### 集群 A：難度感知的 Token 預算分配（~10 篇）

| 論文 | 核心方法 | 與本研究的關鍵差異 |
|---|---|---|
| ROI-Reasoning (2026-01) | Meta-cognitive 預測 reasoning cost + RL budget allocation | 不用 IRT，不測信心校準，用自訓 predictor |
| UAB (2026-05) | log-probability 做 sampling budget 分配 | 不是 verbalized confidence，做 sampling 不是 reasoning length |
| CARD (2025-12) | 0.6B 模型預測 complexity → thought budget | 用外部小模型，不涉及自我評估 |
| TAB (2026-04) | 多輪 sequential compute allocation | 不涉及自我評估 |
| "LLM Already Knows" (2025-09) | Hidden states 估計難度，不需生成 token | 用 hidden states，不是 verbalized confidence |
| DSC (2026-02) | FFN neuron activations 做 difficulty probe | 用 internal activations，做 sampling 不是 reasoning length |

**集群 A 總結：** 非常活躍，但所有人都在做「外部難度估計 → budget 分配」，幾乎沒有人做「模型自我評估能力 → token 需求預測」。

#### 集群 B：LLM 信心校準（~8 篇）

| 論文 | 核心方法 | 與本研究的關鍵差異 |
|---|---|---|
| 學姐 LCAE (IEEE IRI 2026) | IRT + LCAE + IDS | 沒深入 token 效率 |
| Kumaran (2026-06) | **Verbalized confidence 追蹤 commitment 而非 correctness** | 沒探討 token 分配 |
| "Asking Is Not Enough" (2026-05) | 信心測量高度依賴 protocol | 不涉及 token |
| Score Granularity (2026-06) | Verbalized confidence 只有少數離散值 | 不涉及 token |
| Query-Level Uncertainty (ICLR 2026) | 生成前估計能否回答 → 避免 generation cost | 用 internal signals，目標是 cascade 不是 reasoning length |

**集群 B 總結：** 信心校準研究活躍，但焦點在「信號是什麼」和「校準好不好」，沒有連接到 token 需求預測或 token 效率優化。

#### 集群 C：Test-Time Compute Scaling（~9 篇）

| 論文 | 核心方法 | 與本研究的關鍵差異 |
|---|---|---|
| Entropy-Gated Branching (2026-01) | 高不確定性才分支 | 用 entropy 不是自我評估 |
| SLAT (2026-05) | Segment 級修剪，50% reasoning 減少 | 不涉及自我評估 |
| TRIAGE (2026-05) | **測 prospective metacognitive control + token budget** | 評估分配品質，不研究信心校準 × token 的關係 |
| RLCM (2026-04) | RL 聯合優化 correctness 和 confidence | 目標是校準本身，不是用校準分配 token |
| SR²AM (2026-05) | 三系統架構，學會何時規劃、規劃多深 | 用 RL policy，不用信心校準做信號 |

**集群 C 總結：** 熱點領域，但大部分用 entropy/hidden state/RL policy 做 adaptive computation，幾乎沒有人用 verbalized confidence 或自我評估指標做 token 分配。

#### 集群 D：IRT × LLM 評估

- 只有學姐一篇用 Rasch model 做 LLM 信心校準
- 其他 IRT × LLM 論文（Multilingual-IRT, GAOKAO-Eval 等）用 IRT 評估能力，沒人用 IRT 預測 token 需求

#### 集群 E：Overthinking / 推理冗餘

- 多篇論文研究 LLM reasoning 的冗餘問題
- **沒有任何人從「自我評估能力」角度分析 overthinking 的原因**

---

## 四、四個核心文獻缺口

### Gap 1（★★★ 主要空白）：自我評估準確度 → Token 需求預測，無人做

**現狀：**
- 有人用 external difficulty estimator 預測 token 需求（集群 A）
- 有人用 hidden states 預測難度（"LLM Already Knows"）
- 有人用 log-probability 做 budget 分配（UAB）
- 有人研究 verbalized confidence 的性質（集群 B）

**空白：**
- 沒有人研究「模型對自己能力的評估有多準」和「它實際需要多少 token」之間的關係
- 學姐發現 reliability 與 inference cost 有關聯，但沒有深入
- 沒有人測試「自我評估準的模型 → 能用更少 token 達到同樣品質」這個假設

**為什麼重要：**
- 如果自我評估能力能預測 token 需求，就有了一個 **training-free 的 token 分配信號**
- 這跟用外部模型/hidden states 的方法不同——它是模型「自己知道」的

### Gap 2（★★☆ 重要空白）：IRT 難度信號 × Token 分配，無人做

**現狀：**
- 學姐證明 IRT 難度信號 (IDS) 能改善信心校準
- 有人做 difficulty-aware budget allocation（集群 A），但用自己訓練的 estimator

**空白：**
- 沒有人用 IRT 的客觀難度估計來指導 token 分配
- IRT 提供的是「相對於模型能力的題目難度」，比 ad-hoc difficulty estimator 更有理論基礎

### Gap 3（★★☆ 有風險也有機會）：Verbalized Confidence 作為 Token 分配信號，未被測試

**現狀：**
- Kumaran (2026-06) 發現 verbalized confidence 追蹤 commitment 而非 correctness
- 這意味著用 verbalized confidence 分配 token 可能有根本問題

**機會：**
- 如果 verbalized confidence 不追蹤 correctness，那什麼信號才追蹤？
- 能否設計一個「correctness-tracking 的 verbalized 信心」用於 token 分配？
- 這反而是一個研究問題而非阻礙

### Gap 4（★★★ 核心機會）：信心校準改善 → Token 效率提升，因果鏈未驗證

**現狀：**
- 學姐證明 IDS 能改善信心校準
- 多人證明 difficulty-aware allocation 能減少 token
- **沒有人把這兩件事連起來**

**這就是論文的 story：**

```
[IRT 難度信號] → [改善自我評估/信心校準] → [更準的 token 需求預測] → [更高效的 token 分配]
     (學姐已證)         (學姐已證)              (本研究驗證)               (本研究驗證)
```

---

## 五、研究問題與假設

### 5.1 研究問題

**RQ1:** LLM 的自我評估準確度（LCAE）能否預測其 token 需求？

> 如果模型「知道自己會不會」，它是否自然地用更少 token？

**RQ2:** IRT 難度信號（IDS）能否作為 token 分配的有效信號？

> 學姐證明 IDS 改善校準；如果再用 IDS 來分配 token，能否在不犧牲品質下減少 token？

**RQ3:** 信心校準改善是否因果性地導致 token 效率提升？

> 不是相關性，是因果鏈：改善校準 → 更好的 token 預測 → 更少 token 達到同品質

**RQ4:** Verbalized confidence 和 log-probability confidence 哪個更適合做 token 分配信號？

> Kumaran (2026-06) 發現 verbalized confidence 追蹤 commitment 而非 correctness。這在 token 分配場景下是否成立？

### 5.2 假設

| 假設 | 方向 | 信心 |
|---|---|---|
| H1 | LCAE 與 token 效率正相關（校準好 → token 省） | 中高 |
| H2 | IDS 難度信號能改善 token 分配效率 | 中高 |
| H3 | 信心校準改善 → token 效率提升的因果鏈成立 | 中（可能不成立，但不成立也是發現） |
| H4 | Log-prob confidence 比 verbalized confidence 更適合 token 分配 | 中（Kumaran 證據支持） |

---

## 六、論文 Story 與貢獻設計

### 6.1 論文 Story（一段話版本）

> 學姐證明了 IRT 難度信號能改善 LLM 的自我評估準確度（LCAE），並提到 reliability 與 inference cost 有關聯。但這個關聯從未被深入探討。本研究填補這個缺口：我們測量自我評估準確度與 token 使用效率的關係，驗證「校準好 → token 省」的因果鏈，並提出基於自我評估的 token 分配策略。如果成立，這提供了一個 training-free 的 token 優化方法——不需要額外訓練，只需要讓模型更了解自己。

### 6.2 貢獻設計（4 個貢獻）

| # | 貢獻 | 類型 | 對應 Gap |
|---|---|---|---|
| C1 | 揭示自我評估能力（LCAE）與 token 需求的關係 | 新發現 | Gap 1 |
| C2 | 用 IRT 難度信號預測 token 需求 | 新方法 | Gap 2 |
| C3 | 驗證「校準好 → token 省」的因果鏈 | 新驗證 | Gap 4 |
| C4 | 提出基於自我評估的 token 分配策略 | 新框架 | Gap 1+2+4 |

### 6.3 與現有工作的區別

| 最接近競爭者 | 重疊點 | 關鍵差異 |
|---|---|---|
| ROI-Reasoning (2026-01) | 預測 reasoning cost + budget allocation | 不用 IRT，不用自我評估，用自訓 predictor |
| TRIAGE (2026-05) | Metacognitive control + token budget | 評估分配品質，不研究信心校準 × token 的關係 |
| 學姐 LCAE | IRT + 信心校準 + 提到 cost | 沒深入 token 效率 |
| UAB (2026-05) | 不確定性 → budget 分配 | 用 log-prob，不是自我評估 |
| "LLM Already Knows" (2025-09) | 回答前預測難度 | 用 hidden states，不是 verbalized confidence |

**沒有任何一篇同時做到：** IRT 難度框架 ✗ + 測量自我評估能力 ✗ + 預測 token 需求 ✗ + 驗證校準→token 因果鏈 ✗

### 6.4 目標投稿場所

- **首選：** IEEE Big Data 2026（八月截止，約 6 週可做）
- **備選：** AAAI 2027 Workshop / IEEE IRI 2027（延續學姐發表場所）
- **長期：** 擴展為期刊版本（TKDE / TNNLS）

---

## 七、實驗設計

### 7.1 總體架構

```
Phase 1: 關聯性分析（學姐資料 + token 測量）
    ↓
Phase 2: 因果鏈驗證（操控校準 → 測量 token 變化）
    ↓
Phase 3: Token 分配策略（基於 Phase 1-2 發現，設計分配方法）
```

### 7.2 Phase 1：LCAE × Token 關聯性分析

**目標：** 驗證 H1 — LCAE 與 token 效率是否有相關性

**資料來源：**
- 學姐的 20 個模型 × 多難度題目資料
- 在相同題目上測量每個模型的 token 使用量

**測量變量：**

| 變量 | 來源 | 說明 |
|---|---|---|
| LCAE | 學姐資料 | 自我評估與 IRT 客觀估的一致性 |
| Ability (θ) | 學姐資料 | IRT 估計的模型能力 |
| Difficulty (b) | 學姐資料 | IRT 估計的題目難度 |
| Token usage (T) | **本研究新測** | 每題實際使用的 reasoning token 數 |
| Accuracy | 學姐資料 | 答題正確率 |
| Token efficiency | **本研究新定義** | Accuracy / Token usage（每 token 貢獻的正確率） |

**實驗步驟：**

1. 在學姐使用的 benchmark 上，對 20 個模型分別測量每題的 reasoning token 使用量
2. 計算每個模型的 LCAE 與平均 token efficiency 的相關性
3. 按難度分層分析：簡單題、中等題、困難題中，LCAE 與 token 效率的關係
4. 分析：校準好的模型是否在「簡單題少 token、困難題多 token」的分配上更合理

**預期結果：**
- 如果 H1 成立：LCAE 與 token efficiency 正相關，尤其在高難度題目上更顯著
- 如果 H1 不成立：自我評估能力和 token 效率無關——這本身也是重要發現

**控制變因：**
- 固定 temperature（0.0 或 0.3，需確認學姐設定）
- 固定 max_tokens（足夠大，不截斷）
- 同一 prompt template（避免 protocol sensitivity，參考 B3）

### 7.3 Phase 2：因果鏈驗證

**目標：** 驗證 H3 — 信心校準改善是否因果性地導致 token 效率提升

**設計邏輯：**
- 學姐已證明 IDS（給難度信號）能改善 LCAE
- 如果我們在有/無 IDS 的情況下測量 token 使用量，就能看到「校準改善 → token 變化」的因果效應

**實驗分組：**

| 組別 | 難度信號 | 預期 LCAE | 測量 |
|---|---|---|---|
| Control | 無（QOQ） | 較差（學姐已證） | Token usage + Accuracy |
| Treatment 1 | IDS | 較好（學姐已證） | Token usage + Accuracy |
| Treatment 2 | DPR | 中等（學姐已證） | Token usage + Accuracy |
| Treatment 3 | Combined | 最好（學姐已證） | Token usage + Accuracy |

**因果邏輯：**

```
IDS 改善 LCAE（學姐已證，已知效應）
         ↓
如果 IDS 同時改善了 token efficiency
         ↓
且 token efficiency 改善幅度與 LCAE 改善幅度正相關
         ↓
則支持「校準改善 → token 省」的因果鏈
```

**進一步分析：**

- 按 difficulty 分層：IDS 在哪個難度範圍對 token 效率影響最大？
- Token 分配合理性：IDS 組是否表現出「簡單題少 token、困難題多 token」的適應性分配？
- Overthinking 分析：IDS 組是否減少了簡單題的冗餘推理？

**控制實驗：Token 分配 vs Token 總量**

為了區分「更好的分配」和「更少的總量」：

| 條件 | 說明 |
|---|---|
| Free budget | 不限制 token，模型自然決定推理長度 |
| Fixed budget | 限制總 token，看不同校準組的分配品質 |
| Adaptive budget | 根據自我評估分配 token，看是否比 fixed 更好 |

### 7.4 Phase 3：Token 分配策略

**目標：** 驗證 H2 — 基於自我評估的 token 分配策略能否提升效率

**分配策略設計：**

```
輸入：模型收到題目
  ↓
Step 1: 模型自我評估（產生信心分數或預估難度）
  ↓
Step 2: 根據自我評估分配 token 預算
  - 高信心（簡單題）→ 少 token
  - 低信心（困難題）→ 多 token
  - 極低信心 → 棄權（不浪費 token）
  ↓
Step 3: 在分配的預算內生成回答
  ↓
Step 4: 評估 accuracy 和 token efficiency
```

**對照組：**

| 策略 | Token 分配依據 | 預期 |
|---|---|---|
| Uniform | 所有題目相同 token budget | 基線 |
| Oracle | IRT 難度（事後，知道正確答案） | 上限 |
| Self-assessment (verbalized) | 模型 verbalized confidence | 測 H4 |
| Self-assessment (log-prob) | 模型 log-prob confidence | 測 H4 |
| IDS-based | IRT 難度信號 + 自我評估 | 結合學姐框架 |
| External estimator | 外部模型預測難度 | 對照 ROI-Reasoning 風格 |

**評估指標：**

| 指標 | 定義 |
|---|---|
| Token efficiency | Accuracy / Total tokens |
| Budget utilization | Used tokens / Allocated tokens |
| Allocation quality | 與 Oracle 分配的相關性（Spearman ρ） |
| Regret | 比 Oracle 多用的 token 或少得的 accuracy |
| Calibration-aware efficiency | 在同 LCAE 水平下比較 token 效率 |

### 7.5 模型選擇

**優先使用學姐的 20 模型清單**（具體清單待確認），涵蓋：

- Frontier: GPT-5, Claude Sonnet 4.5, Gemini 2.5 Pro
- Mid-tier: Llama 3 70B, Mistral Large, Qwen 3.5
- Small: 各廠商輕量模型

**新增考量：**
- 為了 token 分析，需要選擇支援 reasoning token 計數的模型
- 確認學姐資料中是否已有 token 使用記錄（如有，可直接分析）

### 7.6 Benchmark 選擇

**優先使用學姐的 benchmark**（具體待確認），需涵蓋：
- 多難度等級（IRT 需要 spread）
- 多領域（避免 domain-specific bias）
- 有客觀正確答案（binary 或 graded）

**擴展考量：**
- 如學姐 benchmark 太單一，可加入 MMLU subset（多領域多難度）
- 考慮加入 GSM8K 或 MATH（reasoning 密集，token 差異更明顯）

---

## 八、與學姐論文的銜接

### 8.1 資產重用

| 學姐的資產 | 本研究的用途 |
|---|---|
| 20 models 的 IRT 能力估計 (θ) | 直接重用，不需重新估計 |
| 題目難度參數 (b) | 直接重用 |
| LCAE 指標計算方法 | 直接重用，可能擴展 |
| IDS/QOQ/DPR/Combined 四種自我評估情境 | Phase 2 因果實驗的操控變因 |
| 自我評估 prompt templates | 直接重用，控制 protocol sensitivity |
| Benchmark 資料 | Phase 1 關聯性分析的基礎 |

### 8.2 新增部分

| 本研究新增 | 學姐沒做的 |
|---|---|
| Token 使用量精確測量 | 學姐只有粗估 cost |
| Token efficiency 指標定義 | 學姐未定義 |
| 因果鏈驗證實驗 | 學姐只觀察到關聯 |
| Token 分配策略 | 學姐未設計分配方法 |
| Verbalized vs log-prob 比較 | 學姐未比較信號類型 |
| Overthinking 分析 | 學姐未分析推理冗餘 |

### 8.3 敘事銜接

```
學姐的 Story:
  IRT → LCAE → IDS 改善校準 → 提到 cost 關聯

Ryan的 Story:
  LCAE → token 需求預測 → token 分配優化 → 驗證因果鏈
  (把學姐「提到的 cost 關聯」變成「深入驗證的因果鏈」)
```

---

## 九、風險評估與緩解策略

### 9.1 高風險

**風險 1：Verbalized confidence 不適合做 token 分配信號**

Kumaran (2026-06) 發現 verbalized confidence 追蹤 commitment 而非 correctness。如果用 verbalized confidence 分配 token，可能分配錯誤。

- **機率：** 中高（有直接證據）
- **影響：** 如果只用 verbalized confidence，H4 可能不成立
- **緩解：**
  1. 同時測 verbalized 和 log-prob 兩種信號（H4 就是為了回答這個）
  2. 設計新的 verbalized 格式（如「預估需要多少推理步驟」而非「信心幾分」）
  3. 將此作為研究問題而非假設——「哪種信號更適合 token 分配？」
  4. 即使 verbalized 不行，log-prob 或 IDS 仍然可能有效

**風險 2：因果鏈不成立**

校準好不代表 token 省。可能校準好的模型在某些場景反而用更多 token（因為「知道自己不會」所以更謹慎、推理更長）。

- **機率：** 中
- **影響：** H3 不成立，但 H1 可能仍然成立（只是不是因果）
- **緩解：**
  1. 不成立本身是一個重要發現（「校準好 ≠ 省 token」打破了直覺假設）
  2. 區分「token 分配合理性」和「token 總量」——校準好可能改善分配但不減少總量
  3. 報告 null result 並分析為什麼不成立

### 9.2 中風險

**風險 3：範圍太窄**

只有「自我評估 × token」一個交集，可能被認為 contribution 不夠。

- **機率：** 中
- **影響：** 被 reviewer 認為 incremental
- **緩解：**
  1. 擴大 framing 為「後設認知 × 計算分配」
  2. 貢獻 C1-C4 涵蓋發現、方法、驗證、框架四個層面
  3. 與 ROI-Reasoning、TRIAGE 等最近工作比較，強調差異

**風險 4：學姐資料不一定有 token 記錄**

如果學姐的實驗沒有記錄 token 使用量，需要重跑實驗。

- **機率：** 中（需確認）
- **影響：** 增加 1-2 週工作量
- **緩解：**
  1. 先跟學姐確認資料格式
  2. 如需重跑，只跑代表性子集（如 5 個模型 × 100 題），而非全部 20 模型
  3. 重跑時順便收集更豐富的 token metrics（reasoning tokens vs output tokens）

**風險 5：ROI-Reasoning 太接近**

已經做了 meta-cognitive prediction + budget allocation。

- **機率：** 低中
- **影響：** 被質疑 novelty
- **緩解：** 差異足夠大（ROI-Reasoning 不用 IRT、不測信心校準、不做校準×token 因果分析、用自訓 predictor 而非自我評估）

### 9.3 低風險

**風險 6：缺乏 benchmarks**

需要自己設計實驗，沒有現成 benchmark。

- **機率：** 低
- **影響：** 需要更多設計工作
- **緩解：** 可借力學姐的 benchmark 和框架

---

## 十、時程規劃

### 10.1 以 IEEE Big Data 2026（八月截止）為目標

| 週次 | 時間 | 任務 | 產出 |
|---|---|---|---|
| W1 | 7/1–7/7 | 確認學姐資料格式、取得 20 模型清單、確認 token 記錄狀況 | 資料清單、缺口確認 |
| W2 | 7/8–7/14 | Phase 1 資料收集（如需重跑：5 模型 × 學姐 benchmark + token 測量） | Phase 1 raw data |
| W3 | 7/15–7/21 | Phase 1 分析 + Phase 2 實驗執行（IDS/QOQ/DPR/Combined × token 測量） | Phase 1 結果 + Phase 2 raw data |
| W4 | 7/22–7/28 | Phase 2 分析 + Phase 3 策略設計與實驗 | Phase 2 結果 + Phase 3 raw data |
| W5 | 7/29–8/4 | Phase 3 分析 + 論文初稿撰寫 | 完整結果 + 初稿 |
| W6 | 8/5–8/11 | 論文修改、補實驗、定稿 | 論文終稿 |
| 截止 | 8/12 前 | 投稿 | ✅ |

### 10.2 如時間不足的降級方案

| 降級級別 | 內容 | 仍有的貢獻 |
|---|---|---|
| Level 0（完整） | Phase 1+2+3 全做 | C1+C2+C3+C4 |
| Level 1 | Phase 1+2，Phase 3 簡化（只做策略設計不做實驗） | C1+C2+C3 |
| Level 2 | Phase 1+2，不做 Phase 3 | C1+C3（關聯+因果） |
| Level 3 | 只做 Phase 1 | C1（關聯性發現） |

**即使 Level 3 仍然是一個貢獻：** 首次揭示自我評估能力與 token 需求的關係，配合學姐框架延伸，足以寫一篇 short paper 或 workshop paper。

### 10.3 如不趕 IEEE Big Data 的長期規劃

| 階段 | 時間 | 內容 |
|---|---|---|
| 短期 | 7–8 月 | Phase 1+2，投 IEEE Big Data 或 Workshop |
| 中期 | 9–12 月 | Phase 3 + 擴展模型/題目集，投 AAAI 2027 或期刊 |
| 長期 | 2027 春 | 結合 nhri-kidney-agent 的記憶衝突實驗（metadata 消融類似 IDS 結構化信號），探討「結構化信號能否同時改善校準和 token 效率」 |

---

## 十一、給老師的問題清單

### 核心問題

**Q1: 方向確認**
> 老師之前建議延續學姐的 token 最小使用議題。我做了一輪深度文獻調查（16 組 arXiv 搜尋），確認了四個核心缺口。請問老師覺得這個 story——「自我評估準確度 → token 需求預測 → token 分配優化」——是否可行？

**Q2: 與學姐資料的銜接**
> 學姐的 20 模型實驗資料中，是否有記錄 token 使用量？如果沒有，我需要重跑。老師能否協助取得學姐的實驗資料和 benchmark 細節？

**Q3: 期刊 vs 會議**
> 以目前 6 週可做的實驗量（Phase 1+2，可能加 Phase 3），適合投 IEEE Big Data 2026（八月截止）嗎？還是老師建議做更深再投其他場所？

**Q4: 範圍取捨**
> 如果時間不夠做完整三個 Phase，老師覺得哪個 Phase 最重要？Phase 1（關聯性）是基礎，Phase 2（因果鏈）是核心論點，Phase 3（分配策略）是應用。砍哪個最可惜？

**Q5: Benchmark 選擇**
> 學姐用的 benchmark 是什麼？是否需要擴展到多領域（如 MMLU + GSM8K）以增加 generalizability？

**Q6: Verbalized confidence 風險**
> Kumaran (2026-06) 發現 verbalized confidence 追蹤 commitment 而非 correctness。老師覺得這是一個風險還是一個研究機會？我應該把「哪種信號更適合 token 分配」作為研究問題，還是直接假設用 log-prob？

**Q7: 與 nhri-kidney-agent 的關係**
> 之前的記憶衝突實驗（2,800 + 280 calls）發現「status metadata 類似 IDS 結構化信號」。這兩個方向有沒有可能結合？例如：在記憶衝突場景下，metadata 能否同時改善校準和 token 效率？還是應該專注一個方向？

**Q8: 模型選擇**
> 學姐用了 20 個模型。我需要全部重跑嗎？還是選代表性子集（如 5-8 個，涵蓋 frontier/mid/small）即可？

---

## 附錄 A：文獻空白地圖

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

## 附錄 B：所有搜尋查詢結果

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

## 附錄 C：關鍵論文清單

| ID | 論文 | arXiv | 集群 | 與本研究的關係 |
|---|---|---|---|---|
| A1 | ROI-Reasoning | 2601.03822 | A | 最接近的競爭者 |
| A2 | UAB | 2605.26849 | A | log-prob budget 分配 |
| A3 | CARD | 2601.04210 | A | 外部小模型預測難度 |
| A7 | "LLM Already Knows" | 2509.12886 | A | Hidden states 預測難度 |
| B1 | 學姐 LCAE | 2606.21937 | B | 直接延續 |
| B2 | Kumaran | 2606.29490 | B | Verbalized conf ≠ correctness |
| B3 | Protocol Sensitivity | 2605.27752 | B | 測量方式影響結果 |
| B8 | Query-Level Uncertainty | 2506.09669 | B | 生成前估計能力 |
| C1 | Entropy-Gated Branching | 2503.21961 | C | Entropy 信號 |
| C2 | SLAT | 2605.30832 | C | Segment 修剪 |
| C7 | TRIAGE | 2605.13414 | C | Metacognitive budget |
| C8 | SR²AM | 2605.22138 | C | 自我調節推理 |

---

> **文件位置：** `docs/advisor-meeting-2026-07-04.md`  
> **完整文獻調查報告：** `docs/literature-survey-token-direction-2026-07-01.md`  
> **前次討論報告：** `docs/advisor-discussion-2026-06-30.md`