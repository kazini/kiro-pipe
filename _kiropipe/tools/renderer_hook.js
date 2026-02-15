/**
 * Renderer Process Hook for Kiro
 * Targets browser APIs in Chromium renderer processes
 */

console.log("[*] Renderer Hook Loading...");
console.log("[*] Targeting browser APIs in renderer process");

// Track activity
let activity = {
    startTime: Date.now(),
    totalCalls: 0,
    byType: {},
    destinations: new Set(),
    requests: []
};

// Function to log activity
function logRequest(type, url, method, details = '') {
    activity.totalCalls++;
    activity.byType[type] = (activity.byType[type] || 0) + 1;
    
    if (url) {
        activity.destinations.add(url);
        
        // Check for Kiro/AWS endpoints
        if (url.includes('kiro.dev') || url.includes('amazonaws.com') || 
            url.includes('amazon.com') || url.includes('aws')) {
            console.log(`\n🎯 [${type.toUpperCase()}] ${method} ${url}`);
            if (details) console.log(`   ${details}`);
            
            // Store for analysis
            activity.requests.push({
                type: type,
                url: url,
                method: method,
                timestamp: Date.now(),
                details: details
            });
        } else {
            console.log(`\n[${type.toUpperCase()}] ${method} ${url}`);
            if (details) console.log(`   ${details}`);
        }
    } else {
        console.log(`\n[${type.toUpperCase()}] ${details}`);
    }
}

// Phase 1: Hook XMLHttpRequest (traditional AJAX)
console.log("\n[PHASE 1] Hooking XMLHttpRequest...");

try {
    // Get XMLHttpRequest constructor
    const XMLHttpRequest = ObjC.classes.XMLHttpRequest;
    
    if (XMLHttpRequest) {
        // Hook open method
        Interceptor.attach(XMLHttpRequest['- open:'].implementation, {
            onEnter: function(args) {
                try {
                    const method = ObjC.Object(args[2]).toString();
                    const url = ObjC.Object(args[3]).toString();
                    logRequest('xhr', url, method, 'XMLHttpRequest.open()');
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        // Hook send method
        Interceptor.attach(XMLHttpRequest['- send:'].implementation, {
            onEnter: function(args) {
                try {
                    // We can't get URL here easily, but we know a request is being sent
                    console.log(`[XHR-SEND] Request sent`);
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        console.log("  ✓ XMLHttpRequest hooks installed");
    } else {
        console.log("  ✗ XMLHttpRequest not found (not a renderer process?)");
    }
} catch (e) {
    console.log(`  ✗ XMLHttpRequest hook failed: ${e.message}`);
}

// Phase 2: Hook fetch API (modern)
console.log("\n[PHASE 2] Hooking fetch API...");

try {
    // Get global fetch function
    const fetchFunc = ObjC.classes.fetch;
    
    if (fetchFunc) {
        // This is tricky - fetch is a JavaScript function, not ObjC
        // We'll need a different approach
        console.log("  ⚠️ fetch is JavaScript function, need JS hooking");
    } else {
        console.log("  ⚠️ fetch not found as ObjC class");
    }
} catch (e) {
    console.log(`  ✗ fetch hook failed: ${e.message}`);
}

// Phase 3: Hook URL loading (NSURLSession, NSURLConnection)
console.log("\n[PHASE 3] Hooking URL loading APIs...");

try {
    // NSURLSession (modern)
    const NSURLSession = ObjC.classes.NSURLSession;
    if (NSURLSession) {
        // Hook dataTaskWithURL:completionHandler:
        Interceptor.attach(NSURLSession['- dataTaskWithURL:completionHandler:'].implementation, {
            onEnter: function(args) {
                try {
                    const url = ObjC.Object(args[2]).toString();
                    logRequest('nsurlsession', url, 'GET', 'NSURLSession.dataTaskWithURL');
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        // Hook dataTaskWithRequest:completionHandler:
        Interceptor.attach(NSURLSession['- dataTaskWithRequest:completionHandler:'].implementation, {
            onEnter: function(args) {
                try {
                    const request = ObjC.Object(args[2]);
                    const url = request.URL().toString();
                    const method = request.HTTPMethod() || 'GET';
                    logRequest('nsurlsession', url, method, 'NSURLSession.dataTaskWithRequest');
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        console.log("  ✓ NSURLSession hooks installed");
    }
} catch (e) {
    console.log(`  ✗ URL loading hooks failed: ${e.message}`);
}

// Phase 4: Hook WebSocket connections
console.log("\n[PHASE 4] Hooking WebSocket...");

try {
    const WebSocket = ObjC.classes.WebSocket;
    if (WebSocket) {
        // Hook initWithURL:
        Interceptor.attach(WebSocket['- initWithURL:'].implementation, {
            onEnter: function(args) {
                try {
                    const url = ObjC.Object(args[2]).toString();
                    logRequest('websocket', url, 'WS', 'WebSocket connection');
                } catch (e) {
                    // Silently fail
                }
            }
        });
        
        console.log("  ✓ WebSocket hooks installed");
    }
} catch (e) {
    console.log(`  ✗ WebSocket hook failed: ${e.message}`);
}

// Phase 5: JavaScript evaluation hook (to catch fetch calls)
console.log("\n[PHASE 5] Setting up JavaScript evaluation monitoring...");

try {
    // Hook JavaScript evaluation to catch fetch calls
    // This is more advanced and may not work in all cases
    console.log("  ⚠️ JavaScript evaluation monitoring would be complex");
} catch (e) {
    console.log(`  ✗ JavaScript monitoring failed: ${e.message}`);
}

// Summary
console.log("\n" + "=".repeat(70));
console.log("[RENDERER HOOK - READY]");
console.log("=".repeat(70));
console.log(`Monitoring browser APIs in renderer process`);
console.log(`\n[EXPECTED TO CATCH]:`);
console.log(`- XMLHttpRequest calls to kiro.dev, q.*.amazonaws.com`);
console.log(`- NSURLSession requests`);
console.log(`- WebSocket connections`);
console.log(`\n[INSTRUCTIONS]:`);
console.log(`1. Use Kiro's AI features`);
console.log(`2. Watch for 🎯 markers (Kiro/AWS endpoints)`);
console.log(`3. Check for any network activity`);

// Dashboard
setInterval(function() {
    const elapsed = Math.floor((Date.now() - activity.startTime) / 1000);
    
    console.log(`\n` + "=".repeat(70));
    console.log(`[RENDERER DASHBOARD] ${elapsed}s elapsed`);
    console.log("=".repeat(70));
    console.log(`Total API calls: ${activity.totalCalls}`);
    
    if (Object.keys(activity.byType).length > 0) {
        console.log(`\nBy type:`);
        for (const [type, count] of Object.entries(activity.byType)) {
            console.log(`  ${type}: ${count}`);
        }
    }
    
    console.log(`\nUnique destinations: ${activity.destinations.size}`);
    
    if (activity.destinations.size > 0) {
        console.log(`\nDestinations found:`);
        const destArray = Array.from(activity.destinations);
        for (let i = 0; i < Math.min(destArray.length, 10); i++) {
            const url = destArray[i];
            const isKiro = url.includes('kiro.dev') || url.includes('amazonaws.com');
            console.log(`  ${isKiro ? '🎯 ' : ''}${url}`);
        }
        if (destArray.length > 10) {
            console.log(`  ... and ${destArray.length - 10} more`);
        }
    }
    
    if (activity.totalCalls === 0) {
        console.log(`\n❌ NO BROWSER API CALLS DETECTED`);
        console.log(`Possible reasons:`);
        console.log(`  1. Wrong process (not a renderer)`);
        console.log(`  2. Different API usage pattern`);
        console.log(`  3. No network activity`);
    } else if (activity.destinations.size === 0) {
        console.log(`\n⚠️ API calls detected but no URLs captured`);
    } else {
        console.log(`\n✅ Browser API activity detected`);
    }
    
}, 10000);

console.log("\n[✓] Renderer hook loaded successfully");
console.log("[!] Monitoring browser APIs for 60+ seconds");

// Keep alive
setTimeout(function() {
    console.log("\n[INFO] Still monitoring...");
}, 60000);

send({
    type: 'send',
    payload: 'SUCCESS: Renderer hook loaded - monitoring browser APIs'
});