"""
计算器工具测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCalculator:
    """计算器工具测试类"""

    def test_basic_addition(self):
        """测试基本加法"""
        from tools.calc_tool import calc_tool

        result = calc_tool.invoke("2 + 3")
        assert "5" in result

    def test_basic_subtraction(self):
        """测试基本减法"""
        from tools.calc_tool import calc_tool

        result = calc_tool.invoke("10 - 4")
        assert "6" in result

    def test_basic_multiplication(self):
        """测试基本乘法"""
        from tools.calc_tool import calc_tool

        result = calc_tool.invoke("3 * 4")
        assert "12" in result

    def test_basic_division(self):
        """测试基本除法"""
        from tools.calc_tool import calc_tool

        result = calc_tool.invoke("20 / 4")
        assert "5" in result

    def test_complex_expression(self):
        """测试复杂表达式"""
        from tools.calc_tool import calc_tool

        result = calc_tool.invoke("(2 + 3) * 4")
        assert "20" in result

    def test_division_by_zero(self):
        """测试除以零"""
        from tools.calc_tool import calc_tool

        result = calc_tool.invoke("1 / 0")
        # 应该返回错误信息而不是崩溃
        assert result is not None
