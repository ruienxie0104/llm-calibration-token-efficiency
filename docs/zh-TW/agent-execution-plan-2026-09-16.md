---
> **歷史文件** — 已被 docs/zh-TW/research-narrative-2026-09-11.md 取代。保留僅供參考。

# 專案後續處理執行計畫（提供 Agent 交接）

> 日期：2026-09-16  
> 適用專案：`llm-calibration-token-efficiency`  
> 目的：將目前已發現的技術、資料、研究方法與文件問題，拆成可依序執行、可驗證、可交接的工作項目。

## 0. 執行原則

1. 先修正資料與評分管線，再重新解讀研究結論；不可在評分器未確認前直接撰寫最終結果。
2. 所有模型呼叫都必須保留原始輸出、請求設定、錯誤資訊與可重跑的 metadata。
3. Hard Budget 與 Soft Budget 必須分開報告；Soft 的實際 token 超額不可當成等資源比較。
4. 每一項工作都要有完成條件（acceptance criteria）與可重現的驗證指令。
5. 不要覆寫既有結果；重新評分或重新實驗要使用新的版本化輸出目錄。

## 1. P0：修正數學答案解析與重新評分

### 問題

目前對 `\\boxed{...}` 使用的簡單正則式無法正確處理巢狀 LaTeX，例如 `\\boxed{\\frac{2}{21}}` 可能被截成 `\\frac{2`。這會把模型實際答對的答案標成錯誤，直接影響所有 accuracy、Brier、LCAE 與 budget 曲線。

### 處理內容

1. 找出共用答案解析函式與所有呼叫位置。
2. 實作 brace-aware parser：從 `\\boxed{` 開始計算大括號深度，直到配對的最外層 `}`。
3. 建立答案正規化層，至少處理：
   - 巢狀分數與 LaTeX 指令。
   - 整數、小數、負號、千分位。
   - 等價分數與可安全轉換的數值形式。
   - `\\frac{a}{b}` 與 `a/b` 的等價比較。
4. 對無法解析的答案回傳明確狀態（例如 `unparsed`），不可靜默視為錯誤。
5. 加入單元測試與錯誤案例 fixture。
6. 對所有既有 raw／derived 結果重新評分，輸出新版本資料，不覆蓋舊檔。

### 建議檔案

- `experiments/v3-budget-pilot/` 內的 answer parser、分析腳本與結果產生腳本。
- `tests/` 新增 parser 測試。

### 驗證方式

```bash
pytest -q
python3 scripts/check_v2_results.py
```

另需輸出一份 parser audit：列出原始答案、舊解析、 新解析與是否改判，並人工抽查至少 30 筆。

### 完成條件

- 巢狀 `\\boxed{}` 測試全部通過。
- 舊資料重新評分完成，並報告改判數量。
- 研究文件清楚標註哪些數字因 parser 修正而改變。

## 2. P0：補齊 Phase 3 原始資料與可重現性

### 問題

文件引用 `phase3_raw.json`，但 repository 主要只有衍生後的 budget、calibration、IRT 檔案。沒有原始完整 response，就無法獨立重建 Phase 3 Process Mining 結果。

### 處理內容

1. 確認原始檔實際所在位置、大小、是否包含敏感資訊。
2. 若可納入 repository，加入 `experiments/v3-budget-pilot/results/raw/`，並建立 checksum 與 schema。
3. 若檔案太大或不能公開，建立明確的受控資料取得說明、版本 ID 與最小可重現 sample。
4. 修改分析腳本，所有輸入路徑從命令列參數或專案根目錄解析，不依賴目前 shell 的 cwd。
5. 建立 `manifest.json`，記錄模型、題目版本、budget、replicate、prompt 版本、時間戳與程式版本。
6. 從 raw 重新產生 Phase 3 derived results，並比較現有檔案差異。

### 完成條件

- 新環境可由 raw 或明確的受控資料流程產生相同 derived 結果。
- `unzip`／JSON schema／筆數／欄位檢查均通過。
- Process Mining 報告中的每一個數字都能追溯到 raw record。

## 3. P0：統一環境與測試入口

### 問題

目前系統 Python 3.13 缺少 `numpy`、`pandas`、`scipy`、`pm4py`、`datasets`、`matplotlib`、`seaborn`、`python-pptx` 與 Graphviz；直接執行 `pytest` 會在 collection 階段失敗。

### 處理內容

1. 以 `pyproject.toml` 與 `uv.lock` 為唯一依賴來源。
2. 建立明確的 bootstrap 指令：建立 `.venv`、同步 dependencies、確認 Python 版本。
3. 修正測試從 repository root 執行時的 import path，不依賴隱含的 `PYTHONPATH`。
4. 將外部服務檢查（Ollama、Graphviz）與純單元測試分開。
5. `check_environment.py` 應區分：必要套件、可選套件、外部服務、環境變數。
6. 在 README 增加從全新環境開始的完整命令。

### 驗證方式

```bash
uv sync
uv run python scripts/check_environment.py
uv run pytest -q
```

### 完成條件

- 全新環境可安裝並執行測試。
- 測試 collection 不再因 import path 失敗。
- 外部 API 未設定時，測試仍能執行；只有需要 API 的實驗才明確 skip。

## 4. P1：修正 raw response 保存策略

### 問題

部分 V3 實驗只保存 `response[:500]`。這會限制完整推理重建、答案重解析與 Process Mining 重跑。

### 處理內容

1. 新實驗一律保存完整 response；若需隱私或容量控制，另產生 preview 欄位。
2. 將 request、response、parsed answer、usage、error、retry count 分開保存。
3. 為 raw schema 加上 `schema_version`。
4. 對既有資料標記 `truncated_response=true`，不可假設其可支援完整 PM 重分析。
5. 若原始完整回應不存在，文件要明確列為 reproducibility limitation。

### 完成條件

- 新 runner 不再以切片字串取代完整 response。
- 每筆資料可追溯到模型設定與 prompt 版本。
- PM 分析腳本能使用完整 trace 或明確跳過不完整資料。

## 5. P1：重新分析並建立統一結果表

parser 與 raw data 修正後，依序重新計算：

1. Hard Phase 3 accuracy、token、IRT、Brier、LCAE。
2. Hard IDS 的 QoQ／IDS 差異。
3. Soft Pilot 的 accuracy、actual tokens、budget compliance、confidence gap。
4. Soft + IDS 的相同指標。
5. 所有結果附 bootstrap 或 replicate-level uncertainty；不可只報平均值。

建議輸出：

- `results/analysis_v2/summary.csv`
- `results/analysis_v2/summary.json`
- `results/analysis_v2/figures/`
- `results/analysis_v2/README.md`

### 完成條件

- 一張表能同時看到條件、模型、budget、replicate、accuracy、actual tokens、compliance、Brier、LCAE。
- 圖表與研究文件使用同一份 derived summary。
- 若修正 parser 後主要排序改變，必須更新研究結論。

## 6. P1：建立公平的 Hard／Soft 比較方法

Soft Budget 目前是 prompt 建議，模型常超出要求，不能直接宣稱同 token 成本下更有效率。

後續分析必須同時報告：

- requested budget
- actual completion tokens
- within-budget compliance rate
- accuracy per actual token
- 超額 token 比例
- 相同 actual-token 區間的 accuracy

研究報告中應把 Soft 的解讀改為「具自主推理權的 instruction-mediated behavior」，除非後續設計能嚴格控制實際成本。

### 建議新實驗

比較以下三種機制：

1. Hard truncation。
2. Soft instruction。
3. Agency + stopping controller：允許模型決定是否繼續，但由外部 controller 控制總成本。

三者使用同一批題目、同一模型、同一 replicate 規格，並預先註冊主要指標。

## 7. P1：改進信心取得方式

目前 Soft 下的事後文字 confidence gap 接近 0，不能直接當作可靠的 allocation signal。

優先順序：

1. 先在既有 Soft 資料上重新計算 LCAE，確認免費可得的結果。
2. 測試 prospective confidence：先要求模型預測成功機率，再開始推理。
3. 測試多次短暫預測或 confidence decomposition。
4. 若模型或 API 支援，再加入 log-prob／token-level uncertainty。
5. 評估 CABStop 或 Think Just Enough 類型的停止方法。

每個方法都要回答三個問題：

- 信心是否能預測正確率？
- 信心是否能預測題目所需推理量？
- 使用信心後，實際 token 成本是否下降且 accuracy 不下降？

## 8. P2：完成 Process Mining 人工標記與機制分析

1. 依現有 activity taxonomy 抽樣 100 個步驟。
2. 兩位 reviewer 獨立標記。
3. 計算 Cohen’s kappa。
4. 針對歧異案例建立 adjudication 規則。
5. 重新訓練或調整規則式 labeler。
6. 比較 H256、H1024、Soft256、Soft512 的活動分佈與轉移。
7. 特別檢查 `verify`、`reconsider`、`answer` 出現位置，以及被 truncation 的狀態。

### 完成條件

- 有 annotation guide、原始雙人標記、kappa、最終標記資料。
- PM 圖表能回答「為什麼低 budget 失敗」，而不只呈現步驟數量。

## 9. P2：清理文件與路徑漂移

需要檢查並更新：

- `README.md`
- `docs/zh-TW/agent-handoff-2026-07-24.md`
- `docs/zh-TW/plan-2026-09-15.md`
- `experiments/v2-mmlu-arc/results/README.md`
- `experiments/v3-budget-pilot/results/analysis_phase3.md`

處理規則：

1. 以 `research-complete-2026-09-16.md` 作為目前結論的權威來源。
2. 舊文件保留歷史內容，但加上「歷史狀態」標示。
3. 所有不存在的檔名、尚未完成事項與已完成事項重新核對。
4. README 的專案樹必須與實際 `find` 結果一致。
5. 加入文件狀態欄位：`completed`、`in progress`、`blocked`、`historical`。

## 10. P2：安全性與公開前檢查

1. 確認目前程式只從環境變數讀取 API key。
2. 搜尋 Git 歷史中的憑證痕跡；若曾暴露，先撤銷／輪替憑證。
3. 檢查 public Pages allowlist，不得意外發布 raw response、秘密或本機路徑。
4. 建立公開前檢查指令，掃描 key pattern、`.env`、大型 raw 檔與個人資訊。
5. 不在文件、commit message 或 Agent 交接內容中放置 token。

## 11. 交付順序與停止點

### Sprint A：資料正確性

- P0 parser
- P0 raw data／schema
- P0 environment／tests

只有 Sprint A 全部完成後，才可以凍結新的研究數字。

### Sprint B：研究重分析

- 統一 summary
- Hard／Soft 公平比較
- 重新計算 IDS、LCAE、Brier 與 PM 結果

若主要結論因 parser 修正而改變，停止撰寫論文，先更新研究主軸。

### Sprint C：研究延伸

- prospective confidence
- stopping controller
- activity labeling
- 新的 agency 實驗

### Sprint D：文件與發表

- 更新 README 與 handoff
- 產生 reproducibility checklist
- 完成 Methods、Results、Limitations
- 做公開前安全檢查

## 12. Agent 每次交接必須回報

每個 Agent 完成工作後，請回報：

1. 修改或新增的檔案。
2. 執行過的命令與結果。
3. 新增的資料版本、筆數與 checksum（若適用）。
4. 是否改變既有研究數字。
5. 尚未處理的風險與下一個建議工作。
6. 明確標示「已完成」或「僅完成診斷，尚未修正」。

## 最終完成定義

本專案只有在以下條件全部成立時，才可宣稱研究管線完成：

- 乾淨環境可安裝並通過測試。
- 答案解析器對巢狀數學答案有測試保護。
- Phase 3 及後續結果可由版本化 raw／manifest 重建。
- Hard／Soft 的實際成本與遵從率分開報告。
- 研究文件、README、資料與程式狀態一致。
- 主要結論已在 parser 修正後重新確認。
- 公開內容不包含憑證、敏感 raw data 或不必要的本機資訊。
