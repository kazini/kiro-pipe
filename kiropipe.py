#!/usr/bin/env python3
import subprocess
import sys
import time
import os
from pathlib import Path

# ============================================================
# DEPENDENCY CHECK
# ============================================================
def check_dependencies():
    """Check and install/upgrade dependencies from requirements.txt"""
    requirements_file = Path(__file__).parent / "_kiropipe" / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"WARNING: requirements.txt not found at {requirements_file}")
        return
    
    print("Checking dependencies...")
    
    try:
        import pkg_resources
        
        # Read requirements
        with open(requirements_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        missing = []
        outdated = []
        
        for requirement in requirements:
            if not requirement:
                continue
            
            try:
                pkg_resources.require(requirement)
            except pkg_resources.DistributionNotFound:
                missing.append(requirement)
            except pkg_resources.VersionConflict as e:
                outdated.append((requirement, str(e)))
        
        if missing or outdated:
            print("\n" + "="*60)
            print("DEPENDENCY ISSUES DETECTED")
            print("="*60)
            
            if missing:
                print("\nMissing packages:")
                for pkg in missing:
                    print(f"  - {pkg}")
            
            if outdated:
                print("\nOutdated packages:")
                for pkg, error in outdated:
                    print(f"  - {pkg}")
                    print(f"    {error}")
            
            print("\nOptions:")
            print("  1. Auto-install/upgrade all packages")
            print("  2. Show manual install commands and exit")
            print("  3. Continue anyway (may cause errors)")
            
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == '1':
                print("\nInstalling/upgrading packages...")
                try:
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install', '--upgrade',
                        '-r', str(requirements_file)
                    ])
                    print("\n[OK] All dependencies installed successfully!")
                    print("Please restart the script.\n")
                    sys.exit(0)
                except subprocess.CalledProcessError as e:
                    print(f"\n[ERROR] Failed to install dependencies: {e}")
                    print("Please install manually and try again.")
                    sys.exit(1)
            
            elif choice == '2':
                print("\nTo fix, run:")
                print(f"  pip install -r {requirements_file}")
                print("\nOr install/upgrade individually:")
                for pkg in missing + [p for p, _ in outdated]:
                    print(f"  pip install --upgrade {pkg}")
                print()
                sys.exit(1)
            
            elif choice == '3':
                print("\nContinuing without fixing dependencies...")
                print("Warning: This may cause errors!\n")
            
            else:
                print("\nInvalid choice. Exiting.")
                sys.exit(1)
        
        else:
            print("All dependencies satisfied.\n")
        
    except ImportError:
        print("WARNING: pkg_resources not available, skipping dependency check")
    except Exception as e:
        print(f"WARNING: Dependency check failed: {e}")

# Check dependencies before importing anything else
check_dependencies()

from mitmproxy import http
from mitmproxy.tools.main import mitmdump
import json
import threading

"""
KiroPipe || Proxies Kiro and enables custom API use.
> Uses _kiropipe folder.
Usage: python kiropipe.py [port]

Configuration: Edit _kiropipe/kiropipe_config.yaml
"""
#
# ============================================================
# HARDCODED DEFAULTS (overridden by config file if present)
# ============================================================
DEFAULT_PORT = 29974
KIRO_EXE_PATH = None  # Set to custom path or None to auto-detect
ALLOW_TELEMETRY = False  # FALSE = block
ALLOW_UPDATES = False  # FALSE = block
FORCE_TOGGLE_USAGE_LIMITS = None  # None=auto, True=always allow, False=always block
DEBUG_MODE_ENABLED = True  # Show detailed output
DEBUG_STORE_INTERACTION_BLOCKS = False  # Save requests/responses to files
ALLOW_KIRO_MODELS = True  # TRUE = allow Kiro's default models
# ============================================================
#
#
#
#
#
#
#
#

# Setup directories
SCRIPT_DIR = Path(__file__).parent  # Base directory (where kiropipe.py is)
KIROPIPE_DIR = SCRIPT_DIR / "_kiropipe"  # Module directory
DEBUG_DIR = KIROPIPE_DIR / "debug_logs" / "interactions"
RESPONSES_DIR = DEBUG_DIR / "responses"
POSTED_DIR = DEBUG_DIR / "posted"

# Injection queue file (after KIROPIPE_DIR is defined)
INJECTION_QUEUE_FILE = KIROPIPE_DIR / "debug_logs" / ".injection_queue.json"

# Add _kiropipe to Python path for module imports
sys.path.insert(0, str(KIROPIPE_DIR))

# Load configuration
from engine.config_loader import load_config
CONFIG = load_config(KIROPIPE_DIR / 'kiropipe_config.yaml')

# Override hardcoded values with config file values
DEFAULT_PORT = CONFIG.get('proxy.port', DEFAULT_PORT)
KIRO_EXE_PATH = CONFIG.get('kiro.exe_path', KIRO_EXE_PATH)
ALLOW_TELEMETRY = CONFIG.get('kiro_endpoint.telemetry', ALLOW_TELEMETRY)
ALLOW_UPDATES = CONFIG.get('kiro_endpoint.updates', ALLOW_UPDATES)
FORCE_TOGGLE_USAGE_LIMITS = CONFIG.get('kiro_endpoint.force_toggle_usage_limits', FORCE_TOGGLE_USAGE_LIMITS)
DEBUG_MODE_ENABLED = CONFIG.get('debug.debug_mode_enabled', DEBUG_MODE_ENABLED)
DEBUG_STORE_INTERACTION_BLOCKS = CONFIG.get('debug.store_interaction_blocks', DEBUG_STORE_INTERACTION_BLOCKS)
ALLOW_KIRO_MODELS = CONFIG.get('kiro_endpoint.models', ALLOW_KIRO_MODELS)

# Current model being used (for dynamic usage limits)
CURRENT_MODEL = CONFIG.get_default_model()

if DEBUG_STORE_INTERACTION_BLOCKS:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)
# Add _kiropipe to Python path for module imports (moved before config loading)
sys.path.insert(0, str(KIROPIPE_DIR))

# Load configuration
from engine.config_loader import load_config
CONFIG = load_config(KIROPIPE_DIR / 'kiropipe_config.yaml')

# Override hardcoded values with config file values
DEFAULT_PORT = CONFIG.get('proxy.port', DEFAULT_PORT)
KIRO_EXE_PATH = CONFIG.get('kiro.exe_path', KIRO_EXE_PATH)
ALLOW_TELEMETRY = CONFIG.get('kiro_endpoint.telemetry', ALLOW_TELEMETRY)
ALLOW_UPDATES = CONFIG.get('kiro_endpoint.updates', ALLOW_UPDATES)
FORCE_TOGGLE_USAGE_LIMITS = CONFIG.get('kiro_endpoint.force_toggle_usage_limits', FORCE_TOGGLE_USAGE_LIMITS)
DEBUG_MODE_ENABLED = CONFIG.get('debug.debug_mode_enabled', DEBUG_MODE_ENABLED)
DEBUG_STORE_INTERACTION_BLOCKS = CONFIG.get('debug.store_interaction_blocks', DEBUG_STORE_INTERACTION_BLOCKS)
ALLOW_KIRO_MODELS = CONFIG.get('kiro_endpoint.models', ALLOW_KIRO_MODELS)

# Current model being used (for dynamic usage limits)
CURRENT_MODEL = CONFIG.get_default_model()

if DEBUG_STORE_INTERACTION_BLOCKS:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to_file = DEBUG_STORE_INTERACTION_BLOCKS
        self.telemetry_blocked = 0
        self.current_model = CURRENT_MODEL

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1
        
        # Block telemetry if not allowed
        if not ALLOW_TELEMETRY and 'telemetry' in flow.request.pretty_host:
            self.telemetry_blocked += 1
            if DEBUG_MODE_ENABLED:
                print(f"\n[BLOCKED TELEMETRY #{self.telemetry_blocked}] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"status":"ok"}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block update checks if not allowed
        if not ALLOW_UPDATES and 'metadata-win32' in flow.request.path:
            if DEBUG_MODE_ENABLED:
                print(f"\n[BLOCKED UPDATE CHECK] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"currentRelease":"0.9.40","releases":[]}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Dynamic usage limits blocking
        should_block_limits = CONFIG.should_block_usage_limits(self.current_model)
        if should_block_limits and 'getUsageLimits' in flow.request.path:
            if DEBUG_MODE_ENABLED:
                print(f"\n[BLOCKED USAGE LIMITS] {flow.request.pretty_url}")
                print(f"  Current model: {self.current_model}")
            flow.response = http.Response.make(
                200,
                b'{"limits":[],"subscriptionInfo":{"type":"FREE"}}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block Kiro models if not allowed
        if not ALLOW_KIRO_MODELS and 'generateAssistantResponse' in flow.request.path:
            # Check if we have any custom providers enabled
            custom_providers = [p for p in CONFIG.get_enabled_providers() if p != 'kiro']
            
            if not custom_providers:
                if DEBUG_MODE_ENABLED:
                    print(f"\n[ERROR] Kiro models blocked but no custom providers enabled!")
                    print(f"  Enable a custom provider in config or set kiro_endpoint.models: true")
                flow.response = http.Response.make(
                    503,
                    b'{"error":"Kiro models blocked and no custom providers configured"}',
                    {"Content-Type": "application/json"}
                )
                return
            
            # Forward to custom provider (handled below)
            if DEBUG_MODE_ENABLED:
                print(f"\n[KIRO MODELS BLOCKED] Forwarding to custom provider")
        
        # Check if request should be allowed (all blocking enabled = nothing through)
        if not CONFIG.should_allow_request(flow.request.path, self.current_model):
            if DEBUG_MODE_ENABLED:
                print(f"\n[BLOCKED ALL] All traffic blocked by configuration")
                print(f"  Telemetry: {ALLOW_TELEMETRY}, Updates: {ALLOW_UPDATES}")
                print(f"  Kiro models: {ALLOW_KIRO_MODELS}, Usage limits: {should_block_limits}")
            flow.response = http.Response.make(
                503,
                b'{"error":"All traffic blocked by configuration"}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Route to custom provider if not using Kiro passthrough
        if 'generateAssistantResponse' in flow.request.path:
            model_info = CONFIG.get_model_info(self.current_model)
            
            if model_info and model_info['provider'] != 'kiro':
                # Forward to custom provider
                provider_name = model_info['provider']
                provider_config = CONFIG.get_provider_config(provider_name)
                
                if DEBUG_MODE_ENABLED:
                    print(f"\n[CUSTOM PROVIDER] Routing to {provider_name}")
                    print(f"  Model: {model_info['model']['name']}")
                
                try:
                    import httpx
                    
                    # Get bridge URL from provider config or use default
                    bridge_url = provider_config.get('bridge_url', 'http://localhost:8000')
                    
                    # Forward request to bridge with streaming
                    with httpx.Client(timeout=300.0) as client:
                        bridge_response = client.post(
                            f"{bridge_url}/generateAssistantResponse",
                            content=flow.request.content,
                            headers={
                                'Content-Type': 'application/json',
                                'X-Model': self.current_model  # Pass model to bridge
                            }
                        )
                        
                        # Create response with bridge data
                        flow.response = http.Response.make(
                            bridge_response.status_code,
                            bridge_response.content,
                            dict(bridge_response.headers)
                        )
                        
                        if DEBUG_MODE_ENABLED:
                            print(f"[CUSTOM PROVIDER] Response received: {bridge_response.status_code} ({len(bridge_response.content)} bytes)")
                        
                        return
                    
                except Exception as e:
                    if DEBUG_MODE_ENABLED:
                        print(f"[CUSTOM PROVIDER] Error: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # Return error response
                    flow.response = http.Response.make(
                        503,
                        json.dumps({'error': f'Custom provider error: {str(e)}'}).encode(),
                        {"Content-Type": "application/json"}
                    )
                    return
        
        # Check for injected responses (no flag needed - just check if queue exists)
        if 'generateAssistantResponse' in flow.request.path and INJECTION_QUEUE_FILE.exists():
            try:
                # Read the queue
                queue_data = json.loads(INJECTION_QUEUE_FILE.read_text())
                
                if queue_data and len(queue_data) > 0:
                    # Get the first item from queue
                    injection = queue_data.pop(0)
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"\n[INJECT] Using queued response")
                        print(f"[INJECT] Message: {injection.get('text', 'unknown')}")
                    
                    # Get the binary data (it's base64 encoded in the queue)
                    import base64
                    injected_binary = base64.b64decode(injection['binary'])
                    
                    # Create response
                    flow.response = http.Response.make(
                        200,
                        injected_binary,
                        {
                            'Content-Type': 'application/vnd.amazon.eventstream',
                            'x-amzn-RequestId': 'injected-response-123'
                        }
                    )
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"[INJECT] Injected {len(injected_binary)} bytes")
                        if injection.get('include_tool'):
                            print(f"[INJECT] Includes tool call")
                    
                    # Update the queue file (remove the used injection)
                    if len(queue_data) > 0:
                        INJECTION_QUEUE_FILE.write_text(json.dumps(queue_data, indent=2))
                        if DEBUG_MODE_ENABLED:
                            print(f"[INJECT] {len(queue_data)} injection(s) remaining in queue")
                    else:
                        INJECTION_QUEUE_FILE.unlink()
                        if DEBUG_MODE_ENABLED:
                            print(f"[INJECT] Queue empty, file deleted")
                    
                    return
                
            except Exception as e:
                if DEBUG_MODE_ENABLED:
                    print(f"[INJECT] Error reading queue: {e}")
                    import traceback
                    traceback.print_exc()
                # Fall through to normal AWS Q request if injection fails
                pass


        # Check if it's an AWS Q request
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            self.aws_requests.append({
                'url': flow.request.pretty_url,
                'method': flow.request.method,
                'host': flow.request.pretty_host,
                'path': flow.request.path
            })

            if DEBUG_MODE_ENABLED:
                print(f"\n{'='*60}")
                print(f"[AWS REQUEST #{len(self.aws_requests)}]")
                print(f"{'='*60}")
                print(f"Method: {flow.request.method}")
                print(f"Host: {flow.request.pretty_host}")
                print(f"Path: {flow.request.path}")
                print(f"URL: {flow.request.pretty_url}")

                # Print headers
                print(f"\nHeaders:")
                for k, v in flow.request.headers.items():
                    if k.lower() in ['authorization', 'x-amz-target', 'content-type', 'user-agent']:
                        print(f"  {k}: {v}")

            # Print and save body if present
            if flow.request.content:
                try:
                    body = flow.request.text
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"\nBody ({len(flow.request.content)} bytes):")
                        # Try to parse as JSON for pretty printing
                        try:
                            body_json = json.loads(body)
                            body_str = json.dumps(body_json, indent=2)
                            if len(body_str) > 1000:
                                print(f"  {body_str[:1000]}...")
                            else:
                                print(f"  {body_str}")
                        except:
                            # Not JSON, print as text
                            if len(body) > 500:
                                print(f"  {body[:500]}...")
                            else:
                                print(f"  {body}")
                    
                    # Save to file in debug mode
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = POSTED_DIR / f'request_{len(self.aws_requests)}.json'
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump({
                                'type': 'request',
                                'url': flow.request.pretty_url,
                                'headers': dict(flow.request.headers),
                                'body': body
                            }, f, indent=2)
                except:
                    if DEBUG_MODE_ENABLED:
                        print(f"  [Binary content]")

            if DEBUG_MODE_ENABLED:
                print(f"{'='*60}\n")

    def response(self, flow: http.HTTPFlow) -> None:
        """Intercept all responses"""
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            if DEBUG_MODE_ENABLED:
                print(f"\n{'='*60}")
                print(f"[AWS RESPONSE]")
                print(f"{'='*60}")
                print(f"Status: {flow.response.status_code}")
                print(f"URL: {flow.request.pretty_url}")
                
                # Print response headers
                print(f"\nResponse Headers:")
                for k, v in flow.response.headers.items():
                    if k.lower() in ['content-type', 'content-encoding', 'content-length', 'x-amzn-requestid']:
                        print(f"  {k}: {v}")

            if flow.response.content:
                if DEBUG_MODE_ENABLED:
                    print(f"\nResponse Body ({len(flow.response.content)} bytes):")
                
                # Try multiple decoding strategies
                decoded = False
                
                # Strategy 1: Try as text/JSON
                try:
                    text = flow.response.text
                    # Try to parse as JSON
                    try:
                        response_json = json.loads(text)
                        if DEBUG_MODE_ENABLED:
                            response_str = json.dumps(response_json, indent=2)
                            if len(response_str) > 1000:
                                print(f"  [JSON] {response_str[:1000]}...")
                            else:
                                print(f"  [JSON] {response_str}")
                        decoded = True
                        
                        # Save to file
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.json'
                            with open(filename, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'type': 'response',
                                    'url': flow.request.pretty_url,
                                    'status': flow.response.status_code,
                                    'headers': dict(flow.response.headers),
                                    'body': response_json
                                }, f, indent=2)
                    except:
                        # Not JSON, but is text
                        if DEBUG_MODE_ENABLED:
                            if len(text) > 500:
                                print(f"  [TEXT] {text[:500]}...")
                            else:
                                print(f"  [TEXT] {text}")
                        decoded = True
                        
                        # Save raw text
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.txt'
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(text)
                except Exception as e:
                    pass
                
                # Strategy 2: Check if it's event-stream (streaming response)
                if not decoded and 'text/event-stream' in flow.response.headers.get('content-type', ''):
                    try:
                        text = flow.response.content.decode('utf-8')
                        if DEBUG_MODE_ENABLED:
                            print(f"  [EVENT-STREAM]")
                            lines = text.split('\n')[:20]  # First 20 lines
                            for line in lines:
                                print(f"    {line}")
                            if len(text.split('\n')) > 20:
                                print(f"    ... ({len(text.split('\n'))} total lines)")
                        decoded = True
                        
                        # Save event-stream to file
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}_stream.txt'
                            with open(filename, 'w', encoding='utf-8') as f:
                                f.write(text)
                    except:
                        pass
                
                # Strategy 3: Binary/unknown
                if not decoded:
                    if DEBUG_MODE_ENABLED:
                        print(f"  [BINARY] First 100 bytes (hex):")
                        hex_data = flow.response.content[:100].hex()
                        print(f"    {hex_data}")
                    
                    # Try to identify format
                    if flow.response.content[:2] == b'\x1f\x8b':
                        if DEBUG_MODE_ENABLED:
                            print(f"  Format: GZIP compressed")
                        try:
                            import gzip
                            decompressed = gzip.decompress(flow.response.content)
                            if DEBUG_MODE_ENABLED:
                                print(f"  Decompressed ({len(decompressed)} bytes):")
                                decompressed_text = decompressed[:500].decode('utf-8', errors='ignore')
                                print(f"    {decompressed_text}")
                            
                            # Save decompressed to file
                            if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                                filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}_gzip.txt'
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(decompressed.decode('utf-8', errors='ignore'))
                        except Exception as e:
                            if DEBUG_MODE_ENABLED:
                                print(f"  Failed to decompress: {e}")
                    
                    # Save binary to file
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.bin'
                        with open(filename, 'wb') as f:
                            f.write(flow.response.content)
                        if DEBUG_MODE_ENABLED:
                            print(f"  Saved binary to: {filename.name}")
            
            if DEBUG_MODE_ENABLED:
                print(f"{'='*60}\n")

addons = [KiroInterceptor()]

def find_kiro_exe():
    """Find Kiro.exe - check custom path, then auto-detect"""
    if KIRO_EXE_PATH:
        kiro_exe = Path(KIRO_EXE_PATH)
        if kiro_exe.exists():
            return kiro_exe
        print(f"WARNING: Custom KIRO_EXE_PATH not found: {KIRO_EXE_PATH}")
    
    # Auto-detect: look in same directory as script (base directory)
    script_dir = Path(__file__).parent
    
    # Option 1: Kiro/Kiro.exe (subfolder)
    kiro_exe = script_dir / "Kiro" / "Kiro.exe"
    if kiro_exe.exists():
        return kiro_exe
    
    # Option 2: Kiro.exe (same folder as script)
    kiro_exe = script_dir / "Kiro.exe"
    if kiro_exe.exists():
        return kiro_exe
    
    # Option 3: Try from current working directory
    kiro_exe = Path("Kiro") / "Kiro.exe"
    if kiro_exe.exists():
        return kiro_exe
    
    # Option 4: Current working directory
    kiro_exe = Path("Kiro.exe")
    if kiro_exe.exists():
        return kiro_exe
    
    return None

def kill_existing_launcher():
    """Kill any existing kiropipe.py processes (except this one)"""
    try:
        current_pid = os.getpid()
        result = subprocess.run(['wmic', 'process', 'where', 
                               'name="python.exe"', 'get', 'processid,commandline'],
                              capture_output=True, text=True)
        
        for line in result.stdout.split('\n'):
            if 'kiropipe.py' in line and str(current_pid) not in line:
                # Extract PID
                parts = line.strip().split()
                if parts:
                    try:
                        pid = parts[-1]
                        print(f"Existing kiropipe.py instance found (PID: {pid}). Terminating...")
                        subprocess.run(['taskkill', '/F', '/PID', pid], 
                                     capture_output=True)
                        time.sleep(1)
                        print("Existing launcher terminated.\n")
                        return True
                    except:
                        pass
    except Exception as e:
        print(f"Warning: Could not check for existing launcher: {e}")
    return False

def wait_for_kiro_window(timeout=10):
    """Wait for Kiro window to appear and return its PID"""
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Look for Kiro.exe processes with a window
            result = subprocess.run(
                ['powershell', '-Command', 
                 'Get-Process | Where-Object {$_.ProcessName -eq "Kiro" -and $_.MainWindowTitle -ne ""} | Select-Object -ExpandProperty Id'],
                capture_output=True, text=True, timeout=2
            )
            
            if result.stdout.strip():
                pids = [int(pid.strip()) for pid in result.stdout.strip().split('\n') if pid.strip().isdigit()]
                if pids:
                    return pids[0]  # Return first Kiro window PID
        except:
            pass
        
        time.sleep(0.5)
    
    return None

def monitor_kiro_process(pid):
    """Monitor a specific Kiro process by PID"""
    import psutil
    
    try:
        process = psutil.Process(pid)
        print(f"Monitoring Kiro process (PID: {pid})...\n")
        
        # Wait for process to terminate
        process.wait()
        
        print(f"\n{'='*60}")
        print("Kiro closed")
        print(f"{'='*60}\n")
        
        # Exit the entire process
        os._exit(0)
        
    except psutil.NoSuchProcess:
        print(f"\nKiro process (PID: {pid}) not found.")
        os._exit(1)
    except Exception as e:
        print(f"\nError monitoring Kiro: {e}")
        os._exit(1)

def launch_kiro(port, proxy_process=None):
    """Launch Kiro with proxy settings"""
    # Wait a bit for proxy to be ready
    time.sleep(3)
    
    # Find Kiro.exe
    kiro_exe = find_kiro_exe()
    
    if not kiro_exe:
        print(f"\nERROR: Kiro.exe not found!")
        print(f"Set KIRO_EXE_PATH at the top of this script, or place Kiro in:")
        print(f"  - {Path(__file__).parent / 'Kiro' / 'Kiro.exe'}")
        print(f"  - {Path('Kiro') / 'Kiro.exe'}")
        return
    
    # Find cli.js relative to Kiro.exe
    kiro_cli = kiro_exe.parent / "resources" / "app" / "out" / "cli.js"
    
    if not kiro_cli.exists():
        print(f"\nERROR: cli.js not found at {kiro_cli}")
        return
    
    print(f"\n{'='*60}")
    print(f"Launching Kiro from: {kiro_exe}")
    print(f"{'='*60}\n")
    
    # Set environment variables
    env = os.environ.copy()
    env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
    env['ELECTRON_IGNORE_CERTIFICATE_ERRORS'] = '1'
    env['VSCODE_DEV'] = ''
    env['ELECTRON_RUN_AS_NODE'] = '1'
    
    # Launch Kiro (non-blocking - it spawns child processes)
    try:
        subprocess.Popen([
            str(kiro_exe),
            str(kiro_cli),
            '--ignore-certificate-errors',
            f'--proxy-server=127.0.0.1:{port}'
        ], env=env)
        
        # Wait for the actual Kiro window to appear
        print("Waiting for Kiro window to appear...")
        kiro_pid = wait_for_kiro_window(timeout=15)
        
        if not kiro_pid:
            print("\nERROR: Kiro window did not appear within 15 seconds.")
            os._exit(1)
        
        print(f"Kiro window detected (PID: {kiro_pid})")
        
        # Monitor the actual Kiro window process
        monitor_kiro_process(kiro_pid)
        
    except Exception as e:
        print(f"\nError launching Kiro: {e}")
        os._exit(1)

if __name__ == "__main__":
    # Check dependencies first
    try:
        import mitmproxy
        from mitmproxy.tools.main import mitmdump
    except ImportError:
        print("\nERROR: mitmproxy not installed.")
        print("Install with: pip install mitmproxy")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    try:
        import psutil
    except ImportError:
        print("\nERROR: psutil not installed.")
        print("Install with: pip install psutil")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Get port from command line or use default
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = DEFAULT_PORT

    print("\n" + "="*60)
    print("KiroPipe - Unified Launcher")
    print("="*60)
    
    # Print configuration summary
    CONFIG.print_summary()
    
    print(f"Proxy Configuration:")
    print(f"  - Port: {port}")
    print(f"  - Certificate validation: DISABLED")
    print(f"  - Only Kiro traffic is proxied")
    
    print(f"\nKiro Endpoint (TRUE=allow, FALSE=block):")
    print(f"  - Telemetry: {'ALLOWED' if ALLOW_TELEMETRY else 'BLOCKED'}")
    print(f"  - Updates: {'ALLOWED' if ALLOW_UPDATES else 'BLOCKED'}")
    print(f"  - Kiro models: {'ALLOWED' if ALLOW_KIRO_MODELS else 'BLOCKED'}")
    
    # Show usage limits status
    usage_limits_status = "AUTO (dynamic)"
    if FORCE_TOGGLE_USAGE_LIMITS is True:
        usage_limits_status = "ALWAYS ALLOWED"
    elif FORCE_TOGGLE_USAGE_LIMITS is False:
        usage_limits_status = "ALWAYS BLOCKED"
    print(f"  - Usage limits: {usage_limits_status}")
    
    print(f"\nCurrent Model: {CURRENT_MODEL}")
    model_info = CONFIG.get_model_info(CURRENT_MODEL)
    if model_info:
        print(f"  Provider: {model_info['provider']}")
        print(f"  Description: {model_info['model'].get('description', 'N/A')}")
    
    if DEBUG_MODE_ENABLED:
        print(f"\nDebug:")
        print(f"  - Console logging: ENABLED")
        print(f"  - Store interaction blocks: {'ENABLED' if DEBUG_STORE_INTERACTION_BLOCKS else 'DISABLED'}")
        if DEBUG_STORE_INTERACTION_BLOCKS:
            print(f"  - Files saved to: {DEBUG_DIR}")
    
    print("\nNote: Edit _kiropipe/kiropipe_config.yaml to change settings")
    print("="*60 + "\n")
    
    # Kill any existing launcher instances first
    kill_existing_launcher()
    
    # Start Kiro in a separate thread
    kiro_thread = threading.Thread(target=lambda: launch_kiro(port, None), daemon=False)
    kiro_thread.start()
    
    # Run mitmproxy in main thread (this blocks until proxy stops)
    try:
        sys.argv = ['mitmdump', '-s', __file__, '--listen-port', str(port)]
        mitmdump()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    
    print("Proxy stopped. Waiting for cleanup...")
    kiro_thread.join(timeout=5)
    print("Cleanup complete.")

    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to_file = True

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1

        # Check if it's an AWS Q request
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            self.aws_requests.append({
                'url': flow.request.pretty_url,
                'method': flow.request.method,
                'host': flow.request.pretty_host,
                'path': flow.request.path
            })

            print(f"\n{'='*60}")
            print(f"[AWS REQUEST #{len(self.aws_requests)}]")
            print(f"{'='*60}")
            print(f"Method: {flow.request.method}")
            print(f"Host: {flow.request.pretty_host}")
            print(f"Path: {flow.request.path}")
            print(f"URL: {flow.request.pretty_url}")

            # Print headers
            print(f"\nHeaders:")
            for k, v in flow.request.headers.items():
                if k.lower() in ['authorization', 'x-amz-target', 'content-type', 'user-agent']:
                    print(f"  {k}: {v}")

            # Print body if present
            if flow.request.content:
                print(f"\nBody ({len(flow.request.content)} bytes):")
                try:
                    body = flow.request.text
                    # Try to parse as JSON for pretty printing
                    try:
                        body_json = json.loads(body)
                        body_str = json.dumps(body_json, indent=2)
                        if len(body_str) > 1000:
                            print(f"  {body_str[:1000]}...")
                        else:
                            print(f"  {body_str}")
                    except:
                        # Not JSON, print as text
                        if len(body) > 500:
                            print(f"  {body[:500]}...")
                        else:
                            print(f"  {body}")
                    
                    # Save to file
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        with open('captured_requests.jsonl', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({
                                'type': 'request',
                                'url': flow.request.pretty_url,
                                'headers': dict(flow.request.headers),
                                'body': body
                            }) + '\n')
                except:
                    print(f"  [Binary content]")

            print(f"{'='*60}\n")

    def response(self, flow: http.HTTPFlow) -> None:
        """Intercept all responses"""
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            print(f"\n{'='*60}")
            print(f"[AWS RESPONSE]")
            print(f"{'='*60}")
            print(f"Status: {flow.response.status_code}")
            print(f"URL: {flow.request.pretty_url}")
            
            # Print response headers
            print(f"\nResponse Headers:")
            for k, v in flow.response.headers.items():
                if k.lower() in ['content-type', 'content-encoding', 'content-length', 'x-amzn-requestid']:
                    print(f"  {k}: {v}")

            if flow.response.content:
                print(f"\nResponse Body ({len(flow.response.content)} bytes):")
                
                # Try multiple decoding strategies
                decoded = False
                
                # Strategy 1: Try as text/JSON
                try:
                    text = flow.response.text
                    # Try to parse as JSON
                    try:
                        response_json = json.loads(text)
                        response_str = json.dumps(response_json, indent=2)
                        if len(response_str) > 1000:
                            print(f"  [JSON] {response_str[:1000]}...")
                        else:
                            print(f"  [JSON] {response_str}")
                        decoded = True
                        
                        # Save to file
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            with open('captured_responses.jsonl', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({
                                    'type': 'response',
                                    'url': flow.request.pretty_url,
                                    'status': flow.response.status_code,
                                    'headers': dict(flow.response.headers),
                                    'body': response_json
                                }) + '\n')
                    except:
                        # Not JSON, but is text
                        if len(text) > 500:
                            print(f"  [TEXT] {text[:500]}...")
                        else:
                            print(f"  [TEXT] {text}")
                        decoded = True
                        
                        # Save raw text
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            with open('captured_responses.jsonl', 'a', encoding='utf-8') as f:
                                f.write(json.dumps({
                                    'type': 'response',
                                    'url': flow.request.pretty_url,
                                    'status': flow.response.status_code,
                                    'headers': dict(flow.response.headers),
                                    'body': text
                                }) + '\n')
                except Exception as e:
                    pass
                
                # Strategy 2: Check if it's event-stream (streaming response)
                if not decoded and 'text/event-stream' in flow.response.headers.get('content-type', ''):
                    try:
                        text = flow.response.content.decode('utf-8')
                        print(f"  [EVENT-STREAM]")
                        lines = text.split('\n')[:20]  # First 20 lines
                        for line in lines:
                            print(f"    {line}")
                        if len(text.split('\n')) > 20:
                            print(f"    ... ({len(text.split('\n'))} total lines)")
                        decoded = True
                    except:
                        pass
                
                # Strategy 3: Binary/unknown
                if not decoded:
                    print(f"  [BINARY] First 100 bytes (hex):")
                    hex_data = flow.response.content[:100].hex()
                    print(f"    {hex_data}")
                    
                    # Try to identify format
                    if flow.response.content[:2] == b'\x1f\x8b':
                        print(f"  Format: GZIP compressed")
                        try:
                            import gzip
                            decompressed = gzip.decompress(flow.response.content)
                            print(f"  Decompressed ({len(decompressed)} bytes):")
                            print(f"    {decompressed[:500].decode('utf-8', errors='ignore')}")
                        except Exception as e:
                            print(f"  Failed to decompress: {e}")
                    
                    # Save binary to file
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = f'response_binary_{len(self.aws_requests)}.bin'
                        with open(filename, 'wb') as f:
                            f.write(flow.response.content)
                        print(f"  Saved to: {filename}")
            
            print(f"{'='*60}\n")

addons = [KiroInterceptor()]

def launch_kiro(port):
    """Launch Kiro with proxy settings"""
    # Wait for proxy to be ready
    time.sleep(2)
    
    # Find Kiro.exe
    script_dir = Path(__file__).parent.parent
    kiro_exe = script_dir / "Kiro" / "Kiro.exe"
    kiro_cli = script_dir / "Kiro" / "resources" / "app" / "out" / "cli.js"
    
    if not kiro_exe.exists():
        print(f"\nERROR: Kiro.exe not found at {kiro_exe}")
        return
    
    if not kiro_cli.exists():
        print(f"\nERROR: cli.js not found at {kiro_cli}")
        return
    
    print(f"\n{'='*60}")
    print("Launching Kiro...")
    print(f"{'='*60}\n")
    
    # Set environment variables
    env = os.environ.copy()
    env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
    env['ELECTRON_IGNORE_CERTIFICATE_ERRORS'] = '1'
    env['VSCODE_DEV'] = ''
    env['ELECTRON_RUN_AS_NODE'] = '1'
    
    # Launch Kiro
    try:
        subprocess.run([
            str(kiro_exe),
            str(kiro_cli),
            '--ignore-certificate-errors',
            f'--proxy-server=127.0.0.1:{port}'
        ], env=env)
        
        print(f"\n{'='*60}")
        print("Kiro closed")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\nError launching Kiro: {e}")

if __name__ == "__main__":
    # Check dependencies first
    try:
        import mitmproxy
    except ImportError:
        print("\nERROR: mitmproxy not installed.")
        print("Install with: pip install mitmproxy")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Get port from command line or use default
    port = 29974
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = 29974

    print("\n" + "="*60)
    print("Kiro Intercepted - Unified Launcher")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  - Proxy port: {port}")
    print(f"  - Certificate validation: DISABLED")
    print(f"  - Only Kiro traffic is proxied")
    print("\nCapture features:")
    print("  - JSON pretty-printing")
    print("  - Event-stream detection")
    print("  - GZIP decompression")
    print("  - Binary format identification")
    print("  - Auto-save to captured_*.jsonl files")
    print("\nStarting proxy...")
    print("="*60 + "\n")
    
    # Start Kiro in a separate thread
    kiro_thread = threading.Thread(target=launch_kiro, args=(port,), daemon=True)
    kiro_thread.start()
    
    # Run mitmproxy in main thread
    sys.argv = ['mitmdump', '-s', __file__, '--listen-port', str(port)]
    mitmdump()

