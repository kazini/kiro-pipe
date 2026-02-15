# Kiro-Conduit: Project Steering Documentation

## Overview

Kiro-Conduit is an ambitious project to reroute Kiro IDE's traffic to alternative LLM backends. This folder contains comprehensive steering documents that define the project's goals, strategy, testing approach, development standards, and workflow.

## Strategic Documents Summary

### 📋 [GOALS.md](./GOALS.md)
**What we're trying to accomplish**

Defines:
- Primary objective: Enable traffic rerouting to custom LLM backends
- Success criteria for core functionality
- Secondary goals (multiple providers, performance, logging)
- What's out-of-scope (license bypasses, UI changes)
- Success metrics for validation

**Start here if**: You want to understand the project's vision and success criteria

---

### 🎯 [STRATEGY.md](./STRATEGY.md)
**How we'll tackle this challenge**

Evaluates 5 different technical approaches:
1. **MITM with mitmproxy + Certificate Installation** - Proxy-based, non-invasive
2. **Reverse Proxy + DNS Spoofing** - DNS redirection to local proxy
3. **Electron App Unpacking** - Modify and repack the Kiro executable
4. **Frida Runtime Hooking** - Inject code into running process at runtime
5. **Hybrid Approach (RECOMMENDED)** - Reconnaissance first, then select best approach

For each approach, documents:
- Pros and cons
- Certificate pinning risk assessment
- Viability rating
- Development effort estimate
- Fallback strategies

**Recommendation**: Start with **Hybrid Approach - Phase 1 (Reconnaissance)** using mitmproxy to determine certificate pinning status, then decide path forward.

**Start here if**: You want to understand the technical landscape and our selected strategy

---

### 🧪 [TESTING_PLAN.md](./TESTING_PLAN.md)
**How we'll verify each approach works**

Comprehensive testing strategy across 4 phases:

**Phase 1: Reconnaissance Testing**
- Test 1.1: mitmproxy baseline interception
- Test 1.2: API endpoint discovery
- Test 1.3: Authentication flow analysis

**Phase 2: Approach Viability Testing**
- Test 2.1: Frida runtime hooking PoC
- Test 2.2: Electron app unpacking PoC
- Test 2.3: DNS spoofing + local proxy PoC

**Phase 3: Integration Testing**
- Test 3.1: Request/response translation
- Test 3.2: End-to-end flow testing

**Phase 4: Performance & Reliability Testing**
- Test 4.1: Latency benchmarking
- Test 4.2: Stability & error recovery

Each test includes:
- Objective and prerequisites
- Step-by-step procedure
- Expected outcomes
- Pass criteria
- Failure handling
- Output/documentation

**Start here if**: You want to understand how we'll validate our work at each step

---

### 📐 [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md)
**The rules we follow while coding**

Establishes standards for:
- **Code Quality**: PEP 8, Black formatter, Type hints, Google-style docstrings
- **Project Structure**: Organized directory layout for source, tests, tools, docs
- **Dependencies**: Managed requirements.txt with version strategy
- **Git Workflow**: Git Flow branching model with conventional commit messages
- **Code Review**: Review checklist and PR standards
- **Error Handling**: Custom exception hierarchy
- **Logging**: Structured logging with sensitive data protection
- **Testing**: Unit test templates, coverage requirements
- **Security**: Credential protection, HTTPS handling, input validation
- **Performance**: Monitoring, optimization priorities, caching strategy
- **Deployment**: Release process, version compatibility

**Start here if**: You're going to write code and need to know the standards

---

### 🔄 [WORKFLOW.md](./WORKFLOW.md)
**How we organize our day-to-day work**

Provides:
- **Phase-Based Development Model**: 4 phases with clear exit criteria
- **Phase 1 Reconnaissance**: 1 week mitmproxy testing
- **Phase 2 Implementation**: 2 weeks of core development  
- **Phase 3 Integration**: 1.5 weeks building translators
- **Phase 4 Production**: 1.5 weeks of hardening & release
- **Daily Workflow**: Standups, development sessions, testing cycles
- **Work Item Tracking**: Using GitHub Issues and labels
- **Code Review Process**: Before submitting, during review
- **Risk Management**: Known risks and mitigation strategies
- **Phase Transitions**: Decision meetings and go/no-go criteria
- **Communication**: Weekly status reports and visibility

**Start here if**: You're starting a development session or managing the project

---

## Quick Start Guide

### For Project Managers/Leads
1. Read [GOALS.md](./GOALS.md) - understand objectives
2. Read [STRATEGY.md](./STRATEGY.md) - understand approach
3. Use [WORKFLOW.md](./WORKFLOW.md) - manage execution

### For Developers Starting a New Task
1. Review [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md) - code standards
2. Check [TESTING_PLAN.md](./TESTING_PLAN.md) - what tests apply to your work
3. Follow [WORKFLOW.md](./WORKFLOW.md) - daily process

### For Quality Assurance
1. Study [TESTING_PLAN.md](./TESTING_PLAN.md) - all test procedures
2. Learn [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md) - code quality criteria
3. Use [WORKFLOW.md](./WORKFLOW.md) - phase transitions and exit criteria

### For Code Reviewers
1. Reference [DEVELOPMENT_GUIDELINES.md](./DEVELOPMENT_GUIDELINES.md) - code standards
2. Use code review checklist in [WORKFLOW.md](./WORKFLOW.md)
3. Verify test coverage from [TESTING_PLAN.md](./TESTING_PLAN.md)

---

## Document Hierarchy & Dependencies

```
GOALS.md (What)
├─ STRATEGY.md (How - at 30,000 ft)
│  ├─ TESTING_PLAN.md (How - tactical, per phase)
│  │  └─ DEVELOPMENT_GUIDELINES.md (How - per commit)
│  └─ WORKFLOW.md (How - day-to-day)
```

**Read in this order for complete understanding**:
1. GOALS.md - Define the target
2. STRATEGY.md - Choose the path
3. TESTING_PLAN.md - Validate the path
4. DEVELOPMENT_GUIDELINES.md - Write quality code
5. WORKFLOW.md - Execute systematically

---

## Key Decisions Made

### 1. Technical Approach: Hybrid Strategy Starting with Phase 1 Reconnaissance
**Rationale**: Minimize risk by understanding Kiro's architecture first before committing to a specific implementation approach. Start with mitmproxy to determine if certificate pinning is implemented, then select Frida or Electron unpacking accordingly.

**Decision Point**: End of Week 1 after certificate pinning status is known

### 2. Language & Ecosystem: Python + Frida
**Rationale**: 
- Python: Cross-platform, rich ecosystem for networking/proxying, easy to prototype
- Frida: Proven for runtime hooking, no app repackaging needed, JavaScript-based hooks

**Alternative if needed**: Electron app modification (if Frida doesn't work)

### 3. Supported LLM Backends (Priority Order)
**Rationale**: Start with open-source/self-hosted options, expand to cloud APIs
1. **Ollama** (local, no API key) - Phase 3 primary
2. **OpenRouter** (cloud, supports many models) - Phase 3 secondary
3. **Anthropic** (direct API) - Phase 4 if time permits

### 4. Testing: Comprehensive Phase-Based Approach
**Rationale**: De-risk by validating assumptions at each phase with specific tests

### 5. Development Model: Phase-Based with Clear Exit Criteria
**Rationale**: Provides checkpoints for decision-making and risk management

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|-----------|
| Certificate pinning determination | Week 1 | Phase 1 exit |
| Interception PoC | Week 2 | Phase 2 exit |
| 1+ LLM translator working | Week 4 | Phase 3 exit |
| 2+ LLM translators working | Week 5 | Phase 4 start |
| Code coverage | >80% | Ongoing |
| API response latency overhead | <200ms p95 | Phase 4 testing |
| Documentation completeness | All guides + API docs | Phase 4 release |

---

## Risk Assessment & Mitigation

### Highest Risk: Certificate Pinning
- **Impact**: Could block MITM approach entirely
- **Probability**: HIGH (modern apps use this)
- **Mitigation**: Test in Week 1 with mitmproxy, have Frida backups ready

### Medium Risk: API Changes Between Kiro Versions
- **Impact**: Translators may break on Kiro updates
- **Probability**: MEDIUM
- **Mitigation**: Pin Kiro version in testing, monitor upstream changes

### Medium Risk: Frida Detection by Antivirus
- **Impact**: Users may have issues with Frida injection
- **Probability**: LOW-MEDIUM
- **Mitigation**: Document workarounds, have Electron unpacking as backup

### Lower Risk: Request Translation Complexity
- **Impact**: More translation logic required
- **Probability**: MEDIUM
- **Mitigation**: Prototype early with actual request samples

---

## Dependencies & Prerequisites

### Hardware/OS
- Windows 10+ (primary target)
- Linux/macOS support secondary
- 8GB+ RAM for development
- 2GB+ free disk space

### Software Stack
```
Python 3.9+
├─ mitmproxy (traffic interception)
├─ Frida + frida-tools (runtime hooking)
├─ pytest (testing)
├─ black (formatting)
├─ flake8 (linting)
├─ requests (HTTP client)
└─ pydantic (data validation)

Node.js
└─ @electron/asar (Electron app tools)

Kiro IDE (latest stable)

Optional: Ollama (for LLM testing)
```

---

## Document Maintenance

These documents are **living documents** that should evolve as the project progresses:

### Update Triggers
- **Phase transitions**: Update status in WORKFLOW.md
- **Risk discovery**: Add to STRATEGY.md or TESTING_PLAN.md
- **Code standards changes**: Update DEVELOPMENT_GUIDELINES.md
- **Test results**: Document in TESTING_PLAN.md appropriately

### Version Control
- Documents live in project root Git repository
- Changes tracked in git history
- Major updates tagged with phase release (v0.1-phase1, etc.)

---

## How to Use These Documents Effectively

### Sprint Planning
1. Check current phase in WORKFLOW.md
2. Pull work items from TESTING_PLAN.md for current phase
3. Assign work using GitHub Issues (see WORKFLOW.md)
4. Track daily progress in standup notes

### Development Session
1. Pull assigned issue
2. Review relevant section in DEVELOPMENT_GUIDELINES.md
3. Reference test procedure in TESTING_PLAN.md
4. Follow daily workflow in WORKFLOW.md
5. Commit using format from DEVELOPMENT_GUIDELINES.md

### Code Review
1. Check against DEVELOPMENT_GUIDELINES.md code standards
2. Use review checklist from WORKFLOW.md
3. Reference STRATEGY.md for architectural soundness
4. Verify tests per TESTING_PLAN.md

### Phase Exit
1. Verify all items in WORKFLOW.md phase section are complete
2. Run test suite from TESTING_PLAN.md
3. Review documentation updates
4. Hold phase transition meeting (per WORKFLOW.md)
5. Update status files

---

## Next Steps

### Immediate Actions (This Week)
- [ ] Review all 5 steering documents (2-3 hours)
- [ ] Set up development environment (Python, mitmproxy, Kiro IDE)
- [ ] Create GitHub repository for kiro-conduit_development
- [ ] Assign Phase 1 reconnaissance tasks
- [ ] Schedule Phase 1 → Phase 2 decision meeting for end of Week 1

### First Week Deliverables (Phase 1)
- [ ] mitmproxy setup and CA certificate installation
- [ ] API endpoint capture and documentation (`API_ENDPOINTS_DISCOVERED.md`)
- [ ] Authentication flow analysis (`AUTH_FLOW_ANALYSIS.md`)
- [ ] Certificate pinning status determination (`CERTIFICATE_PINNING_ANALYSIS.md`)
- [ ] Phase 1 test reports
- [ ] Go/No-Go decision for Phase 2

---

## Questions & Clarifications

For questions about:
- **Project goals**: See GOALS.md
- **Technical approach**: See STRATEGY.md
- **Testing procedures**: See TESTING_PLAN.md
- **Code standards**: See DEVELOPMENT_GUIDELINES.md
- **Daily workflow**: See WORKFLOW.md
- **This summary**: See this document

---

## Document Checklist

Before proceeding to development, confirm:

- [ ] GOALS.md reviewed - understand project objectives
- [ ] STRATEGY.md reviewed - understand selected approach (Hybrid/Phase 1)
- [ ] TESTING_PLAN.md reviewed - understand how to validate work
- [ ] DEVELOPMENT_GUIDELINES.md reviewed - understand code standards
- [ ] WORKFLOW.md reviewed - understand daily process
- [ ] Development environment set up (Python, mitmproxy)
- [ ] GitHub repository created and configured
- [ ] Phase 1 tasks assigned to developers
- [ ] First standup scheduled

---

**Document Generated**: February 15, 2026  
**Strategic Framework Version**: 1.0  
**Next Review**: End of Phase 1 (Week 1)

This strategic framework provides the foundation for a systematic, well-organized approach to the kiro-conduit project. Success depends on following these guidelines while remaining flexible to adapt based on actual findings during Phase 1 reconnaissance.
