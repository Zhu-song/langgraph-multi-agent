"""
pytest 配置文件
"""
import sys
import os
import pytest
from fastapi.testclient import TestClient

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def app():
    """返回 FastAPI 应用实例"""
    from main import app
    return app


@pytest.fixture(scope="session")
def client(app):
    """返回测试客户端"""
    return TestClient(app)


@pytest.fixture
def test_user():
    """测试用户信息"""
    return {
        "name": "test_user",
        "password": "test123456"
    }
