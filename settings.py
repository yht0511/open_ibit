import os
import models.agent as agent
import models.ibit as ibit
import tokenizer.deepseek.deepseek_tokenizer as deepseek_tokenizer


bit_username = ""
bit_password = ""
agent_app_key = ""
agent_visitor_key = ""

api_key = ""

print_statistics_interval = 60 

price_log_file = "./data/statistics.txt"
price_log_json = "./data/statistics.json"

os.makedirs(os.path.dirname(price_log_file), exist_ok=True)
if not os.path.exists(price_log_file):
    with open(price_log_file, 'w') as f:
        f.write("")
os.makedirs(os.path.dirname(price_log_json), exist_ok=True)
if not os.path.exists(price_log_json):
    with open(price_log_json, 'w') as f:
        f.write("{}")
if os.environ.get('BIT_USERNAME'):
    bit_username = os.environ.get('BIT_USERNAME')
if os.environ.get('BIT_PASSWORD'):
    bit_password = os.environ.get('BIT_PASSWORD')
if os.environ.get('AGENT_APP_KEY'):
    agent_app_key = os.environ.get('AGENT_APP_KEY')
if os.environ.get('AGENT_VISITOR_KEY'):
    agent_visitor_key = os.environ.get('AGENT_VISITOR_KEY')
if os.environ.get('API_KEY'):
    api_key = os.environ.get('API_KEY')
    
models = {}

if bit_username and bit_password:
    models["ibit"] = {
        "name": "iBit",
        "model": ibit.iBit(bit_username, bit_password),
        "price": {
            "input": 4,
            "output": 16
        },
        "tokenizer": deepseek_tokenizer.count_tokens
    }
if agent_app_key and agent_visitor_key:
    models["deepseek-r1"] = {
        "name": "DeepSeek-R1",
        "model": agent.Agent(
            appkey=agent_app_key,
            visitor_key=agent_visitor_key
        ),
        "price": {
            "input": 4,
            "output": 16
        },
        "tokenizer": deepseek_tokenizer.count_tokens
    }
    
if not models:
    raise ValueError("No valid models configured!")

    
