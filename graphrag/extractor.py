from .config import llm

def extract_entity_relation(text: str) -> str:
    """
    从文本中抽取实体-关系-实体三元组，并附带置信度。
    输出格式：实体1|关系|实体2|置信度
    """
    prompt = f"""
你是知识图谱实体关系抽取专家。
从下面文本中抽取所有【实体1、关系、实体2】，并给出0~1的置信度。
严格按每行一条输出，格式固定：
实体1|关系|实体2|0.85
不要多余解释、不要多余文字、不要编号。

文本内容：
{text}
"""
    response = llm.invoke(prompt)
    return response.content.strip()