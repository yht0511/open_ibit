/**
 * OpenAI-compatible API for Deno Deploy
 * 
 * 部署步骤 / Deployment Steps:
 * 1. 访问 https://dash.deno.com 登录或注册
 * 2. 创建新项目,选择 "Deploy from URL" 或连接 GitHub 仓库
 * 3. 设置环境变量:
 *    - AGENT_APP_KEY: Agent应用密钥
 *    - AGENT_VISITOR_KEY: 访客密钥
 *    - API_KEY: (可选) API访问密钥
 * 4. 部署此文件
 * 
 * 本地测试:
 *   AGENT_APP_KEY=xxx AGENT_VISITOR_KEY=xxx deno run --allow-net --allow-env deno-deploy.ts
 * 
 * 环境变量 / Environment Variables:
 * - AGENT_APP_KEY: Agent应用密钥 (必需)
 * - AGENT_VISITOR_KEY: 访客密钥 (必需)
 * - API_KEY: (可选) API访问密钥
 * - PORT: (可选) 服务端口,默认 8000
 */

// CORS headers
const CORS_HEADERS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Credentials': 'true',
};

// Model configuration
interface ModelConfig {
  name: string;
  owned_by: string;
}

const MODELS: Record<string, ModelConfig> = {
  'deepseek-r1': {
    name: 'DeepSeek-R1',
    owned_by: 'Teclab',
  },
};

// Types
interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string | ContentItem[];
}

interface ContentItem {
  type: 'text' | 'image_url';
  text?: string;
  image_url?: { url: string };
}

interface ChatRequest {
  model: string;
  messages: Message[];
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}

interface HistoryMessage {
  role: string;
  content: string;
}

/**
 * Create a JSON response with CORS headers
 */
function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}

/**
 * Create an error response
 */
function errorResponse(message: string, status = 400): Response {
  return jsonResponse({ error: { message, type: 'invalid_request_error' } }, status);
}

/**
 * Verify API key from Authorization header
 */
function verifyApiKey(request: Request, apiKey: string | undefined): boolean {
  if (!apiKey) return true;
  const authHeader = request.headers.get('Authorization');
  if (!authHeader) return false;
  return authHeader === `Bearer ${apiKey}`;
}

/**
 * Handle OPTIONS preflight requests
 */
function handleCors(): Response {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

/**
 * Extract text content from message content
 */
function extractTextContent(content: string | ContentItem[]): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .filter((item): item is ContentItem & { text: string } => 
        item.type === 'text' && typeof item.text === 'string')
      .map(item => item.text)
      .join(' ');
  }
  return '';
}

/**
 * Build history prompt from conversation history
 */
function buildHistoryPrompt(history: HistoryMessage[]): string {
  if (!history || history.length === 0) return '';
  let res = '[历史对话](请注意这是由程序提供的历史对话功能,不要把它当成用户对话的一部分,不要刻意提及它):';
  for (const msg of history) {
    res += `\n${msg.role}:${msg.content}`;
  }
  res += '\n接下来是用户的新一轮问题:\n';
  return res;
}

/**
 * Process messages to extract query and history
 */
function processMessages(messages: Message[]): { query: string; history: HistoryMessage[] } {
  if (!messages || messages.length === 0) {
    throw new Error('No messages provided');
  }
  
  const lastMessage = messages[messages.length - 1];
  if (lastMessage.role !== 'user') {
    throw new Error('Last message must be from user');
  }
  
  let query = extractTextContent(lastMessage.content);
  const prevMessages = [...messages.slice(0, -1)];
  
  if (prevMessages.length > 0 && prevMessages[0].role === 'system') {
    const systemContent = extractTextContent(prevMessages.shift()!.content);
    query = `[系统提示]:\n${systemContent}\n\n[用户问题]:\n${query}`;
  }
  
  const history: HistoryMessage[] = [];
  for (let i = 0; i < prevMessages.length - 1; i += 2) {
    if (prevMessages[i].role === 'user' && prevMessages[i + 1]?.role === 'assistant') {
      history.push({
        role: 'user',
        content: extractTextContent(prevMessages[i].content),
      });
      history.push({
        role: 'assistant',
        content: extractTextContent(prevMessages[i + 1].content),
      });
    }
  }
  
  return { query, history };
}

/**
 * Agent API client
 */
class AgentClient {
  private appKey: string;
  private visitorKey: string;
  private baseUrl: string;
  private headers: Record<string, string>;
  
  constructor(appKey: string, visitorKey: string) {
    this.appKey = appKey;
    this.visitorKey = visitorKey;
    this.baseUrl = 'https://agent.bit.edu.cn';
    this.headers = {
      'Accept': 'application/json, text/event-stream',
      'Content-Type': 'application/json; charset=utf-8',
      'Origin': 'https://agent.bit.edu.cn',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      'accept-language': 'zh',
      'app-visitor-key': visitorKey,
    };
  }
  
  async createConversation(): Promise<string> {
    const response = await fetch(`${this.baseUrl}/api/proxy/chat/v2/create_conversation`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        AppKey: this.appKey,
        Inputs: {},
      }),
    });
    const data = await response.json();
    return data.Conversation?.AppConversationID;
  }
  
  async deleteConversation(conversationId: string): Promise<void> {
    await fetch(`${this.baseUrl}/api/proxy/chat/v2/delete_conversation`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        AppKey: this.appKey,
        AppConversationID: conversationId,
      }),
    });
  }
  
  async chat(query: string, history: HistoryMessage[] = []): Promise<{ content: string; reasoningContent: string }> {
    const conversationId = await this.createConversation();
    const fullQuery = buildHistoryPrompt(history) + query;
    
    try {
      const response = await fetch(`${this.baseUrl}/api/proxy/chat/v2/chat_query`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          Query: fullQuery,
          AppConversationID: conversationId,
          AppKey: this.appKey,
          QueryExtends: { Files: [] },
        }),
      });
      
      const text = await response.text();
      let content = '';
      let reasoningContent = '';
      
      const lines = text.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.event === 'think_message' && data.answer) {
              reasoningContent += data.answer;
            } else if (data.event === 'message' && data.answer) {
              content += data.answer;
            }
          } catch {
            // Skip invalid JSON
          }
        }
      }
      
      return { content, reasoningContent };
    } finally {
      await this.deleteConversation(conversationId);
    }
  }
  
  async *chatStream(query: string, history: HistoryMessage[] = []): AsyncGenerator<{ content: string | null; reasoningContent: string | null }> {
    const conversationId = await this.createConversation();
    const fullQuery = buildHistoryPrompt(history) + query;
    
    try {
      const response = await fetch(`${this.baseUrl}/api/proxy/chat/v2/chat_query`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          Query: fullQuery,
          AppConversationID: conversationId,
          AppKey: this.appKey,
          QueryExtends: { Files: [] },
        }),
      });
      
      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.event === 'think_message' && data.answer) {
                yield { content: null, reasoningContent: data.answer };
              } else if (data.event === 'message' && data.answer) {
                yield { content: data.answer, reasoningContent: null };
              }
            } catch {
              // Skip invalid JSON
            }
          }
        }
      }
    } finally {
      await this.deleteConversation(conversationId);
    }
  }
}

/**
 * Handle GET /v1/models
 */
function handleModels(): Response {
  const models = Object.keys(MODELS).map(id => ({
    id,
    object: 'model',
    created: Math.floor(Date.now() / 1000),
    owned_by: MODELS[id].owned_by,
  }));
  return jsonResponse({ object: 'list', data: models });
}

/**
 * Handle POST /v1/chat/completions
 */
async function handleChatCompletions(request: Request): Promise<Response> {
  const agentAppKey = Deno.env.get('AGENT_APP_KEY');
  const agentVisitorKey = Deno.env.get('AGENT_VISITOR_KEY');
  
  if (!agentAppKey || !agentVisitorKey) {
    return errorResponse('Server configuration error: Missing AGENT_APP_KEY or AGENT_VISITOR_KEY', 500);
  }
  
  try {
    const body: ChatRequest = await request.json();
    const { model, messages, stream } = body;
    
    if (!MODELS[model]) {
      return errorResponse(`Model ${model} not supported. Available models: ${Object.keys(MODELS).join(', ')}`);
    }
    
    const { query, history } = processMessages(messages);
    const client = new AgentClient(agentAppKey, agentVisitorKey);
    
    if (stream) {
      // Streaming response
      const encoder = new TextEncoder();
      
      const stream = new ReadableStream({
        async start(controller) {
          try {
            for await (const chunk of client.chatStream(query, history)) {
              let data = null;
              
              if (chunk.reasoningContent) {
                data = {
                  id: `chatcmpl-${Date.now()}`,
                  object: 'chat.completion.chunk',
                  created: Math.floor(Date.now() / 1000),
                  model,
                  choices: [{
                    index: 0,
                    delta: { reasoning_content: chunk.reasoningContent },
                    finish_reason: null,
                  }],
                };
              } else if (chunk.content) {
                data = {
                  id: `chatcmpl-${Date.now()}`,
                  object: 'chat.completion.chunk',
                  created: Math.floor(Date.now() / 1000),
                  model,
                  choices: [{
                    index: 0,
                    delta: { content: chunk.content },
                    finish_reason: null,
                  }],
                };
              }
              
              if (data) {
                controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
              }
            }
            
            // Send final chunk
            const finalChunk = {
              id: `chatcmpl-${Date.now()}`,
              object: 'chat.completion.chunk',
              created: Math.floor(Date.now() / 1000),
              model,
              choices: [{
                index: 0,
                delta: {},
                finish_reason: 'stop',
              }],
            };
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(finalChunk)}\n\n`));
            controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          } catch (error) {
            console.error('Stream error:', error);
          } finally {
            controller.close();
          }
        },
      });
      
      return new Response(stream, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive',
          ...CORS_HEADERS,
        },
      });
    } else {
      // Non-streaming response
      const { content, reasoningContent } = await client.chat(query, history);
      
      const response = {
        id: `chatcmpl-${Date.now()}`,
        object: 'chat.completion',
        created: Math.floor(Date.now() / 1000),
        model,
        choices: [{
          index: 0,
          message: {
            role: 'assistant',
            content,
            ...(reasoningContent && { reasoning_content: reasoningContent }),
          },
          finish_reason: 'stop',
        }],
        usage: {
          prompt_tokens: 0,
          completion_tokens: 0,
          total_tokens: 0,
        },
      };
      
      return jsonResponse(response);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return errorResponse(message, 500);
  }
}

/**
 * Main request handler
 */
async function handler(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  // Handle CORS preflight
  if (method === 'OPTIONS') {
    return handleCors();
  }
  
  // Verify API key if configured
  const apiKey = Deno.env.get('API_KEY');
  if (!verifyApiKey(request, apiKey)) {
    return errorResponse('Unauthorized', 403);
  }
  
  // Route requests
  if (path === '/v1/models' && method === 'GET') {
    return handleModels();
  }
  
  if (path === '/v1/chat/completions' && method === 'POST') {
    return handleChatCompletions(request);
  }
  
  // Health check
  if (path === '/' || path === '/health') {
    return jsonResponse({ status: 'ok', message: 'OpenAI-compatible API (Deno Deploy)' });
  }
  
  return errorResponse('Not Found', 404);
}

// Start server
const port = parseInt(Deno.env.get('PORT') || '8000');
console.log(`Server running on http://localhost:${port}`);
Deno.serve({ port }, handler);
