# Kiro-Conduit Development Workflow

## Overview
This document provides the step-by-step workflow for developing kiro-conduit across all phases. It defines how work is organized, tracked, and transitioned between phases.

## Phase-Based Development Model

The project uses a **Phase-Based Development Model** with 4 distinct phases, each with clear entry/exit criteria.

```
Phase 1: Reconnaissance
  ↓ [Pinning status determined]
Phase 2: Implementation
  ↓ [Approach selected & working PoC]
Phase 3: Integration
  ↓ [Translators working for 1+ LLM]
Phase 4: Production
  ↓ [All criteria met]
Release
```

---

## Phase 1: Reconnaissance (1 Week)

**Goal**: Understand Kiro's architecture and determine certificate pinning status

### Deliverables
- [ ] mitmproxy setup and configuration guide
- [ ] Captured API traces and documented endpoints
- [ ] `API_ENDPOINTS_DISCOVERED.md`
- [ ] `AUTH_FLOW_ANALYSIS.md`
- [ ] `CERTIFICATE_PINNING_ANALYSIS.md`
- [ ] Test Report: Test 1.1, 1.2, 1.3 (from TESTING_PLAN.md)

### Daily Standup Template
```
Date: YYYY-MM-DD

✅ Completed Today:
- [Task 1]
- [Task 2]

🔄 In Progress:
- [Task 3]

⚠️ Blockers:
- [Issue] - Mitigation: [Plan]

📋 Tomorrow's Plan:
- [Task 4]
```

### Work Items

#### Week 1-2: mitmproxy Setup & Traffic Capture

1. **Setup mitmproxy Environment**
   - [ ] Install mitmproxy on test machine
   - [ ] Generate and install CA certificate
   - [ ] Configure system proxy to route through mitmproxy
   - [ ] Verify proxy is transparent (test with browser)
   - [ ] Create `MITMPROXY_SETUP.md` guide

2. **Kiro API Interception Test (Test 1.1)**
   - [ ] Launch Kiro IDE
   - [ ] Trigger API call (chat, completion)
   - [ ] Observe mitmproxy console
   - [ ] Document findings in test report
   - [ ] **Decision Point**: Does traffic appear?
     - YES → Continue to Phase 1 Step 3
     - NO → Likely certificate pinning, skip to Phase 2

3. **API Endpoint Discovery (Test 1.2)**
   - [ ] Map all discovered endpoints
   - [ ] Document request/response schemas
   - [ ] Identify patterns (model names, token types, etc.)
   - [ ] Create `API_ENDPOINTS_DISCOVERED.md`

4. **Authentication Flow Analysis (Test 1.3)**
   - [ ] Capture authentication handshake
   - [ ] Identify token types and formats
   - [ ] Document refresh mechanisms
   - [ ] Locate production auth server endpoints
   - [ ] Create `AUTH_FLOW_ANALYSIS.md`

### Success Criteria for Phase 1 Exit
- [ ] Certificate pinning status determined (YES or NO)
- [ ] At least 3 API endpoints fully documented with schemas
- [ ] Authentication flow understood and documented
- [ ] All test reports completed
- [ ] Team agrees on Phase 2 approach selection

---

## Phase 2: Implementation (2 Weeks)

**Goal**: Implement and validate the chosen interception approach

### Entry Criteria
- Certificate pinning status known from Phase 1
- Approach selected (Frida, Electron unpacking, or DNS spoofing)

### Deliverables
- [ ] Working proof-of-concept for chosen approach
- [ ] Test Report: Test 2.1, 2.2, or 2.3 (depending on approach)
- [ ] `IMPLEMENTATION_NOTES.md` documenting technical decisions
- [ ] Initial source code structure with basic interceptor
- [ ] Setup guide for developers

### Branching Strategy
```
develop → feature/phase2-frida-integration
            ├─ src/interceptor/base.py
            ├─ tools/frida_hooks/certificate_hook.js
            └─ tests/integration/test_frida_hooking.py
```

### Work Items - If Selecting Frida (Most Likely)

#### Week 2-3: Frida Integration

1. **Frida Environment Setup**
   - [ ] Install Frida and Frida tools on Windows
   - [ ] Verify Frida can attach to Kiro process
   - [ ] Create simple test hook that logs function calls
   - [ ] Document setup in `FRIDA_SETUP.md`

2. **Certificate Validation Hook Development (Test 2.1)**
   - [ ] Analyze Kiro's Node.js/Chromium version
   - [ ] Research certificate validation function locations
   - [ ] Create JavaScript hook to intercept validation calls
   - [ ] Test hook against Kiro without breaking it
   - [ ] Document hook in `frida_hooks/certificate_hook.js`
   - [ ] Run Test 2.1 and report findings

3. **Request Interception Hook**
   - [ ] Create hook to intercept HTTPS requests
   - [ ] Log request details (method, URL, headers, body)
   - [ ] Implement hook reinjection to allow modification
   - [ ] Test that modified requests reach intended destination
   - [ ] Document in `frida_hooks/request_logger.js`

4. **Local Proxy Integration**
   - [ ] Create minimal Python HTTPS proxy
   - [ ] Route Frida-captured requests through proxy
   - [ ] Build basic request logging and modification system
   - [ ] Verify round-trip request/response flow
   - [ ] Create `src/interceptor/base.py` abstract class

### Work Items - If Selecting Electron Unpacking

1. **App Extraction & Analysis (Test 2.2)**
   - [ ] Install @electron/asar tool
   - [ ] Extract Kiro's app.asar
   - [ ] Search for certificate pinning code
   - [ ] Analyze pinning implementation (if found)
   - [ ] Document findings in test report
   - [ ] Create `electron_tools/analyze_asar.py`

2. **Modification Development**
   - [ ] Identify functions to modify
   - [ ] Create modification script that patches certificate validation
   - [ ] Test patch doesn't break app
   - [ ] Repack modified app
   - [ ] Document process in `electron_tools/rebuild_asar.py`

3. **Distribution Strategy**
   - [ ] Design auto-update mechanism
   - [ ] Plan how users will install modified app
   - [ ] Document in setup guide

### Phase 2 Success Criteria
- [ ] Chosen approach has working PoC
- [ ] Can intercept at least 1 Kiro API request
- [ ] Test report completed with findings
- [ ] Code follows DEVELOPMENT_GUIDELINES.md
- [ ] Team validates approach is viable before Phase 3

---

## Phase 3: Integration (1.5 Weeks)

**Goal**: Build request/response translators for LLM backends

### Entry Criteria
- Working interception PoC from Phase 2
- API schemas documented from Phase 1

### Deliverables
- [ ] Ollama translator implementation
- [ ] OpenRouter translator implementation
- [ ] Configuration system working
- [ ] Test Report: Test 3.1 (Request/Response Translation)
- [ ] Test Report: Test 3.2 (End-to-End Flow for Ollama)
- [ ] User configuration template

### Translator Development Template

Each translator should follow this interface:

```python
# src/translators/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMTranslator(ABC):
    """Abstract base for LLM API translators"""
    
    @abstractmethod
    def translate_request(self, kiro_request: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Kiro request to target LLM format"""
        pass
    
    @abstractmethod
    def translate_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """Convert target LLM response to Kiro format"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration for this translator"""
        pass
```

### Work Items

#### Week 3-4: Ollama Translator

1. **API Schema Analysis**
   - [ ] Study Ollama API documentation
   - [ ] Understand request/response formats
   - [ ] Identify model name mappings
   - [ ] Document parameter translation (e.g., temperature, tokens)

2. **Translator Implementation (Test 3.1)**
   - [ ] Create `src/translators/ollama.py`
   - [ ] Implement `KiroRequest → OllamaRequest` conversion
   - [ ] Implement `OllamaResponse → KiroResponse` conversion
   - [ ] Handle error cases and edge cases
   - [ ] Write comprehensive unit tests
   - [ ] Achieve 100% test coverage for translator

3. **End-to-End Testing (Test 3.2)**
   - [ ] Start local Ollama instance (with neural-chat model)
   - [ ] Route Kiro request through interceptor → translator → Ollama
   - [ ] Verify response comes back correctly formatted
   - [ ] Test multiple sequential requests
   - [ ] Document any issues in test report

#### Week 4-5: OpenRouter Translator & Configuration

1. **OpenRouter Translator Implementation**
   - [ ] Create `src/translators/openrouter.py`
   - [ ] Implement request/response translation
   - [ ] Support header-based authentication
   - [ ] Unit tests with mocked API responses

2. **Configuration System**
   - [ ] Design configuration file format (TOML or JSON)
   - [ ] Implement config loader with validation
   - [ ] Support multiple profiles (ollama, openrouter, local, etc.)
   - [ ] Environment variable override support

3. **Example Configuration**
   ```toml
   [active]
   backend = "ollama"
   
   [backends.ollama]
   endpoint = "http://localhost:11434"
   model_mapping = {
       "gpt-4" = "neural-chat:latest",
       "gpt-3.5" = "mistral:latest"
   }
   
   [backends.openrouter]
   api_key = "${OPENROUTER_API_KEY}"
   model_mapping = {
       "gpt-4" = "openai/gpt-4",
       "gpt-3.5" = "openai/gpt-3.5-turbo"
   }
   ```

### Phase 3 Success Criteria
- [ ] Ollama translator working end-to-end
- [ ] OpenRouter translator implemented
- [ ] Configuration system flexible and user-friendly
- [ ] All translators have >90% test coverage
- [ ] Test reports show successful request/response translation
- [ ] Can demonstrate Kiro IDE → Ollama flow working

---

## Phase 4: Production & Release (1.5 Weeks)

**Goal**: Polish, document, test thoroughly, and prepare for release

### Entry Criteria
- All Phase 3 deliverables complete
- Translators working for ≥2 LLM backends
- Code passes style and quality checks

### Deliverables
- [ ] Complete source code with documentation
- [ ] SETUP_GUIDE.md for all operating systems
- [ ] TROUBLESHOOTING.md for common issues
- [ ] ARCHITECTURE.md explaining system design
- [ ] Test Report: Test 4.1 (Latency Benchmarking)
- [ ] Test Report: Test 4.2 (Stability & Error Recovery)
- [ ] Configuration examples for each LLM provider
- [ ] Version bump and release notes
- [ ] PyPI package (if applicable)

### Work Items

#### Week 5-6: Testing & Reliability

1. **Latency Benchmarking (Test 4.1)**
   - [ ] Run 50+ requests through each component
   - [ ] Measure per-stage latencies
   - [ ] Identify bottlenecks
   - [ ] Document in test report
   - [ ] Ensure < 200ms overhead (p95)

2. **Stability Testing (Test 4.2)**
   - [ ] Force various failure scenarios
   - [ ] Verify graceful degradation
   - [ ] Test error messages and recovery
   - [ ] Load testing with rapid requests
   - [ ] Document findings and fixes

3. **Edge Case Testing**
   - [ ] Very large prompts (truncation)
   - [ ] Special characters and encoding
   - [ ] Token limit boundary cases
   - [ ] Network interruptions
   - [ ] Token expiration during request

#### Week 6-7: Documentation & Release

1. **User Documentation**
   - [ ] Write SETUP_GUIDE.md with step-by-step instructions
   - [ ] Include screenshots for key steps
   - [ ] Document for Windows (primary target)
   - [ ] Include Linux/macOS variants
   - [ ] Create troubleshooting guide for common issues

2. **Developer Documentation**
   - [ ] Document system architecture
   - [ ] Explain each component's role
   - [ ] Include sequence diagrams for request flow
   - [ ] Document how to add new LLM backends
   - [ ] Create contributing guide

3. **Code Finalization**
   - [ ] Code review of all components
   - [ ] Final style/quality check
   - [ ] Update docstrings and comments
   - [ ] Bump version (semantic versioning)
   - [ ] Create release notes

4. **Release Preparation**
   - [ ] Tag release in git: `git tag v0.1.0`
   - [ ] Build distribution packages
   - [ ] Test installation in clean environment
   - [ ] Create release on GitHub
   - [ ] Document installation methods

### Phase 4 Success Criteria
- [ ] All code passes review and quality checks
- [ ] Test coverage > 80% overall
- [ ] No critical issues in stability testing
- [ ] Complete user and developer documentation
- [ ] Release packaged and ready for users
- [ ] Latency targets met
- [ ] Can demonstrate full flow with multiple backends

---

## Daily Workflow Template

### Morning Standup (15 min)
```
What did I accomplish yesterday?
- [Task 1]
- [Task 2]

What am I working on today?
- [Task 3]
- [Task 4]

Any blockers or help needed?
- [Blocker]: [Mitigation plan]
```

### Development Session (4 hours)
1. **Code**: Implement assigned work item (60-90 min)
2. **Test**: Write/run tests for code (30-60 min)
3. **Review**: Self-review code quality (15 min)
4. **Commit**: Create meaningful git commits (10 min)

### Testing Session (2 hours)
1. **Manual Testing**: Run test cases from TESTING_PLAN.md
2. **Documentation**: Update relevant documentation files
3. **Test Report**: Record findings and issues

### End of Day
- [ ] Commit all code changes
- [ ] Update status in tracking system
- [ ] Document blockers for next standup
- [ ] Plan next day's priorities

---

## Work Item Tracking

### Using GitHub Issues

Each work item becomes a GitHub issue with structure:

```markdown
# [Phase X] - [Work Item Title]

**Type**: Feature/Bug/Investigation
**Assigned To**: [Developer]
**Phase**: [Current Phase]
**Status**: Not Started / In Progress / Review / Done

## Description
[What needs to be done]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Testing
[How to verify completion]

## Related
- Depends on: [Issue #]
- Related to: [Issue #]
```

### Issue Labels
- `phase1-reconnaissance`
- `phase2-implementation`
- `phase3-integration`
- `phase4-production`
- `blocker`
- `bug`
- `documentation`
- `testing`
- `priority-high`

---

## Code Review Process

### Before Submitting PR
1. Self-review code against DEVELOPMENT_GUIDELINES.md
2. Run tests: `pytest`
3. Check style: `black . && flake8 src/`
4. Verify docstrings exist and are accurate
5. Check for hardcoded secrets or paths

### Pull Request Template
```markdown
# [Phase X] - [Feature/Fix Description]

## Changes
- [Change 1]
- [Change 2]

## Testing
- [How tested]
- [Tests added]
- [Coverage %]

## Related Issues
Closes #[Issue Number]

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No secrets or sensitive data
- [ ] Reviewed against DEVELOPMENT_GUIDELINES.md
```

### Review Checklist
Reviewer should verify:
- [ ] Code does what PR describes
- [ ] No security issues
- [ ] Tests are comprehensive
- [ ] Documentation is clear
- [ ] Follows style guidelines

---

## Risk Management

### Known Risks & Mitigation Strategies

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Certificate pinning prevents MITM | Phase 1 blocked | HIGH | Test early, have Frida as backup |
| Kiro has obfuscated code | Harder analysis | MEDIUM | Document findings, seek community help |
| API changes between versions | Compatibility issues | MEDIUM | Pin Kiro version in testing, plan updates |
| Frida detection by antivirus | Security concern | LOW | Document workarounds, have Electron backup |
| Request translation too complex | Design rework needed | MEDIUM | Prototype early, validate assumptions |

### Escalation Process
1. **Technical Blockers** → Discuss in team standup
2. **Scope Changes** → Document decision and rationale
3. **Timeline Issues** → Re-estimate and adjust plan
4. **Release Blockers** → Identify workarounds or defer to next phase

---

## Transition Between Phases

### Phase 1 → Phase 2 Decision Meeting
**When**: End of Week 1
**Attendees**: Development team
**Agenda**:
1. Present findings from Phase 1 reconnaissance
2. Certificate pinning status: YES/NO/UNCLEAR
3. Proposed implementation approach
4. Risk assessment and mitigation
5. **Go/No-Go Decision**

### Phase 2 → Phase 3 Transition
**When**: End of Week 3
**Criteria**:
- [ ] Working PoC for interception
- [ ] Can capture real Kiro requests
- [ ] Test 2.1/2.2/2.3 passed
- [ ] Team confidence in approach

### Phase 3 → Phase 4 Transition
**When**: End of Week 4.5
**Criteria**:
- [ ] ≥2 LLM translators implemented
- [ ] End-to-end flow working
- [ ] Code quality checks passing
- [ ] No critical issues remaining

### Phase 4 → Release
**When**: End of Week 7
**Criteria**:
- [ ] All documentation complete
- [ ] Code review approved
- [ ] Test coverage adequate
- [ ] Stability testing passed
- [ ] Release packaged and tested

---

## Communication & Visibility

### Weekly Status Report Template
```
# Week [N] Status Report

## Overall Progress
[Phase X]: [X]% complete

## Completed This Week
- [Task 1]
- [Task 2]

## In Progress
- [Task 3]

## Planned Next Week
- [Task 4]

## Blockers
[Any issues affecting progress]

## Metrics
- Code coverage: [X]%
- Lines of code added: [N]
- Tests added: [N]
```

### Documentation Updates
- [ ] Update README.md with latest status
- [ ] Keep ARCHITECTURE.md synchronized with code
- [ ] Update SETUP_GUIDE.md as process changes
- [ ] Maintain FAQ/Troubleshooting guide

---

## Success Checkpoints

- **Week 1 End**: Kiro's API endpoints documented, certificate pinning status known
- **Week 2 End**: Interception approach selected and working PoC exists
- **Week 3.5 End**: Request/response translation working for Ollama
- **Week 5 End**: Both Ollama and OpenRouter translators complete
- **Week 6 End**: All testing complete, documentation written
- **Week 7 End**: Release ready for users

This workflow ensures steady progress, quality code, and a manageable release schedule.
