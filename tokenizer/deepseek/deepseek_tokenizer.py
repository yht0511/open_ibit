"""
deepseek_tokenizer.py - DeepSeek 模型分词器

本模块加载 DeepSeek 模型的分词器，用于计算文本的 Token 数量。
主要用于费用计算，将文本长度转换为 Token 数量。

分词器配置文件：
- tokenizer.json: 分词器词表配置
- tokenizer_config.json: 分词器参数配置

使用方式：
    from tokenizer.deepseek import deepseek_tokenizer
    token_count = deepseek_tokenizer.count_tokens("你好世界")
"""

import transformers  # HuggingFace Transformers 库
import os  # 操作系统接口，用于获取文件路径


def count_tokens(str):
    """
    计算文本的 Token 数量
    
    使用 DeepSeek 分词器对输入文本进行编码，返回 Token 数量。
    用于费用计算时统计输入和输出的 Token 数。
    
    Args:
        str: 要计算 Token 数量的文本字符串
        
    Returns:
        int: 文本对应的 Token 数量
    """
    result = tokenizer.encode(str)
    return len(result)


# 获取分词器配置文件所在目录（当前文件所在目录）
chat_tokenizer_dir = os.path.dirname(os.path.abspath(__file__))


# 加载 DeepSeek 分词器
# trust_remote_code=True 允许执行分词器中的自定义代码
# 分词器配置从 tokenizer.json 和 tokenizer_config.json 读取
tokenizer = transformers.AutoTokenizer.from_pretrained( 
        chat_tokenizer_dir, trust_remote_code=True
        )
