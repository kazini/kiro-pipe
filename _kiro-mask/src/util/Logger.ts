/**
 * Logger
 * Chalk-based console logger with levels, timestamps, and optional prefixes.
 * Levels: debug < info < warn < error
 */

import chalk from 'chalk'

// ─── Types ───────────────────────────────────────────────────────────────────

export type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const LEVEL_RANK: Record<LogLevel, number> = {
  debug: 0,
  info:  1,
  warn:  2,
  error: 3,
}

// ─── Singleton state ──────────────────────────────────────────────────────────

let currentLevel: LogLevel = 'info'

// ─── Public API ───────────────────────────────────────────────────────────────

/** Set the minimum level that will be printed. */
export function setLevel(level: LogLevel): void {
  currentLevel = level
}

export const log = {

  debug(msg: string, meta?: unknown): void {
    if (!shouldPrint('debug')) return
    const prefix = chalk.dim.gray(`[${ts()}] DBG`)
    print(prefix, chalk.dim(msg), meta)
  },

  info(msg: string, meta?: unknown): void {
    if (!shouldPrint('info')) return
    const prefix = chalk.cyan(`[${ts()}] INF`)
    print(prefix, msg, meta)
  },

  warn(msg: string, meta?: unknown): void {
    if (!shouldPrint('warn')) return
    const prefix = chalk.yellow(`[${ts()}] WRN`)
    print(prefix, chalk.yellow(msg), meta)
  },

  error(msg: string, errOrMeta?: unknown): void {
    if (!shouldPrint('error')) return
    const prefix = chalk.red(`[${ts()}] ERR`)
    print(prefix, chalk.red(msg), errOrMeta)
    if (errOrMeta instanceof Error && errOrMeta.stack) {
      console.error(chalk.dim(errOrMeta.stack))
    }
  },

  // ── Structured display helpers (used in startup banner) ──────────────────

  /** Bold section heading */
  section(title: string): void {
    console.log()
    console.log(chalk.bold.cyan(`  ▸ ${title}`))
  },

  /** Key–value line, indented */
  kv(key: string, value: unknown, note?: string): void {
    const keyStr   = chalk.dim(key.padEnd(28))
    const valStr   = valueColour(value)
    const noteStr  = note ? chalk.dim.italic(`  ${note}`) : ''
    console.log(`    ${keyStr} ${valStr}${noteStr}`)
  },

  /** Separator line */
  rule(): void {
    console.log(chalk.dim('  ' + '─'.repeat(58)))
  },

  /** Blank line */
  blank(): void {
    console.log()
  },
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

function shouldPrint(level: LogLevel): boolean {
  return LEVEL_RANK[level] >= LEVEL_RANK[currentLevel]
}

function ts(): string {
  return new Date().toISOString().slice(11, 23)  // HH:MM:SS.mmm
}

function print(prefix: string, msg: string, meta?: unknown): void {
  if (meta !== undefined) {
    console.log(`${prefix}  ${msg}`)
    console.log(chalk.dim(JSON.stringify(meta, null, 2)
      .split('\n')
      .map(l => '        ' + l)
      .join('\n')))
  } else {
    console.log(`${prefix}  ${msg}`)
  }
}

function valueColour(value: unknown): string {
  if (value === true)  return chalk.green('true')
  if (value === false) return chalk.red('false')
  if (value === null || value === undefined) return chalk.dim('—')
  if (typeof value === 'number') return chalk.yellow(String(value))
  return chalk.white(String(value))
}
