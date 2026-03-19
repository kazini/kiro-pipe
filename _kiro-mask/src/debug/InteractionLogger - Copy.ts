/**
 * InteractionLogger
 *
 * Saves intercepted requests and responses to disk when
 * debug.save_interactions is enabled in config.
 *
 * Mirrors the Python version's debug_logs/interactions/ structure:
 *   <output_dir>/interactions/posted/request_N.json   — request body
 *   <output_dir>/interactions/responses/response_N.bin — raw binary response
 *
 * The counter is per-session and resets on restart.
 * Files are written synchronously to avoid dropping captures under load.
 *
 * Usage:
 *   const logger = new InteractionLogger(config)
 *   logger.saveRequest(body, url, headers)
 *   logger.saveResponse(buffer)
 */

import {
  mkdirSync,
  writeFileSync,
  existsSync,
}                       from 'node:fs'
import path             from 'node:path'
import { log }          from '../util/Logger.js'
import type { Config }  from '../config/schema.js'

export class InteractionLogger {

  private readonly enabled:     boolean
  private readonly postedDir:   string
  private readonly responsesDir: string
  private counter = 0

  constructor(config: Config) {
    this.enabled = config.debug.enabled && config.debug.save_interactions

    const base         = path.resolve(config.debug.output_dir)
    this.postedDir     = path.join(base, 'interactions', 'posted')
    this.responsesDir  = path.join(base, 'interactions', 'responses')

    if (this.enabled) {
      try {
        mkdirSync(this.postedDir,    { recursive: true })
        mkdirSync(this.responsesDir, { recursive: true })
        log.info(`[Debug] Interaction logging enabled → ${path.join(base, 'interactions')}`)
      } catch (err) {
        log.warn(`[Debug] Could not create interaction log directories: ${String(err)}`)
      }
    }
  }

  /**
   * Save an intercepted request body to disk as JSON.
   * Also saves the URL and headers for full context.
   *
   * @param body     Raw request body string (should be valid JSON for AWS Q requests)
   * @param url      Full request URL
   * @param headers  Request headers object
   */
  saveRequest(
    body:    string,
    url:     string,
    headers: Record<string, string | string[] | undefined>,
  ): number {
    if (!this.enabled) return -1

    this.counter++
    const n = this.counter

    const envelope: Record<string, unknown> = {
      _index:  n,
      _url:    url,
      _headers: headers,
    }

    // Try to parse body as JSON for pretty storage; fall back to raw string
    try {
      envelope['body'] = JSON.parse(body)
    } catch {
      envelope['body'] = body
    }

    const filePath = path.join(this.postedDir, `request_${n}.json`)
    try {
      writeFileSync(filePath, JSON.stringify(envelope, null, 2), 'utf-8')
      log.debug(`[Debug] Saved request #${n} → ${filePath}`)
    } catch (err) {
      log.warn(`[Debug] Failed to save request #${n}: ${String(err)}`)
    }

    return n
  }

  /**
   * Save a raw binary response buffer to disk.
   * Pass the index returned by saveRequest() to pair them by number.
   *
   * @param buffer  The complete AWS Event Stream binary response
   * @param index   Index from saveRequest(), or -1 to auto-increment
   */
  saveResponse(buffer: Buffer, index?: number): void {
    if (!this.enabled) return

    const n        = index ?? ++this.counter
    const filePath = path.join(this.responsesDir, `response_${n}.bin`)

    try {
      writeFileSync(filePath, buffer)
      log.debug(`[Debug] Saved response #${n} → ${filePath} (${buffer.length} bytes)`)
    } catch (err) {
      log.warn(`[Debug] Failed to save response #${n}: ${String(err)}`)
    }
  }

  /**
   * Save a passthrough response body as binary.
   * Called when Kiro's native models respond — captures the real AWS format.
   *
   * @param data   Raw response bytes from AWS Q
   * @param label  Optional label suffix for the filename (e.g. "passthrough")
   */

  /**
   * Decode a binary AWS Event Stream buffer and save as human-readable JSON.
   * Produces response_N.json alongside response_N.bin.
   * Useful for reviewing captures and sending to collaborators.
   */
  saveResponseText(buffer: Buffer, index?: number): void {
    if (!this.enabled) return

    const n = index ?? this.counter
    const filePath = path.join(this.responsesDir, `response_${n}.json`)

    try {
      const events = decodeEventStream(buffer)
      writeFileSync(filePath, JSON.stringify(events, null, 2), 'utf-8')
      log.debug(`[Debug] Saved decoded response #${n} → ${filePath} (${events.length} events)`)
    } catch (err) {
      log.warn(`[Debug] Failed to decode response #${n}: ${String(err)}`)
    }
  }

    savePassthroughResponse(data: Buffer, label = 'passthrough'): void {
    if (!this.enabled) return

    this.counter++
    const n        = this.counter
    const filePath = path.join(this.responsesDir, `response_${n}_${label}.bin`)

    try {
      writeFileSync(filePath, data)
      log.debug(`[Debug] Saved passthrough #${n} → ${filePath} (${data.length} bytes)`)
    } catch (err) {
      log.warn(`[Debug] Failed to save passthrough #${n}: ${String(err)}`)
    }
  }

  get isEnabled(): boolean {
    return this.enabled
  }
}

// ─── Inline event stream decoder ─────────────────────────────────────────────
// Mirrors Python decode_event_stream.py — kept inline to avoid circular imports.

interface DecodedEvent {
  eventType:   string
  contentType: string
  payload:     unknown
}

function decodeEventStream(data: Buffer): DecodedEvent[] {
  const events: DecodedEvent[] = []
  let offset = 0

  while (offset < data.length) {
    if (offset + 12 > data.length) break
    const totalLength   = data.readUInt32BE(offset)
    const headersLength = data.readUInt32BE(offset + 4)
    if (offset + totalLength > data.length || totalLength < 16) break

    const headersEnd = offset + 12 + headersLength
    const headers: Record<string, string> = {}
    let h = offset + 12

    while (h < headersEnd) {
      const nameLen = data.readUInt8(h);        h += 1
      const name    = data.subarray(h, h + nameLen).toString('utf8'); h += nameLen
      h += 1  // value_type byte (always 7 = string)
      const valLen  = data.readUInt16BE(h);     h += 2
      const value   = data.subarray(h, h + valLen).toString('utf8'); h += valLen
      headers[name] = value
    }

    const payloadBuf = data.subarray(headersEnd, offset + totalLength - 4)
    let payload: unknown
    try   { payload = JSON.parse(payloadBuf.toString('utf8')) }
    catch { payload = payloadBuf.toString('utf8') }

    events.push({
      eventType:   headers[':event-type']   ?? '(unknown)',
      contentType: headers[':content-type'] ?? '(unknown)',
      payload,
    })

    offset += totalLength
  }

  return events
}
