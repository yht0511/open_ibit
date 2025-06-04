import json
import uuid
import requests
import auth.login
import urllib.parse
import time
import threading

class iBit:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.url = "https://ibit.yanhekt.cn"
    
    def init(self):
        self.login(self.username, self.password)
        self.check_login_thread = threading.Thread(target=self.check_login)
        self.check_login_thread.daemon = True
        self.check_login_thread.start()
    
    def login(self, username, password):
        self.username = username
        self.password = password
        self.cookies = auth.login.login(username, password)["cookie_json"]
        self.badge = self.cookies["badge_2"]
        self.badge_decoded = urllib.parse.quote(self.badge)
        self.headers = {
            "Host": "ibit.yanhekt.cn",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Chromium";v="108"',
            "badge": self.badge_decoded,
            "sec-ch-ua-mobile": "?0",
            "Authorization": "Bearer undefined",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.5359.125 Safari/537.36 dingtalk-win/1.0.0 nw(0.14.7) DingTalk(7.6.45-Release.250241020) Mojo/1.0.0 Native AppType(release) Channel/201200 Architecture/x86_64",
            "Content-Type": "application/json",
            "Xdomain-Client": "web_user",
            "x-assistant-id": "43",
            "sec-ch-ua-platform": '"Windows"',
            "Accept": "*/ *",
            "Origin": "https://ibit.yanhekt.cn",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": f"badge_2={self.badge}"
        }
    
    def check_login(self):
        while True:
            temp_dialogue_id=self.new_dialogue()
            self.delete_dialogue(temp_dialogue_id)
            time.sleep(60)
    
    def chat(self, query, history=[], temperature=0.7, top_k=3, score_threshold=0.5, prompt_name="", knowledge_base_name=""):
        result = ""
        reasoning =  ""
        for chunk in self.chat_stream(query, history, temperature, top_k, score_threshold, prompt_name, knowledge_base_name):
            if chunk.get("content"):
                result += chunk["content"]
            if chunk.get("reasoning_content"):
                reasoning += chunk["reasoning_content"]
        return reasoning, result
    
    def chat_stream(self, query, history=[], temperature=0.7, top_k=3, score_threshold=0.5, prompt_name="", knowledge_base_name=""):
        print(f"User: {query}")
        url = self.url + "/proxy/v1/chat/stream/private/kb"
        temp_dialogue_id = self.new_dialogue()
        query = self.get_history_prompt(history) + query
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
        response = requests.post(url, headers=self.headers, json=data, stream=True)
        response.raw.decode_content = True
        print("Assistant:",end="",flush=True)
        res = ""
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                try:
                    answer = json.loads(chunk.decode("utf-8").split("data: ")[1].replace("\n",""))["answer"]
                    res += answer
                    if answer not in ["<think>","</think>"]:
                        if "<think>" in res and "</think>" not in res:
                            yield {
                                "content": None,
                                "reasoning_content": answer
                            }
                        else:
                            yield {
                                "content": answer,
                                "reasoning_content": None
                            }
                    print(answer,end="",flush=True)
                except: pass
        self.delete_dialogue(temp_dialogue_id)

    def get_history_prompt(self, history):
        res = "[历史对话](请注意这是由程序提供的历史对话功能,不要把它当成用户对话的一部分,不要刻意提及它):"
        for i in history:
            res += f"\n{i['role']}:{i['content']}"
        res += "\n接下来是用户的新一轮问题:\n"
        return res
        
    def new_dialogue(self):
        url= self.url + "/proxy/v1/dialogue"
        data = {
            "assistant_id": 43,
            "title": f"[程序生成]{int(time.time()*1000)}-{uuid.uuid4().hex[:4]}",
        }
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code != 200:
            print(f"[ERROR] Failed to create dialogue, message: {response.json()['message']}")
            print("[INFO] Trying to re-login in 3 seconds...")
            time.sleep(3)
            self.login(self.username, self.password)
            return self.new_dialogue()
        return response.json()["data"]["id"]

    def delete_dialogue(self, dialogue_id):
        url = self.url + f"/proxy/v1/dialogue"
        data = {
            "ids": [dialogue_id]
        }
        response = requests.delete(url, headers=self.headers, json=data)
        return response.json()["data"]["success"]

    def parse_cookie(self, cookie):
        cookie = cookie.replace(" ","")
        cookie = cookie.split(";")
        cookie = {i.split("=")[0]:i.split("=")[1] for i in cookie}
        return cookie