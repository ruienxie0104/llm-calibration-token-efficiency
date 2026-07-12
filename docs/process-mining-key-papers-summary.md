# Process Mining × LLM Token Efficiency — Key Papers Summary

> Generated: 2026-07-12
> Purpose: Literature review for positioning our research on Process Mining × LLM Token Efficiency

---

## Paper 1: Re-Thinking Process Mining in the AI-Based Agents Era

### 論文基本資訊
- **標題:** Re-Thinking Process Mining in the AI-Based Agents Era
- **作者:** Andrea Berti, Wil M. P. van der Aalst, Marco Montali
- **年份:** 2024
- **arXiv ID:** 2408.07720

### 核心問題
傳統 Process Mining 假設事件日誌（event log）是被人類或固定資訊系統記錄的「已完成的過程」。但 AI agents（基於 LLM）現在成為過程的執行者，它們的行為是 stochastic 的——同一個任務可能走完全不同的路徑。傳統 PM 工具（如 discovery、conformance checking）能否直接應用於 agent 產生的 traces？有哪些新的挑戰和機會？

### 方法
- **概念分析框架:** 作者提出了 AI agent era 的 PM 新分類法，區分三個層次：
  1. **Agent-in-the-loop PM:** PM 用於分析 agent 的執行行為（agent traces 作為 event log）
  2. **PM for agent design:** 用 PM 發現的過程模型來設計/改進 agent 的 workflow
  3. **Agent-assisted PM:** 用 LLM agent 來輔助 PM 任務（如自動解釋 process model、自動修復 event log）
- **Trace 結構分析:** Agent traces 與傳統 event log 的關鍵差異：
  - Agent traces 包含 reasoning steps（不只是 actions）
  - 同一任務的 trace 長度和結構差異極大
  - Tool calls 是多層次的（一個 tool call 可能內含子過程）
  - 失敗和重試是常態，不是例外
- **Open challenges 識別:** 如何定義 agent trace 的「case」？如何處理 reasoning steps 和 tool calls 的混合？如何在 noisy traces 上做 conformance checking？

### 結果
- 提出了新的研究議程，將 PM 與 AI agents 結合
- 識別了傳統 PM 假設在 agent 場景下的失效點
- 呼籲開發專門針對 agent traces 的 PM 技術
- 指出 LLM 的 reasoning 能力可用來增強 PM 任務（如自動解釋偏差）

### 跟 Process Mining × LLM Token Efficiency 的關係
- **直接啟發:** 定義了 agent traces 作為 PM 分析對象的合法性。我們的研究進一步問：在 token 效率視角下，agent traces 能告訴我們什麼？
- **Trace 分析需求:** Agent traces 包含大量冗餘 reasoning，這正是 token 效率問題的來源。PM 可發現哪些 reasoning steps 是重複的、可省略的。
- **Conformance checking 的 token 含義:** 傳統 conformance checking 問「過程是否符合模型？」；token 效率視角下可問「agent 的 token 使用是否符合最優過程？」

### 可借用的方法/工具/指標
- **Agent trace 分類法:** reasoning steps vs. tool calls 的區分
- **三層 PM-Agent 互動框架:** 作為研究定位框架
- **Open challenges list:** 作為 research question 來源

---

## Paper 2: PMAx — An Agentic Framework for AI-Driven Process Mining

### 論文基本資訊
- **標題:** PMAx: An Agentic Framework for AI-Driven Process Mining
- **作者:** (多作者)
- **年份:** 2026
- **arXiv ID:** 2603.15351

### 核心問題
現有的 Process Mining 工具需要專業知識和手動操作。能否用 LLM-based agent 自動化整個 PM 流程——從 event log 載入、process discovery、conformance checking 到 result interpretation？

### 方法
- **多 Agent 架構:** Discovery Agent（自動選擇 discovery 演算法）、Conformance Agent（執行 conformance checking）、Enhancement Agent（效能/時間分析）、Orchestrator Agent（協調各 agent）
- **Tool integration:** 將 PM4Py 等傳統 PM 工具包裝為 agent tools
- **自然語言介面:** 用戶用自然語言描述分析需求，Orchestrator 轉化為具體 PM 任務
- **視覺化生成:** 自動生成 process model 圖表和自然語言解釋

### 結果
- 能自動完成 end-to-end PM 分析流程
- 在多個 benchmark event log 上展示正確的 discovery 和 conformance checking
- 大幅降低 PM 使用門檻
- LLM 能理解 activity label 語意，做出比純頻率更好的決策

### 跟 Process Mining × LLM Token Efficiency 的關係
- **Token 成本視角:** PMAx 的多 agent 架構本身有 token 效率問題——每個 agent 都需要完整 context。可用 PM 分析 PMAx 自己的 traces。
- **PM 作為 token efficiency 工具:** 反向應用——用 PM 來分析 LLM agent 行為。
- **自動化 PM 的 token 開銷:** Orchestrator 需大量 token 理解需求和選擇策略，是可優化點。

### 可借用的方法/工具/指標
- **多 agent 架構設計:** specialized agent 分工方式
- **PM4Py as agent tools:** 傳統 PM 工具包裝為 LLM tools
- **自然語言 → PM 任務映射**
- **Benchmark event logs**

---

## Paper 3: BPOP — De-Linearizing Agent Traces: Bayesian Inference of Latent Partial Orders for Efficient Execution

### 論文基本資訊
- **標題:** De-Linearizing Agent Traces: Bayesian Inference of Latent Partial Orders for Efficient Execution
- **作者:** Dongqing Li, Zheqiao Cheng, Geoff K. Nicholls, Quyu Kong
- **年份:** 2026
- **arXiv ID:** 2602.02806

### 核心問題
AI agents 產生線性化的 action traces，但很多 actions 之間無依賴關係，可並行執行。線性化掩蓋並行性，導致 agent 每步都需完整上下文推理。如何從 noisy 線性 traces 推斷潛在的依賴偏序關係？

### 方法
- **BPOP (Bayesian Partial Order) 框架:**
  - 將 agent trace 建模為潛在 dependency graph 的 stochastic linear extension
  - 用 MCMC 進行貝葉斯推斷恢復 dependency structure
  - 關鍵創新：**frontier-softmax likelihood** 避免了 #P-hard marginalization over linear extensions
- **資料集:** Cloud-IaC-6（開源雲端部署任務）、WFCommons（科學工作流程）
- **Compiled executor:** 基於推斷出的 dependency graph，識別可並行 actions、剪枝不相關 context、減少每步 token

### 結果
- BPOP 恢復 dependency structure 比 trace-only 和 process mining baselines 更準確
- Compiled executor 實現 **substantial reductions in token usage and execution time**
- 開源 Cloud-IaC-6 資料集和程式碼
- 證明線性化是效率損失主要來源

### 跟 Process Mining × LLM Token Efficiency 的關係
- **核心關聯:** 直接連接 PM 和 token efficiency——用 PM 技術減少 agent token 使用。Dependency discovery 本質上就是 process discovery，context pruning 就是 conformance-based optimization。
- **Partial order vs. linear trace:** 線性 trace 掩蓋並行性的洞見直接啟發我們用 PM 發現偏序結構來優化 token。
- **Context pruning:** 具體的 token efficiency 技術可結合我們的研究。
- **Bayesian 方法:** 為 PM 引入新的推斷方法，區別於傳統頻率式 discovery。

### 可借用的方法/工具/指標
- **Frontier-softmax likelihood:** 高效推斷技術
- **Cloud-IaC-6 dataset:** 實驗資料集
- **Compiled executor with context pruning:** Token reduction 技術
- **Dependency recovery accuracy / Token usage reduction / Execution time reduction:** 評估指標

---

## Paper 4: On the Potential of Large Language Models to Solve Semantics-Aware Process Mining Tasks

### 論文基本資訊
- **標題:** On the Potential of Large Language Models to Solve Semantics-Aware Process Mining Tasks
- **作者:** Adrian Rebmann, Fabian David Schmidt, Goran Glavaš, Han van der Aa
- **年份:** 2025
- **arXiv ID:** 2504.21074

### 核心問題
傳統 PM 基於頻率分析，忽略 activity 的語意。LLM 能否利用自然語言理解能力來解決 semantics-aware PM 任務？

### 方法
- **五個 semantics-aware PM 任務:** Semantic anomaly detection、Next activity prediction (semantic)、Process discovery (semantic)、Directly-follows relation generation、Process tree generation
- **Benchmark datasets:** 基於最大公開 process model collection 構建
- **LLM 評估:** In-context learning (zero/few-shot)、Supervised fine-tuning、Discriminative encoder models (BERT-based)
- **任務形式化:** PM 任務轉化為 NLP classification/generation 任務

### 結果
- 通用 LLM (zero-shot, few-shot) 在 semantics-aware PM 上表現不佳
- Fine-tuned LLM 在所有五個任務上達到 strong performance，跨產業泛化
- Generation 任務（DFG, process tree）比 classification 更難
- 證明語意理解確實改善 PM 性能

### 跟 Process Mining × LLM Token Efficiency 的關係
- **LLM 的 PM 能力邊界:** Zero-shot 不行，fine-tuning 可以。用 LLM 分析 agent traces 可能需 task-specific fine-tuning。
- **Token cost of fine-tuning vs. inference:** 需權衡 fine-tuning token 成本和推理 token 節省。
- **Semantic understanding → token efficiency:** 語意理解可能用更少 token 完成 PM 任務。
- **Benchmark datasets:** 可用於評估 token-efficient PM 方法。

### 可借用的方法/工具/指標
- **五個 semantics-aware PM 任務定義**
- **Benchmark datasets**
- **Fine-tuning pipeline for PM tasks**
- **In-context learning vs. fine-tuning 比較**
- **DFG 和 process tree generation 作為 output format**

---

## Paper 5: Progressive Crystallization — Turning Agent Exploration into Deterministic, Lower-Cost Workflows in Production

### 論文基本資訊
- **標題:** Progressive Crystallization: Turning Agent Exploration into Deterministic, Lower-Cost Workflows in Production
- **作者:** Arun Malik
- **年份:** 2026
- **arXiv ID:** 2607.07052

### 核心問題
AI agents 在 IT operations 中是永久成本中心——每次執行都需完整 LLM inference，即使問題已解決過。如何系統性地將 agent 探索行為轉化為更便宜、更確定的 workflow？

### 方法
- **Execution-type taxonomy:**
  - **Type 3 (Agent-orchestrated):** 自由探索，~10K–50K tokens/run
  - **Type 2 (Hybrid):** 固定步驟，特定步驟調用 LLM，~1K–5K tokens/run
  - **Type 1 (Deterministic):** 預編碼邏輯，零 token，毫秒級
- **Promotion lifecycle:** Discovery → Capture (trace extraction) → Promotion to Hybrid → Promotion to Deterministic
- **Evidence-based promotion criteria:** 最低成功次數（≥5）、一致性閾值（≥95%）、無 regression、acceptance test 100%
- **Automatic demotion:** Regression 時自動降級
- **Trace extraction:** 使用 process mining 從 agent traces 恢復 executable playbook
- **Economic model:** Type 1 比例增加，總 inference cost 下降

### 結果
- 生產環境（雲端 AIOps，每月數萬 incidents）：
  - Deterministic execution 0% → **45%**（8 個月）
  - Per-incident cost 降低 **>70%**（volume 翻倍情況下）
  - Reproducibility ~50% → 100%
  - False-positive rate <5%
- Safety monotonicity: 每次 promotion 保持或改善 safety

### 跟 Process Mining × LLM Token Efficiency 的關係
- **最佳案例:** 用 PM 技術系統性減少 LLM token 使用。Progressive crystallization 本質上就是「PM-driven token efficiency」。
- **Trace → Workflow 轉化:** 展示了我們研究的價值主張：PM 分析 agent traces → 發現可重複模式 → 減少 token。
- **Token cost spectrum:** Type 3→2→1 的 token 成本（50K→5K→0）量化了 PM 的 token savings。
- **Safety monotonicity:** 減少 token 不只省錢還更安全——重要附帶論證。
- **Economic model:** 量化 PM token savings 的經濟模型框架。

### 可借用的方法/工具/指標
- **Execution-type taxonomy (Type 1/2/3):** 分類 agent traces 和量化 token efficiency
- **Trace extraction algorithm**
- **Promotion/demotion criteria:** Evidence-based promotion gate
- **Economic model:** Token cost → dollar cost 量化
- **Type 1:2:3 ratio:** Maturity metric
- **Safety monotonicity argument**
- **Acceptance test generation from traces**

---

## Paper 6: CacheRL — Multi-Turn Tool-Calling Agents via Cached Rollouts and Hybrid Reward

### 論文基本資訊
- **標題:** CacheRL: Multi-Turn Tool-Calling Agents via Cached Rollouts and Hybrid Reward
- **作者:** (多作者)
- **年份:** 2026
- **arXiv ID:** 2606.14179

### 核心問題
Multi-turn tool-calling agents 在長流程中容易出錯——早期錯誤 cascade 到後續步驟。同時每次從頭推理非常昂貴。如何保持高 process accuracy 同時降低計算成本？

### 方法
- **Cached rollouts:** 緩存成功軌跡，在相似任務中重用
- **Hybrid reward:** Process reward（步驟順序正確性）+ Outcome reward（最終結果正確）
- **RL training:** Cached rollouts + hybrid reward 進行強化學習
- **Cache management:** 基於任務相似度的智慧緩存檢索

### 結果
- **92% process accuracy**（接近 GPT-5 的 94%）
- **~100× less compute** 達到這個水平
- Process reward 顯著改善步驟順序正確性
- Cached rollouts 同時加速訓練和推理

### 跟 Process Mining × LLM Token Efficiency 的關係
- **Process accuracy = conformance checking:** 步驟順序正確性本質上就是 PM 的 conformance checking，提供直接評估指標。
- **Cached rollouts = crystallized workflows:** 與 Progressive Crystallization 異曲同工——將成功軌跡固化為可重用資源。
- **Hybrid reward → token efficiency:** Process reward 鼓勵更短路徑，直接減少不必要步驟和 token。
- **100× compute reduction:** 證明 process-aware optimization 可帶來數量級效率提升。

### 可借用的方法/工具/指標
- **Process accuracy metric**
- **Cached rollout 機制:** Token-efficient agent execution 技術
- **Hybrid reward design:** Process + outcome reward 組合
- **Cache-based retrieval:** 任務相似度 cache 檢索
- **Compute reduction benchmark (100×)**

---

## Paper 7: Improving Hospital Process Management through Process Mining: COVID-19 Clinical Pathways

### 論文基本資訊
- **標題:** Improving Hospital Process Management through Process Mining: A Case Study on COVID-19 Clinical Pathways
- **作者:** Pasquale Ardimento, Mario Luca Bernardi, Marta Cimitile, Samuele Latorre
- **年份:** 2026
- **arXiv ID:** 2606.00041

### 核心問題
COVID-19 疫情期間醫院面臨極端流程變異性和容量壓力。傳統報告系統無法提供即時流程可見性。如何用 PM 從異質臨床資料重建患者照護路徑，識別瓶頸和變異，支援醫院治理決策？

### 方法
- **資料集:** CDSL (COVID Data for Shared Learning)，4,479 名患者，2019/12–2021/02，六個來源表格
- **Event log 構建 pipeline:** 六個 CSV 表格整合 → 統一 activity label set → 時間戳驗證修正 → XES 格式匯出（PM4Py）
- **三階段 PM 分析:**
  1. **Discovery:** DFG 發現主流程（ER Admission → Hospital Stay → Discharge，optional ICU Stay）
  2. **Conformance checking:** Declare reference model，檢查 triage 优先性、discharge 前提等約束
  3. **Enhancement/Outcome analysis:** 按年齡、ICU 暴露、監測強度分層分析 mortality 和 length of stay

### 結果
- 發現 monitoring backbone 貫穿住院全程
- ER→admission 介面存在高變異性
- Mortality 隨年齡增長（尤其 >70 歲），ICU 暴露者死亡率更高
- 中等監測強度（4-5 次/天）mortality 最低；過高（>6 次/天）反而升高（反映 case-mix 差異）
- 8% 患者 ICU 轉移，ER median LOS 6.2h，hospital median LOS 11.7 days
- 支援 triage 標準化、capacity planning、ICU step-down coordination

### 跟 Process Mining × LLM Token Efficiency 的關係
- **PM 的傳統應用案例:** 展示 PM 在真實場景的端到端流程——從資料構建到 insight 提取。我們的研究可借鑑這個流程應用於 agent traces。
- **Event log 構建經驗:** 從異質資料構建 event log 的 pipeline 設計可借鑑——agent traces 同樣是異質的（reasoning, tool calls, observations）。
- **Conformance checking 的價值:** Declare 模型的應用展示了 conformance checking 如何識別「文檔變異」vs「真正的過程偏差」——對 agent traces 同樣重要。
- **Outcome analysis 分層:** 按多維度分層分析 outcome 的方法可用於分析 agent token efficiency（按任務類型、模型、複雜度分層）。

### 可借用的方法/工具/指標
- **Event log 構建 pipeline:** 從異質資料 → XES 的完整流程
- **Declare conformance checking:** 規則式 conformance 模型
- **DFG discovery:** 可視化主流程
- **Outcome stratification:** 多維度分層分析
- **PM4Py pipeline:** Python PM 工具鏈
- **Median LOS / IQR / mortality rate:** 可改為 token usage 類似指標

---

## 總結與研究定位

### 這 7 篇合起來告訴我們什麼？

這 7 篇論文形成了一個從「問題定義」到「解決方案」的完整光譜：

1. **問題定義層 (Paper 1):** Berti et al. 定義了 PM × Agent 的新研究議程，指出 agent traces 作為 PM 分析對象的合法性與挑戰。

2. **能力評估層 (Paper 4):** Rebmann et al. 評估了 LLM 在 semantics-aware PM 任務上的能力邊界——zero-shot 不足，fine-tuning 有效。

3. **自動化 PM 層 (Paper 2):** PMAx 展示了用 LLM agent 自動化 PM 流程的可行性，同時暴露了 PM agent 本身的 token 效率問題。

4. **傳統 PM 應用層 (Paper 7):** Ardimento et al. 展示了 PM 在真實場景的端到端應用，提供了方法學和 pipeline 設計的參考。

5. **Token Efficiency 解決方案層 (Papers 3, 5, 6):** 這三篇直接解決 token efficiency 問題，但策略不同：
   - **BPOP (Paper 3):** Bayesian 推斷 → 偏序結構 → context pruning（**結構優化**）
   - **Progressive Crystallization (Paper 5):** Trace 提取 → 確定化 workflow → 零 token 執行（**生命周期優化**）
   - **CacheRL (Paper 6):** Cached rollouts + RL → process accuracy + compute reduction（**學習優化**）

**核心共識:** Agent traces 包含大量可被 PM 技術識別和消除的冗餘。PM 不只是分析工具，更是 token efficiency 的驅動力。

### 最大的研究缺口在哪？

1. **缺乏統一的 PM-based Token Efficiency 框架:**
   - BPOP 做結構優化，Crystallization 做生命周期優化，CacheRL 做學習優化——但沒有一個統一框架整合這三個維度。
   - 缺乏一個通用的「PM for Token Efficiency」方法論，可以系統性地指導何時用哪種優化策略。

2. **缺乏 Agent Trace 專用的 PM 技術:**
   - Berti et al. (Paper 1) 指出了這個缺口：傳統 PM 假設在 agent 場景下失效。
   - 現有解決方案（BPOP, Crystallization）各自設計了特定的 trace 處理方法，但沒有建立通用的 agent trace PM 技術。
   - 特別是 reasoning steps 的處理——傳統 PM 只有 activity-level event，agent traces 有 reasoning-step-level 和 tool-call-level 兩個層次。

3. **缺乏 Token Efficiency 的 PM 評估指標體系:**
   - 現有指標是分散的：BPOP 用 dependency recovery accuracy，Crystallization 用 Type 1:2:3 ratio，CacheRL 用 process accuracy。
   - 缺乏一個統一的指標體系來衡量「PM 技術對 token efficiency 的貢獻」。
   - 需要回答：多少 token 節省來自 PM 分析？vs. 來自模型改進？vs. 來自 prompt engineering？

4. **缺乏跨領域的 Agent Trace Benchmark:**
   - BPOP 有 Cloud-IaC-6，Crystallization 有 AIOps traces，CacheRL 有自己的 benchmark——但沒有跨領域的標準 agent trace dataset。
   - Rebmann et al. 的 PM benchmark 是基於 process models，不是 agent traces。

5. **Semantic-aware Token Efficiency 未被探索:**
   - Rebmann et al. 證明語意理解改善 PM 性能，但沒有人探索語意理解能否改善 token efficiency。
   - 例如：如果 LLM 理解 activity 語意，能否用更少的 token 完成 process discovery？

### 我們的研究應該怎麼定位才能填補這個缺口？

**定位建議：** 我們的研究應該定位為 **"Process Mining as a Token Efficiency Engine for LLM Agents"**——一個統一框架，用 PM 技術系統性地分析 agent traces 並優化 token 使用。

具體來說：

1. **統一框架:** 整合 BPOP 的結構優化、Crystallization 的生命周期優化、CacheRL 的學習優化為一個三層框架：
   - **結構層:** 用 PM 發現 traces 的偏序結構 → context pruning（BPOP 路線）
   - **模式層:** 用 PM 發現重複模式 → workflow 結晶化（Crystallization 路線）
   - **學習層:** 用 PM 的 conformance checking 構建 process reward → RL 優化（CacheRL 路線）

2. **Agent Trace 專用 PM 技術:** 開發專門處理 reasoning steps + tool calls 混合 traces 的 PM 技術，填補 Berti et al. 識別的缺口。

3. **Token Efficiency 指標體系:** 建立統一指標：
   - **Token Conformance Score:** Agent 的 token 使用與最優過程的偏差
   - **Token Efficiency Ratio:** PM 優化前後的 token 使用比
   - **PM-attributable Savings:** 歸因於 PM 分析的 token 節省量

4. **跨領域 Benchmark:** 構建涵蓋 coding agents、AIOps agents、tool-calling agents 的標準 trace dataset，附帶 token usage 標註。

5. **語意增強的 Token Efficiency:** 探索 LLM 的語意理解能力能否直接減少 PM 分析本身的 token 成本（結合 Rebmann et al. 的方向）。

**一句話定位:** 我們的研究是首個用 Process Mining 系統性驅動 LLM Agent Token Efficiency 的統一框架，填補現有工作在結構優化、生命周期管理、和學習優化之間的碎片化缺口。