import json
import time
import uvicorn
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Response, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List, Literal, Optional, Union
from sse_starlette.sse import ServerSentEvent, EventSourceResponse
from ibit import iBit
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

# 定义ChatMessage 数据模型
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

# 定义DeltaMessage 数据模型
class DeltaMessage(BaseModel):
    role: Optional[Literal["user", "assistant", "system"]] = None
    content: Optional[str] = None

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
    model_card = ModelCard(id="deepseek-r1")
    return ModelList(data=[model_card])

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse, dependencies=[Depends(verify_api_key)])
async def create_chat_completion(request: ChatCompletionRequest, response: Response):
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="Invalid request")
    query = request.messages[-1].content
   
    prev_messages = request.messages[:-1]
    if len(prev_messages) > 0 and prev_messages[0].role == "system":
        query = f"[系统提示]:\n{prev_messages.pop(0).content}\n\n[用户问题]:\n{query}"
    
    history = []
    if len(prev_messages) % 2 == 0:
        for i in range(0, len(prev_messages)-1):
            if prev_messages[i].role == "user" and prev_messages[i+1].role == "assistant":
                history.append({"role": "user", "content": prev_messages[i].content})
                history.append({"role": "assistant", "content": prev_messages[i+1].content})
                
    if request.stream:
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Content-Type"] = "text/event-stream"
        
        generate = predict(query, history, request.model)
        return EventSourceResponse(generate, media_type="text/event-stream")
    
    response = ibit.chat(query, history=history)
    choice_data = ChatCompletionResponseChoice(
        index=0,
        message=ChatMessage(role="assistant", content=response),
        finish_reason="stop"
    )

    return ChatCompletionResponse(model=request.model, choices=[choice_data], object="chat.completion")

def predict(query: str, history: List[List[str]], model_id: str):
    global ibit
    response = ibit.chat_stream(query, history=history)  # 获取流式输出
    
    for chunk in response:
        choice_data = ChatCompletionResponseStreamChoice(
            index=0,
            delta=DeltaMessage(content=chunk),
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

if __name__ == "__main__":
    t = time.time()
    print("正在登录账号...")  # 提示信息
    ibit = iBit(settings.username,settings.password)  # 初始化 iBit 实例
    print(f"账号登录成功(用时{round(time.time()-t,1)}s),启动 FastAPI 应用程序...")
    uvicorn.run(app,host='0.0.0.0',port=8000,workers=1)  # 启动 FastAPI 应用程序
