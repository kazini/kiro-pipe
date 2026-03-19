/**
 * TrafficRouter
 *
 * Pure routing decisions — no I/O, no async, fully unit-testable.
 * Given a request's method / host / path / body, returns a RouteDecision.
 * ProxyManager consumes this to determine what to do with each request.
 */

import type { Config, ResolvedProvider } from '../config/schema.js'
import type { ModelRegistry }            from '../registry/ModelRegistry.js'

// ─── Route decision types ─────────────────────────────────────────────────────

export type RouteDecision =
  | { action: 'block';            status: number; body: string; contentType: string }
  | { action: 'passthrough' }
  | { action: 'intercept-response' }   // pass request through, transform the response
  | { action: 'custom-model';     modelId: string; provider: ResolvedProvider }

// ─── Canned block responses ───────────────────────────────────────────────────
// Always 200 OK — returning 4xx/5xx causes Kiro to enter an error state.

function blockOk(body: string): RouteDecision {
  return { action: 'block', status: 200, body, contentType: 'application/json' }
}

const BLOCKED = {
  telemetry:   blockOk('{"status":"ok"}'),
  updates:     blockOk('{"currentRelease":"0.9.40","releases":[]}'),
  metrics:     blockOk('{"status":"ok"}'),
  usageLimits: blockOk('{"limits":[],"subscriptionInfo":{"type":"FREE"}}'),
} as const

// ─── TrafficRouter ────────────────────────────────────────────────────────────

export class TrafficRouter {

  private readonly startedAt: number

  constructor(
    private readonly config:   Config,
    private readonly registry: ModelRegistry,
    startedAt?: number,
  ) {
    this.startedAt = startedAt ?? Date.now()
  }

  /**
   * Decide what to do with an intercepted request.
   * Rules are evaluated in priority order — first match wins.
   */
  decideRequest(
    method: string,
    host:   string,
    path:   string,
    body?:  string,
  ): RouteDecision {

    const ep = this.config.kiro_endpoint

    // ── 1. Telemetry ──────────────────────────────────────────────────────────
    if (!ep.telemetry && host.includes('telemetry')) {
      return BLOCKED.telemetry
    }

    // ── 2. Update checks ─────────────────────────────────────────────────────
    if (!ep.updates) {
      if (path.includes('metadata-win32')) {
        return BLOCKED.updates
      }
      if (method === 'POST' &&
          (path.toLowerCase().includes('update') ||
           path.toLowerCase().includes('metadata'))) {
        return BLOCKED.updates
      }
    }

    // ── 3. Metrics / metering (POST only) ────────────────────────────────────
    if (!ep.telemetry &&
        method === 'POST' &&
        (path.toLowerCase().includes('metric') ||
         path.toLowerCase().includes('metering'))) {
      return BLOCKED.metrics
    }

    // ── 4. Usage limits ───────────────────────────────────────────────────────
    if (path.includes('getUsageLimits') && this.shouldBlockUsageLimits()) {
      return BLOCKED.usageLimits
    }

    // ── 5. ListAvailableModels ────────────────────────────────────────────────
    // Let the request reach AWS Q, but intercept and modify the response.
    if (path.includes('ListAvailableModels')) {
      return { action: 'intercept-response' }
    }

    // ── 6. generateAssistantResponse ─────────────────────────────────────────
    if (path.includes('generateAssistantResponse')) {
      return this.routeAssistantRequest(body)
    }

    // ── Fallback ──────────────────────────────────────────────────────────────
    return { action: 'passthrough' }
  }

  // ─── Internal helpers ──────────────────────────────────────────────────────

  /**
   * Usage limits blocking logic:
   *   - force_usage_limits: true  → always allow (don't block)
   *   - force_usage_limits: false → always block
   *   - force_usage_limits: null  → block during 5s startup window
   *                                 OR whenever custom models are loaded
   *
   * The startup window handles the race between Kiro's first requests
   * and our ListAvailableModels injection completing.
   */
  shouldBlockUsageLimits(): boolean {
    const force = this.config.kiro_endpoint.force_usage_limits
    if (force === true)  return false   // always allow
    if (force === false) return true    // always block

    const uptimeMs = Date.now() - this.startedAt
    return uptimeMs < 5_000 || this.registry.hasCustomModels()
  }

  /**
   * Route a generateAssistantResponse request.
   * Extracts the modelId from the AWS Q request body and decides:
   *   - known custom model → custom-model (route to provider)
   *   - kiro model or unknown → passthrough (let AWS Q handle it)
   */
  private routeAssistantRequest(body?: string): RouteDecision {
    if (!body) return { action: 'passthrough' }

    let modelId: string | undefined
    try {
      const parsed        = JSON.parse(body) as Record<string, unknown>
      const convState     = parsed['conversationState']     as Record<string, unknown> | undefined
      const currentMsg    = convState?.['currentMessage']   as Record<string, unknown> | undefined
      const userInput     = currentMsg?.['userInputMessage'] as Record<string, unknown> | undefined
      modelId             = userInput?.['modelId']           as string | undefined
    } catch {
      // Unparseable body — let AWS Q handle it
      return { action: 'passthrough' }
    }

    if (!modelId) return { action: 'passthrough' }

    // Route to custom provider if we recognise this model
    if (this.registry.isCustomModel(modelId)) {
      const provider = this.findProviderForModel(modelId)
      if (provider) {
        return { action: 'custom-model', modelId, provider }
      }
    }

    // Kiro model or unrecognised — passthrough
    return { action: 'passthrough' }
  }

  /**
   * Find which enabled non-passthrough provider owns a given modelId.
   * Checks both model.name and model.alias[].
   */
  private findProviderForModel(modelId: string): ResolvedProvider | null {
    for (const [name, pc] of Object.entries(this.config.providers)) {
      if (!pc.enabled || pc.type === 'passthrough') continue
      for (const model of pc.models) {
        if (model.name === modelId || model.alias.includes(modelId)) {
          return { name, config: pc }
        }
      }
    }
    return null
  }
}
