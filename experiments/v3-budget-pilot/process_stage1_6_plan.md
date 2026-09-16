# Stage 1.6：Process-conditioned confidence diagnosis

> 日期：2026-09-17
>
> 狀態：分析設計與腳本已完成；正式解讀前需先重建最新 parser 標籤
>
> 成本：Offline only，不呼叫模型 API

## 1. 研究目的

Stage 1.5 顯示，流程訊號的主要價值來自粗粒度進度狀態：

- 已完成且有可解析答案（`complete`）。
- 尚未完成，但有可觀察推理內容（`visible_unfinished`）。
- 尚未完成，而且 observable trace 為空（`empty_unfinished`）。

把所有案例混在一起時，process features 明顯優於 confidence；但在
`nonempty_unfinished` 內，細粒度結構沒有穩定區分力。這不等於 confidence 完全無用，因為
Stage 1/1.5 主要測試的是 confidence 的全域 main effect，尚未回答：

> 同一個 confidence，在不同流程狀態中是否代表不同意義？流程與信心不一致時，是否能預測
> 額外運算的價值？

Stage 1.6 因此不是再加入一個更複雜的 confidence prompt，而是使用現有 retrospective
confidence 做免費、離線的 conditional-value diagnosis。

## 2. 主要研究問題

### RQ1：Process-conditioned confidence

在控制 context、runtime 與 observable process state 後，confidence 是否仍能預測
512→1024 的 benefit？

### RQ2：Interaction 而非 main effect

`process_state × confidence` 是否優於：

1. process-only；以及
2. process + confidence 的 additive model？

若 interaction 有效但 additive 無效，代表 confidence 不是全域 allocation signal，而是必須依
流程狀態解讀。

### RQ3：Discordance

下列流程—信心不一致案例的 benefit rate 是否不同？

- 高信心＋未完成：可能是 premature confidence。
- 低信心＋已完成：可能是 conservative confidence。
- 高信心＋verify/conclude：流程與信心一致。
- 低信心＋空白：可能需要 retry/escalate，而不只是延長同一條推理。

### RQ4：取得成本

若 confidence 只在 process-only 決策邊界附近被詢問，計入 prompt + completion token overhead
後，是否仍能改善相同 nominal Hard-token budget 下的最終 accuracy？

## 3. Target 與研究單位

研究單位維持：

```text
model × question_id × replicate
```

Primary target：

```text
benefit = (low_correct == 0 and high_correct == 1)
```

它表示低預算答錯／未完成，但獨立的高預算呼叫答對。

重要限制：Phase 3 的 512 與 1024 是獨立呼叫，不是相同 trajectory 的 continuation，因此
`benefit` 是 observational counterfactual proxy，不能解讀成因果 continuation gain。

Secondary descriptive target：

```text
low_correct
```

這只用來檢查 retrospective confidence 對「當前答案正確性」的 calibration。因為 unfinished
案例沒有可解析答案，`low_correct` 幾乎由 completion state 決定；它不是 allocation primary
target。

## 4. Process state 定義

```text
complete:
    low_has_parsed_answer == 1

visible_unfinished:
    low_has_parsed_answer == 0 and activity_sequence 非空

empty_unfinished:
    low_has_parsed_answer == 0 and activity_sequence 為空
```

細粒度 process features 一律移除 `conclude`，避免把 answer presence 用另一個名稱重新放入模型。

## 5. 預註冊模型

| Profile | 特徵 | 目的 |
|---|---|---|
| `P0_process_only` | context + runtime + coarse state + non-conclusion process | 強 process baseline |
| `P1_confidence_only` | context + runtime + confidence | confidence main effect |
| `P2_additive` | P0 + confidence | 一般「把 confidence 加進去」做法 |
| `P3_state_interaction` | P2 + confidence × coarse state | **Primary model** |
| `P4_process_interaction` | P3 + confidence × selected process summaries | Exploratory fine-grained interaction |

### Context/runtime features

- level、question length、model、subject。
- low completion tokens、token fraction、near-cap。

### Non-conclusion process features

- trace 是否為空、step count、unique activities、entropy、loop count。
- verify/backtrack presence。
- 最後一個非 conclusion activity。
- 各非 conclusion activity 的 count/share。

### Confidence handling

- confidence 除以 100 映射到 `[0, 1]`。
- 缺失值只使用 training fold 的平均 confidence 補值。
- 額外加入 `confidence_missing`，避免把缺失誤認成真正的低信心。
- 所有 imputation、standardization 與模型 fitting 都只能使用 training fold。

## 6. Validation 與 primary contrasts

- 5-fold grouped cross-validation，group=`question_id`。
- 同一題的所有模型與 replicates 不得跨 fold。
- Primary metric：PR-AUC（target=`benefit`）。
- Secondary metrics：AUROC、Brier、log loss。
- 以 question-cluster bootstrap 建立 95% CI。

Primary contrast：

```text
P3_state_interaction - P0_process_only PR-AUC
```

Mechanism contrast：

```text
P3_state_interaction - P2_additive PR-AUC
```

若 P3 只優於 P1、卻不優於 P0，不能說 confidence 有 incremental value。

所有 profile 都先在完整資料上產生同一組 OOF predictions，再在下列 cohort 內評估，避免每個
cohort 重新訓練出不可直接比較的模型：

- `all`
- `complete`
- `visible_unfinished`
- `empty_unfinished`

另外執行 leave-one-model-out，檢查 interaction 是否只適用某個模型介面。

## 7. Calibration 與 discordance 診斷

### Current-correctness reliability

用 retrospective confidence 直接對 `low_correct` 計算：

- Brier score。
- fixed-bin ECE。
- reliability bins。

固定 bins：

```text
[0, 25), [25, 50), [50, 75), [75, 90), [90, 100]
```

此結果會依 `all`、三個 process states 與各模型分開報告。

### Discordance table

預先固定：

```text
low confidence:  c <= 75
mid confidence:  75 < c < 90
high confidence: c >= 90
```

每個 state × confidence band 報告：

- n。
- low/high accuracy。
- benefit/harm rate。
- mean confidence。
- mean confidence acquisition tokens。

這是描述性機制檢查，不使用結果反過來調整 threshold。

## 8. Selective-confidence policy simulation

對 nominal extra-budget 25%、50%、75% 分別模擬：

1. `process_only`：全部使用 P0 排序，不詢問 confidence。
2. `confidence_all`：全部使用 P3，向每個案例支付 confidence overhead。
3. `selective_10/25/50pct`：只對最接近 P0 upgrade cutoff 的 10%、25%、50% 案例使用 P3，
   其餘案例保留 P0 score。
4. `random_expected` 與 `oracle`。

每次 upgrade 先保留完整 Hard-cap increment：

```text
1024 - 512 = 512 tokens
```

confidence prompt + completion overhead 必須先從 nominal budget 扣除，剩餘額度才能 upgrade。
同時報告 realized completion-token proxy。

限制：confidence cost 同時包含 prompt/completion tokens，但 low/high proxy 只使用 completion tokens；
這是保守的 acquisition-cost accounting，不等同實際金額或 latency。

## 9. Go／No-go 判準

### Scientific interaction Go

需同時滿足：

1. P3−P0 primary PR-AUC delta 為正，且 question-cluster bootstrap 95% CI 不含 0。
2. P3 優於 P2，證明效果來自 conditional interpretation，而不只是多一個欄位。
3. 改善至少出現在一個同時含足夠正負例的 unfinished state，而不是只由 `complete` 的極少數
   positive cases 造成。
4. leave-one-model-out 不得完全由單一模型支撐；若只在部分模型成立，必須定位為
   model/interface-dependent。

### Operational allocation Go

需看到：

1. 至少一個 selective policy 在相同 nominal budget 下優於 process-only。
2. 改善至少出現在 3 個 budget levels 中的 2 個。
3. 不能依賴向所有案例取得昂貴 confidence 才成立。

### Diagnostic-only result

若 interaction 有訊號，但計入 confidence cost 後沒有改善，結論是：

> Confidence has conditional diagnostic value but is not yet a cost-effective allocation input.

下一步應設計低成本 inline/action-specific confidence，而不是直接上完整 online pilot。

### Confidence No-go

若 P3 不優於 P0，且 selective policy 不改善，則不應為了 novelty 把 confidence 硬放進 controller。
可保留的重要負面結論是：

> Observable progress is more useful than retrospective self-confidence for allocation, even after
> conditioning confidence on process state.

## 10. 正式執行前置條件

目前 `process_poc_parser_audit.json` 仍有 14 筆 `stored_correct=true`、`rescored_correct=false` 的
表面等價 LaTeX 案例，例如：

- `2\sqrt5` vs `2\sqrt{5}`。
- `4210_5` vs `4210_{5}`。

正式解讀 Stage 1.6 前必須：

1. 保守修正上述 harmless formatting normalization。
2. 使用原始 `phase3_raw.json` 重建 `process_poc_dataset.json`。
3. 重新執行 Stage 1.5，確認 labels 與基線。
4. 人工抽查 event labeling；尤其避免把一般否定詞誤標成 backtrack。

本機 repository 沒有追蹤 `phase3_raw.json`，因此 Agent 執行時需要提供原始檔案路徑。

## 11. 執行方式與輸出

先重建資料：

```bash
python experiments/v3-budget-pilot/build_process_poc_dataset.py \
  --raw /absolute/path/to/phase3_raw.json
```

再執行 Stage 1.6：

```bash
python experiments/v3-budget-pilot/analyze_process_confidence_stage1_6.py
```

預期輸出：

```text
results/process_stage1_6_analysis.json
results/process_stage1_6_predictions.json
results/process_stage1_6_report.md
results/process_stage1_6_summary.png
```

## 12. 本階段不回答的問題

- 不證明 512 response 在相同 context 中繼續生成後一定改善。
- 不證明新的 action-specific confidence 已有效。
- 不把空白 content 等同於沒有內部 reasoning；API 若提供 `message.thinking`，後續 runner 必須保存。
- 不以 retrospective confidence 的高成本否定所有低成本 confidence 取得方式。
- 不在看到結果後重新選 confidence threshold、cohort 或 primary metric。
