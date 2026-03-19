/**
 * devtools/translator/testPipeline.ts
 *
 * Translation pipeline test runner.
 * All test data is loaded from devtools/fixtures/ via fixtures.ts.
 * This file contains only assertions — no hardcoded JSON, no mock data.
 *
 * Three independent axes that can each fail independently:
 *   1. Fixture files (devtools/fixtures/)     — edit JSON to fix format issues
 *   2. Conversion code (src/lib/awsq-adapter) — edit translator/encoder to fix logic
 *   3. Test assertions (this file)            — edit assertions to fix test issues
 *
 * Run all:
 *   npx tsx devtools/translator/testPipeline.ts
 *
 * Run one suite:
 *   npx tsx devtools/translator/testPipeline.ts --test plain
 *   npx tsx devtools/translator/testPipeline.ts --test history
 *   npx tsx devtools/translator/testPipeline.ts --test tools
 *   npx tsx devtools/translator/testPipeline.ts --test multitool
 *   npx tsx devtools/translator/testPipeline.ts --test encoder
 *
 * Run with a specific request fixture by name:
 *   npx tsx devtools/translator/testPipeline.ts --request plain
 *   npx tsx devtools/translator/testPipeline.ts --request tool_result
 */

import { RequestTranslator }  from '../../src/lib/awsq-adapter/RequestTranslator.js'
import { ResponseTranslator } from '../../src/lib/awsq-adapter/ResponseTranslator.js'
import { encodeEvent }        from '../../src/lib/awsq-adapter/eventStream.js'

import {
  loadRequest,
  loadAnthropicStream,
  loadOpenAIStream,
  loadExpect,
}                             from './fixtures.js'

import type {
  AnthropicMessage,
  AnthropicContentBlock,
}                             from '../../src/lib/awsq-adapter/types.js'

// ─── Binary decoder ───────────────────────────────────────────────────────────
// Mirrors Python decode_event_stream.py exactly.
// Used to verify encoder output is readable before Kiro ever sees it.

interface DecodedEvent {
  eventType:   string
  contentType: string
  payload:     unknown
}

function decodeEventStream(data: Buffer): DecodedEvent[] {
  const events: DecodedEvent[] = []
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
      const nameLen = data.readUInt8(h);      h += 1
      const name    = data.subarray(h, h + nameLen).toString('utf8'); h += nameLen
      h += 1  // value_type byte (always 7 = string)
      const valLen  = data.readUInt16BE(h);   h += 2
      const value   = data.subarray(h, h + valLen).toString('utf8'); h += valLen
      headers[name] = value
    }

    const payloadBuf = data.subarray(headersEnd, offset + totalLength - 4)
    let payload: unknown
    try   { payload = JSON.parse(payloadBuf.toString('utf8')) }
    catch { payload = payloadBuf.toString('utf8') }

    events.push({
      eventType:   headers[':event-type']   ?? '(unknown)',
      contentType: headers[':content-type'] ?? '(unknown)',
      payload,
    })

    offset += totalLength
  }

  return events
}

// ─── Assertion helpers ────────────────────────────────────────────────────────

const C = {
  pass: '\x1b[32m✓\x1b[0m',
  fail: '\x1b[31m✗\x1b[0m',
  cyan: '\x1b[36m',
  dim:  '\x1b[2m',
  bold: '\x1b[1m',
  rst:  '\x1b[0m',
}

let _failures = 0

function assert(condition: boolean, label: string): void {
  if (condition) {
    console.log(`  ${C.pass}  ${label}`)
  } else {
    console.log(`  ${C.fail}  ${C.bold}FAIL: ${label}${C.rst}`)
    _failures++
  }
}

function section(title: string): void {
  console.log(`\n${C.cyan}${'─'.repeat(62)}${C.rst}`)
  console.log(`${C.bold}  ${title}${C.rst}`)
  console.log(`${C.cyan}${'─'.repeat(62)}${C.rst}`)
}

function printJson(label: string, value: unknown): void {
  const lines = JSON.stringify(value, null, 2).split('\n')
  console.log(`\n  ${C.dim}── ${label}:${C.rst}`)
  for (const l of lines) console.log(`  ${C.dim}${l}${C.rst}`)
}

function printEvents(events: DecodedEvent[]): void {
  console.log(`\n  ${C.dim}── Decoded Event Stream (${events.length} frames):${C.rst}`)
  for (const e of events) {
    console.log(`    ${C.dim}[${e.eventType}]  ${JSON.stringify(e.payload)}${C.rst}`)
  }
}

// ─── Translator instances ─────────────────────────────────────────────────────

const T = new RequestTranslator()
const R = new ResponseTranslator()

// ─── Test suites ──────────────────────────────────────────────────────────────

async function testPlain(): Promise<void> {
  section('plain — Simple text message, no history, no tools')

  const req = loadRequest('plain')

  // Anthropic translation
  const a = T.toAnthropic(req, 'claude-3-5-sonnet-20241022', 4096)
  assert(a.model      === 'claude-3-5-sonnet-20241022', 'Anthropic: model set')
  assert(a.max_tokens === 4096,                         'Anthropic: max_tokens set')
  assert(a.stream     === true,                         'Anthropic: stream: true')
  assert(a.messages.length === 1,                       'Anthropic: 1 message')
  assert(a.messages[0]?.role === 'user',                'Anthropic: role user')
  assert(typeof a.messages[0]?.content === 'string',    'Anthropic: content is plain string')
  assert(a.tools === undefined,                         'Anthropic: no tools')
  printJson('Anthropic request', a)

  // OpenAI translation
  const o = T.toOpenAI(req, 'gpt-4o', 4096)
  assert(o.model === 'gpt-4o',              'OpenAI: model set')
  assert(o.messages.length === 1,           'OpenAI: 1 message')
  assert(o.messages[0]?.role === 'user',    'OpenAI: role user')
  assert(o.tools === undefined,             'OpenAI: no tools')
  printJson('OpenAI request', o)

  // Anthropic response stream
  // Each text_delta becomes its own frame. 2 text chunks = 2 frames.
  // Total: N text frames + 1 metering + 1 context. Read count from fixture.
  const streamExp = loadExpect('streams', 'anthropic_text')
  const bufA = await R.fromAnthropicStream(loadAnthropicStream('anthropic_text'))
  const evA  = decodeEventStream(bufA)
  assert(
    evA.length === (streamExp['event_stream_event_count'] as number),
    `Anthropic stream: ${streamExp['event_stream_event_count']} total frames`
  )
  const textFramesA = evA.filter(e => e.eventType === 'assistantResponseEvent')
  assert(textFramesA.length >= 1,                                        'Anthropic stream: has text frame(s)')
  assert(evA.some(e => e.eventType === 'meteringEvent'),                 'Anthropic stream: has metering frame')
  assert(evA.some(e => e.eventType === 'contextUsageEvent'),             'Anthropic stream: has context frame')
  assert((textFramesA[0]?.payload as {content?:string}).content !== '', 'Anthropic stream: first text frame non-empty')
  printEvents(evA)

  // OpenAI response stream
  const bufO = await R.fromOpenAIStream(loadOpenAIStream('openai_text'))
  const evO  = decodeEventStream(bufO)
  assert(evO.some(e => e.eventType === 'assistantResponseEvent'), 'OpenAI stream: has text frame')
  assert(evO.some(e => e.eventType === 'meteringEvent'),          'OpenAI stream: has metering frame')
  printEvents(evO)
}

async function testHistory(): Promise<void> {
  section('history — Prior conversation turns reconstructed correctly')

  const req  = loadRequest('history')
  const exp  = loadExpect('requests', 'history')

  const a = T.toAnthropic(req, 'claude-3-5-sonnet-20241022', 4096)
  assert(
    a.messages.length === (exp['anthropic_message_count'] as number),
    `Anthropic: ${exp['anthropic_message_count']} messages`
  )
  assert(a.messages[0]?.role === 'user',      'Anthropic: history[0] user')
  assert(a.messages[1]?.role === 'assistant', 'Anthropic: history[1] assistant')
  assert(a.messages[2]?.role === 'user',      'Anthropic: current turn user')
  printJson('Anthropic (history)', a)

  const o = T.toOpenAI(req, 'gpt-4o', 4096)
  assert(
    o.messages.length === (exp['openai_message_count'] as number),
    `OpenAI: ${exp['openai_message_count']} messages`
  )
  assert(o.messages[0]?.role === 'user',      'OpenAI: history[0] user')
  assert(o.messages[1]?.role === 'assistant', 'OpenAI: history[1] assistant')
  printJson('OpenAI (history)', o)
}

async function testTools(): Promise<void> {
  section('tools — Tool definitions, tool use in streams')

  const req = loadRequest('tool_defs')
  const exp = loadExpect('requests', 'tool_defs')

  // Anthropic tool definition format
  const a = T.toAnthropic(req, 'claude-3-5-sonnet-20241022', 4096)
  assert(a.tools?.length === (exp['tool_count'] as number), `Anthropic: ${exp['tool_count']} tool(s)`)
  const aTool = a.tools?.[0]
  assert(aTool?.name === 'readFile',              'Anthropic: tool name correct')
  assert('input_schema' in (aTool ?? {}),         `Anthropic: has ${exp['anthropic_tool_key']}`)
  assert(!('inputSchema' in (aTool ?? {})),        'Anthropic: raw inputSchema wrapper stripped')
  assert(!('parameters'  in (aTool ?? {})),        'Anthropic: no OpenAI-style parameters key')
  printJson('Anthropic tools', a.tools)

  // OpenAI tool definition format
  const o = T.toOpenAI(req, 'gpt-4o', 4096)
  const oTool = o.tools?.[0]
  assert(oTool?.type === 'function',              'OpenAI: type: function')
  assert(oTool?.function.name === 'readFile',     'OpenAI: function.name correct')
  assert('parameters' in (oTool?.function ?? {}), `OpenAI: has ${exp['openai_tool_key']}`)
  assert(!('input_schema' in (oTool?.function ?? {})), 'OpenAI: no Anthropic-style input_schema key')
  printJson('OpenAI tools', o.tools)

  // Anthropic tool use stream
  section('tools — Tool use in Anthropic response stream')
  const streamExp = loadExpect('streams', 'anthropic_tool')
  const bufA      = await R.fromAnthropicStream(loadAnthropicStream('anthropic_tool'))
  const evA       = decodeEventStream(bufA)
  const toolEvA   = evA.filter(e => e.eventType === 'toolUseEvent')
  assert(toolEvA.length >= 2, 'Anthropic: at least 2 toolUseEvents (chunks + terminator)')
  const lastA = toolEvA[toolEvA.length - 1]?.payload as { input?: string; toolUseId?: string }
  assert(lastA?.input === '', 'Anthropic: last toolUseEvent is empty terminator')
  const expIds = streamExp['tool_ids'] as string[]
  assert(
    expIds.every(id => toolEvA.some(e => (e.payload as { toolUseId?: string }).toolUseId === id)),
    `Anthropic: all expected tool IDs present: ${expIds.join(', ')}`
  )
  printEvents(evA)

  // OpenAI tool use stream
  section('tools — Tool use in OpenAI response stream')
  const bufO    = await R.fromOpenAIStream(loadOpenAIStream('openai_tool'))
  const evO     = decodeEventStream(bufO)
  const toolEvO = evO.filter(e => e.eventType === 'toolUseEvent')
  assert(toolEvO.length >= 1, 'OpenAI: has toolUseEvents')
  printEvents(evO)

  // Tool result in current message
  section('tools — Tool result in current turn')
  const reqR = loadRequest('tool_result')
  const expR = loadExpect('requests', 'tool_result')

  const ar = T.toAnthropic(reqR, 'claude-3-5-sonnet-20241022', 4096)
  const lastMsgA = ar.messages[ar.messages.length - 1] as AnthropicMessage
  const contentA = lastMsgA.content
  assert(Array.isArray(contentA), 'Anthropic: current turn content is array (not plain string)')
  const trBlock = (contentA as AnthropicContentBlock[])
    .find(b => b.type === 'tool_result') as { type: string; tool_use_id?: string } | undefined
  assert(trBlock !== undefined,                                    'Anthropic: has tool_result block')
  assert(trBlock?.tool_use_id === expR['tool_use_id'] as string,  'Anthropic: tool_use_id matches')
  printJson('Anthropic (tool result)', ar)

  const or = T.toOpenAI(reqR, 'gpt-4o', 4096)
  const toolMsg = or.messages.find(m => m.role === 'tool') as { role: string; tool_call_id?: string } | undefined
  assert(toolMsg !== undefined,                              'OpenAI: has role:tool message')
  assert(toolMsg?.tool_call_id === expR['tool_use_id'] as string, 'OpenAI: tool_call_id matches')
  printJson('OpenAI (tool result)', or)
}

async function testMultitool(): Promise<void> {
  section('multitool — Two concurrent tool calls (index tracking, the Python bug)')

  // Anthropic stream
  const expA  = loadExpect('streams', 'anthropic_multitool')
  const bufA  = await R.fromAnthropicStream(loadAnthropicStream('anthropic_multitool'))
  const evA   = decodeEventStream(bufA)
  const tvA   = evA.filter(e => e.eventType === 'toolUseEvent')
  const idsA  = expA['tool_ids'] as string[]

  for (const id of idsA) {
    const events = tvA.filter(e => (e.payload as { toolUseId?: string }).toolUseId === id)
    assert(events.length > 0, `Anthropic: events present for tool ID "${id}"`)
    const last = events[events.length - 1]?.payload as { input?: string }
    assert(last?.input === '', `Anthropic: tool "${id}" has empty terminator`)
  }
  printEvents(evA)

  // OpenAI stream
  const expO = loadExpect('streams', 'openai_multitool')
  const bufO = await R.fromOpenAIStream(loadOpenAIStream('openai_multitool'))
  const evO  = decodeEventStream(bufO)
  const tvO  = evO.filter(e => e.eventType === 'toolUseEvent')
  const idsO = expO['tool_ids'] as string[]

  for (const id of idsO) {
    const events = tvO.filter(e => (e.payload as { toolUseId?: string }).toolUseId === id)
    assert(events.length > 0, `OpenAI: events present for tool ID "${id}"`)
  }
  printEvents(evO)
}

async function testEncoder(): Promise<void> {
  section('encoder — Frame structure and round-trip integrity')

  const payload   = { content: 'Hello, KiroMask!' }
  const frame     = encodeEvent('assistantResponseEvent', payload)
  const totalLen  = frame.readUInt32BE(0)
  const headerLen = frame.readUInt32BE(4)

  assert(frame.length === totalLen, 'frame.length matches total_length field')
  assert(
    totalLen === 12 + headerLen + Buffer.byteLength(JSON.stringify(payload)) + 4,
    'total_length formula: 12 + headers_length + payload_length + 4'
  )

  const decoded = decodeEventStream(frame)
  assert(decoded.length === 1,                                          '1 event decoded from 1 frame')
  assert(decoded[0]?.eventType === 'assistantResponseEvent',            'event type survives round-trip')
  assert(
    (decoded[0]?.payload as { content?: string }).content === payload.content,
    'payload content survives round-trip'
  )

  // Verify CRC fields are present (non-zero for a non-trivial payload)
  const preludeCrc = frame.readUInt32BE(8)
  const messageCrc = frame.readUInt32BE(frame.length - 4)
  assert(preludeCrc !== 0, 'prelude CRC is non-zero')
  assert(messageCrc !== 0, 'message CRC is non-zero')

  console.log(`\n  ${C.dim}Frame: ${frame.length} bytes${C.rst}`)
  console.log(`  ${C.dim}Hex:   ${frame.toString('hex').slice(0, 80)}…${C.rst}`)
}

// ─── Runner ───────────────────────────────────────────────────────────────────

const SUITES: Record<string, () => Promise<void>> = {
  plain:     testPlain,
  history:   testHistory,
  tools:     testTools,
  multitool: testMultitool,
  encoder:   testEncoder,
}

async function runSingleRequest(name: string): Promise<void> {
  section(`Spot-check: request fixture "${name}"`)

  const req = loadRequest(name)

  const a = T.toAnthropic(req, 'claude-3-5-sonnet-20241022', 4096)
  assert(a.messages.length > 0, `Anthropic: produced ${a.messages.length} message(s)`)
  assert(a.stream === true,      'Anthropic: stream: true')
  printJson(`Anthropic output for "${name}"`, a)

  const o = T.toOpenAI(req, 'gpt-4o', 4096)
  assert(o.messages.length > 0, `OpenAI: produced ${o.messages.length} message(s)`)
  printJson(`OpenAI output for "${name}"`, o)
}

async function main(): Promise<void> {
  console.log(`\n${C.bold}${C.cyan}KiroMask — Translation Pipeline Tests${C.rst}`)
  console.log(`${C.dim}Fixtures: devtools/fixtures/   |   Code: src/lib/awsq-adapter/${C.rst}`)
  console.log(`${C.dim}No network. No LLM. No Kiro. Tests actual production code paths.${C.rst}`)

  const args      = process.argv.slice(2)
  const suiteIdx  = args.indexOf('--test')
  const reqIdx    = args.indexOf('--request')

  if (reqIdx !== -1) {
    const name = args[reqIdx + 1]
    if (!name) { console.error('--request requires a fixture name'); process.exit(1) }
    await runSingleRequest(name)

  } else if (suiteIdx !== -1) {
    const name = args[suiteIdx + 1]
    if (!name) { console.error('--test requires a suite name'); process.exit(1) }
    const fn = SUITES[name]
    if (!fn) {
      console.error(`Unknown suite "${name}". Available: ${Object.keys(SUITES).join(', ')}`)
      process.exit(1)
    }
    await fn()

  } else {
    for (const fn of Object.values(SUITES)) {
      await fn()
    }
  }

  console.log()
  if (_failures > 0) {
    console.log(`${C.fail} ${_failures} assertion(s) failed — see above.\n`)
    process.exit(1)
  } else {
    console.log(`${C.pass} All assertions passed.\n`)
  }
}

main().catch(err => {
  console.error('\nFatal error:', err)
  process.exit(1)
})
