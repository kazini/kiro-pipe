/**
 * Test Any Network - Catch ALL network activity from Kiro
 * Ultimate network monitoring script
 */

console.log("[*] Test Any Network Loading...");
console.log("[*] Attempting to catch ALL network activity from Kiro");

// Comprehensive tracking
let activity = {
    startTime: Date.now(),
    totalCalls: 0,
    byFunction: {},
    byProtocol: {http: 0, https: 0, other: 0, dns: 0, ssl: 0},
    destinations: new Set(),
    uniqueIPs: new Set(),
    dataSent: 0,
    dataReceived: 0
};

// Function to log activity
function logActivity(type, details) {
    activity.totalCalls++;
    
    // Track by function
    activity.byFunction[type] = (activity.byFunction[type] || 0) + 1;
    
    // Log to console
    console.log(`\n[NET-${activity.totalCalls}] ${type}`);
    if (details) {
        console.log(`  ${details}`);
    }
    
    // Check for interesting patterns
    if (details && (
        details.includes('kiro.dev') || 
        details.includes('amazonaws') ||
        details.includes('bedrock') ||
        details.includes('aws') ||
        details.includes('amazon.com')
    )) {
        console.log(`  🎯 INTERESTING: ${details.match(/(kiro\.dev|amazonaws|bedrock|aws|amazon\.com)/i)[0]}`);
    }
}

// Phase 1: Hook ALL Windows networking APIs we can find
console.log("\n[PHASE 1] Hooking Windows Networking APIs...");

// Comprehensive list of Windows networking functions
const windowsNetworkingFuncs = [
    // WinHTTP
    'WinHttpOpen', 'WinHttpConnect', 'WinHttpOpenRequest', 'WinHttpSendRequest',
    'WinHttpReceiveResponse', 'WinHttpReadData', 'WinHttpWriteData',
    'WinHttpQueryHeaders', 'WinHttpQueryDataAvailable',
    
    // WinINET
    'InternetOpenA', 'InternetOpenW', 'InternetConnectA', 'InternetConnectW',
    'InternetOpenUrlA', 'InternetOpenUrlW', 'HttpOpenRequestA', 'HttpOpenRequestW',
    'HttpSendRequestA', 'HttpSendRequestW', 'HttpSendRequestExA', 'HttpSendRequestExW',
    'InternetReadFile', 'InternetWriteFile', 'InternetQueryDataAvailable',
    
    // Sockets (WS2_32)
    'connect', 'send', 'recv', 'WSASend', 'WSARecv', 'WSASendTo', 'WSARecvFrom',
    'accept', 'listen', 'bind', 'socket', 'closesocket', 'shutdown',
    'getpeername', 'getsockname', 'getsockopt', 'setsockopt',
    
    // DNS
    'getaddrinfo', 'GetAddrInfoW', 'getnameinfo', 'GetNameInfoW',
    'gethostbyname', 'gethostbyaddr', 'gethostname',
    
    // WSA (Windows Sockets Async)
    'WSAConnect', 'WSAAccept', 'WSAAsyncSelect', 'WSAEventSelect',
    
    // HTTP.sys (if used)
    'HttpInitialize', 'HttpCreateHttpHandle', 'HttpAddUrl', 'HttpRemoveUrl',
    'HttpReceiveHttpRequest', 'HttpSendHttpResponse',
    
    // Other networking
    'Netbios', 'WNetAddConnection2A', 'WNetAddConnection2W',
    
    // SSL/TLS (Schannel)
    'SslEncryptPacket', 'SslDecryptPacket', 'SslStreamOpen', 'SslStreamClose',
    'SslStreamRead', 'SslStreamWrite', 'SslGenerateRandomBits',
    
    // Cryptography (for certs)
    'CertVerifyCertificateChainPolicy', 'CertGetCertificateChain',
    'CertVerifyRevocation', 'CertOpenStore', 'CertCloseStore'
];

let windowsHooksInstalled = 0;
for (const funcName of windowsNetworkingFuncs) {
    try {
        const funcAddr = Module.getGlobalExportByName(funcName);
        if (funcAddr) {
            Interceptor.attach(funcAddr, {
                onEnter: function(args) {
                    let details = '';
                    
                    // Try to extract useful info based on function type
                    if (funcName.includes('Connect')) {
                        // Connection functions
                        try {
                            if (funcName.includes('WinHttpConnect') || funcName.includes('InternetConnect')) {
                                const hostnamePtr = funcName.includes('WinHttpConnect') ? args[2] : args[1];
                                if (!hostnamePtr.isNull()) {
                                    const isWide = funcName.endsWith('W');
                                    const hostname = isWide ? hostnamePtr.readUtf16String() : hostnamePtr.readUtf8String();
                                    if (hostname) {
                                        details = `to: ${hostname}`;
                                        activity.destinations.add(hostname);
                                        
                                        // Check port if available
                                        if (args.length > (funcName.includes('WinHttpConnect') ? 3 : 2)) {
                                            const port = args[funcName.includes('WinHttpConnect') ? 3 : 2].toInt32();
                                            details += `:${port}`;
                                            if (port === 443) activity.byProtocol.https++;
                                            else if (port === 80) activity.byProtocol.http++;
                                            else activity.byProtocol.other++;
                                        }
                                    }
                                }
                            } else if (funcName === 'connect' || funcName === 'WSAConnect') {
                                // Socket connect
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
                                    
                                    details = `to ${ip}:${port}`;
                                    activity.uniqueIPs.add(ip);
                                    if (port === 443) activity.byProtocol.https++;
                                    else if (port === 80) activity.byProtocol.http++;
                                    else activity.byProtocol.other++;
                                }
                            }
                        } catch (e) {}
                    } else if (funcName.includes('addrinfo') || funcName.includes('hostbyname')) {
                        // DNS functions
                        activity.byProtocol.dns++;
                        try {
                            const namePtr = args[0];
                            if (!namePtr.isNull()) {
                                const isWide = funcName.includes('W');
                                const name = isWide ? namePtr.readUtf16String() : namePtr.readUtf8String();
                                if (name) details = `lookup: ${name}`;
                            }
                        } catch (e) {}
                    } else if (funcName.includes('Ssl') || funcName.includes('Cert')) {
                        // SSL/TLS or certificate functions
                        activity.byProtocol.ssl++;
                        details = 'SSL/certificate operation';
                    } else if (funcName.includes('send') || funcName.includes('Write')) {
                        // Data sending
                        try {
                            const length = args[2] ? args[2].toInt32() : 0;
                            if (length > 0) {
                                activity.dataSent += length;
                                details = `${length} bytes`;
                                
                                // Try to peek at data (small buffers only)
                                if (length < 1024) {
                                    try {
                                        const buffer = args[1];
                                        const data = buffer.readByteArray(Math.min(length, 256));
                                        let str = '';
                                        for (let i = 0; i < data.length; i++) {
                                            const byte = data[i];
                                            if (byte >= 32 && byte <= 126) str += String.fromCharCode(byte);
                                            else if (byte === 10 || byte === 13) str += ' ';
                                            else str += '.';
                                        }
                                        
                                        // Check for interesting patterns
                                        if (str.includes('Host:') || str.includes('GET ') || str.includes('POST ') || 
                                            str.includes('HTTP/') || str.includes('Content-Type:')) {
                                            details += ' (HTTP data)';
                                            // Extract host if possible
                                            const hostMatch = str.match(/Host:\s*([^\r\n]+)/i);
                                            if (hostMatch) details += ` Host: ${hostMatch[1].trim()}`;
                                        }
                                    } catch (e) {}
                                }
                            }
                        } catch (e) {}
                    } else if (funcName.includes('recv') || funcName.includes('Read')) {
                        // Data receiving
                        try {
                            const length = args[2] ? args[2].toInt32() : 0;
                            if (length > 0) {
                                activity.dataReceived += length;
                                details = `${length} bytes`;
                            }
                        } catch (e) {}
                    }
                    
                    logActivity(funcName, details);
                }
            });
            
            windowsHooksInstalled++;
            // console.log(`  ✓ ${funcName}`);
        }
    } catch (e) {
        // Function not found - that's OK
    }
}

console.log(`[PHASE 1] Installed ${windowsHooksInstalled} Windows API hooks`);

// Phase 2: Try to find and hook any other networking modules
console.log("\n[PHASE 2] Searching for other networking modules...");

try {
    const modules = Process.enumerateModules();
    let otherNetModules = 0;
    
    for (const mod of modules) {
        const name = mod.name.toLowerCase();
        
        // Look for modules that might contain networking code
        // but aren't standard Windows DLLs we already hooked
        if ((name.includes('net') || name.includes('http') || name.includes('ssl') || 
             name.includes('tls') || name.includes('curl') || name.includes('socket')) &&
            !name.includes('winhttp') && !name.includes('wininet') && 
            !name.includes('ws2_32') && !name.includes('crypt32') &&
            !name.includes('schannel') && !name.includes('bcrypt')) {
            
            console.log(`  Found potential networking module: ${mod.name}`);
            otherNetModules++;
            
            // Try to enumerate exports and hook them
            try {
                const exports = mod.enumerateExports();
                console.log(`    ${exports.length} exports`);
                
                // Hook a few interesting ones
                let hookedFromModule = 0;
                for (const exp of exports.slice(0, 20)) { // First 20
                    const expName = exp.name.toLowerCase();
                    if (expName.includes('connect') || expName.includes('send') || 
                        expName.includes('request') || expName.includes('http') ||
                        expName.includes('ssl') || expName.includes('tls')) {
                        
                        try {
                            Interceptor.attach(exp.address, {
                                onEnter: function(args) {
                                    logActivity(`${mod.name}!${exp.name}`, 'from non-standard module');
                                }
                            });
                            hookedFromModule++;
                        } catch (e) {}
                    }
                }
                
                if (hookedFromModule > 0) {
                    console.log(`    Hooked ${hookedFromModule} functions`);
                }
            } catch (e) {
                // Couldn't enumerate exports
            }
        }
    }
    
    console.log(`[PHASE 2] Found ${otherNetModules} other potential networking modules`);
} catch (e) {
    console.log(`[PHASE 2] Failed: ${e.message}`);
}

// Phase 3: Monitor process creation (in case networking happens in child processes)
console.log("\n[PHASE 3] Monitoring process creation...");

try {
    // This would require different Frida APIs
    console.log(`  Process creation monitoring would need Process.enumerateThreads() etc.`);
} catch (e) {
    console.log(`[PHASE 3] Limited: ${e.message}`);
}

// Summary
console.log("\n" + "=".repeat(70));
console.log("[ULTIMATE NETWORK MONITOR - READY]");
console.log("=".repeat(70));
console.log(`Total hooks installed: ${windowsHooksInstalled}`);
console.log(`Monitoring started at: ${new Date(activity.startTime).toLocaleTimeString()}`);
console.log(`\n[INSTRUCTIONS]`);
console.log(`1. Use Kiro's AI features (chat, code generation, etc.)`);
console.log(`2. Watch for [NET-XX] output above`);
console.log(`3. Interesting destinations marked with 🎯`);
console.log(`4. All network activity will be logged`);
console.log(`\n[EXPECTED OUTPUT]`);
console.log(`- HTTP/HTTPS connections to kiro.dev, AWS, Bedrock, etc.`);
console.log(`- DNS lookups for domain names`);
console.log(`- SSL/TLS handshakes`);
console.log(`- Data sent/received`);

// Real-time monitoring dashboard
let updateCount = 0;
setInterval(function() {
    updateCount++;
    const elapsed = Math.floor((Date.now() - activity.startTime) / 1000);
    
    console.log(`\n` + "=".repeat(70));
    console.log(`[DASHBOARD ${updateCount}] ${elapsed}s elapsed`);
    console.log("=".repeat(70));
    console.log(`Total network calls: ${activity.totalCalls}`);
    console.log(`\nProtocol breakdown:`);
    console.log(`  HTTPS: ${activity.byProtocol.https}`);
    console.log(`  HTTP: ${activity.byProtocol.http}`);
    console.log(`  DNS: ${activity.byProtocol.dns}`);
    console.log(`  SSL/TLS: ${activity.byProtocol.ssl}`);
    console.log(`  Other: ${activity.byProtocol.other}`);
    console.log(`\nData transfer:`);
    console.log(`  Sent: ${(activity.dataSent / 1024).toFixed(1)} KB`);
    console.log(`  Received: ${(activity.dataReceived / 1024).toFixed(1)} KB`);
    console.log(`\nUnique destinations: ${activity.destinations.size}`);
    console.log(`Unique IPs: ${activity.uniqueIPs.size}`);
    
    // Show top functions being called
    if (Object.keys(activity.byFunction).length > 0) {
        console.log(`\nTop functions:`);
        const sorted = Object.entries(activity.byFunction)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
        for (const [func, count] of sorted) {
            console.log(`  ${func}: ${count} calls`);
        }
    }
    
    // Show destinations if any
    if (activity.destinations.size > 0) {
        console.log(`\nDestinations found:`);
        const destArray = Array.from(activity.destinations);
        for (let i = 0; i < Math.min(destArray.length, 5); i++) {
            console.log(`  ${destArray[i]}`);
        }
        if (destArray.length > 5) {
            console.log(`  ... and ${destArray.length - 5} more`);
        }
    }
    
    // Analysis
    if (activity.totalCalls === 0) {
        console.log(`\n❌ NO NETWORK ACTIVITY DETECTED`);
        console.log(`This suggests:`);
        console.log(`  1. Wrong process (Kiro networking in different process)`);
        console.log(`  2. Different networking stack (HTTP/3, WebSockets, etc.)`);
        console.log(`  3. No network calls being made (offline/cached)`);
        console.log(`  4. All hooks failed (unlikely with ${windowsHooksInstalled} hooks)`);
    } else if (activity.byProtocol.https === 0 && activity.byProtocol.http === 0) {
        console.log(`\n⚠️ Network activity but no HTTP/HTTPS`);
        console.log(`Only seeing: ${Object.entries(activity.byProtocol).filter(([k,v]) => v > 0).map(([k,v]) => `${k}:${v}`).join(', ')}`);
    } else {
        console.log(`\n✅ Network activity detected`);
        console.log(`Check output above for specific calls`);
    }
    
}, 15000);

console.log("\n[✓] Ultimate Network Monitor loaded successfully");
console.log("[!] Monitoring ALL network activity for 60+ seconds");

// Keep alive for extended monitoring
setTimeout(function() {
    console.log("\n[INFO] Still monitoring... (extended session)");
}, 60000);

send({
    type: 'send',
    payload: 'SUCCESS: Ultimate network monitor loaded - catching ALL network activity'
});