"""
ibit.py - iBit 平台 DeepSeek 模型接口封装

本模块封装了北理工 iBit 平台（ibit.yanhekt.cn）的 DeepSeek 模型 API。
主要功能：
1. 使用北理工统一身份认证登录获取凭证
2. 支持流式和非流式对话
3. 自动会话管理（创建和删除对话）
4. 支持思维链（reasoning_content）输出
5. 自动保持登录状态（定期检查连接）

使用方式：
    ibit_model = iBit(username, password)
    ibit_model.init()  # 必须先初始化
    reasoning, content = ibit_model.chat("你好")  # 非流式对话
    for chunk in ibit_model.chat_stream("你好"):  # 流式对话
        print(chunk)
"""

import json  # JSON 数据解析
import uuid  # 生成唯一标识符
import requests  # HTTP 请求库
import auth.login  # 北理工统一身份认证登录模块
import urllib.parse  # URL 编码工具
import time  # 时间处理
import threading  # 多线程支持


class iBit:
    """
    iBit 平台模型封装类
    
    封装了 iBit 平台的 DeepSeek 模型 API，提供统一的对话接口。
    支持流式和非流式两种调用方式，自动管理登录状态和会话。
    
    Attributes:
        username: 北理工统一身份认证用户名
        password: 北理工统一身份认证密码
        url: iBit 平台 API 基础 URL
        timeout_seconds: 请求超时时间（秒）
        cookies: 登录后获取的 Cookie
        badge: 认证徽章（用于 API 鉴权）
        headers: HTTP 请求头
    """
    
    def __init__(self, username, password, timeout_seconds=10):
        """
        初始化 iBit 模型实例
        
        Args:
            username: 北理工统一身份认证用户名
            password: 北理工统一身份认证密码
            timeout_seconds: HTTP 请求超时时间，默认 10 秒
        """
        self.username = username
        self.password = password
        self.url = "https://ibit.yanhekt.cn"  # iBit 平台 API 基础 URL
        self.timeout_seconds = timeout_seconds
    
    def init(self):
        """
        初始化模型（必须在使用前调用）
        
        执行登录操作并启动后台线程定期检查登录状态。
        """
        self.login(self.username, self.password)
        # 启动守护线程，定期检查登录状态
        self.check_login_thread = threading.Thread(target=self.check_login)
        self.check_login_thread.daemon = True
        self.check_login_thread.start()
    
    def login(self, username, password):
        """
        使用统一身份认证登录 iBit 平台
        
        通过 bit_login 库完成北理工统一身份认证，获取访问凭证。
        
        Args:
            username: 统一身份认证用户名
            password: 统一身份认证密码
        """
        self.username = username
        self.password = password
        # 调用统一身份认证登录，获取 Cookie
        self.cookies = auth.login.login(username, password)["cookie_json"]
        self.badge = self.cookies["badge_2"]  # 提取认证徽章
        self.badge_decoded = urllib.parse.quote(self.badge)  # URL 编码
        
        # 构造请求头
        self.headers = {
            "Host": "ibit.yanhekt.cn",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Chromium";v="108"',
            "badge": self.badge_decoded,  # 认证徽章
            "sec-ch-ua-mobile": "?0",
            "Authorization": "Bearer undefined",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.125 Safari/537.36 dingtalk-win/1.0.0 nw(0.14.7) DingTalk(7.6.45-Release.250241020) Mojo/1.0.0 Native AppType(release) Channel/201200 Architecture/x86_64",
            "Content-Type": "application/json",
            "Xdomain-Client": "web_user",
            "x-assistant-id": "43",  # 助手 ID，指定使用 DeepSeek 模型
            "sec-ch-ua-platform": '"Windows"',
            "Accept": "*/ *",
            "Origin": "https://ibit.yanhekt.cn",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": f"badge_2={self.badge}"  # Cookie 认证
        }
    
    def check_login(self):
        """
        定期检查登录状态
        
        每 60 秒创建并删除一个临时对话，以保持连接活跃。
        如果操作失败，会触发重新登录。
        """
        while True:
            temp_dialogue_id=self.new_dialogue()
            self.delete_dialogue(temp_dialogue_id)
            time.sleep(60)
    
    def chat(self, query, history=[], temperature=0.7, top_k=3, score_threshold=0.5, prompt_name="", knowledge_base_name=""):
        """
        非流式对话
        
        发送查询并等待完整响应返回。
        
        Args:
            query: 用户查询内容
            history: 历史对话列表，格式为 [{"role": "user", "content": "..."}, ...]
            temperature: 生成温度，控制输出随机性，默认 0.7
            top_k: 知识库检索返回条数，默认 3
            score_threshold: 知识库检索分数阈值，默认 0.5
            prompt_name: 提示模板名称（可选）
            knowledge_base_name: 知识库名称（可选）
            
        Returns:
            tuple: (reasoning_content, content)
                - reasoning_content: 模型的思考过程
                - content: 最终回复内容
        """
        result = ""
        reasoning = ""
        # 通过流式接口收集完整响应
        for chunk in self.chat_stream(query, history, temperature, top_k, score_threshold, prompt_name, knowledge_base_name):
            if chunk.get("content"):
                result += chunk["content"]
            if chunk.get("reasoning_content"):
                reasoning += chunk["reasoning_content"]
        return reasoning, result
    
    def chat_stream(self, query, history=[], temperature=0.7, top_k=3, score_threshold=0.5, prompt_name="", knowledge_base_name=""):
        """
        流式对话（生成器）
        
        发送查询并以流式方式逐步返回响应。
        自动管理临时对话的创建和删除。
        
        Args:
            query: 用户查询内容
            history: 历史对话列表
            temperature: 生成温度
            top_k: 知识库检索返回条数
            score_threshold: 知识库检索分数阈值
            prompt_name: 提示模板名称（可选）
            knowledge_base_name: 知识库名称（可选）
            
        Yields:
            dict: 包含增量内容的字典
                - content: 普通回复内容（可能为 None）
                - reasoning_content: 思考过程内容（可能为 None）
        """
        url = self.url + "/proxy/v1/chat/stream/private/kb"  # 流式对话 API
        temp_dialogue_id = self.new_dialogue()  # 创建临时对话
        query = self.get_history_prompt(history) + query  # 将历史对话拼接到查询中
        
        # 构造请求数据
        data = {
            "query": query,
            "dialogue_id": temp_dialogue_id,
            "stream": True,
            "history": history,
            "temperature": temperature,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "prompt_name": prompt_name,
            "knowledge_base_name": knowledge_base_name
        }
        
        # 发送流式请求
        response = requests.post(url, headers=self.headers, json=data, stream=True, timeout=self.timeout_seconds)
        response.raw.decode_content = True
        
        res = ""  # 累积响应，用于判断是否在思考阶段
        
        # 逐块处理响应
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    # 解析 SSE 数据格式
                    answer = json.loads(chunk.decode("utf-8").split("data: ")[1].replace("\n",""))["answer"]
                    res += answer
                    
                    # 根据 <think> 标签判断是思考内容还是回复内容
                    if answer not in ["<think>","</think>"]:
                        if "<think>" in res and "</think>" not in res:
                            # 在 <think> 标签内，输出为思考内容
                            yield {
                                "content": None,
                                "reasoning_content": answer
                            }
                        else:
                            # 在 <think> 标签外，输出为普通回复
                            yield {
                                "content": answer,
                                "reasoning_content": None
                            }
                except:
                    pass  # 忽略解析错误
        
        # 删除临时对话
        self.delete_dialogue(temp_dialogue_id)

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
        
        在 iBit 平台创建一个新的对话会话。
        如果创建失败，会自动重试登录。
        
        Returns:
            int: 新创建的对话 ID
        """
        url = self.url + "/proxy/v1/dialogue"
        data = {
            "assistant_id": 43,  # DeepSeek 助手 ID
            "title": f"[程序生成]{int(time.time()*1000)}-{uuid.uuid4().hex[:4]}",  # 唯一标题
        }
        response = requests.post(url, headers=self.headers, json=data)
        
        # 检查是否需要重新登录
        if response.status_code != 200:
            print(f"[ERROR] Failed to create dialogue, message: {response.json()['message']}")
            print("[INFO] Trying to re-login in 3 seconds...")
            time.sleep(3)
            self.login(self.username, self.password)  # 重新登录
            return self.new_dialogue()  # 递归重试
        
        return response.json()["data"]["id"]

    def delete_dialogue(self, dialogue_id):
        """
        删除对话
        
        删除指定的对话会话，用于清理临时对话。
        
        Args:
            dialogue_id: 要删除的对话 ID
            
        Returns:
            bool: 删除是否成功
        """
        url = self.url + f"/proxy/v1/dialogue"
        data = {
            "ids": [dialogue_id]
        }
        response = requests.delete(url, headers=self.headers, json=data)
        return response.json()["data"]["success"]

    def parse_cookie(self, cookie):
        """
        解析 Cookie 字符串
        
        将 Cookie 字符串解析为字典格式。
        
        Args:
            cookie: Cookie 字符串，格式为 "key1=value1; key2=value2"
            
        Returns:
            dict: Cookie 键值对字典
        """
        cookie = cookie.replace(" ","")
        cookie = cookie.split(";")
        cookie = {i.split("=")[0]:i.split("=")[1] for i in cookie}
        return cookie