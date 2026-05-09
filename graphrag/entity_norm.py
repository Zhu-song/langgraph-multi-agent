# 可扩展的同义词映射表
# 作用：把不同叫法、英文、缩写统一成一个标准实体名，避免知识图谱重复建节点
SYNONYM_MAP = {
    "大语言模型": "大模型",         # 全称 → 简称
    "LLM": "大模型",               # 英文缩写 → 中文标准名
    "large language model": "大模型", # 英文全称 → 中文标准名
    "检索增强生成": "RAG",          # 中文 → 缩写
    "知识图谱": "KG",              # 中文 → 缩写
    "图谱": "KG",                  # 简称 → 标准缩写
    "人工智能": "AI",              # 中文 → 英文缩写
}

def normalize_entity(entity: str) -> str:
    """对实体进行标准化，合并同义词"""
    # 如果传入的实体为空，直接返回原内容（防止报错）
    if not entity:
        return entity
    
    # 去掉实体字符串前后的空格、换行等空白字符
    entity = entity.strip()
    
    # 从同义词表中查找标准名称
    # 找到 → 返回标准值；没找到 → 返回原实体（不修改）
    return SYNONYM_MAP.get(entity, entity)