/**
 * ProxyManager
 *
 * HTTPS MITM proxy via mockttp.
 *
 * Critical mockttp constraint:
 *   thenCallback() callbacks MUST return a response object.
 *   Returning undefined throws: "Cannot read properties of undefined (reading 'json')"
 *   There is no 'passthrough' return in thenCallback.
 *
 * Solution for generateAssistantResponse:
 *   We handle ALL requests to this endpoint ourselves:
 *   - Custom model  → call AWSQAdapter → return our event stream
 *   - Kiro native   → relay request to AWS Q via fetch → capture + return response
 *
 * This gives us full control over both paths and clean capture of native responses.
 *
 * For static block rules (telemetry, updates, metrics):
 *   Use thenReply() — no callback needed, no undefined risk.
 *
 * For dynamic block rules (getUsageLimits):
 *   Use .matching() to check the condition; let the fallback thenPassThrough
 *   handle the non-blocked case. Never use thenCallback for conditional passthrough.
 */

import mockttp                           from 'mockttp'
import type { Mockttp, CompletedRequest } from 'mockttp'

import type { TrafficRouter }            from './TrafficRouter.js'
import type { ModelRegistry }            from '../registry/ModelRegistry.js'
import { AWSQAdapter,
         encodeErrorResponse }           from '../adapter/AWSQAdapter.js'
import { InteractionLogger }             from '../debug/InteractionLogger.js'
import { log }                           from '../util/Logger.js'
import type { Config }                   from '../config/schema.js'

// ─── ProxyManager ─────────────────────────────────────────────────────────────

export class ProxyManager {

  private server:  Mockttp | null = null
  private adapter: AWSQAdapter
  private logger:  InteractionLogger

  constructor(
    private readonly router:   TrafficRouter,
    private readonly registry: ModelRegistry,
    private readonly config:   Config,
  ) {
    this.adapter = new AWSQAdapter(config)
    this.logger  = new InteractionLogger(config)
  }

  async start(port: number): Promise<string> {
    const https = await mockttp.generateCACertificate({ bits: 2048 })
    this.server = mockttp.getLocal({ https })

    await this.registerRules()
    await this.server.start(port)

    log.info(`[Proxy] HTTPS MITM proxy listening on port ${port}`)
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

  private async registerRules(): Promise<void> {
    const server = this.server!

    // ── 1. Static block rules — thenReply(), no callback risk ────────────────

    // Telemetry
    await server.forAnyRequest()
      .matching(req => (req.hostname ?? '').includes('telemetry'))
      .thenReply(200, '{"status":"ok"}', { 'content-type': 'application/json' })

    // Update checks (GET metadata-win32, or POST update/metadata)
    await server.forAnyRequest()
      .matching(req =>
        req.path.includes('metadata-win32') ||
        (req.method === 'POST' && (
          req.path.toLowerCase().includes('update') ||
          (req.path.toLowerCase().includes('metadata') && !req.path.includes('ListAvailableModels'))
        ))
      )
      .thenReply(200, '{"currentRelease":"0.9.40","releases":[]}', { 'content-type': 'application/json' })

    // Metrics / metering POST
    await server.forAnyRequest()
      .matching(req =>
        req.method === 'POST' && (
          req.path.toLowerCase().includes('metric') ||
          req.path.toLowerCase().includes('metering')
        )
      )
      .thenReply(200, '{"status":"ok"}', { 'content-type': 'application/json' })

    // ── 2. Usage limits — conditional block via .matching() ───────────────────
    // .matching() checks the dynamic condition. When matched → thenReply().
    // When not matched → falls through to the general thenPassThrough at the end.
    await server.forAnyRequest()
      .matching(req =>
        req.path.includes('getUsageLimits') &&
        this.router.shouldBlockUsageLimits()
      )
      .thenReply(
        200,
        '{"limits":[],"subscriptionInfo":{"type":"FREE"}}',
        { 'content-type': 'application/json' }
      )

    // ── 3. ListAvailableModels — passthrough with response body injection ─────
    await server.forAnyRequest()
      .matching(req => req.path.includes('ListAvailableModels'))
      .thenPassThrough({
        beforeResponse: async (response) => {
          let originalText: string
          try {
            originalText = await response.body.getText()
          } catch (err) {
            log.warn(`[Proxy] Could not read ListAvailableModels body: ${String(err)}`)
            return undefined
          }

          if (!originalText) {
            log.debug('[Proxy] ListAvailableModels response was empty — skipping injection')
            return undefined
          }

          log.debug(`[Proxy] ListAvailableModels received (${originalText.length} chars)`)

          try {
            const modifiedText  = this.registry.injectCustomModels(originalText)
            const modifiedBytes = Buffer.byteLength(modifiedText, 'utf-8')

            const headers = { ...response.headers }
            delete headers['content-length']
            delete headers['transfer-encoding']
            headers['content-length'] = modifiedBytes.toString()

            return { headers, body: modifiedText }
          } catch (err) {
            log.error('[Proxy] Model injection failed — returning original response', err)
            return undefined
          }
        },
      })

    // ── 4. generateAssistantResponse — full intercept, no undefined returns ───
    // We handle ALL requests: custom model → adapter, native → relay to AWS Q.
    // This is the only safe pattern for thenCallback with conditional routing.
    await server.forAnyRequest()
      .matching(req => req.path.includes('generateAssistantResponse'))
      .thenCallback(async (req) => {
        const body = await this.getBodyText(req)

        // Save request for debug capture
        const reqIndex = this.logger.saveRequest(
          body,
          req.url,
          req.headers as Record<string, string>,
        )

        const decision = this.router.decideRequest(
          req.method,
          req.hostname ?? '',
          req.path,
          body,
        )

        // ── Custom model path ───────────────────────────────────────────────
        if (decision.action === 'custom-model') {
          log.info(`[Proxy] → ${decision.provider.name} / ${decision.modelId}`)
          try {
            const responseBuffer = await this.adapter.handle(body, decision.provider)
            this.logger.saveResponse(responseBuffer, reqIndex)
            this.logger.saveResponseText(responseBuffer, reqIndex)
            return {
              status:  200,
              headers: { 'content-type': 'application/vnd.amazon.eventstream' },
              body:    responseBuffer,
            }
          } catch (err) {
            const message = err instanceof Error ? err.message : String(err)
            log.error(`[Proxy] Adapter error for ${decision.modelId}: ${message}`, err)
            const errorBuffer = encodeErrorResponse(message)
            this.logger.saveResponse(errorBuffer, reqIndex)
            return {
              status:  200,
              headers: { 'content-type': 'application/vnd.amazon.eventstream' },
              body:    errorBuffer,
            }
          }
        }

        // ── Native Kiro path — relay to AWS Q manually ──────────────────────
        // We cannot return undefined from thenCallback.
        // Instead, relay the request to AWS Q ourselves so we can also capture it.
        log.debug(`[Proxy] Native Kiro → relaying to AWS Q`)
        return this.relayToAWSQ(req, body, reqIndex)
      })

    // ── 5. Fallback — everything else passes through ─────────────────────────
    await server.forAnyRequest().thenPassThrough()

    log.debug('[Proxy] Rules registered')
  }

  // ─── Native AWS Q relay ───────────────────────────────────────────────────

  /**
   * Forward a native Kiro request to AWS Q and return the response.
   * This replaces the mockttp passthrough for generateAssistantResponse,
   * giving us the ability to capture the raw binary response.
   *
   * The Authorization header from the original request is preserved,
   * so Kiro's AWS credentials are forwarded as-is.
   */
  private async relayToAWSQ(
    req:      CompletedRequest,
    body:     string,
    reqIndex: number,
  ): Promise<{ status: number; headers: Record<string, string>; body: Buffer }> {
    try {
      const url = req.url

      // Build relay headers — forward everything except hop-by-hop headers
      const skipHeaders = new Set([
        'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
        'te', 'trailers', 'transfer-encoding', 'upgrade',
      ])
      const relayHeaders: Record<string, string> = {}
      for (const [key, value] of Object.entries(req.headers)) {
        if (!skipHeaders.has(key.toLowerCase()) && typeof value === 'string') {
          relayHeaders[key] = value
        }
      }

      const response = await fetch(url, {
        method:  req.method,
        headers: relayHeaders,
        body:    body || undefined,
      })

      // Read the raw binary response — AWS Q returns event stream binary
      const arrayBuffer = await response.arrayBuffer()
      const responseBuffer = Buffer.from(arrayBuffer)

      log.debug(`[Proxy] AWS Q relayed: ${response.status} (${responseBuffer.length} bytes)`)

      // Capture the response
      this.logger.saveResponse(responseBuffer, reqIndex)
      this.logger.saveResponseText(responseBuffer, reqIndex)

      // Build response headers
      const responseHeaders: Record<string, string> = {}
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value
      })
      // Ensure content-type is correct for event stream
      if (!responseHeaders['content-type']) {
        responseHeaders['content-type'] = 'application/vnd.amazon.eventstream'
      }
      // Remove transfer-encoding to avoid conflicts — we have a full buffer
      delete responseHeaders['transfer-encoding']
      responseHeaders['content-length'] = responseBuffer.length.toString()

      return {
        status:  response.status,
        headers: responseHeaders,
        body:    responseBuffer,
      }
    } catch (err) {
      log.error('[Proxy] Failed to relay to AWS Q', err)
      // Return a minimal error response so thenCallback doesn't crash
      const errorMsg = `Failed to relay to AWS Q: ${err instanceof Error ? err.message : String(err)}`
      return {
        status:  503,
        headers: { 'content-type': 'application/json' },
        body:    Buffer.from(JSON.stringify({ error: errorMsg })),
      }
    }
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  private async getBodyText(req: CompletedRequest): Promise<string> {
    try {
      return await req.body.getText()
    } catch {
      return ''
    }
  }
}
