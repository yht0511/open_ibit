/**
 * OpenAI-compatible API for Vercel Edge Functions
 * 
 * 部署步骤 / Deployment Steps:
 * 1. 安装 Vercel CLI: npm install -g vercel
 * 2. 登录 Vercel: vercel login
 * 3. 复制 vercel 目录到项目根目录
 * 4. 设置环境变量:
 *    vercel env add AGENT_APP_KEY
 *    vercel env add AGENT_VISITOR_KEY
 *    vercel env add API_KEY (可选)
 * 5. 部署: vercel deploy
 * 
 * 环境变量 / Environment Variables:
 * - AGENT_APP_KEY: Agent应用密钥 (必需)
 * - AGENT_VISITOR_KEY: 访客密钥 (必需)
 * - API_KEY: (可选) API访问密钥
 */

export const config = {
  runtime: 'edge',
};

// CORS headers
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Credentials': 'true',
};

// Model configuration
const MODELS = {
  'deepseek-r1': {
    name: 'DeepSeek-R1',
    owned_by: 'Teclab',
  },
};

/**
 * Create a JSON response with CORS headers
 */
function jsonResponse(data, status = 200) {
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
function errorResponse(message, status = 400) {
  return jsonResponse({ error: { message, type: 'invalid_request_error' } }, status);
}

/**
 * Verify API key from Authorization header
 */
function verifyApiKey(request, apiKey) {
  if (!apiKey) return true;
  const authHeader = request.headers.get('Authorization');
  if (!authHeader) return false;
  return authHeader === `Bearer ${apiKey}`;
}

/**
 * Handle OPTIONS preflight requests
 */
function handleCors() {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

/**
 * Extract text content from message content
 */
function extractTextContent(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .filter(item => item.type === 'text' && item.text)
      .map(item => item.text)
      .join(' ');
  }
  return '';
}

/**
 * Build history prompt from conversation history
 */
function buildHistoryPrompt(history) {
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
function processMessages(messages) {
  if (!messages || messages.length === 0) {
    throw new Error('No messages provided');
  }
  
  const lastMessage = messages[messages.length - 1];
  if (lastMessage.role !== 'user') {
    throw new Error('Last message must be from user');
  }
  
  let query = extractTextContent(lastMessage.content);
  const prevMessages = messages.slice(0, -1);
  
  if (prevMessages.length > 0 && prevMessages[0].role === 'system') {
    const systemContent = extractTextContent(prevMessages.shift().content);
    query = `[系统提示]:\n${systemContent}\n\n[用户问题]:\n${query}`;
  }
  
  const history = [];
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
  constructor(appKey, visitorKey) {
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
  
  async createConversation() {
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
  
  async deleteConversation(conversationId) {
    await fetch(`${this.baseUrl}/api/proxy/chat/v2/delete_conversation`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({
        AppKey: this.appKey,
        AppConversationID: conversationId,
      }),
    });
  }
  
  async chat(query, history = []) {
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
}

/**
 * Handle GET /v1/models
 */
function handleModels() {
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
async function handleChatCompletions(request) {
  const agentAppKey = process.env.AGENT_APP_KEY;
  const agentVisitorKey = process.env.AGENT_VISITOR_KEY;
  
  if (!agentAppKey || !agentVisitorKey) {
    return errorResponse('Server configuration error: Missing AGENT_APP_KEY or AGENT_VISITOR_KEY', 500);
  }
  
  try {
    const body = await request.json();
    const { model, messages, stream } = body;
    
    if (!MODELS[model]) {
      return errorResponse(`Model ${model} not supported. Available models: ${Object.keys(MODELS).join(', ')}`);
    }
    
    const { query, history } = processMessages(messages);
    const client = new AgentClient(agentAppKey, agentVisitorKey);
    
    if (stream) {
      // Streaming response using TransformStream
      const conversationId = await client.createConversation();
      const fullQuery = buildHistoryPrompt(history) + query;
      
      const { readable, writable } = new TransformStream();
      const writer = writable.getWriter();
      const encoder = new TextEncoder();
      
      (async () => {
        try {
          const response = await fetch(`${client.baseUrl}/api/proxy/chat/v2/chat_query`, {
            method: 'POST',
            headers: client.headers,
            body: JSON.stringify({
              Query: fullQuery,
              AppConversationID: conversationId,
              AppKey: client.appKey,
              QueryExtends: { Files: [] },
            }),
          });
          
          const reader = response.body.getReader();
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
                  let chunk = null;
                  
                  if (data.event === 'think_message' && data.answer) {
                    chunk = {
                      id: `chatcmpl-${Date.now()}`,
                      object: 'chat.completion.chunk',
                      created: Math.floor(Date.now() / 1000),
                      model,
                      choices: [{
                        index: 0,
                        delta: { reasoning_content: data.answer },
                        finish_reason: null,
                      }],
                    };
                  } else if (data.event === 'message' && data.answer) {
                    chunk = {
                      id: `chatcmpl-${Date.now()}`,
                      object: 'chat.completion.chunk',
                      created: Math.floor(Date.now() / 1000),
                      model,
                      choices: [{
                        index: 0,
                        delta: { content: data.answer },
                        finish_reason: null,
                      }],
                    };
                  }
                  
                  if (chunk) {
                    await writer.write(encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`));
                  }
                } catch {
                  // Skip invalid JSON
                }
              }
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
          await writer.write(encoder.encode(`data: ${JSON.stringify(finalChunk)}\n\n`));
          await writer.write(encoder.encode('data: [DONE]\n\n'));
        } finally {
          await client.deleteConversation(conversationId);
          await writer.close();
        }
      })();
      
      return new Response(readable, {
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
    return errorResponse(error.message, 500);
  }
}

/**
 * Main request handler for Vercel Edge Functions
 */
export default async function handler(request) {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;
  
  // Handle CORS preflight
  if (method === 'OPTIONS') {
    return handleCors();
  }
  
  // Verify API key if configured
  const apiKey = process.env.API_KEY;
  if (!verifyApiKey(request, apiKey)) {
    return errorResponse('Unauthorized', 403);
  }
  
  // Route requests - handle both /api/* and /v1/* paths
  if ((path === '/api/models' || path === '/v1/models') && method === 'GET') {
    return handleModels();
  }
  
  if ((path === '/api/chat/completions' || path === '/v1/chat/completions') && method === 'POST') {
    return handleChatCompletions(request);
  }
  
  // Health check
  if (path === '/' || path === '/api' || path === '/health') {
    return jsonResponse({ status: 'ok', message: 'OpenAI-compatible API (Vercel Edge Functions)' });
  }
  
  return errorResponse('Not Found', 404);
}
