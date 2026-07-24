# 專案維護交接：環境建立與 High 問題修正

**更新日期：** 2026-07-24  
**適用範圍：** `llm-calibration-token-efficiency` 全專案  
**目前狀態：** 程式修正與單元測試已完成；套件尚未安裝，V2 尚未重新執行  
**重要：** 本文件建立時，以下變更仍在工作目錄中，尚未 commit

## 1. 後續 Agent 開始前必讀

1. 不要把目前的 `conformance_deepseek_ref.json` 或
   `entropy_step_analysis.json` 當成修正後結果；它們是舊程式產生的歷史輸出。
2. 不要在沒有新 Ollama API key 的情況下執行付費／遠端實驗。
3. 舊 Ollama key 曾存在 Git 歷史，不能重複使用。撤銷 key 和改寫 Git
   歷史都尚未完成。
4. V2 所有正式輸出都必須放在
   `experiments/v2-mmlu-arc/results/`，不要再建立
   `experiment_v2_results/` 或其他平行結果目錄。
5. 修改後至少執行：

   ```bash
   python -m compileall -q experiments scripts tests
   pytest -q
   git diff --check
   ```

6. 只有 `python scripts/check_v2_results.py` 成功，V2 結果才能標示為已驗證。

## 2. 本次已完成的改動

### 2.1 Python 環境與安全設定

- 建立 `pyproject.toml`，指定 Python `>=3.12,<3.14` 和固定的直接相依版本。
- 建立 `requirements.txt`、`requirements-dev.txt` 和 `.python-version`。
- 建立 `.env.example`；API 腳本改讀取：
  - `OLLAMA_API_KEY`
  - `OLLAMA_API_URL`
- 原始碼中已移除明文 Ollama key。
- 修正 `.gitignore` 原本黏在一起的 `*.logpilot_results/` 規則。
- 新增 `scripts/check_environment.py`，檢查 Python、套件、Graphviz 和 API
  環境變數。

### 2.2 Conformance checking

原問題：

- DeepSeek reference 腳本讀取不存在的 `deviation` 欄位，導致所有
  alignment deviations 都是 0。
- `signal.alarm()` 沒有 handler，逾時可能直接終止程序。
- 不同 PM4Py 版本可能回傳簡單或巢狀 alignment move。

已完成：

- 新增 `analysis_utils.count_alignment_deviations()`。
- 同時支援簡單 move 和 transition-aware 巢狀 move。
- 只計算 log move／model move，不計 synchronous move。
- TBR deviation 改成 `missing_tokens + remaining_tokens`。
- DeepSeek reference 腳本加入 300 秒 timeout handler 與明確的
  `alignment_timeout` 狀態。
- V2 主流程、`run_pm_step4.py`、`finish_pm.py` 全部改用同一套計數函式。

### 2.3 Levenshtein 與 Jensen–Shannon 分析

原問題：

- `(A, B)` 和 `(B, A)` 分別抽樣與重算，產生非對稱距離矩陣。
- 對角線使用 intra-model distance，而不是距離矩陣應有的 0。
- SciPy `jensenshannon()` 回傳 distance，程式卻標示成 divergence。

已完成：

- 抽樣由每組 trace 自身內容決定，結果可重現且不受參數順序影響。
- 模型 pair 只計算一次，再同時寫入 `[i, j]` 和 `[j, i]`。
- 距離矩陣對角線固定為 0。
- `jensenshannon(...) ** 2` 後才儲存為 Jensen–Shannon divergence。
- 新增對稱性單元測試。

### 2.4 Confidence 評估

原問題：

- 信心重跑只傳入 `response`，沒有傳入 `thinking`。
- reasoning 被截斷為 500／1000 字。
- checkpoint 只要存在就視為完成，部分結果無法續跑。
- checkpoint 與原始資料只靠陣列 index 對應。
- 新實驗仍先產生 context-free confidence。

已完成：

- 新增 `confidence_utils.make_confidence_prompt_with_context()`。
- confidence turn 使用完整 `thinking + response`，不再截斷。
- 新 V2 實驗第一次執行就使用完整多輪對話脈絡。
- checkpoint 支援續跑、錯誤重試及 `question_id` 一致性檢查。
- checkpoint 和正式輸出改用暫存檔加 `os.replace()` 原子寫入。
- 已移除退休的 GLM-4.7；正式實驗固定為四個模型。

### 2.5 API 失敗、續跑與資料污染

原問題：

- 以 list 長度判斷完成進度。
- API error 被記成答錯，且下次不會重試。
- error case 仍被強制建立 `understand → answer` trace。

已完成：

- V1、V2 都改用 `question_id` 判斷完成狀態。
- 失敗案例下次會重試並取代原位置，不會 append duplicate case。
- `build_traces()` 會排除有 `error` 的回應。
- accuracy、平均時間和平均 token 只使用成功回應。
- 如果完全沒有成功回應，分析會明確停止。

### 2.6 V2 artifact 流程

- 所有 V2 路徑改成相對於腳本位置解析，不再依賴目前 shell 工作目錄。
- 正式 artifact 統一命名：

  | Artifact | 用途 |
  | --- | --- |
  | `raw_responses_v2.json` | 完整且成功的 API 結果 |
  | `traces_final.json` | 有效 reasoning traces |
  | `calibration_final.json` | Calibration 指標 |
  | `conformance_final.json` | GLM-5.2 reference 結果 |
  | `conformance_deepseek_ref.json` | DeepSeek reference 結果 |
  | `discovery_final.json` | Process discovery 摘要 |
  | `entropy_step_analysis.json` | Entropy、Levenshtein、JSD |
  | `full_metrics_final.csv` | 最終彙整表 |

- `experiment_v2.py` 仍會逐題寫入被忽略的 `raw_responses.json`
  checkpoint；只有所有題目、模型、答案與 confidence 都成功，才會提升為
  `raw_responses_v2.json`。
- `.gitignore` 只允許正式 artifact 被追蹤，部分 checkpoint 仍保持忽略。
- 新增 `scripts/check_v2_results.py` 驗證 artifact 完整性、矩陣對稱性與對角線。
- 中英文 V2 報告頂端都已加入「舊數值尚未驗證」警告。

## 3. 已完成的驗證

目前驗證結果：

```text
pytest: 7 passed
compileall: passed
git diff --check: passed
```

測試涵蓋：

- 環境檔案與相依宣告存在。
- `.env.example` 沒有真實 key。
- alignment deviation 支援簡單與巢狀 move。
- token diagnostics 可處理整數與 mapping。
- pairwise distance 具對稱性與確定性。
- confidence context 保留超過 1000 字的完整 thinking。
- API error 會在下次執行被重試並取代，不會產生 duplicate case。
- 未完成 run 不會提升為正式 artifact；完成後才會提升。

## 4. 目前尚未完成／被阻擋的部分

### 4.1 V2 歷史原始資料缺失

目前缺少：

- `raw_responses_v2.json`
- `traces_final.json`
- `calibration_final.json`
- `conformance_final.json`
- `discovery_final.json`
- `full_metrics_final.csv`

現有 `entropy_step_analysis.json` 的 Levenshtein 矩陣不對稱，現有
`conformance_deepseek_ref.json` 也是舊 deviation 演算法產物。因缺少它們的
來源 trace，不能只靠修改 JSON 修復，必須重跑。

執行以下指令應該要失敗，這是目前的預期行為：

```bash
python scripts/check_v2_results.py
```

### 4.2 套件與系統依賴尚未安裝

目前本機仍缺：

- `datasets`
- `pm4py`
- `python-pptx`
- Graphviz `dot`

尚未執行端到端 PM4Py 流程。

### 4.3 外部安全操作尚未完成

- 舊 Ollama key 必須在供應商後台撤銷／輪替。
- 舊 key 仍存在 Git 歷史。
- GitHub Pages 仍會上傳整個 repository root。

這三項涉及外部狀態或破壞性 Git 歷史改寫，後續 Agent 不得自行假設已獲授權。

## 5. 下一步工作順序

### P0：完成憑證處理

1. 請使用者確認舊 Ollama key 已撤銷。
2. 建立新 key，只放在本機 `.env`。
3. 使用者明確授權後，才評估使用 `git filter-repo` 清除歷史並 force-push。
4. 將 GitHub Pages 部署來源由 `path: .` 改成明確的靜態網站輸出目錄。

完成標準：

- Git 目前版本與歷史掃描都找不到舊 key。
- Pages artifact 不包含 Python 原始碼、原始回應或 `.env`。

### P1：安裝與鎖定環境

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
brew install graphviz
python scripts/check_environment.py
```

安裝成功後產生實際 lockfile，記錄平台、Python 和完整 transitive
dependencies。不要只依賴直接相依版本。

完成標準：

- `check_environment.py` 成功。
- PM4Py 可輸出測試 Petri net 圖。
- 乾淨環境可以重建。

### P1：完整重跑 V2

此步驟會呼叫外部 API、產生費用，開始前需確認新 key、模型可用性和預算。

```bash
python experiments/v2-mmlu-arc/experiment_v2.py
python experiments/v2-mmlu-arc/run_pm_step4.py
python experiments/v2-mmlu-arc/run_entropy_step_analysis.py
python experiments/v2-mmlu-arc/run_conformance_deepseek_ref.py
python experiments/v2-mmlu-arc/generate_v2_figures.py
python scripts/check_v2_results.py
```

完成標準：

- 四模型各有 100 個成功 case。
- 無 answer error、confidence error 或 duplicate `question_id`。
- 八個正式 artifact 全部存在。
- Levenshtein 矩陣對稱且對角線為 0。
- `check_v2_results.py` 成功。

### P1：重算並更新報告

1. 由新 artifact 重算所有表格與圖。
2. 移除中英文報告頂端的未驗證警告。
3. 修正舊報告「所有 Brier < 0.05」與表格 `0.052` 的矛盾。
4. 不再宣稱舊的「DeepSeek reference alignment deviations 全為 0」結果。
5. 記錄資料集 revision、模型 ID／revision、API 參數和執行時間。

完成標準：

- 報告中的每個數值都能追溯到正式 artifact。
- 中英文表格一致。
- 圖表可以從程式重新生成。

### P2：改善研究方法

1. 修正 activity label precedence：
   `verify`／`reconsider` 應優先於一般 `reason` 關鍵字。
2. 修正 `"first.*then"` 被當成普通 substring 的問題。
3. 不應無條件強制加入 `understand` 和 `answer`，需區分觀察到的活動與
   pipeline 補值。
4. 建立人工標註樣本，計算 inter-rater reliability。
5. 對 accuracy、Brier、confidence gap 和 token metrics 加入 bootstrap
   confidence interval。
6. 四個模型點不足以支持「反相關」結論；報告應改成 exploratory
   observation，或增加模型數後正式檢定。
7. GLM-5.2／DeepSeek 的錯誤樣本只有 2／3 題，confidence-when-wrong
   不應做強結論。

完成標準：

- Labeling 有可量化的一致性驗證。
- 統計結論包含樣本數、effect size、CI 和檢定方法。
- 報告明確區分 observation、association 和 causality。

## 6. 建議後續 Agent 的第一個工作回合

1. 先執行 `git status --short`，確認本文件所述變更是否已 commit。
2. 執行 `pytest -q` 和 `python scripts/check_v2_results.py`。
3. 如果使用者尚未提供外部 API 執行授權，先完成不需 API 的 P2
   labeling 修正與測試。
4. 如果使用者要重跑，先確認：
   - 新 key 已設定；
   - API 預算；
   - 四個模型 ID 仍可用；
   - 是否接受重新抽取 100 題 benchmark。
5. 不要用手動編輯 JSON 的方式讓 artifact checker 通過。

## 7. 重要檔案索引

- 環境設定：`pyproject.toml`
- 環境檢查：`scripts/check_environment.py`
- V2 artifact 檢查：`scripts/check_v2_results.py`
- V2 主實驗：`experiments/v2-mmlu-arc/experiment_v2.py`
- Confidence 共用邏輯：`experiments/v2-mmlu-arc/confidence_utils.py`
- Conformance／distance 共用邏輯：`experiments/v2-mmlu-arc/analysis_utils.py`
- V2 artifact 說明：`experiments/v2-mmlu-arc/results/README.md`
- V2 英文報告：`experiments/v2-mmlu-arc/report/REPORT.md`
- V2 中文報告：`experiments/v2-mmlu-arc/report/REPORT_zh-TW.md`
- 回歸測試：`tests/test_project_environment.py`

