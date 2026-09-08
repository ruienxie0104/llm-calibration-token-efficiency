#!/usr/bin/env python3
"""
Phase 3: Requirement Ground Truth + IRT Calibration.

4 models × 60 questions (MATH-500 L3+L4) × 3 budgets × 3 reps
= 2160 answer calls + 2160 confidence calls = 4320 total API calls.

Outputs:
- raw_responses_phase3.json  (all API responses)
- calibration_phase3.json    (Brier, conf gap, LCAE)
- irt_phase3.json            (Rasch model parameters)
- budget_sensitivity.json    (accuracy per model×budget)
"""
import json, os, time, urllib.request, urllib.error, re, random
from pathlib import Path
from collections import defaultdict

from datasets import load_dataset

# ============================================================
# CONFIG
# ============================================================
OLLAMA_URL = os.environ.get("OLLAMA_API_URL", "https://ollama.com/api/chat")
OLLAMA_KEY = os.environ.get("OLLAMA_API_KEY", "")
RESULTS_DIR = Path("experiments/v3-budget-pilot/results")
DATA_DIR = Path("experiments/v3-budget-pilot/data")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

MODELS = [
    "GPT-OSS-20B",
    "GPT-OSS-120B",
    "DeepSeek-V4-Flash-158B",
    "GLM-5.2-756B",
]

MODEL_MAP = {
    "GPT-OSS-20B": "gpt-oss:20b-cloud",
    "GPT-OSS-120B": "gpt-oss:120b-cloud",
    "DeepSeek-V4-Flash-158B": "deepseek-v4-flash:cloud",
    "GLM-5.2-756B": "glm-5.2:cloud",
}

BUDGETS = [256, 512, 1024]
REPLICATES = 3

# 60 questions: Level 3 (30) + Level 4 (30)
QUESTIONS_PER_LEVEL = 30
SEED = 42


# ============================================================
# QUESTION LOADING
# ============================================================
def load_questions():
    """Load 60 questions: 30 L3 + 30 L4 from MATH-500."""
    rng = random.Random(SEED)
    ds = load_dataset("HuggingFaceH4/MATH-500", split="test")
    selected = []
    for level in [3, 4]:
        candidates = [d for d in ds if d["level"] == level]
        chosen = rng.sample(candidates, QUESTIONS_PER_LEVEL)
        for c in chosen:
            selected.append({
                "id": c["unique_id"],
                "problem": c["problem"],
                "answer": c["answer"],
                "level": c["level"],
                "subject": c["subject"],
            })
    return selected


# ============================================================
# API CALL
# ============================================================
def call_ollama(model_name, messages, max_tokens=0):
    """Call Ollama. max_tokens>0 applies budget limit."""
    payload = {
        "model": MODEL_MAP[model_name],
        "messages": messages,
        "stream": False,
    }
    if max_tokens > 0:
        payload["options"] = {"num_predict": max_tokens, "temperature": 0.0}

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA_URL, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {OLLAMA_KEY}"},
    )
    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
            elapsed = time.time() - start
            content = body.get("message", {}).get("content", "")
            pt = body.get("prompt_eval_count", 0)
            ct = body.get("eval_count", 0)
            return content, pt, ct, elapsed, None
    except urllib.error.HTTPError as e:
        return None, 0, 0, 0, f"HTTP {e.code}"
    except Exception as e:
        return None, 0, 0, 0, str(e)


# ============================================================
# ANSWER PARSING
# ============================================================
def extract_boxed(text):
    if not text: return None
    m = re.findall(r'\\boxed\{(.*?)\}', text, re.DOTALL)
    return m[-1].strip() if m else None

def normalize(a):
    if not a: return ""
    a = re.sub(r'\\[a-z]+', '', a.strip())
    a = re.sub(r'[{}]', '', a)
    return a.replace(' ', '').lower()

def is_correct(pred, exp):
    if not pred: return False
    if normalize(pred) == normalize(exp): return True
    # Numeric fallback
    try:
        import ast
        def safe_eval(s):
            s = s.replace('\\frac','').replace('{','(').replace('}',')')
            s = s.replace('\\pi','3.141592653589793')
            t = ast.parse(s, mode='eval')
            for n in ast.walk(t):
                if not isinstance(n, (ast.Expression, ast.Constant,
                                      ast.Add, ast.Sub, ast.Mult, ast.Div,
                                      ast.Pow, ast.UnaryOp, ast.USub,
                                      ast.BinOp)):
                    return None
            return eval(compile(t, '', 'eval'))
        pv, ev = safe_eval(pred), safe_eval(exp)
        if pv is not None and ev is not None and abs(pv - ev) < 1e-6:
            return True
    except:
        pass
    return False


# ============================================================
# CONFIDENCE EXTRACTION
# ============================================================
def parse_confidence(text):
    """Extract single number 0-100 from confidence response."""
    if not text: return None
    nums = re.findall(r'(\d+)', text.strip())
    if nums:
        return min(100, max(0, int(nums[0])))
    return None


# ============================================================
# IRT RASCH MODEL
# ============================================================
def estimate_rasch(response_matrix):
    """
    Estimate Rasch model parameters using simple iterative method.

    response_matrix: dict of {model_name: {question_id: 0/1}}
    Returns: {model: {theta}, item: {beta,}, item_order}
    """
    import math

    models = sorted(response_matrix.keys())
    items = set()
    for m in models:
        items.update(response_matrix[m].keys())
    items = sorted(items)

    # Initialize theta=0, beta=0
    theta = {m: 0.0 for m in models}
    beta = {i: 0.0 for i in items}

    def logistic(x):
        return 1.0 / (1.0 + math.exp(-x))

    # Iterate (simple alternating estimation)
    for _ in range(50):
        # Update betas (fixed thetas)
        for i in items:
            num, den = 0.0, 0.0
            for m in models:
                if i in response_matrix[m]:
                    p = logistic(theta[m] - beta[i])
                    num += response_matrix[m][i] - p
                    den += p * (1 - p)
            if den > 1e-10:
                beta[i] += num / den

        # Update thetas (fixed betas)
        for m in models:
            num, den = 0.0, 0.0
            for i in response_matrix[m]:
                if i in beta:
                    p = logistic(theta[m] - beta[i])
                    num += response_matrix[m][i] - p
                    den += p * (1 - p)
            if den > 1e-10:
                theta[m] += num / den

    # Center item difficulties (mean=0)
    beta_mean = sum(beta.values()) / len(beta)
    for i in beta:
        beta[i] -= beta_mean

    return {"theta": theta, "beta": beta, "items": items}


def compute_lcae(theta, beta, response_matrix, confidences):
    """
    Compute LCAE: mean squared error between calibrated confidence
    and IRT-predicted error probability.

    confidences: {model: {question_id: confidence_value}}
    Returns: {model: lcae_score, model_item: {q: prob_error, conf, diff}}
    """
    import math
    def logistic(x):
        return 1.0 / (1.0 + math.exp(-x))

    results = {}
    for model in response_matrix:
        items_data = []
        for qid in response_matrix[model]:
            if qid in beta and qid in confidences.get(model, {}) and confidences[model][qid] is not None:
                theta_m = theta.get(model, 0)
                beta_i = beta.get(qid, 0)
                prob_error = 1.0 - logistic(theta_m - beta_i)  # IRT-predicted error prob
                conf = confidences[model][qid]
                conf_error = 1.0 - (conf / 100.0)  # Model's self-assessed error prob
                items_data.append({
                    "question_id": qid,
                    "irt_error_prob": prob_error,
                    "conf_error_prob": conf_error,
                    "confidence": conf,
                    "raw_error": conf_error - prob_error,
                })
        if items_data:
            mse = sum((d["conf_error_prob"] - d["irt_error_prob"]) ** 2 for d in items_data) / len(items_data)
        else:
            mse = None
        results[model] = {"lcae": mse, "items": items_data}
    return results


# ============================================================
# MAIN
# ============================================================
def main():
    questions = load_questions()

    # Save question list
    q_path = DATA_DIR / "phase3_questions.json"
    with open(q_path, "w") as f:
        json.dump(questions, f, indent=2)
    print(f"Loaded {len(questions)} questions (L3: {sum(1 for q in questions if q['level']==3)}, L4: {sum(1 for q in questions if q['level']==4)})")

    total_calls = len(questions) * len(MODELS) * len(BUDGETS) * REPLICATES
    total_with_conf = total_calls * 2  # answer + confidence = 4320
    print(f"Total: {total_calls} answer calls + {total_calls} conf calls = {total_with_conf}")
    print()

    # Check for existing checkpoint
    checkpoint = RESULTS_DIR / "phase3_raw.json"
    existing_results = []
    if checkpoint.exists():
        try:
            with open(checkpoint) as f:
                existing_results = json.load(f)
            print(f"Found existing checkpoint: {len(existing_results)} calls")
        except:
            pass

    # Build set of already-completed calls
    done_set = set()
    for r in existing_results:
        key = (r["model"], r["budget"], r["replicate"], r["question_id"], r["call_type"])
        done_set.add(key)

    results = list(existing_results)
    call_count = len(existing_results)
    start_time = time.time()

    for model in MODELS:
        for budget in BUDGETS:
            for rep in range(1, REPLICATES + 1):
                for q in questions:
                    # --- Answer call ---
                    ak = (model, budget, rep, q["id"], "answer")
                    if ak in done_set:
                        continue

                    call_count += 1
                    elapsed = time.time() - start_time
                    eta = (total_with_conf - call_count) / (call_count / elapsed) if elapsed > 0 and call_count > 0 else 0

                    print(f"[{call_count}/{total_with_conf}] {model} b={budget} r={rep} q={q['id'][:20]} (L{q['level']}) [answer]", end=" ... ", flush=True)

                    msg = [{"role": "user",
                            "content": f"Solve the math problem step by step, then give the final answer in \\boxed{{}}.\n\n{q['problem']}"}]
                    content, pt, ct, t_elap, err = call_ollama(model, msg, max_tokens=budget)
                    if err:
                        print(f"ERR: {err}")
                        continue

                    boxed = extract_boxed(content) if content else None
                    correct = is_correct(boxed, q["answer"])

                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "level": q["level"], "subject": q["subject"],
                        "call_type": "answer", "correct": correct,
                        "parsed_answer": boxed or "", "expected_answer": q["answer"],
                        "content": content, "prompt_tokens": pt, "completion_tokens": ct,
                        "elapsed": t_elap,
                    })
                    print(f"acc={'✓' if correct else '✗'} tok={ct}")

                    # --- Confidence call ---
                    ck = (model, budget, rep, q["id"], "confidence")
                    if ck in done_set:
                        continue

                    call_count += 1
                    conf_msg = [
                        {"role": "user",
                         "content": f"Solve the math problem step by step, then give the final answer in \\boxed{{}}.\n\n{q['problem']}"},
                        {"role": "assistant", "content": content or ""},
                        {"role": "user",
                         "content": "Based on your reasoning above, how confident are you that your answer is correct? Give ONLY a single number from 0 to 100."},
                    ]
                    conf, pt2, ct2, t2, err2 = call_ollama(model, conf_msg)
                    conf_val = parse_confidence(conf)

                    results.append({
                        "model": model, "budget": budget, "replicate": rep,
                        "question_id": q["id"], "level": q["level"], "subject": q["subject"],
                        "call_type": "confidence", "correct": correct,
                        "confidence_raw": conf or "",
                        "confidence_value": conf_val,
                        "prompt_tokens": pt2, "completion_tokens": ct2,
                        "elapsed": t2,
                    })
                    print(f"    [{call_count}/{total_with_conf}] [conf] conf={conf_val} tok={ct2}")

                    # Save checkpoint every 50 calls
                    if call_count % 50 == 0:
                        with open(checkpoint, "w") as f:
                            json.dump(results, f, indent=2)

                    time.sleep(0.25)

    # Save all raw responses
    raw_path = RESULTS_DIR / "phase3_raw.json"
    with open(raw_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved raw: {raw_path}")

    # ============================================================
    # ANALYSIS
    # ============================================================
    answer_calls = [r for r in results if r["call_type"] == "answer"]
    conf_calls = [r for r in results if r["call_type"] == "confidence"]

    # --- 1. Budget Sensitivity ---
    print("\n\n=== BUDGET SENSITIVITY ===")
    for model in MODELS:
        print(f"\n--- {model} ---")
        for budget in BUDGETS:
            rr = [r for r in answer_calls if r["model"] == model and r["budget"] == budget]
            n = len(rr)
            c = sum(1 for r in rr if r["correct"])
            avg_tok = sum(r["completion_tokens"] for r in rr) / n if n else 0
            print(f"  Budget {budget}: acc={c}/{n}={c/n*100:.1f}% avg_tok={avg_tok:.0f}")

    # --- 2. Calibration (Raw Confidence) ---
    print("\n\n=== RAW CONFIDENCE CALIBRATION ===")
    for model in MODELS:
        print(f"\n--- {model} ---")
        for budget in BUDGETS:
            cc = [r for r in conf_calls if r["model"] == model and r["budget"] == budget]
            # Match answer calls for correctness
            ac = [r for r in answer_calls if r["model"] == model and r["budget"] == budget]
            if not cc or not ac:
                continue
            # Build lookup: (model, budget, rep, qid) -> correct
            correct_map = {}
            for r in ac:
                correct_map[(r["model"], r["budget"], r["replicate"], r["question_id"])] = r["correct"]
            n = len(cc)
            confs = [(r["confidence_value"], correct_map.get((r["model"], r["budget"], r["replicate"], r["question_id"]), None))
                     for r in cc if r["confidence_value"] is not None]
            valid = [(c, ok) for c, ok in confs if ok is not None]
            if not valid:
                continue
            avg_conf = sum(c for c, _ in valid) / len(valid)
            correct_conf = [c for c, ok in valid if ok]
            wrong_conf = [c for c, ok in valid if not ok]
            avg_correct = sum(correct_conf) / len(correct_conf) if correct_conf else 0
            avg_wrong = sum(wrong_conf) / len(wrong_conf) if wrong_conf else 0
            # Brier score
            brier = sum((c / 100.0 - (1 if ok else 0)) ** 2 for c, ok in valid) / len(valid)
            gap = avg_correct - avg_wrong
            print(f"  Budget {budget}: n={len(valid)} Brier={brier:.4f} avg_conf={avg_conf:.0f} correct_conf={avg_correct:.0f} wrong_conf={avg_wrong:.0f} gap={gap:.1f}")

    # --- 3. IRT Calibration ---
    print("\n\n=== IRT CALIBRATION (Rasch + LCAE) ===")
    # Build response matrix for ALL budgets (combine all budgets to get more data per model×item)
    # Only use correctness from answer calls
    from collections import defaultdict
    resp_matrix = defaultdict(dict)
    conf_matrix = defaultdict(dict)

    for model in MODELS:
        for qid in set(r["question_id"] for r in answer_calls if r["model"] == model):
            # Majority vote across all budgets and replicates
            rr = [r for r in answer_calls if r["model"] == model and r["question_id"] == qid]
            correct_votes = sum(1 for r in rr if r["correct"])
            total_votes = len(rr)
            if total_votes > 0:
                resp_matrix[model][qid] = 1 if correct_votes > total_votes / 2 else 0

            # Average confidence across all calls
            cc = [r for r in conf_calls if r["model"] == model and r["question_id"] == qid and r["confidence_value"] is not None]
            if cc:
                conf_matrix[model][qid] = sum(r["confidence_value"] for r in cc) / len(cc)

    rasch = estimate_rasch(dict(resp_matrix))
    print(f"\nItem difficulties: min={min(rasch['beta'].values()):.2f} max={max(rasch['beta'].values()):.2f}")
    for m, t in rasch["theta"].items():
        print(f"  {m:30s}: θ={t:.3f}")

    lcae = compute_lcae(rasch["theta"], rasch["beta"], dict(resp_matrix), dict(conf_matrix))
    print("\nLCAE scores:")
    for model in MODELS:
        if model in lcae and lcae[model]["lcae"] is not None:
            print(f"  {model:30s}: LCAE={lcae[model]['lcae']:.4f}")

    # --- Save analysis outputs ---
    cal_path = RESULTS_DIR / "calibration_phase3.json"
    cal_data = {}
    for model in MODELS:
        cal_data[model] = {}
        for budget in BUDGETS:
            cc = [r for r in conf_calls if r["model"] == model and r["budget"] == budget]
            ac = [r for r in answer_calls if r["model"] == model and r["budget"] == budget]
            correct_map = {}
            for r in ac:
                correct_map[(r["model"], r["budget"], r["replicate"], r["question_id"])] = r["correct"]
            valid = [(r["confidence_value"], correct_map.get((r["model"], r["budget"], r["replicate"], r["question_id"]), None))
                     for r in cc if r["confidence_value"] is not None]
            valid = [(c, ok) for c, ok in valid if ok is not None]
            if not valid:
                continue
            avg_c = sum(c for c, _ in valid) / len(valid)
            correct_c = sum(c for c, ok in valid if ok) / max(1, sum(1 for _, ok in valid if ok))
            wrong_c = sum(c for c, ok in valid if not ok) / max(1, sum(1 for _, ok in valid if not ok))
            brier = sum((c/100.0 - (1 if ok else 0))**2 for c, ok in valid) / len(valid)
            cal_data[model][str(budget)] = {
                "n": len(valid), "n_correct": sum(1 for _, ok in valid if ok),
                "brier": brier, "avg_confidence": avg_c,
                "conf_correct": correct_c, "conf_wrong": wrong_c,
                "confidence_gap": correct_c - wrong_c,
            }
    with open(cal_path, "w") as f:
        json.dump(cal_data, f, indent=2)
    print(f"\nSaved calibration: {cal_path}")

    budget_path = RESULTS_DIR / "budget_sensitivity_phase3.json"
    budget_data = {}
    for model in MODELS:
        budget_data[model] = {}
        for budget in BUDGETS:
            rr = [r for r in answer_calls if r["model"] == model and r["budget"] == budget]
            n = len(rr)
            c = sum(1 for r in rr if r["correct"])
            avg_tok = sum(r["completion_tokens"] for r in rr) / n if n else 0
            budget_data[model][str(budget)] = {
                "n": n, "correct": c, "accuracy": c/n if n else 0,
                "avg_tokens": avg_tok,
            }
    with open(budget_path, "w") as f:
        json.dump(budget_data, f, indent=2)
    print(f"Saved budget sensitivity: {budget_path}")

    irt_path = RESULTS_DIR / "irt_phase3.json"
    irt_data = {
        "theta": rasch["theta"],
        "beta": rasch["beta"],
        "items": rasch["items"],
        "lcae": {m: {"lcae": lcae[m]["lcae"]} for m in MODELS if m in lcae and lcae[m]["lcae"] is not None},
    }
    with open(irt_path, "w") as f:
        json.dump(irt_data, f, indent=2)
    print(f"Saved IRT: {irt_path}")

    print(f"\nDone. Total calls: {call_count} ({time.time()-start_time:.0f}s)")


if __name__ == "__main__":
    main()