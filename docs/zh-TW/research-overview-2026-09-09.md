# LLM 校準 × Token Allocation × Process Mining — 完整研究紀錄

> **研究主題：** 探討 LLM 自我評估的校準品質與推理 Token 分配效率之間的關係
> **研究脈絡：** 延續學姐 LCAE 框架（Chen et al., IEEE IRI 2026），引入 Process Mining 分析推理軌跡
> **最後更新：** 2026-09-09（Phase 3 執行中）
> **GitLab：** https://datasci.mis.nsysu.edu.tw/ryan0104/llm-calibration-token-efficiency
> **GitHub：** https://github.com/ruienxie0104/llm-calibration-token-efficiency

---

## 一、研究起源：從學姐的 LCAE 框架出發

### 學姐論文回顧

Chen et al. (IEEE IRI 2026) 提出了 **LCAE（Latent Confidence Alignment Error）** 框架，核心方法是使用 **IRT（Item Response Theory）的 Rasch Model**：

$$P(\text{模型 m 答對題目 i}) = \sigma(\theta_m - \beta_i)$$

- $\theta_m$：模型 m 的 latent ability（能力）
- $\beta_i$：題目 i 的 latent difficulty（難度）
- $\sigma$：logistic function

這把模型能力和題目難度放在同一把尺上，可以客觀計算出模型在每題的答錯機率。

**三階段框架：**

| 階段 | 內容 | 關鍵發現 |
|------|------|---------|
| Stage 1：IRT 能力估計 | Rasch Model 估計 θ 與 β | 客觀計算答錯機率 |
| Stage 2：自我評估 | QOQ / IDS / DPR / Combined 四種情境 | **IDS（給難度訊號）最有效**；改善校準不傷能力 |
| Stage 3：模型選擇 | LCAE 比較自估 vs IRT 客觀估計 | **能力強 ≠ 自評準**；提及 cost 關聯但未深入 |

**核心發現：** GPT-5 能力最強但自評校準不是最好的，Llama 3 70B 自評反而最準。

### 我的研究問題

學姐回答了「模型知不知道自己的實力」，我進一步問：

> **知道自己會不會 → 能否知道自己需要思考多久？**
> **校準品質 → Token 分配效率？**

**核心假設：** 校準好的模型不一定總 token 更少，但分配更合理——簡單題少 token、困難題多 token。在有限資源下，準確率損失更小。

### 引入 Process Mining（流程挖掘）

為了分析推理軌跡的「結構」，引入 Process Mining。將模型的 CoT 文字切成活動序列（understand / recall / plan / calculate / reason / evaluate / verify / reconsider / answer），用 pm4py 做流程分析，可以看到：

- 是先理解還是直接算？
- 有沒有驗證步驟？
- 有沒有回頭修正？
- 不同模型的推理結構差異

---

## 二、初步實驗：V1 → V2

### V1：Process Mining 可行性驗證

| 項目 | 設定 |
|------|------|
| 題目 | 20 題 GSM8K 小學數學 |
| 模型 | 5 個（GPT-20B/120B, DeepSeek, GLM-4.7, GLM-5.2） |
| 活動類型 | 8 種 |
| 信心 | 未收集 |

**發現：** Process Mining 能區分推理風格——直覺型（DeepSeek）、系統型（120B）、掙扎型（20B），三種風格跨實驗穩定。

**限制：**
- ❌ 題目太簡單（95-100% acc），零變異量
- ❌ 無信心數據，無法驗證校準

### V2：加入校準指標

| 面向 | V1 | V2 |
|------|----|----|
| 題目 | 20 GSM8K | 100（MMLU STEM 50 + ARC 50） |
| 模型 | 5 | 4（GLM-4.7 退休） |
| 活動 | 8 種 | 9 種（+ evaluate） |
| 信心 | 無 | 多輪對話式 0-100% |
| 校準 | 無 | Brier, 信心差距 |
| PM | Petri net | Petri net + 熵 + JSD |

**信心 prompt 教訓：** 最初無上下文問「你有多確定」→ DeepSeek 回 2%（失真）。改成多輪對話式 → 99%。無上下文的信心 prompt 會產生完全失真的數據——這本身就是一個 methodology finding。

### V2 Rebuild：Bug 修正與數據翻轉

執行後發現多個 bug，做了完整 rebuild：

| Bug | 原本問題 | 修正 |
|-----|---------|------|
| Conformance | 讀取不存在欄位 → alignment 全 0 | 只計 log/model move |
| Levenshtein | (A,B) 和 (B,A) 分別抽樣 → 非對稱 | 對稱寫入 |
| JSD | distance 被標成 divergence | distance² = divergence |
| Confidence | 只傳 response 沒傳 thinking | 完整上下文 |

**影響：** 修正後數據完全不同——GPT-20B 從 56% 跳到 98%，信心差距全部縮小到趨近於零。前一版「信心差距與準確率反相關」的核心發現被推翻。

V2 作為校準分析價值下降，但 PM pipeline 驗證成功。更重要的是暴露了 prompt sensitivity、confidence scarcity、Petri net flower model 等問題，後續實驗不會重複犯錯。

---

## 三、文獻調查與方向收斂（7/28 Deep Research）

### 競爭者分析

| 競爭者 | 發表 | 已證明 | 我們能差異化之處 |
|--------|------|--------|----------------|
| **Think Just Enough** (Kim) | EACL 2026 | Verbalized confidence → stopping signal | 信心未校準 → 我們比較 raw vs calibrated |
| **SelfBudgeter** (Li) | ACL 2026 | 模型預估 budget + RL | 需 training → 我們 training-free |
| **CAT** (Jiang) | ACL Industry | Confidence-adaptive + preference opt | 需 token distribution → 我們 black-box |
| **Capability Cal.** (Yang) | arXiv 2026 | Calibration → best-of-k allocation | 配置 sampling 次數 → 我們配置 reasoning length |
| **Sonata** (Apple) | ICLR 2026 | Hidden-state adapter 預測 consistency | 需 hidden states → 我們 verbalized |
| **Berti / PM4GRPO** | TechRxiv 2025 | PM 分析 LLM reasoning | PM 定位為 diagnosis，非主要 novelty |

### 論文定位收斂

**核心命題：**
> 現有研究已證明 confidence 可控制推理長度，但通常假設 confidence 夠可靠。本研究改問：真正決定配置效果的，是否是 confidence 的校準品質本身？

**完整因果鏈：**
```
IRT 難度/能力 → LCAE 校準 → Token Requirement 預測 → 動態 Allocation → Accuracy-Frontier 改善 → PM 診斷
```

**差異化總結：**

| 面向 | 競爭者 | 本研究 |
|------|--------|--------|
| 校準方法 | raw confidence / hidden state | **IRT/LCAE psychometric** |
| 訓練需求 | SFT + RL / preference opt | **Training-free** |
| 模型存取 | hidden states / logits | **Black-box** |
| 配置對象 | sampling 次數 | **Reasoning length** |
| 因果驗證 | cross-model correlation | **IDS intervention** |
| 機制分析 | 只看 token 總量 | **PM activity-level** |

---

## 四、V3 Budget Sensitivity Pilot（Phase 2）

### 實驗設計

| 參數 | 設定 |
|------|------|
| 題目 | 30 題 MATH-500（Level 3-5 各 10） |
| 模型 | GPT-OSS-20B（校準差）vs DeepSeek（校準好） |
| Budgets | 128 / 256 / 512 / 1024 tokens |
| 重複 | 每條件 2 次 replicate |
| API 控制 | Ollama num_predict（真正事前限制） |
| 總呼叫 | 480 次 |

### 主要結果

| Budget | GPT-OSS-20B | DeepSeek | 差距 |
|--------|------------|----------|------|
| 128 | 0.0% | 0.0% | — |
| **256** | **3.3%** | **15.0%** | **5.0× 🏆** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

### 逐題對決

30 題中：
- **8 題** DeepSeek 比 GPT 省 token 就答對（例：L4 Algebra，DS 256 答對、GPT 要 1024，差 4 倍）
- **1 題** GPT 比 DeepSeek 省（L4 Number Theory）
- **1 題** DeepSeek 做到但 GPT 連 1024 都做不到（L5 Algebra）

### 結論

✅ **Budget sensitivity 存在** — MATH-500 L3-5 難度剛好，128→1024 穩定爬升
✅ **DeepSeek 全勝** — 256 差 5 倍、1024 趨近 1.2 倍
✅ **校準優勢在低 token 時最明顯** — 論文核心論點有初步支持

⚠️ 只有 2 個模型，無法區分校準 vs 模型能力的 confound
⚠️ 沒有信心收集，還不能驗證因果鏈

---

## 五、B + C：信心測試與活動標註

### B：Confidence Test（✅ 通過）

| 模型 | 答對時信心 | 答錯時信心 | 有無區分力 |
|--------|-----------|-----------|-----------|
| GPT-OSS-20B | **97** | **70** | ✅ 差 27 分 |
| DeepSeek | **100** | **99** | ❌ 幾乎無差 |

**結果：** Confidence prompt 正常運作，可直接用在 Phase 3。

### C：Activity Labeling（✅ 匯出）

- 已匯出 100 段文字樣本至 `experiments/v2-mmlu-arc/results/activity_label_sample.csv`
- 4 模型各 25 段，等人工標註驗證

---

## 六、Phase 3：決定性實驗（執行中）

### 設計

| 參數 | 設定 | 目的 |
|------|------|------|
| 模型 | 4 個（+GPT-120B, +GLM-5.2） | 區分校準 vs 能力的 confound |
| 題目 | 60 題 MATH-500 L3+L4 | 剔除太難的 L5 |
| Budgets | 256 / 512 / 1024 | 剔除 128（0% 無資訊量） |
| 信心 | 每題答完立刻問 | 驗證校準品質與 requirement 的關係 |
| 重複 | 3 次 replicate | 提高高 budget 穩定度 |
| 總呼叫 | 4×60×3×3×2 = 4320 次 | 約 1-2 小時 |

### 執行進度（即時更新）

最新進度：**400 / 4320（9.3%）**

| 模型 | Budget 256 | Budget 512 | Budget 1024 |
|------|-----------|-----------|------------|
| GPT-OSS-20B | ✅ 0/180 = 0% | ⏳ 7/20 = 35% | ❌ 未開始 |
| GPT-OSS-120B | ❌ 未開始 | ❌ 未開始 | ❌ 未開始 |
| DeepSeek | ❌ 未開始 | ❌ 未開始 | ❌ 未開始 |
| GLM-5.2 | ❌ 未開始 | ❌ 未開始 | ❌ 未開始 |

### 預期產出

| 檔案 | 內容 |
|------|------|
| `phase3_raw.json` | 所有 4320 次 API 原始回應（含續跑用） |
| `budget_sensitivity_phase3.json` | 每模型 × budget 的準確率 |
| `calibration_phase3.json` | Brier、信心差距（分 budget） |
| `irt_phase3.json` | θ（模型能力）、β（題目難度）、LCAE |

### 關鍵預測

如果 GLM-5.2（校準最好）在低 budget 勝 DeepSeek，且 GPT-120B（中等校準）接近 GPT-20B → **校準是獨立的解釋變數**。
如果只是模型大小在排序 → **方向需要調整**。

---

## 七、專案結構

```
llm-calibration-token-efficiency/
├── experiments/
│   ├── v1-pilot/                    # GSM8K pilot（PM feasibility）
│   │   ├── pilot_real_experiment.py
│   │   ├── report/
│   │   └── slides.pptx
│   ├── v2-mmlu-arc/                 # MMLU + ARC（校準 + PM）
│   │   ├── experiment_v2.py
│   │   ├── run_pm_analysis.py
│   │   ├── run_entropy_step_analysis.py
│   │   ├── run_conformance_deepseek_ref.py
│   │   ├── generate_v2_figures.py
│   │   ├── rerun_confidence.py
│   │   ├── export_activity_label_sample.py
│   │   ├── annotation/
│   │   ├── results/                 # 12 張圖 + 校準/PM 數據
│   │   └── report/                  # 雙語報告（EN + zh-TW）
│   └── v3-budget-pilot/             # 現行實驗
│       ├── run_pilot.py             # Phase 2（已跑完）
│       ├── run_confidence_test.py   # B 測試（已跑完）
│       ├── run_phase3.py            # Phase 3（執行中）
│       ├── data/                    # 題目清單
│       ├── results/                 # 實驗結果
│       ├── presentation-*.html      # 簡報
│       └── speaker-notes-*.md       # 講稿
├── docs/
│   ├── zh-TW/
│   │   ├── deep-research-*.md       # 7/28 文獻調查（1612 行）
│   │   └── agent-handoff-*.md       # 環境交接文件
│   ├── literature-survey-*.md
│   └── feasibility-analysis-*.md
├── scripts/                         # 環境檢查 + 結果驗證
├── tests/                           # pytest 測試
└── public/
    └── presentation.html            # 線上簡報
```

---

## 八、參考文獻

1. Chen, T.-Y. et al. (2026). Latent Confidence Alignment for LLM Self-Assessment. *IEEE IRI 2026.*
2. Kim, J., Lee, S.-G., & Kim, T. (2026). Think Just Enough: Leveraging Self-Assessed Confidence for Adaptive Reasoning. *EACL 2026.*
3. Li, Z. et al. (2026). SelfBudgeter: Adaptive Token Allocation for Efficient LLM Reasoning. *ACL 2026.*
4. Yang, S.-H. et al. (2026). On Calibration of Large Language Models: From Response to Capability. *arXiv 2602.13540.*
5. Han, T. et al. (2025). Token-Budget-Aware LLM Reasoning. *ACL 2025.*
6. Li, P. et al. (2026). Adaptive Thinking: LLMs Know When to Think in Latent Space. *ICLR 2026 / Apple ML Research.*
7. Al Nazi, Z. & Roy Dipta, S. (2026). TRIAGE: Evaluating Prospective Metacognitive Control in LLMs. *arXiv 2605.13414.*
8. Zhao, M. et al. (2026). ROI-Reasoning: Rational Optimization for Inference via Meta-Cognition. *arXiv 2601.03822.*
9. Berti, A. et al. (2025). Configuring Large Reasoning Models using Process Mining. *TechRxiv.*
10. Park, T. et al. (2025). Reasoning-Aware GRPO using Process Mining. *arXiv 2510.25065.*
11. van der Aalst, W. (2016). Process Mining: Data Science in Action. *Springer.*