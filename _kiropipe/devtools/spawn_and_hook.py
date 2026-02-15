#!/usr/bin/env python3
"""
Frida Spawn Gating - Start Kiro with Frida from the beginning

This attempts to bypass anti-debugging by injecting hooks before
the process fully initializes.
"""

import frida
import sys
import time
from pathlib import Path

# Color codes
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'

def find_kiro_executable():
    """Find Kiro.exe location"""
    common_paths = [
        r"C:\Users\{username}\AppData\Local\Programs\Kiro\Kiro.exe",
        r"C:\Program Files\Kiro\Kiro.exe",
        r"C:\Program Files (x86)\Kiro\Kiro.exe",
    ]
    
    import os
    username = os.environ.get('USERNAME', '')
    
    for path_template in common_paths:
        path = path_template.format(username=username)
        if Path(path).exists():
            return path
    
    return None

def load_hook_script(hook_name):
    """Load hook JavaScript from file"""
    script_dir = Path(__file__).parent
    hook_file = script_dir / f"{hook_name}.js"
    
    if not hook_file.exists():
        print(f"{Colors.RED}Hook file not found: {hook_file}{Colors.ENDC}")
        return None
    
    with open(hook_file, 'r', encoding='utf-8') as f:
        return f.read()

def on_message(message, data):
    """Handle messages from Frida script"""
    if message['type'] == 'send':
        payload = message.get('payload', '')
        if 'ERROR' in str(payload):
            print(f"{Colors.RED}[HOOK] {payload}{Colors.ENDC}")
        elif 'SUCCESS' in str(payload):
            print(f"{Colors.GREEN}[HOOK] {payload}{Colors.ENDC}")
        else:
            print(f"{Colors.CYAN}[HOOK] {payload}{Colors.ENDC}")
    elif message['type'] == 'error':
        print(f"{Colors.RED}[ERROR] {message.get('description', 'Unknown error')}{Colors.ENDC}")
        if message.get('stack'):
            print(f"Stack: {message['stack']}")

def spawn_and_hook(kiro_path, hook_name='kiro_api_hook'):
    """Spawn Kiro with Frida and inject hooks"""
    
    print(f"\n{Colors.CYAN}=== Frida Spawn Gating ==={Colors.ENDC}")
    print(f"Kiro path: {kiro_path}")
    print(f"Hook: {hook_name}")
    
    # Load hook script
    print(f"\n{Colors.YELLOW}[1/5] Loading hook script...{Colors.ENDC}")
    hook_code = load_hook_script(hook_name)
    if not hook_code:
        return False
    print(f"{Colors.GREEN}Loaded {hook_name}.js{Colors.ENDC}")
    
    # Get device
    print(f"\n{Colors.YELLOW}[2/5] Connecting to device...{Colors.ENDC}")
    device = frida.get_local_device()
    print(f"{Colors.GREEN}Connected{Colors.ENDC}")
    
    # Spawn Kiro (suspended)
    print(f"\n{Colors.YELLOW}[3/5] Spawning Kiro (suspended)...{Colors.ENDC}")
    try:
        pid = device.spawn([kiro_path])
        print(f"{Colors.GREEN}Spawned with PID: {pid}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Failed to spawn: {e}{Colors.ENDC}")
        return False
    
    # Attach to spawned process
    print(f"\n{Colors.YELLOW}[4/5] Attaching to spawned process...{Colors.ENDC}")
    try:
        session = device.attach(pid)
        print(f"{Colors.GREEN}Attached to PID {pid}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Failed to attach: {e}{Colors.ENDC}")
        device.kill(pid)
        return False
    
    # Inject hooks BEFORE resuming
    print(f"\n{Colors.YELLOW}[5/5] Injecting hooks (before resume)...{Colors.ENDC}")
    try:
        script = session.create_script(hook_code)
        script.on('message', on_message)
        script.load()
        print(f"{Colors.GREEN}Hooks injected successfully{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}Failed to inject hooks: {e}{Colors.ENDC}")
        device.kill(pid)
        return False
    
    # Resume process
    print(f"\n{Colors.GREEN}=== Resuming Kiro ==={Colors.ENDC}")
    device.resume(pid)
    print(f"{Colors.CYAN}Kiro is now running with hooks active{Colors.ENDC}")
    print(f"{Colors.CYAN}Main PID: {pid}{Colors.ENDC}")
    
    # Monitor for child processes
    print(f"\n{Colors.YELLOW}Monitoring for child processes...{Colors.ENDC}")
    print(f"{Colors.YELLOW}(Network subprocess should spawn soon){Colors.ENDC}")
    
    # Wait and monitor
    try:
        print(f"\n{Colors.CYAN}Press Ctrl+C to stop monitoring{Colors.ENDC}\n")
        
        # Keep monitoring
        monitored_pids = {pid}
        
        while True:
            time.sleep(2)
            
            # Check for new child processes
            try:
                processes = device.enumerate_processes()
                kiro_processes = [p for p in processes if 'kiro' in p.name.lower()]
                
                for proc in kiro_processes:
                    if proc.pid not in monitored_pids:
                        print(f"{Colors.GREEN}[NEW PROCESS] PID {proc.pid}: {proc.name}{Colors.ENDC}")
                        monitored_pids.add(proc.pid)
                        
                        # Try to attach to new process
                        try:
                            print(f"{Colors.YELLOW}  Attempting to attach...{Colors.ENDC}")
                            child_session = device.attach(proc.pid)
                            child_script = child_session.create_script(hook_code)
                            child_script.on('message', on_message)
                            child_script.load()
                            print(f"{Colors.GREEN}  Hooks injected into PID {proc.pid}{Colors.ENDC}")
                        except Exception as e:
                            print(f"{Colors.RED}  Failed to attach to PID {proc.pid}: {e}{Colors.ENDC}")
            except Exception as e:
                # Ignore enumeration errors
                pass
                
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Stopping...{Colors.ENDC}")
        
        # Cleanup
        try:
            script.unload()
            session.detach()
        except:
            pass
        
        print(f"{Colors.GREEN}Detached successfully{Colors.ENDC}")
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Spawn Kiro with Frida hooks from the start',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--kiro-path', 
                       help='Path to Kiro.exe (auto-detected if not provided)')
    parser.add_argument('--hook',
                       default='kiro_api_hook',
                       choices=['kiro_api_hook', 'test_any_network', 'socket_intercept', 
                               'chromium_network_hook', 'intercept_and_redirect'],
                       help='Hook script to inject (default: kiro_api_hook)')
    
    args = parser.parse_args()
    
    # Find Kiro executable
    kiro_path = args.kiro_path
    if not kiro_path:
        print(f"{Colors.YELLOW}Auto-detecting Kiro.exe...{Colors.ENDC}")
        kiro_path = find_kiro_executable()
        
        if not kiro_path:
            print(f"{Colors.RED}Could not find Kiro.exe{Colors.ENDC}")
            print(f"Please specify path with --kiro-path")
            return 1
    
    if not Path(kiro_path).exists():
        print(f"{Colors.RED}Kiro.exe not found at: {kiro_path}{Colors.ENDC}")
        return 1
    
    # Spawn and hook
    success = spawn_and_hook(kiro_path, args.hook)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
