"""
agent.py - 智能体广场 (HiAgent) 模型接口封装

本模块封装了北理工智能体广场（agent.bit.edu.cn）的模型 API。
支持官方 API Key 模式和旧的应用密钥/访客密钥模式。

官方文档参考：https://agent.bit.edu.cn/platform/doc/

主要功能：
1. 通过官方 API Key (Apikey Header) 或旧凭证进行身份验证
2. 支持流式和非流式对话
3. 自动会话管理（创建和删除对话）
4. 支持思维链 (reasoning_content) 输出
"""

import json
import time
import requests
import uuid

class Agent:
    """
    智能体广场 (HiAgent) 模型封装类
    
    支持官方 API 和旧版集成 API。
    """
    
    def __init__(self, api_key=None, appkey=None, visitor_key=None, timeout_seconds=15):
        """
        初始化 HiAgent 模型实例
        
        Args:
            api_key: 官方 API Key (推荐)，从智能体发布管理获取
            appkey: 旧版应用密钥 (可选)
            visitor_key: 旧版访客密钥 (可选)
            timeout_seconds: 请求超时时间
        """
        self.api_key = api_key
        self.appkey = appkey
        self.visitor_key = visitor_key
        self.timeout_seconds = timeout_seconds
        
        # 官方 API 配置
        self.base_url = "https://agent.bit.edu.cn/api/proxy/api/v1"
        
        # 旧版 API 配置 (回退使用)
        self.legacy_url = f"https://agent.bit.edu.cn/product/llm/chat/{appkey}" if appkey else ""
        
        # 默认 UserID，用于官方 API
        self.user_id = f"openai_ibit_{uuid.uuid4().hex[:8]}"

    def _get_headers(self):
        """构造请求头"""
        if self.api_key:
            return {
                "Apikey": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
        else:
            # 旧版模拟浏览器请求头
            return {
                'Accept': 'application/json, text/event-stream',
                'Content-Type': 'application/json; charset=utf-8',
                'app-visitor-key': self.visitor_key,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
            }

    def _get_cookies(self):
        """构造旧版 API 所需的 Cookie"""
        if self.api_key:
            return None
        return {'app-visitor-key': self.visitor_key}

    def init(self):
        """初始化操作"""
        # 官方模式通常不需要预清理，但可以根据需要添加
        pass

    def chat(self, query, history=[]):
        """非流式对话"""
        result = ""
        reasoning = ""
        for chunk in self.chat_stream(query, history):
            if chunk.get("content"):
                result += chunk["content"]
            if chunk.get("reasoning_content"):
                reasoning += chunk["reasoning_content"]
        return reasoning, result

    def chat_stream(self, query, history=[]):
        """流式对话 (生成器)"""
        if self.api_key:
            yield from self._chat_stream_official(query, history)
        else:
            yield from self._chat_stream_legacy(query, history)

    def _chat_stream_official(self, query, history):
        """使用官方 API 进行流式对话"""
        # 1. 创建会话
        create_url = f"{self.base_url}/create_conversation"
        try:
            res_create = requests.post(
                create_url, 
                headers=self._get_headers(), 
                json={"UserID": self.user_id},
                timeout=self.timeout_seconds
            )
            conv_id = res_create.json().get("Conversation", {}).get("AppConversationID")
        except Exception as e:
            print(f"[Agent] Create conversation failed: {e}")
            return

        # 2. 发送查询
        query_url = f"{self.base_url}/chat_query_v2"
        # 官方目前主要通过 prompt 传递历史
        full_query = self.get_history_prompt(history) + query
        
        payload = {
            "UserID": self.user_id,
            "AppConversationID": conv_id,
            "Query": full_query,
            "ResponseMode": "streaming"
        }

        try:
            response = requests.post(
                query_url, 
                headers=self._get_headers(), 
                json=payload, 
                stream=True,
                timeout=self.timeout_seconds
            )
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        try:
                            data = json.loads(line_str[6:])
                            # 官方 API 格式解析
                            # 注：此处需要根据官方 R1 的具体返回字段适配思维链
                            # 假设官方也遵循类似的 event 或 answer 结构
                            if data.get("event") == "think_message":
                                yield {"content": None, "reasoning_content": data.get("answer", "")}
                            elif data.get("event") == "message":
                                yield {"content": data.get("answer", ""), "reasoning_content": None}
                        except:
                            pass
        except Exception as e:
            print(f"[Agent] Chat stream failed: {e}")
        finally:
            # 3. 官方 API 可选：删除会话 (保持环境整洁)
            delete_url = f"{self.base_url}/delete_conversation"
            requests.post(
                delete_url, 
                headers=self._get_headers(), 
                json={"UserID": self.user_id, "AppConversationID": conv_id}
            )

    def _chat_stream_legacy(self, query, history):
        """使用旧版模拟接口进行流式对话 (回退逻辑)"""
        url = "https://agent.bit.edu.cn/api/proxy/chat/v2/chat_query"
        conv_id = self._new_dialogue_legacy()
        query = self.get_history_prompt(history) + query
        
        json_data = {
            'Query': query,
            'AppConversationID': conv_id,
            'AppKey': self.appkey,
            'QueryExtends': {'Files': []}
        }
        
        try:
            response = requests.post(url, json=json_data, cookies=self._get_cookies(), headers=self._get_headers(), stream=True)
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    try:
                        data = json.loads(chunk.decode("utf-8").split("data: ")[1].replace("\n",""))
                        if data["event"] == "think_message":
                            yield {"content": None, "reasoning_content": data["answer"]}
                        elif data["event"] == "message":
                            yield {"content": data["answer"], "reasoning_content": None}
                    except: pass
        finally:
            self._delete_dialogue_legacy(conv_id)

    def get_history_prompt(self, history):
        """构造历史对话提示"""
        if not history: return ""
        res = "[历史对话](程序提供):"
        for i in history:
            res += f"\n{i['role']}:{i['content']}"
        res += "\n新问题:\n"
        return res

    def _new_dialogue_legacy(self):
        url = "https://agent.bit.edu.cn/api/proxy/chat/v2/create_conversation"
        res = requests.post(url, json={'AppKey': self.appkey}, cookies=self._get_cookies(), headers=self._get_headers())
        return res.json().get("Conversation", {}).get("AppConversationID")

    def _delete_dialogue_legacy(self, dialogue_id):
        url = 'https://agent.bit.edu.cn/api/proxy/chat/v2/delete_conversation'
        requests.post(url, json={'AppKey': self.appkey, 'AppConversationID': dialogue_id}, cookies=self._get_cookies(), headers=self._get_headers())
