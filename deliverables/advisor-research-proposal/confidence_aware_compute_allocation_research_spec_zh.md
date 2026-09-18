# 以流程狀態與反事實信心進行成本感知的測試時計算分配

## 研究說明書、假設與後續驗證計畫

> 文件用途：作為研究 Proposal、後續實驗設計、Agent 實作與論文撰寫的共同依據。
>
> 文件狀態：研究方向規格書；不是最終論文，也不是過去實驗流水帳。
>
> 更新日期：2026-09-18。
>
> 核心原則：清楚區分「信心能否控制後續運算」、「信心本身需要多少成本」與「整體系統是否真正改善」三個層次。

---

## 0. 摘要

大型語言模型在解題時通常能藉由更多 test-time compute 改善表現，但額外推理並非對每一題都有幫助。部分題目在低預算下已經完成，部分題目能藉由 continuation 被救回，另一些題目即使增加 token 仍然不會改善，甚至可能從正確變成錯誤。當系統只有固定總預算時，真正的問題因此不是「是否給所有題目更多 token」，而是：

> 在模型已經完成一段低成本推理後，哪些題目值得繼續投入運算？

本研究提出一個兩層式、適用於黑箱 API 的資源配置框架：

1. **Visible-progress controller**：先根據模型輸出的可觀察流程狀態，排除明顯不需要或不適合 continuation 的案例。
2. **Process-conditioned counterfactual confidence**：只對需要進一步判斷的案例，估計「若停止」與「若繼續」的結果，以及額外運算帶來改善或傷害的機率。

本研究不再把 confidence 只定義為「目前答案正確的機率」，而是將它轉化成與決策直接對齊的反事實問題：

> 如果現在停止，答案正確的機率是多少？如果再投入一段運算，正確率會提高、維持或下降的機率是多少？

研究的最終目標，是在事前固定的全域 token ledger 下，使用流程狀態、反事實信心與實際成本，選擇最值得 continuation 的題目，使系統：

- 在相同總 token 成本下得到更高正確率；或
- 在維持相同正確率的情況下使用更少 token。

---

## 1. 一句話研究定位

> 本研究利用模型低預算推理後的可觀察進度，以及針對額外運算價值所設計的反事實信心，在固定總 token 預算下動態決定哪些題目應停止、哪些題目應繼續。

更口語的說法是：

> 每題先做一小段；先看模型現在做到哪裡，再只對模糊案例詢問「繼續算真的有幫助嗎」，最後把有限 token 留給最可能被救回的題目。

---

## 2. 研究背景與動機

### 2.1 更多推理不等於每題都更好

推理型大型語言模型可以使用更長的 reasoning、continuation、self-consistency、search 或 verifier 來改善答案。但增加 test-time compute 會同時增加：

- 生成 token；
- API 成本；
- 回應延遲；
- 系統吞吐量壓力；
- 在大規模服務中的能源與運算需求。

更重要的是，額外運算的收益具有高度異質性：

| 低預算狀態 | 增加運算後 | 配置含義 |
|---|---|---|
| 已經正確完成 | 維持正確 | 額外運算通常浪費 |
| 尚未完成但已有有效進展 | 從錯誤／未完成變正確 | 最值得追加 |
| 沒有可用進展 | 仍然無法完成 | 追加可能無效 |
| 已正確但被後續推理改壞 | 從正確變錯誤 | 追加可能有害 |

因此，平均而言「更多 token 是否有效」並不是最關鍵的問題。真正需要解決的是每題的**額外運算邊際價值**。

### 2.2 題目難度不等於 continuation value

困難題不一定值得投入更多運算：有些困難題即使增加大量 token 仍無法被解決。相反地，一些中等難度題可能只差最後一個推導步驟，少量 continuation 就能完成。

所以研究目標不應只是預測：

$$
P(\text{question is difficult})
$$

而應該預測：

$$
P(\text{additional compute improves the outcome})
$$

前者描述題目的靜態屬性；後者描述採取一個額外運算 action 的預期收益。

### 2.3 一般 correctness confidence 也不一定適合配置資源

傳統信心通常詢問：

$$
C_{\text{correct}}=P(\text{current answer is correct})
$$

但資源配置真正需要知道的是：

$$
C_{\text{gain}}=P(\text{continuation improves the result})
$$

兩者並不相同。

例如，一個模型可能對目前答案沒有信心，但即使繼續推理也無法改善；此時低信心不代表值得追加資源。反過來，一個模型可能對目前答案很有信心，但 continuation 仍有機會發現錯誤並修正。

因此，若直接用一般自評信心控制 token，訊號目標可能從一開始就與 allocation decision 不對齊。

### 2.4 信心是有成本的訊號

如果系統需要額外呼叫模型才能取得 confidence，該次呼叫本身也會使用 prompt token、completion token、時間與金錢。這造成一個重要但容易被忽略的問題：

> 信心可能成功降低後續推理量，但取得信心的成本可能大於它省下的 token。

因此，研究必須同時回答：

1. 信心是否讓後段推理變少或配置得更好？
2. 取得信心所付出的成本是多少？
3. 扣除信心成本後，整體系統是否仍然改善？

這三個問題不能混成同一個數字。

### 2.5 研究缺口與本研究定位

Adaptive test-time compute、difficulty routing、confidence-based stopping、hidden-state probe 與 learned router 都已有相關研究。因此，本研究不把「動態配置 token」本身宣稱為全新的問題。

本研究聚焦的是一個更具體的組合：

1. **Black-box compatible**：不要求 logits、hidden state 或模型權重。
2. **Post-prefix decision**：模型先執行一段推理，再根據當下狀態決策。
3. **Continuation-value target**：預測額外運算的邊際價值，而非只有難度或目前正確性。
4. **Selective confidence acquisition**：只在資訊可能改變決策時支付信心成本。
5. **Full cost accounting**：將 confidence acquisition 與 continuation token 全部納入。
6. **Global-ledger evaluation**：在事前固定總資源下比較政策，而非只比較分類指標。

因此，預期創新不是「第一次使用信心」或「第一次分配 test-time compute」，而是：

> 將免費的可觀察流程狀態與有成本的 action-conditional confidence 結合，直接預測 continuation value，並檢驗這份額外資訊在完整成本核算下是否值得取得。

### 2.6 目前可支持這個方向的初步基礎

既有實驗已提供兩項方法設計所需的基礎證據：

1. Observable progress state 能辨識具有不同 continuation outcome 的案例，說明 post-prefix allocation 具有可行性。
2. 在 held-out、cost-matched 評估中，visible-progress policy 已呈現正向 accuracy improvement，說明 process signal 可以被轉化成政策，而不只是描述性相關。

這些結果支持將 visible progress 保留為主 controller。新的 confidence 研究不是推翻它，而是回答下一個問題：

> 在 process-only 仍無法區分的案例中，一個對準 continuation value、成本受控的 confidence 是否能進一步改善分配？

Confidence 因此扮演「增量決策訊號」，而不是取代整個流程狀態方法。

---

## 3. 研究問題的精確定義

### 3.1 系統設定

給定一批問題 $q_1,\ldots,q_N$，系統對每一題先執行相同的低預算 prefix。完成 prefix 後，controller 只能使用當下可取得的資訊：

- 原始問題；
- visible prefix content；
- 是否已經出現可解析答案；
- observable process state；
- 已使用 token 與 API metadata；
- 在被選擇查詢時，額外取得的反事實信心。

Controller 不可以看到：

- ground-truth answer；
- continuation 之後的真實結果；
- oracle gain；
- 未公開 hidden representation；
- 其他只存在於離線 action bank 的未來資訊。

### 3.2 最終決策

對每一題，controller 必須選擇：

- **Stop**：保留 prefix 階段的答案；或
- **Continue**：支付額外 continuation 成本，讓模型繼續完成或修正。

若總 continuation 預算有限，controller 還必須在所有候選題目之間排序，直到全域 token ledger 用完。

### 3.3 最佳化目標

本研究的主要目標是：

$$
\max_{\pi}\; \mathbb{E}[\text{Accuracy}(\pi)]
\quad
\text{s.t.}
\quad
\mathbb{E}[T_{\text{total}}(\pi)]\le B,
$$

其中：

- $\pi$ 是 allocation policy；
- $B$ 是事前固定的總 token 預算；
- $T_{\text{total}}$ 必須包含 prefix、confidence 與 continuation 的實際成本。

等價地，也可以在要求正確率至少達到 $A^*$ 的條件下，最小化總 token：

$$
\min_{\pi}\; \mathbb{E}[T_{\text{total}}(\pi)]
\quad
\text{s.t.}
\quad
\mathbb{E}[\text{Accuracy}(\pi)]\ge A^*.
$$

---

## 4. 核心概念與符號

### 4.1 Low action、High action 與 continuation gain

對第 $i$ 題：

- $y_i^L\in\{0,1\}$：在 prefix 後停止的正確性；
- $y_i^H\in\{0,1\}$：執行 continuation 後的正確性；
- $g_i=y_i^H-y_i^L$：continuation 的真實邊際收益。

因此：

| $g_i$ | 名稱 | 意義 |
|---:|---|---|
| +1 | benefit | 原本未正確，continuation 後正確 |
| 0 | unchanged / unresolved | continuation 沒有改變正確性 |
| -1 | harm | 原本正確，continuation 後變錯 |

在部署時，$g_i$ 不可觀察；它只能在離線 action bank 中作為訓練或評估標籤。

### 4.2 Observable process state

根據 prefix 的 visible content，定義三種粗粒度狀態：

| 狀態 | 可觀察定義 | 直觀含義 |
|---|---|---|
| `complete` | visible content 中已有可解析最終答案 | 通常可以停止 |
| `visible_unfinished` | 沒有可解析答案，但已有非空白可見推理 | 有進展、可能值得繼續 |
| `empty_unfinished` | 沒有可解析答案，visible content 亦為空 | 可見進展不足，追加價值不確定 |

這些狀態是 allocation signal，不是真實能力、難度或正確率的完整描述。

### 4.3 反事實信心

本研究將 confidence 拆成四個 action-conditional 預測：

$$
C_i^{\text{stop}}=P(y_i^L=1\mid q_i,x_i,s_i),
$$

$$
C_i^{\text{continue}}=P(y_i^H=1\mid q_i,x_i,s_i,B_i),
$$

$$
C_i^{\text{benefit}}=P(g_i=+1\mid q_i,x_i,s_i,B_i),
$$

$$
C_i^{\text{harm}}=P(g_i=-1\mid q_i,x_i,s_i,B_i),
$$

其中：

- $x_i$ 是 visible prefix；
- $s_i$ 是 process state；
- $B_i$ 是可追加的 continuation budget。

最簡單的預期正確率改善量為：

$$
\Delta C_i=C_i^{\text{continue}}-C_i^{\text{stop}}.
$$

若直接預測 benefit 與 harm，則成本感知分數可以寫成：

$$
U_i=C_i^{\text{benefit}}
-\alpha C_i^{\text{harm}}
-\lambda \widehat{c_i^H},
$$

其中：

- $\alpha$ 表示錯誤 continuation 所造成傷害的權重；
- $\lambda$ 將 token 成本轉換成效用懲罰；
- $\widehat{c_i^H}$ 是 continuation 成本的事前估計。

### 4.4 信心成本、後段成本與總成本

定義：

- $T_i^P$：prefix 成本；
- $T_i^C$：confidence query 成本；
- $T_i^H$：continuation 成本；
- $Q_i\in\{0,1\}$：是否查詢 confidence；
- $Z_i\in\{0,1\}$：是否執行 continuation。

則每題總成本為：

$$
T_i^{\text{total}}=T_i^P+Q_iT_i^C+Z_iT_i^H.
$$

沒有 confidence controller 的 baseline 後段成本記為 $T_0$，使用 confidence controller 後的 continuation 成本記為 $T_1$，confidence 成本記為 $T_C$。

後段毛節省：

$$
G=T_0-T_1.
$$

端到端淨節省：

$$
N=T_0-(T_C+T_1)=G-T_C.
$$

Break-even confidence cost 為：

$$
T_C^{\text{break-even}}=G.
$$

只有當 $G>T_C$ 時，confidence 在 token 數量上才具有正的端到端淨節省。

---

## 5. 提出的方法：兩層式資源配置框架

### 5.1 整體流程

```text
問題 q
  │
  ▼
固定低預算 prefix
  │
  ▼
解析 visible content 與 process state
  │
  ├─ 明確可停止 ──────────────────────► Stop
  │
  ├─ 明確值得繼續 ────────────────────► Continue
  │
  └─ 決策模糊
          │
          ▼
  短格式 counterfactual-confidence query
          │
          ▼
  校準後的 benefit / harm / cost score
          │
          ▼
  全域 token ledger 下排序與選擇
          │
          ├─ 預期淨效用 > threshold ─► Continue
          └─ 其他 ────────────────────► Stop
```

### 5.2 第一層：免費或近乎免費的流程狀態

第一層使用 prefix 原本就會產生的 visible output，因此不需要額外模型呼叫。它的目的不是做完所有決策，而是：

- 排除已經明確完成的案例；
- 找出具有可見進展的 continuation 候選；
- 縮小需要昂貴 confidence query 的集合。

### 5.3 第二層：只在模糊案例查詢信心

第二層不是 query-all。它只對第一層無法可靠決策的案例取得反事實信心。這種 selective elicitation 有三個理由：

1. 減少 confidence overhead；
2. 避免對明顯案例重複取得沒有價值的資訊；
3. 讓 confidence 專注在 process-only policy 的決策邊界。

### 5.4 第三層：在全域預算下分配

若同時存在多個候選案例，系統不應逐題使用固定 threshold 而忽略總成本。Controller 應依預期效用排序，在 ledger 尚有足夠預算時執行 continuation。

這使研究從單純的 stopping rule，發展成真正的 resource allocation method。

---

## 6. 研究目標

### 主要目標

建立一個黑箱 API 可部署、成本可核算、以 continuation value 為目標的動態 test-time compute allocation 方法。

### 次要目標

1. 分辨 confidence 的**預測價值**、**控制價值**與**端到端經濟價值**。
2. 找出 confidence 最適合介入的 process state 與適用邊界。
3. 量化 confidence acquisition cost 的 break-even 門檻。
4. 比較 correctness confidence 與 counterfactual gain confidence，確認預測目標是否需要與 action 對齊。
5. 在模型、題目與狀態分布改變時，評估方法是否仍能泛化。

---

## 7. 研究問題

### RQ1：流程狀態是否能辨識 continuation value 的異質性？

不同 observable process state 的 benefit、harm 與 unchanged 比例是否不同？

### RQ2：傳統 correctness confidence 與 counterfactual confidence 分別預測什麼？

一般「我答對的機率」是否主要反映當前正確性、題目難度或預期推理成本？針對 continuation 設計的 confidence 是否更能預測 $g_i$？

### RQ3：confidence 是否能降低後續推理成本？

在暫時不計 confidence query 成本時，confidence-guided policy 是否能用更少 continuation token 維持相同正確率，或在相同 continuation token 下提高正確率？

### RQ4：計入 confidence 成本後，整體系統是否仍然有效？

信心帶來的後段毛節省是否大於信心取得成本？

### RQ5：process-conditioned confidence 是否優於 process-only？

在已知 process state 後，confidence 是否仍提供增量資訊與政策收益？

### RQ6：selective confidence 是否優於 query-all confidence？

只在模糊狀態查詢 confidence，是否比每題都查詢具有更好的 accuracy–cost trade-off？

### RQ7：方法在哪些模型與狀態分布下有效？

當模型在 prefix 階段幾乎全部完成，或幾乎沒有可救回案例時，配置方法的改善空間是否自然縮小？

---

## 8. 可驗證研究假設

## H1：流程狀態異質性假設

### 假設內容

`visible_unfinished`、`complete` 與 `empty_unfinished` 具有不同的 continuation-value 分布；其中 `visible_unfinished` 的 benefit rate 預期較高。

### 對立假設

不同流程狀態的 continuation gain 沒有實質差異，visible state 無法支援資源配置。

### 驗證方式

- 比較各 state 的 benefit、harm、unchanged、unresolved 比率；
- 使用 question-clustered bootstrap 估計差異 CI；
- 模型分開報告，避免被單一模型的狀態分布驅動。

### 支持條件

至少一個可部署 state 在 held-out data 上具有穩定、方向一致的正 continuation gain，且有足夠案例支持。

---

## H2：目標對齊假設

### 假設內容

Action-conditional counterfactual confidence 比一般 correctness confidence 更能預測 continuation benefit 與 harm。

### 直觀原因

Correctness confidence 回答的是「現在是否正確」；allocation 需要回答的是「採取 continuation 是否改善」。當預測目標與 action 不一致時，即使 confidence 校準良好，也未必能提供配置價值。

### 驗證方式

比較下列訊號對 $g_i$ 或 benefit label 的 held-out 表現：

1. correctness confidence；
2. $C^{\text{continue}}-C^{\text{stop}}$；
3. 直接詢問的 $C^{\text{benefit}}$；
4. process-only baseline；
5. process + counterfactual confidence。

主要指標：

- PR-AUC：處理 benefit 少數類別；
- AUROC：作為次要判別指標；
- Brier score／log loss：評估機率品質；
- reliability curve：檢查機率是否可被政策使用。

### 支持條件

Counterfactual confidence 對 continuation benefit 的 held-out discrimination 或 probabilistic loss 優於 correctness confidence，且 paired CI 支持正向差異。

---

## H3：後段毛節省假設

### 假設內容

暫時不計 confidence query 成本時，confidence-guided allocation 能降低後續 continuation token，且不降低正確率；或在相同 continuation token 下提高正確率。

### 驗證方式

比較：

- process-only downstream cost；
- process + confidence downstream cost；
- random matched downstream cost。

此階段故意將 $T_C$ 分開，不是為了隱藏成本，而是確認 confidence 是否真的具有**控制價值**。

### 支持條件

至少滿足其中一項：

- $G=T_0-T_1>0$，且 accuracy 不下降；
- 在相同 downstream continuation ledger 下，confidence policy accuracy 較高；
- 在相同 accuracy target 下，confidence policy downstream token 較少。

---

## H4：流程條件化增量價值假設

### 假設內容

在控制 observable process state 後，counterfactual confidence 仍能辨識同一 state 內哪些題目值得 continuation。

### 驗證方式

比較：

- P0：process-only；
- P1：confidence-only；
- P2：question features + process；
- P3：question features + process + counterfactual confidence；
- P4：process × counterfactual-confidence interaction。

所有模型選擇、校準與 threshold 必須在 training/calibration split 完成，再於 held-out test split 評估。

### 支持條件

P3 或 P4 相對 P0/P2 的 paired held-out 增量為正，且不是只由一個模型或極少數案例造成。

---

## H5：端到端淨效益假設

### 假設內容

confidence 所節省的後段 token 大於取得 confidence 所花的 token，或其正確率提升足以形成更好的 accuracy–cost Pareto point。

### 驗證方式

完整計入：

$$
T^{\text{total}}=T^P+QT^C+ZT^H.
$$

比較 process-only 與 confidence-augmented policy 的：

- mean actual total tokens；
- aggregate total tokens；
- accuracy；
- accuracy per 1K tokens；
- matched-total-token accuracy；
- matched-accuracy token use；
- latency 與 API calls，若資料可取得。

### 支持條件

最強支持為：

$$
N=G-T_C>0
$$

且 accuracy 不下降。

若 $N\le0$ 但 accuracy 顯著提高，則需證明該點仍位於更佳的 Pareto frontier，不能宣稱為純 token saving。

---

## H6：選擇性查詢假設

### 假設內容

只在 process-only controller 的模糊案例查詢 confidence，會優於每題 query confidence。

### 驗證方式

比較：

- no confidence；
- query-all confidence；
- state-gated confidence；
- uncertainty-gated confidence；
- oracle query placement，僅作上界。

### 支持條件

Selective policy 在較低 query rate 下，取得不低於 query-all 的 accuracy，並具有較佳淨 token 或成本效用。

---

## H7：適用邊界假設

### 假設內容

方法的收益取決於 prefix 後是否存在足夠的「可分配案例」與 continuation headroom，而不是對所有模型固定成立。

### 驗證方式

對每個模型報告：

- process-state prevalence；
- benefit/harm prevalence；
- oracle headroom；
- confidence query eligibility rate；
- policy improvement；
- 每個 state 的有效樣本數。

### 支持條件

當 allocatable cases 足夠時，方法呈現正向改善；當大多數題目在 prefix 已完成時，改善空間縮小。後者應被解釋為 deployment boundary，而不是自動視為演算法失敗。

---

## 9. 假設之間的邏輯關係

這些假設不是七個互不相關的實驗，而是一條有順序的證據鏈：

```text
H1：不同流程狀態是否真的有不同 continuation value？
  │
  ▼
H2：重新設計的 confidence 是否對準 continuation gain？
  │
  ▼
H4：它是否在 process-only 之外提供增量資訊？
  │
  ▼
H3：它是否真的減少後段 continuation 或提高配置品質？
  │
  ▼
H6：只在需要時查詢，是否降低 confidence overhead？
  │
  ▼
H5：把所有成本算回來後，整體系統是否更好？
  │
  ▼
H7：方法在哪些模型、資料與 state distribution 下成立？
```

如果 H2 不成立，就不應急著做昂貴的正式 policy experiment。如果 H3 成立但 H5 不成立，代表訊號具有控制價值，但取得方式太昂貴；此時下一步應優化 confidence acquisition，而不是否定整個概念。

---

## 10. 建議實驗流程

## Stage A：既有資料的成本分解分析

### 目的

先使用現有 action bank 與 confidence 資料，將先前的 end-to-end 結果拆成：

1. downstream gross saving；
2. confidence acquisition cost；
3. end-to-end net saving；
4. accuracy change；
5. break-even confidence cost。

### 不需要新 API calls

這一階段主要建立統一分析框架，避免直接把「淨效益為負」誤寫成「confidence 完全沒有控制資訊」。

### 主要輸出

- `confidence_cost_decomposition.json`
- `confidence_cost_decomposition.md`
- accuracy–downstream-token 圖；
- accuracy–total-token 圖；
- 每個 state 的 gross/net saving 表；
- break-even confidence-cost curve。

### 決策

- 若 gross value 也不存在：重新設計 confidence target，不進正式實驗。
- 若 gross value 存在但 net value 不存在：進入低成本 elicitation 設計。
- 若 gross 與 net value 都存在：直接做 held-out confirmation。

---

## Stage B：Counterfactual-confidence elicitation gate

### 目的

確認新的 confidence prompt 是否具備最基本的資料品質與目標對齊能力。

### 查詢時點

此處的「事先信心」是指**在 continuation action 之前**取得，而不是一定要在任何推理之前取得。模型可以看到：

- 原始題目；
- 已產生的 visible prefix；
- 可追加的 budget；
- 但不能看到 continuation outcome 或正確答案。

### 建議輸出協議

```json
{
  "p_stop_correct": 0,
  "p_continue_correct": 0,
  "p_continue_improves": 0,
  "p_continue_harms": 0
}
```

數值範圍可使用 0–100 的整數。Prompt 必須要求：

- 只輸出單行 JSON；
- 不提供解釋；
- 不重新解題；
- 不輸出答案；
- 使用非常短的 output cap，例如 24–40 tokens；
- 保存 raw content、thinking、done reason 與 token accounting 以供 audit。

### Smoke gate

至少檢查：

- parse rate ≥ 95%；
- 欄位完整率 ≥ 95%；
- 不同案例間具有足夠變異；
- 沒有大規模固定輸出 90/95/100；
- confidence completion cost 足夠低；
- 沒有洩漏 continuation 結果；
- 兩次重複查詢的一致性可接受。

Smoke 只驗證 protocol，不用來估計正式效果。

---

## Stage C：離線訊號與政策可行性實驗

### 目的

利用已保存的 prefix 與 action-bank outcome，測試 H2、H3、H4 與 H6。

### 資料切分

必須依 `question_id` 分割：

- training split：學習簡單 mapping 或 ranking model；
- calibration split：校準 confidence、選 threshold 與 query rule；
- test split：只做一次主要評估。

同一題的不同模型、budget、action 或重複樣本不得跨 split，以避免 leakage。

### Policy variants

| Policy | 使用訊號 | 是否付 confidence 成本 | 用途 |
|---|---|---:|---|
| Fixed Low | 無 | 否 | 低成本基準 |
| Fixed Continue | 無 | 否 | 高計算基準 |
| Random matched | 無 | 否 | 無訊號公平基準 |
| Process-only | process state | 否 | 現有主方法 |
| Confidence-only | counterfactual confidence | 是 | 檢驗單獨價值 |
| Process + query-all | state + confidence | 是 | 信心完整介入基準 |
| Process + selective confidence | state + gated confidence | 是 | 主要候選方法 |
| Oracle | future gain | 否 | 不可部署的上界 |

### 兩套成本視圖必須同時報告

#### View 1：Controller value

暫時分開列出 confidence cost，只比較 downstream continuation allocation。用來回答 confidence 是否真的改變了後續運算。

#### View 2：Deployable system value

將 confidence prompt/completion token 與 continuation token 全部計入。用來回答整體方法是否值得部署。

兩套視圖不得互相替代。

---

## Stage D：Held-out matched-ledger confirmatory experiment

### 目的

在新題目上，確認 frozen selective-confidence policy 是否能在相同實際總 token 預算下超越 process-only 與 random allocation。

### 實驗前必須凍結

- dataset 與排除清單；
- process-state parser；
- confidence prompt；
- confidence output cap；
- calibration mapping；
- query eligibility rule；
- continue ranking score；
- token ledger；
- fallback rule；
- success criteria；
- bootstrap procedure。

### 執行成本公式

對每個 policy：

$$
T_{\pi}=\sum_i T_i^P+
\sum_i Q_iT_i^C+
\sum_i Z_iT_i^H.
$$

主要比較必須在相同 $T_{\pi}$ 或同一 pre-specified ledger 下進行。

### Primary contrast

$$
\Delta A=
A_{\text{process + selective confidence}}
-A_{\text{process-only matched total cost}}.
$$

若 process-only 無法剛好使用相同成本，可使用事前定義的 cost-calibrated randomization 或 ledger replay，但必須清楚標明它是評估 benchmark 還是可線上部署的政策。

### 推論方式

- 以 `question_id` 為 cluster；
- paired bootstrap，建議至少 10,000 replicates；
- pooled 結果與模型別結果同時報告；
- paired difference CI，而不是比較兩個互相重疊的個別 CI；
- 報告 state support，避免極少案例造成不穩定結論。

---

## 11. 評估指標

### 11.1 訊號層

- parse rate；
- missing rate；
- confidence distribution；
- PR-AUC；
- AUROC；
- Brier score；
- log loss；
- ECE 與 reliability curve；
- benefit/harm ranking quality；
- 與 actual continuation cost 的相關性。

### 11.2 決策層

- continuation precision：被選中的題目中有多少真正 benefit；
- continuation recall：所有可救回題目中選到多少；
- harm rate；
- query rate；
- continuation rate；
- 每個 process state 的 selection rate。

### 11.3 系統層

- final accuracy；
- prefix tokens；
- confidence prompt tokens；
- confidence completion tokens；
- continuation tokens；
- mean／median／aggregate total tokens；
- downstream gross saving $G$；
- end-to-end net saving $N$；
- break-even confidence cost；
- accuracy–cost Pareto frontier；
- latency 與 call count，若可取得。

### 11.4 不應單獨作為成功證據的指標

- 只有 confidence 與 token 的相關係數；
- 只有 confidence calibration；
- 只有分類 AUROC；
- 只有平均 token 下降而沒有 accuracy；
- 只有 accuracy 上升而沒有計入 confidence cost；
- 只有 oracle 表現。

---

## 12. 成功、部分成功與失敗應如何解讀

| 實驗結果 | 正確解釋 | 下一步 |
|---|---|---|
| Counterfactual confidence 無法預測 benefit | 預測目標或 elicitation 仍無效 | 不做正式 policy；重新設計訊號 |
| 能預測 benefit，但不優於 process-only | confidence 沒有增量資訊 | 維持 visible-progress 主方法 |
| 優於 process-only，且後段 token 減少 | confidence 具有控制價值 | 檢查取得成本 |
| 後段 token 減少，但淨 token 增加 | 訊號有效但 elicitation 太昂貴 | 壓縮輸出、selective query、surrogate |
| 淨 token 減少，accuracy 不下降 | 強端到端成功 | 進 held-out confirmation |
| token 相同，accuracy 提高 | 有效的固定預算配置方法 | 進 held-out confirmation |
| token 增加、accuracy 也提高 | 可能是 Pareto 改善，不是省 token | 報告 cost–quality trade-off |
| 某模型無改善且幾乎全在 prefix 完成 | 缺少 allocation headroom | 視為適用邊界，不直接否定方法 |

---

## 13. 預期學術貢獻

若主要假設獲得支持，本研究可形成下列貢獻：

### 貢獻一：重新定義適合資源配置的 confidence target

將 confidence 從靜態 correctness self-assessment，轉換為 action-conditional continuation value：停止會如何、繼續會如何，以及追加運算改善或傷害的機率。

### 貢獻二：兩層式低成本 controller

先以免費的 observable progress state 篩選，再只對模糊案例支付 confidence 成本，避免 query-all 的固定 overhead。

### 貢獻三：完整的 confidence cost decomposition

明確區分：

- predictive value；
- downstream control value；
- gross token saving；
- confidence acquisition cost；
- end-to-end net value。

這能避免將「訊號沒有用」與「訊號取得太昂貴」混為一談。

### 貢獻四：黑箱、post-prefix、matched-cost 的政策驗證

方法只依賴一般 API 可見輸出，不要求 hidden state，且在事前 token ledger 與實際總成本下評估，而不是只報告分類指標。

### 貢獻五：方法的適用邊界

研究不只回答方法何時有效，也說明當 prefix 已幾乎解決所有題目、benefit prevalence 太低或 confidence overhead 太高時，方法為何失去優勢。

---

## 14. 研究限制與風險

### 14.1 Confidence 仍是模型自我報告

模型可能輸出社會期許式、離散化或過度集中的數字。JSON 可改善解析率，但不保證語義有效。

### 14.2 Confidence query 可能改變後續行為

若同一 conversation 中先詢問信心，再要求 continuation，confidence prompt 可能影響後續推理。正式設計需要區分：

- confidence 僅供外部 controller 使用；
- confidence message 是否被 continuation model 看見。

原則上，為避免干擾，continuation 不應看到 confidence response，除非研究明確要測 confidence-conditioned reasoning。

### 14.3 Action bank 與線上部署不同

離線 action bank 能同時看到 stop 與 continue outcome，方便公平比較，但線上系統只會執行被選中的 action。Oracle 與使用未來 realized cost 的 comparator 只能作為評估工具。

### 14.4 類別不平衡

真正 benefit 的案例可能很少。單看 AUROC 可能過度樂觀，必須同時報告 PR-AUC、base rate 與 state support。

### 14.5 模型與 API 行為差異

不同模型對 `think`、output cap、hidden reasoning 與 visible content 的處理不同。Protocol feasibility 必須逐模型確認。

### 14.6 目前主要任務類型有限

若資料以數學題為主，不能直接宣稱對 coding、planning、QA 或 agent workflow 普遍成立。跨任務泛化應是後續研究，而不是先驗假設。

---

## 15. 論文主張邊界

### 如果只有 H1 成立

可以說 observable progress 與 continuation value 有關；不能說已有新 allocation algorithm。

### 如果 H2、H3 成立但 H5 不成立

可以說 counterfactual confidence 具有控制資訊，但目前取得成本抵消其收益；不能說它提高端到端 token efficiency。

### 如果 H4、H5、H6 成立

可以主張 process-conditioned selective confidence 在完整成本核算下改善固定預算資源配置。

### 不應做的過度主張

- 不能宣稱 confidence-based allocation 沒有人研究；
- 不能宣稱所有 confidence 方法都失效或都有效；
- 不能把 soft prompt budget 當成實際 API token cap；
- 不能以 oracle 當成可部署方法；
- 不能以 prediction metric 取代 matched-cost policy result；
- 不能忽略 confidence prompt token、completion token 或額外 API call。

---

## 16. 最精簡的論文故事

如果後續結果支持主要假設，整篇論文可以用以下方式串接：

1. **問題**：更多 test-time compute 並非對每題都有價值，固定配置浪費有限資源。
2. **觀察**：模型完成一段 prefix 後，可見流程狀態揭示題目目前的進度。
3. **不足**：流程狀態雖然便宜，但同一狀態內仍存在「可救回、無法改善、可能被改壞」的差異。
4. **方法**：以 visible progress 作第一層篩選，只對模糊案例取得 action-conditional counterfactual confidence。
5. **成本設計**：將 confidence 成本與 downstream saving 分開，再進行完整端到端核算。
6. **政策**：在固定全域 token ledger 下，依預期 benefit、harm 與 cost 排序 continuation。
7. **驗證**：與 fixed、random matched、process-only、query-all confidence 比較，使用 held-out matched-cost policy evaluation。
8. **貢獻**：提出一個黑箱、post-prefix、成本感知，並直接預測額外運算價值的資源配置框架。

---

## 17. 下一步執行順序

建議按照以下順序進行，避免直接投入高成本正式實驗：

1. **Stage A：成本分解**——使用既有資料，確認 gross saving、confidence cost 與 net saving。
2. **凍結 Stage B prompt**——設計短 JSON counterfactual-confidence protocol。
3. **Stage B smoke**——只確認解析率、成本、變異與 protocol feasibility。
4. **Stage C signal gate**——在既有 action bank 上確認是否優於 correctness confidence 與 process-only。
5. **Stage C policy replay**——同時報告 downstream-only 與 end-to-end cost。
6. **只有通過前述 gate 才做 Stage D**——使用新 held-out questions 做 matched-ledger confirmatory experiment。
7. **最後再擴展跨任務或跨模型驗證**——避免在主方法尚未成立前擴大成本。

---

## 18. 給後續 Agent 的實作原則

1. 不得用 test set 選 prompt、threshold、state eligibility 或 cost penalty。
2. 所有 split 以 `question_id` 為單位，避免同題洩漏。
3. 所有信心輸出保存 raw response、parsed fields、thinking、done reason 與實際 token。
4. confidence completion 應短而結構化，不要求重新解題。
5. continuation 不應看到 confidence response，除非另設干預實驗。
6. 必須同時產生 downstream-only 與 total-cost-inclusive 報表。
7. 比較政策時使用相同 actual total-token ledger；nominal budget 不等於實際成本。
8. Bootstrap 應重算 policy 與 cost matching，不只對最後一欄做獨立抽樣。
9. Oracle 只用於 headroom 與上界，不可出現在可部署主方法描述中。
10. 若 state support 不足，標示 inconclusive／insufficient support，不可偷偷合併狀態。
11. 若 H3 成立但 H5 失敗，結論應是 elicitation overhead 問題，不是直接否定 confidence concept。
12. 所有正式結果要附 parser audit、duplicate check、error audit 與 cost identity check。

---

## 19. 最終研究命題

本研究最終要驗證的，不是「模型說自己有沒有信心」這個孤立問題，而是：

> 在模型已經完成一段推理後，流程狀態能否先界定它目前的位置；而一個針對 stop/continue action 設計、成本足夠低的反事實信心，能否進一步估計追加運算的價值，讓系統在固定全域資源下做出更好的配置？

這個命題同時保留三個研究核心：

- **流程**：模型目前做到哪裡；
- **信心**：模型預期停止或繼續會發生什麼；
- **資源配置**：有限 token 應該給誰，以及是否真正形成端到端效益。

它不是單純研究 confidence calibration，也不是單純研究 token stopping，而是一個以 continuation value 為中心、將訊號成本納入決策的 test-time compute allocation 問題。

---

## 20. 專案內的證據與設計依據

後續 Agent 在實作前，應優先對照以下文件：

- `experiments/v3-budget-pilot/results/process_stage3_report.md`：held-out visible-progress matched-cost 結果。
- `experiments/v3-budget-pilot/process_stage3_confirmatory_plan.md`：Stage 3 的政策、成本公式與推論規格。
- `experiments/v3-budget-pilot/results/process_stage1_6_report.md`：process × confidence 的預測與 cost-aware policy 分析。
- `experiments/v3-budget-pilot/results/process_confidence_audit_report.md`：不同 timing、model、budget 與 process state 下的 confidence audit。
- `experiments/v3-budget-pilot/results/prospective_conf_analysis.md`：prospective／retrospective confidence 與 token、accuracy 的關係。
- `deliverables/advisor-research-proposal/paper_survey_adaptive_test_time_compute_zh.md`：adaptive test-time compute 與 confidence allocation 的文獻定位。

本文件若與正式 pre-registered plan 發生衝突，應以該階段經確認並在資料收集前凍結的 plan 為準。
