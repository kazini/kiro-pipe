/**
 * devtools/translator/fixtures.ts
 *
 * Loads test fixtures from devtools/fixtures/ and exposes them as typed
 * objects to the test runner.
 *
 * This is the only file that knows about fixture file paths and JSON shapes.
 * The test runner (testPipeline.ts) imports from here — never reads files directly.
 *
 * To replace a fixture with real captured Kiro traffic:
 *   1. Save the captured JSON to devtools/fixtures/requests/your_name.json
 *   2. Add a loader below
 *   3. Import it in testPipeline.ts — no other changes needed
 *
 * Fixture JSON files may contain "_description" and "_expect" keys.
 * These are metadata for humans; the loader strips them before returning.
 */

import { readFileSync }       from 'node:fs'
import { resolve, dirname }   from 'node:path'
import { fileURLToPath }      from 'node:url'

import type {
  AWSQRequest,
  AnthropicStreamEvent,
  OpenAIStreamChunk,
}                             from '../../src/lib/awsq-adapter/types.js'

// ─── Paths ────────────────────────────────────────────────────────────────────

const __dirname  = dirname(fileURLToPath(import.meta.url))
const FIXTURE_DIR = resolve(__dirname, '../fixtures')
const REQ_DIR     = resolve(FIXTURE_DIR, 'requests')
const STREAM_DIR  = resolve(FIXTURE_DIR, 'streams')

// ─── Loader helpers ───────────────────────────────────────────────────────────

function loadJson(filePath: string): Record<string, unknown> {
  try {
    const raw  = readFileSync(filePath, 'utf-8')
    const data = JSON.parse(raw) as Record<string, unknown>
    // Strip metadata keys — they're for humans, not the test runner
    delete data['_description']
    delete data['_expect']
    return data
  } catch (err) {
    throw new Error(`Failed to load fixture at "${filePath}": ${String(err)}`)
  }
}

/**
 * Load a request fixture and return it as a typed AWSQRequest.
 * Throws with the file path if the file is missing or invalid JSON.
 */
export function loadRequest(name: string): AWSQRequest {
  return loadJson(resolve(REQ_DIR, `${name}.json`)) as unknown as AWSQRequest
}

/**
 * Load an Anthropic SSE stream fixture and return an async generator
 * that yields the events in sequence.
 *
 * Fixture format: { "events": [ ...AnthropicStreamEvent[] ] }
 */
export async function* loadAnthropicStream(
  name: string
): AsyncGenerator<AnthropicStreamEvent> {
  const data   = loadJson(resolve(STREAM_DIR, `${name}.json`))
  const events = data['events'] as AnthropicStreamEvent[]

  if (!Array.isArray(events)) {
    throw new Error(`Fixture "${name}" has no "events" array`)
  }

  for (const event of events) {
    yield event
  }
}

/**
 * Load an OpenAI SSE stream fixture and return an async generator
 * that yields the chunks in sequence.
 *
 * Fixture format: { "chunks": [ ...OpenAIStreamChunk[] ] }
 */
export async function* loadOpenAIStream(
  name: string
): AsyncGenerator<OpenAIStreamChunk> {
  const data   = loadJson(resolve(STREAM_DIR, `${name}.json`))
  const chunks = data['chunks'] as OpenAIStreamChunk[]

  if (!Array.isArray(chunks)) {
    throw new Error(`Fixture "${name}" has no "chunks" array`)
  }

  for (const chunk of chunks) {
    yield chunk
  }
}

/**
 * Load the raw _expect metadata from a fixture without stripping it.
 * Useful for data-driven assertions (the fixture describes what it expects).
 */
export function loadExpect(dir: 'requests' | 'streams', name: string): Record<string, unknown> {
  const base = dir === 'requests' ? REQ_DIR : STREAM_DIR
  const raw  = readFileSync(resolve(base, `${name}.json`), 'utf-8')
  const data = JSON.parse(raw) as Record<string, unknown>
  return (data['_expect'] ?? {}) as Record<string, unknown>
}

/**
 * List all fixture files available in a directory.
 * Useful for running all fixtures in a directory automatically.
 */
export function listFixtures(dir: 'requests' | 'streams'): string[] {
  const { readdirSync } = require('node:fs') as typeof import('node:fs')
  const base = dir === 'requests' ? REQ_DIR : STREAM_DIR
  return readdirSync(base)
    .filter((f: string) => f.endsWith('.json'))
    .map((f: string) => f.replace(/\.json$/, ''))
}

// ─── Loaders for captured interaction files ───────────────────────────────────
// Load files saved by InteractionLogger during a real Kiro session.
// Pass a path relative to the project root (cwd).

import { readFileSync as _rfs } from 'node:fs'
import { resolve as _res }      from 'node:path'
import type {
  AnthropicStreamEvent,
}                               from '../../src/lib/awsq-adapter/types.js'

/**
 * Load a captured posted/request_N.json as an AWSQRequest.
 * Strips the _index / _url / _headers envelope if present.
 */
export function loadCapturedRequest(filePath: string): AWSQRequest {
  const abs  = _res(process.cwd(), filePath)
  const data = JSON.parse(_rfs(abs, 'utf-8')) as Record<string, unknown>
  // InteractionLogger wraps the body in an envelope
  const body = ('body' in data) ? data['body'] : data
  return body as unknown as AWSQRequest
}

/**
 * Load a captured responses/response_N.json and yield frames as a stream
 * the ResponseTranslator can consume.
 *
 * File format (Python-compatible):
 *   [{ "headers": {":event-type": "..."}, "payload": {...} }, ...]
 *
 * Mapping: assistantResponseEvent → text_delta, meteringEvent → message_stop.
 * Use this to test that re-encoding a captured response produces valid output.
 */
export async function* loadCapturedResponseAsStream(
  filePath: string,
): AsyncGenerator<AnthropicStreamEvent> {
  const abs    = _res(process.cwd(), filePath)
  const frames = JSON.parse(_rfs(abs, 'utf-8')) as Array<{
    headers: Record<string, string>
    payload: Record<string, unknown>
  }>

  let index = 0
  for (const frame of frames) {
    const eventType = frame.headers[':event-type'] ?? ''
    const payload   = frame.payload

    if (eventType === 'assistantResponseEvent') {
      yield {
        type:  'content_block_delta',
        index: index++,
        delta: { type: 'text_delta', text: String(payload['content'] ?? '') },
      }
    } else if (eventType === 'meteringEvent') {
      yield { type: 'message_stop' }
    }
    // toolUseEvent and contextUsageEvent are output-only — skip for re-encoding test
  }
}
