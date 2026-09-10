# 研究進度完整總覽（2026-09-10）

> 從研究動機到最新實驗結果的完整記錄
> 已執行：V1 → V2 → V3 Phase 2 → B+C → V3 Phase 3 → IDS → PM 分析

---

## 一、研究動機與核心問題

### 背景

LLM 推理消耗大量 token，每個 API 呼叫都有成本。現有 adaptive reasoning 研究（如 Think Just Enough）假設模型對自己的信心可以直接作為推理深度的控制信號，但這個假設的基礎——模型信心的校準品質——本身很少被檢驗。

### 核心研究問題

> LLM 自我評估的校準品質，能否預測並改善推理 Token 的分配效率？

### 核心假設

校準好的模型不一定在無限制下使用更少 token，但分配更合理——簡單題少 token、困難題多 token。在有限資源下，準確率損失更小。

### 使用的方法

- **Brier Score**：傳統校準指標，比較信心與單次對錯
- **LCAE（IRT-based）**：學姐方法，同時考慮模型能力 θ 與題目難度 β
- **Controlled Budget Sweep**：我們原創的實驗設計，固定 token 預算比較模型表現
- **Process Mining**：分析推理軌跡的活動序列與結構

---

## 二、實驗歷程與結果

### 2.1 V1 Pilot（7 月初）

| 項目 | 設定 |
|------|------|
| 題目 | 20 GSM8K（小學數學） |
| 模型 | 5 個 |
| 信心 | 未收集 |

**結果：** PM 能區分三種推理風格（直覺型/系統型/掙扎型），但題目太簡單（95-100% acc），無變異量。

### 2.2 V2（7 月中）

| 改動 | 說明 |
|------|------|
| 題目 | 100 題（MMLU STEM + ARC） |
| 信心 | 加入多輪對話式自評 |
| 校準 | Brier、信心差距 |
| PM 分析 | Petri net + 熵 + JSD |

**V2 Rebuild：** 執行後發現多個 bug（conformance、Levenshtein、JSD、confidence），修正後數據完全不同——GPT-20B 從 56% 跳到 98%，前一版核心發現被推翻。

**教訓：** PM pipeline 驗證成功，暴露了 prompt sensitivity、confidence scarcity 等後續可避免的問題。

### 2.3 7/28 Deep Research

1612 行文獻調查，確認競爭者狀況：

| 競爭者 | 已證明 | 我們可差異化 |
|--------|--------|------------|
| Think Just Enough (EACL 2026) | confidence → stopping signal | 信心未校準 vs IRT-calibrated |
| SelfBudgeter (ACL 2026) | 預估 budget + RL | 需要 training vs training-free |
| Capability Calibration (arXiv 2026) | 校準→best-of-k | sampling 次數 vs reasoning length |
| Sonata (ICLR 2026) | hidden-state adapter | 需 hidden states vs black-box |
| **R³-Bench (arXiv 2026-08)** | 共享預算下評估資源理性 | 無校準分析/無 IRT/無 IDS |

### 2.4 V3 Phase 2 — Budget Sensitivity Pilot

2 模型 × 30 題 × 4 budgets × 2 reps = **480 calls**

| Budget | GPT-OSS-20B | DeepSeek | 差距 |
|--------|------------|----------|------|
| 128 | 0.0% | 0.0% | — |
| **256** | 3.3% | **15.0%** | **5×** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

**結論：** Budget sensitivity 存在、DeepSeek 全勝。但只有 2 模型無法區分校準 vs 能力。

### 2.5 B + C — 信心測試 + 活動標註

**B（信心測試）：** 確認 confidence prompt 正常運作。
- GPT-20B：答對 97 / 答錯 70（可區分 ✅）
- DeepSeek：答對 100 / 答錯 99（overconfident）

**C（活動標註）：** 匯出 100 段文字樣本，待人工驗證。

### 2.6 V3 Phase 3 — 決定性實驗

4 模型（GPT-20B、GPT-120B、DeepSeek、GLM-5.2）× 60 題（MATH-500 L3+L4）× 3 budgets（256/512/1024）× 3 reps = **4320 calls**

#### Budget Sensitivity

| 模型 | @256 | @512 | @1024 | Acc@1024 | 能力 θ | LCAE |
|------|-------|-------|--------|---------|-------|------|
| GPT-20B | 0.0% | 19.4% | 48.3% | 48.3% | −0.09 | 0.341 |
| GPT-120B | 0.0% | 17.2% | 50.6% | 50.6% | +0.00 | **0.247 🏆** |
| **DeepSeek** | **18.3%** | **49.4%** | **66.1%** | **66.1%** | **+0.65** 🏆 | 0.303 |
| GLM-5.2 | 0.0% | 4.4% | 36.7% | 36.7% | −0.57 | 0.438 |

#### 關鍵發現

| 發現 | 說明 |
|------|------|
| **能力 θ ≠ 校準 LCAE** | DeepSeek 能力最強（θ=+0.65）但 LCAE 不是最好；GPT-120B 能力中等但校準最好（LCAE=0.247） |
| **Brier vs LCAE 排名不同** | Brier 看 DeepSeek 最好（0.284），LCAE 看 GPT-120B 最好（0.247）→ 選擇指標影響判斷 |
| **信心差距可做代理指標** | GPT-120B（+25.5）> DeepSeek（+15.5）> GPT-20B（+7.3）> GLM-5.2（+3.4）— 與 LCAE 排序一致 |
| **GLM-5.2 是最大但最差** | 756B MoE，但能力最低（θ=−0.57）、校準最差（LCAE=0.438） |

### 2.7 IDS Intervention

2 模型（GPT-120B、DeepSeek）× 2 條件（QOQ、IDS）× 2 budgets × 3 reps × 30 題 = **1440 calls**

#### 主要結果

| 模型 | 條件 | Budget | 準確率 | Brier | 答對信心 | 答錯信心 |
|------|------|--------|-------|-------|---------|---------|
| GPT-120B | QOQ | 256 | 0.0% | 0.471 | 0% | 56% |
| GPT-120B | IDS | 256 | 0.0% | 0.432 ✅ | 0% | 51% ✅ |
| GPT-120B | QOQ | 512 | 27.8% | 0.403 | 97% | 62% |
| GPT-120B | IDS | 512 | 27.8% | **0.370** ✅ | 98% | 59% ✅ |
| DeepSeek | QOQ | 256 | 34.4% | 0.479 | 100% | 76% |
| DeepSeek | IDS | 256 | 30.0% | 0.485 | 100% | **71%** ✅ |
| DeepSeek | QOQ | 512 | 57.8% | 0.273 | 100% | 73% |
| DeepSeek | IDS | 512 | 60.0% | 0.266 ✅ | 100% | 72% |

#### IDS 結論

| 效果 | 結果 |
|------|------|
| 校準改善？ | ✅ GPT-120B Brier ↓, 答錯信心 ↓；DeepSeek 答錯信心 ↓ |
| 準確率提升？ | ❌ 無顯著變化 |
| 因果鏈成立？ | ❌ 校準改善未轉換成準確率提升 |

### 2.8 PM 分析 — 為什麼 IDS 沒有效果

#### 低預算下模型被強制截斷

| 模型 | @256 平均步數 | @1024 平均步數 | 比例 | Answer@256 |
|------|------------|-------------|------|-----------|
| GPT-20B | 1.1 | 11.0 | 10% | 0.0% |
| GPT-120B | 1.8 | 12.7 | 14% | 0.0% |
| DeepSeek | **2.3** | 6.6 | **35%** | 0.0% |
| GLM-5.2 | 0.1 | 7.8 | 1% | 0.0% |

#### 活動分佈（GPT-120B 為例）

| 活動 | @256 | @1024 |
|------|------|-------|
| calculate | **46.4%** | 46.5% |
| reason | **50.2%** | 43.9% |
| answer | **0.0%** | 6.2% |
| verify | 0.0% | 0.7% |

#### PM 結論

- 256 tokens 下模型不是「做分配決策」，而是「被 `num_predict` 強制截斷」
- DeepSeek 的優勢是每步 token 更少，被截斷時損失較小
- **這解釋了 IDS 沒有改善準確率：** 模型沒有分配 agency，校準訊號沒有作用空間

---

## 三、四個貢獻

1. **新的研究問題：** 首次系統性探討「校準品質 × token 效率」的交叉點
2. **新實驗設計：** Controlled Budget Sweep（原創方法）
3. **新的發現：** LCAE vs Brier 排名不同、信心差距代理指標、雙維度框架、budget sensitivity 曲線
4. **新的整合框架：** 校準品質 × 推理效率 = 資源受限表現

---

## 四、目前定位與下一步

### 實驗設計的根本問題

`num_predict` 截斷讓模型沒有 token 分配的 agency。Phase 3 測的是「推理被截斷後的殘存準確率」，不是「token 分配效率」。Kimiko 已確認這個 validity gap。

### 可選擇的方向

| 選項 | 內容 | 優點 | 缺點 |
|------|------|------|------|
| **A：保留數據** | 重新定義 RQ 為「推理韌性（reasoning robustness）」 | 數據已存在，時間成本低 | 故事與原本不同 |
| **B：重跑實驗** | 改 prompt 指示預算限制，讓模型有 agency | 與原本 RQ 一致，IDS 可能有效 | 需重跑全部實驗 |

### 下一步

1. **首要：** 跟老師開會，說明當前狀況與選擇
2. **論文定位：** 視老師方向決定選 A 或 B
3. **IDS 因果鏈：** 若選 B，核心任務

### 關鍵檔案位置

| 檔案 | 路徑 |
|------|------|
| Phase 3 raw data | `experiments/v3-budget-pilot/results/phase3_raw.json` |
| Budget sensitivity | `experiments/v3-budget-pilot/results/budget_sensitivity_phase3.json` |
| Calibration | `experiments/v3-budget-pilot/results/calibration_phase3.json` |
| IRT + LCAE | `experiments/v3-budget-pilot/results/irt_phase3.json` |
| IDS raw data | `experiments/v3-budget-pilot/results/ids_raw.json` |
| PM analysis | `experiments/v3-budget-pilot/run_pm_analysis_phase3.py` |
| PM summary | `experiments/v3-budget-pilot/pm_analysis_summary.md` |
| IDS design doc | `experiments/v3-budget-pilot/ids_experiment_design.md` |
| Full narrative | `docs/zh-TW/research-narrative-2026-09-11.md` |