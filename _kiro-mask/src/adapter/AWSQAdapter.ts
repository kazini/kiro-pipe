/**
 * AWSQAdapter
 *
 * Pipeline orchestrator for custom model requests.
 * The ONLY place that bridges config knowledge and lib knowledge.
 *
 * Responsibilities:
 *   1. Parse raw AWS Q request body
 *   2. Resolve provider settings from config (api_key, api_base, model, maxTokens)
 *   3. Call lib/awsq-adapter translator (Anthropic or OpenAI path)
 *   4. Call the provider SDK directly (Phase 3: direct calls)
 *      Phase 4 will replace SDK calls with AnthropicClient/OpenAIClient
 *      which add RetryHandler and RateLimitTracker.
 *   5. Call lib/awsq-adapter response translator
 *   6. Return complete AWS Event Stream Buffer
 *
 * Throws on unrecoverable errors. ProxyManager catches and returns
 * an encoded error response to Kiro.
 */

import Anthropic from '@anthropic-ai/sdk'
import OpenAI    from 'openai'

import { RequestTranslator }  from '../lib/awsq-adapter/RequestTranslator.js'
import { ResponseTranslator } from '../lib/awsq-adapter/ResponseTranslator.js'
import { TranslationError }   from '../lib/awsq-adapter/errors.js'
import { encodeTextChunk,
         encodeResponseEnd }  from '../lib/awsq-adapter/eventStream.js'
import type { AWSQRequest }   from '../lib/awsq-adapter/types.js'

import type { Config, ResolvedProvider } from '../config/schema.js'
import { log }                           from '../util/Logger.js'

// ─── AWSQAdapter ──────────────────────────────────────────────────────────────

export class AWSQAdapter {

  private readonly requestTranslator  = new RequestTranslator()
  private readonly responseTranslator = new ResponseTranslator()

  constructor(private readonly config: Config) {}

  /**
   * Handle a generateAssistantResponse request for a custom model.
   *
   * @param rawBody   Raw JSON string from Kiro's request body
   * @param provider  The resolved provider that owns this model
   * @returns         Complete AWS Event Stream binary buffer
   */
  async handle(rawBody: string, provider: ResolvedProvider): Promise<Buffer> {
    // ── 1. Parse AWS Q request ──────────────────────────────────────────────
    let awsRequest: AWSQRequest
    try {
      awsRequest = JSON.parse(rawBody) as AWSQRequest
    } catch (err) {
      throw new TranslationError('Failed to parse AWS Q request body', {}, err)
    }

    const userInput  = awsRequest.conversationState.currentMessage.userInputMessage
    const modelId    = userInput.modelId

    // ── 2. Resolve model config ──────────────────────────────────────────────
    const modelConfig = provider.config.models.find(m => m.name === modelId)
    const maxTokens   = modelConfig?.max_tokens ?? 4096
    const apiKey      = this.resolveApiKey(provider)
    const apiBase     = provider.config.api_base

    log.debug(`[Adapter] ${provider.name} / ${modelId} (maxTokens: ${maxTokens})`)

    // ── 3. Route by provider type ────────────────────────────────────────────
    if (provider.config.type === 'anthropic') {
      return this.handleAnthropic(awsRequest, modelId, maxTokens, apiKey, apiBase)
    }

    if (provider.config.type === 'openai') {
      return this.handleOpenAI(awsRequest, modelId, maxTokens, apiKey, apiBase)
    }

    throw new TranslationError(
      `Unknown provider type "${provider.config.type}" for provider "${provider.name}"`,
      { providerName: provider.name, providerType: provider.config.type },
    )
  }

  // ── Anthropic path ──────────────────────────────────────────────────────────

  private async handleAnthropic(
    awsRequest: AWSQRequest,
    modelId:    string,
    maxTokens:  number,
    apiKey:     string,
    apiBase:    string | undefined,
  ): Promise<Buffer> {
    // Translate AWS Q → Anthropic
    const anthropicRequest = this.requestTranslator.toAnthropic(
      awsRequest,
      modelId,
      maxTokens,
    )

    log.debug(`[Adapter] Sending to Anthropic: ${anthropicRequest.messages.length} messages`)

    // Phase 3: direct SDK call.
    // Phase 4: replace with AnthropicClient.stream() which adds retry + rate limit tracking.
    const clientOptions: ConstructorParameters<typeof Anthropic>[0] = { apiKey }
    if (apiBase) clientOptions.baseURL = apiBase

    // Handle Portkey passthrough — if portkey is enabled, point at Portkey gateway
    if (this.config.portkey.enabled && this.config.portkey.api_key) {
      clientOptions.baseURL         = 'https://api.portkey.ai'
      clientOptions.defaultHeaders  = {
        'x-portkey-api-key':     this.config.portkey.api_key,
        'x-portkey-virtual-key': apiKey,
      }
    }

    const client = new Anthropic(clientOptions)

    const stream = await client.messages.stream({
      model:      anthropicRequest.model,
      max_tokens: anthropicRequest.max_tokens,
      messages:   anthropicRequest.messages as Parameters<typeof client.messages.stream>[0]['messages'],
      tools:      anthropicRequest.tools as Parameters<typeof client.messages.stream>[0]['tools'],
    })

    // Translate Anthropic SSE stream → AWS Event Stream
    return this.responseTranslator.fromAnthropicStream(
      anthropicStreamToAsyncIterable(stream)
    )
  }

  // ── OpenAI path ─────────────────────────────────────────────────────────────

  private async handleOpenAI(
    awsRequest: AWSQRequest,
    modelId:    string,
    maxTokens:  number,
    apiKey:     string,
    apiBase:    string | undefined,
  ): Promise<Buffer> {
    // Translate AWS Q → OpenAI
    const openAIRequest = this.requestTranslator.toOpenAI(
      awsRequest,
      modelId,
      maxTokens,
    )

    log.debug(`[Adapter] Sending to OpenAI-compatible: ${openAIRequest.messages.length} messages`)

    // Phase 3: direct SDK call.
    // Phase 4: replace with OpenAIClient.stream() which adds retry + rate limit tracking.
    const client = new OpenAI({
      apiKey,
      baseURL: apiBase,
    })

    const stream = await client.chat.completions.create({
      model:      openAIRequest.model,
      max_tokens: openAIRequest.max_tokens,
      messages:   openAIRequest.messages as Parameters<typeof client.chat.completions.create>[0]['messages'],
      tools:      openAIRequest.tools as Parameters<typeof client.chat.completions.create>[0]['tools'],
      stream:     true,
    })

    // Translate OpenAI SSE stream → AWS Event Stream
    return this.responseTranslator.fromOpenAIStream(
      openAIStreamToAsyncIterable(stream)
    )
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  private resolveApiKey(provider: ResolvedProvider): string {
    // Config value first, then environment variable
    if (provider.config.api_key) return provider.config.api_key

    const envKey = `${provider.name.toUpperCase()}_API_KEY`
    const envVal = process.env[envKey]
    if (envVal) return envVal

    throw new TranslationError(
      `No API key configured for provider "${provider.name}". ` +
      `Set api_key in config or the ${envKey} environment variable.`,
      { providerName: provider.name },
    )
  }
}

// ─── SDK stream adapters ──────────────────────────────────────────────────────
// The Anthropic and OpenAI SDKs return their own stream types.
// These adapt them to plain AsyncIterable so ResponseTranslator stays SDK-free.

import type { AnthropicStreamEvent } from '../lib/awsq-adapter/types.js'
import type { OpenAIStreamChunk }    from '../lib/awsq-adapter/types.js'

async function* anthropicStreamToAsyncIterable(
  stream: ReturnType<Anthropic['messages']['stream']>
): AsyncGenerator<AnthropicStreamEvent> {
  for await (const event of stream) {
    yield event as AnthropicStreamEvent
  }
}

async function* openAIStreamToAsyncIterable(
  stream: AsyncIterable<OpenAI.Chat.Completions.ChatCompletionChunk>
): AsyncGenerator<OpenAIStreamChunk> {
  for await (const chunk of stream) {
    yield chunk as OpenAIStreamChunk
  }
}

// ─── Error response encoder ───────────────────────────────────────────────────
// Used by ProxyManager when AWSQAdapter.handle() throws.

/**
 * Encode an error message as a minimal valid AWS Event Stream response.
 * Kiro will display it as an assistant message.
 */
export function encodeErrorResponse(message: string): Buffer {
  return Buffer.concat([
    encodeTextChunk(`[KiroMask error] ${message}`),
    encodeResponseEnd(0, 0),
  ])
}
