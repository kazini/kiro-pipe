/**
 * devtools/proxy/decodeResponse.ts
 *
 * Reads a captured .bin response file, decodes the AWS Event Stream,
 * and prints the full structure to console — both a human-readable
 * summary and the raw decoded JSON.
 *
 * Usage:
 *   npx tsx devtools/proxy/decodeResponse.ts <path-to-file.bin>
 *   npx tsx devtools/proxy/decodeResponse.ts logs/interactions/responses/response_2_kiro_native.bin
 *
 * Also accepts a .json file (previously decoded) and re-prints it.
 */

import { readFileSync } from 'node:fs'
import { resolve }      from 'node:path'

const C = {
  bold:  '\x1b[1m',
  cyan:  '\x1b[36m',
  green: '\x1b[32m',
  yellow:'\x1b[33m',
  dim:   '\x1b[2m',
  rst:   '\x1b[0m',
}

// ─── Decoder — identical to InteractionLogger's internal decoder ──────────────

interface DecodedFrame {
  headers: Record<string, string>
  payload: unknown
}

function decodeEventStream(data: Buffer): DecodedFrame[] {
  const frames: DecodedFrame[] = []
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
      const nameLen = data.readUInt8(h);    h += 1
      const name    = data.subarray(h, h + nameLen).toString('utf8'); h += nameLen
      h += 1
      const valLen  = data.readUInt16BE(h); h += 2
      const value   = data.subarray(h, h + valLen).toString('utf8'); h += valLen
      headers[name] = value
    }

    const payloadBuf = data.subarray(headersEnd, offset + totalLength - 4)
    let payload: unknown
    try   { payload = JSON.parse(payloadBuf.toString('utf8')) }
    catch { payload = payloadBuf.toString('utf8') }

    frames.push({ headers, payload })
    offset += totalLength
  }

  return frames
}

// ─── Printer ──────────────────────────────────────────────────────────────────

function printFrames(frames: DecodedFrame[], filePath: string): void {
  console.log()
  console.log(`${C.cyan}${'═'.repeat(64)}${C.rst}`)
  console.log(`${C.bold}  Decoded: ${filePath}${C.rst}`)
  console.log(`${C.dim}  ${frames.length} frame(s)${C.rst}`)
  console.log(`${C.cyan}${'═'.repeat(64)}${C.rst}`)
  console.log()

  // ── Human-readable summary ──
  console.log(`${C.bold}  SUMMARY${C.rst}`)
  console.log(`${C.dim}  ${'─'.repeat(60)}${C.rst}`)

  const textChunks: string[] = []
  for (const frame of frames) {
    const eventType = frame.headers[':event-type'] ?? '(unknown)'
    const p = frame.payload as Record<string, unknown>

    switch (eventType) {
      case 'assistantResponseEvent':
        textChunks.push(String(p['content'] ?? ''))
        break
      case 'toolUseEvent':
        console.log(`  ${C.yellow}[TOOL USE]${C.rst} ${p['name']} (id: ${p['toolUseId']})`)
        if (p['input']) {
          console.log(`    input chunk: ${C.dim}${JSON.stringify(p['input'])}${C.rst}`)
        }
        break
      case 'meteringEvent':
        console.log(`  ${C.green}[METERING]${C.rst} ${p['usage']} ${p['unitPlural'] ?? p['unit']}`)
        break
      case 'contextUsageEvent':
        console.log(`  ${C.green}[CONTEXT]${C.rst} ${p['contextUsagePercentage']}%`)
        break
      default:
        console.log(`  ${C.dim}[${eventType}]${C.rst} ${JSON.stringify(p)}`)
    }
  }

  if (textChunks.length > 0) {
    console.log()
    console.log(`  ${C.bold}Full text response:${C.rst}`)
    console.log(`  ${C.dim}${'─'.repeat(60)}${C.rst}`)
    console.log('  ' + textChunks.join('').split('\n').join('\n  '))
    console.log()
  }

  // ── Raw frame dump ──
  console.log()
  console.log(`${C.bold}  RAW FRAMES (full JSON — no filtering)${C.rst}`)
  console.log(`${C.dim}  ${'─'.repeat(60)}${C.rst}`)

  frames.forEach((frame, i) => {
    console.log()
    console.log(`  ${C.cyan}Frame ${i + 1}/${frames.length}  [${frame.headers[':event-type']}]${C.rst}`)
    console.log('  Headers: ' + C.dim + JSON.stringify(frame.headers) + C.rst)
    console.log('  Payload: ' + C.dim + JSON.stringify(frame.payload, null, 2)
      .split('\n').join('\n  ') + C.rst)
  })

  console.log()
  console.log(`${C.cyan}${'═'.repeat(64)}${C.rst}`)
  console.log()
}

// ─── Main ─────────────────────────────────────────────────────────────────────

function main(): void {
  const args = process.argv.slice(2)
  if (args.length === 0) {
    console.error('Usage: npx tsx devtools/proxy/decodeResponse.ts <file.bin|file.json>')
    process.exit(1)
  }

  const filePath = resolve(process.cwd(), args[0]!)

  if (filePath.endsWith('.json')) {
    // Already decoded — re-print
    const frames = JSON.parse(readFileSync(filePath, 'utf-8')) as DecodedFrame[]
    printFrames(frames, filePath)
  } else {
    // Binary — decode then print
    const buf    = readFileSync(filePath)
    const frames = decodeEventStream(buf)
    console.log(`${C.dim}  Binary: ${buf.length} bytes → ${frames.length} frame(s)${C.rst}`)
    printFrames(frames, filePath)
  }
}

main()
