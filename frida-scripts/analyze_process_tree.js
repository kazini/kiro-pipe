/**
 * Analyze Process Tree - Map all Kiro processes and their relationships
 */

console.log("[*] Analyze Process Tree Loading...");
console.log("[*] Mapping all Kiro processes to find networking targets");

// We'll try to build a process tree
let processTree = {};

try {
    console.log("[STEP 1] Getting all processes on system...");
    
    // Note: Process.enumerateProcesses might not work in all Frida contexts
    // We'll try multiple approaches
    
    let allProcesses = [];
    
    // Approach 1: Try standard API
    try {
        if (typeof Process !== 'undefined' && Process.enumerateProcesses) {
            allProcesses = Process.enumerateProcesses();
            console.log(`[INFO] Found ${allProcesses.length} total processes via Process.enumerateProcesses`);
        }
    } catch (e) {
        console.log(`[WARNING] Process.enumerateProcesses failed: ${e.message}`);
    }
    
    // Approach 2: Try via command if available (Windows)
    if (allProcesses.length === 0) {
        console.log("[INFO] Trying alternative approach to get processes...");
        // We can't run commands from Frida JS, but we can try other methods
    }
    
    // Filter for Kiro processes
    const kiroProcesses = [];
    for (const proc of allProcesses) {
        if (proc.name && proc.name.toLowerCase().includes('kiro')) {
            kiroProcesses.push(proc);
        }
    }
    
    console.log(`\n[STEP 2] Found ${kiroProcesses.length} Kiro-related processes:`);
    
    // Display basic info
    for (const proc of kiroProcesses) {
        console.log(`  ${proc.name} (PID: ${proc.pid})`);
        
        // Try to get more info
        try {
            // Get module count as proxy for "size"
            const modules = Process.enumerateModules({pid: proc.pid});
            console.log(`    Modules: ${modules.length}`);
            
            // Check for network-related modules
            let networkModules = 0;
            for (const mod of modules) {
                const name = mod.name.toLowerCase();
                if (name.includes('http') || name.includes('wininet') || 
                    name.includes('ws2_32') || name.includes('crypt') ||
                    name.includes('ssl') || name.includes('net') ||
                    name.includes('socket') || name.includes('dns')) {
                    networkModules++;
                }
            }
            console.log(`    Network modules: ${networkModules}`);
            
            // Check for Chromium/Electron modules
            let chromiumModules = 0;
            for (const mod of modules) {
                const name = mod.name.toLowerCase();
                if (name.includes('chrome') || name.includes('chromium') || 
                    name.includes('electron') || name.includes('cef') ||
                    name.includes('blink') || name.includes('v8')) {
                    chromiumModules++;
                }
            }
            console.log(`    Chromium modules: ${chromiumModules}`);
            
        } catch (e) {
            console.log(`    Could not analyze modules: ${e.message}`);
        }
    }
    
    // Try to build process tree (we need parent PID info)
    console.log("\n[STEP 3] Attempting to build process tree...");
    
    // In Windows, we'd need to use different APIs to get parent PID
    // For now, we'll make educated guesses based on process characteristics
    
    // Categorize processes
    const categorized = {
        main: [],      // Likely main process
        renderer: [],  // Likely renderer processes
        utility: [],   // Utility processes (GPU, etc.)
        unknown: []    // Can't determine
    };
    
    for (const proc of kiroProcesses) {
        try {
            const modules = Process.enumerateModules({pid: proc.pid});
            let moduleNames = modules.map(m => m.name.toLowerCase());
            
            // Heuristic classification
            let isMain = false;
            let isRenderer = false;
            
            // Check for Node.js indicators (main process)
            for (const mod of modules) {
                if (mod.name.toLowerCase().includes('node.dll')) {
                    isMain = true;
                    break;
                }
            }
            
            // Check for browser indicators (renderer)
            for (const mod of modules) {
                if (mod.name.toLowerCase().includes('blink') || 
                    mod.name.toLowerCase().includes('chrome_child')) {
                    isRenderer = true;
                    break;
                }
            }
            
            // Check module count (renderers often have more modules)
            if (modules.length > 100 && !isMain) {
                isRenderer = true;
            }
            
            // Classify
            if (isMain) {
                categorized.main.push(proc);
                console.log(`  ${proc.pid} -> MAIN process (Node.js detected)`);
            } else if (isRenderer) {
                categorized.renderer.push(proc);
                console.log(`  ${proc.pid} -> RENDERER process (browser-like)`);
            } else if (modules.length < 50) {
                categorized.utility.push(proc);
                console.log(`  ${proc.pid} -> UTILITY process (small)`);
            } else {
                categorized.unknown.push(proc);
                console.log(`  ${proc.pid} -> UNKNOWN type`);
            }
            
        } catch (e) {
            categorized.unknown.push(proc);
            console.log(`  ${proc.pid} -> UNKNOWN (analysis failed)`);
        }
    }
    
    // Summary
    console.log("\n" + "=".repeat(60));
    console.log("[PROCESS TREE ANALYSIS SUMMARY]");
    console.log("=".repeat(60));
    console.log(`Total Kiro processes: ${kiroProcesses.length}`);
    console.log(`  Main processes: ${categorized.main.length}`);
    console.log(`  Renderer processes: ${categorized.renderer.length}`);
    console.log(`  Utility processes: ${categorized.utility.length}`);
    console.log(`  Unknown: ${categorized.unknown.length}`);
    
    // Recommendations
    console.log("\n[RECOMMENDATIONS FOR NETWORK HOOKING]");
    
    if (categorized.renderer.length > 0) {
        console.log("1. ✅ ATTACH TO RENDERER PROCESSES for networking:");
        for (const proc of categorized.renderer) {
            console.log(`   PID ${proc.pid} (${proc.name})`);
        }
        console.log("\n2. Renderer processes handle:");
        console.log("   - Web page rendering");
        console.log("   - JavaScript execution");
        console.log("   - fetch() / XMLHttpRequest calls");
        console.log("   - WebSocket connections");
        console.log("   - AWS Bedrock API calls (if using browser APIs)");
    } else {
        console.log("1. ⚠️ No clear renderer processes identified");
        console.log("2. Try attaching to all Kiro processes one by one");
    }
    
    if (categorized.main.length > 0) {
        console.log("\n3. Main process(es) found (what we've been attaching to):");
        for (const proc of categorized.main) {
            console.log(`   PID ${proc.pid} (${proc.name})`);
        }
        console.log("   - Handles app lifecycle");
        console.log("   - May do SOME networking via Node.js");
        console.log("   - But most AI/LLM calls in renderers");
    }
    
    // Next steps
    console.log("\n[NEXT STEPS]");
    console.log("1. For each renderer PID, run:");
    console.log('   python frida-scripts/attach.py --hook test_any_network --process <PID>');
    console.log("\n2. Or create a multi-attach script");
    console.log("\n3. In renderer, hook browser APIs:");
    console.log("   - window.fetch");
    console.log("   - XMLHttpRequest.prototype.open");
    console.log("   - WebSocket constructor");
    
    // If we can't get all processes, provide manual instructions
    if (kiroProcesses.length === 0) {
        console.log("\n[MANUAL PROCESS DISCOVERY INSTRUCTIONS]");
        console.log("1. Open Task Manager (Ctrl+Shift+Esc)");
        console.log("2. Go to Details tab");
        console.log("3. Look for all Kiro.exe processes");
        console.log("4. Note their PIDs");
        console.log("5. Try attaching to each with:");
        console.log('   python frida-scripts/attach.py --hook test_any_network --process <PID>');
        console.log("\n6. Look for processes with:");
        console.log("   - High memory usage (renderers)");
        console.log("   - Network activity when using AI features");
        console.log("   - Many loaded modules");
    }
    
} catch (e) {
    console.log("[ERROR] Process tree analysis failed:", e.message);
    console.log("[ERROR] Stack:", e.stack);
    
    // Fallback instructions
    console.log("\n[FALLBACK INSTRUCTIONS]");
    console.log("1. Use Windows Task Manager to find Kiro PIDs");
    console.log("2. Look for multiple Kiro.exe processes");
    console.log("3. The 'main' process is usually the first one");
    console.log("4. 'Renderer' processes have similar names but different PIDs");
    console.log("5. Try attaching to each PID until you see network activity");
}

// Create a simple test to run if we're in a renderer
console.log("\n[QUICK RENDERER TEST]");
console.log("If you attach to a renderer process, this script will:");
console.log("1. Check for window/document objects");
console.log("2. Hook fetch() and XMLHttpRequest");
console.log("3. Log all network requests");

// Quick check if we're in a renderer now
try {
    if (typeof window !== 'undefined') {
        console.log("\n🎯 CURRENTLY IN A RENDERER PROCESS!");
        console.log(`Window location: ${window.location.href}`);
        
        // Demo hooking
        console.log("\n[DEMO] Hooking browser APIs...");
        
        // Hook XMLHttpRequest
        if (typeof XMLHttpRequest !== 'undefined') {
            const OriginalXHR = XMLHttpRequest;
            XMLHttpRequest = function() {
                const xhr = new OriginalXHR();
                const originalOpen = xhr.open;
                xhr.open = function(method, url) {
                    console.log(`🎯 [XHR] ${method} ${url}`);
                    return originalOpen.apply(this, arguments);
                };
                return xhr;
            };
            console.log("✅ XMLHttpRequest hooked");
        }
        
        // Hook fetch
        if (typeof fetch !== 'undefined') {
            const originalFetch = fetch;
            window.fetch = function() {
                console.log(`🎯 [FETCH] ${arguments[0]}`);
                return originalFetch.apply(this, arguments);
            };
            console.log("✅ fetch() hooked");
        }
        
        console.log("\n✅ Ready to catch browser network requests!");
    } else {
        console.log("\n⚠️ Not in a renderer process (no window object)");
    }
} catch (e) {
    console.log(`\n⚠️ Renderer check failed: ${e.message}`);
}

console.log("\n[✓] Process Tree Analysis completed");

send({
    type: 'send',
    payload: 'SUCCESS: Process tree analysis completed - check recommendations above'
});