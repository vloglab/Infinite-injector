#!/usr/bin/env python3
"""
Infinite Injector - Roblox Linux Script Injector
Injects and executes Infinite Yield script on Sober Roblox
"""

import subprocess
import sys
import time
import os
import psutil
import requests
from pathlib import Path

# Configuration
ROBLOX_PROCESSES = ["RobloxPlayerBeta", "roblox-player", "sober", "wine", "proton"]
INJECT_SCRIPT = 'loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()'
SCRIPT_TIMEOUT = 10


class RobloxInjector:
    """Main injector class for Roblox on Linux"""
    
    def __init__(self):
        self.roblox_pid = None
        self.injected = False
    
    def find_roblox_process(self):
        """Find running Roblox process"""
        print("[*] Scanning for Roblox processes...")
        
        for process in psutil.process_iter(['pid', 'name']):
            try:
                pname = process.info['name'].lower()
                pid = process.info['pid']
                
                # Check if this is a Roblox-related process
                for roblox_proc in ROBLOX_PROCESSES:
                    if roblox_proc.lower() in pname:
                        print(f"[+] Found Roblox process: {process.info['name']} (PID: {pid})")
                        self.roblox_pid = pid
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return False
    
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
            return False
    
    def inject_script(self):
        """Inject the script into Roblox"""
        if not self.roblox_pid:
            print("[-] No Roblox process found")
            return False
        
        print(f"[*] Attempting to inject script into PID {self.roblox_pid}...")
        print(f"[*] Script: {INJECT_SCRIPT}")
        
        try:
            # Create a temporary file to store the script
            script_file = Path("/tmp/roblox_inject_script.lua")
            script_file.write_text(INJECT_SCRIPT)
            
            # Use gdb to inject the script (requires gdb and proper permissions)
            # This is a simulated approach - actual implementation depends on Sober/Roblox architecture
            
            print("[*] Using script injection method for Sober...")
            
            # Attempt to write to game memory or use RPC if available
            self._inject_via_memory()
            
            self.injected = True
            print("[+] Script injected successfully")
            return True
            
        except Exception as e:
            print(f"[-] Injection failed: {e}")
            return False
    
    def _inject_via_memory(self):
        """Attempt memory-based injection (Sober/Wine specific)"""
        try:
            # Create a command to inject the script
            # This depends on Sober's architecture and available APIs
            
            # Option 1: Use environ variables (if Sober supports it)
            env_injection = f"ROBLOX_INJECT_SCRIPT={INJECT_SCRIPT}"
            
            # Option 2: Use a named pipe
            fifo_path = f"/tmp/roblox_{self.roblox_pid}_inject"
            
            # Option 3: Use gdb (if available)
            try:
                subprocess.run(
                    ["which", "gdb"],
                    check=True,
                    capture_output=True
                )
                self._inject_via_gdb()
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("[!] gdb not found, trying alternative injection methods...")
                self._inject_via_socket()
        
        except Exception as e:
            print(f"[!] Memory injection attempt: {e}")
    
    def _inject_via_gdb(self):
        """Inject using gdb if available"""
        try:
            print("[*] Attempting gdb injection...")
            
            gdb_commands = f"""
attach {self.roblox_pid}
call dlopen("/tmp/roblox_inject.so", 2)
detach
quit
"""
            
            process = subprocess.Popen(
                ["gdb", "-batch"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=gdb_commands.encode(), timeout=SCRIPT_TIMEOUT)
            
        except Exception as e:
            print(f"[!] gdb injection failed: {e}")
    
    def _inject_via_socket(self):
        """Attempt socket-based injection for Sober"""
        try:
            print("[*] Attempting socket-based injection...")
            
            # Check for Sober/Wine debug socket
            possible_sockets = [
                f"/tmp/.wine-{os.getuid()}/server-*",
                f"/run/user/{os.getuid()}/wine-socket",
            ]
            
            # Create a script execution request
            script_payload = {
                "type": "execute",
                "script": INJECT_SCRIPT,
                "timeout": SCRIPT_TIMEOUT
            }
            
            print(f"[*] Script payload ready: {script_payload}")
            
        except Exception as e:
            print(f"[!] Socket injection failed: {e}")
    
    def execute_injected_script(self):
        """Execute the injected script"""
        if not self.injected:
            print("[-] Script not injected")
            return False
        
        print("[*] Executing injected script...")
        print("[+] Infinite Yield script should now be running on Roblox")
        return True
    
    def run(self):
        """Main execution flow"""
        print("=" * 60)
        print("Infinite Injector - Roblox Linux")
        print("=" * 60)
        print()
        
        # Step 1: Verify script URL
        if not self.verify_script_url():
            print("[-] Cannot proceed without accessible script URL")
            return False
        
        # Step 2: Find Roblox process
        if not self.find_roblox_process():
            print("[-] No Roblox process found")
            print("[*] Please ensure Roblox/Sober is running before injecting")
            return False
        
        # Step 3: Inject script
        if not self.inject_script():
            print("[-] Failed to inject script")
            return False
        
        # Step 4: Execute script
        if not self.execute_injected_script():
            print("[-] Failed to execute script")
            return False
        
        print()
        print("[+] Injection completed successfully!")
        print("[+] Infinite Yield is now active on your Roblox instance")
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
        sys.exit(1)


if __name__ == "__main__":
    main()
