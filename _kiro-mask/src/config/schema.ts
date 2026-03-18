/**
 * Configuration schema
 * Zod schemas for kiromask.config.yaml validation.
 * Types are inferred from schemas — no manual interface duplication.
 */

import { z } from 'zod'

// ─── Sub-schemas ──────────────────────────────────────────────────────────────

export const RetryConfigSchema = z.object({
  max_attempts:    z.number().int().min(1).default(3),
  base_delay_ms:   z.number().int().min(0).default(1000),
  max_delay_ms:    z.number().int().min(0).default(30_000),
  jitter_factor:   z.number().min(0).max(1).default(0.25),
  retry_on_status: z.array(z.number().int()).default([429, 500, 502, 503, 504]),
})

export const ModelConfigSchema = z.object({
  name:         z.string().min(1),
  display_name: z.string().optional(),
  alias:        z.array(z.string()).default([]),
  description:  z.string().default(''),
  max_tokens:       z.number().int().positive().default(4096),
  max_input_tokens: z.number().int().positive().default(200_000),
  // Optional cost overrides — take priority over all fetched data
  cost_per_1m_input_tokens:  z.number().nonnegative().optional(),
  cost_per_1m_output_tokens: z.number().nonnegative().optional(),
})

export const ProviderConfigSchema = z.object({
  enabled:             z.boolean().default(false),
  type:                z.enum(['passthrough', 'anthropic', 'openai']),
  description:         z.string().optional(),
  api_base:            z.string().url().optional(),
  api_key:             z.string().nullable().default(null),
  portkey_virtual_key: z.string().nullable().default(null),
  discover_models:     z.boolean().default(false),
  model_filter:        z.string().nullable().default(null),
  retry:               RetryConfigSchema.default({}),
  models:              z.array(ModelConfigSchema).default([]),
})

// ─── Root schema ──────────────────────────────────────────────────────────────

export const ConfigSchema = z.object({

  proxy: z.object({
    port: z.number().int().min(1024).max(65535).default(29974),
  }).default({}),

  kiro: z.object({
    exe_path: z.string().nullable().default(null),
  }).default({}),

  // true = allow through to AWS Q, false = block
  kiro_endpoint: z.object({
    telemetry:            z.boolean().default(false),
    updates:              z.boolean().default(false),
    models:               z.boolean().default(true),
    // null = auto (block when custom models exist or within startup window)
    // true  = always allow
    // false = always block
    force_usage_limits:   z.boolean().nullable().default(null),
  }).default({}),

  portkey: z.object({
    enabled: z.boolean().default(false),
    api_key: z.string().nullable().default(null),
  }).default({}),

  debug: z.object({
    enabled:           z.boolean().default(false),
    log_level:         z.enum(['error', 'warn', 'info', 'debug']).default('info'),
    save_interactions: z.boolean().default(false),
    output_dir:        z.string().default('./logs'),
  }).default({}),

  providers: z.record(z.string(), ProviderConfigSchema).default({
    kiro: {
      enabled:         true,
      type:            'passthrough',
      description:     "Kiro's default AWS Q models",
      api_base:        undefined,
      api_key:         null,
      portkey_virtual_key: null,
      discover_models: false,
      model_filter:    null,
      retry: {
        max_attempts:    1,
        base_delay_ms:   0,
        max_delay_ms:    0,
        jitter_factor:   0,
        retry_on_status: [],
      },
      models: [{
        name:        'kiro-default',
        alias:       ['kiro', 'default', 'aws-q'],
        description: "Kiro's default model",
        max_tokens:       4096,
        max_input_tokens: 200_000,
      }],
    },
  }),

})

// ─── Inferred types ───────────────────────────────────────────────────────────

export type Config         = z.infer<typeof ConfigSchema>
export type ProviderConfig = z.infer<typeof ProviderConfigSchema>
export type ModelConfig    = z.infer<typeof ModelConfigSchema>
export type RetryConfig    = z.infer<typeof RetryConfigSchema>

// ─── Derived helper types (not in YAML, built at load time) ──────────────────

/** A provider with its name attached — used after config is loaded. */
export interface ResolvedProvider {
  name:   string
  config: ProviderConfig
}

/** A model with its provider attached — used for routing decisions. */
export interface ResolvedModel {
  modelName:  string   // the config `name` field — also the injected modelId
  provider:   ResolvedProvider
  config:     ModelConfig
}
