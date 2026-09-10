# 研究進度完整總覽（2026-09-11 更新版）

> 核心敘事：我們試圖驗證「校準 → token 分配效率」的因果鏈，但實驗設計本身揭示了一個更根本的問題——hard constraint 與 soft constraint 兩種預算機制對模型行為的影響根本不同。
> V1 → V2 → Deep Research → V3 Phase 2 → B+C → Phase 3 → IDS → PM 分析

---

## 一、研究動機、研究問題與假設

### 1.1 背景

LLM 推理消耗大量 token，每個 API 呼叫都有成本。現有 adaptive reasoning 研究（如 Think Just Enough）假設模型對自己的信心可以直接作為推理深度的控制信號，但這個假設的基礎——模型信心的校準品質——本身很少被檢驗。

更重要的是，現有 budget sensitivity 相關研究（包括 R³-Bench 等 2026 年的工作）在設計實驗時，普遍沒有區分 **hard constraint（API 層截斷）** 和 **soft constraint（prompt 指示）** 兩種不同的預算機制。這兩種情境下模型的行為機制完全不同，但文獻裡幾乎沒有人明確討論這個差異。

### 1.2 研究問題

**原始 RQ：** 校準品質能否預測並改善 token 分配效率？

這個問題預設了「模型有分配 agency」，但實驗過程中我們發現實際的預算機制會剝奪這個 agency。因此修正為兩個 RQ：

- **RQ1（描述性）：** 在硬性 token 上限（hard budget constraint）下，模型的推理韌性（reasoning robustness）與校準品質是否相關？
- **RQ2（機制性）：** Hard constraint 與 soft constraint 兩種預算機制，對模型推理行為的影響是否根本不同？

### 1.3 研究假設的演進

**原始假設：** 校準好的模型不一定總 token 更少，但分配更合理——簡單題少 token、困難題多 token。在有限資源下，準確率損失更小。

**重要認知：** 這個假設在 hard constraint 的實驗設計下無法被驗證——模型沒有做分配決策的 agency，它的輸出只是被截斷。這不是「假設被推翻」，而是「假設尚未被測試」（Kimiko 2026-09-10）。

因此當前研究的假設更新為：

- **H1：** 校準品質（LCAE）與推理韌性（hard constraint 下的殘存準確率）是兩個獨立維度
- **H2：** Hard constraint 與 soft constraint 下模型的行為序列有根本性差異

### 1.4 使用的方法

| 方法 | 用途 | 狀態 |
|------|------|------|
| Brier Score | 傳統校準指標（baseline） | ✅ 已完成 |
| LCAE（IRT-based） | 校準品質測量（學姐方法） | ✅ 已完成 |
| Controlled Budget Sweep | 固定 token 預算比較模型表現（**hard constraint 設計**） | ✅ 已完成 |
| Process Mining | 診斷推理軌跡的行為機制 | ✅ 已完成（核心發現來源） |
| Soft Constraint 對比實驗 | Prompt 指示預算，讓模型有 agency | 📝 規劃中（最高優先） |

> **方法論備註：** Controlled Budget Sweep 使用 hard constraint（`num_predict` 截斷）而非 soft constraint（prompt 指示），目的是排除模型對預算指示的遵從性差異，聚焦在推理內容本身的韌性。這個選擇的 limitation 在 discussion 中誠實交代。

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

### 信心 Prompt 的設計教訓

最初用無上下文的方式問：

> User: You answered D. How confident are you?

結果 DeepSeek 回傳 2%，GLM-5.2 回傳 27%。數字完全沒有意義。

改成多輪對話：

> User: [題目]
> Assistant: [完整推理]
> User: Based on your reasoning above, how confident are you? Give ONLY a number 0-100.

才得到 DeepSeek 99%、GLM-5.2 99% 這種有意義的數字。

**這本身就是一個 methodology finding：無上下文的信心 prompt 會產生完全失真的數據。**

### V2 Rebuild — 數據翻轉

執行後發現多個 bug：Conformance 欄位錯誤、Levenshtein 非對稱、JSD 標錯、Confidence 截斷。7/24 完整 rebuild 後，GPT-20B 從 56% 跳到 98%，前一版「信心差距與準確率反相關」的核心發現直接被推翻。

### 學到的教訓

V2 作為校準分析的價值大幅下降（準確率變異消失）。但 PM pipeline 驗證成功，且暴露了 prompt sensitivity、confidence scarcity、Petri net flower model 等問題。這也促使我做了 7/28 的文獻調查。

---

## 四、7/28 Deep Research — 文獻調查

### 為什麼要做這個？

V2 的數據被推翻後，需要先完整 survey 競爭者，確認研究方向還有沒有 novelty。

### 最重要的發現

| 競爭者 | 已證明 | 對我的影響 |
|--------|--------|-----------|
| Think Just Enough (EACL 2026) | 自評信心可做 stopping signal | 不能說「首次用 confidence 控制推理長度」 |
| SelfBudgeter (ACL 2026) | 模型預估 token budget + RL | 不能說「首次讓模型預估 budget」 |
| Capability Calibration (arXiv 2026) | 校準→best-of-k allocation | 需轉向 reasoning length |
| Sonata (ICLR 2026) | hidden-state adapter 配置 budget | 需強調 black-box 優勢 |
| Berti et al. (TechRxiv 2025) | PM 分析 LLM reasoning | PM 降級為 diagnosis |
| **R³-Bench (arXiv 2026-08)** | 共享預算下評估資源理性 | 未區分 hard/soft constraint |

### 重新定位

不能再用「首次用 confidence 省 token」或「首次用 PM 分析 LLM」這種寬宣稱。差異化：IRT 校準、training-free、black-box、reasoning length、IDS 因果驗證、PM 機制診斷。

---

## 五、V3 Phase 2 — Budget Sensitivity Pilot

### 為什麼這樣設計？

需要先確認最基本的假設：**到底存不存在可測量的 token requirement？**

2 個極端模型（校準差的 GPT-20B vs 校準好的 DeepSeek）× 30 題 × 4 budgets（128/256/512/1024）確認題目難度夠、存在 budget sensitivity。

### 結果

| Budget | GPT-20B | DeepSeek | 差距 |
|--------|---------|----------|------|
| 128 | 0.0% | 0.0% | — |
| **256** | 3.3% | **15.0%** | **5×** |
| 512 | 20.0% | 33.3% | 1.7× |
| 1024 | 31.7% | 36.7% | 1.2× |

### 想法與下一步

✅ Budget sensitivity 存在，MATH-500 難度剛好。
✅ DeepSeek 在所有 budget 下都贏。
⚠️ 但只有 2 模型，無法區分校準 vs 能力的 confound。
⚠️ 沒有 confidence 收集，不能驗證因果鏈。

**決定：進入 Phase 3。**

---

## 六、B + C — 信心測試與活動標註

### B：為什麼要先測信心？

信心 prompt 在 V2 出過問題（無上下文失真）。先用 2 模型 × 10 題 × 2 budgets 確認機制正常。

**結果：** GPT-20B 答對 97 / 答錯 70（可區分 ✅），DeepSeek 答對 100 / 答錯 99（overconfident）。機制正常。

### C：為什麼要匯出活動標註？

V1/V2 的活動標註都是規則式。已匯出 100 段樣本，等人工標註驗證。不影響 Phase 3 進度。

---

## 七、V3 Phase 3 — 決定性實驗

### 為什麼這樣設計？

Phase 2 只有 2 模型無法回答「校準 vs 能力」的 confound。Phase 3 用 4 模型（+GPT-120B、+GLM-5.2）完整回答。從 Phase 2 經驗：剔除 128、replicate 增加到 3、只取 L3+L4、加入 IRT + LCAE。

總規模：4 × 60 × 3 × 3 × 2 = **4320 calls**。

### 關鍵發現

#### 發現一：能力 θ 與校準 LCAE 是兩個獨立維度

| 模型 | Acc@1024 | 能力 θ | LCAE |
|------|---------|-------|------|
| DeepSeek | **66.1% 🏆** | **+0.65 🏆** | 0.303 |
| GPT-120B | 50.6% | +0.00 | **0.247 🏆** |
| GPT-20B | 48.3% | −0.09 | 0.341 |
| GLM-5.2 | 36.7% | −0.57 | 0.438 |

DeepSeek 能力最強但校準不是最好，GPT-120B 能力中等但校準最好。**這回應了學姐：能力強 ≠ 自評準。**

#### 發現二：Brier vs LCAE 排名不同

Brier 看 DeepSeek 最好（0.284），LCAE 看 GPT-120B 最好（0.247）。選擇哪個指標，會影響對「哪個模型最可靠」的判斷。**LCAE 捕捉到 Brier 看不到的訊息——題目難度和模型能力的交互。**

#### 發現三：信心差距可做代理指標

GPT-120B（+25.5）> DeepSeek（+15.5）> GPT-20B（+7.3）> GLM-5.2（+3.4）。與 LCAE 排序一致，計算成本極低。

#### 發現四：GLM-5.2 是最大但表現最差

756B MoE 的 GLM-5.2 能力最低（θ=−0.57）、校準最差（LCAE=0.438）、答錯時還有 96% 信心。模型大小不等於數學推理能力。

### 當時的想法

Phase 3 結果出來時，我原本預期「校準好的模型在低 budget 表現更好」。但數據顯示 DeepSeek 贏是因為推理效率高，不是校準。核心假設好像只對了一半。

---

## 八、Kimiko 的疑慮與 IDS Intervention

### Kimiko 的判斷

1. **Phase 3 結果支撐不了核心 claim**：低預算表現最好的是 DeepSeek，校準最好的是 GPT-120B——兩個不是同一個模型
2. **IDS 是最大差異化但還沒跑**
3. **競爭者 R³-Bench 8 月 arXiv**

### IDS 實驗設計

IDS 是學姐的核心方法——在 prompt 中加「This problem is rated difficult/moderate/easy...」。難度等級從 Phase 3 的 IRT β 分 5 級。

設計：2 模型 × 2 條件（QOQ vs IDS）× 2 budgets × 3 reps × 30 題 = **1440 calls**。QOQ 和 IDS 都重跑（不拿 Phase 3 當對照），因為 intervention 需要乾淨的 paired comparison。

### IDS 結果

| 效果 | 結果 |
|------|------|
| 校準改善？ | ✅ GPT-120B Brier ↓, 答錯信心 ↓ |
| 準確率提升？ | ❌ 無顯著變化 |
| 因果鏈成立？ | ❌ 校準改善未轉換成準確率 |

---

## 九、PM 分析 — 截斷機制的行為診斷（核心發現）

### Kimiko 的關鍵提問

模型在低預算下到底是「不知道該在哪裡停」（校準問題）還是「根本算不出來」（能力問題）？

### PM 分析的發現

| 模型 | @256 步數 | @1024 步數 | 比例 | Answer@256 |
|------|----------|-----------|------|-----------|
| GPT-20B | 1.1 | 11.0 | 10% | 0.0% |
| GPT-120B | 1.8 | 12.7 | 14% | 0.0% |
| DeepSeek | **2.3** | 6.6 | **35%** | 0.0% |
| GLM-5.2 | 0.1 | 7.8 | 1% | 0.0% |

活動分佈（GPT-120B 為例）：

| 活動 | @256 | @1024 |
|------|------|-------|
| calculate | **46.4%** | 46.5% |
| reason | **50.2%** | 43.9% |
| answer | **0.0%** | 6.2% |
| verify | 0.0% | 0.7% |

### 核心發現（發現五：截斷機制的行為診斷）

1. **256 tokens 下模型平均只能產出 1-2 個 step，answer activity 全部為 0%**——不是「分配決策」的問題，是被 `num_predict` 強制截斷
2. **低預算和高預算的活動分佈比例本質上相同**——模型在 256 做的推理跟 1024 的前半段一樣，只是被切斷，沒機會走到 answer/verify
3. **DeepSeek 的優勢是推理風格精簡（每步 token 少），不是校準**——被截斷時損失較小
4. **這解釋了為什麼 IDS 沒有改善準確率**——模型沒有分配 agency，校準訊號沒有作用空間

### 實驗設計的根本問題

`num_predict` 截斷讓模型沒有 token 分配的 agency。模型不知道有預算限制，只是寫到一半被切掉。Phase 3 測量的不是「token 分配效率」，而是「推理被截斷後的殘存準確率」。

---

## 十、Soft vs Hard Constraint — 下一步核心實驗

### Kimiko 的關鍵洞察

現有 adaptive reasoning 研究在設計 budget sensitivity 實驗時，普遍沒有區分 **soft constraint（prompt 指示）** 和 **hard constraint（API 截斷）**。這兩種情境下模型的行為機制完全不同，但文獻裡幾乎沒有人明確討論這個差異。

### 對比實驗設計（最高優先）

| 參數 | 設定 |
|------|------|
| 模型 | GPT-120B + DeepSeek（跟 IDS 同一批） |
| 題目 | 30 題 MATH-500 L3+L4（同一批） |
| Budgets | 256、512 |
| Prompt | 「Please complete your reasoning within approximately N tokens.」 |
| Replicates | 3 |
| 規模 | 約 720 次呼叫 |

### 跑完之後的對比

用 PM 分析比較三種條件下的行為序列：
1. **Hard constraint**（現有數據）— 被截斷，沒有 agency
2. **Soft constraint**（新實驗）— 模型自己決定怎麼分配
3. **Unconstrained @1024**（現有數據）— 對照組

如果 soft 下的 activity distribution 跟 hard 明顯不同（soft 出現更多 answer/evaluate，hard 幾乎沒有），論文核心論點就有了實證支撐：**兩種 constraint 機制根本不同。**

### 需要注意：Soft constraint 的遵從性驗證

模型不一定能準確遵守「請在 N tokens 內完成」——需要在論文裡說明如何驗證遵從性（看實際輸出長度分佈）。

---

## 十一、研究貢獻（重寫版）

1. **新的研究問題：** 首次區分 hard constraint 和 soft constraint 兩種預算機制，並指出文獻中這個區分的缺失
2. **新的發現：** 校準品質與推理韌性是兩個獨立維度；DeepSeek 的低預算優勢來自推理風格精簡，不是校準
3. **新的方法論貢獻：** 用 Process Mining 直接診斷推理截斷的行為機制
4. **誠實的負面結果：** IDS 改善校準但不改善準確率，揭示了因果鏈的斷點在哪裡

---

## 十二、下一步

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **最高** | Soft constraint 對比實驗 | 建立 hard vs soft 的行為對比，撐起論文核心論點 |
| 高 | 跟老師開會 | 完整說明從 Phase 3 到 IDS 到 PM 分析的發現 |
| 高 | 論文初稿 | 用「實驗設計揭示更根本問題」的敘事 |
| 中 | Activity labeling 驗證 | 人工標註 100 段樣本 |

---

## 十三、關鍵檔案位置

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