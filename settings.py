import os


username = ""
password = ""
api_key = ""


if os.environ.get('BIT_USERNAME'):
    username = os.environ.get('BIT_USERNAME')
if os.environ.get('BIT_PASSWORD'):
    password = os.environ.get('BIT_PASSWORD')
if os.environ.get('API_KEY'):
    api_key = os.environ.get('API_KEY')
    
if not username or not password:
    raise Exception("未设置用户名或密码!")