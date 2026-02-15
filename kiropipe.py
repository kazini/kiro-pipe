#!/usr/bin/env python3
import subprocess
import sys
import time
import os
from pathlib import Path
from mitmproxy import http
from mitmproxy.tools.main import mitmdump
import json
import threading

"""
KiroPipe || Proxies Kiro and enables custom LLM API use.
> Uses _kiropipe folder.
Usage: python kiropipe.py [port]
Default port: 29974
"""
#
# ============================================================
# CONFIGURATION
# ============================================================
DEFAULT_PORT = 29974
KIRO_EXE_PATH = None  # Set to custom path or None to auto-detect
BLOCK_TELEMETRY = True  # Block telemetry (metrics/traces)
BLOCK_UPDATES = True  # Block update checks
BLOCK_USAGE_LIMITS = False  # Block kiro credit usage limit checks
DEBUG_MODE = True  # Show detailed output and save to files
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

# Add _kiropipe to Python path for module imports
sys.path.insert(0, str(KIROPIPE_DIR))

if DEBUG_MODE:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to_file = DEBUG_MODE
        self.telemetry_blocked = 0

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1
        
        # Block telemetry (any region, metrics or traces)
        if BLOCK_TELEMETRY and 'telemetry' in flow.request.pretty_host:
            self.telemetry_blocked += 1
            if DEBUG_MODE:
                print(f"\n[BLOCKED TELEMETRY #{self.telemetry_blocked}] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"status":"ok"}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block update checks
        if BLOCK_UPDATES and 'metadata-win32' in flow.request.path:
            if DEBUG_MODE:
                print(f"\n[BLOCKED UPDATE CHECK] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"currentRelease":"0.9.40","releases":[]}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Blocll_process_on_port(proxy_port)
        except Exception as e:
            print(f"Error terminating mitmproxy: {e}")
    
    print("Cleanup complete.")
    print("="*60 + "\n")


# Register cleanup handler
atexit.register(cleanup)


# Normalize configuration values
BLOCK_TELEMETRY = normalize_bool(BLOCK_TELEMETRY)
BLOCK_UPDATES = normalize_bool(BLOCK_UPDATES)
BLOCK_USAGE_LIMITS = normalize_bool(BLOCK_USAGE_LIMITS)
DEBUG_MODE = normalize_bool(DEBUG_MODE)

# Setup directories

KIROPIPE_DIR = SCRIPT_DIR / "_kiropipe"
DEBUG_DIR = KIROPIPE_DIR / "debug_logs" / "interactions"
RESPONSES_DIR = DEBUG_DIR / "responses"
POSTED_DIR = DEBUG_DIR / "posted"

# Add _kiropipe to Python path for module imports
sys.path.insert(0, str(KIROPIPE_DIR))

if DEBUG_MODE:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)


class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to= DEBUG_MODE
        self.telemetry_blocked = 0

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1
        
        # Block telemetry (any region, metrics or traces)
        if BLOCK_TELEMETRY and 'telemetry' in flow.request.pretty_host:
            self.telemetry_blocked += 1
            if DEBUG_MODE:
                print(f"\n[BLOCKED TELEMETRY #{self.telemetry_blocked}] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"status":"ok"}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block update checks
        if BLOCK_UPDATES and 'metadata-win32' in flow.request.path:
            if DEBUG_MODE:
                print(f"\n[BLOCKED UPDATE CHECK] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"currentRelease":"0.9.40","releases":[]}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block usage limits (optional - may break features)
        if BLOCK_USAGE_LIMITS and 'getUsageLimits' in flow.request.path:
            if DEBUG_MODE:
                print(f"\n[BLOCKED USAGE LIMITS] {flow.request.pretty_url}")
            flow.response = http.Response.make(
                200,
                b'{"limits":[],"subscriptionInfo":{"type":"FREE"}}',
                {"Content-Type": "application/json"}
            )
            return

        # Check if it's an AWS Q request
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            self.aws_requests.append({
                'url': flow.request.pretty_url,
                'method': flow.request.method,
                'host': flow.request.pretty_host,
                'path': flow.request.path
            })

            if DEBUG_MODE:
                print(f"\n{'='*60}")
ws_requests)}]")
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
                    
                    if DEBUG_MODE:
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
                                'headerdict(flow.request.headers),
                                'body': body
                            }, f, indent=2)
                except:
                    if DEBUG_MODE:
                        print(f"  [Binary content]")

            if DEBUG_MODE:
                print(f"{'='*60}\n")

    def response(self, flow: http.HTTPFlow) -> None:
        """Intercept all responses"""
        if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
            if DEBUG_MODE:
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
                if DEBUG_MODE:
                    print(f"\nResponse Body ({len(flow.response.content)} bytes):")
                
                # Try multiple decoding strategies
                decoded = False
                
                # Strategy 1: Try as text/JSON
                try:
                    text = flow.response.text
                    # Try to parse as JSON
                    try:
                        response_json = json.loads(text)
                        if DEBUG_MODE:
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
                        if DEBUG_MODE:
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
                
                # Strategy  (streaming response)
                if not decoded and 'text/event-stream' in flow.response.headers.get('content-type', ''):
                    try:
                        text = flow.response.content.decode('utf-8')
                        if DEBUG_MODE:
                            print(f"  [EVENT-STREAM]")
                            lines = text.split('\n')[:20]
                            for line in lines:
                                print(f"    {line}")
                       t('\n')) > 20:
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
                    if DEBUG_MODE:
                        print(f"  [BINARY] First 100 bytes (hex):")
                        hex_data = flow.response.content[:100].hex()
                        print(f"    {hex_data}")
                    
                    # Try to identify format
                    if flow.response.cont:2] == b'\x1f\x8b':
                        if DEBUG_MODE:
                            print(f"  Format: GZIP compressed")
                        try:
                            import gzip
                            decompressed = gzip.decompress(flow.response.content)
                            if DEBUG_MODE:
                                print(f"  Decompressed ({len(decompressed)} bytes):")
                                decompressed_text = decompressed[:500].decode('utf-8', errors='ignore')
                                print(f"    {decompressed_text}")
                            
                            # Save decompressed to file
                            if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                                filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}_gzip.txt'
                                with open(filename, 'w', encoding='utf-8') as f:
                                    f.write(decompressed.decode('utf-8')
                        except Exception as e:
                            if DEBUG_MODE:
                                print(f"  Failed to decompress: {e}")
                    
                    # Save binary to file
                    if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                        filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.bin'
                        with open(filename, 'wb') as f:
    content)
                        if DEBUG_MODE:
                            print(f"  Saved binary to: {filename.name}")
            
            if DEBUG_MODE:
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


def monitor_kiro():
    """Monitor Kiro process and exit when it closes"""
    global kiro_process
    
    if not kiro_process:
        return
    
    try:
        # Convert subprocess.Popen to psutil.Process for better monitoring
        kiro_psutil = psutil.Process(kiro_process.pid)
        
        # Wait for Kiro to exit
        kiro_psutil.wait()
        
        print(f"\n{'='*60}")
        print("Kiro closed - shutting down KiroPipe")
        print(f"{'='*60}\n")
        
        # Exit the program (cleanup will be called automatically)
        os._exit(0)
        
    except (psutil.NoSuchProcess, ProcessLookupError):
        print("\nKiro process ended - shutting down KiroPipe")
        os._exit(0)
    except Exception as e:
        print(f"\nError monitoring Kiro: {e}")


def launch_kiro(port):
    """Launch Kiro with proxy settings"""
    global kiro_process
    
    # Wait for proxy to be ready
    time.sleep(2)
    
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
    
    # Launch Kiro
    try:
        kiro_process = subprocess.Popen([
            str(kiro_exe),
            str(kiro_cli),
            '--ignore-certificate-errors',
            f'--proxy-server=127.0.0.1:{port}'
        ], env=env)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_kiro, daemon=False)
        monitor_thread.start()
        
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
    
    proxy_port = port
    
    # Kill any existing process on this port
    print(f"\nChecking for existing processes on port {port}...")
    kill_process_on_port(port)
    time.sleep(1)

    print("\n" + "="*60)
    print("KiroPipe - Unified Launcher")
    print("="*60)
    print(f"\nConfiguration:")
    print(f"  - Proxy port: {port}")
    print(f"  - Certificate validation: DISABLED")
    print(f"  - Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")
    print(f"  - Telemetry blocking: {'ENABLED' if BLOCK_TELEMETRY else 'DISABLED'}")
    print(f"  - Update checks: {'BLOCKED' if BLOCK_UPDATES else 'ALLOWED'}")
    print(f"  - Usage limits: {'BLOCKED' if BLOCK_USAGE_LIMITS else 'ALLOWED'}")
    print(f"  - Only Kiro traffic is proxied")
    if DEBUG_MODE:
        print(f"\nDebug output:")
        print(f"  - Console: Detailed request/response logging")
        print(f"  - Files saved to: {DEBUG_DIR}")
        print(f"    - Requests: {POSTED_DIR}")
        print(f"    - Responses: {RESPONSES_DIR}")
    print("\nNote: Script changes require restart (Ctrl+C and rerun)")
    print("="*60 + "\n")
    
    # Start Kiro in a separate thread
    kiro_thread = threading.Thread(target=launch_kiro, args=(port,), daemon=True)
    kiro_thread.start()
    
    # Run mitmproxy in main thread
    try:
        sys.argv = ['mitmdump', '-s', __file__, '--listen-port', str(port)]
        mitmdump()
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal...")
    finally:
        cleanup()
