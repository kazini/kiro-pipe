/**
 * KiroMask — main entry point
 *
 * Boot sequence:
 *   1. Load and validate config
 *   2. Configure logger level
 *   3. Print startup banner and config summary
 *   4. Validate providers
 *   5. Assert single instance (exit if another KiroMask is already running)
 *   6. Start proxy
 *   7. Launch Kiro and await exit → graceful shutdown
 *
 * Run:  npx tsx src/index.ts [--config path/to/config.yaml]
 */

import path  from 'node:path'
import chalk from 'chalk'

import { log, setLevel }  from './util/Logger.js'
import { ConfigManager }  from './config/ConfigManager.js'
import { ModelRegistry }  from './registry/ModelRegistry.js'
import { TrafficRouter }  from './proxy/TrafficRouter.js'
import { ProxyManager }   from './proxy/ProxyManager.js'
import { KiroLauncher }   from './launcher/KiroLauncher.js'
import type { Config }    from './config/schema.js'

// ─── CLI args ─────────────────────────────────────────────────────────────────

function parseArgs(): { configPath?: string } {
  const args     = process.argv.slice(2)
  const cfgIndex = args.findIndex(a => a === '--config' || a === '-c')
  if (cfgIndex !== -1 && args[cfgIndex + 1]) {
    return { configPath: path.resolve(args[cfgIndex + 1]!) }
  }
  return {}
}

// ─── Banner ───────────────────────────────────────────────────────────────────

function printBanner(): void {
  console.log()
  console.log(chalk.bold.cyan('  ██╗  ██╗██╗██████╗  ██████╗   ███╗   ███╗ █████╗ ███████╗██╗  ██╗'))
  console.log(chalk.bold.cyan('  ██║ ██╔╝██║██╔══██╗██╔═══██╗  ████╗ ████║██╔══██╗██╔════╝██║ ██╔╝'))
  console.log(chalk.bold.cyan('  █████╔╝ ██║██████╔╝██║   ██║  ██╔████╔██║███████║███████╗█████╔╝ '))
  console.log(chalk.bold.cyan('  ██╔═██╗ ██║██╔══██╗██║   ██║  ██║╚██╔╝██║██╔══██║╚════██║██╔═██╗ '))
  console.log(chalk.bold.cyan('  ██║  ██╗██║██║  ██║╚██████╔╝  ██║ ╚═╝ ██║██║  ██║███████║██║  ██╗'))
  console.log(chalk.bold.cyan('  ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝   ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝'))
  console.log()
  console.log(chalk.dim('  Intercept Kiro · Route to custom LLM providers · v0.1.0'))
  console.log(chalk.dim('  ' + '─'.repeat(58)))
  console.log()
}

// ─── Startup summary ──────────────────────────────────────────────────────────

function printConfigSummary(cfg: Config): void {

  // ── Proxy ──
  log.section('Proxy')
  log.kv('Port', cfg.proxy.port)
  log.blank()

  // ── Kiro ──
  log.section('Kiro')
  log.kv('Exe path', cfg.kiro.exe_path ?? null, 'auto-detect')
  log.blank()

  // ── Endpoint policy ──
  log.section('Kiro Endpoint Policy')
  log.kv('Telemetry',    cfg.kiro_endpoint.telemetry,   'true = allow, false = block')
  log.kv('Updates',      cfg.kiro_endpoint.updates)
  log.kv('Kiro models',  cfg.kiro_endpoint.models)
  log.kv('Usage limits', formatUsageLimits(cfg.kiro_endpoint.force_usage_limits))
  log.blank()

  // ── Portkey ──
  log.section('Portkey')
  log.kv('Enabled', cfg.portkey.enabled)
  if (cfg.portkey.enabled) {
    log.kv('API key', cfg.portkey.api_key ? '✓ set' : null)
  }
  log.blank()

  // ── Providers ──
  log.section('Providers')
  const providers = Object.entries(cfg.providers)
  if (providers.length === 0) {
    log.kv('(none configured)', null)
  }
  for (const [name, pc] of providers) {
    if (!pc.enabled) continue
    const typeLabel = pc.type === 'passthrough'
      ? 'passthrough'
      : `${pc.type} → ${pc.api_base ?? 'api_base not set'}`
    log.kv(name, pc.description ?? typeLabel)
    for (const model of pc.models) {
      const aliasStr = model.alias.length
        ? chalk.dim(` [${model.alias.join(', ')}]`)
        : ''
      console.log(chalk.dim(`      • ${model.display_name ?? model.name}${aliasStr}`))
    }
    if (pc.models.length === 0) {
      console.log(chalk.yellow(
        '      (no models configured — enable discover_models: true to populate at startup)'
      ))
    }
  }

  const disabled = providers.filter(([, pc]) => !pc.enabled)
  if (disabled.length) {
    log.blank()
    console.log(chalk.dim(
      `  (${disabled.length} disabled provider(s): ${disabled.map(([n]) => n).join(', ')})`
    ))
  }
  log.blank()

  // ── Debug ──
  if (cfg.debug.enabled) {
    log.section('Debug')
    log.kv('Log level',         cfg.debug.log_level)
    log.kv('Save interactions', cfg.debug.save_interactions)
    if (cfg.debug.save_interactions) {
      log.kv('Output dir', cfg.debug.output_dir)
    }
    log.blank()
  }

  log.rule()
  log.blank()
}

function formatUsageLimits(force: boolean | null): string {
  if (force === true)  return 'always allow'
  if (force === false) return 'always block'
  return 'auto  (block when custom models are active)'
}

// ─── Graceful shutdown ────────────────────────────────────────────────────────

function registerShutdownHandlers(onShutdown: () => Promise<void>): void {
  let shuttingDown = false

  const shutdown = async (signal: string): Promise<void> => {
    if (shuttingDown) return
    shuttingDown = true
    log.blank()
    log.info(`Received ${signal} — shutting down…`)
    try {
      await onShutdown()
      log.info('Clean shutdown complete.')
    } catch (err) {
      log.error('Error during shutdown', err)
    }
    process.exit(0)
  }

  process.on('SIGINT',             () => { void shutdown('SIGINT')  })
  process.on('SIGTERM',            () => { void shutdown('SIGTERM') })
  process.on('uncaughtException',  (err)    => { log.error('Uncaught exception', err);        process.exit(1) })
  process.on('unhandledRejection', (reason) => { log.error('Unhandled promise rejection', reason); process.exit(1) })
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {

  printBanner()

  // ── 1. Load config ──────────────────────────────────────────────────────────
  const { configPath } = parseArgs()
  let configManager: ConfigManager
  try {
    configManager = ConfigManager.load(configPath)
  } catch (err) {
    console.error(chalk.red('\n  ✖ Config error:'), String(err))
    process.exit(1)
  }

  const cfg = configManager.raw

  // ── 2. Configure logger ─────────────────────────────────────────────────────
  setLevel(cfg.debug.enabled ? cfg.debug.log_level : 'info')

  // ── 3. Print startup summary ────────────────────────────────────────────────
  printConfigSummary(cfg)

  // ── 4. Validate providers ───────────────────────────────────────────────────
  const customProviders = configManager.getCustomProviders()
  const kiroEnabled     = cfg.providers['kiro']?.enabled ?? false

  if (!kiroEnabled && customProviders.length === 0) {
    console.error(chalk.red(
      '  ✖ No providers are enabled.\n' +
      '    Enable at least one provider in kiromask.config.yaml.\n'
    ))
    process.exit(1)
  }

  for (const provider of customProviders) {
    const key = configManager.resolveApiKey(provider)
    if (!key) {
      log.warn(
        `Provider "${provider.name}" is enabled but has no API key. ` +
        `Set api_key in config or the ${provider.name.toUpperCase()}_API_KEY env var.`
      )
    }
  }

  log.info('Config loaded successfully.')
  log.blank()

  // ── 5. Assert single instance ───────────────────────────────────────────────
  // Exits this process immediately if another KiroMask is already running.
  // The existing instance is never touched — the newcomer yields.
  const launcher = new KiroLauncher(cfg)
  launcher.assertSingleInstance()

  // ── 6. Create components ────────────────────────────────────────────────────
  const startedAt = Date.now()
  const registry  = new ModelRegistry(cfg)
  const router    = new TrafficRouter(cfg, registry, startedAt)
  const proxy     = new ProxyManager(router, registry, cfg)

  // ── 7. Register shutdown handler ────────────────────────────────────────────
  registerShutdownHandlers(async () => {
    await proxy.stop()
  })

  // ── 8. Start proxy ──────────────────────────────────────────────────────────
  try {
    await proxy.start(cfg.proxy.port)
  } catch (err) {
    console.error(chalk.red(`\n  ✖ Failed to start proxy on port ${cfg.proxy.port}:`), String(err))
    console.error(chalk.dim('    Is the port already in use?'))
    process.exit(1)
  }

  // ── 9. Launch Kiro ──────────────────────────────────────────────────────────
  try {
    await launcher.launch(cfg.proxy.port)
    // Resolves when the user closes Kiro
    log.info('Kiro exited — shutting down KiroMask.')
    await proxy.stop()
    process.exit(0)
  } catch (err) {
    console.error(chalk.red('\n  ✖ Launcher error:'), String(err))
    process.exit(1)
  }
}

main().catch((err) => {
  console.error(chalk.red('Fatal error:'), err)
  process.exit(1)
})
