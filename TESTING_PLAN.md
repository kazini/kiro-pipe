# Kiro-Conduit Testing Plan

## Testing Objectives
- Validate that each approach can successfully intercept Kiro traffic
- Determine which approach is most viable for production use
- Establish testing procedures for ongoing validation
- Create benchmarks for performance and reliability

## Phase 1: Reconnaissance Testing (Certificate Pinning Detection)

### Test 1.1: mitmproxy Baseline Interception Test

**Objective**: Determine if Kiro can be intercepted at the HTTPS level without certificate pinning.

**Prerequisites**:
- mitmproxy installed on test machine
- Kiro IDE running and configured
- Network route configured to proxy through mitmproxy

**Test Procedure**:
1. Start mitmproxy with verbose logging
2. Install mitmproxy's CA certificate as system root certificate
3. Configure system/network to route HTTPS traffic through mitmproxy
4. Launch Kiro IDE and trigger an API call (e.g., code completion, chat)
5. Observe mitmproxy console for intercepted requests
6. Log all API endpoints, request methods, headers, and response formats

**Expected Outcome (No Pinning)**:
```
Plaintext API requests visible in mitmproxy
Request format: POST /api/v1/chat
Headers include: Authorization, Content-Type
Response bodies fully readable
```

**Expected Outcome (With Pinning)**:
```
TLS Handshake Failure (Hostname/Certificate Validation Error)
Error message: "Could not validate certificate"
Kiro IDE fails to connect or shows auth error
```

**Pass Criteria**: At least one complete API call captured without connection errors

**Failure Handling**: If certificate pinning is detected, proceed to Phase 2 with runtime hooking or app modification approach

**Logging**: 
- Save mitmproxy capture file (`.mitm` format)
- Document all discovered endpoints
- Record response structure and data types

---

### Test 1.2: API Endpoint Discovery

**Objective**: Map all API endpoints that Kiro uses on startup and during normal operation.

**Prerequisites**: Successful completion of Test 1.1

**Test Procedure**:
1. Filter mitmproxy captures to only Kiro domains
2. Categorize requests by endpoint pattern
3. Document request/response pairs for each endpoint
4. Identify authentication tokens and their refresh patterns
5. Note response data formats and structures

**Data to Document**:
- Endpoint URL pattern
- HTTP method (GET, POST, PUT, DELETE)
- Request headers (authorization, content-type, custom headers)
- Request body format (JSON schema)
- Response body format (JSON schema)
- Frequency/timing patterns
- Error responses

**Output**: `API_ENDPOINTS_DISCOVERED.md` with complete mapping

---

### Test 1.3: Authentication Flow Analysis

**Objective**: Understand how Kiro's authentication works and identify where tokens are stored/refreshed.

**Prerequisites**: Successful completion of Test 1.1

**Test Procedure**:
1. Capture authentication handshake on app startup
2. Identify token types (bearer, refresh, session, etc.)
3. Document token storage location (localStorage, sessionStorage, file-based)
4. Monitor token refresh requests during app usage
5. Identify authentication server endpoints (matching known patterns like `prod.us-east-1.auth.desktop.kiro.dev`)

**Key Information to Extract**:
- Token format and structure
- Token expiration times
- Refresh token endpoint
- Account/user identification method
- Any certificate pinning related to auth endpoints

**Output**: `AUTH_FLOW_ANALYSIS.md`

---

## Phase 2: Approach Viability Testing

### Test 2.1: Frida Runtime Hooking PoC

**Objective**: Validate that Frida can successfully hook into Kiro process and intercept certificate validation.

**Prerequisites**:
- Frida and Frida tools installed
- Kiro process running
- JavaScript knowledge of certificate validation patterns

**Test Procedure**:
1. Identify certificate validation functions in Kiro's Node.js/Chromium internals
2. Create Frida script to hook these functions
3. Inject hook script into running Kiro process
4. Trigger API call and observe hook execution
5. Verify if certificate validation can be bypassed

**Success Criteria**:
- [ ] Hook successfully injects into Kiro process
- [ ] Certificate validation function is callable
- [ ] Bypass can be applied without crashing Kiro
- [ ] API requests succeed after bypass

**Frida Script Template**:
```javascript
// Hook Node.js https module
var https = Module.findExportByName(null, "https");
// Hook certificate validation (location varies by Node version)
// Log all intercepted calls
```

**Failure Handling**: If Frida cannot hook, fallback to Electron unpacking approach

---

### Test 2.2: Electron App Unpacking & Modification PoC

**Objective**: Validate that Kiro's Electron app can be successfully unpacked, modified, and repacked.

**Prerequisites**:
- @electron/asar tool installed
- Python script to automate modification
- Kiro's app.asar extracted and analyzed

**Test Procedure**:
1. Extract app.asar from Kiro installation: `npx @electron/asar extract app.asar unpacked/`
2. Search unpacked files for certificate pinning code:
   - `certificatePinner`
   - `checkServerTrusted`
   - `https.Agent({ rejectUnauthorized: false })`
   - Certificate pinning libraries (e.g., `certificate-pin`)
3. Document pinning implementation if found
4. Create modification to disable or redirect certificate validation
5. Repack app: `npx @electron/asar pack unpacked/ app.asar.modified`
6. Test modified app functionality
7. Verify API requests now route to custom proxy

**Success Criteria**:
- [ ] app.asar successfully extracted
- [ ] Packing/repacking maintains app integrity
- [ ] Modified version starts without errors
- [ ] Certificate validation can be disabled/modified

**Output**: 
- `CERTIFICATE_PINNING_ANALYSIS.md` (findings)
- `app_modification_script.py` (automation)

---

### Test 2.3: DNS Spoofing + Local Proxy PoC

**Objective**: Validate that DNS spoofing can redirect Kiro's API calls to a local proxy.

**Prerequisites**:
- mitmproxy for HTTPS decryption (from Test 1.1)
- Local proxy server skeleton in Python
- Hosts file modification capability

**Test Procedure**:
1. Identify all Kiro API domains from Test 1.2
2. Create hosts file entries redirecting these domains to `localhost`
3. Build minimal Python proxy that:
   - Listens on 443 for HTTPS
   - Decrypts traffic via mitmproxy/certificate
   - Logs all requests
   - Forwards to mitmproxy or custom endpoint
4. Test with single API endpoint
5. Verify traffic is intercepted and can be modified

**Success Criteria**:
- [ ] Hosts file entries successfully redirect DNS
- [ ] Local proxy receives Kiro's API requests
- [ ] HTTPS decryption works (with installed CA cert)
- [ ] Can modify requests in-flight and return custom responses

**Failure Points**:
- Certificate pinning prevents connection
- Hosts file insufficient for app-level DNS caching
- HTTPS port already in use

---

## Phase 3: Integration Testing

### Test 3.1: Request/Response Translation

**Objective**: Verify that Kiro API requests can be successfully translated to target LLM APIs.

**Scope**: Create test cases for each supported LLM backend

**Test Data**:
- Sample Kiro chat request (from Test 1.2)
- Expected format for Ollama API
- Expected format for OpenRouter API

**Test Procedure for Each LLM**:
1. Capture authentic Kiro request from Test 1.2
2. Create translator function to convert to target LLM format
3. Send translated request to target LLM
4. Translate response back to Kiro format
5. Verify Kiro accepts response without error
6. Validate response data integrity and quality

**Test Cases**:
- [ ] Simple text completion
- [ ] Multi-turn conversation
- [ ] Code generation
- [ ] Error handling (invalid model, timeout)
- [ ] Large token responses (truncation handling)
- [ ] Special characters and encoding

---

### Test 3.2: End-to-End Flow Testing

**Objective**: Complete user workflow from Kiro IDE through custom LLM backend.

**Test Scenario**:
1. User opens Kiro IDE
2. User types chat prompt or requests code completion
3. Request is intercepted and routed to local Ollama instance
4. Ollama response is translated and returned to Kiro
5. Kiro displays response in UI
6. User continues normal Kiro workflow

**Success Criteria**:
- [ ] No interruption to Kiro's UI responsiveness
- [ ] Response latency < 5 seconds (including LLM processing)
- [ ] Response quality is acceptable for user
- [ ] No errors or exceptions in logs
- [ ] Multiple sequential requests work correctly

---

## Phase 4: Performance & Reliability Testing

### Test 4.1: Latency Benchmarking

**Objective**: Establish baseline latency overhead from interception layer.

**Metrics to Measure**:
- Time from API request sent by Kiro → time interceptor receives it
- Time from translator sends request → target LLM receives it
- Time from LLM responds → translator processes it
- Time from translator sends response → Kiro receives it
- Total end-to-end latency

**Test Procedure**:
1. Run 50+ requests through each stage
2. Record timestamps at each boundary
3. Calculate percentiles (p50, p90, p99)
4. Compare with direct API calls (baseline)

**Pass Criteria**:
- Total overhead < 200ms (p95)
- No single stage exceeds 100ms overhead

---

### Test 4.2: Stability & Error Recovery

**Objective**: Verify system remains stable under various failure conditions.

**Failure Scenarios**:
- [ ] Target LLM becomes unavailable
- [ ] Network interruption during translation
- [ ] Invalid response format from LLM
- [ ] Kiro forces reconnection rapidly
- [ ] Token expiration during request
- [ ] Very large prompt (token limit exceeded)

**Expected Behavior**:
- Graceful error messages to user
- Logging of error conditions
- Automatic retry where appropriate
- Fallback mechanisms

---

## Test Environment Setup

### Hardware Requirements
- Test Machine OS: Windows (matching user environment)
- Disk Space: 2GB (for Kiro + development tools)
- Network: Stable internet connection
- RAM: 8GB minimum

### Software Stack
```
- Kiro IDE (latest stable version)
- Python 3.9+ (for proxy development)
- mitmproxy (latest)
- Frida (latest)
- Ollama (for LLM testing)
- OpenRouter API key (for cloud testing)
- Node.js (for @electron/asar)
```

### Test Configuration File
Create `test_config.toml`:
```toml
[test_environment]
kiro_install_path = "C:/Program Files/Kiro"
proxy_port = 8443
log_level = "DEBUG"
capture_traffic = true

[target_llms]
ollama_endpoint = "http://localhost:11434"
openrouter_api_key = "xxx"

[mitmproxy]
cert_path = "~/.mitmproxy/mitmproxy-ca-cert.pem"
port = 8080
```

---

## Test Reporting

### For Each Test Phase, Document:
1. **Test Date & Environment**
2. **Pass/Fail Status**
3. **Findings & Observations**
4. **Discovered Issues**
5. **Recommendations for Next Phase**
6. **Evidence** (screenshots, logs, captures)

### Test Report Template
```markdown
# Test Report: [Test Name]
**Date**: [YYYY-MM-DD]
**Tester**: [Name]
**Status**: PASS / FAIL / BLOCKED

## Objective
[Objective from test plan]

## Procedure
[Steps taken]

## Results
[What happened]

## Evidence
[Logs, screenshots, captures]

## Issues Discovered
- [Issue 1]
- [Issue 2]

## Next Steps
[Recommendations]
```

---

## Success Criteria Summary

| Phase | Completion Criteria | Time Budget |
|-------|-------------------|-------------|
| 1 | Certificate pinning status determined, API endpoints mapped | 1 week |
| 2 | At least 1 viable approach validated (Frida OR Electron unpacking) | 1 week |
| 3 | Request/response translation works for 1 LLM backend | 1 week |
| 4 | Latency and reliability meet production criteria | 1 week |

**Total Testing Timeline**: 4 weeks
