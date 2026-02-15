# Phase 1 Quick Start Guide

## 🚀 Getting Started with Frida Interception (Estimated: 10 minutes)

### Step 1: Install Frida
```bash
cd C:\Users\Kazini\Vault\Programas\Coding\my_programming_stuff\AI\projects\open-cli_project\kiro-conduit\frida-scripts

# Install dependencies
pip install -r requirements.txt
```

**Verify installation:**
```bash
frida --version
frida-ps
```

Should show frida version and list of running processes.

---

### Step 2: Launch Kiro Application
Start Kiro normally (click desktop shortcut or run Kiro.exe)

**Make sure Kiro is fully loaded** - you should see the IDE window

---

### Step 3: Run Frida Attachment Script

Open PowerShell in the frida-scripts directory and run:

```bash
# First, list all running processes to verify Kiro is there
python attach.py --list

# You should see something like:
# Kiro.exe                              (PID: 12345)
```

Then inject the hooks:
```bash
# Use combined hooks (all-in-one)
python attach.py --hook combined

# OR individual hooks if you prefer:
# python attach.py --hook cert-only    # Just bypass certificate
# python attach.py --hook logger        # Just log requests
# python attach.py --hook redirect      # Just redirect traffic
```

---

### Step 4: Verify Hooks Are Active

You should see output like:
```
🔧 Frida Kiro Interception Setup
============================================================

[Step 1/4] Finding Kiro process...
✓ Found process: Kiro.exe (PID: 12345)

[Step 2/4] Loading combined hook script...
✓ Loaded hook: combined

[Step 3/4] Attaching to process (PID: 12345)...
✓ Attached successfully

[Step 4/4] Injecting hooks...
[*] Loading Certificate Bypass Hook...
[Windows Certificate Bypass Loaded...
[*] Loading Request Logger Hook...
[✓] Request Logger Loaded
[*] Loading Request Redirect Hook...
[✓] Request Redirection Loaded

============================================================
✓ FRIDA INTERCEPTION ACTIVE
============================================================

Monitoring for API calls...
Press Ctrl+C to stop
```

---

### Step 5: Trigger Kiro API Calls

In the Kiro IDE:
1. Click on **Chat** or **Ask an AI** feature
2. Type a message and press Enter
3. Or use **Generate** feature if available

This will trigger API calls to kiro.dev that Frida will intercept.

---

### Step 6: Monitor Interception Output

You should see:
```
[API-1] POST https://prod.us-east-1.auth.desktop.kiro.dev/authenticate
[API-1] Headers: content-type: application/json, authorization: ***REDACTED***
[API-1] Response: 200 OK
[API-1] Response Body: {"token": "...", ...}

[API-2] POST https://prod.us-east-1.auth.desktop.kiro.dev/completions
[API-2] Request Body: {"messages": [...], "model": "...", "temperature": 0.7}
[REDIR-2] prod.us-east-1.auth.desktop.kiro.dev:443 → localhost:8888
[DNS] prod.us-east-1.auth.desktop.kiro.dev → 127.0.0.1
```

✅ **If you see this, Phase 1 is working!**

---

## 🔍 Expected Behavior

### What Should Happen
1. ✅ Kiro launches normally
2. ✅ Frida attaches without errors
3. ✅ Hooks are loaded and logged
4. ✅ When using Kiro features, you see API calls logged
5. ✅ Requests show redirection to localhost:8888
6. ✅ **Kiro will error** (because localhost:8888 doesn't exist yet)

### Why Kiro Will Error
- The hooks redirect requests to `localhost:8888`
- We haven't built the translation server yet (Phase 2)
- So Kiro gets connection refused
- This is **expected and normal** at this stage

---

## 🐛 Troubleshooting

### Problem: "Cannot find process: Kiro"
**Solution:**
```bash
# Check if Kiro is running
python attach.py --list

# If Kiro isn't there, it's not running. Start it first.
# If it shows with different name, try:
python attach.py --process "Kiro.exe"
```

### Problem: "Failed to attach: Permission Denied"
**Solution:**
- Run PowerShell as Administrator
- Right-click PowerShell → Run as Administrator
- Then run `python attach.py --hook combined`

### Problem: "No API calls appearing"
**Solution:**
1. Make sure you're using Kiro features that call APIs (Chat, Generate)
2. Wait a moment - sometimes there's a delay
3. Check if Kiro is showing errors in its UI
4. Review `combined.js` to see if filtering is too strict

### Problem: "Hooks loaded but requests aren't redirecting"
**Solution:**
1. This is okay - certificate bypass might be working but redirect failing
2. Check if DNS resolution is working
3. Try individual hooks to isolate the issue:
   ```bash
   python attach.py --hook logger    # Just see requests
   python attach.py --hook redirect  # Just test redirect
   ```

---

## 📊 What's Next (Phase 2)

Now that Frida interception is **working**:

1. **Analyze API Format**
   - Study the exact structure of Kiro's API requests and responses
   - Document authentication method
   - Map all endpoints
   
2. **Build Translation Server**
   - Create `localhost:8888` server that listens for Kiro's requests
   - Translate Kiro format → OpenAI/Anthropic format
   - Query alternative LLM
   - Translate response back to Kiro format

3. **Test Integration**
   - Stop getting "connection refused" errors
   - Kiro receives responses from alternative LLM
   - Validate that responses appear correctly in Kiro UI

---

## 📝 Testing Checklist

- [ ] Frida installed and verified (`frida --version`)
- [ ] Kiro is running
- [ ] `python attach.py --list` shows Kiro process
- [ ] `python attach.py --hook combined` attaches successfully
- [ ] Hooks are loaded (see certificate bypass message)
- [ ] Used Kiro Chat/Generate feature
- [ ] API calls appear in console output
- [ ] Requests show redirection to localhost:8888
- [ ] Kiro shows error about connection (expected)

---

## 🎯 Success Metrics

✅ **You'll know Phase 1 is successful when:**
1. Frida attachment shows no errors
2. All four hooks report as loaded
3. Using Kiro features triggers visible API calls
4. You can see the request/response details in console
5. You can see redirection attempts to localhost

This means the foundation is ready for Phase 2!

---

## 💡 Tips

- Keep the Python script running in the background
- Test different Kiro features to see different API endpoints
- Note the exact request formats you see (helpful for Phase 2)
- If you get stuck, check `frida-scripts/README.md` for detailed docs
- The `combined.js` hook has detailed logging built in

---

**Ready? Let's go!** 

```bash
cd frida-scripts
python attach.py --hook combined
```

Press **Ctrl+C** when done.
