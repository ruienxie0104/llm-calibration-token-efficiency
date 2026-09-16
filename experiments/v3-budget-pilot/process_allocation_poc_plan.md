# Process- and Confidence-Aware Allocation：Offline PoC 計畫

> 狀態：腳本已設計，尚未執行
>
> 原則：第一階段不呼叫 API；只使用 Phase 3 Hard-budget 原始資料。
>
> 日期：2026-09-17

## 1. 這個 PoC 要回答什麼

研究問題不是「模型現在答對了嗎」，而是：

> 在 Hard 512-token 的可觀察推理前綴下，流程狀態能否在題目特徵、實際
> token 使用量與模型信心之外，額外預測增加到 1024 tokens 是否有收益？

定義：

- `Y_L`：Hard 512 下是否正確。
- `Y_H`：Hard 1024 下是否正確。
- `gain = Y_H - Y_L`。
- `benefit = 1(Y_L = 0 and Y_H = 1)`。

Primary prediction target 是 `benefit`。Secondary analysis 保留 `gain=-1` 的 harm cases，
避免把高預算改壞答案的案例藏起來。

## 2. 研究定位與限制

Phase 3 的 512/1024 是兩次獨立呼叫，不是同一生成在 512 tokens 暫停後繼續。
因此本 PoC 只能證明 predictive feasibility：

```text
512-token observable process prefix
                ↓
predict independent 1024-budget improvement
```

不能把結果寫成 causal continuation effect。若 offline PoC 通過，才進行真正的
pause/continue interventional pilot。

Soft budget-range 不納入主要訓練資料，因為 Soft 64–2048 沒有可靠控制實際成本，
且準確率幾乎不變，缺少可識別的 treatment 與 gain variation。

## 3. 輸入資料

必要輸入：

```text
experiments/v3-budget-pilot/results/phase3_raw.json
experiments/v3-budget-pilot/data/phase3_questions.json
```

`phase3_raw.json` 目前未追蹤於 Git。執行 Agent 必須從原始實驗保存位置取得，或使用：

```bash
python experiments/v3-budget-pilot/build_process_poc_dataset.py \
  --raw /absolute/path/to/phase3_raw.json
```

禁止從 summary accuracy 反推 individual labels。

## 4. Phase A：資料完整性與 gain dataset

執行：

```bash
python experiments/v3-budget-pilot/build_process_poc_dataset.py
```

腳本會：

1. 只讀取 `call_type=answer/confidence`。
2. 用 `(model, question_id, replicate)` 嚴格配對 512/1024。
3. 若有重複或缺少 pair，直接停止。
4. 不使用歷史 `correct` 欄位，從 raw content 重新擷取 `\boxed{}` 並評分。
5. 支援 `\frac`、`\dfrac`、`\tfrac` 與常見無大括號單字元 fraction。
6. 從 512 response 建立 activity sequence 與 process features。
7. 合併 512 retrospective confidence，並保留該 confidence call 的 prompt/completion cost。
8. 計算 low/high accuracy、benefit、harm、prefix similarity。

輸出：

```text
results/process_poc_dataset.json
results/process_poc_dataset_audit.md
```

### 資料 Go/No-Go

進入 prediction analysis 前確認：

- 至少有 10–15% `benefit=1`。
- 至少兩個模型各自具有足夠 positive cases。
- 不能有無法解釋的大量 unpaired rows。
- 人工抽查 parser disagreements 和 harm cases。
- 檢查三個 replicates 是否完全相同；若相同，不得將它們宣稱為獨立樣本。

## 5. Phase B：Observable process event log

活動集合固定為：

```text
understand_setup, recall, plan, calculate, reason,
verify, backtrack, conclude, other
```

每個 event 保存：

```text
case_id, event_index, activity, observable_segment
```

第一版採 deterministic rules，避免額外 LLM 標記成本。正式解讀前須抽查至少
100–200 segments。若有兩位標註者，建議回報 Cohen's kappa。

### Trace-level features

- step count、unique activity count、activity entropy。
- 各 activity count/share。
- last activity。
- verify/backtrack/conclude presence。
- repeated activity loop count。
- directly-follows transition counts。

### Fold-local process features

每一個 training fold 分別建立：

- all-case DFG。
- benefit-case DFG。
- no-benefit-case DFG。

再對 validation/test prefix 計算：

- mean transition log-probability。
- unseen-transition share。
- benefit-vs-no-benefit DFG likelihood advantage。

禁止先用完整資料建立 DFG 再做 cross-validation。

## 6. Phase C：Feature ablation

| Model | Features |
|---|---|
| M0 Context | level、question length、subject、model identity |
| M1 Runtime | M0 + completion tokens、near-cap、parsed-answer presence |
| M2 Confidence | M1 + retrospective confidence |
| M3 Process | M1 + trace/DFG process features |
| M4 Combined | M1 + confidence + process features |

Primary contrast：

```text
M4 Combined vs M2 Confidence
```

如果 M4 沒有優於最強的非流程 baseline，就不能宣稱 process mining 有增量價值。

模型使用 L2-regularized logistic regression。小樣本 PoC 不使用深度模型。

## 7. Validation design

Primary：5-fold grouped cross-validation。

```text
group = question_id
```

同一道題的所有 models、budgets、replicates 必須留在同一 fold。

Secondary：leave-one-model-out。每次用三個模型訓練，在第四個完全未見模型測試，
檢查 process signal 是否只記住模型寫作風格。

評估：

- PR-AUC（primary）。
- AUROC。
- Brier score。
- Log loss。
- M4−M2 PR-AUC 的 question-clustered bootstrap 95% CI。

執行：

```bash
python experiments/v3-budget-pilot/analyze_process_value.py
```

## 8. Phase D：Matched-cost allocation simulation

模擬只能升級 25%、50%、75% cases 時的結果：

- Fixed Low。
- Fixed High。
- Random expected allocation。
- Confidence-only。
- Process-only。
- Process + Confidence。
- Oracle。

每題最終 correctness：

```text
selected for upgrade → Y_H
not selected         → Y_L
```

成本 proxy：

```text
low completion tokens
+ selected * max(0, high completion tokens - low completion tokens)
+ confidence-call cost, if the policy uses confidence
```

注意：incremental cost 是 proxy，不是實測 continuation cost。M2/M4 必須支付 confidence
prompt + completion tokens，process extraction 第一版視為 local compute，不增加 API tokens。

輸出：

```text
results/process_poc_analysis.json
results/process_poc_report.md
results/process_poc_accuracy_cost.png
```

## 9. 建議 Go/No-Go 標準

至少滿足下列兩項才進入線上 pilot：

1. M4 相較最強非流程 baseline 的 PR-AUC 增加至少 0.05。
2. Cluster bootstrap improvement 大部分位於零以上。
3. Leave-one-model-out 至少 3/4 模型方向一致。
4. 相同 cost proxy 下 accuracy 提升至少 2 percentage points。
5. 相較 confidence-only，額外追回至少 20% oracle gap。

若 answer presence 單獨就解釋幾乎所有 benefit，不視為 process-mining success。

## 10. Offline PoC 通過後

在付費 pilot 前，必須先執行 [Stage 1.5 robustness plan](process_stage1_5_plan.md)，排除
answer/conclude shortcut、分開 empty/non-empty traces，並改用 equal Hard-token budget 比較。
只有 Stage 1.5 的 unfinished conditional analysis 仍支持 structural process signal，才進入下列
interventional pilot。

第二階段才進行真正 interventional pilot：

1. 2 models：GPT-120B、DeepSeek。
2. 60 道未見題目。
3. 先生成 Hard 512 prefix。
4. 擷取 prefix process state 與 structured confidence。
5. 讓同一軌跡繼續最多 512 tokens。
6. 比較 stop/continue potential outcomes。

預估 120 prefix + 120 confidence + 120 continuation = 360 calls。在完整實驗前先用
10–20 題確認 API 能可靠延續 partial reasoning；否則 action space 改為 resample、verify
或 model escalation。

## 11. 執行前 checklist

- [ ] 找到原始 `phase3_raw.json`，確認不是摘要或截斷版本。
- [ ] 執行 answer/parser tests。
- [ ] 建立 dataset audit，人工檢查等價答案與 harm cases。
- [ ] 人工抽查 activity labels。
- [ ] 確認 grouped split 沒有 question leakage。
- [ ] 確認 DFG 只使用 training fold。
- [ ] 預先鎖定 Go/No-Go 門檻。
- [ ] 執行 offline prediction 與 policy simulation。
- [ ] Agent 審查報告後，才決定是否啟動付費 interventional pilot。
