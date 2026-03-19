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
from typing import Dict, Any

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

# ── Config hot-reload ──────────────────────────────────────────────────────
_config_lock = threading.Lock()
_config_mtime = 0.0
_config_path  = KIROPIPE_DIR / 'kiropipe_config.yaml'

def _reload_globals_from_config():
    """Re-apply config values to module-level globals after a reload."""
    global ALLOW_TELEMETRY, ALLOW_UPDATES, FORCE_TOGGLE_USAGE_LIMITS
    global DEBUG_MODE_ENABLED, DEBUG_STORE_INTERACTION_BLOCKS, ALLOW_KIRO_MODELS
    if CONFIG:
        ALLOW_TELEMETRY             = CONFIG.get('kiro_endpoint.telemetry', ALLOW_TELEMETRY)
        ALLOW_UPDATES               = CONFIG.get('kiro_endpoint.updates', ALLOW_UPDATES)
        FORCE_TOGGLE_USAGE_LIMITS   = CONFIG.get('kiro_endpoint.force_toggle_usage_limits', FORCE_TOGGLE_USAGE_LIMITS)
        DEBUG_MODE_ENABLED          = CONFIG.get('debug.debug_mode_enabled', DEBUG_MODE_ENABLED)
        DEBUG_STORE_INTERACTION_BLOCKS = CONFIG.get('debug.store_interaction_blocks', DEBUG_STORE_INTERACTION_BLOCKS)
        ALLOW_KIRO_MODELS           = CONFIG.get('kiro_endpoint.models', ALLOW_KIRO_MODELS)

def _config_watcher():
    """Background thread: polls config file mtime and reloads on change."""
    global CONFIG, _config_mtime
    while True:
        try:
            mtime = _config_path.stat().st_mtime
            if mtime != _config_mtime and _config_mtime != 0.0:
                with _config_lock:
                    new_cfg = load_config(_config_path)
                    if new_cfg:
                        CONFIG = new_cfg
                        _reload_globals_from_config()
                        # Mark all active interceptor instances to rebuild the model list.
                        # 'addons' is defined at module level after this thread starts,
                        # so we look it up in the module globals at call time.
                        import sys as _sys
                        _mod = _sys.modules[__name__]
                        for _addon in getattr(_mod, 'addons', []):
                            if hasattr(_addon, '_model_list_dirty'):
                                _addon._model_list_dirty = True
                                _addon._kiro_models_cache = []  # force cold-start rebuild
                        print(f"{Fore.CYAN}[Config] Reloaded — changes applied live{Style.RESET_ALL}")
            _config_mtime = mtime
        except Exception:
            pass
        time.sleep(2)

# Seed the initial mtime so the watcher doesn't fire on startup
try:
    _config_mtime = _config_path.stat().st_mtime
except Exception:
    pass

if not any(t.name == 'config-watcher' for t in threading.enumerate()):
    threading.Thread(target=_config_watcher, daemon=True, name='config-watcher').start()
# ────────────────────────────────────────────────────────────────────────────

if DEBUG_STORE_INTERACTION_BLOCKS:
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    POSTED_DIR.mkdir(parents=True, exist_ok=True)

def _strip_metering_events(data: bytes) -> bytes:
    """
    Parse an AWS Event Stream binary blob and drop any frames whose
    :event-type header is 'metering' or 'contextUsage'.
    All other frames are re-emitted byte-for-byte (CRCs intact).

    Frame layout:
      [4] total_length  [4] headers_length  [4] prelude_crc
      [headers_length] headers
      [total_length - headers_length - 16] payload
      [4] message_crc

    Header entry layout:
      [1] name_length  [name_length] name  [1] type
      [2] value_length  [value_length] value
    """
    out = bytearray()
    pos = 0
    while pos < len(data):
        if pos + 12 > len(data):
            out += data[pos:]          # incomplete prelude — pass through
            break
        total_len     = int.from_bytes(data[pos:pos+4],   'big')
        headers_len   = int.from_bytes(data[pos+4:pos+8], 'big')
        if total_len < 16 or pos + total_len > len(data):
            out += data[pos:]          # malformed / incomplete frame — pass through
            break
        frame       = data[pos:pos + total_len]
        headers_raw = frame[12:12 + headers_len]

        # Parse headers to find :event-type value
        event_type = None
        h = 0
        while h < len(headers_raw):
            if h + 1 > len(headers_raw): break
            name_len = headers_raw[h]; h += 1
            if h + name_len > len(headers_raw): break
            name = headers_raw[h:h + name_len].decode('utf-8', errors='replace'); h += name_len
            if h + 1 > len(headers_raw): break
            h += 1  # type byte (7 = string)
            if h + 2 > len(headers_raw): break
            val_len = int.from_bytes(headers_raw[h:h+2], 'big'); h += 2
            if h + val_len > len(headers_raw): break
            val = headers_raw[h:h + val_len].decode('utf-8', errors='replace'); h += val_len
            if name == ':event-type':
                event_type = val
                break

        if event_type not in ('metering', 'contextUsage'):
            out += frame

        pos += total_len
    return bytes(out)


class KiroInterceptor:
    def __init__(self):
        self.request_count = 0
        self.aws_requests = []
        self.max_requests_history = 100  # Limit history to prevent memory leak
        self.save_to_file = DEBUG_STORE_INTERACTION_BLOCKS
        self.current_model = CURRENT_MODEL
        self.kiro_model_ids = set()  # Track Kiro's original model IDs
        self.custom_model_ids = set()  # Track our custom model IDs
        self.model_is_kiro = True  # Track if current model is Kiro's
        self.start_time = time.time()  # Track when proxy started
        self.usage_tracker = None  # Will be initialized on first use
        self.pending_simple_task = None  # Store pending simple-task request
        self.simple_task_lock = threading.Lock()  # Lock for simple-task handling
        self.last_real_model = None  # Track last non-simple-task model
        # Start blocking if config says so (good for custom-only setups);
        # state flips automatically on first generateAssistantResponse
        self.block_aws_traffic = CONFIG.get('kiro_endpoint.start_blocking', False) if CONFIG else False
        self.tool_call_cache: Dict[str, Any] = {}  # toolUseId -> {name, arguments}; persists across requests
        self._kiro_models_cache: list = []  # Cached Kiro model entries from last ListAvailableModels response
        self._context_window_cache: Dict[str, int] = {}  # model_id -> context_window learned from API responses
        self._custom_routed_once = False  # True after first custom model request — blocks first-switch parallel
        self._model_list_dirty = False    # Set True by config watcher to force rebuild on next ListAvailableModels
    
    def __del__(self):
        """Cleanup and print usage summary on shutdown"""
        if self.usage_tracker:
            try:
                self.usage_tracker.end_session()
                if DEBUG_MODE_ENABLED:
                    print(f"\n{Fore.CYAN}{'='*60}")
                    print(f"{Style.BRIGHT}Session Usage Summary{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
                    self.usage_tracker.print_summary()
                    self.usage_tracker.print_model_summary()
            except Exception as e:
                print(f"{Fore.YELLOW}[Warning] Failed to print usage summary: {e}{Style.RESET_ALL}")

    def _build_model_list(self) -> list:
        """
        Build the authoritative model list:
          1. Kiro AWS models first (only if _kiro_models_cache is populated)
          2. Custom provider models from config
          3. Dummy test models from devtools/dummy_models.json (debug mode only)
             — dummy entries can override existing entries by modelId
        """
        default_template = {
            'promptCaching': {'maximumCacheCheckpointsPerRequest': 4,
                              'minimumTokensPerCacheCheckpoint': 1024,
                              'supportsPromptCaching': True},
            'tokenLimits': {'maxInputTokens': 200000, 'maxOutputTokens': None}
        }
        aws_template = self._kiro_models_cache[0] if self._kiro_models_cache else default_template
        models = []

        # 1. Kiro passthrough models — only if we received them from AWS
        for m in self._kiro_models_cache:
            mid = m.get('modelId')
            if mid:
                self.kiro_model_ids.add(mid)
            models.append(m)

        # 2. Custom provider models from config
        for mi in (CONFIG.get_all_models() if CONFIG else []):
            if mi['provider'] == 'kiro':
                continue
            mid = mi['name']
            self.custom_model_ids.add(mid)
            models.append({
                'modelId': mid,
                'modelName': mi.get('display_name') or mid,
                'description': mi.get('description', ''),
                'promptCaching': aws_template.get('promptCaching', default_template['promptCaching']),
                'rateMultiplier': None,
                'rateUnit': None,
                'supportedInputTypes': ['TEXT', 'IMAGE'],
                'tokenLimits': {
                    'maxInputTokens': (
                        self._context_window_cache.get(mid)
                        or mi.get('context_window')
                        or aws_template.get('tokenLimits', default_template['tokenLimits']).get('maxInputTokens', 200000)
                    ),
                    'maxOutputTokens': mi.get('max_tokens', None)
                }
            })

        # 3. Dummy test models (debug mode only) — support override by modelId
        if DEBUG_MODE_ENABLED:
            dummy_file = KIROPIPE_DIR / 'devtools' / 'dummy_models.json'
            if dummy_file.exists():
                try:
                    dummy_data = json.loads(dummy_file.read_text())
                    valid_fields = {
                        'modelId', 'modelName', 'description', 'promptCaching',
                        'rateMultiplier', 'rateUnit', 'supportedInputTypes', 'tokenLimits'
                    }
                    for dummy in dummy_data.get('models', []):
                        if 'modelId' not in dummy or 'modelName' not in dummy:
                            print(f"{Fore.YELLOW}[DUMMY] Missing required fields, skipping{Style.RESET_ALL}")
                            continue
                        # Strip unknown fields
                        cleaned = {k: v for k, v in dummy.items() if k in valid_fields}
                        stripped = [k for k in dummy if k not in valid_fields]
                        if stripped:
                            print(f"{Fore.YELLOW}[DUMMY] Stripped unknown fields from {cleaned['modelId']}: {stripped}{Style.RESET_ALL}")
                        mid = cleaned['modelId']
                        # Override existing entry if same modelId, otherwise append
                        existing = next((i for i, m in enumerate(models) if m.get('modelId') == mid), None)
                        if existing is not None:
                            was_kiro = mid in self.kiro_model_ids
                            models[existing] = cleaned
                            label = 'Kiro' if was_kiro else 'custom'
                            print(f"{Fore.MAGENTA}[DUMMY OVERRIDE]{Style.RESET_ALL} Replaced {label} model: {mid}")
                            if not was_kiro:
                                self.custom_model_ids.add(mid)
                        else:
                            models.append(cleaned)
                            self.custom_model_ids.add(mid)
                            print(f"{Fore.MAGENTA}[DUMMY ADD]{Style.RESET_ALL} Added test model: {mid}")
                    print(f"{Fore.CYAN}[DUMMY] Loaded {len(dummy_data.get('models', []))} test model(s){Style.RESET_ALL}")
                except json.JSONDecodeError:
                    print(f"{Fore.YELLOW}[DUMMY] dummy_models.json is invalid JSON{Style.RESET_ALL}")
                except Exception as _e:
                    print(f"{Fore.YELLOW}[DUMMY] Error loading: {_e}{Style.RESET_ALL}")

        return models

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercept all requests"""
        self.request_count += 1
        
        # Block OTel telemetry endpoints (/v1/metrics, /v1/traces) only.
        # block_telemetry_always: block these even on Kiro passthrough, but ONLY
        #   when ALLOW_KIRO_MODELS=True (passthrough enabled). When False, follows
        #   block_aws_traffic state (adaptive — blocked with custom, allowed with Kiro).
        # ALLOW_TELEMETRY=False: always block, regardless of model state.
        _is_otel = ('telemetry' in flow.request.pretty_host and
                    flow.request.path in ('/v1/metrics', '/v1/traces'))
        if _is_otel:
            _bta = CONFIG.get('kiro_endpoint.block_telemetry_always', False) if CONFIG else False
            _should_block_otel = (
                not ALLOW_TELEMETRY                       # config: always block
                or self.block_aws_traffic                 # adaptive: custom model active
                or (_bta and ALLOW_KIRO_MODELS)           # always-block when passthrough enabled
            )
            if _should_block_otel:
                if DEBUG_MODE_ENABLED:
                    reason = ('config=false' if not ALLOW_TELEMETRY
                              else 'custom-model' if self.block_aws_traffic
                              else 'always-block+passthrough')
                    print(f"\n{Fore.RED}[BLOCKED TELEMETRY]{Style.RESET_ALL} {reason} — {flow.request.path}")
                flow.response = http.Response.make(
                    200, b'{"status":"ok"}',
                    {"Content-Type": "application/json"}
                )
                return
        # Non-OTel telemetry host requests (e.g. other paths) fall through to
        # other handlers or the strict whitelist
        
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
            # Block when custom model active. Return empty limits with no subscriptionInfo
            # so Kiro suppresses the credits/usage bar without breaking account state.
            if self.block_aws_traffic:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED} [BLOCKED USAGE LIMITS]{Style.RESET_ALL} custom model active")
                flow.response = http.Response.make(
                    200, b'{"limits":[]}',
                    {"Content-Type": "application/json"}
                )
                return
        
        # ── fake_login: treat as full block (no AWS communication at all) ─────
        # When fake_login is enabled, override block_aws_traffic and completions
        # so zero AWS traffic is sent, regardless of other config settings.
        _fake_login_active = CONFIG.get('kiro_endpoint.auth_fake_login', False) if CONFIG else False
        if _fake_login_active:
            # Block AWS/kiro.dev traffic that would actually reach their servers.
            # Exempt endpoints that we intercept and re-route ourselves — they never
            # reach AWS regardless, so blocking them here just breaks functionality.
            _is_routed_locally = (
                'generateAssistantResponse' in flow.request.path  # re-routed to custom provider
                or 'generatecompletions' in flow.request.path      # handled by completions logic
                or 'ListAvailableModels' in flow.request.path      # served from cache/config
                or 'auth.desktop.kiro.dev' in flow.request.pretty_host  # fake login handler
            )
            if not _is_routed_locally and (
                'amazonaws.com' in flow.request.pretty_host
                or 'kiro.dev' in flow.request.pretty_host
            ):
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED}[FAKE LOGIN BLOCK]{Style.RESET_ALL} {flow.request.path}")
                flow.response = http.Response.make(
                    200, b'{"status":"ok"}',
                    {'Content-Type': 'application/json'}
                )
                return

        # ── Block unexpected AWS requests when custom model is active ─────────
        # Any amazonaws.com request that isn't explicitly handled above
        # (generateAssistantResponse is handled separately below, completions
        # and ListAvailableModels above) should be suppressed to prevent
        # metering/credits events leaking back to Kiro.
        if self.block_aws_traffic and 'amazonaws.com' in flow.request.pretty_host:
            _aws_path = flow.request.path
            _allowed_aws = (
                'generateAssistantResponse' in _aws_path
                or 'ListAvailableModels' in _aws_path
                or 'generatecompletions' in _aws_path
            )
            if not _allowed_aws:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED}[BLOCKED AWS]{Style.RESET_ALL} {_aws_path} (custom model active)")
                flow.response = http.Response.make(
                    200, b'{"status":"ok"}',
                    {'Content-Type': 'application/json'}
                )
                return

        # ── Auth interception (fake_login) ──────────────────────────────────
        _fake_login = CONFIG.get('kiro_endpoint.auth_fake_login', False) if CONFIG else False
        if _fake_login and 'auth.desktop.kiro.dev' in flow.request.pretty_host:
            if '/oauth/token' in flow.request.path:
                import json as _json
                fake_token = {
                    'accessToken':  'fake-access-token-kiropipe-bypass',
                    'expiresIn':    315360000,
                    'profileArn':   'arn:aws:codewhisperer:us-east-1:000000000000:profile/KIROPIPE0',
                    'refreshToken': 'fake-refresh-token-kiropipe-bypass'
                }
                body = _json.dumps(fake_token).encode('utf-8')
                flow.response = http.Response.make(
                    200, body,
                    {'Content-Type': 'application/json', 'content-length': str(len(body))}
                )
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.GREEN}[FAKE LOGIN]{Style.RESET_ALL} Synthetic token returned")
                return
            elif '/logout' in flow.request.path:
                flow.response = http.Response.make(
                    200, b'{"message":"ok"}', {'Content-Type': 'application/json'}
                )
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.CYAN}[FAKE LOGOUT]{Style.RESET_ALL} Suppressed")
                return

        # ── /generatecompletions (inline autocomplete) ───────────────────────
        # Config 'completions.mode':
        #   'passthrough'  → always forward to AWS, regardless of model state
        #   None/null      → block when custom model active, passthrough for Kiro
        #   'current'      → use self.last_real_model's provider for completions
        #   '<model_name>' → always use that specific configured model
        if 'generatecompletions' in flow.request.path:
            _comp_cfg = CONFIG.get('completions', None) if CONFIG else None
            # Normalise: treat empty string same as None
            if _comp_cfg == '':
                _comp_cfg = None

            if _comp_cfg == 'passthrough':
                pass  # Fall through to AWS regardless of model state
            elif _comp_cfg is None:
                # Default: block when custom model active, pass through for Kiro
                if self.block_aws_traffic:
                    flow.response = http.Response.make(
                        200,
                        b'{"completions":[],"modelId":null,"nextToken":"","predictions":[]}',
                        {'Content-Type': 'application/json'}
                    )
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.RED}[COMPLETIONS BLOCKED]{Style.RESET_ALL} (null mode, custom model active)")
                    return
                # else: Kiro model active — fall through to AWS
            else:
                # Named model ('current' or a specific model_id) — route via its provider
                _target = (self.last_real_model if _comp_cfg == 'current' else _comp_cfg)
                _comp_model_info = CONFIG.get_model_info(_target) if _target else None
                if _comp_model_info:
                    try:
                        import httpx as _httpx, json as _json
                        _prov_name   = _comp_model_info['provider']
                        _prov_cfg    = CONFIG.get_provider_config(_prov_name) or {}
                        _comp_base   = _prov_cfg.get('api_base', '')
                        _comp_key    = _prov_cfg.get('api_key', '')
                        _comp_mdl    = _target
                        req_body     = _json.loads(flow.request.text)
                        left  = req_body.get('fileContext', {}).get('leftFileContent', '')
                        right = req_body.get('fileContext', {}).get('rightFileContent', '')
                        # FIM-style chat prompt — works with any instruction-following model
                        messages = [
                            {'role': 'system', 'content':
                             'You are a code completion assistant. '
                             'Return ONLY the code to insert at <CURSOR>. No explanation, no markdown.'},
                            {'role': 'user', 'content': f"{left}<CURSOR>{right}"}
                        ]
                        payload = {'model': _comp_mdl, 'messages': messages,
                                   'max_tokens': 128, 'temperature': 0, 'stream': False}
                        resp = _httpx.post(
                            f"{_comp_base}/chat/completions",
                            json=payload,
                            headers={'Authorization': f'Bearer {_comp_key}',
                                     'content-type': 'application/json'},
                            timeout=10.0
                        )
                        completion_text = ''
                        if resp.status_code == 200:
                            completion_text = (resp.json().get('choices', [{}])[0]
                                               .get('message', {}).get('content', ''))
                        result = _json.dumps({
                            'completions': [{'content': completion_text,
                                             'mostRelevantMissingImports': [], 'references': []}],
                            'modelId': None, 'nextToken': '', 'predictions': []
                        }).encode('utf-8')
                        flow.response = http.Response.make(
                            200, result, {'Content-Type': 'application/json'}
                        )
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.CYAN}[COMPLETIONS]{Style.RESET_ALL} Served via {_prov_name}/{_comp_mdl}")
                    except Exception as _e:
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.RED}[COMPLETIONS ERROR]{Style.RESET_ALL} {_e}")
                        flow.response = http.Response.make(
                            200,
                            b'{"completions":[],"modelId":null,"nextToken":"","predictions":[]}',
                            {'Content-Type': 'application/json'}
                        )
                else:
                    # Unknown model — block
                    flow.response = http.Response.make(
                        200,
                        b'{"completions":[],"modelId":null,"nextToken":"","predictions":[]}',
                        {'Content-Type': 'application/json'}
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
        
        # Model list strategy:
        #  - Warm cache: Kiro AWS models known → serve Kiro-first + config immediately
        #  - Cold start + AWS reachable: let request through; response() builds final list
        #  - Cold start + AWS blocked (fake_login etc.): serve config-only immediately
        if 'ListAvailableModels' in flow.request.path or self._model_list_dirty:
            self._model_list_dirty = False
            aws_blocked = CONFIG.get('kiro_endpoint.auth_fake_login', False) if CONFIG else False
            cold_start  = not self._kiro_models_cache and ALLOW_KIRO_MODELS

            if cold_start and not aws_blocked and 'ListAvailableModels' in flow.request.path:
                # Let request reach AWS; response() will build and send the definitive list
                pass
            else:
                # Either warm (cache populated) or AWS blocked → serve now
                flow.response = http.Response.make(
                    200,
                    json.dumps({'models': self._build_model_list()}).encode('utf-8'),
                    {'Content-Type': 'application/json'}
                )
                if DEBUG_MODE_ENABLED:
                    src = 'warm-cache' if self._kiro_models_cache else 'config-only (AWS blocked)'
                    print(f"{Fore.CYAN}[MODEL LIST]{Style.RESET_ALL} Served from {src}")
                return

        # Detect model selection and route to custom provider if needed
        if 'generateAssistantResponse' in flow.request.path:
            if DEBUG_MODE_ENABLED:
                print(f"\n{Fore.MAGENTA}[DEBUG] Routing code reached for generateAssistantResponse{Style.RESET_ALL}")
            
            # Step 1: Parse request to determine which model is being used
            selected_model = None
            is_intent_classification = False
            request_hash = None
            try:
                body = json.loads(flow.request.text)
                # Model ID is nested in conversationState.currentMessage.userInputMessage
                selected_model = (
                    body.get('conversationState', {})
                    .get('currentMessage', {})
                    .get('userInputMessage', {})
                    .get('modelId')
                )
                
                # Check if this is an intent classification request
                is_intent_classification = flow.request.headers.get('x-amzn-kiro-agent-mode') == 'intent-classification'
                
                # Create a hash of the request to detect duplicates
                import hashlib
                request_content = body.get('conversationState', {}).get('currentMessage', {}).get('userInputMessage', {}).get('content', '')
                request_hash = hashlib.md5(f"{selected_model}:{request_content}".encode()).hexdigest()[:8]
                
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.MAGENTA}[DEBUG] Parsed model from request: {selected_model}{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}[DEBUG] Intent classification: {is_intent_classification}{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}[DEBUG] Request hash: {request_hash}{Style.RESET_ALL}")
                    if is_intent_classification:
                        print(f"{Fore.MAGENTA}[DEBUG] Header value: {flow.request.headers.get('x-amzn-kiro-agent-mode')}{Style.RESET_ALL}")
            except Exception as e:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.RED}[ERROR] Failed to parse request body: {e}{Style.RESET_ALL}")
            
            # Step 2: If we found a model, update tracking and check if we need to route
            if selected_model:
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.MAGENTA}[DEBUG] Model found, updating tracking{Style.RESET_ALL}")
                
                # Check if this is a simple-task (intent classification) request
                if selected_model == 'simple-task':
                    with self.simple_task_lock:
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.YELLOW}[SIMPLE-TASK] Received, holding request...{Style.RESET_ALL}")
                        
                        # Store this flow to hold it
                        self.pending_simple_task = {
                            'flow': flow,
                            'timestamp': time.time(),
                            'body': body,
                            'request_hash': request_hash
                        }
                        
                        # Don't respond yet - just return and hold the request
                        # The next request will decide what to do with this
                        return
                
                # This is a real model request (not simple-task)
                # Check if we have a pending simple-task
                with self.simple_task_lock:
                    if self.pending_simple_task:
                        pending_flow = self.pending_simple_task['flow']
                        pending_time = self.pending_simple_task['timestamp']
                        age = time.time() - pending_time
                        
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.YELLOW}[SIMPLE-TASK] Found pending request (age: {age:.3f}s){Style.RESET_ALL}")
                        
                        # Check if this model is passthrough or custom
                        model_info = CONFIG.get_model_info(selected_model)
                        is_passthrough = model_info and model_info['provider'] == 'kiro'
                        
                        if is_passthrough:
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.GREEN}[SIMPLE-TASK] Next model is passthrough, allowing simple-task through{Style.RESET_ALL}")

                            # Clear the pending request - it will go through to AWS naturally
                            self.pending_simple_task = None
                            self._custom_routed_once = False  # User explicitly chose Kiro

                            # Now continue processing this request normally
                        else:
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.YELLOW}[SIMPLE-TASK] Next model is custom, blocking simple-task{Style.RESET_ALL}")
                            
                            # Block the pending simple-task by sending a mock response
                            from engine.event_stream_encoder import encode_text_chunk

                            mock_response = encode_text_chunk("proceed")
                            
                            pending_flow.response = http.Response.make(
                                200,
                                mock_response,
                                {
                                    'Content-Type': 'application/vnd.amazon.eventstream',
                                    'x-amzn-RequestId': 'intent-bypass-simple-task'
                                }
                            )
                            
                            # Clear the pending request
                            self.pending_simple_task = None
                            
                            # Now continue processing this custom model request
                
                # Update current model tracking
                old_model = self.current_model
                self.current_model = selected_model
                self.last_real_model = selected_model  # Track last non-simple-task model
                
                # Step 3: Determine routing based on THIS request's model
                model_info = CONFIG.get_model_info(selected_model)
                
                # Determine if this specific request is for a Kiro or custom model
                is_kiro_request = False
                if model_info:
                    is_kiro_request = model_info['provider'] == 'kiro'
                else:
                    is_kiro_request = selected_model in self.kiro_model_ids
                
                # Update global telemetry blocking state based on model type
                # This only affects telemetry/metrics, not generateAssistantResponse routing
                old_block_state = self.block_aws_traffic
                if is_kiro_request:
                    # Passthrough model - allow telemetry
                    self.block_aws_traffic = False
                    if old_block_state and DEBUG_MODE_ENABLED:
                        print(f"{Fore.GREEN}[TELEMETRY] Unblocking (passthrough model){Style.RESET_ALL}")
                else:
                    # Custom model - block telemetry
                    self.block_aws_traffic = True
                    self._custom_routed_once = True
                    if not old_block_state and DEBUG_MODE_ENABLED:
                        print(f"{Fore.YELLOW}[TELEMETRY] Blocking (custom model){Style.RESET_ALL}")
                
                if DEBUG_MODE_ENABLED and selected_model != old_model:
                    model_type = "Kiro" if is_kiro_request else "Custom"
                    print(f"{Fore.CYAN}[MODEL SELECTED] {selected_model} ({model_type}){Style.RESET_ALL}")
                
                # Step 4: Route this specific request based on its model
                # If it's a Kiro model, let it pass through to AWS
                # If it's a custom model, route to custom provider below
                if is_kiro_request:
                    # Block parallel if: was in custom mode (old_block_state) OR
                    # this is the first-switch where a custom model was just routed
                    # (_custom_routed_once covers the race on the very first switch).
                    if old_block_state or self._custom_routed_once:
                        # A custom model was active — suppress this parallel Kiro request
                        # so it never reaches AWS and returns metering/credits events.
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.RED}[BLOCKED PARALLEL KIRO]{Style.RESET_ALL} Custom model was active, suppressing Kiro chat request")
                        flow.response = http.Response.make(
                            200, b'',
                            {'Content-Type': 'application/vnd.amazon.eventstream',
                             'x-amzn-RequestId': 'blocked-kiro-parallel'}
                        )
                        return
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.GREEN}[ROUTING] Passthrough to AWS Q{Style.RESET_ALL}")
                    # Passthrough — let it reach AWS naturally
                    return
                
                # At this point, we know it's a custom model request
                if DEBUG_MODE_ENABLED:
                    print(f"{Fore.YELLOW}[ROUTING CHECK] Model: {selected_model}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}[ROUTING CHECK] Model info from config: {model_info}{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}[ROUTING CHECK] Provider: {model_info['provider'] if model_info else 'None'}{Style.RESET_ALL}")
                
                # Step 5: Route to custom provider
                if model_info:
                    # Direct API call to custom provider (no bridge needed)
                    provider_name = model_info['provider']
                    provider_config = CONFIG.get_provider_config(provider_name)
                    
                    if DEBUG_MODE_ENABLED:
                        print(f"\n{Fore.CYAN} [CUSTOM PROVIDER]{Style.RESET_ALL} Routing to {Fore.GREEN}{provider_name}{Style.RESET_ALL}")
                        print(f"  {Fore.CYAN}Model:{Style.RESET_ALL} {model_info['model']['name']}")
                    
                    try:
                        import httpx
                        from engine.retry_handler import RetryHandler, RetryConfig
                        from engine.usage_tracker import UsageTracker
                        
                        # Initialize retry handler
                        retry_handler = RetryHandler(RetryConfig(
                            max_retries=7,
                            base_delay=0.5,
                            max_delay=30.0,
                            exponent_cap=4,
                            jitter_factor=0.25,
                            timeout=300.0
                        ))
                        
                        # Initialize usage tracker (shared instance) - always initialize
                        if not hasattr(self, 'usage_tracker') or self.usage_tracker is None:
                            self.usage_tracker = UsageTracker()
                        
                        # Parse AWS request
                        aws_body = json.loads(flow.request.text)
                        
                        # Extract conversation ID for usage tracking
                        conversation_id = aws_body.get('conversationState', {}).get('conversationId', 'unknown')
                        
                        # Get provider type to determine how to route
                        provider_type = provider_config.get('type', provider_name)
                        
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.YELLOW}[ROUTING] Provider: {provider_name}, Type: {provider_type}{Style.RESET_ALL}")

                        if provider_type == 'anthropic':
                            # Import request translator
                            from engine.request_translator import translate_to_anthropic
                            
                            # Transform to Anthropic format using full translation
                            api_base = provider_config.get('api_base', 'https://api.anthropic.com/v1')
                            api_key = provider_config.get('api_key')
                            
                            if not api_key:
                                raise Exception("Anthropic API key not configured")
                            
                            # Use full request translation (includes history, tools, tool results)
                            anthropic_request = translate_to_anthropic(
                                aws_body,
                                model=self.current_model,
                                max_tokens=4096,
                                tool_call_cache=self.tool_call_cache
                            )
                            
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.CYAN} [ANTHROPIC]{Style.RESET_ALL} Calling API...")
                                print(f"  {Fore.CYAN}Model:{Style.RESET_ALL} {self.current_model}")
                                print(f"  {Fore.CYAN}Messages:{Style.RESET_ALL} {len(anthropic_request.get('messages', []))}")
                                if 'tools' in anthropic_request:
                                    print(f"  {Fore.CYAN}Tools:{Style.RESET_ALL} {len(anthropic_request['tools'])}")
                            
                            if DEBUG_MODE_ENABLED:
                                print(f"\n{Fore.YELLOW}[DEBUG] Message structure:{Style.RESET_ALL}")
                                for i, msg in enumerate(anthropic_request.get('messages', [])):
                                    role = msg.get('role')
                                    body = msg.get('content')
                                    if isinstance(body, list):
                                        types = [b.get('type') for b in body]
                                        has_tu = 'tool_use' in types
                                        has_tr = 'tool_result' in types
                                        print(f"  {i+1}. {Fore.CYAN}{role}{Style.RESET_ALL} (has_tool_use: {has_tu}, has_tool_result: {has_tr})")
                                        if has_tu:
                                            for b in body:
                                                if b.get('type') == 'tool_use':
                                                    print(f"     - {b['name']} (id: {b['id']})")
                                    else:
                                        preview = str(body or '')[:50]
                                        print(f"  {i+1}. {Fore.GREEN}{role}{Style.RESET_ALL}: {preview}...")
                                print()

                            # Call Anthropic API with streaming + retry (same loop as OpenAI branch)
                            from engine.response_translator import translate_anthropic_stream
                            last_error_content = None
                            last_error_status = 500
                            with httpx.Client(timeout=300.0) as client:
                                for attempt in range(retry_handler.config.max_retries + 1):
                                    response_stream = client.stream(
                                        "POST",
                                        f"{api_base}/messages",
                                        json=anthropic_request,
                                        headers={
                                            "x-api-key": api_key,
                                            "anthropic-version": "2023-06-01",
                                            "content-type": "application/json"
                                        }
                                    )
                                    with response_stream as response:
                                        if DEBUG_MODE_ENABLED:
                                            print(f"{Fore.GREEN} [ANTHROPIC]{Style.RESET_ALL} Response: {Fore.CYAN}{response.status_code}{Style.RESET_ALL} (attempt {attempt+1})")

                                        if response.status_code != 200:
                                            last_error_content = response.read()
                                            last_error_status = response.status_code
                                            if retry_handler.should_retry(response.status_code, attempt):
                                                delay = retry_handler.calculate_delay(attempt)
                                                if DEBUG_MODE_ENABLED:
                                                    print(f"{Fore.YELLOW}[RETRY]{Style.RESET_ALL} Status {response.status_code}, retrying in {delay:.2f}s (attempt {attempt+1}/{retry_handler.config.max_retries})")
                                                time.sleep(delay)
                                                continue
                                            flow.response = http.Response.make(
                                                last_error_status,
                                                last_error_content,
                                                {'content-type': 'application/json'}
                                            )
                                            return

                                        def anthropic_event_generator():
                                            """Parse Anthropic SSE stream into event objects"""
                                            buffer = ""
                                            for chunk in response.iter_text():
                                                buffer += chunk
                                                while '\n' in buffer:
                                                    line, buffer = buffer.split('\n', 1)
                                                    line = line.strip()
                                                    if line.startswith('data: '):
                                                        data = line[6:]
                                                        if data and data != '[DONE]':
                                                            try:
                                                                yield json.loads(data)
                                                            except json.JSONDecodeError:
                                                                pass

                                        def usage_callback(input_tokens, output_tokens):
                                            self.usage_tracker.track_request(
                                                conversation_id=conversation_id,
                                                model=self.current_model,
                                                input_tokens=input_tokens,
                                                output_tokens=output_tokens,
                                                metadata={'provider': 'anthropic'}
                                            )
                                            if DEBUG_MODE_ENABLED:
                                                print(f"{Fore.CYAN} [USAGE]{Style.RESET_ALL} Tracked: {input_tokens} in, {output_tokens} out")

                                        tool_calls_out: Dict[str, Any] = {}
                                        aws_binary = b''.join(translate_anthropic_stream(
                                            anthropic_event_generator(),
                                            include_usage=False,
                                            usage_callback=usage_callback,
                                            tool_calls_out=tool_calls_out,
                                            context_window=self._context_window_cache.get(
                                                self.current_model,
                                                (CONFIG.get_model_info(self.current_model) or {}).get('context_window', 200000) if CONFIG else 200000
                                            )
                                        ))
                                        self.tool_call_cache.update(tool_calls_out)

                                        if DEBUG_MODE_ENABLED:
                                            print(f"{Fore.GREEN} [ANTHROPIC]{Style.RESET_ALL} Translated to AWS format: {Fore.YELLOW}{len(aws_binary)} bytes{Style.RESET_ALL}")

                                        flow.response = http.Response.make(
                                            200,
                                            aws_binary,
                                            {
                                                'Content-Type': 'application/vnd.amazon.eventstream',
                                                'x-amzn-RequestId': f'anthropic-{self.current_model}'
                                            }
                                        )
                                        return  # success — exit retry loop
                                # All retries exhausted — return last error
                                if last_error_content is not None:
                                    flow.response = http.Response.make(
                                        last_error_status,
                                        last_error_content,
                                        {'content-type': 'application/json'}
                                    )
                                    return
                        
                        elif provider_type == 'openai':
                            # Direct OpenAI API support (without LiteLLM)
                            # Import request translator
                            from engine.request_translator import translate_to_openai
                            
                            # Transform to OpenAI format using full translation
                            api_base = provider_config.get('api_base', 'https://api.openai.com/v1')
                            api_key = provider_config.get('api_key')
                            
                            if not api_key:
                                raise Exception("OpenAI API key not configured")
                            
                            # Use full request translation (includes history, tools, tool results)
                            openai_request = translate_to_openai(
                                aws_body,
                                model=self.current_model,
                                max_tokens=4096,
                                tool_call_cache=self.tool_call_cache
                            )

                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.CYAN} [OPENAI]{Style.RESET_ALL} Calling API...")
                                print(f"  {Fore.CYAN}Model:{Style.RESET_ALL} {self.current_model}")
                                print(f"  {Fore.CYAN}Messages:{Style.RESET_ALL} {len(openai_request.get('messages', []))}")
                                if 'tools' in openai_request:
                                    print(f"  {Fore.CYAN}Tools:{Style.RESET_ALL} {len(openai_request['tools'])}")
                                
                                # Debug: Print message structure to see if tool results are included
                                print(f"\n{Fore.YELLOW}[DEBUG] Message structure:{Style.RESET_ALL}")
                                for i, msg in enumerate(openai_request.get('messages', [])):
                                    role = msg.get('role')
                                    if role == 'tool':
                                        print(f"  {i+1}. {Fore.MAGENTA}tool{Style.RESET_ALL} (tool_call_id: {msg.get('tool_call_id', 'N/A')})")
                                        content_preview = msg.get('content', '')[:50]
                                        print(f"     Content: {content_preview}...")
                                    elif role == 'assistant':
                                        has_tool_calls = 'tool_calls' in msg
                                        print(f"  {i+1}. {Fore.CYAN}assistant{Style.RESET_ALL} (has_tool_calls: {has_tool_calls})")
                                        if has_tool_calls:
                                            for tc in msg.get('tool_calls', []):
                                                print(f"     - {tc['function']['name']} (id: {tc['id']})")
                                    else:
                                        content_preview = str(msg.get('content', ''))[:50]
                                        print(f"  {i+1}. {Fore.GREEN}{role}{Style.RESET_ALL}: {content_preview}...")
                                print()
                            
                            # Call OpenAI-compatible API with streaming + retry.
                            # We can't use execute_with_retry (it closes the stream), so we
                            # wrap the whole request in a manual loop using retry_handler's
                            # delay/should_retry helpers — same backoff curve as LiteLLM.
                            from engine.response_translator import translate_openai_stream
                            last_error_content = None
                            last_error_status = 500
                            with httpx.Client(timeout=300.0) as client:
                                for attempt in range(retry_handler.config.max_retries + 1):
                                    response_stream = client.stream(
                                        "POST",
                                        f"{api_base}/chat/completions",
                                        json=openai_request,
                                        headers={
                                            "Authorization": f"Bearer {api_key}",
                                            "content-type": "application/json"
                                        }
                                    )
                                    with response_stream as response:
                                        if DEBUG_MODE_ENABLED:
                                            print(f"{Fore.GREEN} [OPENAI]{Style.RESET_ALL} Response: {Fore.CYAN}{response.status_code}{Style.RESET_ALL} (attempt {attempt+1})")
                                        
                                        if response.status_code != 200:
                                            last_error_content = response.read()
                                            last_error_status = response.status_code
                                            if retry_handler.should_retry(response.status_code, attempt):
                                                delay = retry_handler.calculate_delay(attempt)
                                                if DEBUG_MODE_ENABLED:
                                                    print(f"{Fore.YELLOW}[RETRY]{Style.RESET_ALL} Status {response.status_code}, retrying in {delay:.2f}s (attempt {attempt+1}/{retry_handler.config.max_retries})")
                                                time.sleep(delay)
                                                continue
                                            # Non-retryable error — return immediately
                                            flow.response = http.Response.make(
                                                last_error_status,
                                                last_error_content,
                                                {'content-type': 'application/json'}
                                            )
                                            return
                                        
                                        # Learn context window from response headers
                                        _ctx_hdr = (response.headers.get('x-ratelimit-limit-tokens')
                                                    or response.headers.get('x-ratelimit-limit-context'))
                                        if _ctx_hdr:
                                            try:
                                                self._context_window_cache[self.current_model] = int(_ctx_hdr)
                                            except (ValueError, TypeError):
                                                pass

                                        # 200 OK — consume and translate the stream.
                                        # Handles three common response formats:
                                        #  a) Standard SSE:  'data: {...}\n'
                                        #  b) Bare JSON lines: '{...}\n'  (some local proxies)
                                        #  c) Non-streaming: single JSON object with 'choices'
                                        def openai_event_generator():
                                            """Parse OpenAI response into event objects, tolerating non-SSE formats"""
                                            buffer = ""
                                            yielded = False
                                            for chunk in response.iter_text():
                                                buffer += chunk
                                                while '\n' in buffer:
                                                    line, buffer = buffer.split('\n', 1)
                                                    line = line.strip()
                                                    if not line:
                                                        continue
                                                    # Standard SSE prefix
                                                    if line.startswith('data: '):
                                                        data = line[6:]
                                                        if data and data != '[DONE]':
                                                            try:
                                                                yield json.loads(data)
                                                                yielded = True
                                                            except json.JSONDecodeError:
                                                                pass
                                                    # Bare JSON line (no 'data: ' prefix)
                                                    elif line.startswith('{'):
                                                        try:
                                                            yield json.loads(line)
                                                            yielded = True
                                                        except json.JSONDecodeError:
                                                            pass
                                            # Flush any remaining buffer content
                                            if buffer.strip() and buffer.strip().startswith('{'):
                                                try:
                                                    yield json.loads(buffer.strip())
                                                    yielded = True
                                                except json.JSONDecodeError:
                                                    pass
                                            # Non-streaming fallback: single JSON object with 'choices'
                                            # Some proxies return this even when stream=True is requested.
                                            if not yielded and buffer.strip():
                                                try:
                                                    obj = json.loads(buffer.strip())
                                                    if 'choices' in obj:
                                                        # Wrap non-streaming response as a single SSE chunk
                                                        choice = obj['choices'][0]
                                                        msg = choice.get('message', {})
                                                        yield {
                                                            'choices': [{
                                                                'delta': {
                                                                    'content':    msg.get('content'),
                                                                    'tool_calls': msg.get('tool_calls'),
                                                                },
                                                                'finish_reason': choice.get('finish_reason', 'stop'),
                                                            }],
                                                            'usage': obj.get('usage', {}),
                                                        }
                                                except json.JSONDecodeError:
                                                    pass
                                        
                                        def usage_callback(input_tokens, output_tokens):
                                            self.usage_tracker.track_request(
                                                conversation_id=conversation_id,
                                                model=self.current_model,
                                                input_tokens=input_tokens,
                                                output_tokens=output_tokens,
                                                metadata={'provider': 'openai'}
                                            )
                                            if DEBUG_MODE_ENABLED:
                                                print(f"{Fore.CYAN} [USAGE]{Style.RESET_ALL} Tracked: {input_tokens} in, {output_tokens} out")
                                        
                                        tool_calls_out: Dict[str, Any] = {}
                                        aws_binary = b''.join(translate_openai_stream(
                                            openai_event_generator(),
                                            include_usage=False,
                                            usage_callback=usage_callback,
                                            tool_calls_out=tool_calls_out,
                                            context_window=self._context_window_cache.get(
                                                self.current_model,
                                                (CONFIG.get_model_info(self.current_model) or {}).get('context_window', 200000) if CONFIG else 200000
                                            )
                                        ))
                                        self.tool_call_cache.update(tool_calls_out)

                                        if DEBUG_MODE_ENABLED:
                                            print(f"{Fore.GREEN} [OPENAI]{Style.RESET_ALL} Translated to AWS format: {Fore.YELLOW}{len(aws_binary)} bytes{Style.RESET_ALL}")
                                        
                                        flow.response = http.Response.make(
                                            200,
                                            aws_binary,
                                            {
                                                'Content-Type': 'application/vnd.amazon.eventstream',
                                                'x-amzn-RequestId': f'openai-{self.current_model}'
                                            }
                                        )
                                        return  # success — exit retry loop
                                # All retries exhausted — return last error
                                if last_error_content is not None:
                                    flow.response = http.Response.make(
                                        last_error_status,
                                        last_error_content,
                                        {'content-type': 'application/json'}
                                    )
                                    return
                        
                        elif provider_type == 'litellm':
                            # Use LiteLLM for universal provider support
                            try:
                                from litellm import completion
                            except ImportError:
                                raise Exception("LiteLLM not installed. Run: pip install litellm")
                            
                            # Import request translator
                            from engine.request_translator import translate_to_openai
                            
                            # Translate to OpenAI format using full translation
                            openai_request = translate_to_openai(
                                aws_body,
                                model=self.current_model,
                                max_tokens=4096,
                                tool_call_cache=self.tool_call_cache
                            )

                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.CYAN} [LITELLM]{Style.RESET_ALL} Using model: {self.current_model}")
                                print(f"  {Fore.CYAN}Messages:{Style.RESET_ALL} {len(openai_request.get('messages', []))}")
                                if 'tools' in openai_request:
                                    print(f"  {Fore.CYAN}Tools:{Style.RESET_ALL} {len(openai_request['tools'])}")
                            
                            # Import response translator
                            from engine.response_translator import translate_openai_stream
                            
                            # Define API call function for retry handler
                            def make_litellm_call():
                                return completion(
                                    model=self.current_model,
                                    messages=openai_request['messages'],
                                    tools=openai_request.get('tools'),
                                    max_tokens=openai_request.get('max_tokens', 4096),
                                    stream=True
                                )
                            
                            # Execute with retry logic
                            response_stream = retry_handler.execute_with_retry(make_litellm_call)
                            
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.GREEN} [LITELLM]{Style.RESET_ALL} Streaming response received")
                            
                            # Convert LiteLLM stream to AWS format
                            # LiteLLM returns OpenAI-compatible chunks
                            def litellm_event_generator():
                                """Convert LiteLLM chunks to dict format"""
                                for chunk in response_stream:
                                    # LiteLLM returns ModelResponse objects, convert to dict
                                    if hasattr(chunk, 'model_dump'):
                                        yield chunk.model_dump()
                                    elif hasattr(chunk, 'dict'):
                                        yield chunk.dict()
                                    else:
                                        yield dict(chunk)
                            
                            # Create usage callback for tracking
                            def usage_callback(input_tokens, output_tokens):
                                self.usage_tracker.track_request(
                                    conversation_id=conversation_id,
                                    model=self.current_model,
                                    input_tokens=input_tokens,
                                    output_tokens=output_tokens,
                                    metadata={'provider': 'litellm'}
                                )
                                if DEBUG_MODE_ENABLED:
                                    print(f"{Fore.CYAN} [USAGE]{Style.RESET_ALL} Tracked: {input_tokens} in, {output_tokens} out")
                            
                            # Translate to AWS event stream with usage tracking
                            # NOTE: Don't include usage/metering for custom models to avoid showing "Credits used"
                            tool_calls_out: Dict[str, Any] = {}
                            aws_binary = b''.join(translate_openai_stream(
                                litellm_event_generator(),
                                include_usage=False,
                                usage_callback=usage_callback,
                                tool_calls_out=tool_calls_out,
                                context_window=self._context_window_cache.get(
                                    self.current_model,
                                    (CONFIG.get_model_info(self.current_model) or {}).get('context_window', 200000) if CONFIG else 200000
                                )
                            ))
                            # Cache any tool calls streamed out for the next round-trip.
                            self.tool_call_cache.update(tool_calls_out)
                            
                            if DEBUG_MODE_ENABLED:
                                print(f"{Fore.GREEN} [LITELLM]{Style.RESET_ALL} Translated to AWS format: {Fore.YELLOW}{len(aws_binary)} bytes{Style.RESET_ALL}")
                            
                            # Return AWS event stream response
                            flow.response = http.Response.make(
                                200,
                                aws_binary,
                                {
                                    'Content-Type': 'application/vnd.amazon.eventstream',
                                    'x-amzn-RequestId': f'litellm-{self.current_model}'
                                }
                            )
                            return
                        
                        else:
                            # Unknown provider type
                            raise Exception(f"Provider type '{provider_type}' not supported. Use 'anthropic', 'openai', or 'litellm'.")
                        
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
            
            # Prevent memory leak: keep only last N requests
            if len(self.aws_requests) > self.max_requests_history:
                self.aws_requests = self.aws_requests[-self.max_requests_history:]

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

        # ── Strict whitelist: block unhandled amazonaws/kiro.dev paths ────────
        _strict = CONFIG.get('kiro_endpoint.strict_whitelist', False) if CONFIG else False
        _is_aws_or_kiro = (
            'amazonaws.com' in flow.request.pretty_host
            or 'kiro.dev' in flow.request.pretty_host
        )
        # Paths we intentionally let pass through to AWS (don't whitelist-block)
        _intentional_passthrough = (
            'ListAvailableModels' in flow.request.path     # cold-start model fetch
            or 'generatecompletions' in flow.request.path  # completions in passthrough mode
            or 'getUsageLimits' in flow.request.path       # handled above
            or 'auth.desktop.kiro.dev' in flow.request.pretty_host  # auth flows
        )
        if _strict and flow.response is None and _is_aws_or_kiro and not _intentional_passthrough:
            if DEBUG_MODE_ENABLED:
                print(f"{Fore.RED}[STRICT WHITELIST BLOCKED]{Style.RESET_ALL} {flow.request.path}")
            flow.response = http.Response.make(
                200, b'{"status":"ok"}', {'Content-Type': 'application/json'}
            )

        # ── Catch-all: block any generateAssistantResponse that hasn't been
        # handled by our routing and would fall through to AWS while a custom
        # model is active. Legitimate custom-model requests set flow.response
        # before returning; legitimate Kiro passthroughs return early at the
        # routing block. Only unhandled parallel/background requests reach here.
        if (
            self.block_aws_traffic
            and flow.response is None
            and 'generateAssistantResponse' in flow.request.path
        ):
            if DEBUG_MODE_ENABLED:
                print(f"{Fore.RED}[BLOCKED PARALLEL]{Style.RESET_ALL} Suppressing unhandled generateAssistantResponse (custom model active)")
            flow.response = http.Response.make(
                200, b'',
                {
                    'Content-Type': 'application/vnd.amazon.eventstream',
                    'x-amzn-RequestId': 'blocked-parallel-request'
                }
            )

    def response(self, flow: http.HTTPFlow) -> None:
            """Intercept all responses"""

            # On cold-start, AWS sends its model list here. Cache the Kiro models,
            # then replace the response with our definitive list (Kiro first + config).
            if 'ListAvailableModels' in flow.request.path and flow.response.status_code == 200:
                try:
                    aws_data = json.loads(flow.response.text)
                    aws_models = aws_data.get('models', [])

                    # Normalise rateUnit and cache all Kiro-native entries
                    for m in aws_models:
                        if m.get('rateUnit') == 'Credit':
                            m['rateUnit'] = 'Kiro Credits'
                        mid = m.get('modelId')
                        if mid:
                            self.kiro_model_ids.add(mid)
                    self._kiro_models_cache = aws_models  # full list, Kiro order preserved

                    # Build and send the definitive combined list
                    combined = self._build_model_list()
                    combined_json = json.dumps({'models': combined}).encode('utf-8')
                    flow.response.content = combined_json
                    flow.response.headers['content-length'] = str(len(combined_json))

                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.CYAN}[MODEL LIST]{Style.RESET_ALL} Cold-start: "
                              f"{len(aws_models)} Kiro + {len(combined)-len(aws_models)} custom → "
                              f"{len(combined)} total sent to client")
                except Exception as e:
                    if DEBUG_MODE_ENABLED:
                        print(f"{Fore.RED}[MODEL LIST ERROR]{Style.RESET_ALL} {e}")

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


                # Strip metering/contextUsage frames from any pass-through AWS
                # event stream responses while custom models are active.
                if (
                    (self.block_aws_traffic or self._custom_routed_once)
                    and 'generateAssistantResponse' in flow.request.path
                    and flow.response.content
                    and 'application/vnd.amazon.eventstream' in flow.response.headers.get('content-type', '')
                ):
                    filtered = _strip_metering_events(flow.response.content)
                    if filtered != flow.response.content:
                        flow.response.content = filtered
                        flow.response.headers['content-length'] = str(len(filtered))
                        if DEBUG_MODE_ENABLED:
                            print(f"{Fore.CYAN}[METERING STRIPPED]{Style.RESET_ALL} Removed metering from pass-through AWS response")

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
                ['powershell', '-NoProfile', '-NonInteractive', '-Command',
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
    print(f"{'='*60}\n")
   