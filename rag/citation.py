def format_citation(results):
    """从检索结果提取来源，生成标准引用文案（文档名 + 片段 + 得分）"""
    # 如果没有检索结果，直接返回空字符串
    if not results:
        return ""
    
    # 用集合存储来源，自动去重（避免重复显示同一个文件）
    sources = set()
    citation_lines = []

    # 遍历每一条检索结果
    for idx, item in enumerate(results, 1):
        # 基础信息
        content = item.get("page_content", "").strip()
        meta = item.get("metadata", {})
        source = meta.get("source", "未知文档")
        score = item.get("score", 0.0)

        # 来源去重
        sources.add(source)

        # 截取片段（避免太长）
        snippet = content[:120] + "..." if len(content) > 120 else content

        # 构建单条引用
        citation_lines.append(
            f"{idx}. 📄 {source} | 匹配度：{score:.2f}\n"
            f"   片段：{snippet}"
        )

    # 如果没有找到任何来源信息
    if not sources:
        return "\n\n📌 来源：无匹配文档"
    
    # 拼接最终格式
    final = "\n\n" + "="*40 + "\n"
    final += "📚 来源引用（可溯源）\n"
    final += "="*40 + "\n"
    final += "\n".join(citation_lines)
    final += f"\n\n📌 参考文档：{', '.join(sources)}"

    return final