# 研究進度完整總覽（2026-09-10）

> 包含每一階段的設計動機、實驗想法、發現與教訓
> V1 → V2 → Deep Research → V3 Phase 2 → B+C → Phase 3 → IDS → PM 分析

---

## 一、研究動機與背景

### 1.1 故事是這樣開始的

學姐 Chen et al. (IEEE IRI 2026) 提出了 LCAE 框架，用 IRT Rasch Model 把模型能力和題目難度放在同一把尺上——σ(θ_m − β_i)。學姐證明了三件事：能力強不等於自評準、給難度訊號（IDS）最能改善校準、改善校準不影響答題能力。

最重要的是，學姐提到 reliability 跟 inference cost 有關聯，但沒有深入驗證。這就是我的切入點。

### 1.2 我想回答的問題

學姐回答了「模型知不知道自己的實力」。我想進一步問：**知道自己會不會，能不能知道自己需要思考多久？校準品質跟 Token 分配效率有沒有關係？**

### 1.3 核心假設

校準好的模型不一定總 token 更少，但分配更合理——簡單題少 token、困難題多 token。在有限資源下，準確率損失更小。

---

## 二、V1 Pilot — 驗證工具可行性

### 為什麼這樣設計？

7/4 跟老師開會時，老師建議引入 Process Mining（流程挖掘）來分析推理軌跡。但我從來沒用過 pm4py，不確定這套工具對 LLM 的 Chain-of-Thought 文字能不能用——CoT 不是標準的事件日誌，沒有固定格式、步驟邊界模糊。

所以 V1 的目標很單純：**用最簡單的題目、最少的成本，確認 PM pipeline 能不能跑通。**

選了 GSM8K 20 題小學數學，5 個模型，8 種活動類型。沒有收集信心數據——因為第一步是確認「切割→標註→分析」的流程能走完，不是驗證假設。

### 發現了什麼

✅ PM 確實能區分推理風格，而且三種風格跨 V1 V2 都穩定：
- **直覺型（DeepSeek）**：短軌跡、高 answer、少思考
- **系統型（GPT-120B）**：calculate+reason 均衡
- **掙扎型（GPT-20B）**：長軌跡、高 reason 佔比

❌ 但限制很清楚：題目太簡單（95-100% acc），零變異量，無法做任何相關分析。沒有信心數據，無法驗證校準。

### 學到的教訓

PM 可以用，但題目要更難、一定要收集信心。

---

## 三、V2 — 加入校準指標

### 為什麼這樣設計？

V1 的教訓直接決定了 V2 的改動方向：
- 題目：20 GSM8K → 100（MMLU STEM 50 + ARC 50），創造準確率變異
- 信心：加入多輪對話式自評，每次答完問 0-100
- 活動：8 種 → 9 種（新增 evaluate）
- PM：從只有 Petri net 擴大到熵分析 + JSD

MMLU 和 ARC 是當時 Ollama 雲端 API 上有的模型相對應的 benchmark。50+50 是取得平衡。

### 信心 Prompt 的設計教訓

這是個重要的教訓。最初用無上下文的方式問：

> User: You answered D. How confident are you?

結果 DeepSeek 回傳 2%，GLM-5.2 回傳 27%。數字完全沒有意義——模型不知道上下文，隨口給了個低信心。

改成多輪對話：

> User: [題目]
> Assistant: [完整推理]
> User: Based on your reasoning above, how confident are you? Give ONLY a number 0-100.

才得到 DeepSeek 99%、GLM-5.2 99% 這種有意義的數字。

**這本身就是一個 methodology finding：無上下文的信心 prompt 會產生完全失真的數據。**

### V2 Rebuild — 數據翻轉

執行後發現多個 bug：
- Conformance 讀取不存在的欄位，alignment 全 0
- Levenshtein (A,B) 和 (B,A) 分別抽樣，非對稱矩陣
- JSD 的 distance 被標成 divergence
- Confidence 只傳 response 沒傳 thinking，還截斷到 500 字

7/24 做了完整 rebuild（環境 + 程式）。修正後 GPT-20B 從 56% 跳到 98%，信心差距全部縮小到趨近於零。前一版「信心差距與準確率反相關」的核心發現直接被推翻。

### 學到的教訓

V2 作為校準分析的價值大幅下降（準確率變異消失）。但 PM pipeline 驗證成功，且暴露了 prompt sensitivity、confidence scarcity、Petri net flower model 等問題。

**但這也讓我重新思考：論文方向是否需要調整？**

---

## 四、7/28 Deep Research — 文獻調查

### 為什麼要做這個？

V2 的數據被推翻後，我意識到不能直接照原計畫走。需要先完整 survey 競爭者，確認這個研究方向還有沒有 novelty，以及怎麼防守。

花了一週寫了 1612 行的文獻調查報告。

### 最重要的發現

2025-2026 年該領域快速升溫，很多基本想法已經被別人做了：

| 競爭者 | 已證明 | 對我的影響 |
|--------|--------|-----------|
| Think Just Enough (EACL 2026) | 自評信心可做 stopping signal | 不能說「首次用 confidence 控制推理長度」 |
| SelfBudgeter (ACL 2026) | 模型預估 token budget + RL | 不能說「首次讓模型預估 budget」 |
| Capability Calibration (arXiv 2026) | 校準→best-of-k allocation | 需轉向 reasoning length |
| Sonata (ICLR 2026) | hidden-state adapter 配置 budget | 需強調 black-box 優勢 |
| Berti et al. (TechRxiv 2025) | PM 分析 LLM reasoning | PM 降級為 diagnosis |

### 重新定位

不能再用「首次用 confidence 省 token」或「首次用 PM 分析 LLM」這種寬宣稱。新定位：

> **以 IRT/LCAE 校準的自我評估，能否更準確預測逐題推理 token 需求？**

差異化：
- IRT 校準不是 raw confidence
- Training-free 不比 SelfBudgeter
- Black-box 不比 Sonata
- 配置 reasoning length 不比 Capability Calibration
- 有 IDS intervention 做因果驗證
- PM 做機制診斷

---

## 五、V3 Phase 2 — Budget Sensitivity Pilot

### 為什麼這樣設計？

文獻調查後，需要先確認最基本的假設：**到底存不存在可測量的 token requirement？** 如果所有題目在低 budget 下都答不出來、高 budget 下都答對，那就沒有 budget sensitivity，後續就不用做了。

所以 Phase 2 的目標很具體：用 2 個極端模型（校準差的 GPT-20B vs 校準好的 DeepSeek）× 30 題 × 4 budgets（128/256/512/1024）確認題目難度夠、存在 budget sensitivity。

選 MATH-500 是因為它是標準 benchmark（Think Just Enough、SelfBudgeter 都在用），只取 Level 3-5 因為 Level 1-2 太簡單。

Budget 的選擇根據 V2 的自然 token 用量（平均 600-900）：128 是極度壓縮、256 顯著壓縮、512 中等、1024 接近無限制。

### 結果

| Budget | GPT-20B | DeepSeek | 差距 |
|--------|---------|----------|------|
| 128 | 0.0% | 0.0% | — |
| **256** | 3.3% | **15.0%** | **5×** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

### 想法與下一步

✅ Budget sensitivity 存在，MATH-500 難度剛好。
✅ DeepSeek 在所有 budget 下都贏，校準優勢在低 token 時最明顯。
⚠️ 但只有 2 模型，無法區分校準 vs 能力的 confound。
⚠️ 沒有 confidence 收集，不能驗證因果鏈。

**決定：進入 Phase 3。**

---

## 六、B + C — 信心測試與活動標註

### B：為什麼要先測信心？

Phase 3 要加入 confidence 收集，但信心 prompt 在 V2 出過問題（無上下文失真）。在衝 Phase 3 之前，先用 2 模型 × 10 題 × 2 budgets 確認 confidence 機制正常。

**結果：** GPT-20B 答對 97 / 答錯 70（可區分 ✅），DeepSeek 答對 100 / 答錯 99（overconfident）。機制正常，可以直接用在 Phase 3。

### C：為什麼要匯出活動標註？

V1/V2 的活動標註都是規則式（關鍵字匹配）。老師之前提過 reliability 的問題。已匯出 100 段樣本，等人工標註驗證。這個不影響 Phase 3 進度，可以平行進行。

---

## 七、V3 Phase 3 — 決定性實驗

### 為什麼這樣設計？

Phase 2 確認了 budget sensitivity，但只有 2 模型無法回答「校準 vs 能力」的 confound。Phase 3 的目標是：**用 4 模型完整回答這個問題**。

加 GPT-120B（校準中等、117B）和 GLM-5.2（校準未知、756B）：
- 如果 GLM-5.2（最大模型）在低 budget 表現最好 → 單純模型大小在解釋
- 如果 GPT-120B（校準最好）在低 budget 表現好 → 校準是獨立因素
- 如果 DeepSeek 還是最好 → 推理風格是關鍵

從 Phase 2 的經驗：
- 剔除 128（0% 無資訊量）
- 增加 replicate 到 3 次（減少 stochastic 誤差）
- 只取 MATH-500 L3+L4（剔除太難的 L5）
- 加入 IRT + LCAE 計算（學姐方法）

總規模：4 × 60 × 3 × 3 × 2 = **4320 calls**。

### 關鍵發現

#### 發現一：能力 θ 與校準 LCAE 是兩個獨立維度

| 模型 | Acc@1024 | 能力 θ | LCAE |
|------|---------|-------|------|
| DeepSeek | **66.1% 🏆** | **+0.65 🏆** | 0.303 |
| GPT-120B | 50.6% | +0.00 | **0.247 🏆** |
| GPT-20B | 48.3% | −0.09 | 0.341 |
| GLM-5.2 | 36.7% | −0.57 | 0.438 |

DeepSeek 能力最強但校準不是最好，GPT-120B 能力中等但校準最好。

**這回應了學姐：能力強 ≠ 自評準。**

#### 發現二：Brier vs LCAE 排名不同

| 模型 | Brier 排名 | LCAE 排名 |
|------|----------|----------|
| DeepSeek | **1** | 2 |
| GPT-120B | 2 | **1** |

選擇哪個指標，會影響你對「哪個模型最可靠」的判斷。
**LCAE 捕捉到 Brier 看不到的訊息——題目難度和模型能力的交互。**

#### 發現三：信心差距可做代理指標

GPT-120B（+25.5）> DeepSeek（+15.5）> GPT-20B（+7.3）> GLM-5.2（+3.4）。與 LCAE 排序一致，計算成本極低。

#### 發現四：GLM-5.2 是最大但表現最差

756B MoE 的 GLM-5.2 在 MATH-500 上能力最低（θ=−0.57）、校準最差（LCAE=0.438）、答錯時還有 96% 信心。這代表模型大小不等於數學推理能力。

### 當時的想法

Phase 3 結果出來時，我原本預期的是「校準好的模型在低 budget 表現更好」。但數據告訴我的是：DeepSeek 在低 budget 贏不是因為校準好，而是因為推理效率高。

這讓我有點困惑——核心假設好像只對了一半。

---

## 八、Kimiko 的疑慮與 IDS Intervention

### Kimiko 的判斷

老師的 agent Kimiko 看了我的研究文件後，說了三個疑慮：

1. **Phase 3 結果支撐不了核心 claim**：低預算表現最好的是 DeepSeek，校準最好的是 GPT-120B——這兩個不是同一個模型。數據呈現的是「能力強→表現好」不是「校準好→表現好」。
2. **IDS 是最大差異化但還沒跑**：沒有 IDS 的論文只能說「觀察到一個現象」，不能說「能操控它」。
3. **競爭者 R³-Bench 8 月 arXiv**：跟 budget sensitivity 的概念重疊。

### IDS 實驗設計

IDS 是學姐的核心方法——在 prompt 中加一句「This problem is rated difficult/moderate/easy...」。從 Phase 3 的 IRT β 算出每題難度 5 級分。

設計：2 模型（GPT-120B 校準最好 vs DeepSeek 能力最強）× 2 條件（QOQ 無 IDS vs IDS 有 IDS）× 2 budgets × 3 reps × 30 題 = **1440 calls**。

選 QOQ vs IDS 都要跑（不是拿 Phase 3 當對照），因為 intervention 需要乾淨的 paired comparison。

### IDS 結果

| 效果 | 結果 |
|------|------|
| 校準改善？ | ✅ GPT-120B Brier ↓, 答錯信心 ↓ |
| 準確率提升？ | ❌ 無顯著變化 |
| 因果鏈成立？ | ❌ 校準改善未轉換成準確率 |

IDS 改善了校準，但沒有改善準確率。

---

## 九、PM 分析 — 為什麼 IDS 沒有效

### Kimiko 的關鍵提問

Kimiko 問了一個根本性的問題：**模型在低預算下到底是「不知道該在哪裡停」（校準問題）還是「根本算不出來」（能力問題）？**

這決定了 IDS 到底有沒有作用空間。

### PM 分析的發現

把 Phase 3 的資料跑 PM 分析：

| 模型 | @256 步數 | @1024 步數 | 比例 | Answer@256 |
|------|----------|-----------|------|-----------|
| GPT-20B | 1.1 | 11.0 | 10% | 0.0% |
| GPT-120B | 1.8 | 12.7 | 14% | 0.0% |
| DeepSeek | **2.3** | 6.6 | **35%** | 0.0% |
| GLM-5.2 | 0.1 | 7.8 | 1% | 0.0% |

256 tokens 下模型連 answer 都寫不出來——不是「分配決策」的問題，是被 `num_predict` 強制截斷。

### 實驗設計的根本問題

`num_predict` 截斷讓模型沒有 token 分配的 agency。模型不知道有預算限制，只是寫到一半被切掉。

**這解釋了為什麼 IDS 沒有改善準確率：** IDS 能改善校準，但模型根本沒有機會去調整推理長度——因為它沒有 agency，輸出直接被 API 切斷。

這也解釋了 DeepSeek 的優勢：不是校準好，是每步用 token 少，被截斷時損失較小。

---

## 十、目前的定位與選擇

### Kimiko 的結論

Kimiko 說：你的實驗設計有一個根本性的 validity gap。`num_predict` 截斷不是「需要在論文裡誠實交代」的細節——它是整個 Phase 3 的 validity 問題。

### 兩個可選的方向

| 選項 | 內容 | 優點 | 缺點 |
|------|------|------|------|
| **A：保留數據** | RQ 改為「推理韌性（reasoning robustness）」 | 數據已存在，PM 分析強 | 故事與原本不同 |
| **B：重跑實驗** | prompt 指示預算，讓模型有 agency | 與原本 RQ 一致 | 需全部重跑 |

Kimiko 建議選 A，但要在 methodology 裡主動說清楚設計選擇：「使用 hard budget constraint 是為了排除模型對預算指示的遵從性差異，聚焦在推理內容本身的韌性。」把截斷從「設計缺陷」變成「有意識的方法論選擇」。

### 時間

不是 10 月截止，所以時間不是問題。選擇空間大很多。

### 下一步

明天跟老師開會，完整說明從 Phase 3 到 IDS 到 PM 分析的發現，討論方向後決定下一步。

---

## 十一、關鍵檔案位置

| 檔案 | 路徑 |
|------|------|
| Phase 3 raw | `experiments/v3-budget-pilot/results/phase3_raw.json` |
| Budget sensitivity | `experiments/v3-budget-pilot/results/budget_sensitivity_phase3.json` |
| Calibration | `experiments/v3-budget-pilot/results/calibration_phase3.json` |
| IRT + LCAE | `experiments/v3-budget-pilot/results/irt_phase3.json` |
| IDS raw | `experiments/v3-budget-pilot/results/ids_raw.json` |
| PM 分析腳本 | `experiments/v3-budget-pilot/run_pm_analysis_phase3.py` |
| PM 摘要 | `experiments/v3-budget-pilot/pm_analysis_summary.md` |
| IDS 設計文件 | `experiments/v3-budget-pilot/ids_experiment_design.md` |
| 文獻調查 | `docs/zh-TW/deep-research-*.md` |
| 研究敘事 | `docs/zh-TW/research-narrative-2026-09-11.md` |