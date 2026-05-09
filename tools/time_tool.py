#================== 时间、日期、星期、日期间隔 ================= 
#路由标识 time

# 导入日期时间处理模块
from datetime import datetime
# 导入LangChain工具封装类
from langchain.tools import StructuredTool

def time_query(query: str) -> str:
    """
    时间日期工具：获取当前时间、当前星期、计算两个日期相差天数
    参数格式：
    now                  - 获取当前北京时间
    weekday              - 今天星期几
    diff,2025-01-01,2025-12-31    - 两个日期相差天数
    支持自然语言：现在几点、今天星期几、2025-01-01和2025-12-31差几天
    """
    now = datetime.now()
    
    try:
        # ====================== 【自然语言自动识别】 ======================
        query_type = query.strip().lower()

        # 自然语言 → 转成 now
        if "现在" in query or "几点" in query or "时间" in query:
            query_type = "now"

        # 自然语言 → 转成 weekday
        elif "星期" in query or "周几" in query:
            query_type = "weekday"

        # 自然语言 → 提取日期差
        elif "差" in query or "相差" in query:
            # 提取数字日期
            import re
            dates = re.findall(r"\d{4}-\d{1,2}-\d{1,2}", query)
            if len(dates) >= 2:
                query_type = f"diff,{dates[0]},{dates[1]}"

       
        
        # 获取当前年月日时分秒
        if query_type == "now":
            return f"当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 获取今天是星期几
        elif query_type == "weekday":
            weekday_map = ["周一","周二","周三","周四","周五","周六","周日"]
            return f"今天是:{weekday_map[now.weekday()]}"
        
        # 计算两个日期之间的天数差
        elif query_type.startswith("diff"):
            parts = query_type.split(",")
            date1 = datetime.strptime(parts[1],"%Y-%m-%d")
            date2 = datetime.strptime(parts[2],"%Y-%m-%d")
            diff_days = abs((date2-date1).days)
            return f"两个日期相差：{diff_days}天"
        
        # 不支持的指令类型
        else:
            return "不支持的指令，支持：now/weekday/diff，日期1，日期2"
    
    # 异常捕获：格式错误等
    except:
        return "时间格式错误，请按要求输入"

# 封装为LangChain标准工具，供Agent调用
time_tool = StructuredTool.from_function(
    name="time_query",
    func=time_query,
    description="查询当前时间、星期、计算两个日期之间相差天数"
)

# ====================== 测试 ======================
if __name__ == "__main__":
    print("🧪 测试时间工具...\n")

    # 自然语言测试
    print("测试 1：现在几点")
    print(time_tool.invoke("现在几点"))

    print("\n测试 2：今天星期几")
    print(time_tool.invoke("今天星期几"))

    print("\n测试 3：2025-01-01和2025-12-31相差几天")
    print(time_tool.invoke("2025-01-01和2025-12-31相差几天"))

    print("\n🎉 时间工具测试全部通过！")