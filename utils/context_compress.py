# utils/context_compress.py
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate
from config import llm

# 上下文压缩提示词模板
# 作用：让大模型把冗长的历史对话精简为核心总结，不丢失关键信息
COMPRESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", 
     "你是对话上下文压缩助手，请精简总结以下历史对话，保留核心问题、关键信息和业务意图，"
     "删除冗余重复寒暄，尽量简洁，不丢失关键上下文，用于后续AI问答接续。"),
    ("human", "历史对话内容：\n{chat_history}")
])

# 触发压缩的对话轮数阈值
# 超过 6 轮对话，自动触发上下文压缩
COMPRESS_THRESHOLD = 6

def count_chat_rounds(messages: list[BaseMessage]) -> int:
    """统计有效对话轮次（一轮 Human + 一轮 AI 算 1 轮完整对话）"""
    rounds = 0
    # 步长为 2，依次检查人+AI配对
    for i in range(0, len(messages)-1, 2):
        if isinstance(messages[i], HumanMessage) and isinstance(messages[i+1], AIMessage):
            rounds += 1
    return rounds

def compress_chat_history(messages: list[BaseMessage]) -> list[BaseMessage]:
    """
    长对话上下文自动压缩
    逻辑：超过阈值 → 历史对话总结成精简文案，保留最新几轮原始对话
    作用：减少上下文长度，降低token消耗，避免LLM上下文溢出
    """
    # 统计当前对话轮次
    rounds = count_chat_rounds(messages)
    
    # 未达到阈值，直接返回原消息列表
    if rounds < COMPRESS_THRESHOLD:
        return messages
    
    # 保留最新 2 轮原始对话，其余全部压缩总结
    keep_latest = 2
    split_idx = len(messages) - keep_latest * 2
    
    # 边界判断：索引不能小于0
    if split_idx <= 0:
        return messages

    # 拆分：需要总结的历史部分 + 保留的最新对话部分
    history_part = messages[:split_idx]
    latest_part = messages[split_idx:]

    # 把历史消息转成纯文本，用于给LLM总结
    chat_text = ""
    for msg in history_part:
        if isinstance(msg, HumanMessage):
            chat_text += f"用户：{msg.content}\n"
        elif isinstance(msg, AIMessage):
            chat_text += f"AI：{msg.content}\n"

    # 调用LLM生成精简总结
    summary_resp = llm.invoke(COMPRESS_PROMPT.format(chat_history=chat_text))
    summary_content = f"【历史对话精简总结】：{summary_resp.content}"

    # 构造新的上下文：总结消息 + 最新原始对话
    new_messages = [HumanMessage(content=summary_content)]
    new_messages.extend(latest_part)
    
    return new_messages