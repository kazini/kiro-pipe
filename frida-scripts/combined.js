/**
 * Combined Frida Hook
 * ==================
 * 
 * This script combines all three hooks:
 * 1. Certificate Bypass
 * 2. Request Logging
 * 3. Request Redirection
 * 
 * Use this for full interception capability
 */

console.log("\n╔════════════════════════════════════════════════════════════╗");
console.log("║         KIRO FRIDA INTERCEPTION - COMBINED HOOKS          ║");
console.log("╚════════════════════════════════════════════════════════════╝\n");

// ============================================================================
// PART 1: CERTIFICATE VALIDATION BYPASS
// ============================================================================

console.log("[*] Loading Certificate Bypass Hook...");

try {
    const Module = require('module');
    const originalRequire = Module.prototype.require;
    
    Module.prototype.require = function(id) {
        const module = originalRequire.apply(this, arguments);
        
        if (id === 'tls' && module.createSecureContext) {
            const originalCreateSecureContext = module.createSecureContext;
            
            module.createSecureContext = function(options) {
                const modifiedOptions = Object.assign({}, options, {
                    rejectUnauthorized: false
                });
                
                const context = originalCreateSecureContext.call(this, modifiedOptions);
                return context;
            };
        }
        
        return module;
    };
} catch (e) {
    console.log("[WARNING] Standard require hook failed:", e.message);
}

try {
    const nodeHttps = require('https');
    const nodeTls = require('tls');
    
    if (nodeTls && nodeTls.TLSSocket) {
        const OriginalTLSSocket = nodeTls.TLSSocket;
        
        nodeTls.TLSSocket = new Proxy(OriginalTLSSocket, {
            construct: function(target, args, newTarget) {
                const socket = new target(...args);
                
                if (socket._handle && socket._handle.verifyError) {
                    socket._handle.verifyError = null;
                }
                
                return socket;
            }
        });
    }
} catch (e) {
    console.log("[WARNING] TLSSocket proxy failed:", e.message);
}

console.log("[✓] Certificate Bypass Loaded\n");

// ============================================================================
// PART 2: REQUEST LOGGING
// ============================================================================

console.log("[*] Loading Request Logger Hook...");

let requestCount = 0;

try {
    const https = require('https');
    const originalRequest = https.request;
    
    https.request = function(options, callback) {
        requestCount++;
        const reqId = requestCount;
        
        if (typeof options === 'string') {
            options = new URL(options);
        }
        
        const hostname = options.hostname || options.host || 'unknown';
        const path = options.path || options.pathname || '/';
        const method = options.method || 'GET';
        
        if (hostname.includes('kiro.dev') || hostname.includes('desktop')) {
            const timestamp = new Date().toISOString();
            
            console.log(`\n[API-${reqId}] ${method} https://${hostname}${path} [${timestamp}]`);
            
            if (options.headers) {
                const safeHeaders = Object.assign({}, options.headers);
                if (safeHeaders['authorization']) {
                    safeHeaders['authorization'] = '***REDACTED***';
                }
                console.log(`[API-${reqId}] Headers:`, 
                    Object.entries(safeHeaders)
                        .map(([k,v]) => `${k}: ${v}`)
                        .join(', ')
                );
            }
            
            const originalCallback = callback;
            const wrappedCallback = function(response) {
                console.log(`[API-${reqId}] Response: ${response.statusCode} ${response.statusMessage}`);
                
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
                                    JSON.parse(responseBody);
                                    console.log(`[API-${reqId}] Response Body: ${responseBody.substring(0, 200)}`);
                                } catch (e) {
                                    console.log(`[API-${reqId}] Response Body: ${responseBody.substring(0, 200)}`);
                                }
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
                    try {
                        const parsed = JSON.parse(chunk.toString());
                        console.log(`[API-${reqId}] Request Body: ${JSON.stringify(parsed).substring(0, 300)}`);
                    } catch (e) {
                        console.log(`[API-${reqId}] Request Body: ${chunk.toString().substring(0, 200)}`);
                    }
                }
                
                return originalWrite.call(this, chunk, encoding, callback);
            };
            
            return req;
        } else {
            return originalRequest.apply(this, arguments);
        }
    };
} catch (e) {
    console.log("[WARNING] Request logging failed:", e.message);
}

console.log("[✓] Request Logger Loaded\n");

// ============================================================================
// PART 3: REQUEST REDIRECTION
// ============================================================================

console.log("[*] Loading Request Redirect Hook...");

const REDIRECT_PORT = 8888;
const REDIRECT_HOST = 'localhost';

const ENDPOINT_MAPPING = {
    'prod.us-east-1.auth.desktop.kiro.dev': REDIRECT_HOST,
    'app.kiro.dev': REDIRECT_HOST,
    'prod.download.desktop.kiro.dev': REDIRECT_HOST,
    'gamma.us-east-1.telemetry.desktop.kiro.dev': REDIRECT_HOST
};

let redirectCount = 0;

try {
    const https = require('https');
    const originalRequest = https.request;
    
    // We already patched https.request, so create new reference
    const httpsRequestPatched = https.request;
} catch (e) {
    console.log("[WARNING] Could not access https module:", e.message);
}

try {
    // Hook at TLS connection level
    const tls = require('tls');
    const originalConnect = tls.connect;
    
    tls.connect = function(options, callback) {
        if (typeof options === 'number') {
            options = { port: options };
        }
        
        const originalHost = options.host || options.hostname || 'localhost';
        const originalPort = options.port || 443;
        
        if (Object.keys(ENDPOINT_MAPPING).includes(originalHost)) {
            redirectCount++;
            console.log(`\n[REDIR-${redirectCount}] ${originalHost}:${originalPort} → localhost:${REDIRECT_PORT}`);
            
            options.host = REDIRECT_HOST;
            options.hostname = REDIRECT_HOST;
            options.port = REDIRECT_PORT;
            options.rejectUnauthorized = false;
        }
        
        return originalConnect.call(this, options, callback);
    };
} catch (e) {
    console.log("[WARNING] TLS redirect failed:", e.message);
}

try {
    // Also hook at DNS level
    const dns = require('dns');
    const originalLookup = dns.lookup;
    
    dns.lookup = function(hostname, options, callback) {
        if (typeof options === 'function') {
            callback = options;
            options = {};
        }
        
        if (Object.keys(ENDPOINT_MAPPING).includes(hostname)) {
            console.log(`[DNS] ${hostname} → 127.0.0.1`);
            if (callback) {
                return callback(null, '127.0.0.1', 4);
            }
        }
        
        if (callback) {
            return originalLookup.call(this, hostname, options, callback);
        } else {
            return originalLookup.call(this, hostname, options);
        }
    };
} catch (e) {
    console.log("[WARNING] DNS redirect failed:", e.message);
}

console.log("[✓] Request Redirection Loaded\n");

// ============================================================================
// STATUS REPORT
// ============================================================================

console.log("╔════════════════════════════════════════════════════════════╗");
console.log("║              HOOKS ACTIVE AND MONITORING                   ║");
console.log("╠════════════════════════════════════════════════════════════╣");
console.log("║ ✓ Certificate validation disabled                         ║");
console.log("║ ✓ HTTPS requests being logged                             ║");
console.log("║ ✓ kiro.dev traffic redirected to localhost:8888           ║");
console.log("╠════════════════════════════════════════════════════════════╣");
console.log("║ Mapped Endpoints:                                          ║");
console.log("║  • prod.us-east-1.auth.desktop.kiro.dev                   ║");
console.log("║  • app.kiro.dev                                            ║");
console.log("║  • prod.download.desktop.kiro.dev                         ║");
console.log("║  • gamma.us-east-1.telemetry.desktop.kiro.dev             ║");
console.log("╚════════════════════════════════════════════════════════════╝\n");

send({
    type: 'send',
    payload: '✓ SUCCESS: All Kiro interception hooks loaded and active'
});
