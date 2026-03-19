/**
 * lib/awsq-adapter/eventStream.ts
 *
 * AWS Event Stream binary encoder.
 * No external dependencies except crc-32.
 *
 * Frame layout:
 *   [0–3]   total_length    UInt32BE  (entire frame)
 *   [4–7]   headers_length  UInt32BE
 *   [8–11]  prelude_crc32   UInt32BE  (CRC32 of bytes 0–7)
 *   [12..]  headers
 *   [..]    payload         (JSON)
 *   [last4] message_crc32   UInt32BE  (CRC32 of everything before)
 *
 * total_length = 12 + headers_length + payload_length + 4
 *
 * Header wire format (per header):
 *   [0]       name_length  UInt8
 *   [1..N]    name         UTF-8
 *   [N+1]     value_type   UInt8  (always 7 = string)
 *   [N+2..3]  value_length UInt16BE
 *   [N+4..M]  value        UTF-8
 *
 * Every event carries exactly three headers:
 *   :event-type    → event type string
 *   :content-type  → "application/json"
 *   :message-type  → "event"
 */

// @ts-ignore — crc-32 has no bundled types in some versions
import CRC32 from 'crc-32'
import { EncodingError } from './errors.js'

// ─── Token → metering conversion ──────────────────────────────────────────────
// Rough approximation matching the Python version.

const TOKENS_PER_CREDIT  = 10_000
const CONTEXT_WINDOW_MAX = 200_000

// ─── Low-level primitives ─────────────────────────────────────────────────────

function crc32(buf: Buffer): number {
  return (CRC32.buf(buf) as number) >>> 0   // force unsigned 32-bit
}

function encodeHeader(name: string, value: string): Buffer {
  const nameBuf  = Buffer.from(name,  'utf8')
  const valueBuf = Buffer.from(value, 'utf8')

  const out = Buffer.alloc(1 + nameBuf.length + 1 + 2 + valueBuf.length)
  let i = 0

  out.writeUInt8(nameBuf.length, i);  i += 1
  nameBuf.copy(out, i);               i += nameBuf.length
  out.writeUInt8(7, i);               i += 1   // value type 7 = string
  out.writeUInt16BE(valueBuf.length, i); i += 2
  valueBuf.copy(out, i)

  return out
}

// ─── Public: encodeEvent ──────────────────────────────────────────────────────

/**
 * Encode a single AWS Event Stream frame.
 * @param eventType  e.g. "assistantResponseEvent"
 * @param payload    Object to JSON-encode as the frame payload
 */
export function encodeEvent(eventType: string, payload: object): Buffer {
  try {
    const payloadBuf = Buffer.from(JSON.stringify(payload), 'utf8')

    const headers = Buffer.concat([
      encodeHeader(':event-type',   eventType),
      encodeHeader(':content-type', 'application/json'),
      encodeHeader(':message-type', 'event'),
    ])

    const totalLength = 12 + headers.length + payloadBuf.length + 4

    const prelude = Buffer.alloc(8)
    prelude.writeUInt32BE(totalLength,    0)
    prelude.writeUInt32BE(headers.length, 4)

    const preludeCrc = Buffer.alloc(4)
    preludeCrc.writeUInt32BE(crc32(prelude), 0)

    const body = Buffer.concat([prelude, preludeCrc, headers, payloadBuf])

    const msgCrc = Buffer.alloc(4)
    msgCrc.writeUInt32BE(crc32(body), 0)

    return Buffer.concat([body, msgCrc])
  } catch (err) {
    throw new EncodingError(
      `Failed to encode event "${eventType}"`,
      { eventType, payloadKeys: Object.keys(payload) },
      err,
    )
  }
}

// ─── Public: high-level event helpers ────────────────────────────────────────

/** Encode a text chunk from the assistant. */
export function encodeTextChunk(text: string): Buffer {
  return encodeEvent('assistantResponseEvent', { content: text })
}

/**
 * Encode one tool use chunk.
 * Pass an empty string for `inputChunk` to signal the end of a tool call.
 */
export function encodeToolUseChunk(
  toolName:   string,
  toolId:     string,
  inputChunk: string,
): Buffer {
  return encodeEvent('toolUseEvent', {
    name:      toolName,
    toolUseId: toolId,
    input:     inputChunk,
  })
}

/**
 * Encode the metering event (usage credits).
 * Sent once at the end of a response.
 */
export function encodeMeteringEvent(
  inputTokens:  number,
  outputTokens: number,
): Buffer {
  const usage = (inputTokens + outputTokens) / TOKENS_PER_CREDIT
  return encodeEvent('meteringEvent', {
    unit:       'credit',
    unitPlural: 'credits',
    usage,
  })
}

/**
 * Encode the context usage percentage event.
 * Sent once at the end of a response.
 */
export function encodeContextUsageEvent(inputTokens: number): Buffer {
  const contextUsagePercentage = (inputTokens / CONTEXT_WINDOW_MAX) * 100
  return encodeEvent('contextUsageEvent', { contextUsagePercentage })
}

/**
 * Encode a complete response terminator:
 * metering + context usage, concatenated into one Buffer.
 */
export function encodeResponseEnd(
  inputTokens:  number,
  outputTokens: number,
): Buffer {
  return Buffer.concat([
    encodeMeteringEvent(inputTokens, outputTokens),
    encodeContextUsageEvent(inputTokens),
  ])
}
