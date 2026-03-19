/**
 * lib/awsq-adapter/ResponseTranslator.ts
 *
 * Consumes provider SSE streams and produces a complete AWS Event Stream
 * binary buffer that Kiro can render.
 *
 * Two entry points:
 *   fromAnthropicStream()  — for type: "anthropic" providers
 *   fromOpenAIStream()     — for type: "openai" providers (OpenRouter, Groq, Ollama, etc.)
 *
 * Both buffer the complete response before returning. Streaming via Transform
 * streams is a Phase 4/5 optimisation (lower memory, faster first token).
 *
 * ⚠️ Tool use index tracking:
 * Both paths key the tool buffer by the streaming INDEX integer, NOT by tool ID.
 * The Python version always grabbed keys()[0] which silently broke concurrent tool calls.
 */

import {
  encodeTextChunk,
  encodeToolUseChunk,
  encodeResponseEnd,
} from './eventStream.js'
import { EncodingError } from './errors.js'
import type {
  AnthropicStreamEvent,
  OpenAIStreamChunk,
} from './types.js'

// ─── Internal tool call buffer ─────────────────────────────────────────────────

interface ToolCallState {
  id:    string
  name:  string
  input: string
}

// ─── ResponseTranslator ───────────────────────────────────────────────────────

export class ResponseTranslator {

  // ── Anthropic path ──────────────────────────────────────────────────────────

  /**
   * Consume an Anthropic SSE stream and return a complete AWS Event Stream buffer.
   * The stream is consumed exactly once.
   */
  async fromAnthropicStream(
    stream: AsyncIterable<AnthropicStreamEvent>,
  ): Promise<Buffer> {
    const chunks:     Buffer[] = []
    const toolBuffer           = new Map<number, ToolCallState>()
    let   inputTokens          = 0
    let   outputTokens         = 0

    try {
      for await (const event of stream) {
        switch (event.type) {

          case 'message_start':
            inputTokens = event.message.usage.input_tokens
            break

          case 'content_block_start': {
            const cb = event.content_block
            if (cb.type === 'tool_use' && cb.id && cb.name) {
              toolBuffer.set(event.index, { id: cb.id, name: cb.name, input: '' })
            }
            break
          }

          case 'content_block_delta': {
            const delta = event.delta

            if (delta.type === 'text_delta' && delta.text) {
              chunks.push(encodeTextChunk(delta.text))

            } else if (delta.type === 'input_json_delta') {
              // Key by index, not tool ID — fixes the Python multi-tool bug
              const entry = toolBuffer.get(event.index)
              if (entry) {
                entry.input += delta.partial_json
                chunks.push(encodeToolUseChunk(entry.name, entry.id, delta.partial_json))
              }
            }
            break
          }

          case 'content_block_stop': {
            // Empty chunk signals end of this tool call to Kiro
            const entry = toolBuffer.get(event.index)
            if (entry) {
              chunks.push(encodeToolUseChunk(entry.name, entry.id, ''))
              toolBuffer.delete(event.index)
            }
            break
          }

          case 'message_delta':
            outputTokens = event.usage.output_tokens
            break

          case 'message_stop':
            // Append metering + context usage at the very end
            chunks.push(encodeResponseEnd(inputTokens, outputTokens))
            break

          // Unknown event types are silently ignored
        }
      }
    } catch (err) {
      throw new EncodingError(
        'Error while consuming Anthropic stream',
        { inputTokens, outputTokens },
        err,
      )
    }

    return Buffer.concat(chunks)
  }

  // ── OpenAI path ─────────────────────────────────────────────────────────────

  /**
   * Consume an OpenAI Chat Completions SSE stream and return a complete
   * AWS Event Stream buffer.
   */
  async fromOpenAIStream(
    stream: AsyncIterable<OpenAIStreamChunk>,
  ): Promise<Buffer> {
    const chunks:     Buffer[] = []
    const toolBuffer           = new Map<number, ToolCallState>()
    let   inputTokens          = 0
    let   outputTokens         = 0

    try {
      for await (const chunk of stream) {
        const choice = chunk.choices[0]

        // Usage may appear on any chunk or on a final chunk after finish_reason
        if (chunk.usage) {
          inputTokens  = chunk.usage.prompt_tokens     ?? inputTokens
          outputTokens = chunk.usage.completion_tokens ?? outputTokens
        }

        if (!choice) continue

        const delta = choice.delta

        // Text content
        if (delta.content) {
          chunks.push(encodeTextChunk(delta.content))
        }

        // Tool calls — keyed by index (not id) to handle concurrent calls
        if (delta.tool_calls) {
          for (const tc of delta.tool_calls) {
            const idx = tc.index

            // Initialise buffer entry on first delta for this index
            if (!toolBuffer.has(idx)) {
              toolBuffer.set(idx, { id: tc.id ?? '', name: '', input: '' })
            }

            const entry = toolBuffer.get(idx)!

            if (tc.id)                     entry.id    = tc.id
            if (tc.function?.name)         entry.name  = tc.function.name
            if (tc.function?.arguments) {
              entry.input += tc.function.arguments
              // Stream each arguments chunk to Kiro as it arrives
              chunks.push(encodeToolUseChunk(entry.name, entry.id, tc.function.arguments))
            }
          }
        }

        // Finish signal — flush any open tool calls and append metering
        if (choice.finish_reason) {
          for (const entry of toolBuffer.values()) {
            chunks.push(encodeToolUseChunk(entry.name, entry.id, ''))
          }
          toolBuffer.clear()
          chunks.push(encodeResponseEnd(inputTokens, outputTokens))
        }
      }
    } catch (err) {
      throw new EncodingError(
        'Error while consuming OpenAI stream',
        { inputTokens, outputTokens },
        err,
      )
    }

    return Buffer.concat(chunks)
  }
}
