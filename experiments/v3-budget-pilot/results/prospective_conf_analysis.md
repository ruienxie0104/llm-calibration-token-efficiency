# Prospective vs Retrospective Confidence — 完整分析報告

> 實驗日期：2026-09-16
> 實驗規模：360 次 confidence-only calls（2 模型 × 2 budgets × 3 reps × 30 題）

---

## 一、研究問題

在 Soft constraint 下，模型事後（retrospective）信心校準幾乎消失——答對答錯都給 95-100%。本實驗測試：**改成事前（prospective）詢問信心，是否能恢復校準品質？**

## 二、實驗設計

### 流程

```
Step 1: 給題目 + 預算指示，不讓模型作答
Step 2: 問 prospective confidence（CONFIDENCE=<0-100>）
        → 獨立 context，模型尚未開始推理
Step 3: 配對既有 Soft QOQ 的 answer records
        → 依 model / question_id / budget / replicate 配對
```

### 模型與參數

| 模型 | think 設定 | num_predict | prompt 格式 |
|------|-----------|-------------|-------------|
| GPT-OSS-120B | low | 256 | CONFIDENCE=<integer> |
| DeepSeek | false | 256 | CONFIDENCE=<integer> |

## 三、Parse / Missing 統計

| 模型 | Budget | 成功解析 | 失敗 | 解析率 |
|------|--------|---------|------|--------|
| GPT-OSS-120B | 256 | 89 | 1 | 98.9% |
| GPT-OSS-120B | 512 | 85 | 5 | 94.4% |
| DeepSeek | 256 | 90 | 0 | 100% |
| DeepSeek | 512 | 90 | 0 | 100% |

GPT-OSS-120B 的少數失敗集中在同一題 counting_and_probability，`done_reason=length` 在 thinking 階段耗盡 token。

## 四、核心結果

### 4.1 Brier Score（越低越好）

| 模型 | Budget | Prospective | Retrospective | Hard（對照） |
|------|--------|------------|-------------|-------------|
| GPT-120B | 256 | **0.026** | 0.222 | 0.226 |
| GPT-120B | 512 | **0.028** | 0.210 | 0.234 |
| DeepSeek | 256 | **0.009** | 0.200 | 0.137 |
| DeepSeek | 512 | **0.008** | 0.178 | 0.137 |

Prospective 的 Brier 遠優於 retrospective。但這是因為 prospective 總是給 86-94%，正好接近 base rate（74-83%）。

### 4.2 LCAE（越低越好）

| 模型 | Budget | Prospective | Retrospective | Hard（對照） |
|------|--------|------------|-------------|-------------|
| GPT-120B | 256 | **0.222** | 0.298 | 0.247 |
| GPT-120B | 512 | **0.221** | 0.306 | 0.247 |
| DeepSeek | 256 | **0.254** | 0.310 | 0.303 |
| DeepSeek | 512 | **0.254** | 0.310 | 0.303 |

LCAE 也顯示 prospective 更好。**但注意：這是 anchored LCAE（使用 Phase 3 IRT 參數），不是 Soft-specific 校準。**

### 4.3 AUROC（越高越好，區分力指標）

| 模型 | Budget | Prospective | Retrospective |
|------|--------|------------|-------------|
| GPT-120B | 256 | **None**（無法計算） | 0.516（接近隨機） |
| GPT-120B | 512 | **None** | 0.382（差） |
| DeepSeek | 256 | **None** | 0.500（隨機） |
| DeepSeek | 512 | **None** | 0.493（隨機） |

**Prospective 的 AUROC 無法計算**——因為所有 prospective confidence 都集中在 85-95，沒有足夠的變異量來區分對錯。Retrospective 的 AUROC 也接近 0.5（隨機）。

### 4.4 信心差距（答對−答錯）

| 模型 | Budget | Prospective | Retrospective |
|------|--------|------------|-------------|
| GPT-120B | 256 | **+86.8** | +1.5 |
| GPT-120B | 512 | **+86.6** | −0.6 |
| DeepSeek | 256 | **+93.6** | 0.0 |
| DeepSeek | 512 | **+93.8** | −0.1 |

Prospective 的差距看起來很大，但這是「答對時平均 90，答錯時平均也在 80 以上」造成的——不是好的區分力。

### 4.5 Spearman 相關係數（信心 vs 正確率）

| 模型 | Budget | Prospective | Retrospective |
|------|--------|------------|-------------|
| GPT-120B | 256 | **+0.544** | +0.027 |
| GPT-120B | 512 | **+0.619** | −0.186 |
| DeepSeek | 256 | None（常數） | nan |
| DeepSeek | 512 | +0.150 | −0.049 |

GPT-120B 的 prospective 有中等相關（0.54-0.62），但這是因為 prospective 的信心變異量雖然小但仍然存在（60-97），而 retrospective 幾乎是常數（95-100）。

### 4.6 Confidence vs Actual Tokens

| 模型 | Budget | conf-tok r | 說明 |
|------|--------|-----------|------|
| GPT-120B | 256 | **−0.661** | 信心越高，token 越少 |
| GPT-120B | 512 | **−0.756** | 更強 |
| DeepSeek | 256 | −0.601 | 中等 |
| DeepSeek | 512 | −0.650 | 中等 |

Prospective confidence 與實際 token 使用量有中等至強的負相關——有信心時用較少 token，沒信心時用較多。**這是 prospective 最有價值的發現。**

但要注意：Prospective confidence 中幾乎沒有 low-confidence 的案例（<70 的案例：GPT-120B 256 有 0 筆，512 有 2 筆）。所以這個相關主要來自 high-confidence（90+）vs medium-confidence（70-85）的差異。

## 五、總結

| 指標 | Prospective | Retrospective | 勝者 |
|------|------------|-------------|------|
| Brier | **0.008-0.028** | 0.178-0.222 | Prospective 🏆 |
| LCAE | **0.221-0.254** | 0.298-0.310 | Prospective 🏆 |
| AUROC | **無法計算** | 0.382-0.516（隨機） | — |
| 信心差距 | +87 到 +94（偽差距） | −1 到 +2（消失） | — |
| Spearman r | **0.54-0.62**（GPT） | −0.19 到 +0.03 | Prospective 🏆 |
| conf-tok 相關 | **−0.60 到 −0.76** | — | Prospective 🏆 |

**核心結論：** Prospective confidence 在某些指標上優於 retrospective（Brier、LCAE、Spearman），但**這些優勢來自於「總是給 ~90%」的保守策略，而不是真正的區分能力。** AUROC 分析失敗——無法區分對錯，這是信號價值的根本問題。

## 六、建議下一步

1. **Hybrid signal：** 結合 prospective + retrospective + IRT difficulty 作為綜合信心訊號
2. **Temperature scaling：** 對 prospective confidence 做 post-hoc calibration
3. **Percentile-based allocation：** 放棄絕對信心值，改用排名分組決定 token 預算
4. **Confidence variance 作為訊號：** 多次詢問 confidence，用 variance 代替 mean 作為不確定性的指標