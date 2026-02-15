/**
 * Request Redirect Hook
 * ====================
 * 
 * Purpose: Redirect HTTPS requests from kiro.dev to localhost:8888
 * 
 * Behavior:
 * - Intercepts all HTTPS requests to prod.us-east-1.auth.desktop.kiro.dev
 * - Redirects to https://localhost:8888 with path preservation
 * - Preserves headers and authentication
 */

console.log("[*] Request Redirect Hook Loading...");

const REDIRECT_PORT = 8888;
const REDIRECT_HOST = 'localhost';

// Map of kiro endpoints to redirect
const ENDPOINT_MAPPING = {
    'prod.us-east-1.auth.desktop.kiro.dev': REDIRECT_HOST,
    'app.kiro.dev': REDIRECT_HOST,
    'prod.download.desktop.kiro.dev': REDIRECT_HOST,
    'gamma.us-east-1.telemetry.desktop.kiro.dev': REDIRECT_HOST
};

let redirectCount = 0;

// Strategy 1: Hook https.request at the option-normalization stage
try {
    const https = require('https');
    const originalRequest = https.request;
    
    https.request = function(options, callback) {
        redirectCount++;
        const id = redirectCount;
        
        // Normalize options
        if (typeof options === 'string') {
            const url = new URL(options);
            options = {
                hostname: url.hostname,
                port: url.port || 443,
                path: url.pathname + url.search,
                method: 'GET',
                headers: {}
            };
        }
        
        const originalHost = options.hostname || options.host;
        
        // Check if this is a kiro.dev request
        if (originalHost && (originalHost.includes('kiro.dev') || originalHost.includes('desktop'))) {
            console.log(`\n[REDIRECT-${id}] Intercepted: ${options.method || 'GET'} https://${originalHost}${options.path}`);
            console.log(`[REDIRECT-${id}] → Redirecting to https://${REDIRECT_HOST}:${REDIRECT_PORT}${options.path}`);
            
            // Preserve the original hostname in a custom header for the local server
            if (!options.headers) {
                options.headers = {};
            }
            
            options.headers['X-Original-Host'] = originalHost;
            options.headers['X-Forwarded-For'] = '127.0.0.1';
            options.headers['X-Forwarded-Proto'] = 'https';
            
            // Override hostname and port
            options.hostname = REDIRECT_HOST;
            options.host = REDIRECT_HOST;
            options.port = REDIRECT_PORT;
            options.rejectUnauthorized = false;  // Accept any certificate from localhost
            
            console.log(`[REDIRECT-${id}] Headers modified:`, Object.keys(options.headers).join(', '));
        } else {
            console.log(`[REDIRECT-${id}] Non-Kiro request to ${originalHost} - passing through`);
        }
        
        return originalRequest.call(this, options, callback);
    };
    
    console.log("[✓] HTTPS request redirection installed");
    
} catch (e) {
    console.log("[ERROR] HTTPS redirect hook failed:", e.message);
}

// Strategy 2: Hook DNS resolution to redirect at network level
try {
    const dns = require('dns');
    const originalLookup = dns.lookup;
    const originalResolve = dns.resolve;
    const originalResolve4 = dns.resolve4;
    
    // Intercept DNS lookups
    dns.lookup = function(hostname, options, callback) {
        // Handle both (hostname, callback) and (hostname, options, callback) forms
        if (typeof options === 'function') {
            callback = options;
            options = {};
        }
        
        if (Object.keys(ENDPOINT_MAPPING).includes(hostname)) {
            console.log(`[DNS] ${hostname} → localhost (127.0.0.1)`);
            
            // Return localhost IP
            if (callback) {
                return callback(null, '127.0.0.1', 4);
            }
        }
        
        // Non-kiro domain, use original
        if (callback) {
            return originalLookup.call(this, hostname, options, callback);
        } else {
            return originalLookup.call(this, hostname, options);
        }
    };
    
    console.log("[✓] DNS lookup redirection installed");
    
} catch (e) {
    console.log("[DNS] Lookup hook failed:", e.message);
}

// Strategy 3: Hook actual socket connections
try {
    const net = require('net');
    const tls = require('tls');
    const originalConnect = tls.connect;
    
    tls.connect = function(options, callback) {
        // Normalize options
        if (typeof options === 'number') {
            // (port, callback) form
            options = { port: options };
        }
        
        const originalPort = options.port || 443;
        const originalHost = options.host || options.hostname || 'localhost';
        
        if (Object.keys(ENDPOINT_MAPPING).includes(originalHost)) {
            console.log(`[TLS-CONNECT] ${originalHost}:${originalPort} → localhost:${REDIRECT_PORT}`);
            
            options.host = REDIRECT_HOST;
            options.hostname = REDIRECT_HOST;
            options.port = REDIRECT_PORT;
            options.rejectUnauthorized = false;
            
            // Preserve original in callback context
            const originalCallbackWrapper = callback;
            if (originalCallbackWrapper) {
                callback = function() {
                    console.log(`[TLS-CONNECT] Connected to localhost:${REDIRECT_PORT} (was ${originalHost}:${originalPort})`);
                    return originalCallbackWrapper.apply(this, arguments);
                };
            }
        }
        
        return originalConnect.call(this, options, callback);
    };
    
    console.log("[✓] TLS connection redirection installed");
    
} catch (e) {
    console.log("[TLS] Connect hook failed:", e.message);
}

// Strategy 4: HTTP remapping if needed
try {
    const http = require('http');
    const originalRequest = http.request;
    
    http.request = function(options, callback) {
        if (typeof options === 'string') {
            const url = new URL(options);
            options = {
                hostname: url.hostname,
                port: url.port || 80,
                path: url.pathname + url.search,
                method: 'GET',
                headers: {}
            };
        }
        
        const originalHost = options.hostname || options.host;
        
        if (originalHost && (originalHost.includes('kiro.dev') || originalHost.includes('desktop'))) {
            console.log(`[HTTP] Redirecting HTTP request from ${originalHost} to localhost:${REDIRECT_PORT}`);
            
            options.hostname = REDIRECT_HOST;
            options.host = REDIRECT_HOST;
            options.port = REDIRECT_PORT;
            
            if (!options.headers) {
                options.headers = {};
            }
            options.headers['X-Original-Host'] = originalHost;
        }
        
        return originalRequest.call(this, options, callback);
    };
    
    console.log("[✓] HTTP request redirection installed");
    
} catch (e) {
    console.log("[HTTP] Redirect hook failed:", e.message);
}

console.log("[✓] Request Redirect Hook loaded successfully");
console.log("[!] All kiro.dev traffic will be redirected to localhost:" + REDIRECT_PORT);
console.log("[!] Mapping:");
Object.keys(ENDPOINT_MAPPING).forEach(endpoint => {
    console.log(`    ${endpoint} → localhost:${REDIRECT_PORT}`);
});

send({
    type: 'send',
    payload: `SUCCESS: Request redirect hook active - routing to localhost:${REDIRECT_PORT}`
});
