/**
 * Debug Logger - Logs ALL HTTPS requests (not filtered)
 * ====================================================
 * 
 * Purpose: Identify what endpoints Kiro actually calls
 * This version logs EVERYTHING to help debug
 */

console.log("[*] Debug Logger Hook Loading...");
console.log("[*] This will log ALL HTTPS requests (not just kiro.dev)");

let requestCount = 0;

try {
    const https = require('https');
    const originalRequest = https.request;
    
    https.request = function(options, callback) {
        requestCount++;
        const reqId = requestCount;
        
        // Normalize options
        if (typeof options === 'string') {
            options = new URL(options);
        }
        
        const hostname = options.hostname || options.host || 'unknown';
        const path = options.path || options.pathname || '/';
        const method = options.method || 'GET';
        
        // LOG EVERYTHING (no filter)
        const timestamp = new Date().toISOString();
        const logPrefix = `[REQ-${reqId}]`;
        
        console.log(`\n${logPrefix} ${timestamp}`);
        console.log(`${logPrefix} METHOD: ${method}`);
        console.log(`${logPrefix} HOST: ${hostname}`);
        console.log(`${logPrefix} PATH: ${path}`);
        console.log(`${logPrefix} PORT: ${options.port || 443}`);
        
        // Log all headers
        if (options.headers) {
            console.log(`${logPrefix} HEADERS:`);
            Object.entries(options.headers).forEach(([key, value]) => {
                const safeValue = key.toLowerCase().includes('auth') ? '***REDACTED***' : value;
                console.log(`${logPrefix}   ${key}: ${safeValue}`);
            });
        }
        
        // Intercept request write to log body
        const originalCallback = callback;
        const wrappedCallback = function(response) {
            console.log(`${logPrefix} RESPONSE: ${response.statusCode} ${response.statusMessage}`);
            
            let responseBody = '';
            const originalOn = response.on;
            
            response.on = function(event, listener) {
                if (event === 'data') {
                    return originalOn.call(this, event, function(chunk) {
                        responseBody += chunk.toString();
                        return listener.call(this, chunk);
                    });
                }
                return originalOn.call(this, event, listener);
            };
            
            const originalOnce = response.once;
            response.once = function(event, listener) {
                if (event === 'end') {
                    return originalOnce.call(this, event, function() {
                        if (responseBody) {
                            console.log(`${logPrefix} BODY: ${responseBody.substring(0, 300)}`);
                        }
                        return listener.call(this);
                    });
                }
                return originalOnce.call(this, event, listener);
            };
            
            return originalCallback.call(this, response);
        };
        
        const req = originalRequest.call(this, options, wrappedCallback);
        
        const originalWrite = req.write;
        req.write = function(chunk, encoding, callback) {
            if (chunk && chunk.length > 0) {
                const chunkStr = chunk.toString();
                console.log(`${logPrefix} REQUEST BODY: ${chunkStr.substring(0, 300)}`);
            }
            return originalWrite.call(this, chunk, encoding, callback);
        };
        
        return req;
        
    };
    
    console.log("[✓] HTTPS request logging installed (ALL REQUESTS)");
    
} catch (e) {
    console.log("[ERROR] Failed to setup request hook:", e.message);
}

console.log("[✓] Debug Logger Hook loaded successfully");
console.log("[!] Now logging ALL HTTPS requests");
console.log("[!] Look for any requests appearing in console\n");

send({
    type: 'send',
    payload: 'SUCCESS: Debug logger active - monitoring ALL HTTPS requests'
});
