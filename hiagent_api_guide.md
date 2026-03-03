# HiAgent API 调用指南

本指南详细介绍了如何使用北京理工大学 HiAgent 平台的 API 接口进行大模型对话调用。

---

## 1. 准备工作

在调用 API 之前，您需要获取以下凭证：

### 1.1 获取 API Key (Apikey)
1. 登录 [HiAgent 平台](https://agent.bit.edu.cn)。
2. 进入您创建或拥有的**智能体**。
3. 在页面右侧或菜单中点击 **“发布管理”** 或 **“API 调用”**。
4. 在“API 密钥”部分，创建一个永久或限时的密钥并复制。

### 1.2 获取 AppID
在智能体页面的 URL 中或“API 调用”页面的代码示例中可以找到 `AppID`（如 `d5akl1...`）。

---

## 2. 接口基本信息

- **Base URL**: `https://agent.bit.edu.cn/api/proxy/api/v1`
- **内容类型 (Content-Type)**: `application/json`
- **鉴权方式**: 在 HTTP Header 中添加 `Apikey`。

---

## 3. 核心调用流程

HiAgent 的对话调用分为两个阶段：**创建会话** 和 **发送查询**。

### 3.1 创建会话 (Create Conversation)
在开始对话前，必须先获取一个有效的会话 ID。

- **Endpoint**: `/create_conversation`
- **Method**: `POST`
- **请求参数 (JSON)**:
  - `UserID` (string, 必填): 用户标识，建议使用随机 ID 或固定用户标识。
- **返回结果**: 包含 `AppConversationID`，用于后续对话。

### 3.2 发送查询 (Chat Query V2)
使用获取到的会话 ID 进行实际的大模型对话。

- **Endpoint**: `/chat_query_v2`
- **Method**: `POST`
- **请求参数 (JSON)**:
  - `UserID` (string, 必填): 与创建会话时一致。
  - `AppConversationID` (string, 必填): 上一步获取的 ID。
  - `Query` (string, 必填): 您的提问内容。
  - `ResponseMode` (string): `blocking` (阻塞返回完整结果) 或 `streaming` (流式返回)。

---

## 4. Python 调用示例

以下是一个完整的自动化脚本，演示了从创建会话到获取回答的全过程。

```python
import requests
import json

# --- 配置区 ---
BASE_URL = "https://agent.bit.edu.cn/api/proxy/api/v1"
API_KEY = "您的_API_KEY"  # 替换为实际密钥
USER_ID = "test_user_01"   # 自定义用户 ID

def hiagent_test():
    headers = {
        "Apikey": API_KEY,
        "Content-Type": "application/json"
    }

    # 1. 创建会话
    create_url = f"{BASE_URL}/create_conversation"
    create_payload = {"UserID": USER_ID}
    
    print("正在创建会话...")
    res_create = requests.post(create_url, headers=headers, json=create_payload)
    if res_create.status_code != 200:
        print(f"创建会话失败: {res_create.text}")
        return

    conv_id = res_create.json().get("Conversation", {}).get("AppConversationID")
    print(f"会话创建成功，ID: {conv_id}")

    # 2. 发送对话请求
    query_url = f"{BASE_URL}/chat_query_v2"
    query_payload = {
        "UserID": USER_ID,
        "AppConversationID": conv_id,
        "Query": "你好，请问 HiAgent 平台支持哪些大模型？",
        "ResponseMode": "blocking"
    }

    print("正在等待模型响应...")
    res_query = requests.post(query_url, headers=headers, json=query_payload)
    if res_query.status_code == 200:
        answer = res_query.json().get("answer")
        print("
=== 模型回复 ===")
        print(answer)
        print("================")
    else:
        print(f"请求失败: {res_query.text}")

if __name__ == "__main__":
    hiagent_test()
```

---

## 5. 常见问题 (FAQ)
- **报错 `missing required parameter`**: 检查是否遗漏了 `AppConversationID` 或 `UserID`。
- **401 Unauthorized**: 检查 Header 中的 `Apikey` 是否正确，注意大小写（`Apikey` 而非 `api-key`）。
- **流式输出**: 如果需要流式响应，需设置 `ResponseMode: "streaming"` 并通过 `requests` 的 `stream=True` 迭代获取数据块。

---

## 6. 资料来源
- [HiAgent OpenAPI 通用说明](https://agent.bit.edu.cn/platform/doc/api/hiagent-openapi-general-instructions)
- [智能体接口详细文档](https://agent.bit.edu.cn/platform/doc/api/agent-api-call/agent-api-documentation)
- [HiAgent API 调用示例代码](https://agent.bit.edu.cn/platform/doc/api/hiagent-api-call-examples)
- [HiAgent 开发者中心](https://agent.bit.edu.cn/platform/doc)

---
*文档生成日期：2026年3月2日*
