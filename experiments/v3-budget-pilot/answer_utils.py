"""
Shared answer parsing utilities for V3 experiments.
Brace-aware boxed parser + fraction-safe normalization.
"""
import ast
import re

def extract_boxed(text):
    """Brace-aware \boxed{} extraction. Handles nested braces."""
    if not text: return None
    results = []
    pos = 0
    while True:
        start = text.find(r'\boxed{', pos)
        if start == -1: break
        bs = start + len(r'\boxed{')
        depth = 1; i = bs
        while i < len(text) and depth > 0:
            if text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            i += 1
        if depth == 0:
            results.append(text[bs:i-1].strip())
        pos = i
    return results[-1] if results else None

def _normalize_fraction_commands(ans):
    """Canonicalize common LaTeX fraction spellings without evaluating them."""
    ans = re.sub(r"\\(?:dfrac|tfrac)", r"\\frac", ans)
    # Standard braced form, including whitespace: \frac {a} {b}.
    ans = re.sub(
        r"\\frac\s*\{\s*([^{}]+)\s*\}\s*\{\s*([^{}]+)\s*\}",
        r"(\1)/(\2)",
        ans,
    )
    # MATH answers sometimes omit braces for one-character operands: \frac 59.
    ans = re.sub(r"\\frac\s*([^\s{}])\s*([^\s{}])", r"(\1)/(\2)", ans)
    return ans


def normalize_answer(ans):
    """Normalize harmless LaTeX surface differences for exact comparison.

    This is deliberately conservative: it canonicalizes presentation variants but
    does not use unrestricted ``eval`` or claim symbolic equivalence.
    """
    if not ans:
        return ""
    ans = ans.strip()
    ans = _normalize_fraction_commands(ans)
    ans = re.sub(r"\\(?:left|right)", "", ans)
    ans = re.sub(r"\\(?:,|!|;|:)", "", ans)
    ans = re.sub(r"\^?\{?\\circ\}?", "", ans)
    ans = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", ans)
    ans = re.sub(r"\s+", "", ans)
    return ans.lower()

def is_correct(predicted, expected):
    if not predicted: return False
    if normalize_answer(predicted) == normalize_answer(expected): return True
    try:
        def safe_eval(expr):
            expr = _normalize_fraction_commands(expr)
            expr = expr.replace("\\pi", str(3.141592653589793))
            expr = re.sub(r"\^?\{?\\circ\}?", "", expr)
            expr = re.sub(r"\\(?:left|right)", "", expr)
            expr = expr.replace("^", "**")
            expr = expr.replace("{", "(").replace("}", ")")
            tree = ast.parse(expr, mode='eval')
            for n in ast.walk(tree):
                if not isinstance(n, (ast.Expression, ast.Constant, ast.Add, ast.Sub,
                                      ast.Mult, ast.Div, ast.Pow, ast.UnaryOp, ast.USub, ast.BinOp)):
                    return None
            return eval(compile(tree, '', 'eval'))
        pv = safe_eval(predicted); ev = safe_eval(expected)
        if pv is not None and ev is not None and abs(pv - ev) < 1e-6: return True
    except: pass
    return False

def _test():
    # extract_boxed tests
    assert extract_boxed(r'\boxed{42}') == '42'
    assert extract_boxed(r'\boxed{\frac{2}{21}}') == r'\frac{2}{21}'
    assert extract_boxed(r'some \boxed{\frac{3}{4}} more') == r'\frac{3}{4}'
    assert extract_boxed(None) is None
    assert extract_boxed('') is None
    # normalize_answer fraction safety
    assert normalize_answer(r'\frac{2}{21}') == '(2)/(21)'
    assert normalize_answer(r'\frac{22}{1}') == '(22)/(1)'
    assert normalize_answer(r'\frac{2}{21}') != normalize_answer(r'\frac{22}{1}')
    # is_correct fraction safety
    assert is_correct(r'\frac{2}{21}', r'\frac{2}{21}') == True
    assert is_correct(r'\frac{2}{21}', r'\frac{22}{1}') == False
    assert is_correct(r'\frac{1}{23}', r'\frac{12}{3}') == False
    assert is_correct(r'\frac{3}{4}', '0.75') == True
    assert is_correct('42', '42') == True
    assert is_correct('42', '43') == False
    assert is_correct(r'\frac{1}{2}', '0.5') == True
    assert is_correct(r'\frac{5}{9}', r'\frac 59') == True
    assert is_correct(r'\frac{33}{100}', r'\dfrac{33}{100}') == True
    assert is_correct(r'75^\circ', '75') == True
    print(f'All tests PASSED')

if __name__ == '__main__':
    _test()
