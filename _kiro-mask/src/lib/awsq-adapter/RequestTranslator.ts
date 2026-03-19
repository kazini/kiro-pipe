/**
 * lib/awsq-adapter/RequestTranslator.ts
 *
 * Translates AWS Q request bodies into Anthropic or OpenAI format.
 *
 * Key finding from real captured traffic (request_1.json):
 *   assistantResponseMessage uses "toolUses" (plural), not "toolUse".
 *   Both are handled here for forward compatibility.
 *
 * No imports from outside this library.
 */

import { TranslationError } from './errors.js'
import type {
  AWSQRequest,
  AWSQHistoryItem,
  AWSQToolResult,
  AWSQTool,
  AWSQToolUse,
  AnthropicRequest,
  AnthropicMessage,
  AnthropicContentBlock,
  AnthropicTool,
  OpenAIRequest,
  OpenAIMessage,
  OpenAITool,
  OpenAIToolCall,
} from './types.js'

// ─── Public API ───────────────────────────────────────────────────────────────

export class RequestTranslator {

  toAnthropic(
    awsRequest:  AWSQRequest,
    targetModel: string,
    maxTokens:   number,
  ): AnthropicRequest {
    try {
      const history    = extractHistory(awsRequest)
      const currentMsg = extractCurrentUserInput(awsRequest)
      const tools      = extractToolsAnthropic(currentMsg.tools)

      const messages: AnthropicMessage[] = [
        ...buildAnthropicHistory(history),
        ...buildAnthropicCurrentMessage(currentMsg),
      ]

      const request: AnthropicRequest = {
        model:      targetModel,
        max_tokens: maxTokens,
        messages,
        stream:     true,
      }
      if (tools.length > 0) request.tools = tools
      return request
    } catch (err) {
      if (err instanceof TranslationError) throw err
      throw new TranslationError('Failed to translate request to Anthropic format', {}, err)
    }
  }

  toOpenAI(
    awsRequest:  AWSQRequest,
    targetModel: string,
    maxTokens:   number,
  ): OpenAIRequest {
    try {
      const history    = extractHistory(awsRequest)
      const currentMsg = extractCurrentUserInput(awsRequest)
      const tools      = extractToolsOpenAI(currentMsg.tools)

      const consumedToolIds = new Set<string>()
      const historyMessages = buildOpenAIHistory(history, consumedToolIds)
      const currentMessages = buildOpenAICurrentMessage(currentMsg, consumedToolIds)

      const messages: OpenAIMessage[] = [...historyMessages, ...currentMessages]

      const request: OpenAIRequest = {
        model:      targetModel,
        max_tokens: maxTokens,
        messages,
        stream:     true,
      }
      if (tools.length > 0) request.tools = tools
      return request
    } catch (err) {
      if (err instanceof TranslationError) throw err
      throw new TranslationError('Failed to translate request to OpenAI format', {}, err)
    }
  }
}

// ─── Shared extraction ────────────────────────────────────────────────────────

function extractHistory(req: AWSQRequest): AWSQHistoryItem[] {
  return req.conversationState.history ?? []
}

interface CurrentUserInput {
  content:     string
  tools:       AWSQTool[]
  toolResults: AWSQToolResult[]
}

function extractCurrentUserInput(req: AWSQRequest): CurrentUserInput {
  const userInput = req.conversationState.currentMessage.userInputMessage
  const ctx       = userInput.userInputMessageContext ?? {}
  return {
    content:     userInput.content,
    tools:       ctx.tools       ?? [],
    toolResults: ctx.toolResults ?? [],
  }
}

function extractToolResultText(result: AWSQToolResult): string {
  if (result.status !== 'success') {
    return `Error: ${result.error ?? 'Tool execution failed'}`
  }
  return result.content
    .map(c => c.text ?? '')
    .filter(t => t.length > 0)
    .join('\n')
}

/**
 * Get tool uses from an assistant response message.
 * Handles both "toolUses" (real Kiro format) and "toolUse" (legacy/test format).
 */
function getToolUses(arm: AWSQHistoryItem['assistantResponseMessage']): AWSQToolUse[] {
  if (!arm) return []
  // Real Kiro format uses "toolUses" — fall back to "toolUse" for test fixtures
  return (arm as any).toolUses ?? (arm as any).toolUse ?? []
}

// ─── Anthropic path ───────────────────────────────────────────────────────────

function buildAnthropicHistory(history: AWSQHistoryItem[]): AnthropicMessage[] {
  const messages: AnthropicMessage[] = []

  for (const item of history) {
    if (item.userInputMessage?.content) {
      messages.push({ role: 'user', content: item.userInputMessage.content })
    }

    if (item.assistantResponseMessage) {
      const arm      = item.assistantResponseMessage
      const toolUses = getToolUses(arm)
      const blocks:  AnthropicContentBlock[] = []

      if (arm.content) {
        blocks.push({ type: 'text', text: arm.content })
      }

      for (const t of toolUses) {
        let parsedInput: unknown = {}
        try { parsedInput = JSON.parse(t.input) }
        catch { parsedInput = { raw: t.input } }
        blocks.push({ type: 'tool_use', id: t.toolUseId, name: t.name, input: parsedInput })
      }

      if (blocks.length > 0) {
        messages.push({ role: 'assistant', content: blocks })
      }
    }
  }

  return messages
}

function buildAnthropicCurrentMessage(current: CurrentUserInput): AnthropicMessage[] {
  const messages: AnthropicMessage[] = []

  if (current.toolResults.length > 0) {
    const blocks: AnthropicContentBlock[] = []
    for (const result of current.toolResults) {
      blocks.push({
        type:        'tool_result',
        tool_use_id: result.toolUseId,
        content:     extractToolResultText(result),
      })
    }
    if (current.content) {
      blocks.push({ type: 'text', text: current.content })
    }
    messages.push({ role: 'user', content: blocks })
  } else if (current.content) {
    messages.push({ role: 'user', content: current.content })
  }

  return messages
}

function extractToolsAnthropic(awsTools: AWSQTool[]): AnthropicTool[] {
  return awsTools.map(t => ({
    name:         t.toolSpecification.name,
    description:  t.toolSpecification.description,
    input_schema: t.toolSpecification.inputSchema.json as Record<string, unknown>,
  }))
}

// ─── OpenAI path ──────────────────────────────────────────────────────────────

function buildOpenAIHistory(
  history:         AWSQHistoryItem[],
  consumedToolIds: Set<string>,
): OpenAIMessage[] {
  const messages:         OpenAIMessage[] = []
  const consumedUserIdxs: Set<number>     = new Set()

  for (let i = 0; i < history.length; i++) {
    const item = history[i]!

    if (item.userInputMessage && !consumedUserIdxs.has(i)) {
      if (item.userInputMessage.content) {
        messages.push({ role: 'user', content: item.userInputMessage.content })
      }
    }

    if (item.assistantResponseMessage) {
      const arm      = item.assistantResponseMessage
      const toolUses = getToolUses(arm)

      if (toolUses.length === 0) {
        messages.push({ role: 'assistant', content: arm.content || '' })
        continue
      }

      messages.push({
        role:    'assistant',
        content: arm.content || null,
        tool_calls: toolUses.map(t => ({
          id:       t.toolUseId,
          type:     'function' as const,
          function: { name: t.name, arguments: t.input },
        })),
      })

      const nextItem = history[i + 1]
      if (nextItem !== undefined) {
        consumedUserIdxs.add(i + 1)
        for (const t of toolUses) {
          consumedToolIds.add(t.toolUseId)
          messages.push({ role: 'tool', tool_call_id: t.toolUseId, content: '' })
        }
      }
    }
  }

  return messages
}

function buildOpenAICurrentMessage(
  current:         CurrentUserInput,
  consumedToolIds: Set<string>,
): OpenAIMessage[] {
  const messages: OpenAIMessage[] = []

  if (current.toolResults.length > 0) {
    if (current.content) {
      messages.push({ role: 'user', content: current.content })
    }
    for (const result of current.toolResults) {
      if (consumedToolIds.has(result.toolUseId)) continue
      messages.push({
        role:         'tool',
        tool_call_id: result.toolUseId,
        content:      extractToolResultText(result),
      })
    }
  } else if (current.content) {
    messages.push({ role: 'user', content: current.content })
  }

  return messages
}

function extractToolsOpenAI(awsTools: AWSQTool[]): OpenAITool[] {
  return awsTools.map(t => ({
    type:     'function' as const,
    function: {
      name:        t.toolSpecification.name,
      description: t.toolSpecification.description,
      parameters:  t.toolSpecification.inputSchema.json as Record<string, unknown>,
    },
  }))
}
