#!/usr/bin/env python3
import subprocess
import sys
import time
import os
from pathlib import Path

# Initialize colorama for cross-platform colored output
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ''
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ''
    COLORS_AVAILABLE = False

# ============================================================
# DEPENDENCY CHECK
# ============================================================
def check_dependencies():
    """Check and install/upgrade dependencies from requirements.txt"""
    requirements_file = Path(__file__).parent / "_kiropipe" / "engine" / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"{Fore.YELLOW} WARNING: requirements.txt not found at {requirements_file}{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN} Checking dependencies...{Style.RESET_ALL}")
    
    try:
        # Try modern importlib.metadata first (Python 3.8+)
        try:
            from importlib.metadata import version, PackageNotFoundError
            use_importlib = True
        except ImportError:
            # Fall back to pkg_resources
            import pkg_resources
            use_importlib = False
        
        # Read requirements
        with open(requirements_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        missing = []
        outdated = []
        
        for requirement in requirements:
            if not requirement:
                continue
            
            # Parse requirement (handle >= and other operators)
            pkg_name = requirement.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].strip()
            
            try:
                if use_importlib:
                    # Check if package exists
                    try:
                        installed_version = version(pkg_name)
                        # Simple check - if requirement has version, we assume it needs checking
                        if '>=' in requirement or '==' in requirement:
                            # For now, just note it exists (full version comparison is complex)
                            pass
                    except PackageNotFoundError:
                        missing.append(requirement)
                else:
                    # Use pkg_resources
                    pkg_resources.require(requirement)
            except Exception as e:
                if 'not found' in str(e).lower() or 'cannot import' in str(e).lower():
                    missing.append(requirement)
                elif 'conflict' in str(e).lower():
                    outdated.append((requirement, str(e)))
        
        if missing or outdated:
            print(f"\n{Fore.RED}{'='*60}")
            print(f"{Style.BRIGHT} DEPENDENCY ISSUES DETECTED")
            print(f"{'='*60}{Style.RESET_ALL}")
            
            if missing:
                print(f"\n{Fore.YELLOW}Missing packages:{Style.RESET_ALL}")
                for pkg in missing:
                    print(f"  {Fore.RED}{Style.RESET_ALL} {pkg}")
            
            if outdated:
                print(f"\n{Fore.YELLOW}Outdated packages:{Style.RESET_ALL}")
                for pkg, error in outdated:
                    print(f"  {Fore.RED}{Style.RESET_ALL} {pkg}")
                    print(f"    {Style.DIM}{error}{Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}1.{Style.RESET_ALL} Auto-install/upgrade all packages")
            print(f"  {Fore.YELLOW}2.{Style.RESET_ALL} Show manual install commands and exit")
            print(f"  {Fore.RED}3.{Style.RESET_ALL} Continue anyway (may cause errors)")
            
            choice = input(f"\n{Fore.CYAN}Enter choice (1-3):{Style.RESET_ALL} ").strip()
            
            if choice == '1':
                print(f"\n{Fore.CYAN} Installing/upgrading packages...{Style.RESET_ALL}")
                try:
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install', '--upgrade',
                        '-r', str(requirements_file)
                    ])
                    print(f"\n{Fore.GREEN} All dependencies installed successfully!{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Please restart the script.{Style.RESET_ALL}\n")
                    sys.exit(0)
                except subprocess.CalledProcessError as e:
                    print(f"\n{Fore.RED} Failed to install dependencies: {e}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Please install manually and try again.{Style.RESET_ALL}")
                    sys.exit(1)
            
            elif choice == '2':
                print(f"\n{Fore.CYAN}To fix, run:{Style.RESET_ALL}")
                print(f"  {Fore.GREEN}pip install -r {requirements_file}{Style.RESET_ALL}")
                print(f"\n{Fore.CYAN}Or install/upgrade individually:{Style.RESET_ALL}")
                for pkg in missing + [p for p, _ in outdated]:
                    print(f"  {Fore.GREEN}pip install --upgrade {pkg}{Style.RESET_ALL}")
                print()
                sys.exit(1)
            
            elif choice == '3':
                print(f"\n{Fore.YELLOW} Continuing without fixing dependencies...{Style.RESET_ALL}")
                print(f"{Fore.RED}Warning: This may cause errors!{Style.RESET_ALL}\n")
            
            else:
                print(f"\n{Fore.RED}Invalid choice. Exiting.{Style.RESET_ALL}")
                sys.exit(1)
        
        else:
            print(f"{Fore.GREEN} All dependencies satisfied.{Style.RESET_ALL}\n")
        
    except ImportError as e:
        print(f"{Fore.YELLOW} WARNING: Dependency checking unavailable ({e}){Style.RESET_ALL}")
        print(f"{Fore.CYAN}To install dependencies manually:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}pip install -r {requirements_file}{Style.RESET_ALL}\n")
    except Exception as e:
        print(f"{Fore.YELLOW} WARNING: Dependency check failed: {e}{Style.RESET_ALL}")

# Global flag to prevent duplicate dependency checks
_DEPENDENCIES_CHECKED = False

def check_dependencies_once():
    """Check dependencies only once per process"""
    global _DEPENDENCIES_CHECKED
    if not _DEPENDENCIES_CHECKED:
        check_dependencies()
        _DEPENDENCIES_CHECKED = True

# Check dependencies before importing anything else
check_dependencies_once()

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
DEBUG_MODE_ENABLED = False  # Show detailed output
DEBUG_STORE_INTERACTION_BLOCKS = False  # Save requests/responses to files
ALLOW_KIRO_MODELS = True  # TRUE = allow Kiro's default models
# ============================================================

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

try:
    CONFIG = load_config(KIROPIPE_DIR / 'kiropipe_config.yaml')
    
    # Override hardcoded values with config file values (only if config loaded successfully)
    if CONFIG:
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
    else:
        print(f"{Fore.YELLOW}[Config]  WARNING: Config not loaded, using hardcoded defaults{Style.RESET_ALL}")
        CURRENT_MODEL = 'kiro-default'
except Exception as e:
    print(f"{Fore.RED}[Config]  ERROR: Failed to load config: {e}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}[Config] Using hardcoded defaults{Style.RESET_ALL}")
    CONFIG = None
    CURRENT_MODEL = 'kiro-default'

if DEBUG_STORE_INTERACTION_BLOCKS:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.save_to_file = DEBUG_STORE_INTERACTION_BLOCKS
        self.current_model = CURRENT_MODEL
        self.kiro_model_ids = set()  # Track Kiro's original model IDs
        self.custom_model_ids = set()  # Track our custom model IDs
        self.model_is_kiro = True  # Track if current model is Kiro's
        self.start_time = time.time()  # Track when proxy started

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1
        
        # Block telemetry if not allowed
        if not ALLOW_TELEMETRY and 'telemetry' in flow.request.pretty_host:
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.RED} [BLOCKED TELEMETRY]{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")
            flow.response = http.Response.make(
                200,
                b'{"status":"ok"}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block update checks if not allowed (GET requests)
        if not ALLOW_UPDATES and 'metadata-win32' in flow.request.path:
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.RED} [BLOCKED UPDATE CHECK]{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")
            flow.response = http.Response.make(
                200,
                b'{"currentRelease":"0.9.40","releases":[]}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Block update POST requests if not allowed
        if not ALLOW_UPDATES and flow.request.method == 'POST':
            # Check for update-related endpoints
            if 'update' in flow.request.path.lower() or 'metadata' in flow.request.path.lower():
                if DEBUG_MODE_ENABLED:
                    print(f"\n{Fore.RED} [BLOCKED UPDATE POST]{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")
                    print(f"  {Fore.CYAN}Method:{Style.RESET_ALL} {flow.request.method}")
                flow.response = http.Response.make(
                    200,
                    b'{"status":"ok"}',
                    {"Content-Type": "application/json"}
                )
                return
        
        # Block metrics POST requests if not allowed
        if not ALLOW_TELEMETRY and flow.request.method == 'POST':
            # Check for metrics-related endpoints
            if 'metric' in flow.request.path.lower() or 'metering' in flow.request.path.lower():
                if DEBUG_MODE_ENABLED:
                    print(f"\n{Fore.RED} [BLOCKED METRICS POST]{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")
                    print(f"  {Fore.CYAN}Method:{Style.RESET_ALL} {flow.request.method}")
                flow.response = http.Response.make(
                    200,
                    b'{"status":"ok"}',
                    {"Content-Type": "application/json"}
                )
                return
        
        # Dynamic usage limits blocking (block when custom models are available OR within first 5 seconds)
        # Note: This is called before model selection, so we check if ANY custom models exist
        if 'getUsageLimits' in flow.request.path:
            elapsed_time = time.time() - self.start_time
            within_startup_window = elapsed_time < 5.0
            should_block = len(self.custom_model_ids) > 0 or within_startup_window
            
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.CYAN}[USAGE LIMITS CHECK]{Style.RESET_ALL}")
                print(f"  Elapsed time: {elapsed_time:.2f}s")
                print(f"  Within startup window (5s): {within_startup_window}")
                print(f"  Custom model IDs: {self.custom_model_ids}")
                print(f"  Count: {len(self.custom_model_ids)}")
                print(f"  Should block: {should_block}")
            
            if should_block:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED} [BLOCKED USAGE LIMITS]{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")
                    if within_startup_window:
                        print(f"  {Fore.CYAN}Reason:{Style.RESET_ALL} Within startup window ({elapsed_time:.2f}s / 5.0s)")
                    else:
                        print(f"  {Fore.CYAN}Reason:{Style.RESET_ALL} Custom models available ({len(self.custom_model_ids)} models)")
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
                    print(f"\n{Fore.RED} [ERROR] Kiro models blocked but no custom providers enabled!{Style.RESET_ALL}")
                    print(f"  {Fore.YELLOW}Enable a custom provider in config or set kiro_endpoint.models: true{Style.RESET_ALL}")
                flow.response = http.Response.make(
                    503,
                    b'{"error":"Kiro models blocked and no custom providers configured"}',
                    {"Content-Type": "application/json"}
                )
                return
            
            # Forward to custom provider (handled below)
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.YELLOW} [KIRO MODELS BLOCKED]{Style.RESET_ALL} Forwarding to custom provider")
        
        # Check if request should be allowed (all blocking enabled = nothing through)
        if not CONFIG.should_allow_request(flow.request.path, self.current_model):
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.RED} [BLOCKED ALL]{Style.RESET_ALL} All traffic blocked by configuration")
                print(f"  Telemetry: {ALLOW_TELEMETRY}, Updates: {ALLOW_UPDATES}")
                print(f"  Kiro models: {ALLOW_KIRO_MODELS}, Usage limits: {should_block_limits}")
            flow.response = http.Response.make(
                503,
                b'{"error":"All traffic blocked by configuration"}',
                {"Content-Type": "application/json"}
            )
            return
        
        # Detect model selection and route to custom provider if needed
        if 'generateAssistantResponse' in flow.request.path:
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.MAGENTA}[DEBUG] Routing code reached for generateAssistantResponse{Style.RESET_ALL}")
            
            # Step 1: Parse request to determine which model is being used
            selected_model = None
            try:
                body = json.loads(flow.request.text)
                # Model ID is nested in conversationState.currentMessage.userInputMessage
                selected_model = (
                    body.get('conversationState', {})
                    .get('currentMessage', {})
                    .get('userInputMessage', {})
                    .get('modelId')
                )
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.MAGENTA}[DEBUG] Parsed model from request: {selected_model}{Style.RESET_ALL}")
            except Exception as e:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED}[ERROR] Failed to parse request body: {e}{Style.RESET_ALL}")
            
            # Step 2: If we found a model, update tracking and check if we need to route
            if selected_model:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.MAGENTA}[DEBUG] Model found, updating tracking{Style.RESET_ALL}")
                
                # Update current model tracking
                old_model = self.current_model
                self.current_model = selected_model
                self.model_is_kiro = selected_model in self.kiro_model_ids
                
                if DEBUG_MODE_ENABLED and selected_model != old_model:
                    model_type = "Kiro" if self.model_is_kiro else "Custom"
                    print(f"{Fore.CYAN}[MODEL SELECTED] {selected_model} ({model_type}){Style.RESET_ALL}")
                
                # Step 3: Check if this model needs custom routing
                model_info = CONFIG.get_model_info(selected_model)
                
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.YELLOW}[ROUTING CHECK] Model: {selected_model}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}[ROUTING CHECK] Model info from config: {model_info}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}[ROUTING CHECK] Provider: {model_info['provider'] if model_info else 'None'}{Style.RESET_ALL}")
                
                # Step 4: Route to custom provider if not Kiro
                if model_info and model_info['provider'] != 'kiro':
                    # Direct API call to custom provider (no bridge needed)
                    provider_name = model_info['provider']
                    provider_config = CONFIG.get_provider_config(provider_name)
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"\n{Fore.CYAN} [CUSTOM PROVIDER]{Style.RESET_ALL} Routing to {Fore.GREEN}{provider_name}{Style.RESET_ALL}")
                        print(f"  {Fore.CYAN}Model:{Style.RESET_ALL} {model_info['model']['name']}")
                    
                    try:
                        import httpx
                        
                        # Parse AWS request
                        aws_body = json.loads(flow.request.text)
                        
                        # Get user message from AWS format
                        user_message = aws_body.get('conversationState', {}).get('currentMessage', {}).get('userInputMessage', {}).get('content', '')
                        
                        if provider_name == 'anthropic':
                            # Transform to Anthropic format
                            api_base = provider_config.get('api_base', 'https://api.anthropic.com/v1')
                            api_key = provider_config.get('api_key')
                            
                            if not api_key:
                                raise Exception("Anthropic API key not configured")
                            
                            anthropic_request = {
                                "model": self.current_model,
                                "max_tokens": 4096,
                                "messages": [
                                    {"role": "user", "content": user_message}
                                ],
                                "stream": True
                            }
                            
                            # Call Anthropic API
                            with httpx.Client(timeout=300.0) as client:
                                response = client.post(
                                    f"{api_base}/messages",
                                    json=anthropic_request,
                                    headers={
                                        "x-api-key": api_key,
                                        "anthropic-version": "2023-06-01",
                                        "content-type": "application/json"
                                    }
                                )
                                
                                if DEBUG_MODE_ENABLED:
                                    print(f"{Fore.GREEN} [ANTHROPIC]{Style.RESET_ALL} Response: {Fore.CYAN}{response.status_code}{Style.RESET_ALL}")
                                
                                # For now, just return the raw response
                                # TODO: Transform Anthropic response to AWS format
                                flow.response = http.Response.make(
                                    response.status_code,
                                    response.content,
                                    dict(response.headers)
                                )
                                return
                        
                        else:
                            # Other providers not yet implemented
                            raise Exception(f"Provider {provider_name} not yet implemented")
                        
                    except Exception as e:
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.RED} [CUSTOM PROVIDER] Error: {e}{Style.RESET_ALL}")
                            import traceback
                            traceback.print_exc()
                        
                        # Return error response
                        flow.response = http.Response.make(
                            503,
                            json.dumps({'error': f'Custom provider error: {str(e)}'}).encode(),
                            {"Content-Type": "application/json"}
                        )
                        return
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
                        print(f"\n{Fore.MAGENTA} [INJECT]{Style.RESET_ALL} Using queued response")
                        print(f"{Fore.MAGENTA} [INJECT]{Style.RESET_ALL} Message: {Fore.CYAN}{injection.get('text', 'unknown')}{Style.RESET_ALL}")
                    
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
                        print(f"{Fore.MAGENTA} [INJECT]{Style.RESET_ALL} Injected {Fore.YELLOW}{len(injected_binary)} bytes{Style.RESET_ALL}")
                        if injection.get('include_tool'):
                            print(f"{Fore.MAGENTA} [INJECT]{Style.RESET_ALL} Includes tool call")
                    
                    # Update the queue file (remove the used injection)
                    if len(queue_data) > 0:
                        INJECTION_QUEUE_FILE.write_text(json.dumps(queue_data, indent=2))
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.MAGENTA} [INJECT]{Style.RESET_ALL} {Fore.YELLOW}{len(queue_data)}{Style.RESET_ALL} injection(s) remaining in queue")
                    else:
                        INJECTION_QUEUE_FILE.unlink()
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.MAGENTA} [INJECT]{Style.RESET_ALL} Queue empty, file deleted")
                    
                    return
                
            except Exception as e:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED} [INJECT] Error reading queue: {e}{Style.RESET_ALL}")
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

            # Check for model-related endpoints (debug mode only)
            model_keywords = ['model', 'list', 'available', 'configuration', 'select', 'choice']
            is_model_related = any(keyword in flow.request.path.lower() for keyword in model_keywords)
            
            if is_model_related and DEBUG_MODE_ENABLED:
                print(f"\n{Fore.MAGENTA}{'='*60}")
                print(f"{Style.BRIGHT} [MODEL-RELATED ENDPOINT DETECTED]{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Path:{Style.RESET_ALL} {flow.request.path}")
                print(f"{Fore.YELLOW}Method:{Style.RESET_ALL} {flow.request.method}")
                print(f"{Fore.YELLOW}URL:{Style.RESET_ALL} {flow.request.pretty_url}")
                print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}\n")

            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.BLUE}{'='*60}")
                print(f"{Style.BRIGHT} [AWS REQUEST #{len(self.aws_requests)}]{Style.RESET_ALL}")
                print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Method:{Style.RESET_ALL} {Fore.GREEN}{flow.request.method}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}Host:{Style.RESET_ALL} {flow.request.pretty_host}")
                print(f"{Fore.CYAN}Path:{Style.RESET_ALL} {Style.DIM}{flow.request.path}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}URL:{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")

                # Print headers
                print(f"\n{Fore.YELLOW}Headers:{Style.RESET_ALL}")
                for k, v in flow.request.headers.items():
                    if k.lower() in ['authorization', 'x-amz-target', 'content-type', 'user-agent']:
                        print(f"  {Fore.CYAN}{k}:{Style.RESET_ALL} {Style.DIM}{v}{Style.RESET_ALL}")

            # Print and save body if present
            if flow.request.content:
                try:
                    body = flow.request.text
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"\n{Fore.YELLOW}Body ({len(flow.request.content)} bytes):{Style.RESET_ALL}")
                        # Try to parse as JSON for pretty printing
                        try:
                            body_json = json.loads(body)
                            body_str = json.dumps(body_json, indent=2)
                            if len(body_str) > 1000:
                                print(f"  {Style.DIM}{body_str[:1000]}...{Style.RESET_ALL}")
                            else:
                                print(f"  {Style.DIM}{body_str}{Style.RESET_ALL}")
                        except:
                            # Not JSON, print as text
                            if len(body) > 500:
                                print(f"  {Style.DIM}{body[:500]}...{Style.RESET_ALL}")
                            else:
                                print(f"  {Style.DIM}{body}{Style.RESET_ALL}")
                    
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
                        print(f"  {Style.DIM}[Binary content]{Style.RESET_ALL}")

            if DEBUG_MODE_ENABLED:
                print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}\n")

    def response(self, flow: http.HTTPFlow) -> None:
            """Intercept all responses"""

            # Inject custom models into ListAvailableModels response
            if 'ListAvailableModels' in flow.request.path and flow.response.status_code == 200:
                try:
                    response_data = json.loads(flow.response.text)

                    if DEBUG_MODE_ENABLED:
                        print(f"\n{Fore.CYAN}{'='*60}")
                        print(f"{Style.BRIGHT} [INJECTING CUSTOM MODELS]{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Original Kiro models: {len(response_data.get('models', []))}{Style.RESET_ALL}")

                    # Track Kiro's original model IDs and modify their rateUnit
                    if 'models' in response_data:
                        for model in response_data['models']:
                            self.kiro_model_ids.add(model.get('modelId'))
                            # Change Kiro's rateUnit from "Credit" to "Kiro Credits"
                            if model.get('rateUnit') == 'Credit':
                                model['rateUnit'] = 'Kiro Credits'

                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.YELLOW}Tracked Kiro model IDs: {len(self.kiro_model_ids)}{Style.RESET_ALL}")
                            print(f"{Fore.YELLOW}Modified Kiro models rateUnit to 'Kiro Credits'{Style.RESET_ALL}")

                        # Get template from first Kiro model
                        template_model = response_data['models'][0] if response_data['models'] else {}

                        custom_models_added = []

                        # 1. Inject models from config
                        for provider_name in CONFIG.get_enabled_providers():
                            if provider_name == 'kiro':
                                continue  # Skip Kiro's own models

                            provider_config = CONFIG.get_provider_config(provider_name)
                            models = provider_config.get('models', [])

                            for model in models:
                                model_id = model.get('name', 'unknown')
                                # Use display_name if provided, otherwise fall back to first alias or name
                                model_name = model.get('display_name') or (model.get('alias', [model.get('name', 'Unknown')])[0] if model.get('alias') else model.get('name', 'Unknown'))

                                custom_model = {
                                    "modelId": model_id,
                                    "modelName": model_name,
                                    "description": model.get('description', f"Custom {provider_name} model"),
                                    "promptCaching": template_model.get('promptCaching', {
                                        "maximumCacheCheckpointsPerRequest": 4,
                                        "minimumTokensPerCacheCheckpoint": 1024,
                                        "supportsPromptCaching": True
                                    }),
                                    "rateMultiplier": None,  # null for config models
                                    "rateUnit": provider_name.upper(),  # Provider name in uppercase
                                    "supportedInputTypes": ["TEXT", "IMAGE"],
                                    "tokenLimits": template_model.get('tokenLimits', {
                                        "maxInputTokens": 200000,
                                        "maxOutputTokens": None
                                    })
                                }

                                response_data['models'].append(custom_model)
                                self.custom_model_ids.add(model_id)
                                custom_models_added.append(model_name)

                        # 2. Inject dummy test models (debug mode only)
                        if DEBUG_MODE_ENABLED:
                            dummy_file = KIROPIPE_DIR / 'devtools' / 'dummy_models.json'
                            if dummy_file.exists():
                                try:
                                    dummy_data = json.loads(dummy_file.read_text())
                                    dummy_models = dummy_data.get('models', [])

                                    # Valid fields for Kiro model schema
                                    valid_fields = {
                                        'modelId', 'modelName', 'description', 'promptCaching',
                                        'rateMultiplier', 'rateUnit', 'supportedInputTypes', 'tokenLimits'
                                    }

                                    for dummy_model in dummy_models:
                                        # Validate required fields
                                        if 'modelId' in dummy_model and 'modelName' in dummy_model:
                                            model_id = dummy_model['modelId']
                                            
                                            # Strip extra fields that aren't part of Kiro's schema
                                            cleaned_model = {}
                                            stripped_fields = []
                                            for key, value in dummy_model.items():
                                                if key in valid_fields:
                                                    cleaned_model[key] = value
                                                else:
                                                    stripped_fields.append(key)
                                            
                                            if stripped_fields:
                                                print(f"{Fore.YELLOW}[STRIP] Removed non-schema fields from {model_id}: {', '.join(stripped_fields)}{Style.RESET_ALL}")
                                            
                                            # Check if this modelId already exists (override feature)
                                            existing_index = None
                                            was_kiro_model = False
                                            for i, existing_model in enumerate(response_data['models']):
                                                if existing_model.get('modelId') == model_id:
                                                    existing_index = i
                                                    was_kiro_model = model_id in self.kiro_model_ids
                                                    break
                                            
                                            if existing_index is not None:
                                                # Override existing model
                                                response_data['models'][existing_index] = cleaned_model
                                                if was_kiro_model:
                                                    # Keep it as a Kiro model (don't add to custom_model_ids)
                                                    print(f"{Fore.MAGENTA}[OVERRIDE] Replaced Kiro model: {model_id} (inherits Kiro type){Style.RESET_ALL}")
                                                else:
                                                    # It was already a custom model, keep it that way
                                                    print(f"{Fore.MAGENTA}[OVERRIDE] Replaced custom model: {model_id}{Style.RESET_ALL}")
                                                custom_models_added.append(f"{cleaned_model['modelName']} (override)")
                                            else:
                                                # New model - add as custom
                                                response_data['models'].append(cleaned_model)
                                                self.custom_model_ids.add(model_id)
                                                custom_models_added.append(cleaned_model['modelName'])
                                        else:
                                            print(f"{Fore.YELLOW}[WARNING] Dummy model missing required fields (modelId, modelName){Style.RESET_ALL}")

                                    if dummy_models:
                                        print(f"{Fore.CYAN}Loaded {len(dummy_models)} dummy test model(s){Style.RESET_ALL}")
                                except json.JSONDecodeError:
                                    print(f"{Fore.YELLOW}[WARNING] dummy_models.json exists but contains invalid JSON{Style.RESET_ALL}")
                                except Exception as e:
                                    print(f"{Fore.YELLOW}[WARNING] Error loading dummy models: {e}{Style.RESET_ALL}")

                        # Update response
                        if custom_models_added:
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.GREEN}Injected {len(custom_models_added)} custom model(s):{Style.RESET_ALL}")
                                for model_name in custom_models_added:
                                    print(f"  - {Fore.CYAN}{model_name}{Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}Total models: {len(response_data['models'])}{Style.RESET_ALL}")

                            modified_json = json.dumps(response_data).encode('utf-8')
                            flow.response.content = modified_json
                            flow.response.headers['content-length'] = str(len(modified_json))

                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
                        else:
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.YELLOW}No custom models to inject{Style.RESET_ALL}")
                                print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

                except json.JSONDecodeError:
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.YELLOW}[WARNING] ListAvailableModels response is not JSON{Style.RESET_ALL}")
                except Exception as e:
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.RED}[ERROR] Failed to inject models: {e}{Style.RESET_ALL}")
                        import traceback
                        traceback.print_exc()

            if 'amazonaws.com' in flow.request.pretty_host or 'kiro.dev' in flow.request.pretty_host:
                if DEBUG_MODE_ENABLED:
                    print(f"\n{Fore.GREEN}{'='*60}")
                    print(f"{Style.BRIGHT} [AWS RESPONSE]{Style.RESET_ALL}")
                    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Status:{Style.RESET_ALL} {Fore.GREEN}{flow.response.status_code}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}URL:{Style.RESET_ALL} {Style.DIM}{flow.request.pretty_url}{Style.RESET_ALL}")

                    # Print response headers
                    print(f"\n{Fore.YELLOW}Response Headers:{Style.RESET_ALL}")
                    for k, v in flow.response.headers.items():
                        if k.lower() in ['content-type', 'content-encoding', 'content-length', 'x-amzn-requestid']:
                            print(f"  {Fore.CYAN}{k}:{Style.RESET_ALL} {Style.DIM}{v}{Style.RESET_ALL}")

                if flow.response.content:
                    if DEBUG_MODE_ENABLED:
                        print(f"\n{Fore.YELLOW}Response Body ({len(flow.response.content)} bytes):{Style.RESET_ALL}")

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
                                    print(f"  {Fore.GREEN}[JSON]{Style.RESET_ALL} {Style.DIM}{response_str[:1000]}...{Style.RESET_ALL}")
                                else:
                                    print(f"  {Fore.GREEN}[JSON]{Style.RESET_ALL} {Style.DIM}{response_str}{Style.RESET_ALL}")
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
                                    print(f"  {Fore.CYAN}[TEXT]{Style.RESET_ALL} {Style.DIM}{text[:500]}...{Style.RESET_ALL}")
                                else:
                                    print(f"  {Fore.CYAN}[TEXT]{Style.RESET_ALL} {Style.DIM}{text}{Style.RESET_ALL}")
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
                                print(f"  {Fore.MAGENTA}[EVENT-STREAM]{Style.RESET_ALL}")
                                lines = text.split('\n')[:20]  # First 20 lines
                                for line in lines:
                                    print(f"    {Style.DIM}{line}{Style.RESET_ALL}")
                                if len(text.split('\n')) > 20:
                                    print(f"    {Style.DIM}... ({len(text.split('\n'))} total lines){Style.RESET_ALL}")
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
                            print(f"  {Fore.YELLOW}[BINARY]{Style.RESET_ALL} First 100 bytes (hex):")
                            hex_data = flow.response.content[:100].hex()
                            print(f"    {Style.DIM}{hex_data}{Style.RESET_ALL}")

                        # Try to identify format
                        if flow.response.content[:2] == b'\x1f\x8b':
                            if DEBUG_MODE_ENABLED:
                                print(f"  {Fore.CYAN}Format:{Style.RESET_ALL} GZIP compressed")
                            try:
                                import gzip
                                decompressed = gzip.decompress(flow.response.content)
                                if DEBUG_MODE_ENABLED:
                                    print(f"  {Fore.CYAN}Decompressed ({len(decompressed)} bytes):{Style.RESET_ALL}")
                                    decompressed_text = decompressed[:500].decode('utf-8', errors='ignore')
                                    print(f"    {Style.DIM}{decompressed_text}{Style.RESET_ALL}")

                                # Save decompressed to file
                                if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                                    filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}_gzip.txt'
                                    with open(filename, 'w', encoding='utf-8') as f:
                                        f.write(decompressed.decode('utf-8', errors='ignore'))
                            except Exception as e:
                                if DEBUG_MODE_ENABLED:
                                    print(f"  {Fore.RED}Failed to decompress: {e}{Style.RESET_ALL}")

                        # Save binary to file
                        if self.save_to_file and 'generateAssistantResponse' in flow.request.path:
                            filename = RESPONSES_DIR / f'response_{len(self.aws_requests)}.bin'
                            with open(filename, 'wb') as f:
                                f.write(flow.response.content)
                            if DEBUG_MODE_ENABLED:
                                print(f"  {Fore.GREEN}Saved binary to:{Style.RESET_ALL} {filename.name}")

                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.GREEN}{'='*60}{Style.RESET_ALL}\n")


addons = [KiroInterceptor()]

def find_kiro_exe():
    """Find Kiro.exe - check custom path, then auto-detect"""
    if KIRO_EXE_PATH:
        kiro_exe = Path(KIRO_EXE_PATH)
        if kiro_exe.exists():
            return kiro_exe
        print(f"{Fore.YELLOW}WARNING: Custom KIRO_EXE_PATH not found: {KIRO_EXE_PATH}{Style.RESET_ALL}")
    
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
                        print(f"{Fore.YELLOW}Existing kiropipe.py instance found (PID: {pid}). Terminating...{Style.RESET_ALL}")
                        subprocess.run(['taskkill', '/F', '/PID', pid], 
                                     capture_output=True)
                        time.sleep(1)
                        print(f"{Fore.GREEN}Existing launcher terminated.{Style.RESET_ALL}\n")
                        return True
                    except:
                        pass
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not check for existing launcher: {e}{Style.RESET_ALL}")
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
        print(f"{Fore.CYAN}Monitoring Kiro process (PID: {pid})...{Style.RESET_ALL}\n")
        
        # Wait for process to terminate
        process.wait()
        
        print(f"\n{Fore.BLUE}{'='*60}")
        print(f"{Style.BRIGHT}Kiro closed{Style.RESET_ALL}")
        print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}\n")
        
        # Exit the entire process
        os._exit(0)
        
    except psutil.NoSuchProcess:
        print(f"\n{Fore.RED}Kiro process (PID: {pid}) not found.{Style.RESET_ALL}")
        os._exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Error monitoring Kiro: {e}{Style.RESET_ALL}")
        os._exit(1)

def launch_kiro(port, proxy_process=None):
    """Launch Kiro with proxy settings"""
    # Wait a bit for proxy to be ready
    time.sleep(3)
    
    # Find Kiro.exe
    kiro_exe = find_kiro_exe()
    
    if not kiro_exe:
        print(f"\n{Fore.RED}ERROR: Kiro.exe not found!{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Set KIRO_EXE_PATH at the top of this script, or place Kiro in:{Style.RESET_ALL}")
        print(f"  - {Path(__file__).parent / 'Kiro' / 'Kiro.exe'}")
        print(f"  - {Path('Kiro') / 'Kiro.exe'}")
        return
    
    # Find cli.js relative to Kiro.exe
    kiro_cli = kiro_exe.parent / "resources" / "app" / "out" / "cli.js"
    
    if not kiro_cli.exists():
        print(f"\n{Fore.RED}ERROR: cli.js not found at {kiro_cli}{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Style.BRIGHT}Launching Kiro from:{Style.RESET_ALL} {Fore.GREEN}{kiro_exe}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
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
        print(f"{Fore.CYAN}Waiting for Kiro window to appear...{Style.RESET_ALL}")
        kiro_pid = wait_for_kiro_window(timeout=15)
        
        if not kiro_pid:
            print(f"\n{Fore.RED}ERROR: Kiro window did not appear within 15 seconds.{Style.RESET_ALL}")
            os._exit(1)
        
        print(f"{Fore.GREEN}Kiro window detected (PID: {kiro_pid}){Style.RESET_ALL}")
        
        # Monitor the actual Kiro window process
        monitor_kiro_process(kiro_pid)
        
    except Exception as e:
        print(f"\n{Fore.RED}Error launching Kiro: {e}{Style.RESET_ALL}")
        os._exit(1)

if __name__ == "__main__":
    # Check dependencies first
    try:
        import mitmproxy
        from mitmproxy.tools.main import mitmdump
    except ImportError:
        print(f"\n{Fore.RED}ERROR: mitmproxy not installed.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Install with:{Style.RESET_ALL} pip install mitmproxy")
        input(f"\n{Fore.YELLOW}Press Enter to exit...{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        import psutil
    except ImportError:
        print(f"\n{Fore.RED}ERROR: psutil not installed.{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Install with:{Style.RESET_ALL} pip install psutil")
        input(f"\n{Fore.YELLOW}Press Enter to exit...{Style.RESET_ALL}")
        sys.exit(1)
    
    # Get port from command line or use default
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            port = DEFAULT_PORT

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Style.BRIGHT}KiroPipe - Unified Launcher{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    
    # Print configuration summary
    CONFIG.print_summary()
    
    print(f"\n{Fore.YELLOW}Proxy Configuration:{Style.RESET_ALL}")
    print(f"  - Port: {Fore.CYAN}{port}{Style.RESET_ALL}")
    print(f"  - Certificate validation: {Fore.RED}DISABLED{Style.RESET_ALL}")
    print(f"  - Only Kiro traffic is proxied")
    
    print(f"\n{Fore.YELLOW}Kiro Endpoint{Style.RESET_ALL} (TRUE=allow, FALSE=block):")
    print(f"  - Telemetry: {Fore.GREEN if ALLOW_TELEMETRY else Fore.RED}{'ALLOWED' if ALLOW_TELEMETRY else 'BLOCKED'}{Style.RESET_ALL}")
    print(f"  - Updates: {Fore.GREEN if ALLOW_UPDATES else Fore.RED}{'ALLOWED' if ALLOW_UPDATES else 'BLOCKED'}{Style.RESET_ALL}")
    print(f"  - Kiro models: {Fore.GREEN if ALLOW_KIRO_MODELS else Fore.RED}{'ALLOWED' if ALLOW_KIRO_MODELS else 'BLOCKED'}{Style.RESET_ALL}")
    
    # Show usage limits status
    usage_limits_status = "AUTO (dynamic)"
    usage_color = Fore.CYAN
    if FORCE_TOGGLE_USAGE_LIMITS is True:
        usage_limits_status = "ALWAYS ALLOWED"
        usage_color = Fore.GREEN
    elif FORCE_TOGGLE_USAGE_LIMITS is False:
        usage_limits_status = "ALWAYS BLOCKED"
        usage_color = Fore.RED
    print(f"  - Usage limits: {usage_color}{usage_limits_status}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}Current Model:{Style.RESET_ALL} {Fore.CYAN}{CURRENT_MODEL}{Style.RESET_ALL}")
    model_info = CONFIG.get_model_info(CURRENT_MODEL)
    if model_info:
        print(f"  Provider: {Fore.GREEN}{model_info['provider']}{Style.RESET_ALL}")
        print(f"  Description: {model_info['model'].get('description', 'N/A')}")
    
    if DEBUG_MODE_ENABLED:
        print(f"\n{Fore.MAGENTA}Debug:{Style.RESET_ALL}")
        print(f"  - Console logging: {Fore.GREEN}ENABLED{Style.RESET_ALL}")
        print(f"  - Store interaction blocks: {Fore.GREEN if DEBUG_STORE_INTERACTION_BLOCKS else Fore.RED}{'ENABLED' if DEBUG_STORE_INTERACTION_BLOCKS else 'DISABLED'}{Style.RESET_ALL}")
        if DEBUG_STORE_INTERACTION_BLOCKS:
            print(f"  - Files saved to: {Fore.CYAN}{DEBUG_DIR}{Style.RESET_ALL}")
    
    print(f"\n{Style.DIM}Note: Edit _kiropipe/kiropipe_config.yaml to change settings{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Kill any existing launcher instances first
    kill_existing_launcher()
    
    # Start Kiro in a separate thread
    kiro_thread = threading.Thread(target=lambda: launch_kiro(port, None), daemon=False)
    kiro_thread.start()
    
    # Run mitmproxy in main thread (this blocks until proxy stops)
    try:
        # Add quiet flag if debug mode is disabled
        if DEBUG_MODE_ENABLED:
            sys.argv = ['mitmdump', '-s', __file__, '--listen-port', str(port)]
        else:
            sys.argv = ['mitmdump', '-s', __file__, '--listen-port', str(port), '-q']
        mitmdump()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}Proxy stopped. Waiting for cleanup...{Style.RESET_ALL}")
    kiro_thread.join(timeout=5)
    print(f"{Fore.GREEN}Cleanup complete.{Style.RESET_ALL}")

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

