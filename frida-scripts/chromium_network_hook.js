/**
 * Chromium Network Hook - Target Chromium's internal networking
 * 
 * Since Windows APIs don't work, we need to hook Chromium's internal functions
 * This requires finding the right symbols in libchromium or similar modules
 */

console.log("[*] Chromium Network Hook Loading...");
console.log("[*] Searching for Chromium networking internals");

// State
let state = {
    startTime: Date.now(),
    foundModules: [],
    hookedFunctions: 0,
    capturedRequests: []
};

// Phase 1: Find Chromium-related modules
console.log("\n[PHASE 1] Searching for Chromium modules...");

const modules = Process.enumerateModules();
const chromiumModules = [];

// Look for modules that might contain networking code
const keywords = ['chrome', 'chromium', 'libcef', 'electron', 'node', 'v8', 'blink'];

for (const mod of modules) {
    const name = mod.name.toLowerCase();
    for (const keyword of keywords) {
        if (name.includes(keyword)) {
            chromiumModules.push(mod);
            console.log(`  Found: ${mod.name} (${(mod.size / 1024 / 1024).toFixed(1)} MB)`);
            state.foundModules.push(mod.name);
            break;
        }
    }
}

console.log(`\nTotal Chromium-related modules: ${chromiumModules.length}`);

// Phase 2: Search for networking-related exports
console.log("\n[PHASE 2] Searching for networking exports...");

const networkingPatterns = [
    'URLRequest', 'HttpRequest', 'NetworkDelegate', 'URLFetcher',
    'SSLConfig', 'CertVerifier', 'HttpTransaction', 'SocketStream',
    'ProxyService', 'HostResolver', 'DNSClient'
];

let foundExports = [];

for (const mod of chromiumModules) {
    try {
        const exports = mod.enumerateExports();
        
        for (const exp of exports) {
            const expName = exp.name;
            
            // Check if export name matches networking patterns
            for (const pattern of networkingPatterns) {
                if (expName.includes(pattern)) {
                    foundExports.push({
                        module: mod.name,
                        name: expName,
                        address: exp.address
                    });
                    
                    if (foundExports.length <= 20) { // Limit output
                        console.log(`  ${mod.name}!${expName}`);
                    }
                    break;
                }
            }
        }
    } catch (e) {
        // Can't enumerate exports from this module
    }
}

console.log(`\nFound ${foundExports.length} networking-related exports`);

// Phase 3: Try to hook Node.js networking (if available)
console.log("\n[PHASE 3] Checking for Node.js networking...");

try {
    // Check if we can access Node.js internals
    if (typeof process !== 'undefined' && process.binding) {
        console.log("  ✓ Node.js process object available");
        
        try {
            const tcp = process.binding('tcp_wrap');
            console.log("  ✓ tcp_wrap binding available");
            
            // Try to hook TCP connections
            // This is tricky and might not work
        } catch (e) {
            console.log(`  ✗ tcp_wrap not accessible: ${e.message}`);
        }
    } else {
        console.log("  ✗ Node.js process object not available");
    }
} catch (e) {
    console.log(`  ✗ Node.js check failed: ${e.message}`);
}

// Phase 4: Try to find and hook DNS resolution
console.log("\n[PHASE 4] Attempting to hook DNS resolution...");

try {
    // Try getaddrinfo (standard DNS function)
    const getaddrinfo = Module.getExportByName(null, 'getaddrinfo');
    if (getaddrinfo) {
        Interceptor.attach(getaddrinfo, {
            onEnter: function(args) {
                try {
                    const hostname = args[0].readUtf8String();
                    if (hostname && (hostname.includes('amazonaws.com') || hostname.includes('kiro.dev'))) {
                        console.log(`\n🔍 [DNS] Resolving: ${hostname}`);
                        state.capturedRequests.push({
                            type: 'dns',
                            hostname: hostname,
                            timestamp: Date.now()
                        });
                    }
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        console.log("  ✓ Hooked getaddrinfo (DNS resolution)");
        state.hookedFunctions++;
    }
} catch (e) {
    console.log(`  ✗ Failed to hook DNS: ${e.message}`);
}

// Phase 5: Try to hook at TLS/SSL layer
console.log("\n[PHASE 5] Attempting to hook SSL/TLS...");

try {
    // Look for SSL_write and SSL_read (OpenSSL functions)
    const sslModules = ['libssl', 'ssleay32', 'libeay32'];
    
    for (const modName of sslModules) {
        try {
            const SSL_write = Module.findExportByName(modName, 'SSL_write');
            const SSL_read = Module.findExportByName(modName, 'SSL_read');
            
            if (SSL_write) {
                Interceptor.attach(SSL_write, {
                    onEnter: function(args) {
                        this.ssl = args[0];
                        this.buf = args[1];
                        this.num = args[2].toInt32();
                        
                        try {
                            if (this.num > 0 && !this.buf.isNull()) {
                                const data = this.buf.readByteArray(Math.min(this.num, 500));
                                const dataStr = bufferToString(data);
                                
                                if (dataStr.includes('amazonaws.com') || 
                                    dataStr.includes('generateAssistantResponse') ||
                                    dataStr.includes('conversationId')) {
                                    console.log(`\n📤 [SSL_WRITE] ${this.num} bytes`);
                                    console.log(`   ${dataStr.substring(0, 300)}`);
                                    
                                    state.capturedRequests.push({
                                        type: 'ssl_write',
                                        data: dataStr,
                                        length: this.num,
                                        timestamp: Date.now()
                                    });
                                }
                            }
                        } catch (e) {
                            // Silently fail
                        }
                    }
                });
                
                console.log(`  ✓ Hooked SSL_write in ${modName}`);
                state.hookedFunctions++;
            }
            
            if (SSL_read) {
                Interceptor.attach(SSL_read, {
                    onEnter: function(args) {
                        this.ssl = args[0];
                        this.buf = args[1];
                        this.num = args[2].toInt32();
                    },
                    onLeave: function(retval) {
                        try {
                            const bytesRead = retval.toInt32();
                            if (bytesRead > 0 && !this.buf.isNull()) {
                                const data = this.buf.readByteArray(Math.min(bytesRead, 500));
                                const dataStr = bufferToString(data);
                                
                                if (dataStr.includes('conversationId') || 
                                    dataStr.includes('message') ||
                                    dataStr.includes('content')) {
                                    console.log(`\n📥 [SSL_READ] ${bytesRead} bytes`);
                                    console.log(`   ${dataStr.substring(0, 300)}`);
                                    
                                    state.capturedRequests.push({
                                        type: 'ssl_read',
                                        data: dataStr,
                                        length: bytesRead,
                                        timestamp: Date.now()
                                    });
                                }
                            }
                        } catch (e) {
                            // Silently fail
                        }
                    }
                });
                
                console.log(`  ✓ Hooked SSL_read in ${modName}`);
                state.hookedFunctions++;
            }
        } catch (e) {
            // Module not found
        }
    }
} catch (e) {
    console.log(`  ✗ SSL/TLS hooking failed: ${e.message}`);
}

// Phase 6: Try BoringSSL (Chromium's SSL library)
console.log("\n[PHASE 6] Checking for BoringSSL...");

try {
    // BoringSSL functions might be in the main executable or a DLL
    const boringSSLFuncs = ['SSL_write', 'SSL_read', 'SSL_do_handshake', 'SSL_connect'];
    
    for (const funcName of boringSSLFuncs) {
        try {
            const funcAddr = Module.findExportByName(null, funcName);
            if (funcAddr) {
                console.log(`  ✓ Found ${funcName} at ${funcAddr}`);
                // Could hook here but already tried above
            }
        } catch (e) {
            // Not found
        }
    }
} catch (e) {
    console.log(`  ✗ BoringSSL check failed: ${e.message}`);
}

// Utility function
function bufferToString(buffer) {
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
        return '[Error]';
    }
}

// Summary
console.log("\n" + "=".repeat(70));
console.log("[CHROMIUM NETWORK HOOK - READY]");
console.log("=".repeat(70));
console.log(`Chromium modules found: ${state.foundModules.length}`);
console.log(`Networking exports found: ${foundExports.length}`);
console.log(`Functions hooked: ${state.hookedFunctions}`);

if (state.hookedFunctions > 0) {
    console.log(`\n✅ Successfully hooked ${state.hookedFunctions} function(s)`);
    console.log(`\n[INSTRUCTIONS]:`);
    console.log(`1. Use Kiro's AI features`);
    console.log(`2. Watch for 🔍 [DNS], 📤 [SSL_WRITE], 📥 [SSL_READ] markers`);
    console.log(`3. Captured data will show decrypted HTTPS traffic`);
} else {
    console.log(`\n⚠️ No functions hooked - Chromium uses internal networking`);
    console.log(`\nPossible reasons:`);
    console.log(`1. Chromium's networking is compiled in (no exports)`);
    console.log(`2. Using BoringSSL with symbol stripping`);
    console.log(`3. Need to hook at a different layer`);
    console.log(`\nNext steps:`);
    console.log(`1. Try hooking renderer process (if anti-debug can be bypassed)`);
    console.log(`2. Use system-wide proxy with custom CA certificate`);
    console.log(`3. Modify Kiro's executable to disable certificate pinning`);
}

// Status updates
setInterval(function() {
    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    
    console.log(`\n[STATUS] ${elapsed}s elapsed - Captured: ${state.capturedRequests.length} requests`);
    
    if (state.capturedRequests.length > 0) {
        console.log(`✅ Successfully capturing traffic!`);
        const recent = state.capturedRequests.slice(-3);
        for (const req of recent) {
            console.log(`  ${req.type}: ${new Date(req.timestamp).toLocaleTimeString()}`);
        }
    }
}, 15000);

console.log("\n[✓] Chromium network hook loaded");

send({
    type: 'send',
    payload: `Chromium hook loaded - ${state.hookedFunctions} functions hooked`
});