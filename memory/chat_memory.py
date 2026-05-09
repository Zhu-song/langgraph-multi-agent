from typing import List, Dict

class ChatMemory:
    """
    多轮对话记忆管理器
    功能：保存历史聊天记录 + 自动限制最大轮数（防止上下文过长）
    插拔式设计，不影响原有 Agent / 工具 / 调度逻辑
    """
    # ===================== 核心配置：设置保留多少轮对话 =====================
    # 数字自己改：3 = 保留最近3轮   5 = 保留5轮   10 = 保留10轮
    # 一轮 = 1句用户问题 + 1句助手回答
    MAX_HISTORY_ROUND = 3
    # =====================================================================

    def __init__(self):
        # 初始化空列表，用于存储对话历史
        # 格式：[{"role":"user", "content":"xxx"}, {"role":"assistant", "content":"yyy"}]
        self.history: List[Dict[str, str]] = []

    def add_user_msg(self, content: str) -> None:
        """添加用户消息到记忆库"""
        self.history.append({"role": "user", "content": content})
        # 添加后自动裁剪，保证不超过最大轮数
        self._trim_history()

    def add_ai_msg(self, content: str) -> None:
        """添加AI助手消息到记忆库"""
        self.history.append({"role": "assistant", "content": content})
        # 添加后自动裁剪，保证不超过最大轮数
        self._trim_history()

    def _trim_history(self):
        """
        【内部工具方法】
        自动裁剪对话历史，只保留最近 N 轮
        一轮对话 = 1条用户消息 + 1条AI消息 → 共2条
        """
        # 最大存储条数 = 轮数 × 2
        max_length = self.MAX_HISTORY_ROUND * 2
        
        # 如果超过最大长度，只保留最后 max_length 条记录
        if len(self.history) > max_length:
            self.history = self.history[-max_length:]

    def get_history_str(self) -> str:
        """
        获取拼接好的对话历史字符串
        用于传给大模型，实现上下文理解
        """
        # 如果没有历史，返回空字符串
        if not self.history:
            return ""
        
        # 拼接成可读的对话格式
        history_text = []
        for msg in self.history:
            role = "用户" if msg["role"] == "user" else "助手"
            history_text.append(f"{role}：{msg['content']}")
        
        # 用换行符连接所有历史
        return "\n".join(history_text)

    def clear(self) -> None:
        """清空所有对话记忆（用户输入 clear 时调用）"""
        self.history.clear()