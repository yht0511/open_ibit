# HiAgent 模型列表与调用指南

本文档汇总了 HiAgent 平台支持的主要模型列表及其调用方式。

## 1. 模型列表 (Available Models)

根据平台当前状态，以下是已部署并可供调用的核心模型：

| 模型名称 | 类型 | 描述 | 适用场景 |
| :--- | :--- | :--- | :--- |
| **DeepSeek-R1** | 对话型 | 深度求索开发的推理型大模型，支持长上下文与强逻辑推理。 | 复杂逻辑分析、代码生成、学术研究 |
| **DeepSeek-V3** | 对话型 | 深度求索通用大模型，知识更新至 2024 年 7 月。 | 日常问答、创意写作、通用任务 |
| **Doubao-1.5-Pro-256k** | 对话型 | 字节跳动豆包大模型 Pro 版，支持极长文本（256k）。 | 长文档解读、超长会话保持 |
| **Doubao-1.5-Pro-32k** | 对话型 | 豆包 Pro 版，性能均衡，适合大多数应用。 | 通用办公、智能助手、知识库问答 |
| **Doubao-1.5-Lite-32k** | 对话型 | 豆包轻量版，响应速度极快，成本更低。 | 快速响应任务、简单文本处理 |

---

## 2. 调用方式

### 2.1 环境变量配置
建议将敏感信息存储在 `.env` 文件中：
```bash
HI_API_KEY=您的_API_KEY
HI_BASE_URL=https://agent.bit.edu.cn/api/proxy/api/v1
```

### 2.2 调用流程
1. **创建会话**: 发送 `POST` 请求到 `/create_conversation` 获取 `AppConversationID`。
2. **对话查询**: 发送 `POST` 请求到 `/chat_query_v2`，并携带会话 ID。

---

## 3. 代码示例 (Python)

```python
import os
import requests
import json
from dotenv import load_dotenv

# 加载配置
load_dotenv()
API_KEY = os.getenv("HI_API_KEY")
BASE_URL = os.getenv("HI_BASE_URL")

def call_hiagent(query):
    headers = {"Apikey": API_KEY, "Content-Type": "application/json"}
    
    # 1. 获取会话 ID
    res_conv = requests.post(f"{BASE_URL}/create_conversation", 
                             headers=headers, json={"UserID": "user_01"})
    conv_id = res_conv.json().get("Conversation", {}).get("AppConversationID")
    
    # 2. 调用对话接口
    payload = {
        "UserID": "user_01",
        "AppConversationID": conv_id,
        "Query": query,
        "ResponseMode": "blocking"
    }
    res_chat = requests.post(f"{BASE_URL}/chat_query_v2", 
                             headers=headers, json=payload)
    
    return res_chat.json().get("answer")

if __name__ == "__main__":
    print(call_hiagent("请简述 DeepSeek-R1 的优势。"))
```

---

## 4. 来源与参考
- **平台地址**: [https://agent.bit.edu.cn](https://agent.bit.edu.cn)
- **官方文档**: [HiAgent Document](https://agent.bit.edu.cn/platform/doc)
- **智能体广场**: 模型详情参考自个人空间及公开智能体配置。

---
*文档生成日期：2026年3月2日*
