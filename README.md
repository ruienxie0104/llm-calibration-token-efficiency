# LLM Calibration × Token Allocation × Process Mining

> 探討 LLM 自我評估校準品質與推理 Token 分配效率的關係 — 從 IRT-Based Self-Assessment 到 Budget-Aware Reasoning

## 研究概述

本專案延續學姐 LCAE 框架（Chen et al., IEEE IRI 2026），探討 LLM 自我評估的校準品質能否預測並優化推理 token 的分配效率。

**核心假設：** 校準好的模型不一定總 token 更少，但分配更合理 — 簡單題少 token、困難題多 token。在有限資源下，準確率損失更小。

**研究方法：** 結合 Item Response Theory (IRT)、Process Mining (PM)、以及受控 budget sweep 實驗，驗證校準品質與 token requirement 之間的因果鏈。

完整因果鏈：`IRT 難度/能力 → LCAE 校準 → Token Requirement 預測 → 動態 Allocation → Accuracy-Frontier 改善 → PM 機制診斷`

## 實驗歷程

| 階段 | 內容 | 狀態 |
|------|------|------|
| **V1 Pilot** | GSM8K 20 題 × 5 模型，驗證 PM 分析推理軌跡可行性 | ✅ 完成 |
| **V2** | MMLU+ARC 100 題 × 4 模型，加入信心校準指標 + PM 分析 | ✅ 完成（含 Rebuild） |
| **Deep Research** | 系統性競爭者分析（7/28，1612 行報告），方向收斂 | ✅ 完成 |
| **V3 Phase 2** | Budget Sensitivity Pilot — MATH-500 30 題 × 2 模型 × 4 budgets | ✅ 完成（Go） |
| **B: Confidence Test** | 確認 confidence prompt 在 budget 限制下正常運作 | ✅ 完成 |
| **C: Activity Labeling** | 匯出 100 段文字樣本供人工標註驗證 | ✅ 完成 |
| **V3 Phase 3** | 4 模型 × 60 題 × 3 budgets + IRT + LCAE 完整實驗 | 📝 腳本完成 |

## 專案結構

```
experiments/
├── v1-pilot/                    # GSM8K pilot (PM feasibility)
│   ├── pilot_real_experiment.py
│   ├── report/
│   └── slides.pptx
├── v2-mmlu-arc/                 # MMLU + ARC (with calibration + PM)
│   ├── experiment_v2.py
│   ├── run_pm_analysis.py
│   ├── run_entropy_step_analysis.py
│   ├── run_conformance_deepseek_ref.py
│   ├── generate_v2_figures.py
│   ├── rerun_confidence.py
│   ├── export_activity_label_sample.py
│   ├── annotation/              # Activity label definitions + review guide
│   ├── results/
│   │   ├── raw_responses_v2.json
│   │   ├── traces_final.json
│   │   ├── calibration_final.json
│   │   ├── conformance_final.json
│   │   ├── entropy_step_analysis.json
│   │   ├── full_metrics_final.csv
│   │   └── figures/             # 12 visualization figures
│   └── report/
│       ├── REPORT.md
│       ├── REPORT_zh-TW.md
│       └── figures/
├── v3-budget-pilot/             # Budget sensitivity experiment (current)
│   ├── run_pilot.py             # Phase 2: 2模型 × 30題 × 4 budgets
│   ├── run_confidence_test.py   # B: confidence mechanism test
│   ├── run_phase3.py            # Phase 3: 4模型 × 60題 × 3 budgets + IRT
│   ├── data/
│   │   ├── sampled_questions.json
│   │   └── phase3_questions.json
│   ├── results/
│   │   ├── results_final.json
│   │   ├── confidence_test.json
│   │   ├── phase3_raw.json      # (after execution)
│   │   └── ..._phase3.json      # (analysis outputs)
│   └── presentation-2026-08-28.html
docs/
├── zh-TW/
│   ├── deep-research-calibration-aware-token-allocation-2026-07-28.md
│   └── agent-handoff-2026-07-24.md
├── literature-survey-token-direction-2026-07-01.md
├── literature-survey-process-mining-2026-07-12.md
└── feasibility-analysis-2026-07-12.md
scripts/
├── check_environment.py
└── check_v2_results.py
tests/
├── test_v2_result_validation.py
├── test_activity_labeling.py
└── test_project_environment.py
public/
└── presentation.html
```

## V3 Phase 2 關鍵結果

| Budget | GPT-OSS-20B | DeepSeek | 差距 |
|--------|------------|----------|------|
| 128 | 0.0% | 0.0% | — |
| **256** | **3.3%** | **15.0%** | **5.0× 🏆** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

**核心發現：** 校準優勢在低 token 時最明顯。256 時 DeepSeek 15% vs GPT 3%（5 倍差），1024 時趨近。當 token 無限大家都差不多，但資源受限時校準好的模型更會把 token 用在對的地方。

## 環境設定

```bash
# Python 3.13 + uv
uv python install 3.13
uv venv --python 3.13 .venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt

# Graphviz (for PM4Py Petri net rendering)
brew install graphviz

# API key (只放本機 .env)
cp .env.example .env
# 編輯 .env 填入 OLLAMA_API_KEY
```

## 執行 V3 Phase 3

```bash
export OLLAMA_API_KEY="your-key"
uv run python3 experiments/v3-budget-pilot/run_phase3.py
```

## 論文定位

不同於現有 adaptive reasoning 方法（Think Just Enough、SelfBudgeter、Capability Calibration、Sonata）：

- 使用 **IRT/LCAE psychometric calibration** 而非 raw confidence
- **Training-free**、**black-box compatible**
- 配置 **single-trajectory reasoning length** 而非 sampling 次數
- 有 **IDS intervention** 建立因果驗證
- 以 **Process Mining** 做 allocation 的行為機制診斷

## Repositories

- GitHub (origin): https://github.com/ruienxie0104/llm-calibration-token-efficiency
- GitLab (mirror): https://datasci.mis.nsysu.edu.tw/ryan0104/llm-calibration-token-efficiency