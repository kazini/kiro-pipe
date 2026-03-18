/**
 * ModelRegistry
 *
 * Tracks which model IDs belong to Kiro and which are our custom ones.
 * Handles injecting custom models into Kiro's ListAvailableModels response.
 *
 * Lifecycle:
 *   1. Created at startup (both sets empty)
 *   2. ListAvailableModels response intercepted →
 *        injectCustomModels() populates both sets and returns modified JSON
 *   3. generateAssistantResponse arrives →
 *        TrafficRouter queries isCustomModel() to decide routing
 */

import type { Config, ProviderConfig, ModelConfig } from '../config/schema.js'
import { log } from '../util/Logger.js'

// ─── Kiro model list schema ───────────────────────────────────────────────────
// Only these fields are accepted by Kiro's model list parser.
// Anything else injected here will be silently ignored or break parsing.

interface KiroModelEntry {
  modelId:           string
  modelName:         string
  description:       string
  promptCaching: {
    maximumCacheCheckpointsPerRequest: number
    minimumTokensPerCacheCheckpoint:   number
    supportsPromptCaching:             boolean
  }
  rateMultiplier:       number | null
  rateUnit:             string
  supportedInputTypes:  string[]
  tokenLimits: {
    maxInputTokens:  number
    maxOutputTokens: number | null
  }
}

interface ModelListResponse {
  models: KiroModelEntry[]
  [key: string]: unknown   // preserve any other top-level fields
}

// ─── Default promptCaching / tokenLimits (used when no Kiro template exists) ──

const DEFAULT_PROMPT_CACHING: KiroModelEntry['promptCaching'] = {
  maximumCacheCheckpointsPerRequest: 4,
  minimumTokensPerCacheCheckpoint:   1024,
  supportsPromptCaching:             true,
}

const DEFAULT_TOKEN_LIMITS: KiroModelEntry['tokenLimits'] = {
  maxInputTokens:  200_000,
  maxOutputTokens: null,
}

// ─── ModelRegistry ────────────────────────────────────────────────────────────

export class ModelRegistry {

  /** Model IDs that came from AWS Q's real ListAvailableModels response. */
  private readonly kiroModelIds   = new Set<string>()

  /** Model IDs we injected from config — these get routed to custom providers. */
  private readonly customModelIds = new Set<string>()

  constructor(private readonly config: Config) {}

  // ── Queries ────────────────────────────────────────────────────────────────

  isKiroModel(modelId: string):   boolean { return this.kiroModelIds.has(modelId)   }
  isCustomModel(modelId: string): boolean { return this.customModelIds.has(modelId) }
  hasCustomModels():              boolean { return this.customModelIds.size > 0      }

  // ── ListAvailableModels response injection ─────────────────────────────────

  /**
   * Called when Kiro's ListAvailableModels response is intercepted.
   * Parses the original JSON, injects custom models, and returns modified JSON.
   * Also populates kiroModelIds and customModelIds as a side effect.
   *
   * @param originalJson  Raw response body from AWS Q
   * @returns             Modified JSON string with custom models appended
   */
  injectCustomModels(originalJson: string): string {
    let data: ModelListResponse
    try {
      data = JSON.parse(originalJson) as ModelListResponse
    } catch {
      log.warn('[ModelRegistry] Could not parse ListAvailableModels response — skipping injection')
      return originalJson
    }

    if (!Array.isArray(data.models)) {
      log.warn('[ModelRegistry] ListAvailableModels response has no models array — skipping injection')
      return originalJson
    }

    // ── Step 1: Track Kiro's native models and rename their rateUnit ──────────
    // Rename "Credit" → "Kiro Credits" so users can visually distinguish
    // Kiro's own quota from our custom model cost display.
    for (const model of data.models) {
      this.kiroModelIds.add(model.modelId)
      if (model.rateUnit === 'Credit') {
        model.rateUnit = 'Kiro Credits'
      }
    }

    // ── Step 2: Capture template from first Kiro model ────────────────────────
    // We copy promptCaching and tokenLimits from the first real model so our
    // injected entries look native and don't confuse Kiro's UI.
    const templateModel  = data.models[0]
    const promptCaching  = templateModel?.promptCaching  ?? DEFAULT_PROMPT_CACHING
    const tokenLimits    = templateModel?.tokenLimits    ?? DEFAULT_TOKEN_LIMITS

    log.debug(`[ModelRegistry] Kiro native models: ${this.kiroModelIds.size}`)

    // ── Step 3: Inject custom models from config ──────────────────────────────
    let injectedCount = 0

    for (const [providerName, providerConfig] of Object.entries(this.config.providers)) {
      if (!providerConfig.enabled || providerConfig.type === 'passthrough') continue

      for (const modelConfig of providerConfig.models) {
        const entry = this.buildInjectedEntry(
          modelConfig,
          providerConfig,
          providerName,
          promptCaching,
          tokenLimits,
        )

        // Check for modelId collision with existing models (e.g. debug override)
        const existingIndex = data.models.findIndex(m => m.modelId === entry.modelId)
        if (existingIndex !== -1) {
          log.debug(`[ModelRegistry] Overriding existing model: ${entry.modelId}`)
          data.models[existingIndex] = entry
        } else {
          data.models.push(entry)
        }

        this.customModelIds.add(entry.modelId)
        injectedCount++
      }
    }

    if (injectedCount > 0) {
      log.info(`[ModelRegistry] Injected ${injectedCount} custom model(s) into model list`)
    } else {
      log.debug('[ModelRegistry] No custom models to inject (all providers disabled or have no models)')
    }

    return JSON.stringify(data)
  }

  // ─── Internal helpers ──────────────────────────────────────────────────────

  private buildInjectedEntry(
    model:         ModelConfig,
    provider:      ProviderConfig,
    providerName:  string,
    promptCaching: KiroModelEntry['promptCaching'],
    tokenLimits:   KiroModelEntry['tokenLimits'],
  ): KiroModelEntry {

    // Display name priority: display_name → first alias → model.name
    const modelName =
      model.display_name ??
      (model.alias.length > 0 ? model.alias[0]! : model.name)

    // Determine cost display
    // Phase 2: static from config or UNKNOWN.
    // Phase 4 (CostCache): will be replaced with live data.
    const { rateMultiplier, rateUnit } = this.resolveCostDisplay(
      model,
      providerName,
    )

    return {
      modelId:     model.name,    // model.name IS the injected modelId
      modelName,
      description: model.description || provider.description || `${providerName} model`,
      promptCaching,
      rateMultiplier,
      rateUnit,
      supportedInputTypes: ['TEXT', 'IMAGE'],
      tokenLimits: {
        maxInputTokens:  model.max_input_tokens,
        maxOutputTokens: null,
      },
    }
  }

  /**
   * Determine rateMultiplier and rateUnit for an injected model.
   *
   * Priority order (Phase 2 — no CostCache yet):
   *   1. Config-provided cost override
   *   2. Provider name in uppercase (e.g. "ANTHROPIC") as a readable label
   *
   * Phase 4 will add:
   *   1. RateLimitTracker live quota data → "% Quota"
   *   2. CostCache → "FREE" or "$/1M Token"
   */
  private resolveCostDisplay(
    model:        ModelConfig,
    providerName: string,
  ): { rateMultiplier: number | null; rateUnit: string } {

    // Config cost override takes highest priority
    if (
      model.cost_per_1m_input_tokens  !== undefined &&
      model.cost_per_1m_output_tokens !== undefined
    ) {
      const avg = (model.cost_per_1m_input_tokens + model.cost_per_1m_output_tokens) / 2
      if (avg === 0) {
        return { rateMultiplier: null, rateUnit: 'FREE' }
      }
      return { rateMultiplier: Math.round(avg * 100) / 100, rateUnit: '$/1M Token' }
    }

    // Fall back to provider name label — at least shows which provider it's from
    return { rateMultiplier: null, rateUnit: providerName.toUpperCase() }
  }
}
