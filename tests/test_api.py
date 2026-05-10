"""
API 端点测试
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHealthEndpoints:
    """健康检查端点测试类"""

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")

        assert response.status_code == 200

    def test_ready_endpoint(self, client):
        """测试就绪检查端点"""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "checks" in data


class TestAuthEndpoints:
    """认证端点测试类"""

    def test_register_password_too_short(self, client):
        """测试注册密码过短"""
        response = client.post(
            "/api/auth/register",
            json={"name": "testuser_shortpwd", "password": "12345"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_register_success(self, client):
        """测试注册成功"""
        import uuid
        unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/auth/register",
            json={"name": unique_name, "password": "test123456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_login_user_not_found(self, client):
        """测试登录用户不存在"""
        response = client.post(
            "/api/auth/login",
            json={"name": "nonexistent_user_xyz", "password": "test123456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 404


class TestKnowledgeEndpoints:
    """知识库端点测试类"""

    def test_knowledge_status(self, client):
        """测试知识库状态端点"""
        response = client.get("/api/knowledge/status")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
