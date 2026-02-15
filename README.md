# Kiro-Conduit Documentation

Quick guide to the project documentation:

## Core Documents (Read in This Order)

1. **[GOALS.md](GOALS.md)** - What we're trying to accomplish
   - Project objectives
   - Success criteria
   - Out-of-scope items

2. **[STRATEGY.md](STRATEGY.md)** - How we'll do it
   - Technical approach (Frida primary, Electron fallback)
   - Why certificate pinning means proxy-based approaches won't work
   - Architecture overview
   - Timeline and success criteria

3. **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Execution details
   - Phase-by-phase breakdown with work items
   - Testing procedures for each phase
   - Daily workflow and standup template
   - Work tracking with GitHub issues
   - Risk management and escalation

4. **[DEVELOPMENT_GUIDELINES.md](DEVELOPMENT_GUIDELINES.md)** - Code standards
   - Python style (PEP 8, Black, type hints)
   - Project structure and dependencies
   - Git workflow and commit format
   - Code review process
   - Testing standards
   - Security considerations

## Quick Start

**For Project Managers**: Read GOALS → STRATEGY → PROJECT_PLAN (Phase Overview)

**For Developers**: Read STRATEGY → PROJECT_PLAN (Current Phase) → DEVELOPMENT_GUIDELINES

**For QA/Testers**: Read PROJECT_PLAN (Testing Procedures section)

**For Code Reviewers**: Reference DEVELOPMENT_GUIDELINES during reviews

## Document Structure

```
GOALS.md              - What? (Objectives & success metrics)
STRATEGY.md           - Why? How? (Technical decisions & reasons)
PROJECT_PLAN.md       - When? Who? (Phases, timeline, workflow)
DEVELOPMENT_GUIDELINES.md - How to code? (Standards & practices)
```

## Key Facts

- **Primary Approach**: Frida runtime injection (non-invasive, survives updates)
- **Fallback**: Electron app modification (if Frida doesn't work)
- **Timeline**: 4 weeks (1 week per 3 phases + 1 for release)
- **Supported Backends**: Ollama (local), OpenRouter (cloud), extensible to others
- **Language**: Python + Frida JavaScript hooks

## Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| GOALS.md | ✅ Final | Feb 15, 2026 |
| STRATEGY.md | ✅ Final (Consolidated) | Feb 15, 2026 |
| PROJECT_PLAN.md | ✅ Final (Consolidated) | Feb 15, 2026 |
| DEVELOPMENT_GUIDELINES.md | ✅ Final | Feb 15, 2026 |

## What's Consolidated Away

- **TESTING_PLAN.md** → Phase testing procedures in PROJECT_PLAN.md
- **WORKFLOW.md** → Daily workflow & phases in PROJECT_PLAN.md
- **README_STRATEGY.md** → This README

This consolidation eliminates duplication while keeping all information accessible.
