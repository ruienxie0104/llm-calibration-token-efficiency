# Reading Notes: Process Mining — Data Science in Action

**Author:** Wil M.P. van der Aalst（PM 領域創始人）
**Publisher:** Springer, 2016
**Pages:** 477（16 章，6 個 Part）

---

## Book Structure

```
Part I: Introduction
  Ch1: Data Science in Action
  Ch2: Process Mining: The Missing Link
Part II: Preliminaries
  Ch3: Process Modeling and Analysis (Petri nets, BPMN, etc.)
  Ch4: Data Mining (classification, clustering, association rules)
Part III: From Event Logs to Process Models
  Ch5: Getting the Data (XES format, data extraction)
  Ch6: From Event Logs to Process Models (α-algorithm)
  Ch7: Advanced Process Discovery Techniques (heuristic, genetic, region-based)
Part IV: Beyond Discovery
  Ch8: Conformance Checking
  Ch9: Mining Additional Perspectives (org, time, case, decision)
  Ch10: Operational Support (predictive, prescriptive)
Part V: Tool Support and Applications
  Ch11: Tool Support (ProM, Disco, etc.)
  Ch12: Process Mining in the Large (big data, decomposition)
  Ch13: Analyzing "Lasagna Processes"
  Ch14: Analyzing "Spaghetti Processes"
Part VI: Reflection
  Ch15: Cartography and Navigation
  Ch16: Epilogue
```

---

## Chapter Summaries

### Chapter 1: Data Science in Action

PM 的定位：介于 process science（BPM、工作流管理）和 data science（數據挖掘、機器學習）之間的橋樑。

關鍵概念：
- **Internet of Events (IoE)**：所有事件數據的總集合，包含 IoC（內容）、IoP（人際）、IoT（物聯網）、IoL（位置）
- 數據從 analog → digital 的轉變產生了大量事件數據
- PM 的核心：用事件數據來發現、監控、改善真實流程

### Chapter 2: Process Mining: The Missing Link

**這是全書最重要的一章。**

#### PM 的三種類型

1. **Discovery（發現）**：從 event log 自動發現 process model，不需要任何先驗資訊
   - 例：α-algorithm 從 log 自動建構 Petri net
   
2. **Conformance（合規檢查）**：拿現有 process model 跟 event log 比對
   - 找出 model 和現實的差異
   - 用途：稽核、詐欺偵測、流程合規
   - 可以量化偏差程度

3. **Enhancement（增強）**：用 event log 的資訊來擴展或修正現有 model
   - Repair：修改 model 使其更符合現實
   - Extension：在 model 上加入新視角（如時間、資源）

#### 四個分析視角

| 視角 | 關注什麼 | 問題舉例 |
|------|----------|----------|
| **Control-flow** | 活動的順序 | 流程的正確路徑是什麼？ |
| **Organizational** | 資源/角色 | 誰在做什麼？人們怎麼合作？ |
| **Case** | 案例屬性 | 什麼因素影響案例的走向？ |
| **Time** | 時間/頻率 | 瓶頸在哪？服務水準如何？ |

#### Event Log 的最基本要求

- 每個 event 必須關聯到一個 **case**（流程實例）
- 每個 event 必須關聯到一個 **activity**（活動類型）
- 同一個 case 內的 events 必須有 **順序**
- 額外資訊：timestamp、resource、costs、data attributes

#### Play-In / Play-Out / Replay

- **Play-In**：從事件行為建構 model（= discovery）
- **Play-Out**：從 model 產生行為（= 模擬/執行）
- **Replay**：在 model 上重播 event log（= conformance + enhancement）

### Chapter 5: Getting the Data

event log 的格式和資料抽取。

- **XES (eXtensible Event Stream)**：PM 的標準格式，基於 XML
- 每個 event 有：trace（case）ID、activity name、timestamp、resource 等 attributes
- 資料抽取是 PM 的第一步，往往最花時間
- 真實資料通常散落在多個系統中，需要整合

### Chapter 6: From Event Logs to Process Models

**α-Algorithm** — 最基本的 process discovery 演算法。

核心思路：
1. 從 event log 找出所有 activity pairs 的因果關係（a → b 表示 a 一定在 b 之前）
2. 用這些關係建構 Petri net
3. 四種基本結構：sequence、choice、parallel、loop

四個品質指標：
- **Fitness**：log 中的行為有多少能被 model replay
- **Precision**：model 不應該允許 log 中沒出現的行為（避免太寬鬆）
- **Generalization**：model 應該能泛化到未見過的行為（避免過擬合）
- **Simplicity**：model 應該越簡單越好

### Chapter 7: Advanced Process Discovery

- **Heuristic Mining**：能處理 noise 和不完整 log，基於頻率
- **Genetic Process Mining**：演化算法，用 fitness function 驅動，能處理複雜結構但很慢
- **Region-Based Mining**：從 transition system 合成 Petri net
- **Inductive Mining**：遞迴分割，產生 process tree（重要！PM4Py 的主力演算法）

### Chapter 8: Conformance Checking

**這章對我們研究最關鍵。**

#### Token Replay 方法
- 把 event log 在 Petri net 上「重播」
- 計算 missing tokens（model 說要有但 log 沒做）和 remaining tokens（log 做了但 model 沒預期）
- **Fitness 公式**：fitness(L,N) = 1 - (missing + remaining) / (consumed + produced)

#### Alignments 方法（更先進）
- 不只是重播，而是找 log trace 和 model 之間的「最佳對齊」
- 每個 alignment 有 log move（log 有 model 沒）、model move（model 有 log 沒）、synchronous move（兩邊都有）
- 可以精確定位偏差在哪個 step

#### 偏差的兩種解讀
1. Model 是錯的 → 需要 repair model
2. 現實偏離了 model → 需要更好的控制
- 這兩種解讀都合理，要看場景

#### 關鍵啟示
- **Conformance checking 不只是「對不對」，而是「差多遠」和「差在哪」**
- 可以產生 global conformance measure（整體合規度）+ local diagnostics（哪個步驟偏離最多）

### Chapter 9: Mining Additional Perspectives

- **Organizational perspective**：從 log 中發現組織結構、社交網路
- **Time perspective**：瓶頸分析、等待時間、服務時間
- **Case perspective**：案例屬性如何影響流程走向
- **Decision mining**：在 decision point 上，哪些因素決定了選哪條路

### Chapter 13-14: Lasagna vs Spaghetti Processes

- **Lasagna processes**：結構化、可預測、有清晰的流程邊界（如銀行貸款流程）
- **Spaghetti processes**：高度不規則、案例間差異大（如醫院急診）
- LLM 推理軌跡可能更接近 Spaghetti（每題解法都不同）但也有 Lasagna 特徵（都有「理解→解題→驗證」的大框架）

---

## Key Concepts for Our Research (PM × LLM Reasoning Trace)

### Event Log → CoT Trace Mapping

| PM Event Log 概念 | LLM 推理軌跡對應 | 說明 |
|-------------------|------------------|------|
| **Case ID** | Question ID | 每個題目 = 一個 process instance |
| **Activity** | Step Type（語義標注） | 如「理解問題」、「回憶知識」、「計算」、「驗證」、「給答案」 |
| **Timestamp** | Step sequence order | CoT step 的先後順序（不需要真實時間，順序即可） |
| **Resource** | Model name / token cost | 哪個模型執行的、花了多少 token |
| **Trace** | Full CoT sequence | 一道題的完整推理過程 |
| **Variant** | Unique trace pattern | 不同模型或不同題目產生的不同推理路徑 |
| **Event attribute** | Step metadata | step 的 token 數、step 類型、是否正確 |

### 需要解決的技術問題

1. **Step Segmentation**：怎麼把一段 CoT 切成 steps？
   - 句子級：太細，noise 太多
   - 段落級：合理但要定義邊界
   - 語義級（推薦）：用 LLM 把 CoT 切成语義步驟，如「理解問題→回憶知識→計算→驗證→給答案」
   - 需要人工驗證一批來確認 segmentation 品質

2. **Activity Labeling**：每個 step 的 activity type 怎麼定？
   - 可以參考 Rebmann et al. (2025) 的 5 種 semantics-aware PM task 分類
   - 候選 label set：{understand, recall, calculate, reason, verify, reconsider, answer, other}
   - 用 LLM 輔助 labeling + 人工驗證

3. **定義「理想路徑」**：conformance checking 需要一個 reference model
   - 方法 A：用高 LCAE + 高 accuracy 模型的常見路徑當 baseline
   - 方法 B：用 expert 解題的標準步驟當 reference
   - 方法 C：用所有模型的最頻繁路徑當 normative model
   - 推薦方法 A：直接從數據中發現，不需要外部標準

### Applicable PM Methods

#### Process Discovery（用於 Phase 1）
- **Inductive Miner**（推薦）：PM4Py 主力，產生 process tree，能處理 noise
- Alpha Miner：最基本，但對 noise 敏感
- Heuristic Miner：能處理 noise，適合不完整 log
- **不建議** Genetic Miner：太慢

#### Conformance Checking（用於 Phase 1-2）
- **Alignments**（推薦）：能精確定位偏差，比 token replay 更好
- Token Replay：簡單但資訊量少
- 可以量化：高 LCAE 模型的推理路徑偏離「理想路徑」多少

#### Enhancement（用於 Phase 2-3）
- **Performance analysis**：把 token cost 投影到 process model 上，看哪些 step 最耗 token
- **Decision mining**：在推理的 decision point（如「要不再算一次？」），分析什麼因素影響決定

### PM-Derived Path Quality Metrics

從 PM 分析中可以提取的指標（這些是我們的新貢獻）：

| 指標 | 來源 | 意義 |
|------|------|------|
| **Path Length** | process model | 推理路徑的結構長度（不是 token 數，是 step 數） |
| **Loop Count** | process model | 迴路次數 = 重做的次數 = overthinking 指標 |
| **Conformance Deviation** | conformance checking | 偏離理想路徑的程度 |
| **Path Complexity** | process model | 模型複雜度（cyclomatic complexity） |
| **Determinism** | variant analysis | 不同題之間路徑的一致性 |
| **Token-per-Step** | enhancement | 每個 step 的平均 token 成本 |
| **Redundant Step Ratio** | conformance checking | 不在理想路徑上的 step 比例 |

### Research Story 用 PM 概念重新表述

```
學姐證明：IRT 難度信號 → LCAE 校準改善

我們的研究：
1. [Discovery] 對不同 LCAE 模型的 CoT trace 做 process discovery
   → 高 LCAE 模型和低 LCAE 模型的 discovered process model 有沒有結構差異？

2. [Conformance] 用高 LCAE 模型的路徑當 reference model
   → 低 LCAE 模型的 conformance deviation 是否顯著更高？

3. [Enhancement] 把 token cost 投影到 process model 上
   → 偏離理想路徑的 step 是否消耗了最多的 excess token？

4. [Causal] LCAE → path quality → token efficiency 的因果鏈
   → PM 指標是否中介了 LCAE 和 token efficiency 的關係？
```

### Open Questions / Research Inspirations

1. **「Overthinking =迴路」假設**：如果高 LCAE 模型的 process model 沒有迴路（不重做），低 LCAE 模型有迴路，這就直接用 PM 證明了 overthinking 的結構性來源

2. **「Underthinking = 路徑太短」假設**：低 LCAE + 低 accuracy 的模型可能路徑太短（跳過了 verify 步驟），PM 可以直接看到

3. **Decision Mining 應用**：在推理的 decision point（如「算了 → 給答案」vs「算了 → 再驗證一次」），用 decision mining 分析 LCAE 是否影響了這個決定

4. **Variant Analysis**：同一道題，不同模型的 variant 分佈——如果高 LCAE 模型的 variant 更集中（路徑更一致），說明校準好 → 推理更穩定

5. **Spaghetti vs Lasanna**：LLM 推理可能是「半結構化」——大框架固定（理解→解題→驗證→答案）但細節高度變異。PM 的 Lasagna/Spaghetti 分析框架可以直接套用

6. **Token as Resource**：PM 的 resource perspective 傳統分析「誰做的」，我們可以重新定義為「花了多少 token」。這讓 token cost 成為 PM 分析的一等公民，而不是附加指標

7. **Progressive Crystallization 對接**：如果發現高 LCAE 模型的路徑模式穩定，可以把這些路徑 crystallize 成 deterministic pattern，減少未來推理的 token 消耗（對接 Phase 3）

---

## TODO: Chapters Still to Read

- [ ] Ch10: Operational Support（預測性分析，可能用於 Phase 3）
- [ ] Ch11: Tool Support（ProM 功能，PM4Py 對應）
- [ ] Ch12: Process Mining in the Large（大規模分解技術）
- [ ] Ch15: Cartography and Navigation（process map 概念）

核心章節（Ch1-2, Ch5-9）已讀完，足夠支撐研究提案。