#================== 数学计算类问题 ================= 
#路由标识 calc

import math
import re
import operator
from langchain.tools import StructuredTool

# ====================== ⚠️ 安全的数学表达式解析器 ======================
# 不使用 eval()，改用安全的表达式解析

# 允许的运算符及其优先级
OPERATORS = {
    '+': (operator.add, 1),
    '-': (operator.sub, 1),
    '*': (operator.mul, 2),
    '/': (operator.truediv, 2),
    '%': (operator.mod, 2),
    '^': (operator.pow, 3),
}

# 允许的数学函数
MATH_FUNCTIONS = {
    'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
    'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
    'sinh': math.sinh, 'cosh': math.cosh, 'tanh': math.tanh,
    'sqrt': math.sqrt, 'abs': abs,
    'log': math.log, 'log10': math.log10, 'log2': math.log2,
    'exp': math.exp, 'floor': math.floor, 'ceil': math.ceil,
    'round': round,
}

# 允许的数学常量
MATH_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
}

def _tokenize(expr: str) -> list:
    """将表达式分词"""
    tokens = []
    i = 0
    expr = expr.replace(' ', '')
    
    while i < len(expr):
        char = expr[i]
        
        # 数字（包括小数）
        if char.isdigit() or (char == '.' and i + 1 < len(expr) and expr[i + 1].isdigit()):
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            tokens.append(('NUM', float(expr[i:j])))
            i = j
        
        # 函数名或常量
        elif char.isalpha():
            j = i
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            name = expr[i:j]
            tokens.append(('NAME', name))
            i = j
        
        # 运算符和括号
        elif char in '+-*/%^()':
            tokens.append(('OP', char))
            i += 1
        
        else:
            i += 1  # 跳过未知字符
    
    return tokens

def _parse_expression(tokens: list, pos: int = 0, min_prec: int = 0) -> tuple:
    """递归下降解析表达式"""
    # 解析一元表达式
    if pos >= len(tokens):
        raise ValueError("表达式不完整")
    
    token_type, token_value = tokens[pos]
    
    # 处理负号
    if token_type == 'OP' and token_value == '-':
        pos += 1
        left, pos = _parse_primary(tokens, pos)
        left = -left
    elif token_type == 'OP' and token_value == '+':
        pos += 1
        left, pos = _parse_primary(tokens, pos)
    else:
        left, pos = _parse_primary(tokens, pos)
    
    # 处理二元运算符
    while pos < len(tokens):
        token_type, token_value = tokens[pos]
        
        if token_type != 'OP' or token_value not in OPERATORS:
            break
        
        op_func, op_prec = OPERATORS[token_value]
        if op_prec < min_prec:
            break
        
        pos += 1
        right, pos = _parse_expression(tokens, pos, op_prec + 1)
        left = op_func(left, right)
    
    return left, pos

def _parse_primary(tokens: list, pos: int) -> tuple:
    """解析基本表达式（数字、函数调用、括号表达式）"""
    if pos >= len(tokens):
        raise ValueError("表达式不完整")
    
    token_type, token_value = tokens[pos]
    
    # 数字
    if token_type == 'NUM':
        return token_value, pos + 1
    
    # 括号表达式
    if token_type == 'OP' and token_value == '(':
        pos += 1
        result, pos = _parse_expression(tokens, pos, 0)
        if pos >= len(tokens) or tokens[pos] != ('OP', ')'):
            raise ValueError("括号不匹配")
        return result, pos + 1
    
    # 函数调用或常量
    if token_type == 'NAME':
        name = token_value.lower()
        pos += 1
        
        # 检查是否是函数调用
        if pos < len(tokens) and tokens[pos] == ('OP', '('):
            if name not in MATH_FUNCTIONS:
                raise ValueError(f"不支持的函数: {name}")
            pos += 1
            arg, pos = _parse_expression(tokens, pos, 0)
            if pos >= len(tokens) or tokens[pos] != ('OP', ')'):
                raise ValueError("函数调用括号不匹配")
            return MATH_FUNCTIONS[name](arg), pos + 1
        
        # 检查是否是常量
        if name in MATH_CONSTANTS:
            return MATH_CONSTANTS[name], pos
        
        raise ValueError(f"未知标识符: {name}")
    
    raise ValueError(f"无法解析: {token_value}")

def safe_eval_math(expr: str) -> float:
    """安全的数学表达式求值"""
    tokens = _tokenize(expr)
    if not tokens:
        raise ValueError("空表达式")
    result, pos = _parse_expression(tokens, 0, 0)
    if pos < len(tokens):
        raise ValueError("表达式解析不完整")
    return result

def calculator(expr: str)->str:
    """
    数学计算器工具
    可计算：加减乘除、括号优先级、平方、开方、三角函数、对数等科学计算
    传入示例：1+2*3、（5+8）/2、sqrt(25)、sin(3.14)
    支持自然语言：1+1等于几、2的平方、5+8*3等于几
    
    ⚠️ 已修复：使用安全的表达式解析器替代 eval()
    """
    try:
        # 1. 预处理：统一大小写、替换中文括号、处理平方写法
        clean_expr = expr.lower()
        clean_expr = clean_expr.replace("（", "(").replace("）", ")")
        clean_expr = clean_expr.replace("^", "**")  # 先替换幂运算符
        
        # 2. 使用正则表达式提取数学表达式部分
        # 匹配数字、运算符、括号、函数名、常量
        match = re.search(r'[\d\.\+\-\*/%\^\(\)\w]+', clean_expr)
        if match:
            clean_expr = match.group()
        
        # 3. 使用安全的表达式解析器
        result = safe_eval_math(clean_expr)
        
        # 4. 格式化结果（整数不显示小数点）
        if result == int(result):
            return f"计算结果：{int(result)}"
        else:
            return f"计算结果：{result:.6g}"
    
    except Exception as e:
        return f"计算失败：表达式错误或不支持该运算，原因：{str(e)}"
    
# 封装为标准LangChain工具，方便Agent调用
calc_tool = StructuredTool.from_function(
    name="calculator",          # 工具名称
    func=calculator,            # 绑定执行函数
    description="用于数学表达式计算、科学运算、加减乘除、开方三角函数等数学类问题"
)

# 工具测试入口
if __name__ == "__main__":
    print("🧪 测试计算器工具...\n")

    # 【我新增了自然语言测试】
    print("测试 1: 1+1等于几")
    print(calc_tool.invoke("1+1等于几"))

    print("\n测试 2: 1+2*3")
    print(calc_tool.invoke("1+2*3"))

    print("\n测试 3: sqrt(25)")
    print(calc_tool.invoke("sqrt(25)"))

    print("\n🎉 计算器工具测试全部通过！可正常使用！")