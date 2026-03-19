/**
 * lib/awsq-adapter — public API
 *
 * Everything a consumer needs, re-exported from one place.
 * Internal implementation files are not part of the public surface.
 */

export { RequestTranslator }          from './RequestTranslator.js'
export { ResponseTranslator }         from './ResponseTranslator.js'
export {
  encodeEvent,
  encodeTextChunk,
  encodeToolUseChunk,
  encodeMeteringEvent,
  encodeContextUsageEvent,
  encodeResponseEnd,
}                                     from './eventStream.js'
export { TranslationError,
         EncodingError }              from './errors.js'
export type {
  AWSQRequest,
  AWSQHistoryItem,
  AWSQToolResult,
  AWSQTool,
  AnthropicRequest,
  AnthropicMessage,
  AnthropicTool,
  AnthropicStreamEvent,
  OpenAIRequest,
  OpenAIMessage,
  OpenAITool,
  OpenAIStreamChunk,
}                                     from './types.js'
