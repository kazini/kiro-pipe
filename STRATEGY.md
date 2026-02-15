# Kiro-Conduit Strategy Document

## Executive Summary
Kiro IDE implements certificate pinning to prevent man-in-the-middle attacks. Therefore, traditional proxy-based interception (mitmproxy, DNS spoofing) are not viable. This strategy focuses on two proven approaches that bypass certificate pinning: **Frida Runtime Injection** and **Electron App Modification**. We evaluate both, with Frida as the primary path and Electron unpacking as the fallback.

## Certificate Pinning Assessment
Based on industry best practices and the architecture of modern Electron apps like Kiro, certificate pinning is very likely implemented. This eliminates proxy-based approaches entirely and requires deep-level interception.

---

## Viable Approaches

### Approach A: Frida Runtime Injection (PRIMARY STRATEGY)
**Overview**: Use Frida to inject JavaScript code into the running Kiro process at runtime. The injected code hooks certificate validation functions and intercepts API calls before they're encrypted, allowing transparent request redirection.

**How It Works**:
1. Kiro IDE starts normally
2. User launches kiro-conduit launcher/configuration tool
3. Frida attaches to running Kiro process
4. JavaScript hooks are injected that:
   - Bypass/disable certificate pinning validation
   - Intercept outbound API calls
   - Route calls to local proxy or directly to target LLM
   - Translate responses back to Kiro format
5. User continues using Kiro normally with custom LLM backend
6. To disable: User stops the conduit service or restarts Kiro

**Pros**:
- Non-invasive (no app modification, no redistribution needed)
- Works immediately without user reinstalling Kiro
- Survives Kiro updates automatically
- Can be toggled on/off without restarting the system
- User doesn't need to modify system CA certificates
- Elegant from a user experience perspective
- Only requires Frida installation

**Cons**:
- Frida installation required (an extra tool to download)
- Frida may trigger antivirus warnings on some systems
- Runtime hooking requires deep knowledge of Kiro's internals
- More complex to debug if something goes wrong
- Requires JavaScript/Frida scripting expertise
- May impact Kiro performance minimally

**Technical Complexity**: HIGH
**Implementation Effort**: 2-3 weeks
**Maintenance Burden**: Medium (must handle Kiro version updates)
**User Friction**: Low (simple setup, automatic after install)

**Why This is the Primary Strategy**:
- Non-invasive (no modified Kiro binary to maintain)
- Survives Kiro updates completely automatically
- Clean, reversible operation
- Modern approach used by security researchers

---

### Approach B: Electron App Modification (FALLBACK STRATEGY)
**Overview**: Extract Kiro's bundled Electron app (app.asar), modify the certificate validation code, repack, and provide users with the modified version.

**How It Works**:
1. Extract app.asar using @electron/asar
2. Search for and analyze certificate pinning implementation
3. Modify JavaScript files to disable certificate validation
4. Modify Node.js bindings if necessary
5. Repack into app.asar
6. Replace user's Kiro app.asar with modified version
7. Kiro runs with certificate validation disabled
8. Local proxy can now intercept and redirect traffic

**Pros**:
- Guaranteed to work (direct code modification)
- No runtime dependencies (no Frida needed)
- Simpler to understand and debug
- Single modification step, then use normally
- No antivirus/security software interference risks
- Well-understood approach in the security community

**Cons**:
- Creates modified Kiro binary diverging from official version
- Must maintain compatibility through future Kiro updates
- Users must replace Kiro binary (file system write, admin access)
- Kiro updates require re-modification and redistribution
- Larger distributable file (entire modified app)
- May have unintended side effects from modifications
- Could potentially violate Kiro's terms of service

**Technical Complexity**: MEDIUM
**Implementation Effort**: 1-2 weeks (initial), ongoing for each Kiro update
**Maintenance Burden**: High (must track and apply changes to new versions)
**User Friction**: Medium (requires replacing app file, survives updates only if we provide patches)

**Why This is the Fallback**:
- More maintenance burden than Frida
- Users must manually update when Kiro updates (or we provide patches)
- Larger file distribution and storage
- Regulatory/licensing uncertainty

---

## Decision Framework: Frida vs Electron Modification

| Factor | Frida | Electron | Winner |
|--------|-------|----------|--------|
| **Setup Complexity** | Medium | Low | Electron |
| **Update Handling** | Automatic | Manual/Patch | Frida ⭐ |
| **Maintenance Burden** | Medium | High | Frida ⭐ |
| **Performance Impact** | Minimal | None | Electron |
| **User Experience** | Seamless toggle | Manual binary swap | Frida ⭐ |
| **Debugging Difficulty** | Medium-High | Low | Electron |
| **Risk of AV Detection** | Medium | Low | Electron ⭐ |
| **Invasiveness** | Medium | High | Frida ⭐ |

**Recommendation: PRIMARY = Frida, FALLBACK = Electron**

---

## Implementation Roadmap

### Phase 1: Initial Development (1 week)

**Primary Path (Frida)**:
1. Analyze Kiro's process structure and Node.js/Chromium internals
2. Identify certificate validation function locations
3. Develop JavaScript hooks for certificate validation bypass
4. Develop request interception and routing hooks
5. Create Python Frida launcher tool
6. Build basic local proxy for request translation
7. **Milestone**: Route one API call successfully through custom backend

**If Frida Blocked**: Immediate pivot to Electron approach

### Phase 2: Integration (1-2 weeks)
1. Build request/response translation layer
2. Implement Ollama translator
3. Implement OpenRouter translator
4. Configuration system
5. Error handling and retry logic
6. **Milestone**: Kiro → Ollama full flow working

### Phase 3: Testing & Hardening (1 week)
1. Comprehensive testing across scenarios
2. Performance benchmarking
3. Edge case handling
4. Documentation and user guides
5. **Milestone**: Production-ready release

---

## Fallback Strategy if Frida Fails

If during Phase 1 we find that Frida cannot adequately hook certificate validation:

1. **Switch to Electron App Modification**
   - Extract app.asar for installed Kiro version
   - Modify certificate validation code
   - Build automated modification/patching tool
   - Create distribution mechanism for users

2. **Plan for Updates**
   - Monitor Kiro release notes
   - Update modification script when needed
   - Test against new Kiro versions
   - Provide patch downloads or auto-update script

---

## Risk Assessment and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Frida hooks break on Kiro update | Feature stops working | MEDIUM | Monitor Kiro versions, update hooks as needed |
| Frida detected by antivirus | User experience issue | LOW | Have Electron backup, document workaround |
| Certificate validation deeper than expected | Frida insufficient | LOW | Switch to Electron unpacking |
| Complex API translation requirements | Delayed implementation | MEDIUM | Prototype early with actual captured requests |
| Request/response format changes between versions | Compatibility issues | LOW | Version-lock translators, monitor changes |
| User adoption low due to complexity | Project deemed not viable | MEDIUM | Provide excellent setup guides and automation tools |

---

## Architecture Overview

```
User Workflow:
┌─────────────────┐
│   User Opens    │
│  Kiro IDE       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Kiro Process Running               │
│  ┌───────────────────────────────┐  │
│  │ Frida Runtime Hooks Injected  │  │
│  │ - Certificate bypass          │  │
│  │ - Request interception        │  │
│  └───────────────────────────────┘  │
└────────┬────────────────────────────┘
         │ Modified API calls
         ▼
┌────────────────────────┐
│ Local Proxy Service    │
│ - Request translation  │
│ - Response conversion  │
│ - Error handling       │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────────┐
│ Target LLM Backend         │
│ ├─ Ollama (local)          │
│ ├─ OpenRouter (cloud)      │
│ └─ Custom provider         │
└────────────────────────────┘
```

---

## Timeline

**Week 1**: Implementation & First Success
- Analyze Kiro internals
- Develop Frida hooks
- Test basic interception
- Decision: Frida working? Continue. Not working? Switch to Electron.

**Week 2-3**: Integration & Multiple Backends
- Build translation layer
- Implement Ollama + OpenRouter support
- Configuration system
- Error handling

**Week 4**: Testing & Release
- Comprehensive testing
- Performance optimization
- Documentation
- Release v0.1

---

## Success Criteria for Phase 1

- [ ] Successfully inject Frida hooks into running Kiro
- [ ] Bypass certificate validation without crashing Kiro
- [ ] Intercept at least one API call
- [ ] Modify intercepted request and return custom response
- [ ] Kiro IDE continues functioning normally
- [ ] Hooks survive multiple sequential requests

If all criteria met → Proceed with Frida
If any criterion fails → Pivot to Electron approach within 48 hours
