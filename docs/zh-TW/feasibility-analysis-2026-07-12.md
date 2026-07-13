# 可行性分析：Process Mining × LLM Token Efficiency 方向

> **日期：** 2026-07-12
> **背景：** 7/4 跟老師開會後，老師建議探索 Process Mining 方向。7/12 完成兩波文獻調查。
> **目的：** 結合現有文獻、研究脈絡、和實際考量，分析這個方向是否可行，以及怎麼做最好。

---

## 一、先回答核心問題：這是一個可行的研究方向嗎？

**是的，而且比原本純 token efficiency 方向更強。** 原因有四：

### 1. 新穎性更高

原本的 token efficiency 方向有一個弱點：難度感知 token 分配已經很多人在做（集群 A 有 ~10 篇），你的差異化靠的是「用 LCAE/IRT 當信號」這個特定角度。雖然沒人做，但故事是「同一個問題換一個信號」。

加入 Process Mining（流程探勘）後，故事變成「用 PM 方法分析推理軌跡品質，連接校準和 token 效率」——這是方法論層級的創新，不只是換信號。目前 7 篇 PM × LLM 論文中，沒有人把 PM 當分析框架來量測 LLM 推理軌跡品質。

### 2. 跟老師的興趣對齊

老師主動提了 Process Mining，還介紹了 BPI Challenge、Springer 書、醫療流程（DRG）。這不是隨口提的——老師在鋪路。如果你沿著這個方向做，老師的指導意願和資源投入會更高。

### 3. 跟學姐的框架銜接更好

原本的 story：
```
校準好 → token 分配品質好（但「分配品質好」只有量化指標，缺乏質化解釋）
```

加入 PM 後的 story：
```
校準好 → 推理路徑更合理（PM 量化）→ token 分配更有效率
```

PM 提供了「為什麼校準好的模型 token 分配更好」的解釋工具。不只是說「校準好的模型 excess token（多餘 token）更少」，還能說「因為它的推理路徑沒有在第 3 步繞路」。這從描述性發現變成診斷性發現，論文厚度完全不同。

### 4. 有實證基線可參考

- Progressive Crystallization：agent → deterministic workflow（確定性工作流），成本降 70%
- CacheRL：小模型 + 快取，100x 更少 compute（運算量），process accuracy（流程準確度）92%
- BPOP：trace de-linearization（軌跡去線性化）+ context pruning（上下文修剪），token 顯著減少

這些數字給你的論文提供了 comparison baseline（比較基線）和 motivation（研究動機）來源。

---

## 二、研究地景全景

### 目前文獻的分布

```
                    Token Efficiency
                         ↑
                         |
        集群A (難度感知)  |   ← 你的位置在這裡
        ~10篇            |   (PM × LCAE × Token)
                         |
--------- PM分析 ------+---- LLM生成 -------→ Process Mining
                         |
        集群B (信心校準)  |   集群A1 (PM→LLM)
        ~8篇             |   ~5篇 (Berti, PMAx...)
                         |
                         |
        集群C (test-time) |   集群A2 (PM←LLM)
        ~9篇             |   ~3篇 (BPOP, M2-PALE...)
                         |   ← 這裡幾乎空的
                         |
                         ↓
```

**你的位置：PM ← LLM 方向（用 PM 分析 LLM 行為）× Token Efficiency**

這個交集目前只有 BPOP 一篇真正沾到邊（用 PM 技術分析 agent trace 來做 context pruning 省 token），但 BPOP 做的是 agent workflow（代理工作流）不是 reasoning trace（推理軌跡），且不用 IRT/LCAE 框架。

### 你的獨特組合

| 元素 | 來源 | 是否有人做過 |
|------|------|-------------|
| IRT/LCAE 校準框架 | 學姐 | ✅ 學姐已建立 |
| Token 分配品質指標 | 原提案 | ❌ 沒人用 LCAE 預測 |
| PM 分析推理軌跡 | 新方向 | ❌ 完全空白 |
| 因果鏈：校準→路徑品質→token 效率 | 整合 | ❌ 連概念都沒人提過 |

**四個元素同時出現 = 零競爭者。**

---

## 三、具體怎麼接：三種方案比較

### 方案 A：PM 當分析工具（穩，推薦）

**定位：** 原本的 token allocation（token 分配）品質研究為主軸，PM 當分析框架

**論文故事：**
> 學姐證明 IRT 難度信號能改善信心校準。我們進一步發現：校準好的模型不只 token 分配更合理（量化），而且推理路徑品質更高（PM 質化分析）。我們用 process discovery（流程發現）和 conformance checking（一致性檢查）分析模型的 CoT 推理軌跡，發現校準好的模型推理路徑更直接、更少繞路，這解釋了為什麼它們的 token 分配更有效率。

**實驗設計：**
- Phase 1：跟原提案一樣，測量 LCAE × excess token usage 的關聯性
- Phase 2：新增 PM 分析——把 CoT steps 當 event log（事件日誌），跑 process discovery 看不同 LCAE 模型的推理路徑模式
- Phase 3：conformance checking——定義「理想推理路徑」，測偏離程度，看是否與 LCAE 相關
- Phase 4（bonus）：基於 PM 分析設計 token 分配策略

**優點：**
- 不改主軸，PM 是加分項
- 如果 PM 分析結果不顯著，論文仍可用 Phase 1 的量化結果支撐
- 老師的 PM 建議有回應到，但不賭全部

**風險：**
- PM 分析可能只是裝飾，reviewer 覺得沒有深入 PM 方法論
- 需要定義「理想推理路徑」這個概念，可能不容易

### 方案 B：PM 當核心方法（大膽，高回報）

**定位：** 用 PM 方法分析 LLM 推理軌跡品質是主要貢獻，LCAE/token 是 application（應用）

**論文故事：**
> LLM 推理軌跡是一種 process trace（流程軌跡）。我們首次將 Process Mining 技術（discovery, conformance checking, enhancement）應用於 LLM 推理軌跡分析，提出一套推理路徑品質評估框架。在此框架下，我們發現模型的自我評估校準能力（LCAE）與推理路徑品質正相關，且校準改善能因果性地提升推理路徑效率，進而改善 token 分配品質。

**實驗設計：**
- 定義 mapping（映射）：CoT step → event，question → case，model → variant
- 用 PM4Py（open-source PM library，開源流程探勘函式庫）做 process discovery
- 建構「理想推理路徑」（可能用高 LCAE + 正確答題的 trace 當 baseline）
- Conformance checking 測偏離
- 連接 LCAE 和 PM-derived（PM 衍生）路徑品質指標
- 驗證因果鏈

**優點：**
- 方法論貢獻更大——首次用 PM 分析 LLM 推理
- 老師的興趣完全對齊
- 如果成功，novelty（新穎性）非常強
- 可以投更好的會議（AAAI / WWW / SIGKDD level）

**風險：**
- PM 方法需要深入學習，不是拿來就用
- CoT step → event 的 mapping 需要驗證合理性
- 「理想推理路徑」難定義——不同問題有不同解法
- 如果 PM 指標跟 token 效率不相關，整篇論文就垮了
- 時間成本更高

### 方案 C：兩層架構（平衡）

**定位：** 量化 + 質化雙軌

**論文故事：**
> 我們從量和質兩個維度分析 LLM token 分配品質。量化方面，我們測量 LCAE 與 excess token usage 的關係。質化方面，我們首次引入 Process Mining 技術分析推理軌跡，發現校準好的模型推理路徑結構更合理。兩個維度交叉驗證，共同支撐「校準好 → 分配好」的因果鏈。

**實驗設計：**
- Track 1（量化）：原提案的 Phase 1-2，LCAE × token 指標
- Track 2（質化）：PM 分析推理軌跡，PM-derived 路徑品質指標
- 交叉驗證：量化指標和 PM 指標是否一致？LCAE 能否同時預測兩者？

**優點：**
- 兩條軌互相支撐，一條弱另一條可以補
- 貢獻面更廣（量化 + 質化）
- 老師的 PM 建議有完整回應
- 如果 PM 軌成功，是亮點；如果不行，量化軌仍可獨立成篇

**風險：**
- 工作量最大
- 需要平衡兩條軌的篇幅，避免都做不深
- PM 部分如果只做表面，reviewer 會批評

---

## 四、我的建議：方案 C，但有主次

**推薦：方案 C（兩層架構），以量化為主、PM 為輔。**

理由：

1. **量化軌是保險**：LCAE × excess token usage 的分析不需要新方法論，直接用學姐資料 + token 測量就能做。就算 PM 完全失敗，這條軌仍是一篇完整論文。

2. **PM 軌是亮點**：用 PM 分析推理軌跡是新東西，做好了是論文最大的賣點。但不需要做完整 PM 方法論——用現有工具（PM4Py）跑 process discovery + conformance checking 就夠了。

3. **時間規劃合理**：
   - 7-8月：跑量化實驗（Phase 1-2），同時學 PM 基礎
   - 9月：跑 PM 分析（Phase 3）
   - 10月：整合寫作
   - 11月：投出
   - 目標：AAAI 2027（通常 8月截止）或 IEEE IRI 2027（延續學姐）

4. **降級方案清晰**：
   - 最好情況：量化 + PM 雙軌都成功 → 投 top venue（頂級會議）
   - 中等情況：量化成功、PM 有部分結果 → PM 當分析工具寫進 discussion（討論）
   - 最差情況：量化也有問題 → 至少有 PM 這個新角度撐住

---

## 五、關鍵風險與緩解

| 風險 | 機率 | 影響 | 緩解 |
|------|------|------|------|
| PM 指標跟 token 效率不相關 | 中 | 高 | 量化軌獨立存在；PM 當探索性分析而非核心假設 |
| CoT step → event mapping 不合理 | 中 | 中 | 用多種 segmentation 策略（sentence-level / paragraph-level / step-level）做 robustness check（穩健性檢查） |
| 「理想推理路徑」難定義 | 高 | 中 | 不定義理想路徑，改用「高 LCAE 模型的平均路徑」當 baseline；或用 conformance checking 的標準 deviance 指標 |
| PM 方法學習曲線 | 中 | 中 | PM4Py 有完整文檔和教學；Berti 的論文有實作範例；只用到 discovery + conformance，不需要發明新 PM 演算法 |
| 老師對 PM 期望過高 | 低 | 中 | 在下次 meeting 明確說明「PM 當分析工具不是研究 PM 方法本身」，對齊期望 |

---

## 六、跟老師怎麼講

下次 meeting 建議這樣定位：

> 我查了 Process Mining × LLM 的文獻，發現目前沒有人用 PM 技術分析 LLM 的推理軌跡品質。我想把 PM 當分析工具，量測校準好的模型推理路徑是否更合理，連接到我們本來的 token 分配品質研究。簡單說就是：量化看 token 分配好不好，PM 看推理路徑好不好，兩個一起驗證「校準好 → 分配好」這個因果鏈。

然後問老師：
1. PM 部分做多深？只做 discovery + conformance checking 夠嗎？還是要做到 enhancement？
2. 醫療流程（DRG）要不要納入？還是先在一般 benchmark 做完再考慮？
3. 目標投稿場所建議？IEEE IRI 2027 延續學姐？還是試更高的？

---

## 七、結論

**這是一個可行的、而且比原本方案更強的研究方向。** 

核心原因：PM × LLM 推理軌跡分析是空白領域，你的 LCAE/IRT 框架提供了獨特的切入角度，而且老師明確表達了對 PM 方向的興趣。

推薦做法：以原本的 token allocation 量化研究為主軸，加入 PM 作為質化分析軌。兩軌互相支撐，風險分散，且 PM 軌成功時論文價值顯著提升。

最重要的下一步：跑一個小型 pilot（先導實驗）——拿 3-5 個模型 × 100 題，提取 CoT trace，用 PM4Py 跑 process discovery，看看不同 LCAE 的模型推理路徑模式有沒有明顯差異。如果有，這個方向就穩了。