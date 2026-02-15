/**
 * Intercept and Redirect Kiro API - Full request/response capture
 * 
 * Goals:
 * 1. Intercept all Kiro API requests
 * 2. Capture request data (headers, body, method)
 * 3. Check for certificate pinning
 * 4. Bypass certificate pinning if present
 * 5. Optionally redirect to our own endpoint
 */

console.log("[*] Kiro API Interceptor - Full Request/Response Capture");
console.log("[*] Goal: Intercept, analyze, and redirect Kiro API calls");

// Configuration
const CONFIG = {
    // Target endpoints
    targetEndpoints: [
        'q.us-east-1.amazonaws.com',
        'q.eu-central-1.amazonaws.com',
        'q.ap-southeast-1.amazonaws.com',
        'amazonaws.com',
        'kiro.dev'
    ],
    
    // Redirect configuration (set to null to just capture, not redirect)
    redirectTo: null, // e.g., 'http://localhost:8000'
    
    // Certificate pinning bypass
    bypassCertPinning: true,
    
    // Logging
    logRequestBody: true,
    logResponseBody: true,
    maxBodyLength: 5000 // Max bytes to log
};

// State
let state = {
    startTime: Date.now(),
    capturedRequests: [],
    capturedResponses: [],
    pinnedCertsDetected: false,
    bypassAttempted: false,
    bypassSuccessful: false
};

// Utility: Check if URL matches target endpoints
function isTargetEndpoint(url) {
    if (!url) return false;
    
    for (const endpoint of CONFIG.targetEndpoints) {
        if (url.includes(endpoint)) {
            return true;
        }
    }
    return false;
}

// Utility: Extract region from URL
function extractRegion(url) {
    const match = url.match(/q\.([a-z]{2}-[a-z]+-\d+)\.amazonaws\.com/i);
    return match ? match[1] : 'unknown';
}

// Phase 1: Certificate Pinning Bypass
console.log("\n[PHASE 1] Certificate Pinning Bypass...");

if (CONFIG.bypassCertPinning) {
    try {
        // Hook SSL/TLS certificate verification functions
        const certFunctions = [
            'CertVerifyCertificateChainPolicy',
            'CertGetCertificateChain',
            'CertVerifyRevocation',
            'SSLSetSessionOption',
            'SSLHandshake'
        ];
        
        let bypassedCount = 0;
        
        for (const funcName of certFunctions) {
            try {
                const funcAddr = Module.getExportByName(null, funcName);
                if (funcAddr) {
                    Interceptor.attach(funcAddr, {
                        onEnter: function(args) {
                            // Log that we're seeing cert verification
                            state.pinnedCertsDetected = true;
                        },
                        onLeave: function(retval) {
                            // Force success (bypass pinning)
                            if (funcName.includes('Verify') || funcName.includes('Chain')) {
                                retval.replace(0); // Return success
                                state.bypassAttempted = true;
                                state.bypassSuccessful = true;
                            }
                        }
                    });
                    bypassedCount++;
                }
            } catch (e) {
                // Function not found
            }
        }
        
        console.log(`  ✓ Hooked ${bypassedCount} certificate verification functions`);
        
    } catch (e) {
        console.log(`  ✗ Certificate bypass failed: ${e.message}`);
    }
} else {
    console.log("  ⚠️ Certificate pinning bypass disabled");
}

// Phase 2: Request Interception
console.log("\n[PHASE 2] Request Interception...");

// Use the same approach as kiro_api_hook.js - try multiple APIs
const winApis = [
    'WinHttpOpenRequest', 'WinHttpSendRequest', 'WinHttpConnect',
    'WinHttpReceiveResponse', 'WinHttpReadData', 'WinHttpWriteData',
    'HttpOpenRequestA', 'HttpOpenRequestW', 'HttpSendRequestA', 'HttpSendRequestW',
    'InternetOpenUrlA', 'InternetOpenUrlW', 'InternetReadFile', 'InternetWriteFile'
];

let hooksInstalled = 0;

for (const funcName of winApis) {
    try {
        const funcAddr = Module.getExportByName(null, funcName);
        if (funcAddr) {
            Interceptor.attach(funcAddr, {
                onEnter: function(args) {
                    try {
                        let info = '';
                        
                        // WinHttpSendRequest - captures request
                        if (funcName === 'WinHttpSendRequest') {
                            this.hRequest = args[0];
                            this.lpszHeaders = args[1];
                            this.dwHeadersLength = args[2].toInt32();
                            this.lpOptional = args[3];
                            this.dwOptionalLength = args[4].toInt32();
                            
                            // Capture headers
                            let headers = '';
                            if (!this.lpszHeaders.isNull() && this.dwHeadersLength > 0) {
                                headers = this.lpszHeaders.readUtf16String(this.dwHeadersLength);
                            }
                            
                            // Capture body
                            let body = '';
                            if (!this.lpOptional.isNull() && this.dwOptionalLength > 0) {
                                const bodyBytes = this.lpOptional.readByteArray(Math.min(this.dwOptionalLength, CONFIG.maxBodyLength));
                                body = arrayBufferToString(bodyBytes);
                            }
                            
                            // Check if this is a Kiro API request
                            if (headers.includes('amazonaws.com') || headers.includes('kiro.dev') || body.includes('conversationId')) {
                                console.log(`\n🔍 [REQUEST INTERCEPTED - ${funcName}]`);
                                console.log(`   Headers (${this.dwHeadersLength} bytes):`);
                                console.log(`   ${headers.substring(0, 500)}`);
                                
                                if (CONFIG.logRequestBody && body) {
                                    console.log(`   Body (${this.dwOptionalLength} bytes):`);
                                    console.log(`   ${body.substring(0, 500)}`);
                                }
                                
                                // Store request
                                state.capturedRequests.push({
                                    timestamp: Date.now(),
                                    function: funcName,
                                    headers: headers,
                                    body: body,
                                    bodyLength: this.dwOptionalLength
                                });
                            }
                        }
                        
                        // WinHttpReadData - captures response
                        else if (funcName === 'WinHttpReadData') {
                            this.hRequest = args[0];
                            this.lpBuffer = args[1];
                            this.dwNumberOfBytesToRead = args[2].toInt32();
                            this.lpdwNumberOfBytesRead = args[3];
                        }
                        
                        // Other functions - just log
                        else {
                            // Try to extract URL or other info
                            if (funcName.includes('OpenRequest') || funcName.includes('Connect')) {
                                const urlPtr = args[2];
                                if (!urlPtr.isNull()) {
                                    const url = urlPtr.readUtf8String() || urlPtr.readUtf16String() || '';
                                    if (url && isTargetEndpoint(url)) {
                                        console.log(`\n📡 [${funcName}] ${url}`);
                                    }
                                }
                            }
                        }
                    } catch (e) {
                        // Silently fail
                    }
                },
                onLeave: function(retval) {
                    try {
                        // WinHttpReadData - capture response data
                        if (funcName === 'WinHttpReadData' && !retval.isNull() && retval.toInt32() !== 0) {
                            const bytesRead = this.lpdwNumberOfBytesRead.readU32();
                            
                            if (bytesRead > 0 && !this.lpBuffer.isNull()) {
                                const responseData = this.lpBuffer.readByteArray(Math.min(bytesRead, CONFIG.maxBodyLength));
                                const responseStr = arrayBufferToString(responseData);
                                
                                // Check if this looks like a Kiro API response
                                if (responseStr.includes('conversationId') || 
                                    responseStr.includes('message') ||
                                    responseStr.includes('content') ||
                                    responseStr.includes('error') ||
                                    responseStr.includes('modelId')) {
                                    
                                    console.log(`\n📥 [RESPONSE INTERCEPTED - ${funcName}]`);
                                    console.log(`   Size: ${bytesRead} bytes`);
                                    
                                    if (CONFIG.logResponseBody) {
                                        console.log(`   Data:`);
                                        console.log(`   ${responseStr.substring(0, 500)}`);
                                    }
                                    
                                    // Store response
                                    state.capturedResponses.push({
                                        timestamp: Date.now(),
                                        function: funcName,
                                        data: responseStr,
                                        size: bytesRead
                                    });
                                }
                            }
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

console.log(`  ✓ Installed ${hooksInstalled} Windows API hooks`);

// Phase 3: URL Redirection (if configured)
console.log("\n[PHASE 3] URL Redirection...");

if (CONFIG.redirectTo) {
    console.log(`  ✓ Redirect enabled: ${CONFIG.redirectTo}`);
    
    try {
        const WinHttpConnect = Module.getExportByName(null, 'WinHttpConnect');
        if (WinHttpConnect) {
            Interceptor.attach(WinHttpConnect, {
                onEnter: function(args) {
                    const serverName = args[1].readUtf16String();
                    
                    if (isTargetEndpoint(serverName)) {
                        console.log(`\n🔀 [REDIRECT] Original: ${serverName}`);
                        
                        // Parse redirect URL
                        const redirectUrl = new URL(CONFIG.redirectTo);
                        const newHost = redirectUrl.hostname;
                        const newPort = redirectUrl.port || (redirectUrl.protocol === 'https:' ? 443 : 80);
                        
                        console.log(`   New: ${newHost}:${newPort}`);
                        
                        // Replace hostname
                        args[1] = Memory.allocUtf16String(newHost);
                        args[2] = ptr(newPort);
                        
                        console.log(`   ✓ Redirected to ${newHost}:${newPort}`);
                    }
                }
            });
            
            console.log("  ✓ Hooked WinHttpConnect for URL redirection");
        }
    } catch (e) {
        console.log(`  ✗ Redirection setup failed: ${e.message}`);
    }
} else {
    console.log("  ⚠️ Redirection disabled (capture only mode)");
}

// Utility: Convert ArrayBuffer to string
function arrayBufferToString(buffer) {
    try {
        const uint8Array = new Uint8Array(buffer);
        let str = '';
        
        for (let i = 0; i < uint8Array.length; i++) {
            const byte = uint8Array[i];
            if (byte >= 32 && byte <= 126) {
                str += String.fromCharCode(byte);
            } else if (byte === 10 || byte === 13) {
                str += '\n';
            } else {
                str += '.';
            }
        }
        
        return str;
    } catch (e) {
        return '[Error converting buffer to string]';
    }
}

// Summary
console.log("\n" + "=".repeat(70));
console.log("[KIRO API INTERCEPTOR - READY]");
console.log("=".repeat(70));
console.log(`Certificate pinning bypass: ${CONFIG.bypassCertPinning ? 'ENABLED' : 'DISABLED'}`);
console.log(`URL redirection: ${CONFIG.redirectTo ? CONFIG.redirectTo : 'DISABLED (capture only)'}`);
console.log(`Request body logging: ${CONFIG.logRequestBody ? 'ENABLED' : 'DISABLED'}`);
console.log(`Response body logging: ${CONFIG.logResponseBody ? 'ENABLED' : 'DISABLED'}`);
console.log(`\n[INSTRUCTIONS]:`);
console.log(`1. Use Kiro's AI features (chat, code completion)`);
console.log(`2. Watch for 🔍 [REQUEST INTERCEPTED] markers`);
console.log(`3. Watch for 📥 [RESPONSE INTERCEPTED] markers`);
console.log(`4. Check for 🔐 certificate pinning indicators`);
console.log(`5. Captured data will be logged above`);

// Status dashboard
setInterval(function() {
    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    
    console.log(`\n` + "=".repeat(70));
    console.log(`[INTERCEPTOR STATUS] ${elapsed}s elapsed`);
    console.log("=".repeat(70));
    console.log(`Captured requests: ${state.capturedRequests.length}`);
    console.log(`Captured responses: ${state.capturedResponses.length}`);
    console.log(`Certificate pinning detected: ${state.pinnedCertsDetected ? 'YES' : 'NO'}`);
    console.log(`Bypass attempted: ${state.bypassAttempted ? 'YES' : 'NO'}`);
    console.log(`Bypass successful: ${state.bypassSuccessful ? 'YES' : 'NO'}`);
    
    if (state.capturedRequests.length > 0) {
        console.log(`\n✅ Intercepting Kiro API traffic!`);
        console.log(`   Last request: ${new Date(state.capturedRequests[state.capturedRequests.length - 1].timestamp).toLocaleTimeString()}`);
    } else {
        console.log(`\n⏳ Waiting for Kiro API calls...`);
        console.log(`   Make sure you're using AI features`);
    }
}, 15000);

console.log("\n[✓] Interceptor loaded successfully");
console.log("[!] Monitoring for Kiro API traffic...");

send({
    type: 'send',
    payload: 'SUCCESS: Kiro API Interceptor loaded - capturing requests/responses'
});