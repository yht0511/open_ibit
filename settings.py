import os
import agent
import ibit


bit_username = ""
bit_password = ""
agent_app_key = ""
agent_visitor_key = ""

api_key = ""

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
    models["ibit"] = ibit.iBit(bit_username, bit_password)
if agent_app_key and agent_visitor_key:
    models["deepseek-r1"] = agent.Agent(agent_app_key, agent_visitor_key)
    
if not models:
    raise ValueError("No valid models configured!")

    
