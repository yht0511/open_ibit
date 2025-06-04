import json
import requests

class Agent:
    def __init__(self, appkey, visitor_key):
        self.appkey = appkey
        self.visitor_key = visitor_key
        self.url = f"https://agent.bit.edu.cn/product/llm/chat/{appkey}"
        self.cookies = {
            'app-visitor-key': visitor_key,
        }

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
            'app-visitor-key': 'd104cralaa6c73dtnoi0',
            'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
    
    def init(self):
        self.clear_conversations()  # 清除所有对话
    
    def chat(self, query, history=[]):
        result = ""
        reasoning =  ""
        for chunk in self.chat_stream(query, history):
            if chunk.get("content"):
                result += chunk["content"]
            if chunk.get("reasoning_content"):
                reasoning += chunk["reasoning_content"]
        return reasoning, result
    
    def chat_stream(self, query, history=[]):
        print(f"User: {query}")
        url = "https://agent.bit.edu.cn/api/proxy/chat/v2/chat_query"
        temp_dialogue_id = self.new_dialogue()
        query = self.get_history_prompt(history) + query
        json_data = {
            'Query': query,
            'AppConversationID': temp_dialogue_id,
            'AppKey': self.appkey,
            'QueryExtends': {
                'Files': [],
            }
        }
        response = requests.post(url, json=json_data, cookies=self.cookies, headers=self.headers, stream=True)
        response.raw.decode_content = True
        print("Assistant:",end="",flush=True)
        answer = ""
        self.delete_dialogue(temp_dialogue_id)
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    data = json.loads(chunk.decode("utf-8").split("data: ")[1].replace("\n",""))
                    if data["event"] == "think_message" and data["answer"]:
                        answer = data["answer"]
                        yield {
                            "content": None,
                            "reasoning_content": answer
                        }
                    elif data["event"] == "message" and data["answer"]:
                        answer = data["answer"]
                        yield {
                            "content": answer,
                            "reasoning_content": None
                        }
                    print(answer,end="",flush=True)
                except: pass

    def get_history_prompt(self, history):
        res = "[历史对话](请注意这是由程序提供的历史对话功能,不要把它当成用户对话的一部分,不要刻意提及它):"
        for i in history:
            res += f"\n{i['role']}:{i['content']}"
        res += "\n接下来是用户的新一轮问题:\n"
        return res
        
    def new_dialogue(self):
        url = "https://agent.bit.edu.cn/api/proxy/chat/v2/create_conversation"
        json_data = {
            'AppKey': self.appkey,
            'Inputs': {},
        }
        response = requests.post(
            url,
            json=json_data,
            cookies=self.cookies, 
            headers=self.headers
        )
        return response.json().get("Conversation").get("AppConversationID")

    def delete_dialogue(self, dialogue_id):
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
        conversations = self.get_conversation_list()
        for conversation in self.get_conversation_list():
            dialogue_id = conversation.get("AppConversationID")
            if dialogue_id:
                self.delete_dialogue(dialogue_id)
        return True

