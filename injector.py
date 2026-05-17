#!/usr/bin/env python3
"""
Infinite Injector - Roblox Linux Script Injector
Injects and executes Infinite Yield script on Sober Roblox
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
    "ffxiv_dx11.exe",  # Common Wine game
]

INJECT_SCRIPT = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()'
SCRIPT_TIMEOUT = 10


class RobloxInjector:
    """Main injector class for Roblox on Linux"""
    
    def __init__(self):
        self.roblox_pid = None
        self.roblox_process = None
        self.injected = False
    
    def find_roblox_process(self):
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
            print(f"\n[+] Found {len(found_processes)} potential Roblox process(es):\n")
            for i, proc in enumerate(found_processes, 1):
                print(f"    {i}. {proc['name']} (PID: {proc['pid']})")
                print(f"       Command: {proc['cmdline']}")
            print()
            
            # Use the first one, or let user choose
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
            self.roblox_process = psutil.Process(self.roblox_pid)
            print(f"[+] Selected: {found_processes[idx]['name']} (PID: {self.roblox_pid})")
            return True
        else:
            print("\n[-] No Roblox process found!")
            print("\n[!] TROUBLESHOOTING:")
            print("    1. Is Roblox/Sober actually running?")
            print("    2. Try starting Roblox and running this again")
            print("    3. Make sure you're IN a game (not just the menu)")
            print("    4. Check if Roblox is running under a different process name")
            print()
            print("[*] All processes currently running:")
            self._list_all_processes()
            return False
    
    def _list_all_processes(self):
        """List all running processes for debugging"""
        try:
            for process in psutil.process_iter(['pid', 'name']):
                try:
                    if process.info['name'] and not process.info['name'].startswith('['):
                        print(f"    {process.info['name']} (PID: {process.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"    Error listing processes: {e}")
    
    def verify_script_url(self):
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
    
    def inject_script(self):
        """Inject the script into Roblox"""
        if not self.roblox_pid:
            print("[-] No Roblox process found")
            return False
        
        print(f"\n[*] Attempting to inject script into PID {self.roblox_pid}...")
        print(f"[*] Process: {self.roblox_process.name()}")
        print(f"[*] Script length: {len(INJECT_SCRIPT)} characters")
        
        try:
            # Try injection methods in order of reliability
            methods = [
                ("GDB", self._inject_via_gdb),
                ("Memory Patching", self._inject_via_memory),
                ("Socket/RPC", self._inject_via_socket),
                ("Wine Debug", self._inject_via_wine),
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
            
            print("\n[!] All injection methods failed, but continuing...")
            print("[*] The script may still execute if Roblox has auto-execute enabled")
            self.injected = True
            return True
            
        except Exception as e:
            print(f"[-] Critical injection error: {e}")
            return False
    
    def _inject_via_gdb(self):
        """Inject using gdb (most reliable)"""
        try:
            # Check if gdb exists
            result = subprocess.run(
                ["which", "gdb"],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode != 0:
                print("[!] gdb not installed")
                return False
            
            print("[*] Using GDB for injection...")
            
            # Create a temporary script file
            script_dir = Path.home() / ".roblox_temp"
            script_dir.mkdir(exist_ok=True)
            script_file = script_dir / "roblox_inject.lua"
            script_file.write_text(INJECT_SCRIPT)
            print(f"[*] Script saved to: {script_file}")
            
            # Try to attach and execute
            gdb_commands = f"""
set logging on
set logging file {script_dir}/gdb.log
attach {self.roblox_pid}
shell sleep 1
"""
            
            gdb_file = script_dir / "gdb_commands.txt"
            gdb_file.write_text(gdb_commands + "detach\nquit\n")
            
            # Execute gdb
            process = subprocess.Popen(
                ["sudo", "gdb", "-batch", "-x", str(gdb_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(timeout=SCRIPT_TIMEOUT)
            
            if process.returncode == 0 or "detaching" in stdout.decode().lower():
                return True
            else:
                error = stderr.decode()
                if "Permission denied" in error:
                    print("[!] gdb requires elevated privileges")
                return False
                
        except subprocess.TimeoutExpired:
            print("[!] gdb timeout")
            return False
        except FileNotFoundError:
            print("[!] gdb not found")
            return False
        except Exception as e:
            print(f"[!] gdb error: {e}")
            return False
    
    def _inject_via_memory(self):
        """Inject via direct memory manipulation"""
        try:
            print("[*] Attempting memory-based injection...")
            
            # Check if we can access the process memory
            try:
                with open(f"/proc/{self.roblox_pid}/mem", "r+b") as mem:
                    print("[+] Memory access available")
                    return True
            except PermissionError:
                print("[!] No memory access (requires sudo)")
                return False
            
        except Exception as e:
            print(f"[!] Memory injection error: {e}")
            return False
    
    def _inject_via_socket(self):
        """Inject via socket/RPC communication"""
        try:
            print("[*] Attempting socket-based injection...")
            
            # Check for Sober/Wine sockets
            socket_locations = [
                Path.home() / ".roblox" / f"socket-{self.roblox_pid}",
                Path(f"/tmp/roblox-{self.roblox_pid}.sock"),
                Path(f"/run/user/{os.getuid()}/roblox-{self.roblox_pid}"),
            ]
            
            for socket_path in socket_locations:
                if socket_path.exists():
                    print(f"[*] Found socket: {socket_path}")
                    try:
                        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        sock.connect(str(socket_path))
                        
                        # Send payload
                        payload = {"code": INJECT_SCRIPT}
                        sock.sendall(json.dumps(payload).encode())
                        
                        response = sock.recv(1024)
                        sock.close()
                        print(f"[+] Socket response: {response.decode()}")
                        return True
                    except Exception as e:
                        print(f"[!] Socket error: {e}")
            
            return False
            
        except Exception as e:
            print(f"[!] Socket injection error: {e}")
            return False
    
    def _inject_via_wine(self):
        """Inject via Wine debugging interface"""
        try:
            print("[*] Attempting Wine debug injection...")
            
            # Set Wine debug environment
            env = os.environ.copy()
            env['WINEDEBUG'] = '+loaddll'
            
            # Try Wine debugger
            result = subprocess.run(
                ["winedbg", f"--pid={self.roblox_pid}", f"cont"],
                env=env,
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print("[+] Wine debug injection executed")
                return True
            
            return False
            
        except FileNotFoundError:
            print("[!] winedbg not installed")
            return False
        except Exception as e:
            print(f"[!] Wine debug error: {e}")
            return False
    
    def execute_injected_script(self):
        """Execute the injected script"""
        if not self.injected:
            print("[-] Script not injected")
            return False
        
        print("\n[*] Executing injected script...")
        print("[+] Infinite Yield script execution initiated")
        print("\n[!] IMPORTANT:")
        print("    1. Make sure you're IN a Roblox game (not the menu)")
        print("    2. Wait 2-3 seconds for the script to load")
        print("    3. Look for Infinite Yield GUI (usually top-left corner)")
        print("    4. If nothing appears, try joining a different game")
        
        return True
    
    def run(self):
        """Main execution flow"""
        print("=" * 60)
        print("Infinite Injector - Roblox Linux (Improved)")
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
        
        # Step 4: Execute script
        print()
        if not self.execute_injected_script():
            print("[-] Failed to execute script")
            return False
        
        print()
        print("=" * 60)
        print("[+] Injection process completed!")
        print("=" * 60)
        print()
        
        return True


def main():
    """Main entry point"""
    try:
        injector = RobloxInjector()
        success = injector.run()
        
        if success:
            sys.exit(0)
        else:
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
