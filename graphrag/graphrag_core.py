# 操作系统库，用于文件/目录操作
import os
import re

# 文档加载器：读取 TXT / Markdown / PDF 文档
from langchain_community.document_loaders import TextLoader, PyPDFLoader

# 文本分割器：将长文档切分成小片段，便于抽取实体关系
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Neo4j 图数据库官方驱动
from neo4j import GraphDatabase

# 从项目配置导入：大模型实例 + Neo4j 连接信息（统一配置，无硬编码）
from config import llm, NEO4J_URI, NEO4J_USER, NEO4J_PWD

# ====================== ⚠️ Cypher 安全检查 ======================
DANGEROUS_KEYWORDS = [
    'DELETE', 'DETACH', 'DROP', 'CREATE', 'SET', 'MERGE',
    'REMOVE', 'CALL', 'LOAD', 'FOREACH', 'UNWIND',
]

def _is_cypher_safe(cypher: str) -> tuple[bool, str]:
    """检查 Cypher 语句是否安全"""
    cypher_upper = cypher.upper()
    for keyword in DANGEROUS_KEYWORDS:
        if re.search(r'\b' + keyword + r'\b', cypher_upper):
            return False, f"❌ 安全限制：Cypher 语句包含禁止的关键字 [{keyword}]"
    return True, ""

# ========== 全局配置 ==========
# 本地知识库文档存放目录
DOC_DIR = "./rag/docs"
# 文本分块大小（每块最大长度）
CHUNK_SIZE = 600
# 文本块之间的重叠长度（保证上下文连贯性）
CHUNK_OVERLAP = 80

# 初始化 Neo4j 数据库驱动（建立连接）
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))

# 初始化文本分割器
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)

def clear_graph():
    """清空整个知识图谱"""
    # 创建数据库会话
    with driver.session() as session:
        # 执行 Cypher 语句：删除所有节点和关系（清空数据库）
        session.run("MATCH (n) DETACH DELETE n")

def extract_entity_relation(text: str):
    """大模型抽取实体-关系-实体"""
    # 提示词：要求 LLM 按固定格式抽取「实体1|关系|实体2」
    prompt = f"""
你是知识图谱实体关系抽取专家。
从下面文本中抽取所有【实体1、关系、实体2】，严格按每行一条输出，格式固定：
实体1|关系|实体2
不要多余解释、不要多余文字、不要编号。

文本内容：
{text}
"""
    # 调用大模型生成抽取结果
    res = llm.invoke(prompt)
    # 返回清理后的结果
    return res.content.strip()

def create_relation(tx, e1, rel, e2):
    """创建实体与关系到图谱"""
    # Cypher 语句（MERGE = 不存在则创建，存在则跳过，避免重复）
    cypher = """
    MERGE (a:Entity{name:$e1})
    MERGE (b:Entity{name:$e2})
    MERGE (a)-[:REL{name:$rel}]->(b)
    """
    # 执行语句，传入参数
    tx.run(cypher, e1=e1, rel=rel, e2=e2)

def build_graph_from_docs():
    """从文档自动构建知识图谱（全量构建，每次清空重建）"""
    # 检查文档目录是否存在
    if not os.path.exists(DOC_DIR):
        return "⚠️ 文档目录不存在"

    # 获取目录下所有文件
    files = os.listdir(DOC_DIR)
    if not files:
        return "⚠️ rag/docs 暂无文档"

    # 构建前先清空图谱
    clear_graph()
    # 统计插入的关系总数
    all_nodes = 0

    # 遍历所有文档
    for file in files:
        file_path = os.path.join(DOC_DIR, file)
        try:
            # 根据文件类型选择加载器
            if file.endswith(".txt") or file.endswith(".md"):
                loader = TextLoader(file_path, encoding="utf-8")
            elif file.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            else:
                # 不支持的文件格式直接跳过
                continue

            # 加载文档内容
            docs = loader.load()
            # 切分文档为小文本块
            split_docs = text_splitter.split_documents(docs)

            # 遍历每个文本块，抽取实体关系
            for doc in split_docs:
                content = doc.page_content
                # 调用 LLM 抽取三元组
                raw = extract_entity_relation(content)
                if not raw:
                    continue

                # 按行分割结果（每行 = 一个三元组）
                lines = raw.splitlines()
                with driver.session() as session:
                    for line in lines:
                        line = line.strip()
                        # 格式校验
                        if "|" not in line:
                            continue

                        parts = line.split("|")
                        if len(parts) != 3:
                            continue

                        # 解析实体1、关系、实体2
                        e1, rel, e2 = parts
                        # 写入知识图谱
                        session.write_transaction(create_relation, e1.strip(), rel.strip(), e2.strip())
                        all_nodes += 1

        # 单个文件异常不影响整体流程
        except Exception as e:
            print(f"处理{file}失败：{e}")

    # 返回构建结果
    return f"✅ 知识图谱构建完成，共抽取关系 {all_nodes} 条"

def graph_qa(question: str) -> str:
    """知识图谱智能问答（NL → Cypher → 结果返回）
    
    ⚠️ 已修复：添加 Cypher 注入防护，使用只读事务
    """
    # 提示词：让 LLM 生成合法的 Cypher 查询语句
    prompt = f"""
你是Neo4j Cypher查询专家。
已知图谱只有一种标签Entity，关系统一为REL。
根据用户问题，生成一条简洁合法的Cypher语句，只输出Cypher，不要解释。
注意：只能使用 MATCH 和 RETURN 语句进行查询，不能使用 DELETE、CREATE、SET 等修改操作。

用户问题：{question}
"""
    # 生成 Cypher
    cypher = llm.invoke(prompt).content.strip()

    # ====================== 安全检查：Cypher 注入防护 ======================
    is_safe, err_msg = _is_cypher_safe(cypher)
    if not is_safe:
        return err_msg

    try:
        # 执行查询（使用只读事务）
        with driver.session() as session:
            result = session.read_transaction(lambda tx: tx.run(cypher))
            # 转为字典格式
            records = [dict(r) for r in result]

        # 无结果返回提示
        if not records:
            return "⚠️ 知识图谱中未查到相关关联信息"

        # 返回查询结果
        return str(records)

    # 异常处理（Cypher 语法错误/连接失败）
    except Exception as e:
        return f"⚠️ 图谱查询异常：{str(e)}"