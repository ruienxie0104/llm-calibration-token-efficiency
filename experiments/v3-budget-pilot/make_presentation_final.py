#!/usr/bin/env python3
"""Final comprehensive presentation for advisor meeting 2026-09-11."""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

prs = Presentation()
prs.slide_width = Inches(13.33)
prs.slide_height = Inches(7.5)

DARK = RGBColor(0x1a, 0x1a, 0x2e)
BLUE = RGBColor(0x4a, 0x6f, 0xd8)
GRAY = RGBColor(0x6b, 0x6b, 0x80)
WHITE = RGBColor(0xff, 0xff, 0xff)
LIGHT = RGBColor(0xf5, 0xf5, 0xfa)

def ts(t, s=""):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.background.fill.solid(); sl.background.fill.fore_color.rgb = DARK
    b = sl.shapes.add_textbox(Inches(1), Inches(2.2), Inches(11.33), Inches(1.5))
    b.text_frame.paragraphs[0].text = t; b.text_frame.paragraphs[0].font.size = Pt(36); b.text_frame.paragraphs[0].font.bold = True; b.text_frame.paragraphs[0].font.color.rgb = WHITE; b.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    if s:
        b2 = sl.shapes.add_textbox(Inches(1), Inches(3.8), Inches(11.33), Inches(1))
        b2.text_frame.paragraphs[0].text = s; b2.text_frame.paragraphs[0].font.size = Pt(20); b2.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xa0,0xa0,0xb0); b2.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

def sec(t, s=""):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    sl.background.fill.solid(); sl.background.fill.fore_color.rgb = BLUE
    b = sl.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.33), Inches(1.5))
    b.text_frame.paragraphs[0].text = t; b.text_frame.paragraphs[0].font.size = Pt(32); b.text_frame.paragraphs[0].font.bold = True; b.text_frame.paragraphs[0].font.color.rgb = WHITE; b.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    if s:
        b2 = sl.shapes.add_textbox(Inches(1), Inches(4), Inches(11.33), Inches(1))
        b2.text_frame.paragraphs[0].text = s; b2.text_frame.paragraphs[0].font.size = Pt(18); b2.text_frame.paragraphs[0].font.color.rgb = RGBColor(0xd0,0xd0,0xe0); b2.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

def bar(sl, t):
    b = sl.shapes.add_textbox(Inches(0.5), Inches(0.2), Inches(12.33), Inches(0.8))
    b.text_frame.paragraphs[0].text = t; b.text_frame.paragraphs[0].font.size = Pt(24); b.text_frame.paragraphs[0].font.bold = True; b.text_frame.paragraphs[0].font.color.rgb = DARK

def content(title, items, note=""):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    bar(sl, title)
    tx = sl.shapes.add_textbox(Inches(0.6), Inches(1.3), Inches(12.13), Inches(5.8))
    tf = tx.text_frame; tf.word_wrap = True
    for i, (text, lv) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = text; p.font.size = Pt(16) if lv == 0 else Pt(14)
        p.font.color.rgb = DARK if lv == 0 else GRAY; p.level = lv; p.space_after = Pt(4)
    if note: sl.notes_slide.notes_text_frame.text = note
    return sl

def table(title, hd, rows, note=""):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    bar(sl, title)
    rn = len(rows) + 1; cn = len(hd)
    ts = sl.shapes.add_table(rn, cn, Inches(0.5), Inches(1.3), Inches(12.33), Inches(0.45 * rn))
    tb = ts.table
    for j, h in enumerate(hd):
        c = tb.cell(0, j); c.text = h
        for p in c.text_frame.paragraphs: p.font.size = Pt(12); p.font.bold = True; p.font.color.rgb = WHITE; p.alignment = PP_ALIGN.CENTER
        c.fill.solid(); c.fill.fore_color.rgb = BLUE
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            c = tb.cell(i+1, j); c.text = str(v)
            for p in c.text_frame.paragraphs: p.font.size = Pt(11); p.font.color.rgb = DARK; p.alignment = PP_ALIGN.CENTER
            if i % 2 == 0: c.fill.solid(); c.fill.fore_color.rgb = LIGHT
    if note: sl.notes_slide.notes_text_frame.text = note
    return sl

# ============ BUILD ============

ts("LLM 校準 × Token Allocation:\n從 LCAE 到 Budget Sensitivity 的完整研究", "2026-09-11 · 指導教授會議報告")

content("報告大綱", [
    ("1. 研究動機：從學姐 LCAE 框架出發", 0),
    ("2. 實驗歷程：V1 → V2 → Rebuild → V3", 0),
    ("3. 7/28 文獻調查：競爭者分析與方向收斂", 0),
    ("4. Phase 3 核心結果：4320 次 API 呼叫的發現", 0),
    ("5. 綜合分析：四個貢獻與雙維度框架", 0),
    ("6. 下一步：IDS 因果實驗與論文投稿", 0),
], "老師好，今天報告完整的研究歷程。從學姐 LCAE 框架出發，經過三階段實驗，到最新的 Phase 3 結果，以及論文定位。")

sec("研究動機", "從學姐 LCAE 框架到我的研究問題")

table("學姐論文回顧 (Chen et al., IEEE IRI 2026)",
    ["階段", "內容", "關鍵發現"],
    [
        ["IRT 能力估計", "Rasch Model: σ(θ_m−β_i)\n模型能力與題目難度同一尺度", "客觀計算答錯機率"],
        ["自我評估", "四種情境: QOQ / IDS / DPR / Combined", "IDS（給難度訊號）最有效"],
        ["模型選擇", "LCAE 指標比較自估 vs 客觀", "能力強 ≠ 自評準\n提及 cost 關聯但未驗證"],
    ],
    "學姐證明了 IRT 可以客觀估計模型能力與題目難度，IDS 能改善校準。但她提到 inference cost 有關聯卻未深入，這是我的切入點。")

content("我的研究問題", [
    ("學姐回答了：模型知道自己會不會嗎？", 0),
    ("本研究進一步問：知道自己會不會 → 能否知道自己需要思考多久？", 0),
    ("", 0),
    ("核心假設", 0),
    ("  校準好的模型不一定總 token 更少，但分配更合理", 1),
    ("  簡單題少 token、困難題多 token → 低資源時準確率損失更小", 1),
], "核心假設是校準品質決定 token 分配效率，特別是在資源受限情境下。")

content("引入 Process Mining", [
    ("把 Chain-of-Thought 切成活動序列，用 pm4py 分析", 0),
    ("", 0),
    ("原始 CoT： 「先理解題意...速度=60 km/h...驗證...答案選B」", 1),
    ("  → understand → calculate → verify → answer", 1),
    ("", 0),
    ("分析面向：流程發現（Petri Net）/ 一致性檢查 / 熵分析 + JSD", 0),
], "Process Mining 讓我可以看到推理的結構，不只是 token 總量。")

sec("實驗歷程", "V1 → V2 → V2 Rebuild → V3 Phase 2 → B+C")

table("V1 → V2 改動",
    ["面向", "V1", "V2"],
    [
        ["題目", "20 GSM8K", "100 (MMLU STEM + ARC)"],
        ["模型", "5", "4（GLM-4.7 退休）"],
        ["信心", "無", "多輪對話式"],
        ["校準", "無", "Brier, 信心差距"],
        ["PM 分析", "Petri net", "Petri net + 熵 + JSD"],
    ],
    "V1 確認 PM 能區分推理風格但題目太簡單。V2 加入信心收集和校準指標。")

content("V2 Rebuild 轉折", [
    ("執行後發現多個 bug → 完整 rebuild", 0),
    ("", 0),
    ("修正項目", 0),
    ("  Conformance：讀取不存在欄位（修正）", 1),
    ("  Levenshtein：(A,B) 和 (B,A) 分別抽樣（修正）", 1),
    ("  JSD：distance 被標成 divergence（修正）", 1),
    ("  Confidence：只傳 response 沒傳 thinking（修正）", 1),
    ("", 0),
    ("Rebuild 後數據完全不同", 0),
    ("  GPT-20B 從 56% 跳到 98%，前一版核心發現被推翻", 1),
    ("  但 PM pipeline 驗證成功，暴露了後續可避免的問題", 1),
], "數據翻轉後 V2 作為校準分析價值下降，但 PM pipeline 驗證成功。")

table("V3 Phase 2 Pilot (480 calls)",
    ["Budget", "GPT-OSS-20B", "DeepSeek", "差距"],
    [
        ["128", "0.0%", "0.0%", "—"],
        ["256", "3.3%", "15.0%", "5.0×"],
        ["512", "20.0%", "33.3%", "1.7×"],
        ["1024", "31.7%", "36.7%", "1.2×"],
    ],
    "Phase 2 確認 budget sensitivity 存在，DeepSeek 全勝。但只有 2 模型無法區分校準 vs 能力 confound。")

sec("文獻調查", "7/28 Deep Research — 競爭者分析與定位收斂")

table("競爭者分析",
    ["競爭者", "已證明", "我們可差異化"],
    [
        ["Think Just Enough (EACL 2026)", "confidence → stopping signal", "信心未校準 → 我們比較 raw vs calibrated"],
        ["SelfBudgeter (ACL 2026)", "預估 budget + RL", "需 training → 我們 training-free"],
        ["Capability Cal. (arXiv 2026)", "校準→best-of-k", "配置 sampling 次數 → 我們配置 reasoning length"],
        ["Sonata (ICLR 2026)", "hidden-state adapter", "需 hidden states → 我們 black-box"],
    ],
    "核心差異化：IRT 校準、training-free、black-box、配置 reasoning length、有 IDS 因果驗證。")

sec("Phase 3 核心結果", "4 模型 × 60 題 × 3 budgets × 3 reps = 4320 calls")

table("Budget Sensitivity (完整 4 模型)",
    ["模型", "@256", "@512", "@1024", "能力 θ", "LCAE"],
    [
        ["GPT-OSS-20B", "0.0%", "19.4%", "48.3%", "−0.086", "0.341"],
        ["GPT-OSS-120B", "0.0%", "17.2%", "50.6%", "+0.003", "0.247 🏆"],
        ["DeepSeek", "18.3% 🏆", "49.4% 🏆", "66.1% 🏆", "+0.649", "0.303"],
        ["GLM-5.2", "0.0%", "4.4%", "36.7%", "−0.566", "0.438"],
    ],
    "DeepSeek 在低 budget 壓倒性領先（唯一 @256 有 acc）。GPT-120B 校準最好（LCAE=0.247）但低 budget 仍 0%。")

content("Brier vs LCAE — 兩種校準指標排名不同", [
    ("Brier 看：DeepSeek 校準最好（0.284），GPT-120B 第二（0.320）", 0),
    ("LCAE 看：GPT-120B 校準最好（0.247），DeepSeek 第二（0.303）", 0),
    ("", 0),
    ("→ 選擇哪個指標，會影響你對「哪個模型最可靠」的判斷", 0),
    ("→ LCAE 考慮了題目難度和模型能力，捕捉到 Brier 看不到的訊息", 0),
], "這是我們的重要發現：校準指標的選擇會影響模型排名。")

content("信心差距 — 誰知道自己錯了？", [
    ("@1024 時的信心數據：", 0),
    ("", 0),
    ("  GPT-120B：答對 96% / 答錯 71% → 差距 +25.5（最有自知之明 🏆）", 1),
    ("  DeepSeek：答對 100% / 答錯 84% → 差距 +15.5", 1),
    ("  GPT-20B： 答對 98% / 答錯 90% → 差距 +7.3", 1),
    ("  GLM-5.2： 答對 100% / 答錯 96% → 差距 +3.4（最沒自覺）", 1),
    ("", 0),
    ("→ 信心差距排序與 LCAE 一致 → 可以做為簡單代理指標", 0),
], "不跑 IRT，光看信心差距就能粗略估計校準品質。")

sec("綜合分析", "四個貢獻與雙維度框架")

content("貢獻一：新的研究問題", [
    ("別人問的：信心校不校準？（Brier / LCAE）", 0),
    ("我們問的：校準品質能不能預測 token 分配效率？", 0),
    ("", 0),
    ("Brier、ECE、LCAE 都是在量「模型知不知道自己的實力」", 1),
    ("但從來沒有人問：知道自己會不會 → 能不能知道自己需要想多久？", 1),
], "這是一個全新的應用場景。")

content("貢獻二：新的實驗設計", [
    ("Controlled Budget Sweep — 我們原創的方法", 0),
    ("", 0),
    ("讓同一個模型用不同的 token 預算回答同一題", 1),
    ("看誰的準確率損失最少", 1),
    ("", 0),
    ("跟所有競爭者都不同：", 0),
    ("  Think Just Enough：推理中問信心 → 決定要不要繼續想", 1),
    ("  SelfBudgeter：訓練模型預估 token 預算", 1),
    ("  我們的 budget sweep：先固定預算 → 比較誰表現更好", 1),
], "Budget sweep 是我們原創的，不是別人的方法。")

content("貢獻三與貢獻四", [
    ("貢獻三：新的發現", 0),
    ("  發現 A：能力 θ 和校準 LCAE 是獨立維度，對低資源表現影響不同", 1),
    ("  發現 B：Brier vs LCAE 排名不同 → 選擇指標影響模型判斷", 1),
    ("  發現 C：信心差距可做為 just-in-time 校準代理指標", 1),
    ("  發現 D：四種模型的 budget sensitivity 曲線（全新實證數據）", 1),
    ("", 0),
    ("貢獻四：雙維度整合框架", 0),
    ("", 0),
    ("  「校準品質 × 推理效率 = 資源受限表現」", 0),
    ("  過去分開研究 → 我們第一個系統性整合證明", 1),
], "這是最核心的論文貢獻。")

sec("下一步", "IDS 因果實驗 + 論文投稿")

content("下一步規劃", [
    ("IDS Intervention（最重要的下一步）", 0),
    ("  目前所有結果是 correlational，不能說「改善校準就能改善表現」", 1),
    ("  IDS 可以做 causal 實驗：同一模型、同一題、有 IDS vs 無 IDS", 1),
    ("  如果 IDS 改善 LCAE → 同時改善 token 分配 → 因果鏈成立", 1),
    ("", 0),
    ("論文投稿", 0),
    ("  目標 IEEE Big Data 2026（10 月截止）或 BPM/ICPM", 1),
    ("", 0),
    ("其他待完成", 0),
    ("  Activity labeling 人工驗證、PM 機制分析（entropy/JSD）", 1),
], "IDS 是跟學姐論文最直接的銜接，也是跟所有競爭者最明顯的差異化。")

ts("謝謝老師", "歡迎討論與指導")

out = "experiments/v3-budget-pilot/presentation-2026-09-11.pptx"
prs.save(out)
print(f"Saved: {out}")
print(f"Slides: {len(prs.slides)}")