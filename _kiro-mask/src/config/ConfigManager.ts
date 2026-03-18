/**
 * ConfigManager
 * Loads kiromask.config.yaml, validates with Zod, provides typed lookup helpers.
 * Falls back to schema defaults if the file doesn't exist.
 * Fails fast with clear messages on invalid YAML or schema violations.
 */

import fs   from 'node:fs'
import path from 'node:path'
import YAML  from 'yaml'
import { ZodError } from 'zod'

import {
  ConfigSchema,
  type Config,
  type ResolvedProvider,
  type ResolvedModel,
} from './schema.js'

import { log } from '../util/Logger.js'

// ─── Default config search paths (relative to cwd) ───────────────────────────

const SEARCH_PATHS = [
  'kiromask.config.yaml',
  'kiromask.config.yml',
]

// ─── ConfigManager ────────────────────────────────────────────────────────────

export class ConfigManager {

  private readonly config: Config

  /**
   * Map of model name/alias → ResolvedModel.
   * Built once at construction time.
   */
  private readonly modelMap = new Map<string, ResolvedModel>()

  private constructor(config: Config) {
    this.config = config
    this.buildModelMap()
  }

  // ── Factory ────────────────────────────────────────────────────────────────

  /**
   * Load and validate config from a YAML file.
   * If `configPath` is not supplied, searches SEARCH_PATHS relative to cwd.
   * If no file is found, falls back to schema defaults (Kiro passthrough only).
   * Throws on invalid YAML syntax or schema validation failure.
   */
  static load(configPath?: string): ConfigManager {
    const filePath = configPath ?? ConfigManager.findConfigFile()

    if (!filePath) {
      log.warn('No config file found — using defaults (Kiro passthrough only)')
      const config = ConfigSchema.parse({})
      return new ConfigManager(config)
    }

    log.info(`Loading config from ${filePath}`)

    let raw: string
    try {
      raw = fs.readFileSync(filePath, 'utf8')
    } catch (err) {
      throw new Error(`Cannot read config file at "${filePath}": ${String(err)}`)
    }

    let parsed: unknown
    try {
      parsed = YAML.parse(raw)
    } catch (err) {
      throw new Error(
        `Invalid YAML in "${filePath}".\n` +
        `  ${String(err)}\n` +
        `  Validate your file at https://www.yamllint.com/`
      )
    }

    let config: Config
    try {
      config = ConfigSchema.parse(parsed ?? {})
    } catch (err) {
      if (err instanceof ZodError) {
        const issues = err.issues
          .map(i => `  • ${i.path.join('.')} — ${i.message}`)
          .join('\n')
        throw new Error(`Config validation failed in "${filePath}":\n${issues}`)
      }
      throw err
    }

    return new ConfigManager(config)
  }

  // ── Accessors ──────────────────────────────────────────────────────────────

  get raw(): Readonly<Config> {
    return this.config
  }

  /**
   * Look up a model by its exact name or any alias.
   * Returns null if not found or the model's provider is disabled.
   */
  getModel(modelId: string): ResolvedModel | null {
    return this.modelMap.get(modelId) ?? null
  }

  /**
   * Get all enabled providers in config order.
   * Passthrough provider is always included if enabled.
   */
  getEnabledProviders(): ResolvedProvider[] {
    return Object.entries(this.config.providers)
      .filter(([, pc]) => pc.enabled)
      .map(([name, config]) => ({ name, config }))
  }

  /**
   * Get all enabled non-passthrough providers
   * (i.e. providers that route to real LLMs).
   */
  getCustomProviders(): ResolvedProvider[] {
    return this.getEnabledProviders()
      .filter(p => p.config.type !== 'passthrough')
  }

  /**
   * True if this model should be passed through to AWS Q unchanged.
   */
  isKiroPassthrough(modelId: string): boolean {
    const model = this.getModel(modelId)
    return model?.provider.config.type === 'passthrough'
  }

  /**
   * Resolve the effective API key for a provider:
   * config value → env var fallback → null.
   */
  resolveApiKey(provider: ResolvedProvider): string | null {
    if (provider.config.api_key) return provider.config.api_key

    // Env var conventions per provider type
    const envMap: Record<string, string> = {
      anthropic: 'ANTHROPIC_API_KEY',
      openai:    'OPENAI_API_KEY',
    }
    const envKey = envMap[provider.name] ?? `${provider.name.toUpperCase()}_API_KEY`
    return process.env[envKey] ?? null
  }

  // ── Internal ───────────────────────────────────────────────────────────────

  /**
   * Walk all enabled providers and build the modelMap.
   * A model's `name` AND each alias are registered as keys.
   * If a name collides across providers, the later provider wins with a warning.
   */
  private buildModelMap(): void {
    for (const [providerName, providerConfig] of Object.entries(this.config.providers)) {
      if (!providerConfig.enabled) continue

      const provider: ResolvedProvider = { name: providerName, config: providerConfig }

      for (const modelConfig of providerConfig.models) {
        const resolved: ResolvedModel = {
          modelName: modelConfig.name,
          provider,
          config: modelConfig,
        }

        const keys = [modelConfig.name, ...modelConfig.alias]
        for (const key of keys) {
          if (this.modelMap.has(key)) {
            log.warn(
              `Model identifier "${key}" is defined in multiple providers. ` +
              `"${providerName}" will override the earlier definition.`
            )
          }
          this.modelMap.set(key, resolved)
        }
      }
    }
  }

  private static findConfigFile(): string | null {
    for (const candidate of SEARCH_PATHS) {
      const resolved = path.resolve(process.cwd(), candidate)
      if (fs.existsSync(resolved)) return resolved
    }
    return null
  }
}
