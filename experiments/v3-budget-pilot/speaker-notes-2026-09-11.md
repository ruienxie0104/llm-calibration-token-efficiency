# 講稿 — 2026-09-11 指導教授會議

> 對應簡報：`presentation-2026-09-11.pptx`（23 頁）
> 預計時間：25-30 分鐘

---

## 1 — 封面

老師好，今天完整報告研究進展。從學姐的 LCAE 框架出發，經過三階段實驗，到最新的 Phase 3 結果，以及論文定位。

---

## 2 — 報告大綱

六個部分：研究動機、實驗歷程、文獻調查、Phase 3 結果、綜合分析、下一步。

---

## 3 — 學姐論文

學姐用 IRT Rasch Model 把模型能力和題目難度放在同一把尺。三個關鍵發現：能力強不等於自評準、IDS 給難度訊號最有效改善校準、提到 cost 關聯但沒深入驗證。這就是我的切入點。

---

## 4 — 我的研究問題

學姐：模型知道自己會不會？我：知道自己會不會，能不能知道自己需要思考多久？

假設：校準好的模型不是總 token 更少，是分配更合理。簡單題少 token、困難題多 token，低資源時準確率損失更小。

---

## 5 — Process Mining

把 CoT 切成活動序列，用 pm4py 分析推理結構。這樣可以看到先理解還是直接算、有沒有驗證等結構。

---

## 6 — 實驗歷程 V1→V2

V1：GSM8K 20 題，PM 能區分推理風格，但題目太簡單、無信心數據。
V2：MMLU+ARC 100 題，加入信心收集和校準指標。

---

## 7 — V2 Rebuild

執行後發現多個 bug（conformance、Levenshtein、JSD、confidence），修正後數據完全不同——GPT-20B 從 56% 跳到 98%，前一版反相關發現被推翻。PM pipeline 驗證成功，暴露了後續可避免的問題。

---

## 8 — V3 Phase 2

2 模型 480 次呼叫。確認 budget sensitivity 存在、DeepSeek 全勝，但只有 2 模型無法區分校準 vs 能力。

---

## 9 — 文獻調查

7/28 做了競爭者分析。Think Just Enough 用 raw confidence 做 stopping signal、SelfBudgeter 預估 budget 但要訓練、Capability Calibration 配置 sampling 次數不是 reasoning length。我們的差異化：IRT 校準、training-free、black-box、reasoning length。

---

## 10 — Phase 3 Budget Sensitivity

4 模型 4320 次呼叫。DeepSeek 在低 budget 壓倒性領先（@256 唯一有 acc）。GPT-120B 校準最好但低 budget 仍是 0%。能力 θ 和校準 LCAE 是兩個獨立維度。

---

## 11 — Brier vs LCAE

Brier 看 DeepSeek 最好，LCAE 看 GPT-120B 最好。選擇哪個指標會影響模型判斷。LCAE 考慮了題目難度和模型能力。

---

## 12 — 信心差距

GPT-120B 答錯時 71%，GLM-5.2 答錯時 96%。排序跟 LCAE 一致，可以做簡單代理指標。

---

## 13 — 貢獻一

新的研究問題：校準品質能不能預測 token 分配效率？從來沒有人問過這個問題。

---

## 14 — 貢獻二

Controlled Budget Sweep：先固定預算再比較。這是原創方法。

---

## 15 — 貢獻三四

發現 A：能力 θ 和 LCAE 是獨立維度。發現 B：Brier vs LCAE 排名不同。發現 C：信心差距可做代理指標。發現 D：全新 budget sensitivity 曲線。

貢獻四：雙維度框架——校準品質 × 推理效率 = 資源受限表現。

---

## 16 — 下一步

IDS intervention 建立因果鏈、論文投稿（IEEE Big Data）、Activity labeling 驗證。

---

## 17 — 謝謝

謝謝老師，歡迎討論。