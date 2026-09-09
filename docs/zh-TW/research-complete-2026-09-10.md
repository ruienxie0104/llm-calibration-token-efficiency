# LLM 校準 × Token Allocation × Process Mining — 完整研究總覽

> 最後更新：2026-09-10 | Phase 3 全部完成

---

## 第一篇：研究動機與起點

### 1.1 從學姐論文出發

Chen et al. (IEEE IRI 2026) 提出了 LCAE 框架，核心是使用 **IRT Rasch Model** 把模型能力和題目難度放到同一把尺：

$$P(答對) = \sigma(\theta_m - \beta_i)$$

學姐證明了三件事：
1. **能力強 ≠ 自評準** — GPT-5 最強但自評不是最好
2. **IDS（給難度訊號）**最有效改善校準，且不傷能力
3. 提到 **reliability 跟 inference cost 有關聯**，但沒有深入驗證

### 1.2 我的研究問題

學姐回答了「模型知道自己會不會嗎？」。我想進一步問：

> **知道自己會不會 → 能否知道自己需要思考多久？**
> **校準品質 → Token 分配效率？**

**核心假設：** 校準好的模型不一定總 token 更少，但分配更合理——簡單題少 token、困難題多 token。

### 1.3 引入 Process Mining

為了分析推理軌跡的「結構」，引入 PM。把 CoT 切成活動序列（understand / reason / calculate / evaluate / verify / reconsider / answer 等），用 pm4py 做流程分析。

---

## 第二篇：實驗歷程

### 2.1 V1 Pilot（驗證 PM 可行性）

| 項目 | 設定 | 結果 |
|------|------|------|
| 題目 | 20 題 GSM8K 小學數學 | 太簡單，95-100% acc |
| 模型 | 5 個 | PM 能區分推理風格 |
| 信心 | 未收集 | 無法驗證校準 |

**三種推理風格（跨實驗穩定）：** 直覺型（DeepSeek）、系統型（GPT-120B）、掙扎型（GPT-20B）

### 2.2 V2（加入校準 + Rebuild）

**改動：** 題目改為 MMLU+ARC 100 題，加入信心收集和校準指標。

**信心 Prompt 教訓：** 無上下文問「多確定」→ DeepSeek 回 2%。改成多輪對話 → 99%。

**Rebuild 轉折：** 執行後發現多個 bug（conformance 欄位錯誤、Levenshtein 非對稱、JSD 標錯），修正後數據完全不同——GPT-20B 從 56% 跳到 98%，前一版「反相關」核心發現被推翻。

**影響：** V2 校準分析價值下降，但 PM pipeline 驗證成功。暴露了 prompt sensitivity、confidence scarcity 等後續可避免的問題。

### 2.3 7/28 Deep Research（文獻調查）

1612 行報告，確認競爭者狀況及研究定位，詳見第五篇。

### 2.4 V3 Phase 2（Budget Sensitivity Pilot）

2 模型 × 30 題 × 4 budgets × 2 reps = 480 calls

| Budget | GPT-20B | DeepSeek | 差距 |
|--------|---------|----------|------|
| **256** | **3.3%** | **15.0%** | **5.0×** |
| 1024 | 31.7% | 36.7% | 1.2× |

**結論：** Budget sensitivity 存在、DeepSeek 全勝，但只有 2 模型無法區分校準 vs 能力 confound。

### 2.5 B + C（信心測試 + 活動標註）

**B（信心測試）：** 2 模型 × 10 題 × 2 budgets，確認 confidence prompt 正常運作。

**C（活動標註匯出）：** 匯出 100 段文字（4 模型各 25）待人工標註驗證。

---

## 第三篇：Phase 3 決定性實驗（核心）

### 3.1 設計

4 模型 × 60 題（MATH-500 L3+L4）× 3 budgets（256/512/1024）× 3 reps = **4320 次 API 呼叫**

### 3.2 Budget Sensitivity

| 模型 | @ 256 | @ 512 | @ 1024 |
|------|-------|-------|--------|
| GPT-20B | 0.0% | 19.4% | 48.3% |
| GPT-120B | 0.0% | 17.2% | 50.6% |
| **DeepSeek** | **18.3% 🏆** | **49.4% 🏆** | **66.1% 🏆** |
| GLM-5.2 | 0.0% | 4.4% | 36.7% |

### 3.3 IRT 能力（θ）vs 校準（LCAE）

| 模型 | Acc@1024 | 能力 θ | LCAE | 校準排名 |
|------|---------|-------|------|---------|
| DeepSeek | 66.1% | **+0.649** 🏆 | 0.303 | 2 |
| **GPT-120B** | 50.6% | +0.003 | **0.247 🏆** | **1** |
| GPT-20B | 48.3% | −0.086 | 0.341 | 3 |
| GLM-5.2 | 36.7% | −0.566 | **0.438** | 4 |

### 3.4 Brier vs LCAE — 兩種校準指標排名不同

| 模型 | Brier（越低越好） | LCAE（越低越好） |
|------|-----------------|----------------|
| DeepSeek | **0.284** 🏆 | 0.303（第二） |
| GPT-120B | 0.320（第二） | **0.247** 🏆 |

**LCAE 和 Brier 給出不同排名。** 選擇哪個指標，會影響你對「哪個模型最可靠」的判斷。

### 3.5 信心差距 — 誰知道自己錯了？（@1024）

| 模型 | 答對信心 | 答錯信心 | 差距 |
|------|---------|---------|------|
| **GPT-120B** | 96% | **71%** | **+25.5 🏆** |
| GLM-5.2 | 100% | **96%** | **+3.4** |

---

## 第四篇：跟競爭者的差異化

### 4.1 競爭者分析

| 競爭者 | 已證明 | 我們的差異化 |
|--------|--------|------------|
| **Think Just Enough** (EACL 2026) | confidence → stopping signal | 信心未校準 → 我們比較 raw vs calibrated |
| **SelfBudgeter** (ACL 2026) | 預估 budget + RL | 需 training → 我們 **training-free** |
| **Capability Cal.** (arXiv 2026) | 校準→best-of-k | 配置 sampling 次數 → 我們配置 **reasoning length** |
| **Sonata** (ICLR 2026) | hidden-state adapter | 需 hidden states → 我們 **black-box** |

### 4.2 本研究差異化

| 面向 | Think Just Enough | SelfBudgeter | Capability Cal. | **本研究** |
|------|-----------------|-------------|-----------------|-----------|
| 校準 | raw confidence | 無 | Brier-calibrated | **IRT/LCAE** |
| 訓練 | 不需要 | SFT+RL 需要 | 不需要 | **Training-free** |
| 配置 | stopping signal | 預估 budget | best-of-k | **reasoning length** |
| 機制分析 | 無 | 無 | 無 | **PM diagnosis** |
| 因果驗證 | 無 | 無 | 無 | **IDS intervention** |

---

## 第五篇：我們的貢獻到底是什麼？

### 5.1 重要認知：不只是「用別人的方法」

Brier 不是我們發明的，LCAE 是學姐的。如果只說「我們用了 LCAE 發現了 XX」，那貢獻確實薄弱。

**但我們做的事情，不只是「用別人的方法」。**

就像生物學家不是發明了顯微鏡，而是用顯微鏡發現了細胞。Brier 和 LCAE 是我們的顯微鏡。我們真正發現的「細胞」是——**校準品質 × Token 效率的交叉點**。

### 5.2 貢獻一：新的研究問題

| 別人問的 | 我們問的 |
|---------|---------|
| 信心校不校準？（Brier / LCAE 都是在回答這個） | **校準品質能不能預測 token 分配效率？** 沒有人問過這個問題。 |

Brier、ECE、LCAE 都是在量「模型知不知道自己的實力」。這些方法被應用在模型選擇、安全校準、成本優化。**但從來沒有人問過：校準品質能不能預測模型需要多少推理資源？** 這是一個全新的應用場景。

### 5.3 貢獻二：新的實驗設計（Controlled Budget Sweep）

沒有人做過 **controlled budget sweep**——讓同一個模型用不同的 token 預算回答同一題，然後看誰的準確率損失最少。

這跟所有競爭者都不同：

| 方法 | 做的事 |
|------|--------|
| Think Just Enough | 推理中問信心 → 決定要不要繼續想 |
| SelfBudgeter | 訓練模型預估 token 預算 |
| Capability Calibration | 根據校準決定每題抽幾次樣本 |
| **我們的 budget sweep** | **先固定每一題的 token 預算 → 看不同校準品質的模型在相同預算下誰表現更好** |

**Budget sweep 是我們原創的實驗方法。**

### 5.4 貢獻三：新的發現

**發現 A：能力 θ 和校準 LCAE 是兩個獨立維度，且對低資源表現有不同的影響方式**
- 校準最好的模型（GPT-120B, LCAE=0.247）在低 budget 時不一定強（0% @256）
- 能力最強的模型（DeepSeek, θ=+0.65）在低 budget 時確實強（18% @256）
- 校準跟能力是兩回事，在 token 有限的現實場景中有不同的影響方式

**發現 B：Brier vs LCAE 排名不同——選擇校準指標會影響模型判斷**
- Brier 看：DeepSeek 校準最好（0.284），GPT-120B 第二（0.320）
- LCAE 看：GPT-120B 校準最好（0.247），DeepSeek 第二（0.303）
- 你對「哪個模型最可靠」的結論會完全不同

**發現 C：信心差距可以做為 just-in-time 校準代理指標**
- 不跑 IRT、不算 LCAE，光看「答對信心 − 答錯信心」就能粗略估計校準排序
- GPT-120B（+25.5）> DeepSeek（+15.5）> GPT-20B（+7.3）> GLM-5.2（+3.4）
- 與 LCAE 排序一致，計算成本極低

**發現 D：四種模型的 budget sensitivity 曲線** — 全新的實證數據

### 5.5 貢獻四：新的整合框架（Two-Dimension Framework）

> **在 token 預算有限的場景下，模型表現由兩個獨立維度共同決定：
> ① 校準品質（知道自己會不會）
> ② 推理效率（把 token 花在刀口上）**

過去這兩個概念被分開研究：校準文獻只看信心準不準，推理效率文獻只看 token 省不省。**我們是第一個把兩者放在同一個框架下、用系統性實驗證明它們獨立且都重要的。**

### 5.6 為論文保留 Brier 的理由

Brier 不是結論，它是 **baseline（基準線）**。

論文的邏輯：

```
─ Step 1：用 Brier 測量（傳統方法，所有文獻都在用）
    → 得到一個排名
─ Step 2：用 LCAE 測量（我們的方法）
    → 得到另一個排名
─ Step 3：兩個排名不同 → 證明 LCAE 有增量價值
    → 如果排名一樣，LCAE 就沒有存在的必要
```

沒有 Brier，就無法證明 LCAE 更好。**Brier 是跳板，不是主角。**

每個領域都有標準指標：語音辨識用 WER、機器翻譯用 BLEU、LLM 校準用 **Brier**（Guo et al., 2017; Kadavath et al., 2022）。

論文不需要「證明大家都在用」，只需要說：

> "Prior work on LLM calibration has primarily used Brier score (Guo et al., 2017)... We show that LCAE provides additional information beyond Brier."

然後用一個簡單的對照表來說明：

| 面向 | Brier | LCAE |
|------|-------|------|
| 比較信心 vs 對錯 | ✅ | ✅ |
| 考慮題目難度 | ❌ | ✅ |
| 考慮模型能力 | ❌ | ✅ |
| 需要 IRT 計算 | ❌ | ✅（但更精確） |
| 給出不同排名 | — | ✅ |

這就是為什麼要保留 Brier：**沒有基準線，就無法證明改善。**

---

## 第六篇：展望與後續

### 6.1 已完成

- [x] V1：PM 可行性驗證
- [x] V2：加入校準 + PM（含 Rebuild）
- [x] 7/28 Deep Research：競爭者分析
- [x] V3 Phase 2：Budget Sensitivity Pilot
- [x] B：Confidence 測試
- [x] C：Activity labeling 匯出
- [x] V3 Phase 3：4 模型 × 60 題決定性實驗
- [x] IRT + LCAE 計算
- [x] 完整分析報告

### 6.2 未完成

| 項目 | 優先級 | 備註 |
|------|--------|------|
| Activity 人工標註（C） | 中 | 100 段文字已匯出 |
| PM 機制分析（entropy/JSD） | 中 | 需將 Phase 3 資料跑 PM pipeline |
| **IDS intervention（給難度訊號）** | **高** | **最重要的下一步—驗證因果鏈** |
| 論文初稿 | 高 | 目標 IEEE Big Data 2026 |

### 6.3 IDS 為什麼是下一步核心

目前的所有結果都是 **correlational**（相關性）。IDS（給模型題目難度訊號）可以做 **interventional**（因果性）實驗：

1. 同一模型、同一題目、有 IDS vs 無 IDS
2. 如果 IDS 改善 LCAE → 同時改善 token 分配 → 這才是因果鏈

這是跟學姐論文最直接的銜接，也是跟所有競爭者最明顯的差異化。

---

> **一句話總結：**
>
> 校準品質和推理效率是兩個獨立維度，共同決定模型在資源受限時的表現。
> 我們用原創的 budget sweep 實驗證明 LCAE 比 Brier 有增量價值，
> 且信心差距可做為簡單代理指標。下一步是 IDS intervention 建立因果鏈。