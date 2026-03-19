/**
 * lib/awsq-adapter/types.ts
 *
 * All types used by the awsq-adapter library.
 * No imports from outside this library.
 *
 * Field names are derived from real captured Kiro traffic (request_1.json).
 * Notable: assistantResponseMessage uses "toolUses" (plural), not "toolUse".
 */

// ─── AWS Q request types ──────────────────────────────────────────────────────

export interface AWSQToolSpecification {
  name:        string
  description: string
  inputSchema: {
    json: Record<string, unknown>
  }
}

export interface AWSQTool {
  toolSpecification: AWSQToolSpecification
}

export interface AWSQToolResultContent {
  text?: string
}

export interface AWSQToolResult {
  toolUseId: string
  status:    string   // "success" | "error"
  content:   AWSQToolResultContent[]
  error?:    string
}

export interface AWSQUserInputMessage {
  content:  string
  modelId:  string
  origin?:  string
  userInputMessageContext?: {
    tools?:       AWSQTool[]
    toolResults?: AWSQToolResult[]
  }
}

// Real field name from captured traffic: "toolUses" (plural), NOT "toolUse"
export interface AWSQToolUse {
  toolUseId: string
  name:      string
  input:     string   // JSON-stringified
}

export interface AWSQAssistantResponseMessage {
  content:   string
  toolUses?: AWSQToolUse[]   // ← "toolUses" — confirmed from request_1.json
}

export interface AWSQHistoryItem {
  userInputMessage?:         { content: string }
  assistantResponseMessage?: AWSQAssistantResponseMessage
}

export interface AWSQRequest {
  conversationState: {
    conversationId:       string
    agentContinuationId?: string
    agentTaskType?:       string
    chatTriggerType?:     string
    currentMessage: {
      userInputMessage: AWSQUserInputMessage
    }
    history?: AWSQHistoryItem[]
  }
  profileArn?: string   // present in real requests, ignored for routing
}

// ─── Anthropic request types ──────────────────────────────────────────────────

export type AnthropicContentBlock =
  | { type: 'text';        text: string }
  | { type: 'tool_use';    id: string; name: string; input: unknown }
  | { type: 'tool_result'; tool_use_id: string; content: string }

export interface AnthropicMessage {
  role:    'user' | 'assistant'
  content: string | AnthropicContentBlock[]
}

export interface AnthropicTool {
  name:         string
  description:  string
  input_schema: Record<string, unknown>
}

export interface AnthropicRequest {
  model:      string
  max_tokens: number
  messages:   AnthropicMessage[]
  tools?:     AnthropicTool[]
  stream:     true
}

// ─── Anthropic stream event types ─────────────────────────────────────────────

export type AnthropicStreamEvent =
  | { type: 'message_start';    message: { usage: { input_tokens: number } } }
  | { type: 'content_block_start'; index: number; content_block: { type: string; id?: string; name?: string } }
  | { type: 'content_block_delta';
      index: number
      delta:
        | { type: 'text_delta';       text: string }
        | { type: 'input_json_delta'; partial_json: string }
    }
  | { type: 'content_block_stop'; index: number }
  | { type: 'message_delta'; usage: { output_tokens: number } }
  | { type: 'message_stop' }
  | { type: string }

// ─── OpenAI request types ─────────────────────────────────────────────────────

export interface OpenAIToolFunction {
  name:        string
  description: string
  parameters:  Record<string, unknown>
}

export interface OpenAITool {
  type:     'function'
  function: OpenAIToolFunction
}

export type OpenAIMessage =
  | { role: 'user';      content: string }
  | { role: 'assistant'; content: string | null; tool_calls?: OpenAIToolCall[] }
  | { role: 'tool';      tool_call_id: string; content: string }

export interface OpenAIToolCall {
  id:       string
  type:     'function'
  function: { name: string; arguments: string }
}

export interface OpenAIRequest {
  model:      string
  max_tokens: number
  messages:   OpenAIMessage[]
  tools?:     OpenAITool[]
  stream:     true
}

// ─── OpenAI stream chunk types ────────────────────────────────────────────────

export interface OpenAIToolCallDelta {
  index:    number
  id?:      string
  type?:    'function'
  function?: {
    name?:      string
    arguments?: string
  }
}

export interface OpenAIStreamChunk {
  choices: Array<{
    delta: {
      content?:     string | null
      tool_calls?:  OpenAIToolCallDelta[]
    }
    finish_reason?: string | null
  }>
  usage?: {
    prompt_tokens?:     number
    completion_tokens?: number
    total_tokens?:      number
  }
}
