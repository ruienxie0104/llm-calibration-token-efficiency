# 以可觀察推理進度進行大型語言模型的動態測試時計算分配

> 中文研究說明初稿。本文只呈現目前已確立的方法、設計與證據；token 指 API request 所記錄的 prompt 與 completion token 總和。

## 摘要

大型語言模型（LLM）可以藉由更長推理或續寫提高表現，但 test-time compute 有限，並非每題都值得投入相同資源。固定地讓所有題目都續寫，會在已完成題目上浪費 token；固定短推理，則可能在已有解題進展、但尚未完成的題目上過早停止。

本研究提出 **Visible-Progress Allocation**。模型先以固定低預算 prefix 解題，系統只根據使用者可見的輸出，判斷是否已有可解析最終答案、是否仍有可見但未完成的推理內容，再決定是否追加一次 contextual continuation。方法不讀取隱藏 thinking、不需額外自評，也不使用題目答案或未來結果作決策。

在新的 held-out MATH-500 Level-3/Level-4 題目上，我們以 GPT-OSS-120B 與 DeepSeek-V4-Flash-158B 評估此方法。相較於沒有任何訊號、但有相同預期實際 continuation token 成本的 random allocation，Visible-Progress Allocation 在 GPT-OSS-120B 增加 9.62 個百分點正確率；兩模型 pooled 結果增加 6.78 個百分點，95% question-clustered bootstrap CI 為 [3.48, 10.22]。結果支持：**可見的推理進度可作為低成本的 test-time compute allocation signal。**

## 1. 研究動機

推理型 LLM 的表現不只取決於模型，也取決於每一題可獲得多少 test-time compute，例如更長 generation budget、續寫、verifier 或其他額外運算。實務上資源有限，因此核心問題不是「多算是否有用」，而是：

> 在看過模型第一段輸出後，系統如何判斷這一題是否值得再投入有限的運算資源？

這是一個動態資源配置問題。模型第一段輸出本身提供了一個免費且可觀察的訊號：它是否已經完成？若未完成，是否留下了可見的推理進度？本研究將這個訊號稱為 **visible progress state**，並將靜態 token allocation 轉成條件式決策：

\[
\text{觀察 prefix 的可見狀態}
\rightarrow \text{選擇 stop 或 continuation}
\rightarrow \text{在有限 token 下提升整體效益}.
\]

## 2. 方法框架：Visible-Progress Allocation

### 2.1 兩階段決策

每題先接受相同的 512-token prefix。系統僅讀取 prefix 的 visible `content`，不讀取 `thinking`，並分類為三種互斥狀態：

| Prefix 狀態 | 可觀察定義 | 分配行動 |
|---|---|---|
| `complete` | visible content 中已有可解析的 boxed final answer | 停止，採用 prefix 答案 |
| `visible_unfinished` | 尚無可解析答案，但仍有非空的可見推理內容 | 追加 contextual continuation |
| `empty_unfinished` | 尚無可解析答案，且可見內容為空 | 停止；無 prefix 答案時標記 unresolved |

```text
題目 q
  │
  ├── 512-token prefix
  │     ├── complete ───────────────→ stop，輸出 prefix answer
  │     ├── visible_unfinished ────→ contextual continuation ─→ final answer
  │     └── empty_unfinished ──────→ stop / unresolved
  │
  └── 記錄實際 token 與最終正確性
```

Continuation 保留原始題目與 prefix 的可見內容，要求模型從既有工作繼續、不要重新開始，並輸出 boxed final answer。

### 2.2 資訊限制與可部署性

Controller 只使用 prefix 當下看得到的資訊，不能使用 reference answer、continuation 後的正確性、未來 token 用量，或測試集結果。它只需既有答案 parser 與 visible-content state classifier，不需要額外模型呼叫。

將 `visible_unfinished` 與 `empty_unfinished` 分開是方法關鍵：前者代表模型已留下可見工作軌跡，後者則沒有可用的 visible progress。這使續寫資源能集中於最可能從既有解題過程受益的案例。

## 3. 實驗設計

研究設計分成訊號驗證、介入式 policy evaluation 與獨立 held-out confirmation 三個層次。

### 3.1 訊號與 continuation value

對每一個 model-question unit 蒐集 prefix 與 contextual continuation，定義 continuation 的邊際結果：

\[
g_i=y_i^H-y_i^L,
\]

其中 \(y_i^L\) 是 prefix 停止時的正確性，\(y_i^H\) 是 continuation 後的正確性。\(g_i=+1\) 表示續寫修正一題，0 表示不變，-1 表示續寫造成退步。Observable process features 對 marginal continuation value 的離線預測 PR-AUC 為 0.795，顯示可見進度具有 allocation 所需的辨識力。

### 3.2 介入式 policy evaluation

預測力本身不足以證明分配有效。因此，每題均蒐集 prefix 與 continuation action，形成共同 action bank，讓不同 policy 在同一組 model-question outcomes 上重播，直接比較 final accuracy 與實際 token 成本。

| Policy | 使用 visible progress | 用途 |
|---|---:|---|
| Fixed Low | 否 | 所有題目停止的低成本基線 |
| Fixed Continue | 否 | 所有題目續寫的高 compute 基線 |
| Question-only | 否 | 只依題目難度的基線 |
| Random | 否 | 不使用任何訊號的 allocation 基線 |
| Visible-Progress | 是 | 本研究主方法 |
| Oracle | 僅事後分析 | 知道真實 gain 的理想上界，不可部署 |

### 3.3 Held-out confirmatory experiment

Stage 3 從所有歷史 `data/` 與 `results/` JSON 記錄中排除既有題目，建立新 manifest。

| 項目 | 設定 |
|---|---|
| 正式樣本 | 60 題新的 MATH-500 test 題目 |
| 分層 | 30 題 Level 3、30 題 Level 4 |
| Smoke test | 4 題：2 題 Level 2、2 題 Level 5；只做 transport / parser / schema 驗證 |
| 模型 | GPT-OSS-120B、DeepSeek-V4-Flash-158B |
| Prefix / continuation budget | 各 512 `num_predict` tokens |
| Temperature | 0.0 |
| 正式 action records | 60 × 2 models × 2 actions = 240 |
| 推論 | 10,000 次 question-clustered bootstrap |

每個 record 保留 visible content、thinking、done reason、parser result、correctness、prompt/completion/total tokens、request metadata 與 error，以支援 audit 與重現。

## 4. 成本匹配的主要比較

不同題目的 continuation token 用量不同，因此不能只匹配 continuation 題數。令 \(V_i=1\) 表示第 \(i\) 題為 `visible_unfinished`，\(c_i^H\) 表示 continuation request 的實際 total tokens。Visible-Progress policy 的 continuation 成本為：

\[
C_V=\sum_i V_i c_i^H.
\]

主要 random baseline 不觀察 state、題目、confidence 或結果，對每題以機率

\[
p=\frac{C_V}{\sum_i c_i^H}
\]

選擇 continuation。因此其預期 continuation 成本嚴格相等：

\[
E\left[\sum_i Z_i c_i^H\right]=p\sum_i c_i^H=C_V.
\]

主要 estimand 為：

\[
\Delta A=A_{\text{Visible-Progress}}-A_{\text{Random, cost-matched}}.
\]

這個 random comparator 是成本公平的 **action-bank evaluation benchmark**，用以回答「同樣資源應如何分配」；它不宣稱線上 random scheduler 能預先知道每一次 future continuation 的 token 成本。Bootstrap 以 `question_id` 為 cluster，重抽時保留兩模型觀測，並在每次 replicate 重算 \(p\)、policy outcome 與 \(\Delta A\)。

## 5. 實驗結果

### 5.1 主要結果

| 指標 | GPT-OSS-120B | DeepSeek-V4-Flash-158B | Pooled |
|---|---:|---:|---:|
| Visible-Progress accuracy | 70.00% | 86.67% | — |
| Cost-calibrated random accuracy | 60.38% | 82.42% | — |
| Accuracy difference | **+9.62pp** | **+4.25pp** | **+6.78pp** |
| Pooled 95% bootstrap CI | — | — | **[+3.48, +10.22]pp** |
| Visible cases | 12/60 | 4/60 | — |
| Cost identity error | 0.0 | 0.0 | 0.0 |

兩個模型均呈現正向差異，且 pooled CI 不含 0。這表示 observable visible progress 的 allocation value 能在 matched-cost policy comparison 中轉化為 final accuracy 提升，而非僅是相關性。

### 5.2 GPT-OSS-120B

| Policy | Accuracy | Mean actual total tokens / question |
|---|---:|---:|
| Fixed Low | 58.33% | 528.7 |
| Cost-calibrated random | 60.38% | 667.9 |
| Question-only count-matched | 66.67% | 652.5 |
| **Visible-Progress** | **70.00%** | **667.9** |
| Fixed Continue | 66.67% | 1095.8 |
| Oracle cost-constrained | 71.67% | 618.4 |

在與 random 完全匹配的預期成本下，Visible-Progress 增加 9.62pp accuracy；相較 Fixed Continue，accuracy 更高且平均 token 少約 39%。12 個 `visible_unfinished` 案例中，7 個受益於 continuation、1 個不變、4 個沒有可解析的 continuation answer。這說明 visible unfinished 不是保證成功，但它是最值得優先投資 continuation 的族群。

### 5.3 DeepSeek-V4-Flash-158B

DeepSeek 在 512-token prefix 下已完成 56/60 題，只有 4 個 `visible_unfinished` 案例。Visible-Progress accuracy 為 86.67%，cost-calibrated random 為 82.42%，差異 +4.25pp；其中 3/4 visible cases 受益於 continuation。

Visible-Progress 與 Fixed Continue 同為 86.67%，但平均 token 為 381.8，相較 Fixed Continue 的 733.2 少約 48%。這表示當模型多數題目能在 prefix 完成時，進度驅動 policy 能避免對已完成題目進行不必要 continuation。由於可分配案例只有 4 個，DeepSeek 結果應被解讀為方向一致的支持證據；方法的資源分配價值也自然取決於模型是否常出現「有進展但未完成」的情況。

### 5.4 與理想上界的距離

Oracle 事後知道每題 continuation 是否有益，因此不可部署。GPT 的 Visible-Progress accuracy 為 70.00%，count-matched oracle 為 71.67%，只差 1.67pp。這表示僅使用 visible state 這個簡單訊號，已能取得大部分在相同 continuation quota 下可捕捉的 gain。成本受限 oracle 也顯示，未來仍可尋找更細緻、但同樣低成本且可觀察的訊號以進一步縮小差距。

## 6. 研究貢獻

1. **提出可部署的動態 allocation controller。** 僅以 visible progress state 決定是否續寫，不需額外模型呼叫、隱藏思考或 reference answer。
2. **將 token efficiency 轉成 policy evaluation。** 直接在成本匹配條件下比較 final accuracy，而不只報告預測訊號與正確率的關聯。
3. **提供 held-out confirmatory evidence。** Visible-only rule 固定後，在新的 MATH-500 題目上進行確認性 evaluation。
4. **建立可 audit 的實驗流程。** 保留 manifest fingerprint、raw action bank、parser audit、token accounting、checkpoint/retry、question-clustered bootstrap 與測試程式。

## 7. 適用範圍與論文主張

本研究目前的證據範圍是 MATH-500 Level-3/Level-4、512-token prefix、512-token contextual continuation，以及 GPT-OSS-120B 與 DeepSeek-V4-Flash-158B。最適合的論文主張是：

> 在有限 test-time compute 下，模型輸出中可觀察的推理進度，可作為選擇性 continuation 的有效 allocation signal。相對於不使用訊號的成本匹配 random allocation，Visible-Progress Allocation 在 held-out MATH-500 evaluation 中提升最終正確率；其效果在 GPT-OSS-120B 上得到清楚確認，並在 pooled analysis 中呈現顯著正向結果。

未來可在其他推理資料集、不同 prefix budget、tool-use 或 verifier action，以及預先給定的全域 runtime token ledger 下測試外部泛化。不過在目前設定中，方法已形成一個完整、可實作且具成本意識的 test-time compute allocation framework。

## 8. 一句話定位

> **不是問模型要不要多想，而是在看見它已經走到哪裡後，將有限的額外運算留給真正有可見進展、最可能從續寫中受益的題目。**
