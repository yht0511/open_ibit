"""
server.py - OpenAI 兼容的 API 服务器

本模块是项目的核心入口，基于 FastAPI 框架实现了与 OpenAI API 兼容的接口服务。
主要功能：
1. 提供 /v1/models 端点，返回可用模型列表
2. 提供 /v1/chat/completions 端点，支持流式和非流式对话补全
3. 可选的 API Key 验证机制
4. 调用统计和费用计算功能

依赖模块：
- settings: 配置管理和模型实例
- models.ibit: iBit 平台模型接口
- models.agent: 智能体广场模型接口
"""

import json  # JSON 数据解析和序列化
import threading  # 多线程支持，用于统计信息定时打印
import time  # 时间处理，用于时间戳和耗时计算
import uvicorn  # ASGI 服务器，用于运行 FastAPI 应用
from pydantic import BaseModel, Field  # 数据模型定义和验证
from fastapi import FastAPI, HTTPException, Response, Depends, Header  # FastAPI 核心组件
from fastapi.middleware.cors import CORSMiddleware  # 跨域资源共享中间件
from typing import Dict, List, Literal, Optional, Union  # 类型注解
from sse_starlette.sse import EventSourceResponse  # Server-Sent Events 响应，用于流式输出
import asyncio  # 异步IO支持
import settings  # 导入配置模块，包含模型实例和配置参数

# 创建 FastAPI 应用程序实例
app = FastAPI()

# 配置 CORS 跨域中间件
# 允许所有来源、方法和头部，以支持各种客户端（如 NextChat、OpenAI SDK 等）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

def verify_api_key(Authorization: str = Header(...)):
    """
    API Key 验证函数
    
    验证请求头中的 Authorization 字段是否包含有效的 API Key。
    支持 Bearer Token 格式：Bearer <api_key>
    
    Args:
        Authorization: HTTP 请求头中的 Authorization 字段
        
    Returns:
        bool: 验证成功返回 True
        
    Raises:
        HTTPException: 验证失败时返回 403 状态码
    """
    if Authorization == "Bearer " + settings.api_key or not settings.api_key:
        return True
    raise HTTPException(status_code=403, detail="Unauthorized")

# 根据配置决定是否启用 API Key 验证
if settings.api_key:
    # 如果设置了 API Key，则添加验证依赖
    dependencies = [Depends(verify_api_key)]
else:
    # 未设置 API Key 时，不进行验证
    dependencies = None

# ==================== 数据模型定义 ====================

class ModelCard(BaseModel):
    """
    模型信息卡片
    
    表示单个模型的元数据，用于 /v1/models 端点返回。
    遵循 OpenAI API 规范。
    
    Attributes:
        id: 模型唯一标识符
        object: 对象类型，固定为 "model"
        created: 模型创建时间戳
        owned_by: 模型所有者
        root: 根模型（可选）
        parent: 父模型（可选）
        permission: 权限列表（可选）
    """
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "owner"
    root: Optional[str] = None
    parent: Optional[str] = None
    permission: Optional[list] = None


class ModelList(BaseModel):
    """
    模型列表
    
    包含所有可用模型的列表，用于 /v1/models 端点返回。
    
    Attributes:
        object: 对象类型，固定为 "list"
        data: ModelCard 对象列表
    """
    object: str = "list"
    data: List[ModelCard] = []


class ContentItem(BaseModel):
    """
    内容项（支持多模态）
    
    表示消息中的单个内容项，支持文本和图片 URL 两种类型。
    用于支持多模态对话场景。
    
    Attributes:
        type: 内容类型，"text" 表示文本，"image_url" 表示图片
        text: 文本内容（当 type 为 "text" 时使用）
        image_url: 图片 URL 信息（当 type 为 "image_url" 时使用）
    """
    type: Literal["text", "image_url"]
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None


class ChatMessage(BaseModel):
    """
    聊天消息
    
    表示对话中的单条消息，包含角色和内容信息。
    支持思维链（reasoning_content）输出。
    
    Attributes:
        role: 消息角色，可选 "user"（用户）、"assistant"（助手）、"system"（系统）
        content: 消息内容，可以是纯文本字符串或 ContentItem 列表（多模态）
        reasoning_content: 推理/思考过程内容，用于展示模型的思维链
    """
    role: Literal["user", "assistant", "system"]
    content: Union[str, List[ContentItem]]
    reasoning_content: str = None


class DeltaMessage(BaseModel):
    """
    增量消息（流式输出专用）
    
    用于流式响应中传输增量内容，只包含本次新增的部分。
    
    Attributes:
        role: 消息角色（可选，通常只在第一个 chunk 中发送）
        content: 增量文本内容（可选）
        reasoning_content: 增量推理内容（可选）
    """
    role: Optional[Literal["user", "assistant", "system"]] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """
    对话补全请求
    
    客户端发送的对话请求数据结构，遵循 OpenAI API 规范。
    
    Attributes:
        model: 要使用的模型名称（如 "ibit"、"deepseek-r1"）
        messages: 对话消息历史列表
        temperature: 生成温度（可选），控制输出随机性
        top_p: 核采样参数（可选）
        max_length: 最大生成长度（可选）
        stream: 是否使用流式输出，默认 False
    """
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_length: Optional[int] = None
    stream: Optional[bool] = False


class ChatCompletionResponseChoice(BaseModel):
    """
    对话补全响应选项（非流式）
    
    表示一个完整的对话补全响应选项。
    
    Attributes:
        index: 选项索引
        message: 完整的响应消息
        finish_reason: 结束原因，"stop" 表示正常结束，"length" 表示达到长度限制
    """
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length"]


class ChatCompletionResponseStreamChoice(BaseModel):
    """
    对话补全响应选项（流式）
    
    用于流式响应中的单个 chunk。
    
    Attributes:
        index: 选项索引
        delta: 增量消息内容
        finish_reason: 结束原因（可选），最后一个 chunk 才会有值
    """
    index: int
    delta: DeltaMessage
    finish_reason: Optional[Literal["stop", "length"]]


class ChatCompletionResponse(BaseModel):
    """
    对话补全响应
    
    完整的对话补全响应数据结构，支持流式和非流式两种格式。
    
    Attributes:
        model: 使用的模型名称
        object: 响应类型，"chat.completion" 或 "chat.completion.chunk"
        choices: 响应选项列表
        created: 响应创建时间戳
    """
    model: str
    object: Literal["chat.completion", "chat.completion.chunk"]
    choices: List[Union[ChatCompletionResponseChoice, ChatCompletionResponseStreamChoice]]
    created: Optional[int] = Field(default_factory=lambda: int(time.time()))

# ==================== API 端点定义 ====================

@app.get("/v1/models", response_model=ModelList, dependencies=dependencies)
async def list_models():
    """
    获取可用模型列表
    
    返回所有已配置的模型信息，遵循 OpenAI API 规范。
    
    Returns:
        ModelList: 包含所有可用模型的 ModelCard 列表
    """
    global Models
    cards = []
    for model in Models:
        cards.append(ModelCard(id=model, owned_by="Teclab"))
    return ModelList(data=cards)


def extract_text_content(content: Union[str, List[ContentItem]]) -> str:
    """
    提取消息内容中的纯文本
    
    处理多模态消息格式，从中提取文本内容。
    支持纯字符串和 ContentItem 列表两种输入格式。
    
    Args:
        content: 消息内容，可以是字符串或 ContentItem 列表
        
    Returns:
        str: 提取出的纯文本内容，多个文本项用空格连接
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if item.type == "text" and item.text:
                text_parts.append(item.text)
        return " ".join(text_parts)
    return ""

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse, dependencies=dependencies)
async def create_chat_completion(request: ChatCompletionRequest, response: Response):
    """
    创建对话补全
    
    处理用户的对话请求，支持流式和非流式两种响应模式。
    遵循 OpenAI API 规范，可直接与 OpenAI SDK 或 NextChat 等客户端对接。
    
    处理流程：
    1. 验证请求的模型是否支持
    2. 验证最后一条消息是否来自用户
    3. 提取查询内容和历史对话
    4. 如果存在系统提示，将其合并到查询中
    5. 根据 stream 参数选择流式或非流式调用模型
    6. 记录调用日志和费用统计
    
    Args:
        request: 对话补全请求，包含模型、消息历史等参数
        response: FastAPI Response 对象，用于设置响应头
        
    Returns:
        ChatCompletionResponse: 对话补全响应
        或 EventSourceResponse: 流式响应（当 stream=True 时）
        
    Raises:
        HTTPException: 模型不支持或请求格式错误时返回 400 状态码
    """
    global Models
    # 验证请求的模型是否在支持列表中
    if request.model not in settings.models:
        raise HTTPException(status_code=400, detail=f"Model {request.model} not supported, suppored models: {settings.models.keys()}")
    
    # 验证最后一条消息必须来自用户
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Invalid request")
    
    # 提取用户查询内容
    query = extract_text_content(request.messages[-1].content)
    
    # 打印请求日志
    print("-----------------------Received Query-----------------------")
    print(f"Model: {request.model}")
    print(f"Stream: {request.stream}")
    print(f"Query: {query}")
    print("Timestamp: ", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    print("------------------------------------------------------------")
   
    # 处理历史消息和系统提示
    prev_messages = request.messages[:-1]
    if len(prev_messages) > 0 and prev_messages[0].role == "system":
        # 如果第一条消息是系统提示，将其合并到查询中
        system_content = extract_text_content(prev_messages.pop(0).content)
        query = f"[系统提示]:\n{system_content}\n\n[用户问题]:\n{query}"
    
    # 构建历史对话列表（用户-助手成对组织）
    history = []
    if len(prev_messages) % 2 == 0:
        for i in range(0, len(prev_messages)-1, 2):
            if prev_messages[i].role == "user" and prev_messages[i+1].role == "assistant":
                user_content = extract_text_content(prev_messages[i].content)
                assistant_content = extract_text_content(prev_messages[i+1].content)
                history.append({"role": "user", "content": user_content})
                history.append({"role": "assistant", "content": assistant_content})
    
    # 根据 stream 参数选择响应模式
    if request.stream:
        # 流式响应：设置 SSE 响应头并返回事件流
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Content-Type"] = "text/event-stream"
        generate = predict(query, history, request.model)
        return EventSourceResponse(generate, media_type="text/event-stream")
    
    # 非流式响应：等待模型完整响应后返回
    reasoning_content, content = await asyncio.to_thread(Models[request.model]["model"].chat, query, history=history)
    
    # 打印响应日志
    print("-----------------------Response Content---------------------")
    print(f"Model: {request.model}")
    print(f"Stream: false")
    print(f"Query: {query}")
    print(f"Response: {content.strip()}")
    print("Timestamp: ", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    print("------------------------------------------------------------")
    
    # 计算费用并记录
    calc_price(Models[request.model], query, content+reasoning_content)
    
    # 构造响应数据
    choice_data = ChatCompletionResponseChoice(
        index=0,
        message=ChatMessage(role="assistant", content=content, reasoning_content=reasoning_content),
        finish_reason="stop"
    )

    return ChatCompletionResponse(model=request.model, choices=[choice_data], object="chat.completion")

def predict(query: str, history: List[List[str]], model_id: str):
    """
    流式响应生成器
    
    生成 Server-Sent Events (SSE) 格式的流式响应。
    从模型获取流式输出，将每个 chunk 转换为 OpenAI 兼容的格式发送。
    
    Args:
        query: 用户查询内容
        history: 历史对话列表
        model_id: 使用的模型标识符
        
    Yields:
        str: JSON 格式的响应 chunk，最后以 '[DONE]' 结束
    """
    global Models
    # 调用模型的流式接口获取响应
    response = Models[model_id]["model"].chat_stream(query, history=history)
    
    # 累积完整响应内容（用于日志和费用计算）
    content = ""
    reasoning_content = ""
    
    # 逐 chunk 处理并转发
    for chunk in response:
        if chunk.get("content", ""): content += chunk.get("content", "")
        if chunk.get("reasoning_content", ""): reasoning_content += chunk.get("reasoning_content", "")
        
        # 构造流式响应 chunk
        choice_data = ChatCompletionResponseStreamChoice(
            index=0,
            delta=DeltaMessage(content=chunk["content"], reasoning_content=chunk["reasoning_content"]),
            finish_reason=None
        )
        chunk = ChatCompletionResponse(model=model_id, choices=[choice_data], object="chat.completion.chunk")
        yield "{}".format(chunk.json(exclude_unset=True))
    
    # 发送结束标记 chunk
    choice_data = ChatCompletionResponseStreamChoice(
        index=0,
        delta=DeltaMessage(),
        finish_reason="stop"
    )
    chunk = ChatCompletionResponse(model=model_id, choices=[choice_data], object="chat.completion.chunk")
    yield "{}".format(chunk.json(exclude_unset=True))
    yield '[DONE]'
    
    # 打印响应日志
    print("-----------------------Response Content---------------------")
    print(f"Model: {model_id}")
    print(f"Stream: true")
    print(f"Query: {query}")
    print(f"Response: {content.strip()}")
    print("Timestamp: ", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    print("------------------------------------------------------------")
    
    # 计算费用
    calc_price(Models[model_id], query, content+reasoning_content)

def calc_price(model, _in, _out):
    """
    计算并记录调用费用
    
    根据模型配置的价格和分词器计算本次调用的费用，
    并将统计数据写入日志文件。
    
    费用计算公式：
    总费用 = (输入Token数 / 1000000) × 输入单价 + (输出Token数 / 1000000) × 输出单价
    
    Args:
        model: 模型配置字典，包含 price、tokenizer、name 等字段
        _in: 输入文本（用于计算输入 Token 数）
        _out: 输出文本（用于计算输出 Token 数）
    """
    if "price" in model and "tokenizer" in model:
        # 获取价格配置（每百万 Token 的价格）
        price_in = model["price"]["input"]
        price_out = model["price"]["output"]
        
        # 使用分词器计算 Token 数量
        in_tokens = model["tokenizer"](_in)
        out_tokens = model["tokenizer"](_out)
        
        # 计算总费用
        total_price = (in_tokens / 1000000) * price_in + (out_tokens / 1000000) * price_out
        
        # 写入文本日志
        with open(settings.price_log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Model: {model['name']}, Input Tokens: {in_tokens}, Output Tokens: {out_tokens}, Price: ¥{total_price:.6f}\n")
        
        # 更新 JSON 统计文件
        f = open(settings.price_log_json,"r", encoding="utf-8")
        data = json.load(f)
        f.close()
        
        # 获取或初始化该模型的统计数据
        _model_data = data.get(model["name"], {"input_tokens": 0, "output_tokens": 0, "total_price": 0.0, "calls": 0})
        _model_data["calls"] += 1  # 增加调用次数
        _model_data["input_tokens"] += in_tokens
        _model_data["output_tokens"] += out_tokens
        _model_data["total_price"] += total_price
        data[model["name"]] = _model_data
        
        # 写回 JSON 文件
        f = open(settings.price_log_json,"w", encoding="utf-8")
        json.dump(data, f, indent=4)
        f.close()

def print_statistics():
    """
    定时打印统计信息
    
    在后台线程中周期性运行，定期打印调用统计数据，包括：
    - 总在线时间
    - 总调用次数
    - 总费用
    - 各模型的详细统计（调用次数、Token 用量、费用）
    
    打印间隔由 settings.print_statistics_interval 控制。
    """
    while True:
        try:
            time.sleep(settings.print_statistics_interval)
            with open(settings.price_log_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                print("\n------------------------------------------------------------------------------------")
                print("统计数据")
                print("------------------------------------------------------------------------------------")
                print(f"总在线时间: {time.strftime('%H小时%M分钟%S秒', time.gmtime(time.time() - start_time))}")
                total_calls = sum(stats.get("calls", 0) for stats in data.values())
                print(f"总调用数: {total_calls}")
                print(f"总花费: ¥{sum(stats.get('total_price', 0.0) for stats in data.values()):.4f}")
                print("模型名称                          调用次数    输入Token     输出Token     Token总量     累计花费")
                for model, stats in data.items():
                    calls = stats.get("calls", 0)
                    input_tokens = stats.get("input_tokens", 0)
                    output_tokens = stats.get("output_tokens", 0)
                    total_tokens = input_tokens + output_tokens
                    total_price = stats.get("total_price", 0.0)
                    print(f"{model:<35} {calls:>8} {input_tokens:>12} {output_tokens:>12} {total_tokens:>12}     ¥{total_price:.4f}")
                print("------------------------------------------------------------------------------------")
        except Exception as e:
            print(f"统计信息读取错误: {e}")

# ==================== 主程序入口 ====================

if __name__ == "__main__":
    """
    应用程序主入口
    
    启动流程：
    1. 记录启动时间
    2. 初始化所有配置的模型（登录、建立连接等）
    3. 启动统计信息打印线程
    4. 启动 FastAPI 服务器（监听 0.0.0.0:8000）
    """
    start_time = time.time()  # 记录启动时间，用于计算在线时长
    
    print("正在初始化模型...")
    Models = settings.models  # 获取已配置的模型字典
    
    # 依次初始化每个模型
    for model in Models:
        print(f"载入: {model}")
        Models[model]["model"].init()  # 调用模型的初始化方法
    
    print(f"各模型初始化成功(用时{round(time.time()-start_time,1)}s),启动 FastAPI 应用程序...")
    
    # 启动费用统计线程（守护线程，随主程序退出）
    threading.Thread(target=print_statistics, daemon=True).start()
    
    # 启动 FastAPI 服务器
    uvicorn.run(app, host='0.0.0.0', port=8000, workers=1)
