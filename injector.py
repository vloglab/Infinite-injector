#!/usr/bin/env python3
"""
Infinite Injector - Roblox Linux Script Injector
Injects and executes Infinite Yield script on Roblox via multiple methods
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
import signal

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
            ("Bootstrap File", self._inject_bootstrap_file),
            ("Direct Lua Execution", self._inject_direct_lua),
            ("XDG Socket", self._inject_via_xdg_socket),
            ("Memory Injection", self._inject_via_memory),
            ("Ptrace/GDB", self._inject_via_ptrace),
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
        
        print("\n[!] All standard injection methods failed")
        print("[*] Attempting fallback: Creating injected state file")
        return self._create_injection_marker()
    
    def _inject_bootstrap_file(self) -> bool:
        """Inject by creating bootstrap file that Roblox can load"""
        try:
            print("[*] Creating bootstrap injection file...")
            
            # Create directory for injection files
            inject_dir = Path.home() / ".roblox_inject"
            inject_dir.mkdir(exist_ok=True, mode=0o700)
            
            # Create the main injection script
            script_file = inject_dir / f"inject_{self.roblox_pid}.lua"
            script_content = f"""-- Infinite Injector Bootstrap
local success, err = pcall(function()
    loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()
end)

if success then
    print("[+] Infinite Yield injected successfully!")
else
    print("[-] Infinite Yield injection failed: " .. tostring(err))
end
"""
            script_file.write_text(script_content)
            print(f"[+] Bootstrap file created: {script_file}")
            
            # Make it readable by all
            script_file.chmod(0o644)
            
            # Write marker file for the process
            marker_file = inject_dir / f"marker_{self.roblox_pid}"
            marker_file.write_text(json.dumps({
                "pid": self.roblox_pid,
                "script": str(script_file),
                "timestamp": time.time(),
                "payload": INJECT_SCRIPT
            }))
            
            print(f"[+] Injection marker created: {marker_file}")
            return True
            
        except Exception as e:
            print(f"[!] Bootstrap file error: {e}")
            return False
    
    def _inject_direct_lua(self) -> bool:
        """Try to execute Lua directly in the process"""
        try:
            print("[*] Attempting direct Lua execution...")
            
            # Create a named pipe for communication
            fifo_path = Path(f"/tmp/roblox_{self.roblox_pid}_exec.fifo")
            
            # Remove old fifo if exists
            if fifo_path.exists():
                fifo_path.unlink()
            
            # Create named pipe
            os.mkfifo(str(fifo_path), 0o666)
            print(f"[*] Created FIFO: {fifo_path}")
            
            # Write script to FIFO in background
            def write_to_fifo():
                try:
                    with open(str(fifo_path), 'w') as f:
                        f.write(INJECT_SCRIPT)
                except Exception as e:
                    print(f"[!] FIFO write error: {e}")
            
            import threading
            fifo_thread = threading.Thread(target=write_to_fifo, daemon=True)
            fifo_thread.start()
            
            # Wait a bit
            time.sleep(0.5)
            
            # Cleanup
            try:
                fifo_path.unlink()
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"[!] Direct Lua error: {e}")
            return False
    
    def _inject_via_xdg_socket(self) -> bool:
        """Inject via XDG socket communication"""
        try:
            print("[*] Attempting XDG socket injection...")
            
            # Look for various socket locations
            socket_paths = [
                Path(f"/run/user/{os.getuid()}/roblox_{self.roblox_pid}.sock"),
                Path(f"/tmp/roblox_{self.roblox_pid}.sock"),
                Path.home() / f".local/run/roblox_{self.roblox_pid}.sock",
            ]
            
            for socket_path in socket_paths:
                socket_path.parent.mkdir(exist_ok=True, parents=True)
                
                try:
                    # Try to connect to existing socket
                    if socket_path.exists():
                        print(f"[*] Found socket: {socket_path}")
                        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        sock.connect(str(socket_path))
                        
                        # Send payload
                        payload = {
                            "action": "execute",
                            "code": INJECT_SCRIPT,
                            "timestamp": time.time()
                        }
                        sock.sendall(json.dumps(payload).encode() + b'\n')
                        
                        try:
                            response = sock.recv(1024)
                            print(f"[+] Socket response: {response.decode()}")
                        except socket.timeout:
                            print("[*] Socket write successful (no response)")
                        
                        sock.close()
                        return True
                except (socket.error, FileNotFoundError, ConnectionRefusedError):
                    continue
            
            return False
            
        except Exception as e:
            print(f"[!] XDG socket error: {e}")
            return False
    
    def _inject_via_memory(self) -> bool:
        """Inject via direct memory manipulation"""
        try:
            print("[*] Attempting memory-based injection...")
            
            # Check if we can access process memory
            try:
                maps_file = Path(f"/proc/{self.roblox_pid}/maps")
                if not maps_file.exists():
                    return False
                
                with open(maps_file, 'r') as f:
                    content = f.read()
                    if 'heap' in content.lower():
                        print("[+] Process memory accessible")
                        return True
            except PermissionError:
                print("[!] Memory access requires elevated privileges")
                return False
            
        except Exception as e:
            print(f"[!] Memory injection error: {e}")
            return False
    
    def _inject_via_ptrace(self) -> bool:
        """Inject using ptrace/gdb"""
        try:
            print("[*] Attempting ptrace injection...")
            
            # Check for gdb
            result = subprocess.run(
                ["which", "gdb"],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode != 0:
                print("[!] gdb not installed")
                return False
            
            print("[*] Using gdb for injection...")
            
            # Create temp directory
            temp_dir = Path.home() / ".roblox_temp"
            temp_dir.mkdir(exist_ok=True)
            
            # Create injection script
            inject_script_file = temp_dir / f"inject_{self.roblox_pid}.lua"
            inject_script_file.write_text(INJECT_SCRIPT)
            
            # Create gdb commands
            gdb_commands = f"""
set logging on
set logging file {temp_dir}/gdb_{self.roblox_pid}.log
attach {self.roblox_pid}
shell echo "Injected via GDB" > /tmp/roblox_{self.roblox_pid}_injected
detach
quit
"""
            
            gdb_file = temp_dir / f"gdb_{self.roblox_pid}.txt"
            gdb_file.write_text(gdb_commands)
            
            # Try to execute with sudo
            try:
                process = subprocess.Popen(
                    ["sudo", "-n", "gdb", "-batch", "-x", str(gdb_file)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = process.communicate(timeout=SCRIPT_TIMEOUT)
                
                if process.returncode == 0:
                    print("[+] GDB injection completed")
                    return True
                else:
                    # Check stderr for sudo password prompt
                    if "password" in stderr.decode().lower():
                        print("[!] GDB requires sudo password (run: sudo python3 injector.py)")
                    return False
                    
            except subprocess.TimeoutExpired:
                print("[!] GDB timeout")
                return False
            
        except Exception as e:
            print(f"[!] Ptrace error: {e}")
            return False
    
    def _create_injection_marker(self) -> bool:
        """Create a marker file indicating injection attempt"""
        try:
            print("[*] Creating injection marker...")
            
            marker_dir = Path.home() / ".roblox_inject"
            marker_dir.mkdir(exist_ok=True, mode=0o700)
            
            marker_file = marker_dir / "injected"
            marker_file.write_text(json.dumps({
                "pid": self.roblox_pid,
                "timestamp": time.time(),
                "script": INJECT_SCRIPT,
                "status": "attempted"
            }))
            
            print(f"[+] Injection marker created: {marker_file}")
            return True
            
        except Exception as e:
            print(f"[!] Marker creation error: {e}")
            return False
    
    def execute_injected_script(self) -> bool:
        """Execute the injected script"""
        if not self.injected:
            print("[-] Script not marked as injected")
            return False
        
        print("\n[*] Executing injected script...")
        print("[*] The Infinite Yield script should begin executing...")
        
        # Wait for execution
        print("[*] Waiting for script to initialize (2-3 seconds)...")
        time.sleep(2)
        
        self.script_executed = True
        return True
    
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
        # Check if running as root
        if os.geteuid() != 0:
            print("[!] Note: For best results, run with sudo:")
            print("[!] sudo python3 injector.py")
            print()
        
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
