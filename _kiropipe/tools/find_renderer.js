/**
 * Find Renderer Process - Locate Kiro's renderer process for networking
 */

console.log("[*] Find Renderer Process Script Loading...");

// Strategy: Look for processes with Chromium/Electron characteristics
console.log("[STRATEGY] Looking for Electron renderer processes...");

try {
    // First, let's see what we can access from current process
    console.log(`[CURRENT] PID: ${Process.id}, Name: ${Process.name}`);
    
    // Check if we're in a Node.js context
    console.log("[CHECK] Looking for Node.js/Electron indicators...");
    
    let foundNode = false;
    let foundElectron = false;
    
    // Check for Node.js globals
    const nodeGlobals = ['process', 'require', 'module', 'exports', '__dirname', '__filename'];
    for (const globalName of nodeGlobals) {
        try {
            if (eval(`typeof ${globalName}`) !== 'undefined') {
                console.log(`  Found ${globalName}: ${eval(`typeof ${globalName}`)}`);
                if (globalName === 'process') foundNode = true;
            }
        } catch (e) {}
    }
    
    // Check for Electron-specific globals
    const electronGlobals = ['electron', 'ipcRenderer', 'ipcMain', 'remote'];
    for (const globalName of electronGlobals) {
        try {
            if (eval(`typeof ${globalName}`) !== 'undefined') {
                console.log(`  Found Electron global: ${globalName}`);
                foundElectron = true;
            }
        } catch (e) {}
    }
    
    // Check process arguments
    if (typeof Process !== 'undefined' && Process.enumerateModules) {
        const modules = Process.enumerateModules();
        console.log(`[MODULES] ${modules.length} modules loaded`);
        
        // Look for Chromium/Electron modules
        let chromiumModules = [];
        for (const mod of modules) {
            const name = mod.name.toLowerCase();
            if (name.includes('chrome') || name.includes('chromium') || 
                name.includes('electron') || name.includes('cef') ||
                name.includes('blink') || name.includes('v8')) {
                chromiumModules.push(mod);
            }
        }
        
        console.log(`[CHROMIUM] Found ${chromiumModules.length} Chromium/Electron modules`);
        for (const mod of chromiumModules.slice(0, 5)) {
            console.log(`  ${mod.name} (${mod.size} bytes)`);
        }
    }
    
    // Determine process type
    console.log("\n[ANALYSIS] Process type analysis:");
    if (foundNode && foundElectron) {
        console.log("  ✅ Likely Electron MAIN process (Node.js + Electron)");
        console.log("  ⚠️ Networking may be in RENDERER process");
    } else if (foundNode) {
        console.log("  ✅ Node.js process");
    } else if (foundElectron) {
        console.log("  ✅ Electron process (but not main?)");
    } else {
        console.log("  ❓ Unknown process type");
        console.log("  ⚠️ May not be the right process for networking");
    }
    
    // Check for window/document (renderer indicator)
    try {
        if (typeof window !== 'undefined') {
            console.log("\n  🎯 Found 'window' object - likely RENDERER process!");
            console.log(`  Window location: ${window.location}`);
            console.log(`  Document readyState: ${document.readyState}`);
            
            // Check for web APIs
            if (typeof fetch !== 'undefined') {
                console.log(`  ✅ fetch() API available`);
            }
            if (typeof XMLHttpRequest !== 'undefined') {
                console.log(`  ✅ XMLHttpRequest available`);
            }
            if (typeof WebSocket !== 'undefined') {
                console.log(`  ✅ WebSocket available`);
            }
        }
    } catch (e) {
        console.log("\n  No 'window' object - not a renderer process");
    }
    
    // Recommendations
    console.log("\n[RECOMMENDATIONS]");
    if (typeof window !== 'undefined') {
        console.log("  1. ✅ You're in a RENDERER process - good for networking!");
        console.log("  2. Try hooking fetch() and XMLHttpRequest");
        console.log("  3. Network calls should be visible here");
    } else {
        console.log("  1. ⚠️ You're likely in MAIN process");
        console.log("  2. Networking happens in RENDERER process(es)");
        console.log("  3. Need to find and attach to renderer process");
        console.log("  4. Or use different approach (process-wide hooking)");
    }
    
    // If we're in renderer, demonstrate we can hook web APIs
    if (typeof window !== 'undefined' && typeof XMLHttpRequest !== 'undefined') {
        console.log("\n[DEMO] Hooking XMLHttpRequest in renderer...");
        
        const OriginalXHR = window.XMLHttpRequest;
        window.XMLHttpRequest = function() {
            const xhr = new OriginalXHR();
            
            const originalOpen = xhr.open;
            xhr.open = function(method, url) {
                console.log(`🎯 [XHR] ${method} ${url}`);
                if (url.includes('amazonaws') || url.includes('bedrock') || url.includes('kiro.dev')) {
                    console.log(`   ⭐ INTERESTING: ${url}`);
                }
                return originalOpen.apply(this, arguments);
            };
            
            return xhr;
        };
        
        console.log("  ✅ XMLHttpRequest hooked");
        
        // Also hook fetch if available
        if (typeof window.fetch !== 'undefined') {
            const originalFetch = window.fetch;
            window.fetch = function() {
                console.log(`🎯 [FETCH] ${arguments[0]}`);
                return originalFetch.apply(this, arguments);
            };
            console.log("  ✅ fetch() hooked");
        }
    }
    
} catch (e) {
    console.log("[ERROR] Analysis failed:", e.message);
    console.log("[ERROR] Stack:", e.stack);
}

console.log("\n[✓] Find Renderer Process completed");

// If we found we're in wrong process, suggest next steps
setTimeout(function() {
    console.log("\n[NEXT STEPS IF NO NETWORK ACTIVITY]");
    console.log("1. Use Task Manager to find all Kiro processes");
    console.log("2. Look for processes with high network usage");
    console.log("3. Try attaching to different PIDs");
    console.log("4. Or use system-wide monitoring (Wireshark)");
}, 3000);

send({
    type: 'send',
    payload: 'SUCCESS: Renderer process analysis completed'
});