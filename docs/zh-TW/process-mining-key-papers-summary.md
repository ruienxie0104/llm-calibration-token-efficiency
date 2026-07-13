# Process Mining × LLM：關鍵論文摘要

> 為 Process Mining × LLM Token 效率研究方向策劃的文獻回顧。
> 7 篇論文，涵蓋 agentic process mining、軌跡去線性化、workflow 結晶化、快取 RL 與臨床 process mining。

---

## 論文 1：Re-Thinking Process Mining in the AI-Based Agents Era（重新思考 AI Agent 時代的 Process Mining）
- **arXiv ID:** 2408.07720
- **作者:** Alessandro Berti et al.
- **年份:** 2024
- **URL:** https://arxiv.org/abs/2408.07720

### 核心問題
LLM 在 process mining（PM，流程探勘）任務上展現潛力，但在需要進階推理的複雜場景中表現不佳。現有方法 — 從流程抽象中提取文字洞察，或 LLM 直接在原始工件上生成程式碼 — 在處理複雜性時有其限制。

### 方法
論文提出 AI-Based Agents Workflow（AgWf）範式用於 PM 任務。核心設計原則：(1) 將複雜 PM 任務分解為更簡單的子任務形成 workflow，(2) 整合 deterministic PM tools（確定性 PM 工具）與 LLM 領域知識，而非完全依賴 LLM，(3) 使用 CrewAI 框架實作。此方法將 LLM 視為呼叫專用 PM 工具的 orchestrator（編排器），而非試圖端到端解決所有問題。

### 關鍵發現
AgWf 透過 workflow 分解和確定性工具整合，顯著提升了 PM 效果，優於直接使用 LLM 的方法。論文證明將 LLM 推理與既有 PM 工具結合（而非取代它們）能產生更好結果。CrewAI 實作提供了一個具體框架來建構這類多步驟 PM pipeline。

### 與我們研究的相關性
直接相關 — 建立了將 PM 任務分解為 LLM 編排 workflow 並結合確定性工具的範式。這是 PMAx 等框架建構的基礎。AgWf 範式意味著 token 效率的提升來自適當的任務分解（更簡單的子任務需要更少 reasoning token）和工具重用（確定性執行避免重複 LLM 推論）。

### 可移轉技術
- Workflow 分解作為 token 效率策略（複雜 → 簡單子任務）
- 確定性工具整合以減少 LLM 推理開銷
- CrewAI 框架用於多 agent PM 編排
- LLM 編排與 PM 計算的分離

---

## 論文 2：PMAx: An Agentic Framework for AI-Driven Process Mining（AI 驅動 Process Mining 的 Agentic 框架）
- **arXiv ID:** 2603.15351
- **作者:** Anton Antonov et al.
- **年份:** 2026
- **URL:** https://arxiv.org/abs/2603.15351

### 核心問題
Process mining 需要專業查詢語言和資料科學工具的專業知識，限制了可及性。將 LLM 作為直接分析引擎在原始 event log 上操作會引入 hallucination（幻覺）風險，且將敏感 log 發送至外部 AI 服務有隱私疑慮。

### 方法
PMAx 採用隱私保護的多 agent 架構，包含兩個專用 agent：(1) **Engineer agent** 分析 event log 元資料並自主生成本地腳本，執行既有 PM 演算法、計算精確指標、產出工件（流程模型、摘要表、視覺化）；(2) **Analyst agent** 詮釋這些工件以編纂綜合報告。所有計算在地執行，確保數學精確性和資料隱私。LLM 負責詮釋，不負責計算。

### 關鍵發現
透過將計算與詮釋分離，PMAx 在確保數學精確性的同時，讓非技術使用者能將高階業務問題轉化為可靠的流程洞察。在地執行消除了隱私疑慮。框架證明 LLM 更適合作為 PM 結果的詮釋者，而非直接分析引擎。

### 與我們研究的相關性
PMAx 的計算-詮釋分離是關鍵的 token 效率模式：LLM 生成程式碼（少量 token）→ 程式碼確定性執行（零 LLM token）→ LLM 詮釋結果（適量 token），而非試圖在原始 event log 上推理（大量 token 且有幻覺風險）。隱私保護的在地執行模式對敏感領域應用也很相關。

### 可移轉技術
- **計算-詮釋分離**: LLM 生成程式碼 → 程式碼執行 → LLM 詮釋結果
- **本地腳本生成**: LLM 撰寫 PM 分析腳本而非直接做 PM
- **多 agent 架構**: Engineer（程式碼生成）+ Analyst（詮釋）
- **隱私保護執行**: 所有敏感資料留在本地，只與 LLM 共享元資料
- **基於工件的溝通**: Agent 間交換結構化工件（表、模型、視覺化）而非原始資料

---

## 論文 3：De-Linearizing Agent Traces: Bayesian Inference of Latent Partial Orders for Efficient Execution (BPOP)（去線性化 Agent 軌跡：用於高效執行的潛在偏序貝氏推論）
- **arXiv ID:** 2602.02806
- **作者:** Dongqing Li, Zheqiao Cheng, Geoff K. Nicholls, Quyu Kong
- **年份:** 2026
- **URL:** https://arxiv.org/abs/2602.02806

### 核心問題
AI agent 以順序行動軌跡執行程序化 workflow，這掩蓋了潛在的並行性並導致重複的逐步推理。這種線性化效率不彰 — 如果知道底層依賴結構，許多步驟可以並行執行，但順序軌跡格式隱藏了這些結構。

### 方法
BPOP（Bayesian Partial Order from traces，從軌跡推論貝氏偏序）是一個貝氏框架，從有雜訊的線性化軌跡中推論潛在依賴偏序。它將軌跡建模為底層圖的 stochastic linear extension（隨機線性延伸），並透過 tractable frontier-softmax likelihood（可處理的前沿 softmax 概似）進行高效 MCMC 推論，避免了對線性延伸的 #P-hard 邊際化。在 Cloud-IaC-6（一套雲端佈建任務，含異質 LLM 生成軌跡）和 WFCommons 科學 workflow 上評估。

### 關鍵發現
BPOP 比純軌跡和 process mining baseline 更準確地恢復依賴結構。推論出的圖支援一個 compiled executor（編譯執行器），能修剪無關 context，大幅減少 token 使用量和執行時間。這證明去線性化 agent 軌跡是提升 agent 效率的可行策略。

### 與我們研究的相關性
高度相關 — BPOP 直接透過從 agent 軌跡推論潛在並行性並修剪不必要 context 來處理 token 效率。PM 的關聯是明確的：BPOP 將 PM 式的依賴發現應用於 LLM agent 軌跡。「compiled executor」概念（推論 workflow 的確定性執行）與結晶化模式一致。Token 減少來自基於依賴結構的 context 修剪。

### 可移轉技術
- **貝氏軌跡去線性化**: 從順序 agent 軌跡推論潛在偏序
- **Frontier-softmax 概似**: 避免 #P-hard 計算的可處理近似
- **透過依賴圖修剪 context**: 識別哪些 context 對每一步是無關的，減少 token 使用
- **Compiled executor**: 將推論出的依賴圖轉為確定性執行計畫
- **Cloud-IaC-6 benchmark**: 開源的雲端佈建任務套件用於評估
- **MCMC workflow discovery**: 流程模型發現的機率方法

---

## 論文 4：On the Potential of Large Language Models to Solve Semantics-Aware Process Mining Tasks（LLM 解決語義感知 Process Mining 任務的潛力）
- **arXiv ID:** 2504.21074
- **作者:** Adrian Rebmann, Fabian David Schmidt, Goran Glavaš, Han van der Aa
- **年份:** 2025
- **URL:** https://arxiv.org/abs/2504.21074

### 核心問題
Process mining 任務越來越需要理解活動的語義含義及其關係（例如從活動名稱推論依賴、從語義辨識異常行為）。LLM 能否利用其語義理解能力來解決這些語義感知 PM 任務？

### 方法
論文系統性地探索了 LLM 在五項語義感知 PM 任務上的能力，透過 in-context learning（語境中學習）和 supervised fine-tuning（監督式微調）兩種方式。作者定義了五項需要語義理解的任務（包括 process discovery、anomaly detection）並提供豐富的 benchmark 資料集。他們在 LLM 的預設狀態、加入語境範例、以及微調後三種設定下評估，涵蓋多種流程類型和產業。

### 關鍵發現
LLM 在開箱即用或僅加少量語境範例時，在具挑戰性的 PM 任務上表現不佳。然而，在跨多種流程類型和產業微調後，它們能達到強勁表現。這揭示了一個關鍵張力：LLM 具備語義理解潛力，但需要任務特定訓練才能解鎖。五任務 benchmark 提供了標準化評估框架。

### 與我們研究的相關性
與 token 效率問題直接相關：微調（高前置成本、低推論成本）vs. in-context learning（零前置成本、高推論成本且需大量範例）。五任務分類法幫助我們理解哪些 PM 任務受益於 LLM 語義理解、哪些需要確定性工具。Benchmark 資料集可用於評估 token 效率方法。

### 可移轉技術
- **五項語義感知 PM 任務**: 評估 LLM 式 PM 的標準化任務分類法
- **微調 vs. in-context learning 取捨**: 前置成本 vs. 推論成本分析
- **Benchmark 資料集**: 跨產業 PM 任務評估的豐富資料集
- **語義理解分類法**: 分類哪些 PM 任務受益於 LLM 語義能力
- **任務難度校準**: 將 LLM 能力匹配到 PM 任務複雜度

---

## 論文 5：Progressive Crystallization: Turning Agent Exploration into Deterministic, Lower-Cost Workflows in Production（漸進式結晶化：在生產環境中將 Agent 探索轉為確定性、更低成本的 Workflow）
- **arXiv ID:** 2607.07052
- **作者:** Arun Malik
- **年份:** 2026
- **URL:** https://arxiv.org/abs/2607.07052

### 核心問題
部署用於 IT 運維的 AI agent 是持續成本中心 — 每次執行都需要完整 LLM 推論，即使問題之前已解決。這使得 agent 方式在大規模時經濟上不可持續。

### 方法
漸進式結晶化定義了三階段執行分類：(1) 完全 agent 編排、(2) 混合、(3) 完全確定性 workflow。一個基於證據的晉升機制將反覆驗證過的 agent 行為轉換為更便宜、更可重現的確定性 workflow，同時自動將出現退化的 workflow 降級。系統在一個生產雲端網路 AIOps 系統上評估，該系統每月處理數萬起事件，為期八個月。

### 關鍵發現
此方法在八個月內將確定性執行比例從 0% 提升至 45%，儘管事件量翻倍，每事件 agent 成本降低超過 70%，並透過更高的可重現性和可稽核性提升安全性。晉升/降級機制確保結晶化 workflow 在系統演進時保持正確。經濟模型證明漸進式結晶化是讓 agent 系統在生產規模下具成本效益的可行策略。

### 與我們研究的相關性
我們 token 效率方向的核心論文 — 結晶化本質上是 token 成本攤提策略。初始探索（高 token 成本）被攤提到後續多次確定性執行（近零 token 成本）。三階段分類法（agent → 混合 → 確定性）直接對應 token 效率光譜。70% 成本降低為預期效益提供了強有力的實證基準。

### 可移轉技術
- **三階段執行分類法**: Agent → 混合 → 確定性（token 成本光譜）
- **基於證據的晉升**: 將驗證過的 agent 行為轉為確定性 workflow
- **自動降級**: 當確定性 workflow 退化時回退為 agent 執行
- **軌跡提取方法論**: 從 agent 執行軌跡提取 workflow 模式
- **經濟模型**: Agent vs. 確定性執行的成本比較
- **透過可重現性實現安全性**: 確定性 workflow 可稽核、可重複
- **70% 成本降低基準**: Token 效率方法的實證目標

---

## 論文 6：CacheRL: Multi-Turn Tool-Calling Agents via Cached Rollouts and Hybrid Reward（透過快取 Rollout 和混合獎勵實現多輪 Tool-Calling Agent）
- **arXiv ID:** 2606.14179
- **作者:** Md Amirul Islam, Sumiran Thakur, Huancheng Chen, Su Min Park, Jiayun Wang, Gyuhak Kim
- **年份:** 2026
- **URL:** https://arxiv.org/abs/2606.14179

### 核心問題
訓練小型 agent 模型執行多步 tool-calling 任務面臨三個挑戰：(1) 從大型模型大規模移轉 tool-calling 知識，(2) 在無需昂貴即時工具執行的情況下進行強化學習，(3) 從有雜訊的快取環境中穩健學習。

### 方法
CacheRL 引入三項創新：(1) **混合思考軌跡 pipeline**，用 LLM 生成的推理軌跡增強 agent 軌跡，教模型不僅呼叫什麼工具還有為什麼；(2) **CacheAgentLoop**，透過三層模糊快取消除即時執行成本，同時透過 token 級遮罩保留軌跡忠實度；(3) **Cache-tier-aware reward**，動態調整答案品質權重以避免因快取限制懲罰模型。訓練使用迭代 SFT 和 GRPO，基於 Qwen3-4B-Thinking。

### 關鍵發現
CacheRL 在多步 tool-calling 任務上達到 92% process accuracy（流程準確率），接近 GPT-5 的 94%，同時計算量少 100 倍。將 Qwen3-4B-Thinking 的驗證獎勵從 0.43 提升至 0.78。消融實驗顯示：移除知識移轉降低 41% 效能，cache-aware reward 貢獻 17% 提升。值得注意的是，RL 改善訓練穩定性但超越強 SFT 的增益有限，顯示資料品質和獎勵設計比複雜優化更重要。

### 與我們研究的相關性
CacheRL 直接處理 agent 訓練和執行中的 token 效率。三層模糊快取消除冗餘工具執行（類似結晶化但在 tool-call 層級）。相對前沿模型 100x 計算減少證明，經過良好訓練的小模型在結構化任務上能匹配大模型。SFT > RL 的發現對於成本效益訓練策略很重要。

### 可移轉技術
- **三層模糊快取**: 在不同粒度級別消除冗餘工具執行
- **混合思考軌跡**: 用推理增強軌跡（「為什麼」而不只是「什麼」）
- **Token 級遮罩**: 使用快取結果時保留軌跡忠實度
- **Cache-tier-aware reward**: 根據快取可靠性調整品質指標
- **SFT > RL 洞見**: 強監督式微調可能比複雜 RL 更具成本效益
- **小模型競爭力**: 4B 模型經適當訓練可匹配前沿模型
- **Process accuracy 指標**: 多步 tool-calling 的標準化評估

---

## 論文 7：Improving Hospital Process Management through Process Mining: A Case Study on COVID-19 Clinical Pathways（透過 Process Mining 改善醫院流程管理：COVID-19 臨床路徑案例研究）
- **arXiv ID:** 2606.00041
- **作者:** Pasquale Ardimento, Mario Luca Bernardi, Marta Cimitile, Samuele Latorre
- **年份:** 2026
- **URL:** https://arxiv.org/abs/2606.00041

### 核心問題
醫院流程，特別是 COVID-19 等複雜疾病的流程，涉及異質性臨床資料，難以分析。需要透明、可重現的 pipeline 將臨床資料轉換為 PM 就緒的 event log，以產出可行動的洞察。

### 方法
研究使用 COVID Data for Shared Learning 資料集，建構透明、可重現的 pipeline，將異質性臨床表格轉換為 PM 就緒的 event log。應用 discovery（流程發現）、declarative conformance checking（宣告式一致性檢查）和 outcome analysis（結果分析）來重建 COVID-19 照護路徑並分析變異性和結果。

### 關鍵發現
重建的路徑突顯了住院照護的 monitoring 主幹、急診-住院介面的變異性、以及由年齡和 ICU 暴露驅動的結果差異。這些洞察支援分流標準化、容量規劃和從 ICU 到低急性病房的轉銜協調。研究展示 PM 如何促進基於實證的醫院治理。

### 與我們研究的相關性
此論文提供了 PM 技術的具體應用領域。雖然不聚焦 LLM，但展示了真實 event log 的複雜性和 PM 洞察的價值。對我們的 token 效率研究而言，這代表了 LLM 輔助 PM 可以民主化分析的領域類型（如 PMAx 所設想）。異質資料轉換 pipeline 是 LLM 編排自動化的候選項目。

### 可移轉技術
- **異質資料 → event log pipeline**: 將原始領域資料轉為 PM 就緒格式的模板
- **宣告式 conformance checking**: discovery 的互補方法，用於合規分析
- **臨床路徑分析**: 領域特定的 PM 應用模式
- **基於結果的流程分析**: 將流程變體連結到結果（年齡、ICU 暴露）
- **醫院治理洞察**: PM 如何轉化為可行動的醫療管理
- **可重現 pipeline 設計**: 透明、可稽核的 PM pipeline 架構

---

## 綜合：這 7 篇論文告訴我們什麼

### 大格局

這七篇論文收斂到一個根本洞察：**PM 與 LLM 的未來不是用 LLM 取代 PM 工具，而是編排 LLM 來生成、執行和詮釋 PM workflow 並實現高效。** 文獻中浮現的關鍵模式：

1. **計算-詮釋分離** (PMAx, Berti): LLM 應該生成程式碼和詮釋結果，而非直接計算。這透過讓確定性工具處理計算來減少幻覺風險和 token 消耗。

2. **軌跡轉 Workflow** (BPOP, Progressive Crystallization): Agent 執行軌跡可被分析以發現潛在依賴結構，再轉換為確定性 workflow — 將未來 token 成本降低 70% 以上。

3. **小模型競爭力** (CacheRL): 經適當訓練的小模型（4B 參數）在結構化 PM 任務上能匹配前沿模型，計算量少 100 倍，特別是有快取和 SFT 支援時。

4. **語義理解差距** (Rebmann et al.): LLM 對流程活動有潛在語義理解能力，但解鎖需要微調。開箱即用的表現不足以應對複雜 PM 任務。

5. **領域應用驗證方法** (Ardimento et al.): 真實世界的臨床路徑分析展示了 PM 的價值和複雜性，推動 LLM 輔助 PM 工具的民主化。

### 最大的研究空白

最顯著的空白是**缺乏一個統一框架，在單一系統中連結軌跡分析、workflow 結晶化和 token 成本優化。** 每篇論文各解決一塊：

- BPOP 發現潛在依賴但未連結到漸進式結晶化
- Progressive Crystallization 將軌跡轉為 workflow 但未用 PM 技術做發現
- CacheRL 降低 tool-call 成本但未利用 PM 做 workflow 分析
- PMAx 分離計算與詮釋但未結晶化重複模式
- Rebmann et al. 探索 LLM 語義但未處理成本/效率

**沒有論文將 process mining（作為 agent 軌跡的分析方法）與 LLM token 效率（作為優化目標）結合。** 這就是我們研究可以定位的交集。

具體而言，目前沒有工作：
- 用 PM 技術分析 LLM agent 執行軌跡的效率模式
- 將 token 成本定義為 PM 驅動 workflow 優化中的一級指標
- 應用基於 PM 晉升標準的結晶化生命週期
- 評估不同 PM 任務分解策略下 LLM 推理品質與 token 成本的取捨

### 我們的定位策略

我們應將研究定位在三個流派的交集：

1. **用於 Agent 軌跡的 Process Mining**: 將 PM 技術（discovery、conformance checking、enhancement）應用於 LLM agent 執行軌跡 — 將 agent 軌跡視為 event log。這在方法論上很新穎：多數 PM 工作分析的是業務流程，而非 AI agent 行為。

2. **Token 效率作為 PM 優化目標**: 將 token 成本定義為流程效能指標，用 PM 式分析識別低效率（冗餘推理、不必要 context、可重複子任務）。這橋接了 PM（流程優化）和 LLM 效率（token 優化）之間的 gap。

3. **基於 PM 晉升標準的漸進式結晶化**: 用 PM 衍生指標（一致性、頻率、成功率）作為將 agent 行為晉升為確定性 workflow 的證據。這將結晶化決策建立於客觀流程分析而非 ad-hoc 閾值。

我們的貢獻：一個 PM 驅動的 LLM agent token 效率框架，(a) 用 PM 技術從 agent 軌跡發現 workflow，(b) 衡量每個 workflow 模式的 token 成本，(c) 將高頻率、高成本模式漸進式結晶化為確定性執行 — 在維持任務品質的同時減少 token 消耗。