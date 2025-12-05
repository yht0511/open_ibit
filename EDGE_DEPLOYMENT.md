# Edge/Serverless 部署指南

本文档提供了将 OpenAI-compatible API 部署到各种无服务器计算和边缘服务平台的详细说明。

## 目录

- [概述](#概述)
- [环境变量](#环境变量)
- [Cloudflare Workers](#cloudflare-workers)
- [Deno Deploy](#deno-deploy)
- [Vercel Edge Functions](#vercel-edge-functions)
- [Netlify Edge Functions](#netlify-edge-functions)
- [API 使用说明](#api-使用说明)
- [常见问题](#常见问题)

## 概述

Edge/Serverless 版本是原 Python FastAPI 服务的 JavaScript/TypeScript 实现，专为边缘计算环境优化。支持以下平台：

| 平台 | 文件 | 运行时 | 免费额度 |
|------|------|--------|----------|
| Cloudflare Workers | `cloudflare-worker.js` | JavaScript | 100,000 请求/天 |
| Deno Deploy | `deno-deploy.ts` | TypeScript/Deno | 100,000 请求/天 |
| Vercel Edge | `vercel/` | JavaScript | 100,000 请求/月 |
| Netlify Edge | `netlify/` | TypeScript/Deno | 1,000,000 请求/月 |

## 环境变量

所有平台都需要配置以下环境变量：

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `AGENT_APP_KEY` | ✅ | 智能体广场应用密钥 |
| `AGENT_VISITOR_KEY` | ✅ | 智能体广场访客密钥 |
| `API_KEY` | ❌ | 可选的 API 访问密钥，用于保护接口 |

### 获取密钥

1. 访问 [智能体广场](https://agent.bit.edu.cn)
2. 登录后进入目标应用
3. 在浏览器开发者工具 (F12) 的 Application > Cookies 中找到 `app-visitor-key`
4. 在网络请求中找到 `AppKey`

---

## Cloudflare Workers

### 准备工作

1. 注册 [Cloudflare](https://cloudflare.com) 账号
2. 安装 Wrangler CLI:
   ```bash
   npm install -g wrangler
   ```
3. 登录:
   ```bash
   wrangler login
   ```

### 部署步骤

1. 创建工作目录并复制文件:
   ```bash
   mkdir cloudflare-openai && cd cloudflare-openai
   cp /path/to/edge/cloudflare-worker.js .
   cp /path/to/edge/wrangler.toml .
   ```

2. 设置密钥:
   ```bash
   wrangler secret put AGENT_APP_KEY
   # 输入你的 AGENT_APP_KEY
   
   wrangler secret put AGENT_VISITOR_KEY
   # 输入你的 AGENT_VISITOR_KEY
   
   # 可选: 设置 API_KEY
   wrangler secret put API_KEY
   ```

3. 部署:
   ```bash
   wrangler deploy
   ```

4. 部署完成后会显示你的 Worker URL，如:
   ```
   https://openai-ibit-api.<your-subdomain>.workers.dev
   ```

### 本地测试

```bash
wrangler dev
```

### 自定义域名 (可选)

编辑 `wrangler.toml`:
```toml
routes = [
  { pattern = "api.yourdomain.com/*", zone_name = "yourdomain.com" }
]
```

---

## Deno Deploy

### 准备工作

1. 注册 [Deno Deploy](https://dash.deno.com) 账号
2. 安装 Deno (本地测试用):
   ```bash
   curl -fsSL https://deno.land/install.sh | sh
   ```

### 方法一: GitHub 连接 (推荐)

1. 将 `deno-deploy.ts` 上传到 GitHub 仓库
2. 访问 [Deno Deploy Dashboard](https://dash.deno.com)
3. 创建新项目 → 选择 "Deploy from GitHub"
4. 选择仓库和入口文件 `deno-deploy.ts`
5. 在 Settings → Environment Variables 中添加:
   - `AGENT_APP_KEY`
   - `AGENT_VISITOR_KEY`
   - `API_KEY` (可选)
6. 部署完成

### 方法二: 直接部署

1. 安装 deployctl:
   ```bash
   deno install -Arf jsr:@deno/deployctl
   ```

2. 部署:
   ```bash
   deployctl deploy --project=your-project-name deno-deploy.ts
   ```

### 本地测试

```bash
AGENT_APP_KEY=xxx AGENT_VISITOR_KEY=xxx deno run --allow-net --allow-env deno-deploy.ts
```

---

## Vercel Edge Functions

### 准备工作

1. 注册 [Vercel](https://vercel.com) 账号
2. 安装 Vercel CLI:
   ```bash
   npm install -g vercel
   ```
3. 登录:
   ```bash
   vercel login
   ```

### 部署步骤

1. 复制 vercel 目录:
   ```bash
   cp -r /path/to/edge/vercel ./openai-api
   cd openai-api
   ```

2. 设置环境变量:
   ```bash
   vercel env add AGENT_APP_KEY
   # 选择环境 (Production, Preview, Development) 并输入值
   
   vercel env add AGENT_VISITOR_KEY
   # 选择环境并输入值
   
   # 可选
   vercel env add API_KEY
   ```

3. 部署:
   ```bash
   vercel deploy --prod
   ```

### 本地测试

```bash
vercel dev
```

### 目录结构

```
vercel/
├── api/
│   └── index.js      # Edge Function 入口
└── vercel.json       # Vercel 配置
```

---

## Netlify Edge Functions

### 准备工作

1. 注册 [Netlify](https://netlify.com) 账号
2. 安装 Netlify CLI:
   ```bash
   npm install -g netlify-cli
   ```
3. 登录:
   ```bash
   netlify login
   ```

### 部署步骤

1. 复制 netlify 目录:
   ```bash
   cp -r /path/to/edge/netlify ./openai-api
   cd openai-api
   ```

2. 初始化站点:
   ```bash
   netlify init
   ```

3. 在 Netlify 控制台设置环境变量:
   - Site settings → Environment variables
   - 添加 `AGENT_APP_KEY`, `AGENT_VISITOR_KEY`, `API_KEY` (可选)

4. 部署:
   ```bash
   netlify deploy --prod
   ```

### 本地测试

```bash
netlify dev
```

### 目录结构

```
netlify/
├── netlify/
│   └── edge-functions/
│       └── api.ts    # Edge Function 入口
├── public/
│   └── index.html    # 静态首页
└── netlify.toml      # Netlify 配置
```

---

## API 使用说明

### 基础 URL

部署完成后，你将获得一个 URL，例如:
- Cloudflare: `https://openai-ibit-api.xxx.workers.dev`
- Deno Deploy: `https://xxx.deno.dev`
- Vercel: `https://xxx.vercel.app`
- Netlify: `https://xxx.netlify.app`

### 可用端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 健康检查 |
| GET | `/v1/models` | 获取可用模型列表 |
| POST | `/v1/chat/completions` | 创建聊天补全 |

### 使用示例

#### cURL

```bash
# 获取模型列表
curl https://your-api-url/v1/models \
  -H "Authorization: Bearer your-api-key"

# 非流式请求
curl https://your-api-url/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "你好"}]
  }'

# 流式请求
curl https://your-api-url/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "deepseek-r1",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

#### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-api-url/v1",
    api_key="your-api-key"  # 如果没有设置 API_KEY，可以填任意值
)

# 非流式
response = client.chat.completions.create(
    model="deepseek-r1",
    messages=[{"role": "user", "content": "你好"}]
)
print(response.choices[0].message.content)

# 流式
stream = client.chat.completions.create(
    model="deepseek-r1",
    messages=[{"role": "user", "content": "你好"}],
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

#### JavaScript/Node.js

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'https://your-api-url/v1',
  apiKey: 'your-api-key'
});

// 非流式
const response = await client.chat.completions.create({
  model: 'deepseek-r1',
  messages: [{ role: 'user', content: '你好' }]
});
console.log(response.choices[0].message.content);

// 流式
const stream = await client.chat.completions.create({
  model: 'deepseek-r1',
  messages: [{ role: 'user', content: '你好' }],
  stream: true
});
for await (const chunk of stream) {
  if (chunk.choices[0].delta.content) {
    process.stdout.write(chunk.choices[0].delta.content);
  }
}
```

### 与 NextChat 等应用集成

1. 在设置中填入:
   - API 接口地址: `https://your-api-url`
   - API Key: 你设置的 `API_KEY` (没有设置则随便填)
2. 选择模型: `deepseek-r1`
3. 开始对话

---

## 常见问题

### Q: 为什么不支持 ibit 模型？

A: Edge 版本目前只支持智能体广场的模型 (`deepseek-r1`)，因为 ibit 模型需要登录 BIT 统一身份认证，这需要复杂的 Cookie 管理，不适合无状态的边缘计算环境。

### Q: 如何查看日志？

A: 各平台都提供了日志查看功能:
- Cloudflare: Workers → 你的 Worker → 日志
- Deno Deploy: 项目页面 → Logs
- Vercel: 项目页面 → Deployments → 选择部署 → Functions
- Netlify: 站点页面 → Functions → Logs

### Q: 请求超时怎么办？

A: 边缘函数通常有执行时间限制 (30秒-60秒)。如果 AI 响应太慢，可以:
1. 使用流式响应 (`stream: true`)
2. 减少输入内容长度
3. 检查上游服务状态

### Q: 如何自定义域名？

A: 各平台都支持自定义域名:
- Cloudflare: Workers → 你的 Worker → Triggers → Custom Domains
- Deno Deploy: 项目页面 → Settings → Domains
- Vercel: 项目页面 → Settings → Domains
- Netlify: 站点页面 → Domain settings

### Q: 费用问题？

A: 所有平台都提供免费额度，通常足够个人使用:
- Cloudflare Workers: 每天 100,000 请求免费
- Deno Deploy: 每天 100,000 请求免费
- Vercel: 每月 100,000 请求免费
- Netlify: 每月 1,000,000 请求免费

---

## 技术支持

如有问题，请在 GitHub Issues 中提交。
