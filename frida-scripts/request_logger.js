/**
 * Request Logger Hook
 * ===================
 * 
 * Purpose: Intercept and log all HTTPS requests to kiro.dev
 * 
 * Captures:
 * - Request method and URL
 * - Request headers
 * - Request body (if JSON)
 * - Response headers
 * - Response body (if JSON)
 */

console.log("[*] Request Logger Hook Loading...");

let requestCount = 0;

// Hook at the ClientRequest level
try {
    const http = require('http');
    const https = require('https');
    
    function setupRequestHook(httpModule, protocol) {
        const originalRequest = httpModule.request;
        
        httpModule.request = function(options, callback) {
            requestCount++;
            const reqId = requestCount;
            
            // Normalize options
            if (typeof options === 'string') {
                options = new URL(options);
            }
            
            const hostname = options.hostname || options.host || 'unknown';
            const path = options.path || options.pathname || '/';
            const method = options.method || 'GET';
            
            // Only log kiro.dev requests
            if (hostname.includes('kiro.dev') || hostname.includes('desktop')) {
                const timestamp = new Date().toISOString();
                const logPrefix = `[${protocol.toUpperCase()}-${reqId}]`;
                
                console.log(`\n${logPrefix} ${timestamp} - ${method} https://${hostname}${path}`);
                
                // Log request headers
                if (options.headers) {
                    console.log(`${logPrefix} Headers:`, JSON.stringify(options.headers, null, 2));
                }
                
                // Store original callback to intercept response
                const originalCallback = callback;
                const wrappedCallback = function(response) {
                    // Log response status
                    console.log(`${logPrefix} Response: ${response.statusCode} ${response.statusMessage}`);
                    console.log(`${logPrefix} Response Headers:`, JSON.stringify(response.headers, null, 2));
                    
                    // Intercept response data
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
                                    try {
                                        const parsed = JSON.parse(responseBody);
                                        console.log(`${logPrefix} Response Body:`, JSON.stringify(parsed, null, 2));
                                    } catch (e) {
                                        console.log(`${logPrefix} Response Body: ${responseBody.substring(0, 500)}`);
                                    }
                                }
                                return listener.call(this);
                            });
                        }
                        return originalOnce.call(this, event, listener);
                    };
                    
                    return originalCallback.call(this, response);
                };
                
                // Make the request
                const req = originalRequest.call(this, options, wrappedCallback);
                
                // Intercept request write to log body
                const originalWrite = req.write;
                let writeCount = 0;
                
                req.write = function(chunk, encoding, callback) {
                    writeCount++;
                    if (chunk && chunk.length > 0) {
                        const chunkStr = chunk.toString();
                        try {
                            const parsed = JSON.parse(chunkStr);
                            console.log(`${logPrefix} Request Body:`, JSON.stringify(parsed, null, 2));
                        } catch (e) {
                            if (chunkStr.length > 500) {
                                console.log(`${logPrefix} Request Body: ${chunkStr.substring(0, 500)}...`);
                            } else {
                                console.log(`${logPrefix} Request Body:`, chunkStr);
                            }
                        }
                    }
                    
                    return originalWrite.call(this, chunk, encoding, callback);
                };
                
                return req;
            } else {
                // Non-kiro request, pass through unchanged
                return originalRequest.apply(this, arguments);
            }
        };
        
        console.log(`[✓] Hooked ${protocol.toUpperCase()} requests`);
    }
    
    setupRequestHook(https, 'https');
    setupRequestHook(http, 'http');
    
} catch (e) {
    console.log("[ERROR] Failed to setup request hook:", e.message);
    console.log("[ERROR] Stack:", e.stack);
}

// Alternative: Hook at socket write level for more granular control
try {
    const net = require('net');
    const originalSocket = net.Socket.prototype;
    const originalWrite = originalSocket.write;
    
    let socketCount = 0;
    
    net.Socket.prototype.write = function(data, encoding, callback) {
        // Try to detect TLS/HTTPS traffic
        if (data && data.length > 0) {
            // TLS records start with content type bytes (0x16 = handshake, 0x17 = application data)
            const firstByte = data[0];
            
            if (firstByte === 0x16 || firstByte === 0x17) {
                socketCount++;
                const isMaybeKiro = this.remoteAddress || this.bytesWritten;
                
                // Log every 100th TLS write to avoid spam
                if (socketCount % 100 === 0) {
                    console.log(`[TLS-Socket-${socketCount}] TLS record written (${data.length} bytes)`);
                }
            }
        }
        
        return originalWrite.call(this, data, encoding, callback);
    };
    
    console.log("[✓] TLS socket write interception installed");
    
} catch (e) {
    console.log("[TLS-Socket] Failed:", e.message);
}

console.log("[✓] Request Logger Hook loaded successfully");
console.log("[!] Now logging all HTTPS requests to kiro.dev");

send({
    type: 'send',
    payload: 'SUCCESS: Request logger hook active - monitoring kiro.dev requests'
});
