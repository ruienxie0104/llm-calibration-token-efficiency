# LLM 自我評估校準與推理 Token 分配效率之研究

> **完整敘事：從研究動機到最新發現**
> 最後更新：2026-09-11

---

## 一、研究動機

### 背景：為什麼要研究這個問題？

大型語言模型（LLM）在進行推理時，會產生大量的 token 消耗。每個 API 呼叫的 token 成本直接反映在運算時間與金錢成本上。隨著 LLM 被廣泛應用在各種場景，如何有效率地使用 token — 特別是在推理過程中 — 成為一個重要的研究問題。

然而，目前大部分推理效率的研究（如 adaptive reasoning、early stopping）都假設模型對自己的信心可以直接作為推理深度的控制信號，但這個假設的基礎 — 模型信心的校準品質 — 本身卻很少被檢驗。

### 核心研究問題

> **LLM 自我評估的校準品質，能否預測並改善推理 Token 的分配效率？更具體地說：校準品質越好的模型，是否能在 token 預算有限的情況下，做出更合理的資源分配，從而在相同 token 成本下達到更高的準確率？**

這個問題可以拆解為兩個層次：

1. **測量層次：** 如何準確評估 LLM 的自我評估校準品質？（傳統 Brier Score vs IRT-based LCAE）
2. **應用層次：** 校準品質是否能實際預測模型在不同 token 預算下的表現變化？（Budget Sensitivity）

### 核心假設

校準好的模型不一定在無限制情況下使用更少的 token，但它的分配應該更合理：
- **簡單題 / 高把握題：** 避免 overthinking，用較少 token 即可
- **困難題 / 低把握題：** 保留足夠的推理預算
- **結果：** 在相同 token 總預算下，校準好的模型能達到更高的準確率

---

## 二、參考文獻與定位

### 學姐論文：LCAE 框架 (Chen et al., IEEE IRI 2026)

本研究的直接起點是學姐的 LCAE（Latent Confidence Alignment Error）框架，該框架使用 **IRT（Item Response Theory）的 Rasch Model**：

$$P(\text{模型 } m \text{ 答對題目 } i) = \sigma(\theta_m - \beta_i)$$

其中 $\theta_m$ 是模型能力、$\beta_i$ 是題目難度、$\sigma$ 是 logistic function。

學姐的三個關鍵發現：
1. **能力強 ≠ 自評準** — GPT-5 能力最強但自評不是最好
2. **IDS（給難度訊號）**最有效改善校準，且不傷能力
3. 提到 reliability 與 inference cost 有關聯，但未深入驗證

### 競爭者分析

| 工作 | 方法 | 與本研究的差異 |
|------|------|----------------|
| **Think Just Enough** (EACL 2026) | 自評信心做 stopping signal | 信心未經校準 → 我們比較 raw vs IRT-calibrated |
| **SelfBudgeter** (ACL 2026) | 訓練模型預估 token 預算 | 需要訓練 → 我們是 training-free |
| **Capability Calibration** (arXiv 2026) | 校準品質指導 best-of-k 配置 | 配置 sampling 次數 → 我們配置 reasoning length |
| **Sonata / Adaptive Thinking** (ICLR 2026) | Hidden-state adapter 預測 consistency | 需 hidden states → 我們只需 verbalized confidence |

### 本研究的差異化定位

| 面向 | 競爭者 | 本研究 |
|------|--------|--------|
| 校準方法 | raw confidence / hidden state | **IRT/LCAE psychometric calibration** |
| 訓練需求 | SFT + RL / preference optimization | **Training-free** |
| 模型存取 | hidden states / logits | **Black-box compatible** |
| 配置對象 | sampling 次數 / best-of-k | **Single-trajectory reasoning length** |
| 因果驗證 | cross-model correlation | **IDS intervention（可驗證因果鏈）** |
| 機制分析 | 無 | **Process Mining 行為診斷** |

---

## 三、使用的方法

### 3.1 校準評估方法

本研究同時使用兩種校準指標進行比較：

**Brier Score（傳統基準）：**
$$Brier = \frac{1}{N}\sum_{i=1}^{N}(conf_i - correct_i)^2$$
- 比較模型信心與當次答對/答錯的差距
- 文獻標準（Guo et al., 2017; Kadavath et al., 2022）

**LCAE（IRT-based，學姐方法）：**
$$LCAE_m = \frac{1}{N}\sum_{i}((1 - conf_i/100) - (1 - \sigma(\theta_m - \beta_i)))^2$$
- 利用 IRT 同時考慮模型能力 $\theta_m$ 與題目難度 $\beta_i$
- 比 Brier 多了解釋層面

### 3.2 Controlled Budget Sweep（本研究原創方法）

這是我們的核心實驗設計。概念上類似藥物試驗中的劑量反應曲線：

**做法：** 讓同一個模型用不同的 token 預算回答同一題目，記錄不同預算下的準確率變化。

```
Budget 256: 模型只能產出 256 tokens → 記錄答對/答錯
Budget 512: 模型可以產出 512 tokens → 記錄答對/答錯
Budget 1024: 接近無限制 → 作為對照組
```

**為什麼這樣設計：** 如果我們直接比較不同模型在無限制情況下的 token 使用量，無法區分「模型本來就比較簡潔」和「模型因為校準好而更有效率」。透過固定預算，我們讓所有模型在「相同的資源限制」下競爭，能更公平地比較 token 使用效率。

### 3.3 Process Mining（輔助分析）

將模型的 Chain-of-Thought 切成活動序列（understand / reason / calculate / evaluate / verify / reconsider / answer），使用 pm4py 進行流程發現、熵分析、Jensen-Shannon 散度分析。

---

## 四、實驗設計

### 4.1 模型選擇

| 模型 | 參數量 | 架構 | 校準預期 |
|------|--------|------|---------|
| GPT-OSS-20B | 21B | Dense | 校準較差（小模型） |
| GPT-OSS-120B | 117B | Dense | 校準中等 |
| DeepSeek-V4-Flash | 158B | MoE (13B active) | 校準較好 |
| GLM-5.2 | 756B | MoE (40B active) | 最大模型，校準未知 |

**選擇策略：** 覆蓋從 21B 到 756B 的能力光譜，且包含不同架構（Dense vs MoE）與不同校準特性。

### 4.2 題目選擇

**MATH-500（Level 3 + Level 4）：**
- 標準化 benchmark（MATH 被 Think Just Enough、TALE、SelfBudgeter 等論文廣泛使用）
- Level 3（中等難度 30 題）+ Level 4（中高難度 30 題）= 60 題
- 排除 Level 1-2（太簡單）和 Level 5（太難，連高預算都答不出來）

### 4.3 Token 預算設定

| Budget | 佔自然用量比例 | 預期效果 |
|--------|--------------|---------|
| 256 | ~30% | 顯著壓縮，多數模型無法完整推理 |
| 512 | ~60% | 中等壓縮，開始能看到差異 |
| 1024 | ~110% | 接近無限制，作為對照組 |

**設計邏輯：** 自然用量平均約 600-900 tokens。256 是「極度不足」、512 是「勉強夠用」、1024 是「接近充足」。三個等級涵蓋從不足到充足的連續變化。

### 4.4 實驗規模

**Phase 2（先導）：** 2 模型 × 30 題 × 4 budgets × 2 reps = 480 calls
**Phase 3（決定性）：** 4 模型 × 60 題 × 3 budgets × 3 reps = 2,160 次答題 + 2,160 次信心評估 = **4,320 次 API 呼叫**

---

## 五、最新發現

### 5.1 Budget Sensitivity：誰在低資源下表現最好？

| 模型 | @ 256 | @ 512 | @ 1024 | 能力 θ | LCAE |
|------|-------|-------|--------|-------|------|
| GPT-OSS-20B | 0.0% | 19.4% | 48.3% | −0.086 | 0.341 |
| GPT-OSS-120B | 0.0% | 17.2% | 50.6% | +0.003 | **0.247** |
| **DeepSeek** | **18.3%** | **49.4%** | **66.1%** | **+0.649** | 0.303 |
| GLM-5.2 | 0.0% | 4.4% | 36.7% | −0.566 | 0.438 |

**核心發現：只有 DeepSeek 在 256 時還有 18.3% 準確率，其他三個模型全部 0%。**

### 5.2 能力 vs 校準：兩個獨立維度

| 模型 | 能力 θ | LCAE | 能力排名 | 校準排名 |
|------|-------|------|---------|---------|
| DeepSeek | **+0.649** | 0.303 | 1 | 2 |
| GPT-120B | +0.003 | **0.247** | 2 | **1** |
| GPT-20B | −0.086 | 0.341 | 3 | 3 |
| GLM-5.2 | −0.566 | 0.438 | 4 | 4 |

**發現：能力最強的模型（DeepSeek）校準不是最好的。校準最好的模型（GPT-120B）能力不是最強的。** 這呼應學姐論文的核心論點：能力強 ≠ 自評準。

### 5.3 Brier vs LCAE：選擇指標影響模型判斷

| 模型 | Brier（越低越好） | LCAE（越低越好） |
|------|-----------------|----------------|
| DeepSeek | **0.284**（第 1 名） | 0.303（第 2 名） |
| GPT-120B | 0.320（第 2 名） | **0.247**（第 1 名） |

**發現：Brier 和 LCAE 對同批模型的校準排名給出不同答案。** 如果你只看 Brier，會認為 DeepSeek 校準最好；如果你看 LCAE，會認為 GPT-120B 校準最好。這證明 LCAE 捕捉到了 Brier 看不到的訊息——它考慮了題目難度和模型能力的差異。

### 5.4 信心差距：誰知道自己錯了？

（@1024 預算下）

| 模型 | 答對時信心 | 答錯時信心 | **差距** | 自覺程度 |
|------|---------|---------|---------|---------|
| GPT-20B | 98% | 90% | +7.3 | 稍能自覺 |
| **GPT-120B** | **96%** | **71%** | **+25.5** | **最有自知之明** |
| DeepSeek | 100% | 84% | +15.5 | 中等 |
| **GLM-5.2** | **100%** | **96%** | **+3.4** | **最沒自覺** |

**發現：GPT-120B 答錯時信心降到 71%（知道自己不會），GLM-5.2 答錯時還有 96%（完全不知道自己錯了）。** 信心差距的排序與 LCAE 完全一致，因此可以做為一個簡易的校準代理指標。

### 5.5 雙維度框架

綜合以上發現，我們提出一個新的理解框架：

> **模型在資源受限時的推理表現，由兩個獨立維度共同決定：**
> 1. **校準品質（知道自己會不會）** — 以 LCAE 測量
> 2. **推理效率（把 token 花在刀口上）** — 以 budget sensitivity 測量

這兩個維度過去被分開研究，但我們證明兩者獨立且都重要。最理想的模型是兩者兼備，但目前的模型尚未達到。

---

## 六、研究貢獻總結

1. **新的研究問題：** 首次系統性探討「校準品質是否能預測 token 分配效率」
2. **新的實驗方法：** 設計 Controlled Budget Sweep 作為標準化評估框架
3. **新的發現：**
   - 能力 θ 與校準 LCAE 是兩個獨立維度
   - Brier vs LCAE 對模型排名給出不同答案
   - 信心差距可做為簡易校準代理指標
   - 首次公開 4 模型 × 3 預算的完整準確率曲線
4. **新的整合框架：** 校準品質 × 推理效率 = 資源受限表現

---

## 七、下一步

| 項目 | 優先級 | 說明 |
|------|--------|------|
| **IDS Intervention** | 最高 | 驗證因果鏈：IDS 改善 LCAE → 改善 token 分配。跟學姐論文最直接銜接 |
| 論文投稿 | 高 | 目標 IEEE Big Data 2026（10 月截止）或 BPM/ICPM |
| Activity Labeling 驗證 | 中 | 人工標註 100 段樣本，驗證規則式分割可靠性 |
| PM 機制分析 | 中 | 將 Phase 3 資料跑 entropy/JSD 分析 |