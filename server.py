import json
import threading
import time
import uvicorn
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Literal, Optional, Union
from sse_starlette.sse import EventSourceResponse
import asyncio
import settings  # 导入 iBit 类

app = FastAPI() # 创建 FastAPI 应用程序
app.add_middleware(     # 使用 add_middleware 方法向 FastAPI 应用程序添加中间件
    CORSMiddleware,     
    allow_origins=["*"], # 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_api_key(Authorization: str = Header(...)):
    if Authorization == "Bearer " + settings.api_key or not settings.api_key:
        return True
    raise HTTPException(status_code=403, detail="Unauthorized")

if settings.api_key:
    # 依赖
    dependencies = [Depends(verify_api_key)]
else:
    dependencies = None

# 定义 ModelCard 数据模型
class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "owner"
    root: Optional[str] = None
    parent: Optional[str] = None
    permission: Optional[list] = None

# 定义 ModelList 数据模型
class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelCard] = []

# 定义内容项数据模型（支持多模态）
class ContentItem(BaseModel):
    type: Literal["text", "image_url"]
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None
    
# 定义ChatMessage 数据模型
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: Union[str, List[ContentItem]]
    reasoning_content: str = None

# 定义DeltaMessage 数据模型
class DeltaMessage(BaseModel):
    role: Optional[Literal["user", "assistant", "system"]] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None

# 定义ChatCompletionRequest 数据模型
class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_length: Optional[int] = None
    stream: Optional[bool] = False

# 定义ChatCompletionResponseChoice 数据模型
class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length"]

# 定义ChatCompletionResponseStreamChoice数据模型
class ChatCompletionResponseStreamChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[Literal["stop", "length"]]

# 定义ChatCompletionResponse数据模型
class ChatCompletionResponse(BaseModel):
    model: str
    object: Literal["chat.completion", "chat.completion.chunk"]
    choices: List[Union[ChatCompletionResponseChoice, ChatCompletionResponseStreamChoice]]
    created: Optional[int] = Field(default_factory=lambda: int(time.time()))

@app.get("/v1/models", response_model=ModelList, dependencies=dependencies)
async def list_models():
    global Models
    cards = []
    for model in Models:
        cards.append(ModelCard(id=model, owned_by="Teclab"))
    return ModelList(data=cards)

# 处理content字段，提取文本内容
def extract_text_content(content: Union[str, List[ContentItem]]) -> str:
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
    global Models
    if request.model not in settings.models:
        raise HTTPException(status_code=400, detail=f"Model {request.model} not supported, suppored models: {settings.models.keys()}")
    
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Invalid request")
    
    query = extract_text_content(request.messages[-1].content)
    print("-----------------------Received Query-----------------------")
    print(f"Model: {request.model}")
    print(f"Stream: {request.stream}")
    print(f"Query: {query}")
    print("Timestamp: ", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    print("------------------------------------------------------------")
   
    prev_messages = request.messages[:-1]
    if len(prev_messages) > 0 and prev_messages[0].role == "system":
        system_content = extract_text_content(prev_messages.pop(0).content)
        query = f"[系统提示]:\n{system_content}\n\n[用户问题]:\n{query}"
    
    history = []
    if len(prev_messages) % 2 == 0:
        for i in range(0, len(prev_messages)-1, 2):
            if prev_messages[i].role == "user" and prev_messages[i+1].role == "assistant":
                user_content = extract_text_content(prev_messages[i].content)
                assistant_content = extract_text_content(prev_messages[i+1].content)
                history.append({"role": "user", "content": user_content})
                history.append({"role": "assistant", "content": assistant_content})
    
    if request.stream:
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Content-Type"] = "text/event-stream"
        generate = predict(query, history, request.model)
        return EventSourceResponse(generate, media_type="text/event-stream")
    
    reasoning_content, content = await asyncio.to_thread(Models[request.model]["model"].chat, query, history=history)
    # print(f"User: {query}\nAssistant: {content.strip()}")
    print("-----------------------Response Content---------------------")
    print(f"Model: {request.model}")
    print(f"Stream: false")
    print(f"Query: {query}")
    print(f"Response: {content.strip()}")
    print("Timestamp: ", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    print("------------------------------------------------------------")
    
    calc_price(Models[request.model], query, content+reasoning_content)
    choice_data = ChatCompletionResponseChoice(
        index=0,
        message=ChatMessage(role="assistant", content=content, reasoning_content=reasoning_content),
        finish_reason="stop"
    )

    return ChatCompletionResponse(model=request.model, choices=[choice_data], object="chat.completion")

def predict(query: str, history: List[List[str]], model_id: str):
    global Models
    response = Models[model_id]["model"].chat_stream(query, history=history)  # 获取流式输出
    
    content = ""
    reasoning_content = ""
    for chunk in response:
        content += chunk.get("content", "")
        reasoning_content += chunk.get("reasoning_content", "")
        choice_data = ChatCompletionResponseStreamChoice(
            index=0,
            delta=DeltaMessage(content=chunk["content"], reasoning_content=chunk["reasoning_content"]),
            finish_reason=None
        )
        chunk = ChatCompletionResponse(model=model_id, choices=[choice_data], object="chat.completion.chunk")
        yield "{}".format(chunk.json(exclude_unset=True))
        
    
    choice_data = ChatCompletionResponseStreamChoice(
        index=0,
        delta=DeltaMessage(),
        finish_reason="stop"
    )
    chunk = ChatCompletionResponse(model=model_id, choices=[choice_data], object="chat.completion.chunk")
    yield "{}".format(chunk.json(exclude_unset=True))
    yield '[DONE]'
    print("-----------------------Response Content---------------------")
    print(f"Model: {model_id}")
    print(f"Stream: true")
    print(f"Query: {query}")
    print(f"Response: {content.strip()}")
    print("Timestamp: ", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))
    print("------------------------------------------------------------")
    calc_price(Models[model_id], query, content+reasoning_content)

def calc_price(model,_in,_out):
    if "price" in model and "tokenizer" in model:
        price_in = model["price"]["input"]
        price_out = model["price"]["output"]
        in_tokens = model["tokenizer"](_in)
        out_tokens = model["tokenizer"](_out)
        total_price = (in_tokens / 1000000) * price_in + (out_tokens / 1000000) * price_out
        with open(settings.price_log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Model: {model['name']}, Input Tokens: {in_tokens}, Output Tokens: {out_tokens}, Price: ¥{total_price:.6f}\n")
        f = open(settings.price_log_json,"r", encoding="utf-8")
        data = json.load(f)
        f.close()
        _model_data = data.get(model["name"], {"input_tokens": 0, "output_tokens": 0, "total_price": 0.0, "calls": 0})
        _model_data["calls"] += 1  # 增加调用次数
        _model_data["input_tokens"] += in_tokens
        _model_data["output_tokens"] += out_tokens
        _model_data["total_price"] += total_price
        data[model["name"]] = _model_data
        f = open(settings.price_log_json,"w", encoding="utf-8")
        json.dump(data, f, indent=4)
        f.close()

def print_statistics():
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
                print(f"总花费: {sum(stats.get('total_price', 0.0) for stats in data.values()):.4f}¥")
                print("模型名称                          调用次数    输入Token     输出Token     Token总量     累计花费")
                for model, stats in data.items():
                    calls = stats.get("calls", 0)
                    input_tokens = stats.get("input_tokens", 0)
                    output_tokens = stats.get("output_tokens", 0)
                    total_tokens = input_tokens + output_tokens
                    total_price = stats.get("total_price", 0.0)
                    print(f"{model:<35} {calls:>8} {input_tokens:>12} {output_tokens:>12} {total_tokens:>12}     {total_price:.4f}¥")
                print("------------------------------------------------------------------------------------")
        except Exception as e:
            print(f"统计信息读取错误: {e}")

if __name__ == "__main__":
    start_time = time.time()
    print("正在初始化模型...")  # 提示信息
    Models = settings.models
    for model in Models:
        print(f"载入: {model}")
        Models[model]["model"].init()  # 初始化模型
    print(f"各模型初始化成功(用时{round(time.time()-start_time,1)}s),启动 FastAPI 应用程序...")
    # 启动费用统计线程
    threading.Thread(target=print_statistics, daemon=True).start()
    # 启动 FastAPI 应用程序
    uvicorn.run(app,host='0.0.0.0',port=8000,workers=1)  # 启动 FastAPI 应用程序
