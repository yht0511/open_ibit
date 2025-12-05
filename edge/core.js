/**
 * Core module for OpenAI-compatible API endpoints
 * This module provides shared functionality for edge/serverless deployments
 * 
 * Note: Only deepseek-r1 model is supported in edge deployments.
 * The ibit model requires BIT authentication which is not suitable for
 * stateless edge computing environments.
 */

// Model configuration - only deepseek-r1 is supported in edge environments
const MODELS = {
  'deepseek-r1': {
    name: 'DeepSeek-R1',
    owned_by: 'Teclab',
  },
};

/**
 * CORS headers for API responses
 */
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Credentials': 'true',
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
 * Get list of available models
 */
function getModels(enabledModels) {
  const models = Object.keys(MODELS)
    .filter(id => enabledModels.includes(id))
    .map(id => ({
      id,
      object: 'model',
      created: Math.floor(Date.now() / 1000),
      owned_by: MODELS[id].owned_by,
    }));
  return { object: 'list', data: models };
}

/**
 * Extract text content from message content (supports multimodal)
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
 * Build chat completion response
 */
function buildCompletionResponse(model, content, reasoningContent = null) {
  const message = {
    role: 'assistant',
    content,
  };
  if (reasoningContent) {
    message.reasoning_content = reasoningContent;
  }
  return {
    id: `chatcmpl-${Date.now()}`,
    object: 'chat.completion',
    created: Math.floor(Date.now() / 1000),
    model,
    choices: [{
      index: 0,
      message,
      finish_reason: 'stop',
    }],
    usage: {
      prompt_tokens: 0,
      completion_tokens: 0,
      total_tokens: 0,
    },
  };
}

/**
 * Build chat completion chunk for streaming
 */
function buildStreamChunk(model, content, reasoningContent = null, finishReason = null) {
  const delta = {};
  if (content !== null) delta.content = content;
  if (reasoningContent !== null) delta.reasoning_content = reasoningContent;
  if (finishReason === null && Object.keys(delta).length === 0) {
    delta.role = 'assistant';
  }
  return {
    id: `chatcmpl-${Date.now()}`,
    object: 'chat.completion.chunk',
    created: Math.floor(Date.now() / 1000),
    model,
    choices: [{
      index: 0,
      delta,
      finish_reason: finishReason,
    }],
  };
}

/**
 * Create SSE stream response
 */
function createStreamResponse(stream) {
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      ...CORS_HEADERS,
    },
  });
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
  
  // Handle system prompt
  if (prevMessages.length > 0 && prevMessages[0].role === 'system') {
    const systemContent = extractTextContent(prevMessages.shift().content);
    query = `[系统提示]:\n${systemContent}\n\n[用户问题]:\n${query}`;
  }
  
  // Build history from remaining messages
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

// Agent API client for DeepSeek-R1
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
      
      // Parse SSE response
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
  
  async *chatStream(query, history = []) {
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

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MODELS,
    CORS_HEADERS,
    jsonResponse,
    errorResponse,
    verifyApiKey,
    handleCors,
    getModels,
    extractTextContent,
    buildCompletionResponse,
    buildStreamChunk,
    createStreamResponse,
    buildHistoryPrompt,
    processMessages,
    AgentClient,
  };
}

// Export for ES modules
export {
  MODELS,
  CORS_HEADERS,
  jsonResponse,
  errorResponse,
  verifyApiKey,
  handleCors,
  getModels,
  extractTextContent,
  buildCompletionResponse,
  buildStreamChunk,
  createStreamResponse,
  buildHistoryPrompt,
  processMessages,
  AgentClient,
};
