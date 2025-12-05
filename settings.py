"""
settings.py - 配置管理模块

本模块负责管理项目的所有配置，包括：
1. 环境变量读取和解析
2. 模型实例的创建和注册
3. 统计日志文件路径配置
4. API Key 和认证信息管理

环境变量说明：
- BIT_USERNAME: 北理工统一身份认证用户名（iBit 模型必需）
- BIT_PASSWORD: 北理工统一身份认证密码（iBit 模型必需）
- AGENT_APP_KEY: 智能体广场应用密钥（Agent 模型必需）
- AGENT_VISITOR_KEY: 智能体广场访客密钥（Agent 模型必需）
- API_KEY: 可选的 API 访问密钥，用于保护服务接口
- PRINT_STATISTICS_INTERVAL: 统计信息打印间隔（秒），默认 30
"""

import os  # 操作系统接口，用于读取环境变量
import models.agent as agent  # 智能体广场模型接口
import models.ibit as ibit  # iBit 平台模型接口
import tokenizer.deepseek.deepseek_tokenizer as deepseek_tokenizer  # DeepSeek 分词器


# ==================== 凭证配置 ====================
# 北理工统一身份认证凭证（用于 iBit 平台）
bit_username = ""  # 统一身份认证用户名
bit_password = ""  # 统一身份认证密码

# 智能体广场凭证
agent_app_key = ""  # 应用密钥（从智能体广场获取）
agent_visitor_key = ""  # 访客密钥（从智能体广场获取）

# API 访问密钥（可选，用于保护服务接口）
api_key = ""

# ==================== 统计配置 ====================
# 统计信息打印间隔（秒）
print_statistics_interval = 30 

# 统计日志文件路径
price_log_file = "./data/statistics.txt"  # 文本格式日志
price_log_json = "./data/statistics.json"  # JSON 格式统计数据

# ==================== 初始化统计文件目录 ====================
# 确保统计日志目录存在
os.makedirs(os.path.dirname(price_log_file), exist_ok=True)
if not os.path.exists(price_log_file):
    with open(price_log_file, 'w') as f:
        f.write("")  # 创建空的文本日志文件

os.makedirs(os.path.dirname(price_log_json), exist_ok=True)
if not os.path.exists(price_log_json):
    with open(price_log_json, 'w') as f:
        f.write("{}")  # 创建空的 JSON 统计文件

# ==================== 从环境变量读取配置 ====================
# 读取 iBit 平台凭证
if os.environ.get('BIT_USERNAME'):
    bit_username = os.environ.get('BIT_USERNAME')
if os.environ.get('BIT_PASSWORD'):
    bit_password = os.environ.get('BIT_PASSWORD')

# 读取智能体广场凭证
if os.environ.get('AGENT_APP_KEY'):
    agent_app_key = os.environ.get('AGENT_APP_KEY')
if os.environ.get('AGENT_VISITOR_KEY'):
    agent_visitor_key = os.environ.get('AGENT_VISITOR_KEY')

# 读取 API 密钥
if os.environ.get('API_KEY'):
    api_key = os.environ.get('API_KEY')

# 读取统计打印间隔
if os.environ.get('PRINT_STATISTICS_INTERVAL'):
    try:
        print_statistics_interval = int(os.environ.get('PRINT_STATISTICS_INTERVAL'))
    except ValueError:
        pass  # 解析失败时保持默认值

# ==================== 模型注册 ====================
# 存储所有可用模型的字典
# 键：模型名称（API 调用时使用）
# 值：包含模型实例、价格、分词器等信息的字典
models = {}

# 注册 iBit 平台模型
# 需要提供统一身份认证的用户名和密码
if bit_username and bit_password:
    models["ibit"] = {
        "name": "iBit",  # 模型显示名称
        "model": ibit.iBit(bit_username, bit_password),  # 模型实例
        "price": {
            "input": 4,  # 输入价格：4元/百万Token
            "output": 16  # 输出价格：16元/百万Token
        },
        "tokenizer": deepseek_tokenizer.count_tokens  # 分词器函数
    }

# 注册智能体广场 DeepSeek-R1 模型
# 需要提供应用密钥和访客密钥
if agent_app_key and agent_visitor_key:
    models["deepseek-r1"] = {
        "name": "DeepSeek-R1",  # 模型显示名称
        "model": agent.Agent(
            appkey=agent_app_key,
            visitor_key=agent_visitor_key
        ),  # 模型实例
        "price": {
            "input": 4,  # 输入价格：4元/百万Token
            "output": 16  # 输出价格：16元/百万Token
        },
        "tokenizer": deepseek_tokenizer.count_tokens  # 分词器函数
    }

# 验证是否至少有一个可用模型
if not models:
    raise ValueError("No valid models configured!")
