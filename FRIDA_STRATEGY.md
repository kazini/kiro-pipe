# Frida Injection Strategy - Kiro API Interception

## Overview

Now that we have identified the exact API endpoints, we can develop a targeted Frida injection strategy to intercept Kiro's network traffic and redirect it to alternative LLMs.

---

## Target API Endpoints

```
Authentication:  https://prod.us-east-1.auth.desktop.kiro.dev
Application:     https://app.kiro.dev
Downloads:       https://prod.download.desktop.kiro.dev
Telemetry:       https://gamma.us-east-1.telemetry.desktop.kiro.dev
```

---

## Frida Hook Strategy

### Phase 1: Certificate Bypass (Priority: CRITICAL)

**Objective**: Bypass certificate pinning validation

**Hook Targets** (in order of attempt):
1. `tls.createConnection()` in Node.js
2. `socket.on('secureConnect')` events
3. `crypto.createSecureContext()` in Node.js
4. Chromium's `net::URLRequestContext::SetProxyDelegate()`

**Hook Location**: 
```javascript
// Target: Node.js https module
// Before: Certificate validation
// After: Connection established

// Possible hook point:
Node.js/lib/tls.js: TLSSocket.prototype._final()
```

**Implementation Pattern**:
```javascript
// Frida hook - pseudocode
Interceptor.attach(moduleName.getExportByName('NODE_TLS_VALIDATE'), {
    onEnter: function(args) {
        console.log("TLS Validation intercepted!");
        // Log certificate details
    },
    onLeave: function(retval) {
        // Force validation to pass
        retval.replace(SUCCESS_CODE);
    }
});
```

---

### Phase 2: Request Interception (Priority: HIGH)

**Objective**: Capture and log all HTTPs requests to kiro.dev domains

**Hook Targets**:
1. `socket.write()` - to intercept TLS record writes
2. `https.request()` - at HTTP layer
3. `fetch()` - if used anywhere (unlikely in Electron)
4. `node_modules/http` - underlying HTTP implementation

**Hook Location**: 
```javascript
// Target: At socket write level
// Catches all encrypted data before TLS encryption
```

**Implementation Pattern**:
```javascript
// Intercept HTTPS request before sending
Interceptor.attach(httpModule['createConnection'], {
    onEnter: function(args) {
        const options = args[0];
        if (options.hostname && options.hostname.includes('kiro.dev')) {
            console.log('Kiro API Request:', {
                method: options.method,
                hostname: options.hostname,
                path: options.path,
                headers: options.headers
            });
        }
    }
});
```

---

### Phase 3: Request Redirection (Priority: HIGH)

**Objective**: Redirect Kiro API calls to local translation server

**Potential Implementation**:

#### Option A: Hostname Redirection
```javascript
// Intercept DNS resolution
Interceptor.attach(nameLookup, {
    onLeave: function(retval) {
        if (retval.hostname.includes('prod.us-east-1.auth.desktop.kiro.dev')) {
            retval.replace('localhost:8888');
        }
    }
});
```

#### Option B: Socket Hijacking
```javascript
// Intercept socket creation and reroute
Interceptor.attach(net.createConnection, {
    onEnter: function(args) {
        const options = args[0];
        if (options.hostname && options.hostname.includes('kiro.dev')) {
            args[0].hostname = 'localhost';
            args[0].port = 8888;
        }
    }
});
```

#### Option C: Proxy Injection
```javascript
// Force all traffic through local proxy
Interceptor.attach(agent.addRequest, {
    onEnter: function(args) {
        // Redirect request through local proxy
        args[0].proxy = 'http://localhost:8888';
    }
});
```

---

## Local Translation Server Architecture

### Purpose
Intercepts Kiro's API requests and:
1. Translates Kiro API format → OpenAI/Anthropic format
2. Routes to alternative LLM backend
3. Translates response back → Kiro format
4. Returns to Kiro with certificate validation acceptable

### Technology Stack
- **Framework**: Python FastAPI or Node.js Express
- **Port**: 8888 (or configurable)
- **Endpoints Needed**:
  - `/auth/*` - Handle authentication requests
  - `/api/*` - Handle LLM requests
  - `/download/*` - Mirror download server (optional)

### Request Flow
```
Kiro Client Request
        ↓
[Frida Hook - Certificate Bypass]
        ↓
TLS Connection Allowed (cert validation skipped/faked)
        ↓
Request sent to localhost:8888 (via hostname redirection)
        ↓
Local Translation Server
        ↓
Convert: Kiro API format → OpenAI/Anthropic format
        ↓
Query: Alternative LLM (OpenAI, Claude, locally-hosted, etc.)
        ↓
Convert: Response → Kiro API format
        ↓
Return: To Kiro with fake certificate
        ↓
Kiro processes response as if from official server
```

---

## Implementation Roadmap

### Week 1-2: Frida Hook Development

**Day 1-2**: Certificate Bypass Hook
- [ ] Develop basic Frida script to attach to running Kiro
- [ ] Identify exact Node.js TLS function to hook
- [ ] Bypass first certificate validation
- [ ] Test: Can Kiro make HTTPS requests?

**Day 3-4**: Request Interception Hook  
- [ ] Hook socket.write() or https.request()
- [ ] Log request headers and body
- [ ] Identify request format/authentication scheme
- [ ] Test: Can we see actual API requests?

**Day 5-7**: Request Redirection Hook
- [ ] Implement hostname redirection
- [ ] Test: Can Kiro be tricked into using localhost?
- [ ] Handle TLS session reuse issues
- [ ] Stabilize hooks (prevent crashes)

### Week 3: Translation Server Development

**Day 1-2**: API Mapping
- [ ] Document Kiro's exact API format
- [ ] Document target LLM API format
- [ ] Create translation layer

**Day 3-4**: Server Implementation
- [ ] Build FastAPI/Express server
- [ ] Implement Kiro API endpoints
- [ ] Add translation logic
- [ ] Add alternative LLM integration

**Day 5**: Integration Testing
- [ ] Full end-to-end test
- [ ] Fix incompatibilities
- [ ] Optimize response times

### Week 4: Hardening & Fallback

- [ ] Handle multiple simultaneous requests
- [ ] Implement request queuing if needed
- [ ] Add fallback error handling
- [ ] Test with real Kiro workflows
- [ ] Production-ready release

---

## Risk Mitigation

### Risk 1: Certificate Validation in Chromium (not Node.js)
**Mitigation**: If Node.js hooks don't work, hook Chromium directly
- Requires: Understanding V8 internals
- Alternative: Use fallback Electron repackaging approach

### Risk 2: Kiro Detects Tampering
**Mitigation**: Implement anti-tampering detection avoidance
- Hook detection functions
- Fake version strings
- Simulate "authentic" responses

### Risk 3: TLS Session Resumption
**Mitigation**: Ensure session IDs are properly handled
- Clear session cache if needed
- Force handshake renegotiation

### Risk 4: Multiple Process Instances
**Mitigation**: Frida hooks per process
- Ensure main process, worker processes, and extensions all hooked
- May need separate Frida scripts for each

---

## Success Criteria

✅ **Phase 1 Success**: 
- Kiro makes HTTPS request to kiro.dev domain without certificate error
- Request visible in Frida output

✅ **Phase 2 Success**:
- Can see full request content (headers, body)
- Can identify authentication method
- Understand request structure

✅ **Phase 3 Success**:
- Kiro can communicate with localhost:8888 server
- Server returns valid responses
- Kiro processes responses normally

✅ **Full Integration Success**:
- Kiro uses alternative LLM without errors
- Requests translated correctly
- Responses appear natural to Kiro

---

## Tools & Setup

### Frida Installation
```bash
pip install frida frida-tools
pip install pycloak  # For Android-style obfuscation hiding
```

### Frida Script Location
```
kiro-conduit/
├── frida-scripts/
│   ├── attach.py              # Main attachment script
│   ├── certificate_bypass.js  # Certificate validation hook
│   ├── request_logger.js      # Request logging hook
│   ├── request_redirect.js    # Hostname redirection hook
│   └── combined.js            # All hooks combined
├── translation-server/
│   ├── main.py                # FastAPI server
│   ├── translators/
│   │   ├── kiro_to_openai.py
│   │   ├── openai_to_kiro.py
│   │   └── ...
│   └── llm_backends/
│       ├── openai_client.py
│       ├── anthropic_client.py
│       └── ...
```

---

## Alternative: If Frida Fails

**Fallback Strategy**: Electron App Repackaging (Week 5-6)
- Extract Kiro.exe (Electron archive)
- Modify `extension.js` to use `localhost:8888`
- Remove or bypass certificate pinning in source
- Repackage Electron app
- Deploy modified version

**Pros**: 100% guaranteed to work  
**Cons**: Requires repackaging for every Kiro update

---

## Next Steps

1. **Start Frida Development** (this week)
   - Set up Frida environment
   - Write basic attachment script
   - Identify exact TLS hook points

2. **Parallel: Design Translation Server**
   - Map Kiro API endpoints
   - Design translation logic
   - Prototype transformation functions

3. **Test Against Real Kiro**
   - Launch Kiro instance
   - Attach Frida scripts
   - Monitor hooks firing

4. **Iterate & Refine**
   - Fix crashes/incompatibilities
   - Expand coverage to all process types
   - Optimize performance

