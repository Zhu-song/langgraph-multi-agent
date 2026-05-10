from langchain_core.tools import StructuredTool
from reflection.reflection_core import reflect_answer

def reflection_self_check(question: str, raw_answer: str) -> str:
    """
    自省纠错工具 Reflection
    对已有答案做自我评审、漏洞检查、逻辑纠错、润色优化
    """
    return reflect_answer(question, raw_answer)

reflection_tool = StructuredTool.from_function(
    name="reflection_self_check",
    func=reflection_self_check,
    description="自省纠错：对回答做逻辑校验、事实自查、错误修正、内容润色优化"
)