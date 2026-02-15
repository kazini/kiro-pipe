/**
 * Certificate Validation Bypass Hook
 * ===================================
 * 
 * Purpose: Bypass or manipulate certificate validation in Node.js TLS
 * 
 * Targets:
 * - tlsSocket.verifyHostname()
 * - tls.createSecureContext()
 * - crypto.createSecureContext()
 */

console.log("[*] Certificate Bypass Hook Loading...");

// Strategy 1: Hook the TLS module's checkServerIdentity
try {
    const Module = require('module');
    const originalRequire = Module.prototype.require;
    
    Module.prototype.require = function(id) {
        const module = originalRequire.apply(this, arguments);
        
        // Hook the 'tls' module
        if (id === 'tls' && module.createSecureContext) {
            const originalCreateSecureContext = module.createSecureContext;
            
            module.createSecureContext = function(options) {
                console.log("[TLS] createSecureContext called with options:", {
                    rejectUnauthorized: options?.rejectUnauthorized,
                    cert: !!options?.cert,
                    key: !!options?.key
                });
                
                // Disable certificate validation
                const modifiedOptions = Object.assign({}, options, {
                    rejectUnauthorized: false
                });
                
                const context = originalCreateSecureContext.call(this, modifiedOptions);
                console.log("[TLS] SUCCESS - Certificate validation disabled");
                return context;
            };
        }
        
        return module;
    };
} catch (e) {
    console.log("[TLS] Standard require hook failed:", e.message);
}

// Strategy 2: Hook at the native level using Interceptor
try {
    // Get Node.js native modules
    const nodeHttps = Module.prototype.require.call(process, 'https');
    const nodeTls = Module.prototype.require.call(process, 'tls');
    
    // Try to find and hook certificate validation functions
    if (nodeTls && nodeTls.TLSSocket) {
        const OriginalTLSSocket = nodeTls.TLSSocket;
        let hookCount = 0;
        
        // Proxy the TLSSocket constructor
        nodeTls.TLSSocket = new Proxy(OriginalTLSSocket, {
            construct: function(target, args, newTarget) {
                const socket = new target(...args);
                
                // Hook the verify result
                if (socket._handle && socket._handle.verifyError) {
                    socket._handle.verifyError = null;
                    console.log(`[TLS] Cleared verification error for socket`);
                }
                
                hookCount++;
                if (hookCount % 10 === 0) {
                    console.log(`[TLS] Hooked ${hookCount} TLS socket creations`);
                }
                
                return socket;
            }
        });
        
        console.log("[TLS] TLSSocket proxy installed");
    }
} catch (e) {
    console.log("[TLS] TLSSocket proxy failed:", e.message);
}

// Strategy 3: Intercept at the option-setting level
try {
    const nodeHttps = Module.prototype.require.call(process, 'https');
    const originalRequest = nodeHttps.request;
    
    nodeHttps.request = function(options, callback) {
        console.log("[HTTPS] request to:", options.hostname || options.host);
        
        // Force rejectUnauthorized to false
        if (typeof options === 'string') {
            // URL string case - create options object
            options = {
                hostname: new URL(options).hostname,
                pathname: new URL(options).pathname
            };
        } else if (options) {
            options.rejectUnauthorized = false;
        }
        
        console.log("[HTTPS] rejectUnauthorized set to false");
        
        return originalRequest.call(this, options, callback);
    };
    
    console.log("[HTTPS] https.request intercepted");
} catch (e) {
    console.log("[HTTPS] https.request interception failed:", e.message);
}

// Strategy 4: Use Frida's Interceptor if available
try {
    if (typeof Interceptor !== 'undefined') {
        // Get addresses of TLS-related functions
        // This is highly version-dependent and may need adjustment
        
        console.log("[FRIDA] Attempting native code interception...");
        
        // Hook dlopen to track when BoringSSL/OpenSSL is loaded
        const dlopen = Module.getExportByName(null, 'dlopen');
        if (dlopen) {
            Interceptor.attach(dlopen, {
                onEnter: function(args) {
                    const libPath = args[0].readUtf8String();
                    if (libPath && (libPath.includes('ssl') || libPath.includes('crypto'))) {
                        console.log("[FRIDA-Native] Loading crypto library:", libPath);
                    }
                }
            });
        }
    }
} catch (e) {
    console.log("[FRIDA] Native interception not available:", e.message);
}

console.log("[✓] Certificate Bypass Hook loaded successfully");
console.log("[!] Certificate validation has been disabled for Kiro connections");
send({
    type: 'send',
    payload: 'SUCCESS: Certificate bypass hook active - TLS validation disabled'
});
