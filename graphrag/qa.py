# 导入配置好的大模型 llm
from .settings import llm
# 导入 Neo4j 数据库驱动
from .neo4j_client import get_driver

# ====================== ⚠️ Cypher 安全检查 ======================
# 禁止的危险关键字列表（防止注入攻击）
DANGEROUS_KEYWORDS = [
    'DELETE', 'DETACH', 'DROP', 'CREATE', 'SET', 'MERGE',
    'REMOVE', 'CALL', 'LOAD', 'FOREACH', 'UNWIND',
]

def _is_cypher_safe(cypher: str) -> tuple[bool, str]:
    """
    检查 Cypher 语句是否安全
    返回: (是否安全, 错误信息)
    """
    cypher_upper = cypher.upper()
    
    # 检查危险关键字
    for keyword in DANGEROUS_KEYWORDS:
        # 使用单词边界匹配，避免误判（如 "DETACH DELETE" 中的 DELETE）
        import re
        if re.search(r'\b' + keyword + r'\b', cypher_upper):
            return False, f"❌ 安全限制：Cypher 语句包含禁止的关键字 [{keyword}]，仅允许查询操作"
    
    return True, ""

def _clean_cypher(raw: str) -> str:
    """清理 LLM 生成的 Cypher 语句，移除 markdown 代码块标记等多余内容"""
    import re
    text = raw.strip()
    # 移除 markdown 代码块标记：```cypher ... ``` 或 ``` ... ```
    text = re.sub(r'^```\s*(?:cypher|neo4j)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    text = text.strip()
    # 移除开头的语言标识（如 "cypher\n" 或 "Cypher:"）
    text = re.sub(r'^(?:cypher|Cypher|CYPHER)\s*[:：]?\s*\n?', '', text)
    text = text.strip()
    # 只取有效语句（跳过空行和注释）
    lines = [line.strip() for line in text.split('\n') if line.strip() and not line.strip().startswith('//')]
    if lines:
        # 找到以 MATCH、OPTIONAL MATCH、WITH 开头的行作为起始
        for i, line in enumerate(lines):
            if re.match(r'^(MATCH|OPTIONAL\s+MATCH|WITH|RETURN)', line, re.IGNORECASE):
                return '\n'.join(lines[i:])
    return text

def graph_qa(question: str) -> str:
    """基于知识图谱问答，并自动附加来源引用
    
    ⚠️ 已修复：添加 Cypher 注入防护，使用只读事务
    """
    # 检查 Neo4j 是否配置
    d = get_driver()
    if d is None:
        return "⚠️ Neo4j 未配置，知识图谱功能不可用"
    
    # 构造提示词，让 LLM 生成 Cypher 查询语句
    prompt = f"""
你是Neo4j Cypher查询专家。
已知图谱节点标签为Entity，关系类型为REL（包含source字段）。
根据用户问题，生成一条简洁合法的Cypher语句，只输出Cypher，不要解释。
注意：只能使用 MATCH 和 RETURN 语句进行查询，不能使用 DELETE、CREATE、SET 等修改操作。

用户问题：{question}
"""
    # 调用大模型，生成 Cypher 查询语句
    raw_cypher = llm.invoke(prompt).content.strip()
    # 清理 LLM 输出中的 markdown 代码块标记等多余内容
    cypher = _clean_cypher(raw_cypher)

    # ====================== 安全检查：Cypher 注入防护 ======================
    is_safe, err_msg = _is_cypher_safe(cypher)
    if not is_safe:
        return err_msg

    try:
        # 打开 Neo4j 会话
        with d.session() as session:
            # 在事务内部消费 Result，避免事务关闭后无法读取
            records = session.read_transaction(lambda tx: tx.run(cypher).data())

        # 如果没有查询到数据
        if not records:
            return "⚠️ 知识图谱中未查到相关关联信息"

        # ======================
        # ✅ 这里开始修复（正确版）
        # ======================
        content_lines = []
        sources = set()

        for rec in records:
            entities = []
            rel_name = ""
            src = "未知文档"

            for k, v in rec.items():
                if isinstance(v, dict):
                    if "name" in v:
                        entities.append(v["name"])
                    if "source" in v:
                        src = v["source"]
                elif k == "name":
                    rel_name = v

            if len(entities) >= 2 and rel_name:
                line = f"{entities[0]} 【{rel_name}】 {entities[1]}"
                content_lines.append(line)
                sources.add(src)

        answer = "📊 知识图谱关联信息：\n" + "\n".join(content_lines)

        # 拼接来源引用
        if sources:
            answer += f"\n\n📌 图谱来源文档：{', '.join(sources)}"
        else:
            answer += "\n\n📌 图谱来源文档：无"

        # 返回最终答案 + 来源
        return answer

    # 异常处理：Cypher 语法错误 / 数据库连接失败
    except Exception as e:
        return f"⚠️ 图谱查询异常：{str(e)}"
