# LLM 自我評估校準與推理 Token 分配效率之研究

> **完整敘事：從研究動機到最新發現**
> 最後更新：2026-09-15（加入 Soft Constraint Pilot 結果）

---

## 一、研究動機

### 背景：為什麼要研究這個問題？

LLM 推理消耗大量 token，每個 API 呼叫都有成本。現有 adaptive reasoning 研究（如 Think Just Enough）假設模型對自己的信心可以直接作為推理深度的控制信號。但這個假設建立在一個未被檢驗的前提上——模型信心的校準品質是否足夠可靠？

更根本的問題是：這些研究在設計預算約束實驗時，普遍沒有區分 **hard constraint（API 層截斷）** 和 **soft constraint（prompt 指示）**。如果兩種機制下模型的行為根本不同，那麼所有基於「預算約束下模型表現」的結論都需要重新檢視。

### 核心研究問題

本研究試圖回答兩個問題：

- **RQ1（方法論）：** Hard constraint 與 soft constraint 兩種預算機制，對模型推理行為的影響是否根本不同？文獻中對這個區分的缺失是否會影響現有結論？
- **RQ2（校準與效率）：** 在軟約束（有 agency）的情境下，模型能夠自主分配 token 時，校準品質與 token 效率之間的關係是什麼？adaptive reasoning 所依賴的校準信號在這種情境下是否仍然有效？

### 核心假設

**原始假設：** 校準好的模型分配更合理——簡單題少 token、困難題多 token。

**這個假設在 hard constraint 下無法被驗證**——模型沒有分配 agency，輸出只是被截斷。經過 soft pilot 實驗後，我們發現了一個更根本的問題：

> **模型在有 agency 的情境下（soft constraint），準確率大幅提升，但校準能力反而下降——adaptive reasoning 依賴的校準信號在它最需要的情境下消失了。**
>
> 這不是 trade-off，而是對這個領域最重要的警告。

---

## 二、參考文獻與定位

### 學姐論文：LCAE 框架 (Chen et al., IEEE IRI 2026)

本研究直接起點是學姐的 LCAE 框架（IRT Rasch Model：$\sigma(\theta_m - \beta_i)$）。學姐證明了能力強 ≠ 自評準、IDS 可改善校準，並提到 cost 關聯但未驗證。這是我的切入點。

### 預算機制在文獻中的缺失

經 survey 發現，現有 token 預算相關研究可分為五類，但**沒有任何一篇論文明確討論或比較 hard constraint 與 soft constraint 的差異**：

| 類別 | 代表論文 | 約束機制 | 明確說明機制？ |
|------|---------|---------|--------------|
| Hard constraint | R³-Bench (2026)、TALE (2025) | API 層截斷（推測） | ❌ 未說明 |
| Soft constraint | TALE (2025)、Steering LLM (2026) | Prompt 指示 | ❌ 未說明 |
| 動態停止 | Think Just Enough (2026) | 無固定預算 | ✅ N/A |
| 訓練-based | SelfBudgeter (2026)、CAT (2026) | 訓練階段學習 | ✅ 不同範式 |
| 事後截斷 | 常見 baseline | 生成後剪裁 | ❌ 未說明 |

**關鍵觀察：** 即使是明確使用了 soft constraint 的論文（如 TALE），也未驗證模型是否真的遵守預算指示。遵從性假設被忽略。

### 競爭者分析

| 競爭者 | 我們可差異化 |
|--------|------------|
| Think Just Enough | 信心未經校準 vs IRT-calibrated |
| SelfBudgeter | 需 training vs training-free |
| Sonata | 需 hidden states vs black-box |
| R³-Bench | 無區分 hard/soft vs 我們證明兩者不同 |

---

## 三、方法

- **Brier Score：「信心−對錯」的差距，標準 baseline**
- **LCAE（IRT-based）：** 同時考慮 $\theta_m$ 與 $\beta_i$，比 Brier 多了解釋層面
- **Controlled Budget Sweep：** 固定 token 預算比較模型表現（**hard constraint 設計**）
- **Soft Constraint Prompt：** prompt 中指示模型在 N tokens 內完成（**新設計，比較用**）
- **Process Mining：** 活動序列分析，診斷推理行為的結構差異

---

## 四、實驗設計

### 模型

| 模型 | 參數量 | 架構 |
|------|--------|------|
| GPT-OSS-20B | 21B | Dense |
| GPT-OSS-120B | 117B | Dense |
| DeepSeek-V4-Flash | 158B | MoE (13B active) |
| GLM-5.2 | 756B | MoE (40B active) |

### 題目

MATH-500 Level 3 + Level 4，共 60 題（Phase 3）/ 30 題（Soft Pilot）

### 預算設定

| Budget | 效果 |
|--------|------|
| 256 | 極度不足 — 多數模型 hard 下 0% |
| 512 | 中等壓縮 |
| 1024 | 接近無限制（對照組） |

---

## 五、最新發現

### 5.1 Phase 3：Hard Constraint 下的四個發現

#### 發現一：能力 θ 與校準 LCAE 是兩個獨立維度

| 模型 | Acc@1024 | 能力 θ | LCAE |
|------|---------|-------|------|
| DeepSeek | **66.1%** | **+0.649** | 0.303 |
| GPT-120B | 50.6% | +0.003 | **0.247** |
| GPT-20B | 48.3% | −0.086 | 0.341 |
| GLM-5.2 | 36.7% | −0.566 | 0.438 |

#### 發現二：Brier vs LCAE 排名不同

Brier 看 DeepSeek 最好；LCAE 看 GPT-120B 最好。選擇指標影響模型判斷。

#### 發現三：信心差距可做代理指標

GPT-120B（+25.5）> DeepSeek（+15.5）> GPT-20B（+7.3）> GLM-5.2（+3.4）。與 LCAE 排序一致。

#### 發現四：IDS 改善校準但不改善準確率

| 效果 | 結果 |
|------|------|
| 校準改善？ | ✅ GPT-120B Brier ↓, 答錯信心 ↓ |
| 準確率提升？ | ❌ 無顯著變化 |

這條線索讓我們開始懷疑：hard constraint 下模型是否有 agency？

### 5.2 PM 分析：Hard 下模型被截斷

256 tokens 下模型平均只有 1-2 個 step，answer 全部為 0%。

| 模型 | @256 步數 | @1024 步數 | Answer@256 |
|------|----------|-----------|-----------|
| GPT-120B | 1.8 | 12.7 | 0.0% |
| DeepSeek | 2.3 | 6.6 | 0.0% |

**解釋了 IDS 為什麼無效：** 模型沒有分配 agency，校準訊號沒有作用空間。

### 5.3 Soft Constraint Pilot：兩種機制根本不同（核心發現）

#### Soft vs Hard 準確率

| 模型 | Budget | Hard 準確率 | Soft 準確率 | 差距 |
|------|--------|-----------|-----------|------|
| **GPT-120B** | **256** | **0.0%** | **74.4%** | **+74%** |
| GPT-120B | 512 | 17.2% | 76.7% | +60% |
| DeepSeek | 256 | 18.3% | 80.0% | +62% |
| DeepSeek | 512 | 49.4% | 82.2% | +33% |

#### 遵從性分析

| 模型 | Budget | 遵守預算 | 超過預算 |
|------|--------|---------|---------|
| GPT-120B | 256 | 31/90 | 59/90 |
| DeepSeek | 256 | 74/90 | 16/90 |

即使低遵從性，soft 仍大幅優於 hard — 「有 agency」本身比「精確遵守預算」更重要。

#### 最重要的發現：Soft 下校準變差了

| 模型 | Budget | Hard 差距 | **Soft 差距** |
|------|--------|----------|-------------|
| GPT-120B | 256 | −52.2（全錯，能自覺） | **+1.5（幾乎沒區分力）** |
| GPT-120B | 512 | +39.7（最好校準） | **−0.5（校準消失）** |
| DeepSeek | 256 | +23.6 | **0.0** |
| DeepSeek | 512 | +23.9 | **−0.1** |

**模型在有 agency 的情況下，準確率大大提高，但同時失去了校準能力——它不知道自己在瞎猜。** 這直接回應了研究動機：adaptive reasoning 所依賴的校準信號，在它最需要被使用的場景下（soft constraint with agency）反而失效了。

### 五維對比

| 面向 | Hard Constraint | Soft Constraint |
|------|---------------|----------------|
| 準確率 @256 | 0-18% | **74-80%** |
| 校準品質 | **✅ 較好** | ❌ 較差（差距趨近 0） |
| 模型 agency | ❌ 無（截斷） | ✅ 有 |
| DeepSeek vs GPT-120B | DeepSeek 大勝 | 兩者接近 |
| IDS 效果 | 改善校準，不改善準確率 | 📝 待測試 |

---

## 六、研究貢獻

1. **新的方法論洞察：** 首次區分 hard constraint 與 soft constraint 兩種預算機制，並證明兩者行為根本不同——但文獻中從未被明確討論
2. **新的發現 — 校準效率 trade-off：** 模型在 soft constraint 下準確率高但校準能力消失，直接挑戰 adaptive reasoning 的核心假設
3. **新的方法論貢獻：** 用 Process Mining 診斷推理截斷的行為機制，提供可視化的行為序列分析
4. **誠實的負面結果：** IDS 改善校準但不改善準確率，揭示因果鏈的斷點在模型 agency 的缺失

---

## 七、下一步

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **最高** | Soft + IDS 實驗 | 在有 agency 的情境下，IDS 是否能改善 token 分配？ |
| 高 | 論文初稿 | 以「校準效率 trade-off 與 hard/soft 機制區分」為核心敘事 |
| 中 | Activity Labeling | 人工標註 100 段樣本 |
| 低 | Post-hoc 模擬 | 從 1024 數據模擬事後截斷效果，成本為零 |