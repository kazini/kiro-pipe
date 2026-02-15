/**
 * Diagnose Networking - Find which modules/APIs Kiro actually uses
 */

console.log("[*] Networking Diagnostics - Finding actual networking stack");

// Check what modules are loaded
console.log("\n[PHASE 1] Enumerating loaded modules...");

const modules = Process.enumerateModules();
console.log(`Total modules loaded: ${modules.length}`);

// Look for networking-related modules
const networkModules = [];
const networkKeywords = ['http', 'net', 'ssl', 'tls', 'socket', 'curl', 'wininet', 'winhttp', 'ws2_32', 'crypt', 'schannel'];

for (const mod of modules) {
    const name = mod.name.toLowerCase();
    for (const keyword of networkKeywords) {
        if (name.includes(keyword)) {
            networkModules.push(mod);
            break;
        }
    }
}

console.log(`\nNetwork-related modules found: ${networkModules.length}`);
for (const mod of networkModules) {
    console.log(`  ${mod.name} (${mod.path})`);
}

// Check for specific Windows networking DLLs
console.log("\n[PHASE 2] Checking for Windows networking DLLs...");

const targetDLLs = ['winhttp.dll', 'wininet.dll', 'ws2_32.dll', 'crypt32.dll', 'schannel.dll'];
for (const dllName of targetDLLs) {
    const mod = Process.findModuleByName(dllName);
    if (mod) {
        console.log(`  ✓ ${dllName} loaded at ${mod.base}`);
        
        // Try to find key functions
        const keyFuncs = ['WinHttpSendRequest', 'WinHttpConnect', 'HttpSendRequestA', 'InternetReadFile', 'send', 'recv'];
        for (const funcName of keyFuncs) {
            try {
                const funcAddr = Module.getExportByName(dllName, funcName);
                if (funcAddr) {
                    console.log(`    → ${funcName} found at ${funcAddr}`);
                }
            } catch (e) {
                // Function not in this DLL
            }
        }
    } else {
        console.log(`  ✗ ${dllName} not loaded`);
    }
}

// Check if we're in a renderer process
console.log("\n[PHASE 3] Checking process type...");

try {
    if (typeof window !== 'undefined') {
        console.log("  ✓ This IS a renderer process (has window object)");
        console.log(`    window.location: ${window.location}`);
        
        // Check for browser APIs
        if (typeof XMLHttpRequest !== 'undefined') {
            console.log("    ✓ XMLHttpRequest available");
        }
        if (typeof fetch !== 'undefined') {
            console.log("    ✓ fetch available");
        }
        if (typeof WebSocket !== 'undefined') {
            console.log("    ✓ WebSocket available");
        }
    } else {
        console.log("  ✗ This is NOT a renderer process (no window object)");
        console.log("    This is likely the main process or a utility process");
    }
} catch (e) {
    console.log(`  ⚠️ Could not determine process type: ${e.message}`);
}

// Try to find ANY networking function
console.log("\n[PHASE 4] Searching for networking functions globally...");

const networkFuncs = [
    'WinHttpSendRequest', 'WinHttpConnect', 'WinHttpOpenRequest',
    'HttpSendRequestA', 'HttpSendRequestW', 'InternetReadFile',
    'send', 'recv', 'connect', 'WSASend', 'WSARecv'
];

let foundFuncs = 0;
for (const funcName of networkFuncs) {
    try {
        const funcAddr = Module.getExportByName(null, funcName);
        if (funcAddr) {
            console.log(`  ✓ ${funcName} found at ${funcAddr}`);
            foundFuncs++;
        }
    } catch (e) {
        // Not found
    }
}

if (foundFuncs === 0) {
    console.log("  ✗ No standard Windows networking functions found!");
    console.log("  This process likely uses:");
    console.log("    - Chromium's internal networking (renderer process)");
    console.log("    - Or a custom networking stack");
}

console.log("\n" + "=".repeat(70));
console.log("[DIAGNOSIS COMPLETE]");
console.log("=".repeat(70));

send({
    type: 'send',
    payload: 'Diagnostics complete - check output above'
});