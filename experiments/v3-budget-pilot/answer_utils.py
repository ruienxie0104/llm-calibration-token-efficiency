"""
Shared answer parsing utilities for V3 experiments.
Brace-aware boxed parser — handles nested LaTeX like \boxed{\frac{2}{21}}.
"""
import re
import ast

def extract_boxed(text):
    """Brace-aware \boxed{} extraction. Handles nested braces like \boxed{\frac{2}{21}}."""
    if not text: return None
    results = []
    pos = 0
    while True:
        start = text.find(r'\boxed{', pos)
        if start == -1: break
        brace_start = start + len(r'\boxed{')
        depth = 1
        i = brace_start
        while i < len(text) and depth > 0:
            if text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            i += 1
        if depth == 0:
            content = text[brace_start:i-1]
            results.append(content.strip())
        pos = i
    return results[-1] if results else None

def normalize_answer(ans):
    if not ans: return ""
    ans = re.sub(r'\\[a-z]+', '', ans.strip())
    ans = re.sub(r'[{}]', '', ans)
    return ans.replace(' ', '').lower()

def is_correct(predicted, expected):
    if not predicted: return False
    if normalize_answer(predicted) == normalize_answer(expected): return True
    try:
        def safe_eval(expr):
            # Convert LaTeX \frac{a}{b} to (a)/(b)
            expr = re.sub(r'\\frac\s*\{\s*([^}]+)\s*\}\s*\{\s*([^}]+)\s*\}', r'(\1)/(\2)', expr)
            expr = re.sub(r'\\[a-z]+', '', expr)
            expr = expr.replace('{', '(').replace('}', ')')
            expr = expr.replace('\\pi', str(3.141592653589793))
            tree = ast.parse(expr, mode='eval')
            for n in ast.walk(tree):
                if not isinstance(n, (ast.Expression, ast.Constant, ast.Add, ast.Sub,
                                      ast.Mult, ast.Div, ast.Pow, ast.UnaryOp, ast.USub, ast.BinOp)):
                    return False
            return eval(compile(tree, '', 'eval'))
        pv = safe_eval(predicted)
        ev = safe_eval(expected)
        if pv is not None and ev is not None and abs(pv - ev) < 1e-6: return True
    except: pass
    return False

def _test():
    cases = [
        (r'\boxed{42}', '42'),
        (r'\boxed{\frac{2}{21}}', r'\frac{2}{21}'),
        (r'some \boxed{\frac{3}{4}} more', r'\frac{3}{4}'),
        (r'\boxed{ \frac{5}{7} }', r'\frac{5}{7}'),
        (r'\boxed{x = 3}', 'x = 3'),
        (None, None), ('', None),
    ]
    for raw, exp in cases:
        r = extract_boxed(raw)
        assert r == exp, f'extract_boxed({raw!r}) = {r!r} != {exp!r}'
    assert is_correct('42', '42') == True
    assert is_correct(r'\frac{2}{21}', r'\frac{2}{21}') == True
    assert is_correct('3/4', r'\frac{3}{4}') == True, f'3/4 vs frac {{3}}{{4}} failed'
    assert is_correct('42', '43') == False
    assert is_correct(r'\frac{1}{2}', '0.5') == True
    print(f'All tests PASSED')

if __name__ == '__main__':
    _test()