# 第1天·Agent 学习知识点总结（极简、可直接背诵） 
## 一、Python 类核心（写 Agent 的基础） 
1. **class 类** 
 - 是创建**智能体/对象的模板** 
	 - 内部包含：属性（变量）+ 方法（函数）
2. **def __init__(self):**
	- **初始化方法**，实例化时**自动第一个执行** 
	- 作用：给对象绑定初始属性（模型、记忆、名字、配置） 
3. **self** 
	- 代表**对象自己** 
	- 类内部要使用自身变量/函数，必须加 `self.` 
	- 例如：`self.history`、`self.llm` 
4. **实例化** 
	- `agent = MemoryChatAgent()` 
	- 用类模板创建一个真实可用的对象
--- 
## 二、带记忆的多轮对话 Agent 
1. **记忆结构** 
	- 用列表保存对话：`self.history = []` 
2. **对话流程** 
	1. 用户提问 
	2. 将用户输入加入 `history` 
	3. 把**全部历史拼接成 prompt** 
	4. 传给 LLM 生成回答 
	5. 将 AI 回答也加入 `history` 
3. **为什么能记住上下文？** 
	- 每一轮都把之前的对话一起发给模型 
	- 模型看到历史，就知道上下文内容 
--- 
## 三、完整 Agent 结构 
```python 
class 智能体类: 
def __init__(self): # 初始化 
self.llm = 大模型 # 大脑 
self.history = [] # 记忆 
def chat(self, user_input): # 对话方法 
self.history.append(用户问题)
prompt = 拼接历史 
ai_reply = self.llm.invoke(prompt) 
self.history.append(AI回答) 
return ai_reply
```
 --- 
 ## 四、**关键词一句话记忆**
 - **class = 模板** 
 - **__init__ = 开机初始化** 
 - **self = 我自己** 
 - **history = 上下文记忆** 
 - **多轮对话 = 每次都把历史拼进去**