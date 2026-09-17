# Stage 2：Process-gated evidence allocation plan

> 日期：2026-09-17
>
> 狀態：規劃階段；尚未呼叫 API
>
> 主張範圍：從 offline predictive feasibility 進入小型、真正有 action outcome 的介入式 pilot

## 1. 為什麼進入 Stage 2

Stage 1.5 證實 observable progress state 與額外運算收益有關，但 512 與 1024 的答案來自
獨立呼叫；因此它不能證明「在同一條 reasoning trajectory 繼續」一定會改善。

Stage 1.6 也已排除目前的 retrospective verbal confidence：

```text
P3 (process × confidence) - P0 (process-only)
PR-AUC = -0.002, clustered 95% CI [-0.009, 0.005]
```

所以 Stage 2 不再把「模型自述 0–100 信心」當 allocation controller，而改問：

> 在 process state 不足以決定下一步時，能否以低成本、可獨立觀察的 evidence（answer
> consistency 或 verifier）判斷該停止、繼續、重試或升級？

這與 verbal confidence 的差異是：

```text
Verbal confidence: 模型說自己多有把握。
Evidence signal:   獨立生成／檢查是否支持目前或候選答案。
```

## 2. 核心研究問題與主張

### RQ1：實際 continuation

在可用 API 介面下，將 512-token prefix 作為 assistant context 後再生成 512 tokens，是否能產生
可評分的 contextual continuation？它與 independent 1024 answer 的 accuracy/cost 關係為何？

### RQ2：Evidence quality

對 process state 不確定的案例，兩條短的 independent answer branches 的 agreement 是否能預測：

- branch consensus 是否正確；以及
- contextual continuation 是否有價值？

### RQ3：Allocation value

在相同或明確報告的實際 token cost 下，process-gated evidence policy 是否優於：

- fixed low budget；
- fixed continuation；
- random allocation；
- process-only allocation？

本階段的主要目標是 evidence allocation，不是宣稱 answer agreement 等同真實 correctness confidence。

## 3. 正式術語

### 3.1 Process state

維持 Stage 1.5/1.6 的 deterministic 定義：

```text
complete:
    512 response 有可解析的 boxed answer

visible_unfinished:
    無可解析答案，但 observable activity sequence 非空

empty_unfinished:
    無可解析答案，且 observable activity sequence 為空
```

`message.thinking` 必須與 `message.content` 分開保存。若 API 回傳 thinking，process extraction 必須
預先指定使用哪一個欄位；不得把空白 `content` 直接解讀成沒有內部推理。

### 3.2 Contextual continuation

本 API 目前未證明能暫停及恢復同一個 decoder state。因此本研究的 continuation 是：

```text
original user problem
  + assistant message containing the complete observed prefix
  + user instruction: continue from the existing work; do not restart
```

它是 **contextual continuation**，不是 native sampler resume。論文與報告禁止聲稱後者，除非 API
明確支援 continuation/cache state 並實測驗證。

### 3.3 Answer agreement

對同一題在獨立 context 生成 `k` 個候選解答。以 `normalize_answer()` 後的最終 boxed answer
分群：

\[
A = \max_a \frac{n_a}{k}
\]

其中：

- \(A=1\)：所有可解析候選答案一致。
- \(A\) 較低：候選解答分歧。
- 無法解析的 branch 需保留為 `unparsed`，不可悄悄移除。

對數學題，第一版用 normalized final-answer agreement；不需要先導入 embedding/NLI semantic
entropy。若答案表面形式差異仍造成誤分群，先修 parser／normalizer，再考慮語義分群。

### 3.4 Action outcome

每一個 action 都保存其 own answer、correctness 與實際 token：

```text
stop                 : 接受 512 prefix 的答案；無答案即 invalid/incorrect
continue             : 512-prefix contextual continuation
resample_vote        : independent branches 的 majority/consensus answer
verify               : verifier 的 accept/reject/uncertain output
escalate             : 預留給後續，不在第一個 pilot 實作
```

不使用 Phase 3 的 independent 1024 outcome 當 Stage 2 的 action outcome。

## 4. 先決條件：資料與 parser

在任何 Stage 2 結果前，完成以下事項：

1. 修正已知 harmless LaTex equivalences，例如 `2\\sqrt5` vs `2\\sqrt{5}`、`4210_5` vs
   `4210_{5}`。
2. 新增對應 unit tests。
3. 使用原始 `phase3_raw.json` 重建並重跑 Stage 1.5/1.6，讓最終 offline baseline 使用一致 labels。
4. 建立一份 Stage 2 未見題目清單，與 Phase 3 60 題完全不重複。

Stage 2 的 online outcome 仍以最新 `answer_utils.py` 評分，但所有 parser failure 都要輸出 audit。

## 5. Gate 0：API capability and format smoke test

此關卡只確認介面與資料契約，未通過就不進行付費主實驗。

### 5.1 Models and questions

```text
Models: GPT-OSS-120B, DeepSeek-V4-Flash-158B
Questions: 10 unseen MATH-500 Level 3/4 questions
Temperature: 0.0 for prefix/continuation/fresh-high comparison
```

總共 20 model-question units。

### 5.2 Per-unit calls

| Call | Budget | 用途 |
|---|---:|---|
| `prefix` | 512 | 產生低預算 observable state |
| `continue` | 512 | 用完整 prefix 作 assistant context 後接續 |
| `fresh_high` | 1024 | independent 1024 baseline，不作 causal label |

總計：`10 × 2 × 3 = 60` calls。

### 5.3 Required raw fields

每個 call 保存：

```text
run_id, case_id, model, question_id, action, parent_call_id,
messages_sent, content, thinking, done_reason,
prompt_tokens, completion_tokens, total_tokens, elapsed, error,
parsed_answer, normalized_answer, correct
```

continuation 另保存：

```text
prefix_content_chars, prefix_thinking_chars,
assistant_context_chars, continuation_instruction,
context_mode = "contextual_continuation"
```

不得只保存 aggregate accuracy 或 token averages。

### 5.4 P(True) capability check

針對每個模型額外做 2 題 API response inspection：

```text
Does the response expose per-token logprobs/probabilities for a forced True/False token?
```

若有可用 logprobs，後續可加入 P(True) comparator；若沒有，禁止把輸出的文字 `True`/`False`
誤稱為 P(True)，它仍只是 verbal self-assessment。

### 5.5 Gate 0 Go/No-go

進入 Gate 1 的必要條件：

- 所有成功 calls 都保存 content、thinking（若存在）、done_reason 與 token fields。
- continuation 的 context contract 可人工抽查，未發生大量重新解題或 prompt formatting failure。
- 至少 90% prefix/continuation calls 不發生 API error。
- 至少 80% continuation 產生可解析 final answer；低於此值先修 prompt/interface。
- 每個模型至少有一個 non-empty thinking example 或明確記錄 API 不提供 thinking。

Gate 0 的目的不是測試顯著性；不可根據 10 題結果宣稱 policy 優越。

## 6. Gate 1：Evidence-signal feasibility smoke test

僅在 Gate 0 通過後執行。它檢查 answer agreement 是否可量測且具有足夠 variation。

### 6.1 Population

```text
20 additional unseen questions × 2 models = 40 units
```

每個 unit 先跑 512-token prefix，並記錄 process state。

### 6.2 Actions collected for every unit

| Action | Budget / setting | 用途 |
|---|---|---|
| `prefix` | 512, temperature 0.0 | state 與低預算 outcome |
| `continue` | 512, temperature 0.0 | 實際 continuation outcome |

### 6.3 Actions collected only for `empty_unfinished`

| Action | Budget / setting | 用途 |
|---|---|---|
| `branch_1` | 256, temperature 0.7 | independent concise solution |
| `branch_2` | 256, temperature 0.7 | independent concise solution |

Branch prompt 必須要求：

```text
Solve independently. Keep the reasoning concise.
End with exactly one final answer in \boxed{}.
```

不得把 prefix 或第一個 branch 放入第二個 branch context，否則不再是 independent evidence。

以既有 empty rate 約 40% 粗估，預計 calls：

```text
40 prefix + 40 continuation + about 32 branches = about 112 calls
```

實際數量必須由 raw log 報告，不可使用估計值取代。

### 6.4 Analysis

主要描述：

- prefix state distribution。
- branch parse rate。
- `agree` / `disagree` / `unparsed` 比例。
- branch consensus accuracy。
- continuation accuracy。
- \(P(\text{continue correct} \mid agree)\) 與
  \(P(\text{continue correct} \mid disagree)\)。
- \(P(\text{consensus correct} \mid agree)\)。
- 實際 action-level prompt/completion/total token cost。

重要：agreement 是 evidence signal，不假設其方向。只有資料支持時，才能決定
`agree → stop/vote` 或 `disagree → continue/verify`。

### 6.5 Gate 1 Go/No-go

進入正式 interventional pilot 前，需同時達到：

1. `branch_1/2` 的最終答案 parse rate ≥ 90%。
2. `agree` 與 `disagree` 都至少出現 6 個可分析 cases；這是 feasibility
   門檻，不是效果顯著性的門檻。若幾乎全一致或全不一致，訊號無法識別。
3. agreement 或 consensus accuracy 顯示與 continuation outcome 有可觀察差異，且方向在兩模型間不完全相反。
4. 分支成本不明顯高於它可能取代的 action；否則只可作診斷，不可進入 allocation controller。

若未通過，停止 answer-consistency 路線，改做 process-gated verifier feasibility，而非再調 verbal
confidence wording。

## 7. Stage 2 formal interventional pilot

只有 Gate 0/1 均通過才開始。

### 7.1 Design

```text
2 models × 60 unseen questions × 1 replicate
```

第一版使用一個 replicate，因為真正的 action outcomes 與實際 token 比更多相同 deterministic
replicates 優先。若 temperature sampling 是 policy 的一部分，branch seeds 必須保存。

### 7.2 Candidate policies

所有 policy 都在相同問題集上執行，保留每個 action 的實際結果；事後不得只挑成本較低的 action。

| Policy | `complete` | `visible_unfinished` | `empty_unfinished` |
|---|---|---|---|
| Fixed Low | stop | stop | stop |
| Fixed Continue | continue | continue | continue |
| Process-only | stop | continue | 預先鎖定的 continue quota |
| Process + evidence | stop | continue | 兩個 short branches；依預註冊 agreement rule 選 vote / continue / verify |
| Random matched-budget | random | random | random |

`empty_unfinished` 的最終 rule 必須使用 Gate 1 後、正式 pilot 前鎖定；不得在正式 60 題結果上再選
threshold。可能的預註冊形式為：

```text
if two branches agree and their answer is parseable:
    return branch consensus
else:
    contextual continuation
```

這個 policy 的高成本 branch+continue path 必須完整計入；不得只報告 agree cases 的成本。

若 Gate 1 顯示此 rule 沒有成本可行性，正式 pilot 改為 `process-gated verifier`，而不是硬跑。

### 7.3 Evaluation

Primary outcome：每個 policy 的 action-level final accuracy 與 mean **actual total tokens**。

Primary comparison：

```text
Process + evidence vs Process-only
```

報告：

- accuracy、exact 95% paired/bootstrap CI。
- prompt tokens、completion tokens、total tokens、latency 分開報告。
- accuracy-cost Pareto curve，不只固定 upgrade rate。
- 每個 state 的 action distribution 與 correctness。
- branch agreement／disagreement／unparsed audit。
- model-wise results；不可只報 pooled result。
- harm：較昂貴 action 把可用答案改壞的比例。

Bootstrap / permutation unit 為 `question_id`；同一題跨模型結果不可被當成獨立題目證據。

### 7.4 Formal Go/No-go

支持方法方向，至少需：

1. Process + evidence 在 paired question analysis 中優於 Process-only，且 CI 不支持只是隨機波動。
2. 改善不是由單一模型或少數幾題驅動。
3. 在相近 actual total-token cost 下改善 accuracy，或在相近 accuracy 下減少 token。
4. `empty_unfinished` action rule 顯示可解釋、可重複的 benefit。
5. 原始 logs 可以重算每一項指標。

若 evidence 有 correctness signal、但成本使政策不 Pareto-improving，結論必須是：

> Evidence is diagnostically informative but not yet a cost-effective allocation signal.

若 process-only 仍優於 evidence policy，將 verbal confidence 與 branch agreement 都定位為經檢驗後未超越
observable progress 的候選訊號；下一步再考慮 verifier 或外部工具，而不是持續增加 sample 數。

## 8. Optional Stage 2D：Process-gated verifier

只有 answer-consistency Gate 1 失敗，或 formal pilot 顯示 agreement 無法成本有效時才做。

Verifier 不是 self-confidence。其輸入應是：

```text
question + candidate answer + concise visible reasoning
```

輸出採固定 schema：

```json
{"verdict":"pass|fail|uncertain","error_type":"...","brief_reason":"..."}
```

比較三種 verifier source：

- 同模型但獨立 verifier prompt。
- 較便宜的不同模型。
- 對可支援題型使用 deterministic math verification。

Verifier 必須與 answer generator 分開保存 model、prompt、tokens、error，且只在 process-gated ambiguous
cases 啟動。不能把 verifier 的文字 `pass` 稱為 calibrated probability。

## 9. P(True) comparator：僅在 API 支援時加入

若 Gate 0 證實可取得 token-level logprob，加入：

```text
P(True) = P(token "1" | prompt that asks whether this proposed answer is correct)
```

它應只作 candidate-path ranking／evidence weighting comparator，不應直接替代 action-level benefit
evaluation。若 API 沒有 logprob，跳過此 comparator；輸出 `True/False` 文字仍是 verbal confidence，
不視為 P(True)。

## 10. Reproducibility contract

Gate 0/1 實作目前提供：

```text
data/process_stage2_questions.json
results/process_stage2_raw.json
results/process_stage2_analysis.json
results/process_stage2_report.md
results/process_stage2_audit.json
```

正式 interventional pilot 通過 Gate 0/1 後，才額外產生 policy dataset 與
accuracy-cost figure；不能在尚未鎖定 policy rule 前虛構這些輸出。

每份輸出保存：

- source question IDs 與 Phase 3 overlap check。
- script Git commit。
- model mapping、temperature、seed、budget、prompt template version。
- raw response content/thinking/done_reason/token counts。
- parser version／answer normalizer audit。
- policy rule version。

## 11. Agent implementation order

1. 修 parser equivalence 與 tests，重建 Stage 1.5/1.6 labels。
2. 執行 `prepare_process_stage2_questions.py`，建立並人工檢查 held-out manifest。
3. 以 `run_process_stage2.py --stage gate0` 執行 Gate 0；未加 `--execute` 時必須是 dry run。
4. 檢視 raw logs 與 `analyze_process_stage2.py` 報告；未通過時先修介面，不跑 Gate 1。
5. 以同一 runner 執行 Gate 1；保存 every branch，不刪除 parse failures。
6. 根據 **Gate 1 held-out results** 鎖定 empty-state rule。
7. 在正式 policy rule 鎖定後，擴充同一 runner 的 formal action collection 與 paired analysis；不得從 independent Phase 3 high call 借用結果。

## 12. 目前不應做的事

- 不再重跑同型 0–100 retrospective confidence prompt。
- 不把 Soft QOQ/Soft IDS 的 prompt-budget 當作實際 token cost。
- 不因 answer agreement 高就宣稱答案正確。
- 不把 stateless contextual continuation 說成 native resume。
- 不用正式 pilot outcome 反過來挑 agreement threshold。
- 不在未確認 logprob 的情況下宣稱使用 P(True)。

## 13. Current script commands

以下命令不會自動執行 API；僅最後兩個有 `--execute` 的命令會產生模型呼叫：

```bash
python3 experiments/v3-budget-pilot/prepare_process_stage2_questions.py
python3 experiments/v3-budget-pilot/run_process_stage2.py --stage gate0
python3 experiments/v3-budget-pilot/run_process_stage2.py --stage gate0 --execute
python3 experiments/v3-budget-pilot/analyze_process_stage2.py
```

Gate 0 通過並經人工 review 後，才可執行：

```bash
python3 experiments/v3-budget-pilot/run_process_stage2.py --stage gate1 --execute
python3 experiments/v3-budget-pilot/analyze_process_stage2.py
```
