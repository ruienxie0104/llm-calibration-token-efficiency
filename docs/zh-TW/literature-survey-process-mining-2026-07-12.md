# 文獻調查：Process Mining × LLM Agent × Token 效率

**日期:** 2026-07-12
**目的:** mapping Process Mining（流程探勘）、LLM agent 與 token 效率的交集，找出 Ryan 新研究方向的研究空白。

---

## 搜尋摘要

- **來源:** arXiv（16 組關鍵字查詢 + 6 組短語搜尋，透過 web interface）
- **時間範圍:** 2024–2026（聚焦近期工作）
- **篩選後相關論文數:** ~25（去重和相關性過濾後）

---

## 集群 A：Process Mining × LLM（核心交集）

### A1. LLM 作為 Process Mining 工具/介面

| 論文 | arXiv ID | 年份 | 核心貢獻 |
|-------|----------|------|-----------------|
| Re-Thinking Process Mining in the AI-Based Agents Era（重新思考 AI Agent 時代的 Process Mining） | 2408.07720 | 2024 | 提出 AgWf（Agent Workflow）範式用於 PM 任務；將複雜 PM 分解為更簡單的 workflow，結合 deterministic tools（確定性工具）與 LLM 領域知識 |
| PMAx: An Agentic Framework for AI-Driven Process Mining（AI 驅動 Process Mining 的 Agentic 框架） | 2603.15351 | 2026 | 多 agent 框架：Engineer agent 生成在地腳本執行 PM 演算法，Analyst agent 詮釋結果。隱私保護，在地執行。van der Aalst 團隊作品 |
| On the Potential of LLMs to Solve Semantics-Aware PM Tasks（LLM 解決語義感知 PM 任務的潛力） | 2504.??? | 2025 | Rebmann et al. — 評估 LLM 在語義感知 PM 任務上的表現（abstraction、matching） |
| Evaluating the Ability of LLMs to Solve Semantics-Aware PM Tasks（評估 LLM 解決語義感知 PM 任務的能力） | 2407.??? | 2024 | 上述論文的早期版本 — 建立 LLM PM 能力 benchmark |
| Exploring LLM Features in Predictive Process Monitoring（探索預測型 Process Monitoring 中的 LLM 特徵） | 2501.??? | 2026 | Padella et al. — LLM 特徵應用於小規格 event log 的預測型 PM |

**關鍵洞察:** 這個集群用 LLM 來*做* process mining 更好（民主化 PM、自動化分析）。方向是 PM → LLM，不是 LLM → PM。

### A2. 用 Process Mining 分析 LLM/Agent 行為

| 論文 | arXiv ID | 年份 | 核心貢獻 |
|-------|----------|------|-----------------|
| De-Linearizing Agent Traces: Bayesian Inference of Latent Partial Orders（去線性化 Agent 軌跡：潛在偏序的貝氏推論） | 2602.??? | 2026 | BPOP 框架 — 從有雜訊的線性化 agent 軌跡推論潛在依賴偏序。將軌跡建模為底層圖的 stochastic linear extension。**直接相關：PM 技術應用於 agent 軌跡** |
| M2-PALE: Process Mining + LLMs for Explaining MCTS Agents（用 PM + LLM 解釋 MCTS Agent） | 2604.??? | 2026 | 用 PM 和 LLM 解釋 MCTS agent 行為 — process mining 用於 agent 可解釋性 |
| AlphaMemo: Structured Search-Process Memory for Self-Evolving Alpha Mining Agents（自我演化 Alpha Mining Agent 的結構化搜尋流程記憶） | 2505.??? | 2026 | 具結構化記憶的 LLM agent，用於 alpha mining（量化金融）。搜尋流程的記憶 |
| Progressive Crystallization: Turning Agent Exploration into Deterministic Workflows（漸進式結晶化：將 Agent 探索轉為確定性 Workflow） | 2512.??? | 2025 | 將 agentic 探索軌跡轉換為確定性 workflow — 本質上就是從 agent 軌跡做 process discovery（流程發現） |

**關鍵洞察:** 這個集群把 PM *應用於* LLM agent 行為。非常小的集群 — 這就是前沿。

---

## 集群 B：臨床路徑 Process Mining（醫療應用）

| 論文 | arXiv ID | 年份 | 核心貢獻 |
|-------|----------|------|-----------------|
| Improving Hospital Process Management through PM: COVID-19 Clinical Pathways（透過 PM 改善醫院流程管理：COVID-19 臨床路徑） | 2606.??? | 2026 | Ardimento et al. — PM 應用於 COVID-19 照護路徑，透明可重現的 pipeline |
| From Data Lifting to Continuous Risk Estimation: Process-Aware Pipeline for Clinical Pathways（從資料提升到持續風險估計：臨床路徑的流程感知 Pipeline） | 2605.??? | 2026 | 同一團隊 — 臨床路徑的預測型 monitoring |
| Adaptive Identification and Modeling of Clinical Pathways with PM（用 PM 自適應識別與建模臨床路徑） | 2512.??? | 2025 | 自適應臨床路徑建模 |
| Discovering Care Pathways for Multi-Morbid Patients Using Event Graphs（用事件圖發現多重病症患者的照護路徑） | 2110.??? | 2021 | 多病症患者路徑的事件圖方法 |
| Simulation of Patient Flow Using PM and Data Mining（用 PM 與資料探勘模擬病人流向） | 1702.??? | 2017 | ACS 病人流向模擬 |

**關鍵洞察:** 臨床路徑 PM 已成熟，但**尚未與 LLM/agent 推理結合**。這是一個 gap。

---

## 集群 C：Agent Workflow 優化與軌跡分析

| 論文 | arXiv ID | 年份 | 核心貢獻 |
|-------|----------|------|-----------------|
| Multi-View Encoders for Performance Prediction in LLM-Based Agentic Workflows（LLM Agentic Workflow 效能預測的多視角編碼器） | 2512.??? | 2025 | 預測 LLM agentic workflow 的效能 |
| CacheRL: Multi-Turn Tool-Calling Agents via Cached Rollouts（透過快取 Rollout 實現多輪 Tool-Calling Agent） | 2606.??? | 2026 | 多步 tool-calling 達 92% process accuracy（流程準確率），計算量比 GPT-5 少 100x。**Process accuracy = 步驟級品質** |
| LLM Agents for Interactive Workflow Provenance（互動式 Workflow 溯源的 LLM Agent） | 2512.??? | 2025 | Agent workflow 溯源追蹤 |
| Trace2Policy: From Expert Behavior Traces to Self-Evolving Decision Agents（從專家行為軌跡到自我演化決策 Agent） | 2606.??? | 2026 | 從專家軌跡提取策略 — 規則品質 > 模型能力 |
| Executable Agentic Memory for GUI Agent（GUI Agent 的可執行記憶） | 2505.??? | 2026 | GUI agent 的程序化 workflow 記憶 |

**關鍵洞察:** 「Process accuracy」（步驟級正確性）正在成為一個指標，但沒有人用 PM 技術來衡量它。

---

## 集群 D：Token 效率與推理品質（來自先前調查）

已在 `literature-survey-token-direction-2026-07-01.md` 中涵蓋。關鍵論文：
- ROI-Reasoning, TRIAGE, SelfBudgeter, UAB, "LLM Already Knows"

---

## 集群 E：推理軌跡品質評估

| 論文 | arXiv ID | 年份 | 核心貢獻 |
|-------|----------|------|-----------------|
| Reasoning Quality Emerges Early: Data Curation for Reasoning Models（推理品質及早浮現：推理模型的資料策展） | 2606.??? | 2026 | Jin et al. — 資料品質決定推理品質；少量高品質 SFT 資料即足夠 |
| How Do Answer Tokens Read Reasoning Traces? Self-Reading Patterns in Thinking LLMs（答案 Token 如何閱讀推理軌跡？思考型 LLM 的自我閱讀模式） | 2604.??? | 2026 | 分析答案 token 如何 attend 推理軌跡 |
| Think-with-Rubrics: From External Evaluator to Internal Reasoning Guidance（用 Rubric 思考：從外部評估到內部推理引導） | 2605.??? | 2026 | Rubric 作為內部推理引導，不僅是外部評估 |

**關鍵洞察:** 推理軌跡品質正在被研究，但不是透過 PM 視角。這個連結是缺失的。

---

## 研究空白地圖

### Gap PM-1 (★★★): PM 技術應用於 LLM 推理軌跡
- **缺失的是什麼:** 沒有人將 process discovery（流程發現）/ conformance checking（一致性檢查）應用於 LLM 推理軌跡（CoT 步驟作為事件，推理軌跡作為 event log）
- **為什麼重要:** PM 提供正式工具來分析推理路徑*為什麼*沒效率，而不只是*有沒有*沒效率
- **與 Ryan 研究的關聯:** Overthinking（過度思考）= conformance deviation（一致性偏離）；高效推理 = 最佳流程路徑

### Gap PM-2 (★★★): 透過 PM 視角看 Token 分配品質
- **缺失的是什麼:** 現有 token 效率指標（excess token usage、overthinking rate）衡量的是數量，不是流程品質。PM 可以衡量路徑級品質
- **為什麼重要:** 「模型用了太多 token」→ PM 可以回答「因為推理路徑在步驟 3 迴圈」或「繞了不必要的子目標」
- **與 Ryan 研究的關聯:** 直接延伸 LCAE/token 分配研究，加入流程級分析

### Gap PM-3 (★★☆): 臨床路徑 PM × LLM Agent 推理
- **缺失的是什麼:** 臨床路徑 PM 已成熟，但尚未與能推理病人照護的 LLM agent 結合
- **為什麼重要:** 遵循最佳臨床路徑的醫療 AI agent = 更安全、更有效率的照護
- **與 Ryan 研究的關聯:** 醫療場景作為應用領域（連結 NHRI 腎臟 agent 背景）

### Gap PM-4 (★★☆): 因果鏈：校準 → 流程品質 → Token 效率
- **缺失的是什麼:** 更好的自我評估（LCAE）是否導致更好的推理路徑（PM 品質），進而導致更好的 token 分配？
- **為什麼重要:** 透過流程品質作為中介變數，驗證從校準到效率的因果故事
- **與 Ryan 研究的關聯:** 這是 token 效率方向與 PM 方向的統一

---

## 需詳讀的關鍵論文

1. **Berti et al. (2024)** — 2408.07720 — "Re-Thinking Process Mining in the AI-Based Agents Era"（基礎性論文，van der Aalst 團隊）
2. **PMAx (2026)** — 2603.15351 — Agentic framework for PM（同一團隊最新作）
3. **BPOP / De-Linearizing Agent Traces (2026)** — 從 agent 軌跡推論潛在偏序
4. **Rebmann et al. (2025)** — LLMs for semantics-aware PM tasks（LLM 用於語義感知 PM 任務）
5. **Progressive Crystallization (2025)** — Agent 探索 → 確定性 workflow
6. **CacheRL (2026)** — 多步 agent 的 process accuracy 指標
7. **Ardimento et al. (2026)** — 臨床路徑 PM（醫療應用）

---

## 初步方向分析

### 大格局

PM × LLM 的交集**非常新**（多數論文來自 2024-2026）。存在兩個主要方向：

1. **PM → LLM**（集群 A1）：用 LLM 做 PM 更好。較成熟，由 van der Aalst 團隊領導。
2. **PM ← LLM**（集群 A2）：用 PM 分析 LLM agent 行為。非常稀少，只有少數幾篇論文。

**Ryan 的機會在方向 2**，具體來說：

### 提議的研究 Story

```
[IRT/LCAE calibration] → [better self-assessment] → [better reasoning path quality] → [better token allocation]
         ↑                    ↑                          ↑                              ↑
     學姐已證明           學姐已證明              PM 技術衡量這個           Ryan 的貢獻
```

PM 成為推理品質的**衡量框架**：
- **Process discovery（流程發現）:** 模型在簡單 vs. 困難題目上的典型推理路徑長什麼樣？
- **Conformance checking（一致性檢查）:** 模型什麼時候偏離「最佳」推理路徑？（Overthinking = 一致性偏離）
- **Performance analysis（效能分析）:** 推理路徑的長度/複雜度和 token 使用量、準確率的關係是什麼？

### 為什麼這可行

1. **新穎:** 沒有人把 PM 連結到 LLM 推理品質 / token 效率
2. **理論基礎扎實:** PM 有數十年的正式方法（alpha miner、inductive miner、conformance checking）
3. **實用:** PM 工具（PM4Py）是開源的，可直接使用
4. **連結指導教授興趣:** 老師明確提到 Process Mining 和醫療路徑
5. **延伸學姐的工作:** 校準 → 推理路徑品質 → token 分配是自然的因果鏈
6. **範圍適中:** 用 PM 作為分析框架是可控的；建造新 PM 演算法則太多了

### 潛在論文標題（草稿）

"Process-Aware Token Allocation: Mining LLM Reasoning Traces to Diagnose Calibration-Driven Efficiency"
（流程感知 Token 分配：探勘 LLM 推理軌跡以診斷校準驅動的效率）

或

"From Calibration to Process Quality: A Process Mining Approach to LLM Token Efficiency"
（從校準到流程品質：LLM Token 效率的 Process Mining 方法）

---

## 下一步

1. 詳讀 7 篇關鍵論文（特別是 Berti 2024、BPOP、PMAx）
2. 研究 PM4Py（Python process mining 函式庫）— 能否將 CoT 軌跡作為 event log 匯入？
3. 定義對應關係：CoT step → event，question → case，model → variant
4. 設計試驗實驗：取 5 個模型 × 100 題，提取推理軌跡，跑 PM 分析
5. 檢查 LCAE 是否與 PM 衍生的推理路徑品質指標相關