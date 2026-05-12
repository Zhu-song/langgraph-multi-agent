# 导入操作系统库，用于文件/目录操作
import os
# 导入文档加载器：加载 TXT/MD/PDF 文档
from langchain_community.document_loaders import TextLoader, PyPDFLoader
# 导入文本分割器：将长文档切分为小片段，便于抽取实体关系
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 从当前包的 settings 导入配置（显式导入，避免命名空间污染）
from .settings import CHUNK_SIZE, CHUNK_OVERLAP, DOC_DIR, IS_INCREMENTAL, ENTITY_SCORE_THRESHOLD
# 导入 Neo4j 客户端：数据库驱动、清空图谱、实体检查、创建关系等方法
from .neo4j_client import get_driver, clear_graph, check_entity_exists, write_relation
# 导入实体关系抽取函数：调用 LLM 从文本抽取「实体1|关系|实体2|置信度」
from .extractor import extract_entity_relation
# 导入实体归一化函数：统一实体名称（如 北京/北京市 → 归一为 北京市）
from .entity_norm import normalize_entity

# 初始化文本分割器（使用配置中的分块大小与重叠长度）
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)

def build_graph_from_docs():
    """从文档构建/增量更新知识图谱"""
    # 检查 Neo4j 是否配置
    d = get_driver()
    if d is None:
        return "⚠️ Neo4j 未配置，无法构建知识图谱"
    
    # 检查文档目录是否存在
    if not os.path.exists(DOC_DIR):
        return "⚠️ 文档目录不存在"

    # 获取文档目录下所有文件
    files = os.listdir(DOC_DIR)
    # 无文件直接返回提示
    if not files:
        return "⚠️ rag/docs 暂无文档"

    # 根据配置决定是否清空图谱（全量/增量模式）
    clear_graph()
    # 统计最终插入的关系条数
    all_nodes = 0

    # 遍历所有文档文件
    for file in files:
        file_path = os.path.join(DOC_DIR, file)
        try:
            # 根据文件类型选择对应的加载器
            if file.endswith((".txt", ".md")):
                loader = TextLoader(file_path, encoding="utf-8")
            elif file.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            else:
                # 非支持格式直接跳过
                continue

            # 加载文档内容
            docs = loader.load()
            # 对文档进行分块处理
            split_docs = text_splitter.split_documents(docs)

            # 遍历每一个文本块
            for doc in split_docs:
                content = doc.page_content
                # 调用 LLM 抽取实体、关系、置信度
                raw_result = extract_entity_relation(content)
                # 抽取结果为空则跳过
                if not raw_result:
                    continue

                # 按行拆分抽取结果（每行格式：实体1|关系|实体2|置信度）
                lines = raw_result.splitlines()
                # 创建 Neo4j 数据库会话
                with d.session() as session:
                    for line in lines:
                        line = line.strip()
                        # 按 | 分割字段
                        parts = line.split("|")
                        # 格式不正确则跳过
                        if len(parts) != 4:
                            continue

                        # 解析实体1、关系、实体2、置信度
                        e1, rel, e2, score_str = parts
                        try:
                            score = float(score_str)
                        except ValueError:
                            # 置信度转数字失败则跳过
                            continue

                        # 1. 置信度过滤：低于阈值的低质量关系直接丢弃
                        if score < ENTITY_SCORE_THRESHOLD:
                            continue

                        # 2. 实体归一化：统一实体名称，避免同义不同名
                        e1_norm = normalize_entity(e1.strip())
                        e2_norm = normalize_entity(e2.strip())

                        # 3. 增量更新模式：两个实体都已存在，则跳过（不重复创建）
                        if IS_INCREMENTAL:
                            if check_entity_exists(session, e1_norm) and check_entity_exists(session, e2_norm):
                                continue

                        # 4. 写入知识图谱：创建实体与关系，并记录来源文档
                        write_relation(session, e1_norm, rel.strip(), e2_norm, source=file)
                        # 统计成功插入的关系数量
                        all_nodes += 1

        # 捕获单个文件处理异常，不影响整体流程
        except Exception as e:
            print(f"处理文件 {file} 失败：{e}")

    # 返回最终执行结果
    return f"✅ 图谱构建/更新完成，共插入 {all_nodes} 条高质量关系"