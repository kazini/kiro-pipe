/**
 * Auto Find and Hook Kiro - Dynamic process discovery and hooking
 * 
 * Features:
 * 1. Automatically finds Kiro processes with network activity
 * 2. Works with ANY AWS region (not just us-east-1)
 * 3. Hooks both Windows APIs and browser APIs
 * 4. Real-time process monitoring
 */

console.log("[*] Auto Find and Hook Kiro - Dynamic Process Discovery");
console.log("[*] No hardcoded PID - Works after Kiro restarts");
console.log("[*] Region-agnostic - Works with any AWS region");

// Configuration
const CONFIG = {
    checkInterval: 5000, // Check for processes every 5 seconds
    maxProcesses: 20,    // Maximum Kiro processes to monitor
    targetPatterns: [
        /q\.[a-z]{2}-[a-z]+-\d+\.amazonaws\.com/i,  // Kiro API any region
        /prod\.[a-z]{2}-[a-z]+-\d+\.auth\.desktop\.kiro\.dev/i, // Kiro Auth
        /oidc\.[a-z]{2}-[a-z]+-\d+\.amazonaws\.com/i, // AWS SSO OIDC
        /amazonaws\.com/i,  // Any AWS service
        /kiro\.dev/i        // Kiro services
    ]
};

// State
let state = {
    startTime: Date.now(),
    monitoredProcesses: new Map(), // pid -> process info
    totalHooksInstalled: 0,
    detectedCalls: 0,
    detectedRegions: new Set(),
    lastActivity: null
};

// Utility functions
function log(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
    console.log(`[${timestamp}] ${prefix} ${message}`);
}

function extractRegionFromURL(url) {
    // Extract AWS region from URL patterns
    const regionPatterns = [
        /q\.([a-z]{2}-[a-z]+-\d+)\.amazonaws\.com/i,
        /prod\.([a-z]{2}-[a-z]+-\d+)\.auth\.desktop\.kiro\.dev/i,
        /oidc\.([a-z]{2}-[a-z]+-\d+)\.amazonaws\.com/i
    ];
    
    for (const pattern of regionPatterns) {
        const match = url.match(pattern);
        if (match && match[1]) {
            return match[1];
        }
    }
    
    return 'unknown';
}

// Process discovery
function findKiroProcesses() {
    log("Scanning for Kiro processes...");
    
    try {
        const processes = Process.enumerateProcesses();
        const kiroProcesses = [];
        
        for (const proc of processes) {
            if (proc.name.toLowerCase().includes('kiro')) {
                kiroProcesses.push({
                    pid: proc.pid,
                    name: proc.name,
                    path: proc.path || 'unknown'
                });
            }
        }
        
        log(`Found ${kiroProcesses.length} Kiro process(es)`);
        return kiroProcesses;
    } catch (e) {
        log(`Error finding processes: ${e.message}`, 'error');
        return [];
    }
}

// Check if process is a renderer
function isRendererProcess(pid) {
    try {
        // Try to attach briefly to check for window object
        const session = attach(pid);
        
        // Inject a small script to check for renderer indicators
        const checkScript = `
            try {
                if (typeof window !== 'undefined') {
                    send({ type: 'renderer_check', isRenderer: true });
                } else {
                    send({ type: 'renderer_check', isRenderer: false });
                }
            } catch(e) {
                send({ type: 'renderer_check', error: e.message });
            }
        `;
        
        let isRenderer = false;
        const script = session.createScript(checkScript);
        
        script.message.connect((message) => {
            if (message.payload && message.payload.type === 'renderer_check') {
                isRenderer = message.payload.isRenderer === true;
            }
        });
        
        script.load();
        script.unload();
        session.detach();
        
        return isRenderer;
    } catch (e) {
        // If we can't attach or check, assume not a renderer
        return false;
    }
}

// Install hooks in a process
function installHooksInProcess(pid, processInfo) {
    if (state.monitoredProcesses.has(pid)) {
        log(`PID ${pid} already monitored`, 'info');
        return false;
    }
    
    log(`Installing hooks in PID ${pid} (${processInfo.name})...`);
    
    try {
        const session = attach(pid);
        
        // Hook script that combines multiple strategies
        const hookScript = `
            // Track activity
            let localActivity = {
                startTime: Date.now(),
                calls: 0,
                regions: new Set(),
                endpoints: new Set()
            };
            
            // Pattern matcher
            function isKiroEndpoint(url) {
                if (!url) return false;
                
                const patterns = [
                    /q\\\\.[a-z]{2}-[a-z]+-\\\\d+\\\\.amazonaws\\\\.com/i,
                    /prod\\\\.[a-z]{2}-[a-z]+-\\\\d+\\\\.auth\\\\.desktop\\\\.kiro\\\\.dev/i,
                    /oidc\\\\.[a-z]{2}-[a-z]+-\\\\d+\\\\.amazonaws\\\\.com/i,
                    /amazonaws\\\\.com/i,
                    /kiro\\\\.dev/i
                ];
                
                for (const pattern of patterns) {
                    if (pattern.test(url)) {
                        return true;
                    }
                }
                return false;
            }
            
            // Hook Windows APIs
            const winApis = ['WinHttpOpenRequest', 'WinHttpSendRequest', 'HttpOpenRequestA', 'HttpOpenRequestW'];
            
            for (const apiName of winApis) {
                try {
                    const apiAddr = Module.getExportByName(null, apiName);
                    if (apiAddr) {
                        Interceptor.attach(apiAddr, {
                            onEnter: function(args) {
                                try {
                                    // Try to extract URL
                                    let url = '';
                                    if (apiName.includes('OpenRequest')) {
                                        const urlPtr = args[2];
                                        if (!urlPtr.isNull()) {
                                            url = urlPtr.readUtf8String() || urlPtr.readUtf16String() || '';
                                        }
                                    }
                                    
                                    if (url && isKiroEndpoint(url)) {
                                        send({
                                            type: 'kiro_call',
                                            pid: ${pid},
                                            api: apiName,
                                            url: url,
                                            timestamp: Date.now()
                                        });
                                        
                                        localActivity.calls++;
                                        localActivity.endpoints.add(url);
                                        
                                        // Extract region
                                        const regionMatch = url.match(/q\\\\.([a-z]{2}-[a-z]+-\\\\d+)\\\\.amazonaws\\\\.com/i);
                                        if (regionMatch) {
                                            localActivity.regions.add(regionMatch[1]);
                                        }
                                    }
                                } catch(e) {
                                    // Silently fail
                                }
                            }
                        });
                    }
                } catch(e) {
                    // API not found
                }
            }
            
            // Check if we're in renderer process
            let isRenderer = false;
            try {
                if (typeof window !== 'undefined') {
                    isRenderer = true;
                    
                    // Hook browser APIs
                    if (typeof XMLHttpRequest !== 'undefined') {
                        const OriginalXHR = window.XMLHttpRequest;
                        window.XMLHttpRequest = function() {
                            const xhr = new OriginalXHR();
                            let requestUrl = '';
                            
                            const originalOpen = xhr.open;
                            xhr.open = function(method, url) {
                                requestUrl = url;
                                if (isKiroEndpoint(url)) {
                                    send({
                                        type: 'kiro_call',
                                        pid: ${pid},
                                        api: 'XMLHttpRequest',
                                        url: url,
                                        method: method,
                                        timestamp: Date.now()
                                    });
                                    
                                    localActivity.calls++;
                                    localActivity.endpoints.add(url);
                                }
                                return originalOpen.apply(this, arguments);
                            };
                            
                            return xhr;
                        };
                    }
                    
                    // Hook fetch
                    if (typeof fetch !== 'undefined') {
                        const originalFetch = window.fetch;
                        window.fetch = function(input, init) {
                            const url = typeof input === 'string' ? input : (input.url || '');
                            if (isKiroEndpoint(url)) {
                                send({
                                    type: 'kiro_call',
                                    pid: ${pid},
                                    api: 'fetch',
                                    url: url,
                                    method: (init && init.method) || 'GET',
                                    timestamp: Date.now()
                                });
                                
                                localActivity.calls++;
                                localActivity.endpoints.add(url);
                            }
                            return originalFetch.apply(this, arguments);
                        };
                    }
                }
            } catch(e) {
                // Not a renderer or hooking failed
            }
            
            // Send initial status
            send({
                type: 'hook_status',
                pid: ${pid},
                isRenderer: isRenderer,
                hooksInstalled: winApis.length,
                timestamp: Date.now()
            });
            
            // Periodic status updates
            setInterval(function() {
                send({
                    type: 'activity_update',
                    pid: ${pid},
                    calls: localActivity.calls,
                    regions: Array.from(localActivity.regions),
                    endpoints: Array.from(localActivity.endpoints).slice(0, 5),
                    uptime: Date.now() - localActivity.startTime
                });
            }, 10000);
            
            // Keep alive
            send({ type: 'hook_loaded', pid: ${pid} });
        `;
        
        const script = session.createScript(hookScript);
        
        script.message.connect((message) => {
            handleHookMessage(pid, message);
        });
        
        script.load();
        
        // Store process info
        state.monitoredProcesses.set(pid, {
            session: session,
            script: script,
            info: processInfo,
            hooksInstalled: 0,
            isRenderer: false,
            lastActivity: Date.now(),
            callCount: 0,
            detectedRegions: new Set()
        });
        
        state.totalHooksInstalled++;
        return true;
        
    } catch (e) {
        log(`Failed to install hooks in PID ${pid}: ${e.message}`, 'error');
        return false;
    }
}

// Handle messages from hook scripts
function handleHookMessage(pid, message) {
    const processInfo = state.monitoredProcesses.get(pid);
    if (!processInfo) return;
    
    if (message.type === 'send' && message.payload) {
        const payload = message.payload;
        
        switch (payload.type) {
            case 'hook_loaded':
                log(`Hooks loaded in PID ${pid}`, 'success');
                break;
                
            case 'hook_status':
                processInfo.hooksInstalled = payload.hooksInstalled || 0;
                processInfo.isRenderer = payload.isRenderer || false;
                log(`PID ${pid}: ${payload.hooksInstalled} hooks, ${payload.isRenderer ? 'Renderer' : 'Not renderer'}`);
                break;
                
            case 'kiro_call':
                state.detectedCalls++;
                state.lastActivity = Date.now();
                
                const region = extractRegionFromURL(payload.url);
                if (region !== 'unknown') {
                    state.detectedRegions.add(region);
                    processInfo.detectedRegions.add(region);
                }
                
                console.log(`\n🎯🎯🎯 [KIRO API - PID ${pid}]`);
                console.log(`   ${payload.method || 'REQUEST'} ${payload.url}`);
                console.log(`   API: ${payload.api}`);
                if (region !== 'unknown') {
                    console.log(`   🌍 Region: ${region}`);
                }
                console.log(`   🕒 ${new Date(payload.timestamp).toLocaleTimeString()}`);
                
                processInfo.callCount++;
                processInfo.lastActivity = Date.now();
                break;
                
            case 'activity_update':
                // Periodic update, just log if there's activity
                if (payload.calls > 0) {
                    log(`PID ${pid}: ${payload.calls} calls, regions: ${payload.regions.join(', ') || 'none'}`);
                }
                break;
        }
    }
}

// Main monitoring loop
function startMonitoring() {
    log("Starting Kiro process monitoring...");
    log("Will automatically find and hook Kiro processes with network activity");
    log("Works with any AWS region, no VPN required");
    
    // Initial scan
    scanAndHookProcesses();
    
    // Periodic scanning
    setInterval(() => {
        scanAndHookProcesses();
        printStatus();
    }, CONFIG.checkInterval);
    
    // Status updates
    setInterval(() => {
        printStatus();
    }, 30000);
}

function scanAndHookProcesses() {
    const processes = findKiroProcesses();
    
    for (const proc of processes) {
        if (state.monitoredProcesses.size >= CONFIG.maxProcesses) {
            log(`Reached maximum monitored processes (${CONFIG.maxProcesses})`, 'info');
            break;
        }
        
        if (!state.monitoredProcesses.has(proc.pid)) {
            // Try to install hooks
            installHooksInProcess(proc.pid, proc);
        }
    }
}

function printStatus() {
    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    
    console.log(`\n` + "=".repeat(70));
    console.log(`[AUTO HOOK STATUS] ${elapsed}s elapsed`);
    console.log("=".repeat(70));
    
    console.log(`Monitored processes: ${state.monitoredProcesses.size}`);
    console.log(`Total hooks installed: ${state.totalHooksInstalled}`);
    console.log(`Detected Kiro API calls: ${state.detectedCalls}`);
    
    if (state.detectedRegions.size > 0) {
        console.log(`Detected regions: ${Array.from(state.detectedRegions).join(', ')}`);
    }
    
    if (state.monitoredProcesses.size > 0) {
        console.log(`\nProcess details:`);
        for (const [pid, info] of state.monitoredProcesses) {
            const age = Math.floor((Date.now() - info.lastActivity) / 1000);
            console.log(`  PID ${pid}: ${info.callCount} calls, ${info.isRenderer ? 'Renderer' : 'Main'}, ${age}s since last activity`);
            if (info.detectedRegions.size > 0) {
                console.log(`    Regions: ${Array.from(info.detectedRegions).join(', ')}`);
            }
        }
    }
    
    if (state.detectedCalls === 0) {
        console.log(`\n❌ No Kiro API calls detected yet`);
        console.log(`   Make sure:`);
        console.log(`   1. Kiro is running`);
        console.log(`   2. You're using AI features (chat, code completion)`);
        console.log(`   3. You're connected to internet`);
        console.log(`   4. Wait for next scan (every 5 seconds)`);
    } else {
        console.log(`\n✅ Kiro API activity detected!`);
        console.log(`   Check output above for specific calls`);
    }
    
    console.log(`\n[INSTRUCTIONS]`);
    console.log(`• Keep Kiro open and use AI features`);
    console.log(`• Watch for 🎯🎯🎯 markers above`);
    console.log(`• No VPN required - works with any region`);
    console.log(`• PIDs auto-detected - works after Kiro restarts`);
}

// Cleanup
function cleanup() {
    log("Cleaning up...");
    
    for (const [pid, info] of state.monitoredProcesses) {
        try {
            if (info.script) {
                info.script.unload();
            }
            if (info.session) {
                info.session.detach();
            }
        } catch (e) {
            // Ignore cleanup errors
        }
    }
    
    state.monitoredProcesses.clear();
    log("Cleanup complete");
}

// Start monitoring
startMonitoring();

// Handle termination
Process.setExceptionHandler(function(exception) {
    log(`Frida exception: ${exception}`, 'error');
    return true;
});

// Keep alive
setTimeout(function() {
    log("Auto-hook monitoring active...");
}, 60000);

// Send success message
send({
    type: 'send',
    payload: 'SUCCESS: Auto Find and Hook loaded - dynamically monitoring Kiro processes'
});