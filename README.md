# 百丽宫的Deepseek R1

## 项目简介

你梨居然上新了满血版的r1 671b模型!可喜可贺~
正愁找不到免费可靠的api吗?刚好来白嫖学校的!

### 本项目的核心价值

北京理工大学提供的 HiAgent (agent.bit.edu.cn) 和 iBit (ibit.yanhekt.cn) 平台虽然功能强大，但其官方 API 接口采用的是自定义协议（需处理会话创建、UserID 管理、特定 SSE 事件等），无法直接与通用的 OpenAI 客户端（如 NextChat, LobeChat, OpenAI SDK 等）对接。

**本项目的作用：**
- **协议转换**：将 BIT 自定义 API 转换为标准的 OpenAI Chat Completions API 协议。
- **无状态化**：自动管理上游会话的创建与销毁，用户只需发送 `messages` 列表。
- **即插即用**：支持流式输出、思维链（Reasoning）显示，完美适配主流 AI 客户端。

## 项目架构图

```
openai_ibit/
├── server.py              # FastAPI 主服务入口，提供 OpenAI 兼容的 API 接口
├── settings.py            # 配置管理模块，负责环境变量读取和模型配置
├── requirements.txt       # Python 依赖包列表
├── Dockerfile             # Docker 容器构建配置文件
├── LICENSE                # 开源许可证文件
├── README.md              # 项目说明文档
│
├── auth/                  # 认证模块目录
│   └── login.py           # 北理工统一身份认证登录封装
│
├── models/                # 模型接口目录
│   ├── ibit.py            # iBit 平台 DeepSeek 模型接口封装
│   └── agent.py           # 智能体广场 DeepSeek-R1 模型接口封装
│
├── tokenizer/             # 分词器目录
│   └── deepseek/          # DeepSeek 模型专用分词器
│       ├── deepseek_tokenizer.py  # 分词器加载和 Token 计数功能
│       ├── tokenizer.json         # 分词器词表配置
│       └── tokenizer_config.json  # 分词器参数配置
│
└── data/                  # 运行时数据目录（自动创建）
    ├── statistics.txt     # 调用统计日志（文本格式）
    └── statistics.json    # 调用统计数据（JSON 格式）
```

## 架构流程图

```
                          ┌─────────────────────────────────────┐
                          │           客户端请求                │
                          │   (OpenAI SDK / NextChat 等)        │
                          └─────────────────┬───────────────────┘
                                            │
                                            ▼
                          ┌─────────────────────────────────────┐
                          │         server.py (FastAPI)         │
                          │   - /v1/models (获取模型列表)       │
                          │   - /v1/chat/completions (对话)     │
                          │   - API Key 验证 (可选)             │
                          └─────────────────┬───────────────────┘
                                            │
                          ┌─────────────────┴───────────────────┐
                          │           settings.py               │
                          │   - 环境变量配置读取                │
                          │   - 模型实例化与注册                │
                          └─────────────────┬───────────────────┘
                                            │
               ┌────────────────────────────┼────────────────────────────┐
               │                            │                            │
               ▼                            ▼                            ▼
┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐
│    models/ibit.py        │  │    models/agent.py       │  │ tokenizer/deepseek/      │
│  iBit 平台接口封装       │  │  智能体广场接口封装      │  │ deepseek_tokenizer.py    │
│  - 登录认证              │  │  - 对话管理              │  │  - Token 计数            │
│  - 流式/非流式对话       │  │  - 流式/非流式对话       │  │  - 费用计算支持          │
└────────────┬─────────────┘  └────────────┬─────────────┘  └──────────────────────────┘
             │                             │
             ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│    auth/login.py         │  │   agent.bit.edu.cn       │
│  统一身份认证登录        │  │   智能体广场 API         │
└────────────┬─────────────┘  └──────────────────────────┘
             │
             ▼
┌──────────────────────────┐
│   ibit.yanhekt.cn        │
│   iBit 平台 API          │
└──────────────────────────┘
```

## 核心模块说明

| 文件路径 | 功能描述 |
|---------|---------|
| `server.py` | FastAPI 主服务，提供 OpenAI 兼容的 Chat Completions API，支持流式和非流式响应 |
| `settings.py` | 配置管理，读取环境变量，初始化模型实例，管理统计文件路径 |
| `auth/login.py` | 封装 bit_login 库，实现北理工统一身份认证登录 |
| `models/ibit.py` | iBit 平台（ibit.yanhekt.cn）的 DeepSeek 模型接口，支持自动重连 |
| `models/agent.py` | 智能体广场（agent.bit.edu.cn）的 DeepSeek-R1 模型接口 |
| `tokenizer/deepseek/deepseek_tokenizer.py` | DeepSeek 模型的分词器，用于计算 Token 数量和费用 |

## 环境变量配置

本项目支持以下环境变量配置：

| 环境变量名 | 必需 | 默认值 | 说明 |
|-----------|------|--------|------|
| `BIT_USERNAME` | 是* | `""` | 北理工统一身份认证用户名，用于 iBit 平台登录 |
| `BIT_PASSWORD` | 是* | `""` | 北理工统一身份认证密码，用于 iBit 平台登录 |
| `HI_API_KEY` | 是* | `""` | **推荐**：HiAgent 平台官方 API Key（从“发布管理”获取） |
| `AGENT_APP_KEY` | 否 | `""` | HiAgent 应用密钥（旧模式，不推荐） |
| `AGENT_VISITOR_KEY` | 否 | `""` | HiAgent 访客密钥（旧模式，不推荐） |
| `API_KEY` | 否 | `""` | 本服务的 API 访问密钥，设置后客户端需在请求头中携带 |
| `PRINT_STATISTICS_INTERVAL` | 否 | `30` | 统计信息打印间隔（秒） |
| `TZ` | 否 | 系统默认 | 时区设置，推荐设置为 `Asia/Shanghai` |

> **官方文档**：有关 HiAgent (agent.bit.edu.cn) 的官方 API 调用方法及说明，请参阅 [HiAgent 开发者中心](https://agent.bit.edu.cn/platform/doc/)。

> **注意**：标记为 `是*` 的环境变量表示至少需要配置一组模型凭证：
> - **iBit 模型**：需要同时设置 `BIT_USERNAME` 和 `BIT_PASSWORD`
> - **DeepSeek-R1 模型**：推荐设置 `HI_API_KEY`；也可使用旧模式 `AGENT_APP_KEY` + `AGENT_VISITOR_KEY`
> 
> 如果两组凭证都未配置，程序启动时会报错。

## 部署方法

### 方式一：Docker 部署（推荐）

#### 1. 仅使用 iBit 模型

```bash
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME=你的统一身份认证用户名 \
    -e BIT_PASSWORD=你的统一身份认证密码 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

#### 2. 仅使用智能体广场 DeepSeek-R1 模型（官方推荐）

```bash
docker run -d -p 8000:8000 --name OpeniBIT \
    -e HI_API_KEY=你的HiAgent官方API密钥 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

#### 3. 仅使用智能体广场 DeepSeek-R1 模型（旧模式）

```bash
docker run -d -p 8000:8000 --name OpeniBIT \
    -e AGENT_APP_KEY=你的应用密钥 \
    -e AGENT_VISITOR_KEY=你的访客密钥 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

#### 4. 同时使用两个模型

```bash
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME=你的统一身份认证用户名 \
    -e BIT_PASSWORD=你的统一身份认证密码 \
    -e HI_API_KEY=你的HiAgent官方API密钥 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

#### 5. 启用 API 密钥保护

```bash
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME=你的统一身份认证用户名 \
    -e BIT_PASSWORD=你的统一身份认证密码 \
    -e API_KEY=你想设置的api密钥 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

#### 6. 完整配置示例

```bash
docker run -d -p 8000:8000 --name OpeniBIT \
    -e BIT_USERNAME=你的统一身份认证用户名 \
    -e BIT_PASSWORD=你的统一身份认证密码 \
    -e HI_API_KEY=你的HiAgent官方API密钥 \
    -e API_KEY=你想设置的api密钥 \
    -e PRINT_STATISTICS_INTERVAL=60 \
    -e TZ=Asia/Shanghai \
    yht0511/open_ibit:latest
```

### 方式二：Docker Compose 部署

创建 `docker-compose.yml` 文件：

```yaml
version: '3'
services:
  openibit:
    image: yht0511/open_ibit:latest
    container_name: OpeniBIT
    ports:
      - "8000:8000"
    environment:
      - BIT_USERNAME=你的统一身份认证用户名
      - BIT_PASSWORD=你的统一身份认证密码
        - HI_API_KEY=你的HiAgent官方API密钥   # 推荐
        - AGENT_APP_KEY=你的应用密钥          # 旧模式可选
        - AGENT_VISITOR_KEY=你的访客密钥      # 旧模式可选
      - API_KEY=你想设置的api密钥           # 可选
      - PRINT_STATISTICS_INTERVAL=30        # 可选
      - TZ=Asia/Shanghai
    restart: unless-stopped
```

启动服务：
```bash
docker-compose up -d
```

### 方式三：本地运行

1. 克隆仓库并安装依赖：
```bash
git clone https://github.com/Bigzhangbig/openai_ibit.git
cd openai_ibit
pip install -r requirements.txt
```

2. 设置环境变量：
```bash
export BIT_USERNAME=你的统一身份认证用户名
export BIT_PASSWORD=你的统一身份认证密码
export HI_API_KEY=你的HiAgent官方API密钥  # 使用 deepseek-r1 时推荐
export API_KEY=你想设置的api密钥  # 可选
```

3. 启动服务：
```bash
python server.py
```

## API 使用说明

服务启动后，你可以通过以下方式访问：

- **API 地址**：`http://localhost:8000`
- **模型列表端点**：`GET /v1/models`
- **对话补全端点**：`POST /v1/chat/completions`

### 可用模型

| 模型名称 | 说明 | 所需环境变量 |
|---------|------|-------------|
| `ibit` | iBit 平台 DeepSeek 模型 | `BIT_USERNAME`, `BIT_PASSWORD` |
| `deepseek-r1` | 智能体广场 DeepSeek-R1 模型 | `HI_API_KEY`（推荐）或 `AGENT_APP_KEY` + `AGENT_VISITOR_KEY`（旧模式） |

### 客户端对接示例

#### Python OpenAI SDK
```python
from openai import OpenAI

client = OpenAI(
    api_key="你设置的API_KEY",  # 如果未设置 API_KEY，可以填任意值
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="ibit",  # 或 "deepseek-r1"
    messages=[
        {"role": "user", "content": "你好"}
    ],
    stream=True  # 支持流式输出
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

#### NextChat / ChatGPT-Next-Web

1. 打开 NextChat 设置
2. 在 API 设置中填入：
   - **API 地址**：`http://localhost:8000`（或你的服务器地址）
   - **API Key**：你设置的 `API_KEY`（未设置则随意填写）
3. 选择模型 `ibit` 或 `deepseek-r1`

## 官方 HiAgent Agent API 直连调用（不经过本项目）

如果你希望直接调用 HiAgent 官方 Agent API（不走 OpenAI 协议转换），可按以下方式：

- **Base URL**：`https://agent.bit.edu.cn/api/proxy/api/v1`
- **鉴权 Header**：`Apikey: 你的_API_KEY`
- **调用流程**：先 `POST /create_conversation`，再 `POST /chat_query_v2`

### 1）创建会话

```bash
curl -X POST 'https://agent.bit.edu.cn/api/proxy/api/v1/create_conversation' \
    -H 'Apikey: 你的_API_KEY' \
    -H 'Content-Type: application/json' \
    -d '{"UserID":"test_user_01"}'
```

从响应中取 `Conversation.AppConversationID`。

### 2）发送查询

```bash
curl -X POST 'https://agent.bit.edu.cn/api/proxy/api/v1/chat_query_v2' \
    -H 'Apikey: 你的_API_KEY' \
    -H 'Content-Type: application/json' \
    -d '{
        "UserID":"test_user_01",
        "AppConversationID":"上一步获取的ID",
        "Query":"你好，请简述 DeepSeek-R1 的优势。",
        "ResponseMode":"blocking"
    }'
```

`ResponseMode` 可选：
- `blocking`：阻塞返回完整回答
- `streaming`：流式返回

### 3）Python 示例

```python
import requests

BASE_URL = "https://agent.bit.edu.cn/api/proxy/api/v1"
API_KEY = "你的_API_KEY"
USER_ID = "test_user_01"

headers = {
        "Apikey": API_KEY,
        "Content-Type": "application/json"
}

# 1. 创建会话
res_create = requests.post(
        f"{BASE_URL}/create_conversation",
        headers=headers,
        json={"UserID": USER_ID}
)
conv_id = res_create.json().get("Conversation", {}).get("AppConversationID")

# 2. 发送查询
res_query = requests.post(
        f"{BASE_URL}/chat_query_v2",
        headers=headers,
        json={
                "UserID": USER_ID,
                "AppConversationID": conv_id,
                "Query": "你好，请问 HiAgent 平台支持哪些大模型？",
                "ResponseMode": "blocking"
        }
)

print(res_query.json().get("answer"))
```

更多参考：
- [HiAgent 开发者中心](https://agent.bit.edu.cn/platform/doc)
- [HiAgent OpenAPI 通用说明](https://agent.bit.edu.cn/platform/doc/api/hiagent-openapi-general-instructions)
- [智能体接口详细文档](https://agent.bit.edu.cn/platform/doc/api/agent-api-call/agent-api-documentation)

## 更新日志

## 2026.3.3更新
- README 新增“官方 HiAgent Agent API 直连调用”章节，补充 `create_conversation` + `chat_query_v2` 的调用流程。
- 增加官方 `curl` 与 Python 示例，便于不经过本项目时直接对接 HiAgent。
- 统一 `deepseek-r1` 的凭证说明：推荐 `HI_API_KEY`，同时保留 `AGENT_APP_KEY` + `AGENT_VISITOR_KEY` 旧模式说明。

## 2025.6.8更新
现在支持智能体广场的模型,设置环境变量`AGENT_APP_KEY`和`AGENT_VISITOR_KEY`即可使用。
默认模型名称:"deepseek-r1",ibit模型名称:"ibit"。

## Edge/Serverless 部署

除了 Docker 部署方式，本项目还支持部署到各种边缘计算/无服务器平台：

- **Cloudflare Workers** - 全球边缘节点，延迟低
- **Deno Deploy** - TypeScript 原生支持
- **Vercel Edge Functions** - 与 Vercel 生态深度集成
- **Netlify Edge Functions** - 简单易用

详细部署说明请参考 [Edge/Serverless 部署指南](EDGE_DEPLOYMENT.md)。

### 快速开始 (以 Cloudflare Workers 为例)

```bash
# 1. 安装 Wrangler
npm install -g wrangler

# 2. 登录
wrangler login

# 3. 复制文件
cd edge
cp cloudflare-worker.js your-project/
cp wrangler.toml your-project/
cd your-project

# 4. 设置密钥
wrangler secret put AGENT_APP_KEY
wrangler secret put AGENT_VISITOR_KEY

# 5. 部署
wrangler deploy
```

部署完成后即可获得一个免费的 API 端点！
