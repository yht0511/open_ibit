"""
agent.py - 智能体广场 DeepSeek-R1 模型接口封装

本模块封装了北理工智能体广场（agent.bit.edu.cn）的 DeepSeek-R1 模型 API。
主要功能：
1. 通过应用密钥和访客密钥进行身份验证
2. 支持流式和非流式对话
3. 自动会话管理（创建和删除对话）
4. 支持思维链（reasoning_content）输出

与 ibit.py 的区别：
- 不需要统一身份认证，使用应用密钥认证
- API 端点不同（agent.bit.edu.cn vs ibit.yanhekt.cn）
- 思维链标签格式不同（think_message 事件 vs <think> 标签）

使用方式：
    agent = Agent(appkey, visitor_key)
    agent.init()  # 必须先初始化
    reasoning, content = agent.chat("你好")  # 非流式对话
    for chunk in agent.chat_stream("你好"):  # 流式对话
        print(chunk)
"""

import json  # JSON 数据解析
import time  # 时间处理（保留供将来使用）
import requests  # HTTP 请求库


class Agent:
    """
    智能体广场模型封装类
    
    封装了智能体广场的 DeepSeek-R1 模型 API，提供统一的对话接口。
    支持流式和非流式两种调用方式，自动管理会话。
    
    Attributes:
        appkey: 应用密钥（从智能体广场获取）
        visitor_key: 访客密钥（从智能体广场获取）
        url: API 请求 URL
        cookies: 请求 Cookie
        timeout_seconds: 请求超时时间（秒）
        headers: HTTP 请求头
    """
    
    def __init__(self, appkey, visitor_key, timeout_seconds=10):
        """
        初始化智能体广场模型实例
        
        Args:
            appkey: 应用密钥，从智能体广场获取
            visitor_key: 访客密钥，从智能体广场获取
            timeout_seconds: HTTP 请求超时时间，默认 10 秒
        """
        self.appkey = appkey
        self.visitor_key = visitor_key
        self.url = f"https://agent.bit.edu.cn/product/llm/chat/{appkey}"  # 应用专属 URL
        self.cookies = {
            'app-visitor-key': visitor_key,  # 访客身份标识
        }
        self.timeout_seconds = timeout_seconds

        # 构造请求头，模拟浏览器访问
        self.headers = {
            'Accept': 'application/json, text/event-stream',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json; charset=utf-8',
            'Origin': 'https://agent.bit.edu.cn',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
            'X-KL-Ajax-Request': 'Ajax_Request',
            'accept-language': 'zh',
            'app-visitor-key': 'd104cralaa6c73dtnoi0',  # 默认访客密钥
            'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
    
    def init(self):
        """
        初始化模型（必须在使用前调用）
        
        清除所有已存在的对话，确保干净的初始状态。
        """
        self.clear_conversations()  # 清除所有对话
    
    def chat(self, query, history=[]):
        """
        非流式对话
        
        发送查询并等待完整响应返回。
        
        Args:
            query: 用户查询内容
            history: 历史对话列表，格式为 [{"role": "user", "content": "..."}, ...]
            
        Returns:
            tuple: (reasoning, result)
                - reasoning: 模型的思考过程
                - result: 最终回复内容
        """
        result = ""
        reasoning = ""
        # 通过流式接口收集完整响应
        for chunk in self.chat_stream(query, history):
            if chunk.get("content"):
                result += chunk["content"]
            if chunk.get("reasoning_content"):
                reasoning += chunk["reasoning_content"]
        return reasoning, result
    
    def chat_stream(self, query, history=[]):
        """
        流式对话（生成器）
        
        发送查询并以流式方式逐步返回响应。
        自动管理临时对话的创建和删除。
        
        Args:
            query: 用户查询内容
            history: 历史对话列表
            
        Yields:
            dict: 包含增量内容的字典
                - content: 普通回复内容（可能为 None）
                - reasoning_content: 思考过程内容（可能为 None）
        """
        url = "https://agent.bit.edu.cn/api/proxy/chat/v2/chat_query"  # 对话 API
        temp_dialogue_id = self.new_dialogue()  # 创建临时对话
        query = self.get_history_prompt(history) + query  # 将历史对话拼接到查询中
        
        # 构造请求数据
        json_data = {
            'Query': query,
            'AppConversationID': temp_dialogue_id,
            'AppKey': self.appkey,
            'QueryExtends': {
                'Files': [],  # 附件文件（暂不支持）
            }
        }
        
        # 发送流式请求
        response = requests.post(url, json=json_data, cookies=self.cookies, headers=self.headers, stream=True)
        response.raw.decode_content = True
        answer = ""
        
        # 提前删除对话（避免对话累积）
        self.delete_dialogue(temp_dialogue_id)
        
        # 逐块处理响应
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    # 解析 SSE 数据格式
                    data = json.loads(chunk.decode("utf-8").split("data: ")[1].replace("\n",""))
                    
                    # 根据事件类型区分思考内容和回复内容
                    if data["event"] == "think_message" and data["answer"]:
                        # 思考过程事件
                        answer = data["answer"]
                        yield {
                            "content": None,
                            "reasoning_content": answer
                        }
                    elif data["event"] == "message" and data["answer"]:
                        # 普通回复事件
                        answer = data["answer"]
                        yield {
                            "content": answer,
                            "reasoning_content": None
                        }
                except: pass  # 忽略解析错误

    def get_history_prompt(self, history):
        """
        构造历史对话提示
        
        将历史对话格式化为提示文本，供模型参考。
        
        Args:
            history: 历史对话列表
            
        Returns:
            str: 格式化后的历史对话提示文本
        """
        res = "[历史对话](请注意这是由程序提供的历史对话功能,不要把它当成用户对话的一部分,不要刻意提及它):"
        for i in history:
            res += f"\n{i['role']}:{i['content']}"
        res += "\n接下来是用户的新一轮问题:\n"
        return res
        
    def new_dialogue(self):
        """
        创建新对话
        
        在智能体广场创建一个新的对话会话。
        
        Returns:
            str: 新创建的对话 ID（AppConversationID）
        """
        url = "https://agent.bit.edu.cn/api/proxy/chat/v2/create_conversation"
        json_data = {
            'AppKey': self.appkey,
            'Inputs': {},  # 初始输入参数（可扩展）
        }
        response = requests.post(
            url,
            json=json_data,
            cookies=self.cookies, 
            headers=self.headers
        )
        return response.json().get("Conversation").get("AppConversationID")

    def delete_dialogue(self, dialogue_id):
        """
        删除对话
        
        删除指定的对话会话，用于清理临时对话。
        
        Args:
            dialogue_id: 要删除的对话 ID
            
        Returns:
            bool: 总是返回 True
        """
        url = 'https://agent.bit.edu.cn/api/proxy/chat/v2/delete_conversation'
        json_data = {
            'AppKey': self.appkey,
            'AppConversationID': dialogue_id,
        }

        response = requests.post(
            url,
            json=json_data,
            cookies=self.cookies, 
            headers=self.headers
        )
        return True

    def get_conversation_list(self):
        """
        获取对话列表
        
        获取当前应用下的所有对话会话。
        
        Returns:
            list: 对话列表，每个元素包含对话的详细信息
        """
        url = 'https://agent.bit.edu.cn/api/proxy/chat/v2/get_conversation_list'
        json_data = {
            'AppKey': self.appkey,
        }
        response = requests.post(
            url,
            json=json_data,
            cookies=self.cookies, 
            headers=self.headers
        )
        return response.json().get("ConversationList",[])
    
    def clear_conversations(self):
        """
        清除所有对话
        
        删除当前应用下的所有对话会话。
        用于初始化时清理环境。
        
        Returns:
            bool: 总是返回 True
        """
        conversations = self.get_conversation_list()
        for conversation in self.get_conversation_list():
            dialogue_id = conversation.get("AppConversationID")
            if dialogue_id:
                self.delete_dialogue(dialogue_id)
        return True

