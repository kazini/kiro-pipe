#!/usr/bin/env python3
"""
Find Kiro PIDs - Help identify which Kiro process to attach to
"""

import psutil
import sys
import os

def find_kiro_processes():
    """Find all Kiro processes and analyze them"""
    print("🔍 Searching for Kiro processes...")
    print("=" * 70)
    
    kiro_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'ppid', 'memory_info']):
        try:
            if 'kiro' in proc.info['name'].lower():
                kiro_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not kiro_processes:
        print("❌ No Kiro processes found!")
        print("\nMake sure Kiro is running.")
        return []
    
    print(f"✅ Found {len(kiro_processes)} Kiro process(es):")
    print("-" * 70)
    
    # Group by parent PID to understand process tree
    processes_by_parent = {}
    for proc in kiro_processes:
        ppid = proc.info['ppid']
        if ppid not in processes_by_parent:
            processes_by_parent[ppid] = []
        processes_by_parent[ppid].append(proc)
    
    # Find root process (process with no parent in our list)
    root_pids = []
    for ppid in processes_by_parent:
        # Check if this parent is also a Kiro process
        parent_is_kiro = any(p.info['pid'] == ppid for p in kiro_processes)
        if not parent_is_kiro:
            root_pids.append(ppid)
    
    print("\n📊 Process Analysis:")
    print("-" * 70)
    
    for i, proc in enumerate(kiro_processes):
        pid = proc.info['pid']
        name = proc.info['name']
        ppid = proc.info['ppid']
        memory = proc.info['memory_info']
        
        # Get connections if possible
        connections = []
        try:
            connections = proc.connections()
        except:
            pass
        
        # Determine process type
        process_type = "Unknown"
        if ppid in root_pids:
            process_type = "Main/Root"
        else:
            process_type = "Child"
        
        # Check if it has network connections
        has_network = len(connections) > 0
        
        print(f"\n{i+1}. PID: {pid} ({name})")
        print(f"   Type: {process_type}")
        print(f"   Parent PID: {ppid}")
        print(f"   Memory: {memory.rss / 1024 / 1024:.1f} MB")
        print(f"   Network: {'✅ Yes' if has_network else '❌ No'}")
        
        if has_network:
            print(f"   Connections: {len(connections)}")
            for conn in connections[:2]:  # Show first 2 connections
                if hasattr(conn, 'raddr') and conn.raddr:
                    print(f"     → {conn.raddr.ip}:{conn.raddr.port}")
    
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDATIONS:")
    print("-" * 70)
    
    # Find best candidates
    candidates = []
    for proc in kiro_processes:
        pid = proc.info['pid']
        
        # Check connections
        connections = []
        try:
            connections = proc.connections()
        except:
            pass
        
        # Check memory (renderers often use more memory)
        memory = proc.info['memory_info'].rss
        
        # Score based on heuristics
        score = 0
        if len(connections) > 0:
            score += 10
        if memory > 100 * 1024 * 1024:  # > 100MB
            score += 5
        if proc.info['ppid'] not in root_pids:  # Child process
            score += 3
        
        candidates.append((pid, score, len(connections), memory))
    
    # Sort by score
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    if candidates:
        print("\nTop candidates for network interception:")
        for pid, score, conn_count, memory in candidates[:3]:
            print(f"  PID {pid}: Score {score}/18")
            print(f"    • Connections: {conn_count}")
            print(f"    • Memory: {memory / 1024 / 1024:.1f} MB")
            print(f"    • Command: python frida-scripts/attach.py --hook kiro_api_hook --process {pid}")
    
    print("\n" + "=" * 70)
    print("📋 NEXT STEPS:")
    print("1. Try the top PID candidate above")
    print("2. If no network activity, try other PIDs")
    print("3. Use Task Manager to check network column")
    print("4. Make sure Kiro is making AI calls while testing")
    
    return kiro_processes

def main():
    try:
        import psutil
    except ImportError:
        print("❌ psutil not installed!")
        print("Install it with: pip install psutil")
        return 1
    
    processes = find_kiro_processes()
    
    if processes:
        print("\n💡 Tip: Run this after starting Kiro and using AI features")
        print("   Network activity is only visible when Kiro makes API calls")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())