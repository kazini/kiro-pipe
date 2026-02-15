#!/usr/bin/env python3
"""
Frida Attachment Script for Kiro Application
================================================

Purpose: Attach Frida to running Kiro process and inject hooks for:
1. Certificate validation bypass
2. HTTPS request interception and logging
3. Request redirection to localhost:8888

Modes:
- ATTACH: Attach to running Kiro process (default)
- SPAWN: Spawn Kiro with Frida from start (bypasses anti-debug)

Usage:
    python attach.py --hook combined      # Use all hooks (attach mode)
    python attach.py --hook cert-only     # Only certificate bypass
    python attach.py --hook logger        # Only request logging
    python attach.py --hook redirect      # Only request redirection
    python attach.py --list               # List running processes
    python attach.py --spawn              # Spawn Kiro with hooks (anti-debug bypass)
    python attach.py --spawn --hook kiro_api_hook  # Spawn with specific hook
"""

import frida
import sys
import os
import argparse
import time
from pathlib import Path

# Optional: psutil for network detection
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class FridaKiroAttacher:
    def __init__(self, target_process="Kiro"):
        self.target_process = target_process
        self.device = frida.get_local_device()
        self.session = None
        self.script = None
        self.hooks_dir = Path(__file__).parent
        self.monitored_pids = set()
        self.child_sessions = []

    def find_process(self):
        """Find Kiro process in running processes or use PID directly"""
        # Check if target_process is a PID (numeric)
        try:
            pid = int(self.target_process)
            # Verify PID exists
            processes = self.device.enumerate_processes()
            for process in processes:
                if process.pid == pid:
                    print(f"{Colors.GREEN}✓ Found process by PID: {process.name} (PID: {process.pid}){Colors.ENDC}")
                    return process.pid
            print(f"{Colors.RED}✗ PID {pid} not found or not running{Colors.ENDC}")
            return None
        except ValueError:
            # Not a PID, treat as process name
            pass
        
        # Search by process name
        processes = self.device.enumerate_processes()
        
        for process in processes:
            if self.target_process.lower() in process.name.lower():
                print(f"{Colors.GREEN}✓ Found process: {process.name} (PID: {process.pid}){Colors.ENDC}")
                return process.pid
        
        print(f"{Colors.RED}✗ Could not find process: {self.target_process}{Colors.ENDC}")
        return None

    def find_kiro_executable(self):
        """Find Kiro.exe location"""
        common_paths = [
            r"C:\Users\{username}\AppData\Local\Programs\Kiro\Kiro.exe",
            r"C:\Program Files\Kiro\Kiro.exe",
            r"C:\Program Files (x86)\Kiro\Kiro.exe",
        ]
        
        username = os.environ.get('USERNAME', '')
        
        for path_template in common_paths:
            path = path_template.format(username=username)
            if Path(path).exists():
                return path
        
        return None

    def list_processes(self):
        """List all running processes"""
        processes = self.device.enumerate_processes()
        print(f"\n{Colors.BOLD}Running Processes:{Colors.ENDC}")
        print("-" * 60)
        
        for proc in processes:
            print(f"  {proc.name:<40} (PID: {proc.pid:>6})")

    def load_hook(self, hook_name):
        """Load hook script from file"""
        hook_file = self.hooks_dir / f"{hook_name}.js"
        
        if not hook_file.exists():
            print(f"{Colors.RED}✗ Hook file not found: {hook_file}{Colors.ENDC}")
            return None
        
        try:
            with open(hook_file, 'r', encoding='utf-8') as f:
                script_code = f.read()
            print(f"{Colors.GREEN}✓ Loaded hook: {hook_name}{Colors.ENDC}")
            return script_code
        except Exception as e:
            print(f"{Colors.RED}✗ Error loading hook {hook_name}: {e}{Colors.ENDC}")
            return None

    def on_message(self, message, data):
        """Handle messages from Frida script"""
        try:
            if message['type'] == 'send':
                payload = message.get('payload', '')
                
                # Color code different message types
                if 'ERROR' in str(payload):
                    print(f"{Colors.RED}[ERROR] {payload}{Colors.ENDC}")
                elif 'SUCCESS' in str(payload):
                    print(f"{Colors.GREEN}[SUCCESS] {payload}{Colors.ENDC}")
                elif 'TLS' in str(payload):
                    print(f"{Colors.CYAN}[TLS] {payload}{Colors.ENDC}")
                elif 'API' in str(payload):
                    print(f"{Colors.YELLOW}[API] {payload}{Colors.ENDC}")
                else:
                    print(payload)
            elif message['type'] == 'error':
                print(f"{Colors.RED}[FRIDA ERROR] {message.get('description', 'Unknown error')}{Colors.ENDC}")
                if message.get('stack'):
                    print(f"Stack: {message['stack']}")
        except Exception as e:
            print(f"{Colors.RED}Error processing message: {e}{Colors.ENDC}")

    def attach_and_inject(self, hook_type="combined"):
        """Main attachment and injection flow"""
        
        print(f"\n{Colors.BOLD}🔧 Frida Kiro Interception Setup{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")
        
        # Step 1: Find process
        print(f"{Colors.BLUE}[Step 1/4] Finding Kiro process...{Colors.ENDC}")
        pid = self.find_process()
        if not pid:
            print(f"{Colors.RED}Cannot proceed without target process{Colors.ENDC}")
            return False
        
        # Step 2: Load hook script
        print(f"\n{Colors.BLUE}[Step 2/4] Loading {hook_type} hook script...{Colors.ENDC}")
        hook_script = self.load_hook(hook_type)
        if not hook_script:
            return False
        
        # Step 3: Attach to process
        print(f"\n{Colors.BLUE}[Step 3/4] Attaching to process (PID: {pid})...{Colors.ENDC}")
        try:
            self.session = self.device.attach(pid)
            print(f"{Colors.GREEN}✓ Attached successfully{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to attach: {e}{Colors.ENDC}")
            return False
        
        # Step 4: Create and load script
        print(f"\n{Colors.BLUE}[Step 4/4] Injecting hooks...{Colors.ENDC}")
        try:
            self.script = self.session.create_script(hook_script)
            self.script.on('message', self.on_message)
            self.script.load()
            print(f"{Colors.GREEN}✓ Hooks injected successfully{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to inject: {e}{Colors.ENDC}")
            if self.session:
                self.session.detach()
            return False
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'=' * 60}")
        print(f"✓ FRIDA INTERCEPTION ACTIVE")
        print(f"{'=' * 60}{Colors.ENDC}\n")
        
        print(f"{Colors.CYAN}Monitoring for API calls...")
        print(f"Press Ctrl+C to stop{Colors.ENDC}\n")
        
        return True

    def run_interactive(self):
        """Keep script running and monitor for messages"""
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Stopping Frida interception...{Colors.ENDC}")
            self.cleanup()
            print(f"{Colors.GREEN}Detached successfully{Colors.ENDC}")

    def spawn_and_hook(self, kiro_path, hook_type='kiro_api_hook'):
        """Spawn Kiro with Frida and inject hooks before anti-debug initializes"""
        
        print(f"\n{Colors.BOLD}🚀 Frida Spawn Gating Mode{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")
        print(f"Kiro path: {kiro_path}")
        print(f"Hook: {hook_type}")
        
        # Load hook script
        print(f"\n{Colors.BLUE}[1/5] Loading hook script...{Colors.ENDC}")
        hook_code = self.load_hook(hook_type)
        if not hook_code:
            return False
        print(f"{Colors.GREEN}✓ Loaded {hook_type}.js{Colors.ENDC}")
        
        # Spawn Kiro (suspended)
        print(f"\n{Colors.BLUE}[2/5] Spawning Kiro (suspended)...{Colors.ENDC}")
        try:
            pid = self.device.spawn([kiro_path])
            print(f"{Colors.GREEN}✓ Spawned with PID: {pid}{Colors.ENDC}")
            self.monitored_pids.add(pid)
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to spawn: {e}{Colors.ENDC}")
            return False
        
        # Attach to spawned process
        print(f"\n{Colors.BLUE}[3/5] Attaching to spawned process...{Colors.ENDC}")
        try:
            self.session = self.device.attach(pid)
            print(f"{Colors.GREEN}✓ Attached to PID {pid}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to attach: {e}{Colors.ENDC}")
            self.device.kill(pid)
            return False
        
        # Inject hooks BEFORE resuming
        print(f"\n{Colors.BLUE}[4/5] Injecting hooks (before resume)...{Colors.ENDC}")
        try:
            self.script = self.session.create_script(hook_code)
            self.script.on('message', self.on_message)
            self.script.load()
            print(f"{Colors.GREEN}✓ Hooks injected successfully{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.RED}✗ Failed to inject hooks: {e}{Colors.ENDC}")
            self.device.kill(pid)
            return False
        
        # Resume process
        print(f"\n{Colors.BLUE}[5/5] Resuming Kiro...{Colors.ENDC}")
        self.device.resume(pid)
        print(f"{Colors.GREEN}✓ Kiro is now running with hooks active{Colors.ENDC}")
        print(f"{Colors.CYAN}Main PID: {pid}{Colors.ENDC}")
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}{'=' * 60}")
        print(f"✓ SPAWN GATING ACTIVE - MONITORING CHILD PROCESSES")
        print(f"{'=' * 60}{Colors.ENDC}\n")
        
        print(f"{Colors.YELLOW}Monitoring for child processes (network subprocess)...{Colors.ENDC}")
        print(f"{Colors.CYAN}Press Ctrl+C to stop{Colors.ENDC}\n")
        
        return True

    def check_network_connections(self, pid):
        """Check if a PID has active network connections (requires psutil)"""
        if not HAS_PSUTIL:
            return None, []
        
        try:
            proc = psutil.Process(pid)
            # Use net_connections() instead of deprecated connections()
            try:
                connections = proc.net_connections()
            except:
                connections = proc.connections()  # Fallback for older psutil
            
            # Look for AWS connections
            aws_connections = []
            for conn in connections:
                if hasattr(conn, 'raddr') and conn.raddr:
                    ip = conn.raddr.ip
                    port = conn.raddr.port
                    
                    # Check if it's an AWS IP (common patterns)
                    if port == 443:  # HTTPS
                        try:
                            import socket
                            hostname = socket.gethostbyaddr(ip)[0]
                            if 'amazonaws.com' in hostname or 'aws.com' in hostname or 'kiro.dev' in hostname:
                                aws_connections.append((ip, port, hostname))
                        except:
                            # Can't resolve, but still note the connection
                            aws_connections.append((ip, port, 'unknown'))
            
            return len(connections), aws_connections
        except:
            return None, []

    def monitor_child_processes(self, hook_code):
        """Monitor for new Kiro child processes and auto-inject hooks"""
        try:
            processes = self.device.enumerate_processes()
            kiro_processes = [p for p in processes if 'kiro' in p.name.lower()]
            
            for proc in kiro_processes:
                if proc.pid not in self.monitored_pids:
                    # Check network connections BEFORE attempting to attach
                    conn_count, aws_conns = self.check_network_connections(proc.pid)
                    
                    network_info = ""
                    if conn_count is not None:
                        if aws_conns:
                            network_info = f" [🌐 {len(aws_conns)} AWS connection(s)]"
                        elif conn_count > 0:
                            network_info = f" [🔌 {conn_count} connection(s)]"
                    
                    print(f"{Colors.GREEN}[NEW PROCESS] PID {proc.pid}: {proc.name}{network_info}{Colors.ENDC}")
                    
                    # Show AWS connections if found
                    if aws_conns:
                        for ip, port, hostname in aws_conns:
                            print(f"{Colors.CYAN}  🎯 AWS: {hostname} ({ip}:{port}){Colors.ENDC}")
                    
                    self.monitored_pids.add(proc.pid)
                    
                    # Try to attach to new process
                    try:
                        print(f"{Colors.YELLOW}  Attempting to attach...{Colors.ENDC}")
                        child_session = self.device.attach(proc.pid)
                        child_script = child_session.create_script(hook_code)
                        child_script.on('message', self.on_message)
                        child_script.load()
                        
                        # Store session to prevent cleanup
                        self.child_sessions.append((child_session, child_script))
                        
                        hook_status = "✓ Hooks injected"
                        if aws_conns:
                            hook_status += " [⚡ NETWORK PROCESS HOOKED!]"
                        print(f"{Colors.GREEN}  {hook_status} into PID {proc.pid}{Colors.ENDC}")
                        
                    except Exception as e:
                        error_msg = f"✗ Failed to attach to PID {proc.pid}: {e}"
                        if aws_conns:
                            error_msg += f"\n{Colors.RED}  ⚠️  WARNING: This process has AWS connections but refused hooks!{Colors.ENDC}"
                        print(f"{Colors.RED}  {error_msg}{Colors.ENDC}")
                        
        except Exception as e:
            # Ignore enumeration errors
            pass

    def run_spawn_interactive(self, hook_code):
        """Keep script running and monitor for child processes"""
        if not HAS_PSUTIL:
            print(f"\n{Colors.YELLOW}⚠️  psutil not installed - network detection disabled{Colors.ENDC}")
            print(f"{Colors.YELLOW}   Install with: pip install psutil{Colors.ENDC}\n")
        
        try:
            while True:
                time.sleep(2)
                self.monitor_child_processes(hook_code)
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Stopping Frida interception...{Colors.ENDC}")
            self.print_summary()
            self.cleanup()
            print(f"{Colors.GREEN}Detached successfully{Colors.ENDC}")
    
    def print_summary(self):
        """Print summary of hooked processes and network status"""
        print(f"\n{Colors.BOLD}{'='*60}")
        print(f"SESSION SUMMARY")
        print(f"{'='*60}{Colors.ENDC}")
        
        print(f"\n{Colors.CYAN}Monitored PIDs: {len(self.monitored_pids)}{Colors.ENDC}")
        print(f"{Colors.GREEN}Successfully hooked: {len(self.child_sessions) + (1 if self.session else 0)}{Colors.ENDC}")
        print(f"{Colors.RED}Refused hooks: {len(self.monitored_pids) - len(self.child_sessions) - (1 if self.session else 0)}{Colors.ENDC}")
        
        if HAS_PSUTIL:
            print(f"\n{Colors.CYAN}Network Analysis:{Colors.ENDC}")
            aws_pids = []
            for pid in self.monitored_pids:
                conn_count, aws_conns = self.check_network_connections(pid)
                if aws_conns:
                    aws_pids.append(pid)
                    hooked = any(s[0].pid == pid for s in self.child_sessions) or (self.session and self.session.pid == pid)
                    status = f"{Colors.GREEN}✓ HOOKED{Colors.ENDC}" if hooked else f"{Colors.RED}✗ REFUSED{Colors.ENDC}"
                    print(f"  PID {pid}: {len(aws_conns)} AWS connection(s) - {status}")
            
            if not aws_pids:
                print(f"  {Colors.YELLOW}No AWS connections detected{Colors.ENDC}")
                print(f"  {Colors.YELLOW}Try using Kiro's AI features to trigger API calls{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

    def cleanup(self):
        """Clean up Frida resources"""
        if self.script:
            try:
                self.script.unload()
            except:
                pass
        
        if self.session:
            try:
                self.session.detach()
            except:
                pass
        
        # Cleanup child sessions
        for child_session, child_script in self.child_sessions:
            try:
                child_script.unload()
            except:
                pass
            try:
                child_session.detach()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(
        description='Frida interception script for Kiro application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --hook combined          # All interception hooks (attach mode)
  %(prog)s --hook cert-only         # Only certificate bypass
  %(prog)s --hook logger            # Only request logging
  %(prog)s --hook redirect          # Only hostname redirect
  %(prog)s --list                   # List running processes
  %(prog)s --spawn                  # Spawn Kiro with hooks (anti-debug bypass)
  %(prog)s --spawn --hook kiro_api_hook  # Spawn with specific hook
  %(prog)s --spawn --kiro-path "C:\\Path\\To\\Kiro.exe"  # Custom Kiro path
        """
    )
    
    parser.add_argument('--hook', 
                       default='combined',
                       choices=['combined', 'cert-only', 'logger', 'redirect', 'debug_logger', 'find_context', 'enumerate_modules', 'windows_net_hook', 'simple_winhttp_hook', 'corrected_hook', 'comprehensive_hook', 'check_processes', 'aws_bedrock_hook', 'socket_monitor', 'diagnostic', 'test_any_network', 'find_renderer', 'analyze_process_tree', 'renderer_hook', 'kiro_api_hook', 'auto_find_and_hook', 'intercept_and_redirect', 'diagnose_networking', 'socket_intercept', 'chromium_network_hook'],
                       help='Which hook set to inject (default: combined)')
    parser.add_argument('--list', 
                       action='store_true',
                       help='List running processes and exit')
    parser.add_argument('--process',
                       default='Kiro',
                       help='Process name or PID to attach to (default: Kiro)')
    parser.add_argument('--spawn',
                       action='store_true',
                       help='Spawn Kiro with Frida (bypasses anti-debug)')
    parser.add_argument('--kiro-path',
                       help='Path to Kiro.exe (auto-detected if not provided)')
    
    args = parser.parse_args()
    
    attacher = FridaKiroAttacher(target_process=args.process)
    
    if args.list:
        attacher.list_processes()
        return 0
    
    # Map hook arguments to file names
    hook_map = {
        'combined': 'combined',
        'cert-only': 'certificate_bypass',
        'logger': 'request_logger',
        'redirect': 'request_redirect',
        'debug_logger': 'debug_logger',
        'find_context': 'find_context',
        'enumerate_modules': 'enumerate_modules',
        'windows_net_hook': 'windows_net_hook',
        'simple_winhttp_hook': 'simple_winhttp_hook',
        'corrected_hook': 'corrected_hook',
        'comprehensive_hook': 'comprehensive_hook',
        'check_processes': 'check_processes',
        'aws_bedrock_hook': 'aws_bedrock_hook',
        'socket_monitor': 'socket_monitor',
        'diagnostic': 'diagnostic',
        'test_any_network': 'test_any_network',
        'find_renderer': 'find_renderer',
        'analyze_process_tree': 'analyze_process_tree',
        'renderer_hook': 'renderer_hook',
        'kiro_api_hook': 'kiro_api_hook',
        'auto_find_and_hook': 'auto_find_and_hook',
        'intercept_and_redirect': 'intercept_and_redirect',
        'diagnose_networking': 'diagnose_networking',
        'socket_intercept': 'socket_intercept',
        'chromium_network_hook': 'chromium_network_hook'
    }
    
    hook_file = hook_map.get(args.hook, 'combined')
    
    # SPAWN MODE: Start Kiro with Frida from the beginning
    if args.spawn:
        # Find Kiro executable
        kiro_path = args.kiro_path
        if not kiro_path:
            print(f"{Colors.YELLOW}Auto-detecting Kiro.exe...{Colors.ENDC}")
            kiro_path = attacher.find_kiro_executable()
            
            if not kiro_path:
                print(f"{Colors.RED}✗ Could not find Kiro.exe{Colors.ENDC}")
                print(f"Please specify path with --kiro-path")
                return 1
        
        if not Path(kiro_path).exists():
            print(f"{Colors.RED}✗ Kiro.exe not found at: {kiro_path}{Colors.ENDC}")
            return 1
        
        # Load hook code for child process monitoring
        hook_code = attacher.load_hook(hook_file)
        if not hook_code:
            return 1
        
        # Spawn and hook
        if attacher.spawn_and_hook(kiro_path, hook_file):
            attacher.run_spawn_interactive(hook_code)
            return 0
        else:
            return 1
    
    # ATTACH MODE: Attach to running process (original behavior)
    else:
        if attacher.attach_and_inject(hook_type=hook_file):
            attacher.run_interactive()
            return 0
        else:
            return 1

if __name__ == '__main__':
    sys.exit(main())
