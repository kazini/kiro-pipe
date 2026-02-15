# Kiro Network Interception Guide

## 🎯 CRUCIAL FINDINGS & TEST RESULTS

### Key Discovery: Kiro uses AWS CodeWhisperer/Amazon Q, NOT AWS Bedrock

**API Endpoints (from kiro-gateway analysis):**
- `https://q.{region}.amazonaws.com` - Main API (ListAvailableModels, generateAssistantResponse)
- `https://prod.{region}.auth.desktop.kiro.dev/refreshToken` - Kiro Desktop Auth
- `https://oidc.{region}.amazonaws.com/token` - AWS SSO OIDC (for kiro-cli)

**Default Region:** `us-east-1` (but your region may differ - see below)

## 🔍 TEST RESULTS & DISCOVERIES

### What We Ran:
1. **Analyzed kiro-gateway code** - Found actual Kiro API endpoints
2. **Created `find_kiro_pids.py`** - Python script to find all Kiro processes
3. **Ran process analysis** - Found 15 Kiro processes running

### Critical Discovery:
**PID 20264** is connecting to AWS infrastructure:
- **Connection**: `18.206.105.168:443`
- **Resolves to**: `ec2-18-206-105-168.compute-1.amazonaws.com`
- **Memory**: 482.4 MB (high - typical for renderer)
- **Type**: Child process (not main process)

**This is likely the renderer process making Kiro API calls!**

## 🌍 REGION CONSIDERATION

**You mentioned you're not on us-east-1 region.** This affects detection:

### Options:
1. **Use VPN to us-east-1** - Ensures you connect to same region as kiro-gateway defaults
2. **Update hook patterns** - Modify scripts to detect your region's endpoints
3. **Test anyway** - The IP `18.206.105.168` is in us-east-1 (Northern Virginia)

**Recommendation**: Use VPN to us-east-1 for consistent results, OR we can update hooks to be region-agnostic.

## 🎯 THE PROBLEM & SOLUTION

### Problem: Wrong Process Attachment
We've been attaching to main Kiro process, but networking happens in **renderer processes**.

### Solution: We Found the Right Process!
**PID 20264** has active AWS connection - this is our target.

### Process Architecture (Based on Findings):
```
Kiro.exe (Main Process, PID: 22168) - NO NETWORKING
├── Renderer Process (PID: 20264) - ✅ HAS AWS CONNECTION
│   └── Connecting to: 18.206.105.168:443 (AWS EC2 in us-east-1)
├── Other Child Processes (13 more) - Various functions
└── GPU Process, Utility Processes, etc.
```

## 🚀 IMMEDIATE ACTION PLAN

### Step 1: Verify PID 20264 is the Right Process

**Run this command FIRST:**
```bash
python frida-scripts/attach.py --hook find_renderer --process 20264
```

**Expected Output:**
- Should show "Found 'window' object - likely RENDERER process!"
- Should confirm browser APIs (fetch, XMLHttpRequest) available

### Step 2: Test Kiro API Hook on PID 20264

**Run this command SECOND:**
```bash
python frida-scripts/attach.py --hook kiro_api_hook --process 20264
```

**What to do while monitoring:**
1. Keep the hook running
2. Use Kiro's AI features (chat, code completion)
3. Watch for `🎯🎯🎯` markers in output

### Step 3: If No Activity, Try Region-Specific Hook

**If you're not on us-east-1 region:**
1. Use VPN to connect to us-east-1 (Northern Virginia)
2. OR we need to update hooks for your region
3. Check your Kiro settings for region information

## 🛠️ ESSENTIAL HOOKS (After Cleanup)

We've cleaned up the workspace - keeping only essential scripts:

### Core Hooks:
```bash
# 1. Kiro-specific API targeting (PRIMARY)
python frida-scripts/attach.py --hook kiro_api_hook --process 20264

# 2. Renderer process verification
python frida-scripts/attach.py --hook find_renderer --process 20264

# 3. Comprehensive network monitoring (fallback)
python frida-scripts/attach.py --hook test_any_network --process 20264

# 4. Renderer-specific browser APIs
python frida-scripts/attach.py --hook renderer_hook --process 20264
```

### Process Analysis Tools:
```bash
# Find all Kiro processes with network connections
python frida-scripts/find_kiro_pids.py

# Analyze process tree
python frida-scripts/attach.py --hook analyze_process_tree --process 20264
```

## 🔬 PROCESS IDENTIFICATION STRATEGY

### We Already Found the Right PID!
**PID 20264** has:
- ✅ Active AWS connection (`18.206.105.168:443`)
- ✅ High memory usage (482.4 MB)
- ✅ Child process (not main)
- ✅ Likely renderer process

### How to Identify Process Communicating with Endpoint:
1. **Already done**: Used `find_kiro_pids.py` to find processes with network connections
2. **Verification needed**: Confirm PID 20264 is making `q.*.amazonaws.com` calls
3. **Alternative**: If wrong, find which process resolves DNS for `q.{region}.amazonaws.com`

### Region-Specific Detection:
Since you're not on us-east-1:
1. **Option A**: Use VPN to us-east-1 (recommended for testing)
2. **Option B**: We need to:
   - Find your Kiro region
   - Update hook patterns to match
   - Test with region-specific endpoints

## 🎯 ESSENTIAL HOOK SCRIPTS (After Cleanup)

### 1. `kiro_api_hook.js` (PRIMARY)
- **Purpose**: Specifically targets Kiro's AWS CodeWhisperer endpoints
- **Targets**: `q.*.amazonaws.com`, `prod.*.auth.desktop.kiro.dev`
- **Key Feature**: Region-agnostic pattern matching (`q.*.amazonaws.com`)
- **Test Command**: `python attach.py --hook kiro_api_hook --process 20264`

### 2. `find_renderer.js` (VERIFICATION)
- **Purpose**: Verify if process is a renderer
- **Checks**: `window` object, browser APIs, process type
- **Key Feature**: Determines if we're in right process for networking
- **Test Command**: `python attach.py --hook find_renderer --process 20264`

### 3. `test_any_network.js` (COMPREHENSIVE)
- **Purpose**: Catch ALL network activity (42+ Windows API hooks)
- **Targets**: Everything - WinHTTP, WinINET, sockets, DNS, SSL
- **Key Feature**: Will catch any networking, regardless of API used
- **Test Command**: `python attach.py --hook test_any_network --process 20264`

### 4. `renderer_hook.js` (BROWSER APIS)
- **Purpose**: Target browser APIs in renderer processes
- **Targets**: `XMLHttpRequest`, `fetch`, `NSURLSession`, `WebSocket`
- **Key Feature**: Specifically for Chromium renderer processes
- **Test Command**: `python attach.py --hook renderer_hook --process 20264`

## 📊 EXPECTED OUTPUT

### If PID 20264 is Correct & You're on us-east-1:
```
🎯🎯🎯 [KIRO API] POST https://q.us-east-1.amazonaws.com/ListAvailableModels
   📍 Type: Kiro API (ListAvailableModels, generateAssistantResponse)
   🔍 Pattern: q.*.amazonaws.com
```

### If PID 20264 is Correct & You're on Different Region:
```
🎯🎯🎯 [KIRO API] POST https://q.eu-central-1.amazonaws.com/ListAvailableModels
   📍 Type: Kiro API (ListAvailableModels, generateAssistantResponse)  
   🔍 Pattern: q.*.amazonaws.com
```

### If We Need to Find Your Region:
1. Check Kiro settings or configuration files
2. Look for region in:
   - `~/.config/kiro/config.json`
   - `%APPDATA%\Kiro\config.json`
   - Environment variables
3. Or use VPN to us-east-1 for testing

## 🚨 TROUBLESHOOTING & REGION ISSUES

### If No Network Activity on PID 20264:
1. **Region mismatch**: You're not on us-east-1
   - **Solution**: Use VPN to us-east-1 (Northern Virginia)
   - **Alternative**: We update hooks for your region

2. **Wrong process**: PID 20264 might not be the renderer
   - **Solution**: Run `python frida-scripts/attach.py --hook find_renderer --process 20264`
   - **Check**: Does it show "Found 'window' object"?

3. **No API calls**: Kiro not making requests
   - **Solution**: Use AI features while monitoring (chat, code completion)

### Region Detection Strategy:
Since you're not on us-east-1, we need to:
1. **Find your Kiro region** (check config files)
2. **Update hook patterns** to match your region
3. **OR use VPN** to us-east-1 for consistent testing

### Quick Region Check:
```bash
# Check if any Kiro process is making AWS calls
python frida-scripts/attach.py --hook test_any_network --process 20264
# Look for any amazonaws.com connections
```

## 🚀 NEXT STEPS (PRIORITIZED)

### IMMEDIATE ACTION:
1. **Verify PID 20264 is renderer**:
   ```bash
   python frida-scripts/attach.py --hook find_renderer --process 20264
   ```

2. **Test Kiro API hook**:
   ```bash
   python frida-scripts/attach.py --hook kiro_api_hook --process 20264
   ```

### IF NO ACTIVITY (Region Issue):
1. **Use VPN to us-east-1** (Northern Virginia) - RECOMMENDED
2. **OR we need to**:
   - Find your Kiro region
   - Update `kiro_api_hook.js` for your region
   - Test with region-specific patterns

### REGION DISCOVERY:
Check these for region info:
- Kiro settings UI
- `%APPDATA%\Kiro\config.json`
- `~/.config/kiro/config.json`
- Environment variables: `KIRO_REGION`, `AWS_REGION`

### FALLBACK STRATEGY:
If PID 20264 is wrong, use:
```bash
# Find ALL processes with network activity
python frida-scripts/find_kiro_pids.py

# Test each candidate
python frida-scripts/attach.py --hook test_any_network --process <PID>
```

## 📁 ESSENTIAL FILES (After Cleanup)

### Core Scripts:
- `frida-scripts/kiro_api_hook.js` - PRIMARY: Targets Kiro AWS endpoints
- `frida-scripts/find_renderer.js` - VERIFICATION: Checks renderer process
- `frida-scripts/test_any_network.js` - COMPREHENSIVE: 42+ API hooks
- `frida-scripts/renderer_hook.js` - BROWSER APIS: Renderer-specific
- `frida-scripts/attach.py` - MAIN: Updated with essential hooks only
- `frida-scripts/find_kiro_pids.py` - ANALYSIS: Finds processes with network

### Support Files:
- `frida-scripts/analyze_process_tree.js` - Process tree analysis
- `frida-scripts/requirements.txt` - Python dependencies
- `frida-scripts/README.md` - Original documentation

### Reference:
- `_reference_kiro-gateway-main/` - Source of endpoint discovery
- `KIRO_NETWORK_INTERCEPTION_GUIDE.md` - This updated guide

## ⚡ QUICK START COMMANDS

### Step 1: Verify PID 20264
```bash
python frida-scripts/attach.py --hook find_renderer --process 20264
```

### Step 2: Test Kiro API Hook
```bash
python frida-scripts/attach.py --hook kiro_api_hook --process 20264
```

### Step 3: If No Activity (Region Issue)
```bash
# Option A: Use VPN to us-east-1, then retry Step 2
# Option B: Find your region and update hooks
# Option C: Try comprehensive monitoring
python frida-scripts/attach.py --hook test_any_network --process 20264
```

## 🎯 CRITICAL NOTES

1. **Region Issue**: You're not on us-east-1 - this affects detection
2. **VPN Recommended**: Use VPN to us-east-1 (Northern Virginia) for testing
3. **PID 20264**: Has AWS connection - prime candidate
4. **Clean Workspace**: Removed 10+ old scripts, keeping only essentials
5. **Use AI Features**: Keep Kiro open and use chat/code completion while monitoring

## 🔄 REGION ADAPTATION NEEDED

If you can't use VPN to us-east-1, we need to:
1. Discover your Kiro region
2. Update `kiro_api_hook.js` patterns
3. Test with `q.{YOUR_REGION}.amazonaws.com`

**Tell me your region or use VPN to us-east-1, and we'll proceed with testing PID 20264!**