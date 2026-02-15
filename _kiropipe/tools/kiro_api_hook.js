/**
 * Kiro API Hook - Specifically target Kiro's AWS CodeWhisperer endpoints
 * Based on kiro-gateway analysis
 */

console.log("[*] Kiro API Hook Loading...");
console.log("[*] Targeting specific Kiro/AWS endpoints discovered from kiro-gateway");

// Key endpoints from kiro-gateway analysis
const KIRO_ENDPOINTS = {
    // API endpoints (AWS CodeWhisperer/Amazon Q) - REGION AGNOSTIC
    'q\\.([a-z]{2}-[a-z]+-\\d+)\\.amazonaws\\.com': 'Kiro API (ListAvailableModels, generateAssistantResponse)',
    'q\\..*\\.amazonaws\\.com': 'Kiro API (any region)',
    
    // Authentication endpoints
    'prod\\.([a-z]{2}-[a-z]+-\\d+)\\.auth\\.desktop\\.kiro\\.dev': 'Kiro Desktop Auth',
    'oidc\\.([a-z]{2}-[a-z]+-\\d+)\\.amazonaws\\.com': 'AWS SSO OIDC',
    
    // Generic patterns (catch all)
    'amazonaws\\.com': 'AWS services',
    'kiro\\.dev': 'Kiro services',
    'aws\\.com': 'AWS domain',
    
    // Specific regions we know about
    'q\\.us-east-1\\.amazonaws\\.com': 'Kiro API (us-east-1)',
    'q\\.eu-central-1\\.amazonaws\\.com': 'Kiro API (eu-central-1)',
    'q\\.ap-southeast-1\\.amazonaws\\.com': 'Kiro API (ap-southeast-1)'
};

// Track activity
let activity = {
    startTime: Date.now(),
    totalCalls: 0,
    byEndpoint: {},
    requests: [],
    capturedData: []
};

// Function to check if URL matches Kiro endpoints
function isKiroEndpoint(url) {
    if (!url) return false;
    
    for (const pattern in KIRO_ENDPOINTS) {
        try {
            const regex = new RegExp(pattern, 'i'); // Case insensitive
            if (regex.test(url)) {
                const match = url.match(regex);
                return {
                    pattern: pattern,
                    description: KIRO_ENDPOINTS[pattern],
                    match: match[0],
                    region: match[1] || 'unknown' // Extract region if pattern has capture group
                };
            }
        } catch (e) {
            // Invalid regex pattern, skip
        }
    }
    
    return false;
}

// Function to log Kiro activity
function logKiroActivity(type, url, method, details = '', data = null) {
    activity.totalCalls++;
    
    const endpointInfo = isKiroEndpoint(url);
    if (endpointInfo) {
        activity.byEndpoint[endpointInfo.pattern] = (activity.byEndpoint[endpointInfo.pattern] || 0) + 1;
        
        console.log(`\n🎯🎯🎯 [KIRO API] ${method} ${url}`);
        console.log(`   📍 Type: ${endpointInfo.description}`);
        console.log(`   🔍 Pattern: ${endpointInfo.pattern}`);
        if (endpointInfo.region && endpointInfo.region !== 'unknown') {
            console.log(`   🌍 Region: ${endpointInfo.region}`);
        }
        if (details) console.log(`   📝 ${details}`);
        
        // Store request
        const request = {
            type: type,
            url: url,
            method: method,
            endpoint: endpointInfo,
            timestamp: Date.now(),
            details: details
        };
        
        activity.requests.push(request);
        
        // If we have data, try to capture it
        if (data) {
            console.log(`   📦 Data captured (${data.length} bytes)`);
            
            // Try to parse as JSON if it looks like JSON
            if (data.length < 10000) { // Limit size
                try {
                    const text = data.toString();
                    if (text.includes('{') || text.includes('[')) {
                        console.log(`   📄 Data preview: ${text.substring(0, 200)}...`);
                        
                        activity.capturedData.push({
                            request: request,
                            data: text,
                            length: data.length
                        });
                    }
                } catch (e) {
                    // Not text data
                }
            }
        }
        
        return true;
    }
    
    return false;
}

// Function to log regular activity
function logActivity(type, url, method, details = '') {
    if (!logKiroActivity(type, url, method, details)) {
        // Not a Kiro endpoint, log normally
        console.log(`\n[${type.toUpperCase()}] ${method} ${url}`);
        if (details) console.log(`   ${details}`);
    }
}

console.log("\n[ENDPOINTS WE'RE LOOKING FOR]:");
for (const [pattern, description] of Object.entries(KIRO_ENDPOINTS)) {
    console.log(`  ${pattern} → ${description}`);
}

// Phase 1: Hook Windows networking APIs (for main/renderer processes)
console.log("\n[PHASE 1] Hooking Windows networking APIs...");

// Key Windows API functions to hook
const keyApis = [
    'WinHttpOpenRequest', 'WinHttpSendRequest', 'WinHttpConnect',
    'HttpOpenRequestA', 'HttpOpenRequestW', 'HttpSendRequestA', 'HttpSendRequestW',
    'InternetOpenUrlA', 'InternetOpenUrlW'
];

let hooksInstalled = 0;

for (const funcName of keyApis) {
    try {
        const funcAddr = Module.getGlobalExportByName(funcName);
        if (funcAddr) {
            Interceptor.attach(funcAddr, {
                onEnter: function(args) {
                    try {
                        let url = '';
                        let method = 'GET';
                        
                        if (funcName.includes('WinHttpOpenRequest') || funcName.includes('HttpOpenRequest')) {
                            // WinHttpOpenRequest(hConnect, pwszVerb, pwszObjectName, ...)
                            // HttpOpenRequest(hConnect, lpszVerb, lpszObjectName, ...)
                            const verbPtr = args[1];
                            const objectPtr = args[2];
                            
                            if (!verbPtr.isNull()) {
                                const isWide = funcName.endsWith('W');
                                method = isWide ? verbPtr.readUtf16String() : verbPtr.readUtf8String();
                            }
                            
                            if (!objectPtr.isNull()) {
                                const isWide = funcName.endsWith('W');
                                const objectName = isWide ? objectPtr.readUtf16String() : objectPtr.readUtf8String();
                                
                                // Object name might be path only, not full URL
                                // We need to combine with hostname from WinHttpConnect/InternetConnect
                                url = objectName;
                            }
                        } else if (funcName.includes('InternetOpenUrl')) {
                            // InternetOpenUrl(hInternet, lpszUrl, ...)
                            const urlPtr = args[1];
                            if (!urlPtr.isNull()) {
                                const isWide = funcName.endsWith('W');
                                url = isWide ? urlPtr.readUtf16String() : urlPtr.readUtf8String();
                            }
                        }
                        
                        if (url) {
                            logActivity('winapi', url, method, funcName);
                        }
                    } catch (e) {
                        // Silently fail
                    }
                }
            });
            
            hooksInstalled++;
        }
    } catch (e) {
        // Function not found
    }
}

console.log(`  Installed ${hooksInstalled} Windows API hooks`);

// Phase 2: Try to hook browser APIs if in renderer process
console.log("\n[PHASE 2] Checking for renderer process (browser APIs)...");

try {
    if (typeof window !== 'undefined') {
        console.log("  ✅ In renderer process - hooking browser APIs");
        
        // Hook XMLHttpRequest
        if (typeof XMLHttpRequest !== 'undefined') {
            const OriginalXHR = window.XMLHttpRequest;
            window.XMLHttpRequest = function() {
                const xhr = new OriginalXHR();
                
                let requestUrl = '';
                let requestMethod = '';
                
                const originalOpen = xhr.open;
                xhr.open = function(method, url) {
                    requestMethod = method;
                    requestUrl = url;
                    logActivity('xhr', url, method, 'XMLHttpRequest.open()');
                    return originalOpen.apply(this, arguments);
                };
                
                const originalSend = xhr.send;
                xhr.send = function(data) {
                    logKiroActivity('xhr-send', requestUrl, requestMethod, 'Sending request', data);
                    return originalSend.apply(this, arguments);
                };
                
                return xhr;
            };
            
            console.log("    ✓ XMLHttpRequest hooked");
        }
        
        // Hook fetch
        if (typeof fetch !== 'undefined') {
            const originalFetch = window.fetch;
            window.fetch = function(input, init) {
                const url = typeof input === 'string' ? input : input.url;
                const method = (init && init.method) || 'GET';
                
                logActivity('fetch', url, method, 'fetch()');
                
                // Capture request body if available
                let requestData = null;
                if (init && init.body) {
                    requestData = init.body;
                }
                
                logKiroActivity('fetch', url, method, 'fetch() with body', requestData);
                
                return originalFetch.apply(this, arguments);
            };
            
            console.log("    ✓ fetch() hooked");
        }
    } else {
        console.log("  ⚠️ Not in renderer process (no window object)");
    }
} catch (e) {
    console.log(`  ✗ Browser API hooking failed: ${e.message}`);
}

// Phase 3: Hook socket-level communication (catch everything)
console.log("\n[PHASE 3] Hooking socket-level communication...");

try {
    // Hook connect() to see all outgoing connections
    const connectAddr = Module.getGlobalExportByName('connect');
    if (connectAddr) {
        Interceptor.attach(connectAddr, {
            onEnter: function(args) {
                try {
                    const sockaddr = args[1];
                    const addrlen = args[2].toInt32();
                    
                    if (addrlen >= 16) {
                        const port = sockaddr.add(2).readU16();
                        const ipBytes = sockaddr.add(4).readU32();
                        const ip = [
                            (ipBytes >> 0) & 0xFF,
                            (ipBytes >> 8) & 0xFF,
                            (ipBytes >> 16) & 0xFF,
                            (ipBytes >> 24) & 0xFF
                        ].join('.');
                        
                        // Only log if it's HTTPS (443) or HTTP (80)
                        if (port === 443 || port === 80) {
                            console.log(`\n[CONNECT] to ${ip}:${port} (${port === 443 ? 'HTTPS' : 'HTTP'})`);
                            
                            // Try to resolve IP to hostname (we'll do this later)
                            // For now, just note the connection
                        }
                    }
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        console.log("    ✓ connect() hooked");
    }
} catch (e) {
    console.log(`  ✗ Socket hooking failed: ${e.message}`);
}

// Summary
console.log("\n" + "=".repeat(70));
console.log("[KIRO API HOOK - READY]");
console.log("=".repeat(70));
console.log(`Specifically targeting Kiro's AWS CodeWhisperer endpoints`);
console.log(`\n[KEY INSIGHTS FROM KIRO-GATEWAY]:`);
console.log(`• Kiro uses AWS CodeWhisperer/Amazon Q, NOT AWS Bedrock`);
console.log(`• API endpoint: https://q.{region}.amazonaws.com`);
console.log(`• Auth: https://prod.{region}.auth.desktop.kiro.dev/refreshToken`);
console.log(`• Default region: us-east-1`);
console.log(`\n[INSTRUCTIONS]:`);
console.log(`1. Use Kiro's AI features (chat, code completion)`);
console.log(`2. Watch for 🎯🎯🎯 markers (Kiro API calls)`);
console.log(`3. Look for q.*.amazonaws.com endpoints`);

// Dashboard
setInterval(function() {
    const elapsed = Math.floor((Date.now() - activity.startTime) / 1000);
    
    console.log(`\n` + "=".repeat(70));
    console.log(`[KIRO API DASHBOARD] ${elapsed}s elapsed`);
    console.log("=".repeat(70));
    console.log(`Total calls: ${activity.totalCalls}`);
    
    if (Object.keys(activity.byEndpoint).length > 0) {
        console.log(`\nKiro endpoints detected:`);
        for (const [pattern, count] of Object.entries(activity.byEndpoint)) {
            console.log(`  ${pattern}: ${count} calls`);
        }
    }
    
    if (activity.requests.length > 0) {
        console.log(`\nRecent Kiro API calls:`);
        const recent = activity.requests.slice(-5).reverse();
        for (const req of recent) {
            const timeAgo = Math.floor((Date.now() - req.timestamp) / 1000);
            console.log(`  [${timeAgo}s ago] ${req.method} ${req.url}`);
            console.log(`     ${req.endpoint.description}`);
        }
    }
    
    if (activity.capturedData.length > 0) {
        console.log(`\n📦 Captured data samples: ${activity.capturedData.length}`);
        for (const data of activity.capturedData.slice(-2)) {
            console.log(`  ${data.request.method} ${data.request.url}`);
            console.log(`    ${data.length} bytes`);
        }
    }
    
    if (activity.totalCalls === 0) {
        console.log(`\n❌ NO NETWORK ACTIVITY DETECTED`);
        console.log(`Possible issues:`);
        console.log(`  1. Wrong process (networking in different process)`);
        console.log(`  2. No Kiro API calls being made`);
        console.log(`  3. Different networking stack`);
    } else if (Object.keys(activity.byEndpoint).length === 0) {
        console.log(`\n⚠️ Network activity but NO KIRO ENDPOINTS`);
        console.log(`We're seeing calls but not to Kiro/AWS endpoints`);
    } else {
        console.log(`\n✅ KIRO API ACTIVITY DETECTED!`);
        console.log(`Check output above for specific calls`);
    }
    
}, 15000);

console.log("\n[✓] Kiro API hook loaded successfully");
console.log("[!] Monitoring for Kiro API calls for 60+ seconds");

// Keep alive
setTimeout(function() {
    console.log("\n[INFO] Still monitoring for Kiro API calls...");
}, 60000);

send({
    type: 'send',
    payload: 'SUCCESS: Kiro API hook loaded - targeting q.*.amazonaws.com endpoints'
});