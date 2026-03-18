/**
 * KiroLauncher
 *
 * Finds, spawns, and monitors Kiro.exe.
 * KiroMask works as a proxy regardless of whether it spawned Kiro itself —
 * if Kiro is already running, its traffic will be intercepted automatically.
 *
 * ── Single-instance enforcement ──────────────────────────────────────────────
 * A lock file (.kiromask.lock) is written to the program folder on startup,
 * containing our PID. On a new launch attempt:
 *   - If the lock file exists AND the PID inside is still a running process
 *     → exit immediately (existing instance wins, newcomer yields)
 *   - If the lock file exists but the PID is dead (crash/power loss)
 *     → delete the stale lock and continue normally
 *   - If no lock file exists → continue normally
 * The lock file is deleted on clean exit via a registered handler.
 *
 * ── exe_path resolution ───────────────────────────────────────────────────────
 * kiro.exe_path in config:
 *   null            → auto-detect from KIRO_SEARCH_PATHS
 *   ends in .exe    → treat as a direct path to the executable
 *   anything else   → treat as a folder; search inside for *.exe,
 *                     preferring a file literally named Kiro.exe
 * In all cases where the configured path is not found, a warning is printed
 * and auto-detection is attempted as fallback.
 */

import { spawn, execSync }                        from 'node:child_process'
import { existsSync, readdirSync,
         writeFileSync, readFileSync, unlinkSync } from 'node:fs'
import path                                        from 'node:path'
import os                                          from 'node:os'
import chalk                                       from 'chalk'

import type { Config }                             from '../config/schema.js'
import { log }                                     from '../util/Logger.js'

// ─── Lock file path ───────────────────────────────────────────────────────────
// Placed in the directory of the running script (the program folder).
// Using __dirname equivalent via import.meta is not available with tsx
// when running directly, so we anchor to process.cwd() which tsx sets to
// the project root — consistent with where the user runs `npx tsx src/index.ts`.

const LOCK_FILE = path.resolve(process.cwd(), '.kiromask.lock')

// ─── Auto-detect search paths ─────────────────────────────────────────────────

const KIRO_SEARCH_PATHS: string[] = [
  'Kiro/Kiro.exe',
  'Kiro.exe',
  path.join(os.homedir(), 'AppData/Local/Programs/Kiro/Kiro.exe'),
  path.join(os.homedir(), 'AppData/Local/Kiro/Kiro.exe'),
]

// ─── KiroLauncher ─────────────────────────────────────────────────────────────

export class KiroLauncher {

  constructor(private readonly config: Config) {}

  // ─── Single-instance enforcement ──────────────────────────────────────────

  /**
   * Check the lock file. If a live instance is found, exit this process.
   * If the lock is stale (process gone), remove it and continue.
   * Then write our own PID to the lock file and register cleanup on exit.
   */
  assertSingleInstance(): void {
    if (existsSync(LOCK_FILE)) {
      let lockedPid: number | null = null

      try {
        const contents = readFileSync(LOCK_FILE, 'utf8').trim()
        lockedPid = parseInt(contents, 10)
      } catch {
        // Unreadable lock — treat as stale
        log.debug('[Launcher] Lock file unreadable — treating as stale')
      }

      if (lockedPid !== null && !isNaN(lockedPid)) {
        if (this.isProcessAlive(lockedPid)) {
          // A live KiroMask is already running — yield to it
          console.error(
            chalk.red('\n  ✖ KiroMask is already running.') + '\n' +
            chalk.dim(`    Existing instance PID: ${lockedPid}\n`) +
            chalk.dim('    Close the existing instance before starting a new one.\n')
          )
          process.exit(1)
        } else {
          // PID is dead — stale lock from a crash or abrupt exit
          log.debug(`[Launcher] Stale lock file found (PID ${lockedPid} is not running) — removing`)
          this.removeLockFile()
        }
      } else {
        // Lock file contained garbage — remove it
        this.removeLockFile()
      }
    }

    // Write our PID and register cleanup
    this.writeLockFile()
  }

  private writeLockFile(): void {
    try {
      writeFileSync(LOCK_FILE, String(process.pid), 'utf8')
      log.debug(`[Launcher] Lock file written (PID: ${process.pid})`)

      // Clean up on any form of exit
      const cleanup = () => this.removeLockFile()
      process.on('exit',    cleanup)
      process.on('SIGINT',  cleanup)
      process.on('SIGTERM', cleanup)
    } catch (err) {
      // Lock file write failure is non-fatal — warn and continue
      log.warn(`[Launcher] Could not write lock file at ${LOCK_FILE}: ${String(err)}`)
    }
  }

  private removeLockFile(): void {
    try {
      if (existsSync(LOCK_FILE)) {
        unlinkSync(LOCK_FILE)
        log.debug('[Launcher] Lock file removed')
      }
    } catch {
      // Best-effort — ignore errors on cleanup
    }
  }

  // ─── exe_path resolution ──────────────────────────────────────────────────

  /**
   * Resolve Kiro.exe path from config or auto-detect.
   *
   * kiro.exe_path = null
   *   → try each path in KIRO_SEARCH_PATHS in order
   *
   * kiro.exe_path ends in ".exe"
   *   → use as a direct file path
   *   → if not found: warn, fall back to auto-detect
   *
   * kiro.exe_path is anything else
   *   → treat as a directory
   *   → search for *.exe inside it, preferring "Kiro.exe" by name
   *   → if folder missing or no .exe inside: warn, fall back to auto-detect
   */
  findKiroExe(): string | null {
    const configured = this.config.kiro.exe_path

    if (!configured) {
      return this.autoDetect()
    }

    const resolved = path.resolve(normalizePath(configured))

    // ── Direct .exe path ──
    if (configured.toLowerCase().endsWith('.exe')) {
      if (existsSync(resolved)) {
        return resolved
      }
      log.warn(
        `[Launcher] exe_path "${configured}" not found — falling back to auto-detect`
      )
      return this.autoDetect()
    }

    // ── Folder path ──
    if (existsSync(resolved)) {
      const found = this.findExeInFolder(resolved)
      if (found) {
        return found
      }
      log.warn(
        `[Launcher] No .exe found in folder "${configured}" — falling back to auto-detect`
      )
    } else {
      log.warn(
        `[Launcher] exe_path "${configured}" is not a file or folder that exists — falling back to auto-detect`
      )
    }

    return this.autoDetect()
  }

  /**
   * Search a folder for an .exe file.
   * Prefers a file literally named Kiro.exe (case-insensitive).
   * Falls back to the first .exe found alphabetically.
   */
  private findExeInFolder(folderPath: string): string | null {
    let entries: string[]
    try {
      entries = readdirSync(folderPath)
    } catch {
      return null
    }

    const exeFiles = entries.filter(e => e.toLowerCase().endsWith('.exe'))
    if (exeFiles.length === 0) return null

    const preferred = exeFiles.find(e => e.toLowerCase() === 'kiro.exe') ?? exeFiles[0]!
    return path.join(folderPath, preferred)
  }

  private autoDetect(): string | null {
    for (const candidate of KIRO_SEARCH_PATHS) {
      const resolved = path.resolve(candidate)
      if (existsSync(resolved)) {
        return resolved
      }
    }
    return null
  }

  // ─── Launch ───────────────────────────────────────────────────────────────

  /**
   * Spawn Kiro with proxy settings and monitor it until it closes.
   * Resolves when Kiro exits. Throws if Kiro cannot be found or started.
   */
  async launch(proxyPort: number): Promise<void> {
    const kiroExe = this.findKiroExe()
    if (!kiroExe) {
      throw new Error(
        'Kiro.exe not found.\n' +
        '  Auto-searched:\n' +
        KIRO_SEARCH_PATHS.map(p => `    • ${p}`).join('\n') + '\n' +
        '  Set kiro.exe_path in kiromask.config.yaml to a .exe file or a folder.'
      )
    }

    const kiroCliJs = path.join(path.dirname(kiroExe), 'resources', 'app', 'out', 'cli.js')
    if (!existsSync(kiroCliJs)) {
      throw new Error(
        `Kiro cli.js not found at:\n  ${kiroCliJs}\n` +
        '  Ensure Kiro is fully installed.'
      )
    }

    log.info(`[Launcher] Kiro found: ${kiroExe}`)
    log.info(`[Launcher] Spawning with proxy on port ${proxyPort}…`)

    const env: NodeJS.ProcessEnv = {
      ...process.env,
      NODE_TLS_REJECT_UNAUTHORIZED:       '0',
      ELECTRON_IGNORE_CERTIFICATE_ERRORS: '1',
      ELECTRON_RUN_AS_NODE:               '1',
      VSCODE_DEV:                         '',
    }

    const child = spawn(
      kiroExe,
      [
        kiroCliJs,
        '--ignore-certificate-errors',
        `--proxy-server=127.0.0.1:${proxyPort}`,
      ],
      { env, stdio: 'ignore', detached: false }
    )

    child.on('error', (err) => {
      log.error('[Launcher] Failed to spawn Kiro process', err)
    })

    // Kiro.exe forks internally — the spawned process is just a launcher stub.
    // We poll for the actual GUI window process separately.
    log.info('[Launcher] Waiting for Kiro window to appear…')
    const windowPid = await this.waitForWindow(15_000)

    if (windowPid === null) {
      throw new Error(
        'Kiro window did not appear within 15 seconds.\n' +
        '  Check that Kiro is installed correctly and can start normally.'
      )
    }

    log.info(`[Launcher] Kiro window detected (PID: ${windowPid})`)
    log.info('[Launcher] KiroMask active — close Kiro to exit.')

    await this.monitorProcess(windowPid)
  }

  // ─── Window detection ─────────────────────────────────────────────────────

  /**
   * Polls PowerShell every 500ms for a Kiro process with a visible window title.
   * Returns that PID, or null if the timeout elapses.
   */
  private waitForWindow(timeoutMs: number): Promise<number | null> {
    return new Promise((resolve) => {

      if (os.platform() !== 'win32') {
        log.debug('[Launcher] Non-Windows — skipping window detection')
        setTimeout(() => resolve(-1), 1500)
        return
      }

      const start    = Date.now()
      const interval = setInterval(() => {

        try {
          const result = execSync(
            'powershell -NoProfile -Command "' +
            "Get-Process | Where-Object { " +
            "  $_.ProcessName -eq 'Kiro' -and $_.MainWindowTitle -ne '' " +
            "} | Select-Object -ExpandProperty Id\"",
            { encoding: 'utf8', timeout: 2000, stdio: ['ignore', 'pipe', 'ignore'] }
          )

          const pids = result
            .trim()
            .split('\n')
            .map(s => parseInt(s.trim(), 10))
            .filter(n => !isNaN(n) && n > 0)

          if (pids[0] !== undefined) {
            clearInterval(interval)
            resolve(pids[0])
            return
          }
        } catch {
          // PowerShell call failed — keep polling
        }

        if (Date.now() - start >= timeoutMs) {
          clearInterval(interval)
          resolve(null)
        }

      }, 500)
    })
  }

  // ─── Process monitoring ───────────────────────────────────────────────────

  /**
   * Polls every 2 seconds to check whether the Kiro window PID is still alive.
   * Resolves when the process exits (user closed Kiro).
   */
  private monitorProcess(pid: number): Promise<void> {
    return new Promise((resolve) => {

      if (pid === -1) {
        // Non-Windows fallback: wait for stdin to close
        process.stdin.resume()
        process.stdin.on('end', resolve)
        return
      }

      const interval = setInterval(() => {
        if (!this.isProcessAlive(pid)) {
          clearInterval(interval)
          log.info('[Launcher] Kiro closed')
          resolve()
        }
      }, 2000)
    })
  }

  private isProcessAlive(pid: number): boolean {
    try {
      process.kill(pid, 0)   // signal 0 = existence check, no signal sent
      return true
    } catch {
      return false
    }
  }
}

// ─── Path normalization helper ────────────────────────────────────────────────
// Collapses any mix of /, \, //, \\ into the platform separator before
// passing to path.resolve. Handles YAML paths written with single backslashes
// (C:\Users\foo), double (C:\\Users\\foo), forward (C:/Users/foo), or mixed.

function normalizePath(raw: string): string {
  return raw.replace(/[/\\]+/g, path.sep)
}
