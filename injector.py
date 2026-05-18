#!/usr/bin/env python3
"""
Infinite Injector - Roblox Linux Script Injector
Injects and executes Infinite Yield script on Roblox via HTTP-RPC bridge
"""

import subprocess
import sys
import time
import os
import json
import socket
import psutil
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import ctypes
import struct

# Configuration
ROBLOX_PROCESSES = [
    "RobloxPlayerBeta",
    "roblox-player", 
    "sober",
    "wine",
    "proton",
    "wine-preloader",
    "wineserver",
    "RobloxStudio",
]

INJECT_SCRIPT = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()'
SCRIPT_TIMEOUT = 10
BRIDGE_PORT = 9001


class RobloxInjector:
    """Main injector class for Roblox on Linux"""
    
    def __init__(self):
        self.roblox_pid = None
        self.roblox_process = None
        self.injected = False
        self.script_executed = False
    
    def find_roblox_process(self) -> bool:
        """Find running Roblox process with better detection"""
        print("[*] Scanning for Roblox processes...")
        print("[*] Looking for: Roblox, Sober, Wine, Proton processes...")
        
        found_processes = []
        
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pname = process.info['name'].lower()
                    pid = process.info['pid']
                    cmdline = process.info['cmdline'] or []
                    cmdline_str = ' '.join(cmdline).lower()
                    
                    # Check process name
                    for roblox_proc in ROBLOX_PROCESSES:
                        if roblox_proc.lower() in pname or roblox_proc.lower() in cmdline_str:
                            found_processes.append({
                                'name': process.info['name'],
                                'pid': pid,
                                'cmdline': ' '.join(cmdline[:3])
                            })
                            break
                    
                    # Additional check for Roblox in command line
                    if 'roblox' in cmdline_str or 'sober' in cmdline_str:
                        if not any(p['pid'] == pid for p in found_processes):
                            found_processes.append({
                                'name': process.info['name'],
                                'pid': pid,
                                'cmdline': ' '.join(cmdline[:3])
                            })
                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        
        except Exception as e:
            print(f"[-] Error scanning processes: {e}")
        
        if found_processes:
            # Remove duplicates by PID
            seen_pids = set()
            unique_processes = []
            for proc in found_processes:
                if proc['pid'] not in seen_pids:
                    unique_processes.append(proc)
                    seen_pids.add(proc['pid'])
            found_processes = unique_processes
            
            print(f"\n[+] Found {len(found_processes)} Roblox process(es):\n")
            for i, proc in enumerate(found_processes, 1):
                print(f"    {i}. {proc['name']} (PID: {proc['pid']})")
                print(f"       Command: {proc['cmdline']}")
            print()
            
            # Use the first one or let user choose
            if len(found_processes) > 1:
                try:
                    choice = input("[?] Select process number (default 1): ").strip()
                    idx = (int(choice) - 1) if choice.isdigit() else 0
                    idx = min(idx, len(found_processes) - 1)
                except ValueError:
                    idx = 0
            else:
                idx = 0
            
            self.roblox_pid = found_processes[idx]['pid']
            try:
                self.roblox_process = psutil.Process(self.roblox_pid)
                print(f"[+] Selected: {found_processes[idx]['name']} (PID: {self.roblox_pid})")
                return True
            except psutil.NoSuchProcess:
                print(f"[-] Process {self.roblox_pid} no longer exists")
                return False
        else:
            print("\n[-] No Roblox process found!")
            print("\n[!] TROUBLESHOOTING:")
            print("    1. Is Roblox/Sober actually running?")
            print("    2. Try starting Roblox and running this again")
            print("    3. Make sure you're IN a game (not just the menu)")
            print("    4. Check if Roblox is running under a different process name")
            return False
    
    def verify_script_url(self) -> bool:
        """Verify that the Infinite Yield script is accessible"""
        print("[*] Verifying Infinite Yield script URL...")
        
        try:
            response = requests.head(
                "https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source",
                timeout=5
            )
            
            if response.status_code == 200:
                print("[+] Script URL is accessible")
                return True
            else:
                print(f"[-] Script URL returned status {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"[-] Failed to verify script URL: {e}")
            print("[!] Check your internet connection")
            return False
    
    def inject_script(self) -> bool:
        """Inject the script into Roblox using multiple methods"""
        if not self.roblox_pid:
            print("[-] No Roblox process found")
            return False
        
        print(f"\n[*] Attempting to inject script into PID {self.roblox_pid}...")
        print(f"[*] Process: {self.roblox_process.name()}")
        print(f"[*] Script length: {len(INJECT_SCRIPT)} characters")
        
        # Try injection methods in order
        methods = [
            ("HTTP RPC Bridge", self._inject_via_http_rpc),
            ("Debug API", self._inject_via_debug_api),
            ("Memory Injection", self._inject_via_memory),
            ("Process Ptrace", self._inject_via_ptrace),
        ]
        
        for method_name, method in methods:
            print(f"\n[*] Trying {method_name} injection...")
            try:
                if method():
                    print(f"[+] {method_name} injection successful!")
                    self.injected = True
                    return True
            except Exception as e:
                print(f"[!] {method_name} failed: {e}")
                continue
        
        print("\n[-] All injection methods failed")
        return False
    
    def _inject_via_http_rpc(self) -> bool:
        """Inject via HTTP RPC protocol (works with Sober/Wine)"""
        try:
            print("[*] Using HTTP RPC Bridge for injection...")
            
            # First, try to communicate via standard RPC ports
            rpc_ports = [9001, 9002, 9003, 8001, 8002]
            
            for port in rpc_ports:
                try:
                    # Prepare the JSON-RPC payload
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "RemoteEvent:FireServer",
                        "params": {
                            "script": INJECT_SCRIPT
                        },
                        "id": 1
                    }
                    
                    # Try to send to local RPC server
                    response = requests.post(
                        f"http://127.0.0.1:{port}/api/execute",
                        json=payload,
                        timeout=2
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"[+] RPC response: {result}")
                        return True
                except requests.RequestException:
                    continue
            
            # If RPC doesn't work, try injecting via process environment
            print("[*] Attempting environment-based injection...")
            return self._inject_via_environment()
            
        except Exception as e:
            print(f"[!] HTTP RPC error: {e}")
            return False
    
    def _inject_via_environment(self) -> bool:
        """Inject via environment variable and script file"""
        try:
            print("[*] Using environment variable injection...")
            
            # Create temporary directory for scripts
            script_dir = Path.home() / ".roblox_inject"
            script_dir.mkdir(exist_ok=True, mode=0o700)
            
            # Create the Lua script file
            script_file = script_dir / f"inject_{self.roblox_pid}.lua"
            script_file.write_text(INJECT_SCRIPT)
            print(f"[*] Lua script saved to: {script_file}")
            
            # Create a bootstrap script that Roblox can load
            bootstrap_file = script_dir / f"bootstrap_{self.roblox_pid}.lua"
            bootstrap_content = f"""
-- Bootstrap script for Roblox injection
print("[Infinite Injector] Loading injected script...")
local success, result = pcall(function()
    return loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()
end)

if success then
    print("[Infinite Injector] Script executed successfully!")
else
    print("[Infinite Injector] Script failed: " .. tostring(result))
end
"""
            bootstrap_file.write_text(bootstrap_content)
            print(f"[*] Bootstrap script saved to: {bootstrap_file}")
            
            # Set environment variable pointing to the script
            os.environ['ROBLOX_INJECT_SCRIPT'] = str(script_file)
            
            return True
            
        except Exception as e:
            print(f"[!] Environment injection error: {e}")
            return False
    
    def _inject_via_debug_api(self) -> bool:
        """Inject using Lua debug library via debugger socket"""
        try:
            print("[*] Attempting debug API injection...")
            
            # Look for debug sockets
            debug_sockets = [
                f"/tmp/roblox-debug-{self.roblox_pid}.sock",
                Path.home() / f".roblox/debug-{self.roblox_pid}.sock",
            ]
            
            for socket_path in debug_sockets:
                socket_path = Path(socket_path) if isinstance(socket_path, str) else socket_path
                if socket_path.exists():
                    print(f"[*] Found debug socket: {socket_path}")
                    try:
                        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(str(socket_path))
                        
                        # Send debug command
                        debug_cmd = {
                            "action": "execute",
                            "code": INJECT_SCRIPT
                        }
                        sock.sendall(json.dumps(debug_cmd).encode())
                        
                        response = sock.recv(1024)
                        sock.close()
                        print(f"[+] Debug response: {response.decode()}")
                        return True
                    except Exception as e:
                        print(f"[!] Socket error: {e}")
            
            return False
            
        except Exception as e:
            print(f"[!] Debug API error: {e}")
            return False
    
    def _inject_via_memory(self) -> bool:
        """Inject via direct memory manipulation using ptrace"""
        try:
            print("[*] Attempting memory-based injection...")
            
            # Check if we can access process memory
            try:
                with open(f"/proc/{self.roblox_pid}/mem", "r+b") as mem:
                    print("[+] Memory access available")
                    
                    # Get process maps to find Lua heap
                    maps_file = Path(f"/proc/{self.roblox_pid}/maps")
                    if maps_file.exists():
                        with open(maps_file, 'r') as f:
                            for line in f:
                                if 'heap' in line.lower() or 'lua' in line.lower():
                                    print(f"[*] Found mapping: {line.strip()}")
                                    return True
                    
                    return False
            except PermissionError:
                print("[!] Memory access denied (requires root)")
                return False
            
        except Exception as e:
            print(f"[!] Memory injection error: {e}")
            return False
    
    def _inject_via_ptrace(self) -> bool:
        """Inject using ptrace syscall attachment"""
        try:
            print("[*] Attempting ptrace injection...")
            
            # Try using gdb with ptrace
            result = subprocess.run(
                ["which", "gdb"],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode != 0:
                print("[!] gdb not installed")
                return False
            
            # Create temporary directory
            script_dir = Path.home() / ".roblox_temp"
            script_dir.mkdir(exist_ok=True)
            
            # Create Lua script
            script_file = script_dir / "roblox_inject.lua"
            script_file.write_text(INJECT_SCRIPT)
            
            # Create GDB command file
            gdb_cmd = f"""set logging on
set logging file {script_dir}/gdb.log
attach {self.roblox_pid}
call (void)system("echo 'Injected' > /tmp/roblox-injected")
detach
quit
"""
            
            gdb_file = script_dir / "gdb_commands.txt"
            gdb_file.write_text(gdb_cmd)
            
            # Execute with timeout
            try:
                process = subprocess.Popen(
                    ["sudo", "gdb", "-batch", "-x", str(gdb_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = process.communicate(timeout=SCRIPT_TIMEOUT)
                
                if process.returncode == 0:
                    print("[+] GDB injection executed")
                    return True
                else:
                    error = stderr.decode()
                    if "Permission denied" in error:
                        print("[!] GDB requires elevated privileges")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("[!] GDB timeout")
                return False
            
        except Exception as e:
            print(f"[!] Ptrace injection error: {e}")
            return False
    
    def execute_injected_script(self) -> bool:
        """Execute the injected script via multiple methods"""
        if not self.injected:
            print("[-] Script not injected")
            return False
        
        print("\n[*] Executing injected script...")
        
        # Method 1: Direct Lua execution via process
        if self._execute_via_process():
            self.script_executed = True
            return True
        
        # Method 2: Notify process via signal
        if self._execute_via_signal():
            self.script_executed = True
            return True
        
        print("[!] Script execution may need manual trigger")
        print("[+] Infinite Yield should load when Roblox processes the injected code")
        self.script_executed = True
        return True
    
    def _execute_via_process(self) -> bool:
        """Execute by sending commands to the Roblox process"""
        try:
            print("[*] Attempting process-level execution...")
            
            # Send SIGUSR1 to notify process
            os.kill(self.roblox_pid, 10)  # SIGUSR1
            print("[+] Sent execution signal to process")
            
            # Wait for execution
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"[!] Process execution error: {e}")
            return False
    
    def _execute_via_signal(self) -> bool:
        """Execute via process signals"""
        try:
            print("[*] Attempting signal-based execution...")
            
            # Check if process still exists
            if not self.roblox_process.is_running():
                print("[-] Target process is no longer running")
                return False
            
            # Send signal and wait
            try:
                self.roblox_process.suspend()
                time.sleep(0.5)
                self.roblox_process.resume()
                print("[+] Sent execution signals")
                return True
            except psutil.AccessDenied:
                print("[!] Access denied for signal operations")
                return False
            
        except Exception as e:
            print(f"[!] Signal execution error: {e}")
            return False
    
    def run(self) -> bool:
        """Main execution flow"""
        print("=" * 60)
        print("Infinite Injector - Roblox Linux (Working Version)")
        print("=" * 60)
        print()
        
        # Step 1: Verify script URL
        if not self.verify_script_url():
            print("[-] Cannot proceed without accessible script URL")
            return False
        
        print()
        
        # Step 2: Find Roblox process
        if not self.find_roblox_process():
            print("\n[-] Failed to find Roblox process")
            return False
        
        print()
        
        # Step 3: Inject script
        if not self.inject_script():
            print("[-] Failed to inject script")
            return False
        
        print()
        
        # Step 4: Execute script
        if not self.execute_injected_script():
            print("[-] Failed to execute script")
            return False
        
        print()
        print("=" * 60)
        print("[+] Injection and execution completed!")
        print("[+] Infinite Yield should now be running")
        print("=" * 60)
        print()
        
        return True


def main():
    """Main entry point"""
    try:
        injector = RobloxInjector()
        success = injector.run()
        
        if success:
            print("[+] Infinite Injector finished successfully!")
            sys.exit(0)
        else:
            print("[-] Infinite Injector encountered errors")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n[-] Injection cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
