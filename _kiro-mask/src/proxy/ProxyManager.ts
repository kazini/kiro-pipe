/**
 * ProxyManager
 *
 * HTTPS MITM proxy via mockttp.
 * Registers rules in priority order, delegates routing decisions to TrafficRouter,
 * and delegates model injection to ModelRegistry.
 *
 * Phase 2: custom model requests return a placeholder event stream response.
 * Phase 3: replace placeholder with AWSQAdapter.handle().
 */

import mockttp                          from 'mockttp'
import type { Mockttp, CompletedRequest } from 'mockttp'
import CRC32                            from 'crc-32'

import type { TrafficRouter }           from './TrafficRouter.js'
import type { ModelRegistry }           from '../registry/ModelRegistry.js'
import { log }                          from '../util/Logger.js'

// ─── ProxyManager ─────────────────────────────────────────────────────────────

export class ProxyManager {

  private server: Mockttp | null = null

  constructor(
    private readonly router:   TrafficRouter,
    private readonly registry: ModelRegistry,
  ) {}

  /**
   * Start the HTTPS MITM proxy on the given port.
   * Returns the CA certificate PEM string (for logging/debugging).
   * Kiro is launched with --ignore-certificate-errors so no install needed.
   */
  async start(port: number): Promise<string> {
    const https = await mockttp.generateCACertificate({ bits: 2048 })
    this.server = mockttp.getLocal({ https })

    await this.registerRules()
    await this.server.start(port)

    log.info(`[Proxy] Listening on port ${port}`)
    log.debug('[Proxy] CA certificate generated (Kiro will use --ignore-certificate-errors)')

    return https.cert
  }

  async stop(): Promise<void> {
    if (this.server) {
      await this.server.stop()
      this.server = null
      log.info('[Proxy] Stopped')
    }
  }

  // ─── Rule registration ─────────────────────────────────────────────────────

  /**
   * Rules are registered in priority order — first match in mockttp wins.
   *
   * Order:
   *   1. Block rules     — telemetry, updates, metrics, usageLimits
   *   2. Model injection — ListAvailableModels (passthrough + response transform)
   *   3. Chat routing    — generateAssistantResponse (custom or passthrough)
   *   4. Passthrough     — everything else
   */
  private async registerRules(): Promise<void> {
    const server = this.server!

    // ── 1a. Telemetry block ───────────────────────────────────────────────────
    await server.forAnyRequest()
      .matching(req => req.hostname?.includes('telemetry') ?? false)
      .thenCallback(req => {
        const d = this.router.decideRequest(req.method, req.hostname ?? '', req.path)
        return d.action === 'block'
          ? { status: d.status, body: d.body, headers: { 'content-type': d.contentType } }
          : undefined   // fall through if router disagrees (shouldn't happen)
      })

    // ── 1b. All other blocking rules via single callback ─────────────────────
    // Rather than one rule per block type, we run every request through the
    // router. If it says 'block', we return the fake response immediately.
    // The router evaluates rules in priority order internally.
    await server.forAnyRequest()
      .matching(req => {
        const d = this.router.decideRequest(req.method, req.hostname ?? '', req.path)
        return d.action === 'block'
      })
      .thenCallback(req => {
        const d = this.router.decideRequest(req.method, req.hostname ?? '', req.path)
        if (d.action !== 'block') return undefined
        log.debug(`[Proxy] Blocked: ${req.method} ${req.path}`)
        return {
          status:  d.status,
          body:    d.body,
          headers: { 'content-type': d.contentType },
        }
      })

    // ── 2. ListAvailableModels — passthrough with response injection ──────────
    await server.forAnyRequest()
      .matching(req => req.path.includes('ListAvailableModels'))
      .thenPassThrough({
        beforeResponse: async (response) => {
          try {
            // mockttp provides body as a Buffer in beforeResponse
            const originalText =
              typeof response.body === 'string'
                ? response.body
                : Buffer.isBuffer(response.body)
                  ? response.body.toString('utf-8')
                  : JSON.stringify(response.body)

            const modifiedText = this.registry.injectCustomModels(originalText)
            const modifiedBytes = Buffer.byteLength(modifiedText, 'utf-8')

            return {
              headers: {
                ...response.headers,
                'content-length':    modifiedBytes.toString(),
                'transfer-encoding': undefined,   // remove if present
              },
              body: modifiedText,
            }
          } catch (err) {
            log.error('[Proxy] Model injection failed — returning original response', err)
            return undefined   // return original unmodified
          }
        },
      })

    // ── 3. generateAssistantResponse ─────────────────────────────────────────
    await server.forAnyRequest()
      .matching(req => req.path.includes('generateAssistantResponse'))
      .thenCallback(async (req) => {
        const body = await this.getBodyText(req)
        const decision = this.router.decideRequest(req.method, req.hostname ?? '', req.path, body)

        if (decision.action === 'custom-model') {
          log.info(`[Proxy] Custom model selected: ${decision.modelId} → ${decision.provider.name}`)

          // ── Phase 2 placeholder ─────────────────────────────────────────────
          // Phase 3 will replace this with AWSQAdapter.handle(body, decision.provider)
          const placeholderText =
            `[KiroMask] Routing to ${decision.provider.name} / ${decision.modelId}. ` +
            `Translation layer not yet implemented — Phase 3 coming soon.`

          return {
            status: 200,
            headers: { 'content-type': 'application/vnd.amazon.eventstream' },
            body:    encodePlaceholderResponse(placeholderText),
          }
        }

        // Kiro model or unknown — pass through to AWS Q
        return undefined   // returning undefined means "use default passthrough"
      })

    // ── 4. Fallback passthrough ───────────────────────────────────────────────
    await server.forAnyRequest().thenPassThrough()

    log.debug('[Proxy] Rules registered')
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  private async getBodyText(req: CompletedRequest): Promise<string> {
    try {
      return await req.body.getText()
    } catch {
      return ''
    }
  }
}

// ─── Phase 2 placeholder: minimal AWS Event Stream encoder ───────────────────
//
// Produces a valid binary event stream containing a single assistantResponseEvent.
// This is temporary — Phase 3 replaces it with lib/awsq-adapter/eventStream.ts.
// Kept here so Phase 2 is testable end-to-end without the full lib.

function encodeEventStreamHeader(name: string, value: string): Buffer {
  const n   = Buffer.from(name,  'utf8')
  const v   = Buffer.from(value, 'utf8')
  const buf = Buffer.alloc(1 + n.length + 1 + 2 + v.length)
  let i = 0
  buf.writeUInt8(n.length, i++);  n.copy(buf, i); i += n.length
  buf.writeUInt8(7,         i++)  // value type 7 = string
  buf.writeUInt16BE(v.length, i); i += 2
  v.copy(buf, i)
  return buf
}

function encodeEventFrame(eventType: string, payload: object): Buffer {
  const payloadBuf = Buffer.from(JSON.stringify(payload), 'utf8')

  const headers = Buffer.concat([
    encodeEventStreamHeader(':event-type',    eventType),
    encodeEventStreamHeader(':content-type',  'application/json'),
    encodeEventStreamHeader(':message-type',  'event'),
  ])

  const totalLength = 12 + headers.length + payloadBuf.length + 4

  const prelude = Buffer.alloc(8)
  prelude.writeUInt32BE(totalLength,    0)
  prelude.writeUInt32BE(headers.length, 4)

  const preludeCrc = Buffer.alloc(4)
  preludeCrc.writeUInt32BE((CRC32.buf(prelude) >>> 0), 0)

  const msgBody = Buffer.concat([prelude, preludeCrc, headers, payloadBuf])
  const msgCrc  = Buffer.alloc(4)
  msgCrc.writeUInt32BE((CRC32.buf(msgBody) >>> 0), 0)

  return Buffer.concat([msgBody, msgCrc])
}

function encodePlaceholderResponse(text: string): Buffer {
  return Buffer.concat([
    encodeEventFrame('assistantResponseEvent', { content: text }),
    encodeEventFrame('meteringEvent',          { unit: 'credit', unitPlural: 'credits', usage: 0 }),
    encodeEventFrame('contextUsageEvent',      { contextUsagePercentage: 0 }),
  ])
}
