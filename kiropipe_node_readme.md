# KiroPipe Node.js - System Design Specification

## Executive Summary

A Node.js reimplementation of KiroPipe using Mockttp for MITM proxy capabilities and Portkey for universal LLM provider integration. This specification defines the functional requirements, component architecture, and implementation guidance for building a production-ready system.

## Technology Stack

### Core Dependencies
- **Mockttp** - HTTPS interception and proxy (replaces mitmproxy)
- **Portkey** - Universal LLM gateway (replaces custom translation + LiteLLM)
- **Node.js** - Runtime environment (v18+ required)
- **TypeScript** - Type safety and development experience

### Supporting Libraries
- **yaml** - Configuration file parsing
- **winston** - Structured logging
- **node-cache** - In-memory caching for model metadata
- **axios** - HTTP client for API calls
- **zod** - Runtime schema validation

## Functional Requirements (EARS Format)

### FR-1: Proxy Interception
**WHEN** Kiro makes an HTTPS request to AWS Q endpoints  
**THE SYSTEM SHALL** intercept the request using Mockttp  
**AND** parse the AWS Q request format  
**AND** determine the target model from request body

### FR-2: Request Routing
**WHEN** a model is identified in the intercepted request  
**IF** the model is configured as a custom provider  
**THE SYSTEM SHALL** route the request to Portkey gateway  
**ELSE IF** the model is a Kiro default model  
**THE SYSTEM SHALL** forward the request to AWS Q unmodified  
**ELSE** the system shall block the request with empty response

### FR-3: Format Translation
**WHEN** routing to a custom provider via Portkey  
**THE SYSTEM SHALL** extract conversation history from AWS Q format  
**AND** transform to Portkey's unified format  
**AND** preserve tool definitions if present  
**AND** maintain conversation context

### FR-4: Response Streaming
**WHEN** receiving streaming response from Portkey  
**THE SYSTEM SHALL** translate chunks to AWS Event Stream binary format  
**AND** throttle chunk delivery to prevent rate limit violations  
**AND** maintain proper event stream framing  
**AND** handle backpressure appropriately


### FR-5: Configuration Management
**WHEN** the system starts  
**THE SYSTEM SHALL** load configuration from YAML file  
**AND** validate all required fields using Zod schemas  
**AND** apply default values for optional fields  
**AND** fail fast with clear error messages on invalid config

### FR-6: Model Discovery
**WHEN** Kiro requests available models (ListAvailableModels)  
**THE SYSTEM SHALL** inject custom models from configuration  
**AND** preserve Kiro's default models if enabled  
**AND** include cost/quota information from Portkey metadata  
**AND** support model aliases for user convenience

### FR-7: Error Handling
**WHEN** an error occurs during request processing  
**THE SYSTEM SHALL** return AWS-formatted error response  
**AND** log detailed error information for debugging  
**AND** NOT expose internal implementation details to Kiro  
**AND** handle rate limits with exponential backoff

### FR-8: Memory Management
**WHEN** storing request history for debugging  
**THE SYSTEM SHALL** limit history to last 100 entries  
**AND** automatically evict oldest entries when limit exceeded  
**AND** provide memory usage metrics in health endpoint

### FR-9: Telemetry Control
**WHEN** Kiro attempts to send telemetry or update checks  
**IF** telemetry/updates are disabled in configuration  
**THE SYSTEM SHALL** block the request with 200 OK response  
**AND** log the blocked request for audit purposes

### FR-10: Debug Capabilities
**WHEN** debug mode is enabled  
**THE SYSTEM SHALL** log all intercepted requests and responses  
**AND** optionally save interactions to disk  
**AND** provide detailed timing information  
**AND** expose internal state via debug endpoints

## Component Architecture

### Component 1: Proxy Server (ProxyManager)
**Purpose:** HTTPS interception and traffic routing  
**Technology:** Mockttp  
**Responsibilities:**
- Initialize HTTPS proxy with self-signed certificate
- Intercept requests to AWS Q endpoints
- Route requests based on configuration
- Handle certificate trust issues
- Manage proxy lifecycle

**Key Methods:**
```typescript
class ProxyManager {
  async start(port: number): Promise<void>
  async stop(): Promise<void>
  async interceptRequest(request: MockttpRequest): Promise<void>
  async forwardToAWS(request: MockttpRequest): Promise<MockttpResponse>
  async routeToPortkey(request: MockttpRequest): Promise<MockttpResponse>
}
```


### Component 2: Request Translator (RequestTranslator)
**Purpose:** Convert AWS Q format to Portkey format  
**Technology:** Custom TypeScript classes  
**Responsibilities:**
- Parse AWS Q request body
- Extract conversation history
- Extract tool definitions
- Transform to Portkey unified format
- Validate transformed request

**Key Methods:**
```typescript
class RequestTranslator {
  parseAWSRequest(body: string): AWSQRequest
  extractMessages(awsRequest: AWSQRequest): PortkeyMessage[]
  extractTools(awsRequest: AWSQRequest): PortkeyTool[]
  toPortkeyFormat(awsRequest: AWSQRequest): PortkeyRequest
}
```

**Data Structures:**
```typescript
interface AWSQRequest {
  conversationState: {
    conversationId: string
    history: Array<{
      userInputMessage?: { content: string }
      assistantResponseMessage?: { content: string }
    }>
    currentMessage: {
      userInputMessage: {
        content: string
        modelId: string
        userInputMessageContext?: {
          tools?: Array<ToolSpecification>
        }
      }
    }
  }
}

interface PortkeyRequest {
  messages: Array<{ role: string; content: string }>
  model: string
  stream: boolean
  tools?: Array<PortkeyTool>
}
```

### Component 3: Response Translator (ResponseTranslator)
**Purpose:** Convert Portkey streaming response to AWS Event Stream  
**Technology:** Custom binary encoding + streaming  
**Responsibilities:**
- Parse Portkey SSE stream
- Encode AWS Event Stream binary format
- Handle text chunks and tool calls
- Add metering and usage information
- Throttle chunk delivery

**Key Methods:**
```typescript
class ResponseTranslator {
  async translateStream(
    portkeyStream: ReadableStream,
    throttleMs: number
  ): AsyncGenerator<Buffer>
  
  encodeTextChunk(text: string): Buffer
  encodeToolUseChunk(toolName: string, toolId: string, args: string): Buffer
  encodeMetering(usage: number): Buffer
  encodeContextUsage(percentage: number): Buffer
}
```

**AWS Event Stream Format:**
```
[Prelude: 12 bytes]
  - Total length (4 bytes, big-endian)
  - Headers length (4 bytes, big-endian)
  - Prelude CRC (4 bytes, big-endian)
[Headers: variable]
  - :event-type (string)
  - :content-type (string)
  - :message-type (string)
[Payload: variable]
  - JSON or binary data
[Message CRC: 4 bytes]
```


### Component 4: Portkey Gateway (PortkeyClient)
**Purpose:** Interface with Portkey for universal LLM access  
**Technology:** Portkey SDK + REST API  
**Responsibilities:**
- Initialize Portkey client with API key
- Route requests to configured providers
- Handle streaming responses
- Capture usage metrics
- Manage provider-specific configurations

**Key Methods:**
```typescript
class PortkeyClient {
  constructor(apiKey: string, config: PortkeyConfig)
  
  async chat(
    request: PortkeyRequest,
    provider: string
  ): Promise<ReadableStream>
  
  async getModelMetadata(modelId: string): Promise<ModelMetadata>
  getCostInfo(modelId: string): CostInfo
  getQuotaInfo(modelId: string): QuotaInfo
}
```

**Portkey Configuration:**
```typescript
interface PortkeyConfig {
  apiKey: string
  virtualKeys: {
    [provider: string]: string  // Provider-specific API keys
  }
  cacheConfig?: {
    mode: 'simple' | 'semantic'
    maxAge: number
  }
  retryConfig?: {
    attempts: number
    onStatusCodes: number[]
  }
}
```

### Component 5: Configuration Manager (ConfigManager)
**Purpose:** Load, validate, and provide configuration  
**Technology:** yaml + zod  
**Responsibilities:**
- Load YAML configuration file
- Validate against schema
- Provide type-safe config access
- Support hot-reload (optional)
- Merge defaults with user config

**Key Methods:**
```typescript
class ConfigManager {
  static load(path: string): Config
  static validate(config: unknown): Config
  getProvider(name: string): ProviderConfig
  getModel(modelId: string): ModelConfig
  isModelEnabled(modelId: string): boolean
}
```

**Configuration Schema:**
```typescript
interface Config {
  proxy: {
    port: number
    host?: string
  }
  
  kiro: {
    exePath?: string
    autoLaunch?: boolean
  }
  
  kiroEndpoint: {
    telemetry: boolean
    updates: boolean
    models: boolean
    usageLimits?: 'auto' | 'always' | 'never'
  }
  
  portkey: {
    apiKey: string
    virtualKeys: Record<string, string>
    cache?: {
      enabled: boolean
      mode: 'simple' | 'semantic'
      maxAge: number
    }
    retry?: {
      enabled: boolean
      attempts: number
      onStatusCodes: number[]
    }
  }
  
  providers: {
    [name: string]: {
      enabled: boolean
      type: 'anthropic' | 'openai' | 'groq' | 'ollama' | 'custom'
      models: Array<{
        name: string
        alias?: string[]
        displayName?: string
        description?: string
        maxTokens?: number
        enabled?: boolean
      }>
    }
  }
  
  rateLimit: {
    enabled: boolean
    defaultInterval: number
    perProvider?: Record<string, number>
  }
  
  debug: {
    enabled: boolean
    logLevel: 'error' | 'warn' | 'info' | 'debug'
    saveInteractions: boolean
    outputDir?: string
  }
}
```


### Component 6: Model Registry (ModelRegistry)
**Purpose:** Track and inject custom models into Kiro  
**Technology:** In-memory cache + Portkey metadata  
**Responsibilities:**
- Maintain list of available models
- Inject custom models into ListAvailableModels response
- Provide cost and quota information
- Support model aliases
- Cache model metadata

**Key Methods:**
```typescript
class ModelRegistry {
  registerModel(model: ModelConfig): void
  getModel(modelId: string): ModelConfig | null
  resolveAlias(alias: string): string | null
  injectModels(awsResponse: AWSModelListResponse): AWSModelListResponse
  getDisplayInfo(modelId: string): ModelDisplayInfo
}
```

**Model Display Info:**
```typescript
interface ModelDisplayInfo {
  modelId: string
  modelName: string
  description: string
  rateMultiplier: number | null
  rateUnit: '$/1M Token' | '% Quota' | 'FREE' | 'UNKNOWN'
  maxInputTokens: number
  supportedInputTypes: string[]
}
```

### Component 7: Request History (RequestHistory)
**Purpose:** Track requests for debugging and metrics  
**Technology:** Circular buffer in memory  
**Responsibilities:**
- Store last N requests (default 100)
- Automatically evict oldest entries
- Provide query interface
- Calculate usage statistics
- Export for debugging

**Key Methods:**
```typescript
class RequestHistory {
  constructor(maxSize: number = 100)
  
  add(request: RequestRecord): void
  getRecent(count: number): RequestRecord[]
  getByConversation(conversationId: string): RequestRecord[]
  getStats(): UsageStats
  clear(): void
}
```

**Request Record:**
```typescript
interface RequestRecord {
  timestamp: Date
  conversationId: string
  modelId: string
  provider: string
  inputTokens: number
  outputTokens: number
  latencyMs: number
  success: boolean
  error?: string
}
```

### Component 8: Rate Limiter (RateLimiter)
**Purpose:** Prevent API rate limit violations  
**Technology:** Token bucket algorithm  
**Responsibilities:**
- Enforce minimum interval between requests
- Support per-provider rate limits
- Queue requests when rate limited
- Implement exponential backoff
- Provide rate limit status

**Key Methods:**
```typescript
class RateLimiter {
  constructor(config: RateLimitConfig)
  
  async acquire(provider: string): Promise<void>
  release(provider: string): void
  getStatus(provider: string): RateLimitStatus
  reset(provider: string): void
}
```

**Rate Limit Algorithm:**
```typescript
interface RateLimitConfig {
  defaultInterval: number  // milliseconds
  perProvider: Record<string, number>
}

// Token bucket implementation
class TokenBucket {
  private tokens: number
  private lastRefill: number
  private capacity: number
  private refillRate: number
  
  async consume(): Promise<void> {
    // Wait if no tokens available
    // Refill tokens based on time elapsed
  }
}
```


### Component 9: Logger (Logger)
**Purpose:** Structured logging with multiple outputs  
**Technology:** winston  
**Responsibilities:**
- Log to console with colors
- Log to file with rotation
- Support multiple log levels
- Structured JSON logging
- Performance metrics

**Key Methods:**
```typescript
class Logger {
  static create(config: LogConfig): winston.Logger
  
  debug(message: string, meta?: object): void
  info(message: string, meta?: object): void
  warn(message: string, meta?: object): void
  error(message: string, error?: Error, meta?: object): void
}
```

**Log Configuration:**
```typescript
interface LogConfig {
  level: 'error' | 'warn' | 'info' | 'debug'
  console: boolean
  file?: {
    enabled: boolean
    path: string
    maxSize: string
    maxFiles: number
  }
  format: 'json' | 'pretty'
}
```

### Component 10: Health Monitor (HealthMonitor)
**Purpose:** System health and metrics endpoint  
**Technology:** Express.js HTTP server  
**Responsibilities:**
- Expose health check endpoint
- Provide system metrics
- Report component status
- Track uptime and requests
- Memory usage monitoring

**Key Methods:**
```typescript
class HealthMonitor {
  constructor(port: number)
  
  async start(): Promise<void>
  getHealth(): HealthStatus
  getMetrics(): SystemMetrics
  recordRequest(record: RequestRecord): void
}
```

**Health Status:**
```typescript
interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  uptime: number
  components: {
    proxy: 'up' | 'down'
    portkey: 'up' | 'down'
    config: 'loaded' | 'error'
  }
  timestamp: Date
}

interface SystemMetrics {
  requests: {
    total: number
    successful: number
    failed: number
    avgLatency: number
  }
  memory: {
    used: number
    total: number
    percentage: number
  }
  providers: Record<string, {
    requests: number
    errors: number
    avgLatency: number
  }>
}
```

## System Flow Diagrams

### Request Flow
```
1. Kiro → HTTPS Request → Mockttp Proxy
2. Mockttp → Parse Request → RequestTranslator
3. RequestTranslator → Extract Model ID → ConfigManager
4. ConfigManager → Route Decision:
   - Kiro Model → Forward to AWS Q
   - Custom Model → Continue to step 5
   - Unknown Model → Block with empty response
5. RequestTranslator → Transform to Portkey format
6. RateLimiter → Check rate limit → Wait if needed
7. PortkeyClient → Send to Portkey Gateway
8. Portkey → Route to Provider (Anthropic/OpenAI/etc)
9. Provider → Streaming Response → PortkeyClient
10. ResponseTranslator → Transform to AWS Event Stream
11. ResponseTranslator → Throttle chunks → Mockttp
12. Mockttp → Return to Kiro
13. RequestHistory → Record request metadata
```

### Model Injection Flow
```
1. Kiro → ListAvailableModels → Mockttp
2. Mockttp → Forward to AWS Q
3. AWS Q → Return Kiro models → Mockttp
4. ModelRegistry → Parse response
5. ModelRegistry → Inject custom models from config
6. ModelRegistry → Add cost/quota info from Portkey
7. ModelRegistry → Return modified response → Kiro
```


### Error Handling Flow
```
1. Error occurs in any component
2. Logger → Log error with context
3. Error Handler → Determine error type:
   - Rate Limit → Retry with backoff
   - Network Error → Return user-friendly message
   - Config Error → Fail fast with clear message
   - Provider Error → Return AWS-formatted error
4. ResponseTranslator → Format error as AWS Event Stream
5. Return to Kiro with 200 OK (AWS format expects this)
```

## Implementation Phases

### Phase 1: Core Proxy (Week 1)
**Goal:** Basic HTTPS interception working  
**Deliverables:**
- ProxyManager with Mockttp integration
- Certificate handling
- Request/response logging
- Basic configuration loading

**Success Criteria:**
- Can intercept Kiro's HTTPS traffic
- Can forward requests to AWS Q unmodified
- Kiro works normally through proxy

### Phase 2: Request Translation (Week 2)
**Goal:** AWS Q to Portkey translation  
**Deliverables:**
- RequestTranslator implementation
- AWS Q format parser
- Portkey format builder
- Unit tests for translation

**Success Criteria:**
- Can parse AWS Q requests correctly
- Can transform to Portkey format
- Preserves conversation history
- Handles tool definitions

### Phase 3: Response Translation (Week 3)
**Goal:** Portkey to AWS Event Stream  
**Deliverables:**
- ResponseTranslator implementation
- AWS Event Stream encoder
- Streaming chunk handler
- Binary format tests

**Success Criteria:**
- Can encode AWS Event Stream format
- Kiro displays responses correctly
- Streaming works smoothly
- No corruption in binary data

### Phase 4: Portkey Integration (Week 4)
**Goal:** Connect to Portkey gateway  
**Deliverables:**
- PortkeyClient implementation
- Provider routing
- Error handling
- Retry logic

**Success Criteria:**
- Can route to Anthropic via Portkey
- Can route to OpenAI via Portkey
- Can route to Groq via Portkey
- Handles errors gracefully

### Phase 5: Model Registry (Week 5)
**Goal:** Custom model injection  
**Deliverables:**
- ModelRegistry implementation
- Model metadata caching
- Cost/quota display
- Alias resolution

**Success Criteria:**
- Custom models appear in Kiro
- Cost information displays correctly
- Aliases work as expected
- Kiro models still available

### Phase 6: Rate Limiting (Week 6)
**Goal:** Prevent API rate limit violations  
**Deliverables:**
- RateLimiter implementation
- Token bucket algorithm
- Per-provider limits
- Request queuing

**Success Criteria:**
- Respects rate limits
- No 429 errors from providers
- Requests queued properly
- Backoff works correctly

### Phase 7: Polish & Testing (Week 7-8)
**Goal:** Production-ready system  
**Deliverables:**
- Comprehensive error handling
- Memory leak prevention
- Performance optimization
- Integration tests
- Documentation

**Success Criteria:**
- No memory leaks
- Stable under load
- Clear error messages
- Complete documentation


## Key Advantages Over Python Version

### 1. Portkey Integration
**Python Version:** Custom translation for each provider  
**Node.js Version:** Portkey handles all providers uniformly  
**Benefit:** 
- Single integration point
- Automatic provider updates
- Built-in caching and retry
- Cost tracking included
- 200+ providers supported

### 2. Mockttp vs mitmproxy
**Python Version:** External mitmproxy process  
**Node.js Version:** Mockttp library in-process  
**Benefit:**
- Better error handling
- Programmatic control
- No external dependencies
- Easier debugging
- TypeScript type safety

### 3. Streaming Performance
**Python Version:** Collect all chunks, then translate  
**Node.js Version:** True streaming with backpressure  
**Benefit:**
- Lower memory usage
- Faster time-to-first-token
- Better rate limit handling
- Smoother user experience

### 4. Type Safety
**Python Version:** Runtime type checking  
**Node.js Version:** Compile-time TypeScript validation  
**Benefit:**
- Catch errors before runtime
- Better IDE support
- Self-documenting code
- Easier refactoring

### 5. Configuration Validation
**Python Version:** Manual validation  
**Node.js Version:** Zod schema validation  
**Benefit:**
- Clear error messages
- Type inference
- Runtime safety
- Schema documentation

## Critical Implementation Details

### AWS Event Stream Binary Format
**Must be implemented exactly:**
```typescript
// Prelude structure (12 bytes)
const prelude = Buffer.alloc(12)
prelude.writeUInt32BE(totalLength, 0)      // Total message length
prelude.writeUInt32BE(headersLength, 4)    // Headers length
prelude.writeUInt32BE(preludeCRC, 8)       // CRC32 of first 8 bytes

// Header structure (variable)
// Each header: [name_len:1][name:N][type:1][value_len:2][value:N]
const header = Buffer.concat([
  Buffer.from([nameBytes.length]),
  nameBytes,
  Buffer.from([valueType]),
  Buffer.from([valueLength >> 8, valueLength & 0xFF]),
  valueBytes
])

// Message structure
const message = Buffer.concat([
  prelude,
  headers,
  payload,
  messageCRC  // CRC32 of entire message
])
```

**CRC32 Implementation:**
```typescript
import { crc32 } from 'crc'

function calculateCRC32(buffer: Buffer): number {
  return crc32(buffer) >>> 0  // Unsigned 32-bit
}
```

### Streaming Throttle Implementation
**Prevent rate limits with controlled chunk delivery:**
```typescript
async function* throttleStream(
  stream: AsyncIterable<Buffer>,
  delayMs: number
): AsyncGenerator<Buffer> {
  for await (const chunk of stream) {
    yield chunk
    await new Promise(resolve => setTimeout(resolve, delayMs))
  }
}

// Usage
const throttled = throttleStream(portkeyStream, 50)  // 50ms between chunks
```

### Memory Leak Prevention
**Circular buffer for request history:**
```typescript
class CircularBuffer<T> {
  private buffer: T[]
  private head: number = 0
  private size: number = 0
  
  constructor(private capacity: number) {
    this.buffer = new Array(capacity)
  }
  
  push(item: T): void {
    this.buffer[this.head] = item
    this.head = (this.head + 1) % this.capacity
    this.size = Math.min(this.size + 1, this.capacity)
  }
  
  getAll(): T[] {
    if (this.size < this.capacity) {
      return this.buffer.slice(0, this.size)
    }
    return [
      ...this.buffer.slice(this.head),
      ...this.buffer.slice(0, this.head)
    ]
  }
}
```


### Portkey Configuration Best Practices
**Virtual Keys for provider isolation:**
```typescript
const portkeyConfig = {
  apiKey: process.env.PORTKEY_API_KEY,
  virtualKeys: {
    anthropic: process.env.ANTHROPIC_API_KEY,
    openai: process.env.OPENAI_API_KEY,
    groq: process.env.GROQ_API_KEY
  },
  cache: {
    mode: 'simple',
    maxAge: 3600  // 1 hour
  },
  retry: {
    attempts: 3,
    onStatusCodes: [429, 500, 502, 503, 504]
  }
}
```

**Provider routing:**
```typescript
// Portkey automatically routes based on model prefix
const response = await portkey.chat({
  model: 'anthropic/claude-3-5-sonnet-20241022',
  messages: [...],
  stream: true
})

// Or use virtual keys
const response = await portkey.chat({
  model: 'claude-3-5-sonnet-20241022',
  messages: [...],
  stream: true,
  virtualKey: 'anthropic'  // Routes to Anthropic
})
```

## Testing Strategy

### Unit Tests
**Test each component in isolation:**
```typescript
describe('RequestTranslator', () => {
  it('should parse AWS Q request correctly', () => {
    const awsRequest = { /* ... */ }
    const result = translator.parseAWSRequest(JSON.stringify(awsRequest))
    expect(result.conversationState).toBeDefined()
  })
  
  it('should extract messages from history', () => {
    const messages = translator.extractMessages(awsRequest)
    expect(messages).toHaveLength(3)
    expect(messages[0].role).toBe('user')
  })
  
  it('should transform to Portkey format', () => {
    const portkey = translator.toPortkeyFormat(awsRequest)
    expect(portkey.messages).toBeDefined()
    expect(portkey.stream).toBe(true)
  })
})
```

### Integration Tests
**Test component interactions:**
```typescript
describe('End-to-End Flow', () => {
  it('should route request through full pipeline', async () => {
    // Start proxy
    await proxy.start(29974)
    
    // Make request to proxy
    const response = await axios.post('http://localhost:29974/generateAssistantResponse', {
      conversationState: { /* ... */ }
    })
    
    // Verify response format
    expect(response.status).toBe(200)
    expect(response.headers['content-type']).toBe('application/vnd.amazon.eventstream')
  })
})
```

### Load Tests
**Verify performance under load:**
```typescript
describe('Performance', () => {
  it('should handle 100 concurrent requests', async () => {
    const requests = Array(100).fill(null).map(() => 
      makeRequest()
    )
    
    const results = await Promise.all(requests)
    const successful = results.filter(r => r.success).length
    
    expect(successful).toBeGreaterThan(95)  // 95% success rate
  })
  
  it('should not leak memory', async () => {
    const initialMemory = process.memoryUsage().heapUsed
    
    // Make 1000 requests
    for (let i = 0; i < 1000; i++) {
      await makeRequest()
    }
    
    global.gc()  // Force garbage collection
    const finalMemory = process.memoryUsage().heapUsed
    
    // Memory should not grow significantly
    expect(finalMemory - initialMemory).toBeLessThan(10 * 1024 * 1024)  // 10MB
  })
})
```

## Configuration Examples

### Minimal Configuration
```yaml
# config.yaml
proxy:
  port: 29974

portkey:
  apiKey: "pk_xxx"
  virtualKeys:
    anthropic: "sk-ant-xxx"

providers:
  anthropic:
    enabled: true
    models:
      - name: "claude-3-5-sonnet-20241022"
        alias: ["claude"]

debug:
  enabled: false
  logLevel: "info"
```

### Full Configuration
```yaml
# config.yaml
proxy:
  port: 29974
  host: "127.0.0.1"

kiro:
  exePath: null  # Auto-detect
  autoLaunch: true

kiroEndpoint:
  telemetry: false
  updates: false
  models: true
  usageLimits: "auto"

portkey:
  apiKey: "pk_xxx"
  virtualKeys:
    anthropic: "sk-ant-xxx"
    openai: "sk-xxx"
    groq: "gsk-xxx"
  cache:
    enabled: true
    mode: "simple"
    maxAge: 3600
  retry:
    enabled: true
    attempts: 3
    onStatusCodes: [429, 500, 502, 503, 504]

providers:
  anthropic:
    enabled: true
    type: "anthropic"
    models:
      - name: "claude-3-5-sonnet-20241022"
        alias: ["claude", "sonnet"]
        displayName: "Claude 3.5 Sonnet"
        description: "Most capable Claude model"
        maxTokens: 8192
  
  openai:
    enabled: true
    type: "openai"
    models:
      - name: "gpt-4o"
        alias: ["gpt4"]
        displayName: "GPT-4o"
        maxTokens: 4096
  
  groq:
    enabled: true
    type: "groq"
    models:
      - name: "llama-3.3-70b-versatile"
        alias: ["llama"]
        displayName: "Llama 3.3 70B"
        maxTokens: 8192

rateLimit:
  enabled: true
  defaultInterval: 2000  # 2 seconds
  perProvider:
    groq: 3000  # 3 seconds for Groq
    openai: 500  # 0.5 seconds for OpenAI

debug:
  enabled: true
  logLevel: "debug"
  saveInteractions: true
  outputDir: "./logs"
```


## Project Structure

```
kiropipe-node/
├── src/
│   ├── core/
│   │   ├── ProxyManager.ts          # Mockttp proxy
│   │   ├── RequestTranslator.ts     # AWS Q → Portkey
│   │   ├── ResponseTranslator.ts    # Portkey → AWS Event Stream
│   │   └── PortkeyClient.ts         # Portkey integration
│   │
│   ├── components/
│   │   ├── ConfigManager.ts         # Configuration
│   │   ├── ModelRegistry.ts         # Model tracking
│   │   ├── RequestHistory.ts        # Request logging
│   │   ├── RateLimiter.ts          # Rate limiting
│   │   ├── Logger.ts               # Logging
│   │   └── HealthMonitor.ts        # Health checks
│   │
│   ├── types/
│   │   ├── aws.ts                  # AWS Q types
│   │   ├── portkey.ts              # Portkey types
│   │   ├── config.ts               # Config types
│   │   └── index.ts                # Exports
│   │
│   ├── utils/
│   │   ├── crc32.ts                # CRC32 calculation
│   │   ├── eventStream.ts          # Event stream helpers
│   │   ├── circularBuffer.ts       # Memory-safe buffer
│   │   └── validation.ts           # Zod schemas
│   │
│   ├── index.ts                    # Main entry point
│   └── cli.ts                      # CLI interface
│
├── tests/
│   ├── unit/
│   │   ├── RequestTranslator.test.ts
│   │   ├── ResponseTranslator.test.ts
│   │   ├── ModelRegistry.test.ts
│   │   └── RateLimiter.test.ts
│   │
│   ├── integration/
│   │   ├── proxy.test.ts
│   │   ├── portkey.test.ts
│   │   └── endToEnd.test.ts
│   │
│   └── fixtures/
│       ├── awsRequests.json
│       ├── portkeyResponses.json
│       └── configs.yaml
│
├── config/
│   ├── config.yaml                 # User configuration
│   ├── config.example.yaml         # Example config
│   └── schema.json                 # JSON schema
│
├── logs/                           # Debug logs (gitignored)
├── docs/                           # Documentation
│   ├── API.md
│   ├── CONFIGURATION.md
│   └── DEVELOPMENT.md
│
├── package.json
├── tsconfig.json
├── .env.example
├── .gitignore
└── README.md
```

## Dependencies

### Production Dependencies
```json
{
  "dependencies": {
    "mockttp": "^3.10.0",
    "portkey-ai": "^1.0.0",
    "yaml": "^2.3.4",
    "zod": "^3.22.4",
    "winston": "^3.11.0",
    "node-cache": "^5.1.2",
    "axios": "^1.6.2",
    "crc": "^4.3.2",
    "express": "^4.18.2"
  }
}
```

### Development Dependencies
```json
{
  "devDependencies": {
    "@types/node": "^20.10.0",
    "@types/express": "^4.17.21",
    "typescript": "^5.3.3",
    "ts-node": "^10.9.2",
    "jest": "^29.7.0",
    "@types/jest": "^29.5.11",
    "ts-jest": "^29.1.1",
    "eslint": "^8.55.0",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "@typescript-eslint/parser": "^6.14.0",
    "prettier": "^3.1.1",
    "nodemon": "^3.0.2"
  }
}
```

## Development Commands

```json
{
  "scripts": {
    "dev": "nodemon --exec ts-node src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "format": "prettier --write src/**/*.ts",
    "type-check": "tsc --noEmit"
  }
}
```

## Environment Variables

```bash
# .env
PORTKEY_API_KEY=pk_xxx
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GROQ_API_KEY=gsk-xxx

# Optional
PROXY_PORT=29974
LOG_LEVEL=info
DEBUG_MODE=false
```

## Error Codes and Messages

### System Errors
```typescript
enum ErrorCode {
  // Configuration errors (1xxx)
  CONFIG_NOT_FOUND = 1001,
  CONFIG_INVALID = 1002,
  CONFIG_MISSING_REQUIRED = 1003,
  
  // Proxy errors (2xxx)
  PROXY_START_FAILED = 2001,
  PROXY_CERT_ERROR = 2002,
  PROXY_PORT_IN_USE = 2003,
  
  // Translation errors (3xxx)
  TRANSLATION_PARSE_ERROR = 3001,
  TRANSLATION_FORMAT_ERROR = 3002,
  TRANSLATION_ENCODING_ERROR = 3003,
  
  // Provider errors (4xxx)
  PROVIDER_NOT_CONFIGURED = 4001,
  PROVIDER_AUTH_FAILED = 4002,
  PROVIDER_RATE_LIMITED = 4003,
  PROVIDER_TIMEOUT = 4004,
  
  // Model errors (5xxx)
  MODEL_NOT_FOUND = 5001,
  MODEL_DISABLED = 5002,
  MODEL_QUOTA_EXCEEDED = 5003
}
```

### User-Facing Error Messages
```typescript
const ERROR_MESSAGES = {
  [ErrorCode.CONFIG_NOT_FOUND]: 
    'Configuration file not found. Please create config.yaml',
  
  [ErrorCode.PROVIDER_RATE_LIMITED]: 
    'Rate limit exceeded. Please wait a moment and try again.',
  
  [ErrorCode.MODEL_NOT_FOUND]: 
    'Model not found. Please check your configuration.',
  
  [ErrorCode.PROVIDER_AUTH_FAILED]: 
    'Authentication failed. Please check your API key.'
}
```

