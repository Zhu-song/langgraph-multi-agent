"""
密码哈希功能测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 main.py 中的实际函数
from main import hash_password, verify_password


class TestPasswordHash:
    """密码哈希功能测试类 - 测试 main.py 中的实际实现"""

    def test_hash_password_returns_string(self):
        """测试哈希函数返回字符串"""
        password = "test123456"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "test123456"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "test123456"
        wrong_password = "wrongpassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_salts_produce_different_hashes(self):
        """测试不同盐值产生不同哈希"""
        password = "test123456"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        # 但两者都能验证通过
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_verify_password_with_empty_hash(self):
        """测试空哈希验证"""
        password = "test123456"
        assert verify_password(password, "") is False

    def test_verify_password_with_invalid_hash(self):
        """测试无效哈希验证"""
        password = "test123456"
        # 无效的 bcrypt 哈希格式
        assert verify_password(password, "invalid_hash") is False
