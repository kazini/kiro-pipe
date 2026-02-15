/**
 * Socket-Level Interception - Hook at the lowest level (send/recv)
 * 
 * This bypasses higher-level APIs and hooks directly at socket level
 * Should work even if WinHTTP functions aren't available
 */

console.log("[*] Socket-Level Interceptor Loading...");
console.log("[*] Hooking send/recv to capture encrypted traffic");

// State
let state = {
    startTime: Date.now(),
    totalSent: 0,
    totalReceived: 0,
    connections: new Map(), // socket -> connection info
    capturedData: []
};

// Try to find ws2_32.dll functions
console.log("\n[PHASE 1] Finding socket functions...");

const ws2_32 = Process.findModuleByName('WS2_32.dll') || Process.findModuleByName('ws2_32.dll');
if (!ws2_32) {
    console.log("  ✗ WS2_32.dll not found!");
} else {
    console.log(`  ✓ WS2_32.dll found at ${ws2_32.base}`);
}

// Hook connect() to track connections
console.log("\n[PHASE 2] Hooking connect()...");

try {
    const connectAddr = Module.getExportByName('ws2_32.dll', 'connect');
    if (connectAddr) {
        Interceptor.attach(connectAddr, {
            onEnter: function(args) {
                this.socket = args[0].toInt32();
                this.sockaddr = args[1];
                this.addrlen = args[2].toInt32();
                
                try {
                    // Parse sockaddr structure
                    if (this.addrlen >= 16) {
                        const family = this.sockaddr.readU16();
                        
                        if (family === 2) { // AF_INET (IPv4)
                            const port = (this.sockaddr.add(2).readU8() << 8) | this.sockaddr.add(3).readU8();
                            const ipBytes = this.sockaddr.add(4).readU32();
                            const ip = [
                                (ipBytes >> 0) & 0xFF,
                                (ipBytes >> 8) & 0xFF,
                                (ipBytes >> 16) & 0xFF,
                                (ipBytes >> 24) & 0xFF
                            ].join('.');
                            
                            console.log(`\n🔌 [CONNECT] Socket ${this.socket} → ${ip}:${port}`);
                            
                            // Store connection info
                            state.connections.set(this.socket, {
                                ip: ip,
                                port: port,
                                timestamp: Date.now(),
                                sent: 0,
                                received: 0
                            });
                            
                            // Check if this is HTTPS (port 443)
                            if (port === 443) {
                                console.log(`   🔐 HTTPS connection detected`);
                            }
                        }
                    }
                } catch (e) {
                    console.log(`   ⚠️ Error parsing sockaddr: ${e.message}`);
                }
            }
        });
        
        console.log("  ✓ Hooked connect()");
    }
} catch (e) {
    console.log(`  ✗ Failed to hook connect(): ${e.message}`);
}

// Hook send() to capture outgoing data
console.log("\n[PHASE 3] Hooking send()...");

try {
    const sendAddr = Module.getExportByName('ws2_32.dll', 'send');
    if (sendAddr) {
        Interceptor.attach(sendAddr, {
            onEnter: function(args) {
                this.socket = args[0].toInt32();
                this.buf = args[1];
                this.len = args[2].toInt32();
                
                try {
                    const connInfo = state.connections.get(this.socket);
                    
                    if (this.len > 0 && !this.buf.isNull()) {
                        const data = this.buf.readByteArray(Math.min(this.len, 1000));
                        const dataStr = bufferToString(data);
                        
                        // Check if this looks like HTTP/HTTPS traffic
                        const isHTTP = dataStr.includes('HTTP/') || 
                                      dataStr.includes('Host:') || 
                                      dataStr.includes('GET ') || 
                                      dataStr.includes('POST ');
                        
                        if (isHTTP || (connInfo && connInfo.port === 443)) {
                            console.log(`\n📤 [SEND] Socket ${this.socket} (${this.len} bytes)`);
                            
                            if (connInfo) {
                                console.log(`   → ${connInfo.ip}:${connInfo.port}`);
                                connInfo.sent += this.len;
                            }
                            
                            // Log data preview
                            console.log(`   Data preview (first 500 bytes):`);
                            console.log(`   ${dataStr.substring(0, 500)}`);
                            
                            // Check for interesting patterns
                            if (dataStr.includes('amazonaws.com') || 
                                dataStr.includes('kiro.dev') ||
                                dataStr.includes('generateAssistantResponse') ||
                                dataStr.includes('conversationId')) {
                                console.log(`   🎯 KIRO API REQUEST DETECTED!`);
                                
                                // Store this
                                state.capturedData.push({
                                    type: 'send',
                                    socket: this.socket,
                                    connection: connInfo,
                                    data: dataStr,
                                    length: this.len,
                                    timestamp: Date.now()
                                });
                            }
                            
                            state.totalSent += this.len;
                        }
                    }
                } catch (e) {
                    console.log(`   ⚠️ Error capturing send: ${e.message}`);
                }
            }
        });
        
        console.log("  ✓ Hooked send()");
    }
} catch (e) {
    console.log(`  ✗ Failed to hook send(): ${e.message}`);
}

// Hook recv() to capture incoming data
console.log("\n[PHASE 4] Hooking recv()...");

try {
    const recvAddr = Module.getExportByName('ws2_32.dll', 'recv');
    if (recvAddr) {
        Interceptor.attach(recvAddr, {
            onEnter: function(args) {
                this.socket = args[0].toInt32();
                this.buf = args[1];
                this.len = args[2].toInt32();
            },
            onLeave: function(retval) {
                try {
                    const bytesReceived = retval.toInt32();
                    
                    if (bytesReceived > 0 && !this.buf.isNull()) {
                        const connInfo = state.connections.get(this.socket);
                        const data = this.buf.readByteArray(Math.min(bytesReceived, 1000));
                        const dataStr = bufferToString(data);
                        
                        // Check if this looks like HTTP/HTTPS traffic
                        const isHTTP = dataStr.includes('HTTP/') || 
                                      dataStr.includes('Content-Type:') ||
                                      dataStr.includes('Transfer-Encoding:');
                        
                        if (isHTTP || (connInfo && connInfo.port === 443)) {
                            console.log(`\n📥 [RECV] Socket ${this.socket} (${bytesReceived} bytes)`);
                            
                            if (connInfo) {
                                console.log(`   ← ${connInfo.ip}:${connInfo.port}`);
                                connInfo.received += bytesReceived;
                            }
                            
                            // Log data preview
                            console.log(`   Data preview (first 500 bytes):`);
                            console.log(`   ${dataStr.substring(0, 500)}`);
                            
                            // Check for interesting patterns
                            if (dataStr.includes('conversationId') || 
                                dataStr.includes('message') ||
                                dataStr.includes('content') ||
                                dataStr.includes('modelId') ||
                                dataStr.includes('error')) {
                                console.log(`   🎯 KIRO API RESPONSE DETECTED!`);
                                
                                // Store this
                                state.capturedData.push({
                                    type: 'recv',
                                    socket: this.socket,
                                    connection: connInfo,
                                    data: dataStr,
                                    length: bytesReceived,
                                    timestamp: Date.now()
                                });
                            }
                            
                            state.totalReceived += bytesReceived;
                        }
                    }
                } catch (e) {
                    console.log(`   ⚠️ Error capturing recv: ${e.message}`);
                }
            }
        });
        
        console.log("  ✓ Hooked recv()");
    }
} catch (e) {
    console.log(`  ✗ Failed to hook recv(): ${e.message}`);
}

// Utility: Convert buffer to string
function bufferToString(buffer) {
    try {
        const uint8Array = new Uint8Array(buffer);
        let str = '';
        
        for (let i = 0; i < uint8Array.length; i++) {
            const byte = uint8Array[i];
            if (byte >= 32 && byte <= 126) {
                str += String.fromCharCode(byte);
            } else if (byte === 10) {
                str += '\n';
            } else if (byte === 13) {
                str += '\r';
            } else {
                str += '.';
            }
        }
        
        return str;
    } catch (e) {
        return '[Error converting buffer]';
    }
}

// Summary
console.log("\n" + "=".repeat(70));
console.log("[SOCKET INTERCEPTOR - READY]");
console.log("=".repeat(70));
console.log("Hooked at socket level (send/recv)");
console.log("Will capture ALL socket traffic including encrypted HTTPS");
console.log("\n[INSTRUCTIONS]:");
console.log("1. Use Kiro's AI features");
console.log("2. Watch for 🔌 [CONNECT] to see connections");
console.log("3. Watch for 📤 [SEND] and 📥 [RECV] for data");
console.log("4. Look for 🎯 markers for Kiro API traffic");
console.log("\n[NOTE]:");
console.log("• HTTPS traffic will appear encrypted (binary data)");
console.log("• We'll see the TLS handshake and encrypted payload");
console.log("• To decrypt, we need to bypass certificate pinning");

// Status dashboard
setInterval(function() {
    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    
    console.log(`\n` + "=".repeat(70));
    console.log(`[SOCKET STATUS] ${elapsed}s elapsed`);
    console.log("=".repeat(70));
    console.log(`Active connections: ${state.connections.size}`);
    console.log(`Total sent: ${(state.totalSent / 1024).toFixed(1)} KB`);
    console.log(`Total received: ${(state.totalReceived / 1024).toFixed(1)} KB`);
    console.log(`Captured Kiro API calls: ${state.capturedData.length}`);
    
    if (state.connections.size > 0) {
        console.log(`\nConnections:`);
        for (const [socket, info] of state.connections) {
            console.log(`  Socket ${socket}: ${info.ip}:${info.port}`);
            console.log(`    Sent: ${(info.sent / 1024).toFixed(1)} KB, Received: ${(info.received / 1024).toFixed(1)} KB`);
        }
    }
    
    if (state.capturedData.length > 0) {
        console.log(`\n✅ Captured Kiro API traffic!`);
        console.log(`   Check output above for details`);
    } else if (state.totalSent > 0 || state.totalReceived > 0) {
        console.log(`\n⚠️ Seeing network traffic but no Kiro API detected yet`);
    } else {
        console.log(`\n⏳ Waiting for network activity...`);
    }
}, 15000);

console.log("\n[✓] Socket interceptor loaded");

send({
    type: 'send',
    payload: 'SUCCESS: Socket-level interceptor loaded'
});