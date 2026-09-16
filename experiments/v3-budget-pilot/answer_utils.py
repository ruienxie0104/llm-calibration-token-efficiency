"""
Shared answer parsing utilities for V3 experiments.
Brace-aware boxed parser + fraction-safe normalization.
"""
import re, ast

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

def normalize_answer(ans):
    """Normalize for comparison. Convert \frac{a}{b} to a/b before removing LaTeX."""
    if not ans: return ""
    ans = re.sub(r'\\frac\s*\{\s*([^}]+)\s*\}\s*\{\s*([^}]+)\s*\}', r'\1/\2', ans.strip())
    ans = re.sub(r'\\[a-z]+', '', ans)
    ans = re.sub(r'[{}]', '', ans)
    return ans.replace(' ', '').lower()

def is_correct(predicted, expected):
    if not predicted: return False
    if normalize_answer(predicted) == normalize_answer(expected): return True
    try:
        def safe_eval(expr):
            expr = re.sub(r'\\frac\s*\{\s*([^}]+)\s*\}\s*\{\s*([^}]+)\s*\}', r'(\1)/(\2)', expr)
            expr = re.sub(r'\\[a-z]+', '', expr)
            expr = expr.replace('{', '(').replace('}', ')')
            expr = expr.replace('\\pi', str(3.141592653589793))
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
    assert normalize_answer(r'\frac{2}{21}') == '2/21'
    assert normalize_answer(r'\frac{22}{1}') == '22/1'
    assert normalize_answer(r'\frac{2}{21}') != normalize_answer(r'\frac{22}{1}')
    # is_correct fraction safety
    assert is_correct(r'\frac{2}{21}', r'\frac{2}{21}') == True
    assert is_correct(r'\frac{2}{21}', r'\frac{22}{1}') == False
    assert is_correct(r'\frac{1}{23}', r'\frac{12}{3}') == False
    assert is_correct(r'\frac{3}{4}', '0.75') == True
    assert is_correct('42', '42') == True
    assert is_correct('42', '43') == False
    assert is_correct(r'\frac{1}{2}', '0.5') == True
    print(f'All tests PASSED')

if __name__ == '__main__':
    _test()