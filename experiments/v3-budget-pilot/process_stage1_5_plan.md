# Stage 1.5：Process Signal Robustness Plan

> 日期：2026-09-17
>
> 狀態：分析腳本已完成，尚未執行
>
> 成本：Offline only，不呼叫模型 API

## 1. 為什麼需要 Stage 1.5

Stage 1 得到正面的 predictive-feasibility 結果：

- M1 runtime PR-AUC = 0.616。
- M2 confidence PR-AUC = 0.614。
- M3 process PR-AUC = 0.795。
- M4 process + confidence PR-AUC = 0.796。
- M4−M2 PR-AUC = +0.182，question-cluster bootstrap 95% CI [0.064, 0.276]。

但進一步診斷發現：

- 512 tokens 無可解析答案時，約 49.9% 可由 1024-budget answer 救回。
- 512 tokens 已有答案時，只有約 1.7% 受益。
- near-cap cases 約 49.5% 受益；非 near-cap cases 約 0.4% 受益。
- 最強 process features 多為 `conclude` presence、last activity 與輸出是否為空。
- 287/720 cases 沒有 observable activity sequence。

因此 Stage 1 尚未排除：模型只是在辨識「是否完成」，而不是真正使用流程結構預測
額外 compute 的價值。

## 2. Primary research question

> 在已知 512-token response 尚未產生可解析答案時，移除所有 conclude／answer-equivalent
> 特徵後，非結論性的流程結構是否仍能預測 512→1024 的 benefit？

Primary cohort：

```text
low_has_parsed_answer = 0
```

Primary contrast：

```text
C4_structural - C0_completion PR-AUC
```

若 C4 在 unfinished cohort 沒有改善 C0，研究應定位為 completion/progress-aware
allocation，而不是 structural process-mining allocation。

## 3. Cohort design

Stage 1.5 同時報告四個 cohorts：

| Cohort | 定義 | 用途 |
|---|---|---|
| `all` | 所有 paired cases | 與 Stage 1 對照 |
| `unfinished` | 沒有 parsed answer | Primary analysis |
| `nonempty_unfinished` | unfinished 且有 activity sequence | 真正可觀察流程的適用範圍 |
| `empty_unfinished` | unfinished 且 sequence 為空 | 缺少流程訊號時的負向控制 |

所有 cross-validation 仍以 `question_id` 分組。同一題的模型與 replicates 不得跨 fold。

## 4. Feature ablation

| Profile | 特徵 | 要回答的問題 |
|---|---|---|
| C0 Completion | context、tokens、near-cap、answer presence | 最強簡單 baseline |
| C1 Last activity | C0 + empty + last non-conclusion activity | 單一進度狀態是否已足夠 |
| C2 Activity counts | C0 + 非結論活動 counts/shares/entropy | 流程組成是否有價值 |
| C3 DFG only | C0 + 移除 conclude 後的 fold-local DFG | transition/conformance 是否有價值 |
| C4 Structural | C0 + last + counts + structural DFG | Primary structural process model |
| C5 Full process | Stage 1 完整流程，包括 conclude | 測量 shortcut 帶來多少提升 |
| C6 Structural + confidence | C4 + confidence | confidence 是否有額外價值 |

### Structural feature exclusion

C1–C4 必須：

- 從 sequence 移除全部 `conclude` events。
- 不使用 `process_has_conclude`。
- 不使用 `process_last_conclude`。
- 不使用 `process_count_conclude` 或 `process_share_conclude`。
- 不使用包含 `conclude` 的 transitions。
- DFG 必須由移除 conclude 後的 training-fold sequence 建立。

C0 仍保留 `low_has_parsed_answer`，因為這是部署時可取得的必要 baseline；在 primary
unfinished cohort 中它自然是常數，無法提供區分力。

## 5. Validation

### Primary validation

- 5-fold GroupKFold equivalent，group=`question_id`。
- PR-AUC 為 primary metric。
- AUROC、Brier、log loss 為 secondary metrics。
- `C4−C0 PR-AUC` 使用 question-cluster bootstrap 95% CI。
- `C5−C4 PR-AUC` 衡量 conclude shortcut 的貢獻。

### Cross-model validation

在 unfinished cohort 執行 leave-one-model-out：

- C0 Completion。
- C4 Structural。
- C5 Full process。
- C6 Structural + confidence。

如果 structural signal 只在部分模型存在，必須報告 output-interface dependency，不得宣稱
完全跨模型泛化。

## 6. Equal Hard-token budget simulation

Stage 1 圖固定 upgrade rate，但不同政策的實際成本不同，因此不能稱為嚴格 matched-cost。

Stage 1.5 改用已知 worst-case Hard-cap increment：

```text
high_budget - low_budget = 1024 - 512 = 512 tokens
```

對每個 upgrade 預留完整 512-token 額度。在 25%、50%、75% nominal extra-budget levels
下，所有不使用 confidence 的政策具有相同可升級上限。

Confidence policy 必須先支付全部 confidence prompt + completion overhead；剩餘預算才能
用於 upgrade。如果 overhead 已超過 budget，標記 `nominal_budget_feasible=false`，不能在圖上
假裝與免費 process features 等成本。

另外報告：

- nominal reserved budget。
- observed realized completion-token proxy。
- final accuracy。
- upgraded case count。

注意：Phase 3 low/high 仍為獨立呼叫，realized increment 仍是 offline proxy。

## 7. Reproducibility improvements

`build_process_poc_dataset.py` 新增：

### Auditable event log

```text
results/process_poc_event_log.json
```

每個 event 保存：

```text
case_id
model
question_id
replicate
event_index
activity
segment_text
```

這讓 Agent／人工標註者可以抽查 activity labeling。若 event log 為空，必須明確保留該 case，
不能從資料中刪除。

### Parser change audit

```text
results/process_poc_parser_audit.json
```

列出 historical `correct` 與最新重新計分不同的所有案例，包括 parsed/expected answer。

### Source identity

Dataset、event log 與 parser audit metadata 保存 `phase3_raw.json` 的 SHA-256，確保不同 Agent
使用的是同一份 raw artifact。SHA-256 只驗證檔案身份，不代表實驗設計正確。

## 8. Outputs

重新建立 dataset：

```bash
python experiments/v3-budget-pilot/build_process_poc_dataset.py \
  --raw /absolute/path/to/phase3_raw.json
```

執行 Stage 1.5：

```bash
python experiments/v3-budget-pilot/analyze_process_stage1_5.py
```

預期輸出：

```text
results/process_poc_dataset.json
results/process_poc_dataset_audit.md
results/process_poc_event_log.json
results/process_poc_parser_audit.json
results/process_stage1_5_analysis.json
results/process_stage1_5_predictions.json
results/process_stage1_5_report.md
results/process_stage1_5_summary.png
```

`process_stage1_5_predictions.json` 保存每個 cohort 的 out-of-fold score，方便後續：

- 重算 metric。
- 查看 false positives/false negatives。
- 做 paired bootstrap。
- 確認圖表不是只由 aggregate summary 產生。

## 9. Go/No-Go interpretation

### 支持 structural process direction

需同時看到：

1. unfinished cohort 中 C4 明顯優於 C0。
2. nonempty unfinished cohort 中 improvement 仍存在。
3. C2/C3 至少一個顯示 counts 或 transitions 具有增量價值。
4. 不只是 C1 last-activity 單一特徵解釋全部改善。
5. 至少 3/4 held-out models 方向一致，或能清楚說明不一致的 observable-interface 邊界。
6. Equal Hard-token budget 下 C4 優於 C0/random。

### 只支持 progress-aware allocation

若：

- C1 已解釋全部改善；或
- C4 在 unfinished cohort 不優於 C0；或
- C5 有效但移除 conclude 的 C4 無效；

則合理結論是：

> Completion/progress state is useful for allocation, but richer process structure has not shown
> incremental value.

這仍是可用的方法結果，但不應以 process mining 作為主要 novelty。

### 不進入線上 pilot

若 unfinished/nonempty unfinished 中所有方法接近 random，停止 360-call continuation pilot，
先改善 observable trace logging 或重新定義 action。

## 10. Stage 1.5 通過後

先做 10–20 題 continuation smoke test，不直接跑完整 360 calls。新的 runner 必須保存：

- `message.content`。
- 若 API 提供，保存 `message.thinking`。
- `done_reason`。
- checkpoint 前後 token counts。
- continuation 是否沿用相同 context/assistant prefix。
- stop outcome 與 continue outcome。

只有確認同一軌跡能可靠繼續，才執行 2 models × 60 questions 的正式 interventional pilot。

## 11. Agent review checklist

- [ ] 確認 raw SHA-256 與原始 Phase 3 artifact 一致。
- [ ] 人工抽查 parser change list。
- [ ] 人工抽查至少 100–200 event segments。
- [ ] 確認 C1–C4 完全移除 conclude-related features。
- [ ] 確認 DFG 只由 training fold 建立。
- [ ] 確認 grouped split 沒有 question leakage。
- [ ] 確認 primary cohort 是 unfinished，而不是 all cases。
- [ ] 確認 confidence overhead 被計入固定 budget。
- [ ] 分開報告 empty/non-empty results。
- [ ] 不把 independent low/high calls 寫成 causal continuation。
