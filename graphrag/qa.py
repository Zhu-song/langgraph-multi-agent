# 导入配置好的大模型 llm
from .config import llm
# 导入 Neo4j 数据库驱动
from .neo4j_client import driver

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

def graph_qa(question: str) -> str:
    """基于知识图谱问答，并自动附加来源引用
    
    ⚠️ 已修复：添加 Cypher 注入防护，使用只读事务
    """
    # 构造提示词，让 LLM 生成 Cypher 查询语句
    prompt = f"""
你是Neo4j Cypher查询专家。
已知图谱节点标签为Entity，关系类型为REL（包含source字段）。
根据用户问题，生成一条简洁合法的Cypher语句，只输出Cypher，不要解释。
注意：只能使用 MATCH 和 RETURN 语句进行查询，不能使用 DELETE、CREATE、SET 等修改操作。

用户问题：{question}
"""
    # 调用大模型，生成 Cypher 查询语句
    cypher = llm.invoke(prompt).content.strip()

    # ====================== 安全检查：Cypher 注入防护 ======================
    is_safe, err_msg = _is_cypher_safe(cypher)
    if not is_safe:
        return err_msg

    try:
        # 打开 Neo4j 会话
        with driver.session() as session:
            # ⚠️ 使用只读事务执行查询，防止数据修改
            result = session.read_transaction(lambda tx: tx.run(cypher))
            # 将查询结果转成字典列表
            records = [dict(record) for record in result]

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