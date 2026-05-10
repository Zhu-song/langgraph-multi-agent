# 导入 Neo4j 官方 Python 驱动，用于连接和操作图数据库
from neo4j import GraphDatabase

# 从当前包的 settings 中导入所有配置（NEO4J_URI、账号密码、IS_INCREMENTAL 等）
from .settings import NEO4J_URI, NEO4J_USER, NEO4J_PWD, IS_INCREMENTAL

# ====================== ⚠️ 延迟初始化：Neo4j 驱动管理 ======================
# 改为延迟初始化，避免模块导入时就创建连接
_driver = None

def get_driver():
    """
    获取 Neo4j 驱动实例（延迟初始化）
    只有在真正需要时才创建连接
    如果未配置则返回 None
    """
    global _driver
    if _driver is None:
        if not NEO4J_URI or not NEO4J_URI.strip() or not NEO4J_URI.startswith(('bolt://', 'neo4j://')):
            return None
        if not NEO4J_USER or not NEO4J_PWD:
            return None
        try:
            _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
        except Exception:
            return None
    return _driver

# 为了向后兼容，提供 driver 属性
class _DriverProxy:
    """代理类，延迟获取驱动"""
    def __getattr__(self, name):
        d = get_driver()
        if d is None:
            raise RuntimeError("Neo4j 未配置，无法使用图谱功能")
        return getattr(d, name)
    
    def __bool__(self):
        return get_driver() is not None
    
    def session(self):
        d = get_driver()
        if d is None:
            raise RuntimeError("Neo4j 未配置，无法使用图谱功能")
        return d.session()

driver = _DriverProxy()

# ====================== 基础连接管理 ======================
def close_driver():
    """关闭驱动连接"""
    global _driver
    if _driver is not None:
        try:
            _driver.close()
        except Exception:
            pass  # 忽略关闭时的异常
        _driver = None

# ====================== 图谱清空（全量模式） ======================
def clear_graph():
    """清空整个图谱（仅在非增量模式下执行）"""
    # 检查 Neo4j 是否配置
    d = get_driver()
    if d is None:
        return  # Neo4j 未配置，直接返回
    
    # 判断是否为【非增量模式】，是才清空（全量重建）
    if not IS_INCREMENTAL:
        with d.session() as session:
            # Cypher 语句：删除所有节点和关系（清空数据库）
            session.run("MATCH (n) DETACH DELETE n")

# ====================== 增量更新：检查实体是否存在 ======================
def is_entity_exists(tx, entity: str) -> bool:
    """检查实体是否已存在（用于增量更新）"""
    # Cypher 查询：根据实体名称查找节点
    result = tx.run("MATCH (e:Entity {name: $entity}) RETURN e", entity=entity)
    # 有结果 → 存在（True），无结果 → 不存在（False）
    return result.single() is not None

# ====================== 核心：创建实体与关系（带来源） ======================
def create_relation_with_source(tx, e1: str, rel: str, e2: str, source: str):
    """创建带来源信息的实体关系"""
    # Cypher 语句（MERGE = 不存在则创建，存在则跳过，避免重复）
    cypher = """
    MERGE (a:Entity {name: $e1})
    MERGE (b:Entity {name: $e2})
    MERGE (a)-[r:REL {name: $rel, source: $source}]->(b)
    """
    # 执行 Cypher，传入参数：实体1、关系、实体2、来源文档
    tx.run(cypher, e1=e1, rel=rel, e2=e2, source=source)