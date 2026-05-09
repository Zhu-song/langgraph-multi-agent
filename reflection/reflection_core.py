from config import llm

def reflect_answer(question: str, raw_answer: str) -> str:
    """
    Reflection 自省纠错
    1. 对初始答案做自我审查：事实、逻辑、完整性、格式、是否编造
    2. 发现问题自动迭代重写
    3. 无问题则直接输出优化后标准答案
    """

    # 第一步：自省评审
    review_prompt = f"""
你是严格的答案评审专家，请对下面【问题+初始回答】做全面自省检查，逐条评审：
1. 回答是否偏离问题
2. 是否存在事实错误、逻辑漏洞
3. 是否有编造幻觉、无依据内容
4. 回答是否完整、条理是否清晰
5. 格式是否工整易读

只输出评审结论：存在问题 / 无问题，不需要多余解释。

用户问题：{question}
初始回答：{raw_answer}
"""
    review_res = llm.invoke(review_prompt).content.strip()

    # 第二步：有问题 → 重写优化
    if "存在问题" in review_res:
        rewrite_prompt = f"""
请根据评审自查，重新严谨回答用户问题，修正逻辑错误、补全遗漏、去除编造内容，条理清晰、精简准确。
用户问题：{question}
旧回答：{raw_answer}
"""
        final_ans = llm.invoke(rewrite_prompt).content.strip()
        return f"【自省检测：发现问题已自动修正】\n{final_ans}"

    # 无问题 → 直接优化润色输出
    else:
        polish_prompt = f"""
请把下面回答精简润色、条理优化，保持原意不变，输出更工整易读的版本。
回答内容：{raw_answer}
"""
        polish_ans = llm.invoke(polish_prompt).content.strip()
        return f"【自省检测：内容无误】\n{polish_ans}"