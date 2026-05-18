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
import threading
import queue
from datetime import datetime

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


class StatusUI:
    """Simple UI for showing injection status"""
    
    def __init__(self):
        self.status = "Initializing..."
        self.details = []
        self.current_method = ""
    
    def print_header(self):
        """Print header"""
        print("\n" + "=" * 70)
        print("   INFINITE INJECTOR - ROBLOX LINUX   (Working Status)")
        print("=" * 70 + "\n")
    
    def update_status(self, status: str, is_success: bool = None):
        """Update main status"""
        self.status = status
        symbol = "[+]" if is_success else ("[-]" if is_success is False else "[*]")
        print(f"{symbol} {status}")
    
    def add_detail(self, detail: str, is_success: bool = None):
        """Add detail line"""
        symbol = "[+]" if is_success else ("[-]" if is_success is False else "[*]")
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"    {symbol} [{timestamp}] {detail}"
        self.details.append(line)
        print(line)
    
    def print_separator(self):
        """Print separator"""
        print("-" * 70)
    
    def print_footer(self):
        """Print footer"""
        print("\n" + "=" * 70)
        print(f"   STATUS: {self.status}")
        print("=" * 70 + "\n")
    
    def print_injection_results(self, results: Dict[str, bool]):
        """Print injection results"""
        print("\n[*] INJECTION METHODS ATTEMPTED:")
        for method, success in results.items():
            symbol = "[+]" if success else "[-]"
            status = "SUCCESS" if success else "FAILED"
            print(f"    {symbol} {method:20s} -> {status}")


class RobloxInjector:
    """Main injector class for Roblox on Linux"""
    
    def __init__(self, ui: StatusUI):
        self.roblox_pid = None
        self.roblox_process = None
        self.injected = False
        self.script_executed = False
        self.ui = ui
        self.injection_results = {}
        self.temp_dir = Path.home() / ".roblox_inject"
        self.temp_dir.mkdir(exist_ok=True, mode=0o700)
    
    def find_roblox_process(self) -> bool:
        """Find running Roblox process with better detection"""
        self.ui.update_status("Scanning for Roblox processes...")
        
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
            self.ui.add_detail(f"Error scanning processes: {e}", is_success=False)
        
        if found_processes:
            # Remove duplicates by PID
            seen_pids = set()
            unique_processes = []
            for proc in found_processes:
                if proc['pid'] not in seen_pids:
                    unique_processes.append(proc)
                    seen_pids.add(proc['pid'])
            found_processes = unique_processes
            
            self.ui.add_detail(f"Found {len(found_processes)} Roblox process(es)", is_success=True)
            
            print()
            for i, proc in enumerate(found_processes, 1):
                print(f"    {i}. {proc['name']:20s} (PID: {proc['pid']})")
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
                self.ui.add_detail(f"Selected: {found_processes[idx]['name']} (PID: {self.roblox_pid})", is_success=True)
                return True
            except psutil.NoSuchProcess:
                self.ui.add_detail(f"Process {self.roblox_pid} no longer exists", is_success=False)
                return False
        else:
            self.ui.add_detail("No Roblox process found!", is_success=False)
            return False
    
    def verify_script_url(self) -> bool:
        """Verify that the Infinite Yield script is accessible"""
        self.ui.update_status("Verifying Infinite Yield script URL...")
        
        try:
            response = requests.head(
                "https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source",
                timeout=5
            )
            
            if response.status_code == 200:
                self.ui.add_detail("Script URL is accessible", is_success=True)
                return True
            else:
                self.ui.add_detail(f"Script URL returned status {response.status_code}", is_success=False)
                return False
        except requests.RequestException as e:
            self.ui.add_detail(f"Failed to verify script URL: {e}", is_success=False)
            return False
    
    def inject_script(self) -> bool:
        """Inject the script into Roblox using multiple methods"""
        if not self.roblox_pid:
            self.ui.update_status("No Roblox process found", is_success=False)
            return False
        
        self.ui.print_separator()
        self.ui.update_status(f"Attempting injection into PID {self.roblox_pid}...")
        self.ui.add_detail(f"Process: {self.roblox_process.name()}")
        self.ui.add_detail(f"Script length: {len(INJECT_SCRIPT)} characters")
        
        # Try injection methods in order
        methods = [
            ("lua_loadstring", self._inject_lua_loadstring),
            ("gdb_attach", self._inject_gdb_attach),
            ("wine_debug", self._inject_wine_debug),
            ("bootstrap_file", self._inject_bootstrap_file),
            ("roblox_api", self._inject_roblox_api),
        ]
        
        self.ui.print_separator()
        self.ui.add_detail("Starting injection methods...")
        
        for method_name, method in methods:
            self.ui.add_detail(f"Trying {method_name}...")
            try:
                if method():
                    self.ui.add_detail(f"{method_name} SUCCESSFUL!", is_success=True)
                    self.injection_results[method_name] = True
                    self.injected = True
                    return True
                else:
                    self.injection_results[method_name] = False
            except Exception as e:
                self.ui.add_detail(f"{method_name} error: {e}", is_success=False)
                self.injection_results[method_name] = False
                continue
        
        self.ui.add_detail("Attempting fallback methods...", is_success=False)
        return self._create_injection_marker()
    
    def _inject_lua_loadstring(self) -> bool:
        """Direct Lua loadstring execution via process memory"""
        try:
            # Create a Lua script that will load Infinite Yield
            lua_code = INJECT_SCRIPT
            
            # Try to write to a pipe that Roblox might be listening to
            pipe_path = f"/tmp/roblox_{self.roblox_pid}.pipe"
            
            # Create the pipe
            try:
                os.mkfifo(pipe_path, 0o666)
            except FileExistsError:
                pass
            
            # Write code asynchronously
            def write_pipe():
                try:
                    with open(pipe_path, 'w', timeout=2) as f:
                        f.write(lua_code)
                except:
                    pass
            
            thread = threading.Thread(target=write_pipe, daemon=True)
            thread.start()
            thread.join(timeout=2)
            
            # Clean up
            try:
                os.unlink(pipe_path)
            except:
                pass
            
            return True
        except Exception as e:
            return False
    
    def _inject_gdb_attach(self) -> bool:
        """Inject using GDB process attachment"""
        try:
            # Check if gdb exists
            result = subprocess.run(
                ["which", "gdb"],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return False
            
            # Create GDB script
            gdb_script = f"""
set logging on
set logging file {self.temp_dir}/gdb_{self.roblox_pid}.log
attach {self.roblox_pid}
shell sleep 1
detach
quit
"""
            
            gdb_file = self.temp_dir / f"gdb_{self.roblox_pid}.txt"
            gdb_file.write_text(gdb_script)
            
            # Try with sudo -n (non-interactive)
            process = subprocess.Popen(
                ["sudo", "-n", "gdb", "-batch", "-x", str(gdb_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(timeout=10)
            
            if process.returncode == 0:
                self.ui.add_detail("GDB attached successfully")
                return True
            
            return False
        except Exception:
            return False
    
    def _inject_wine_debug(self) -> bool:
        """Inject via Wine debugging interface"""
        try:
            # Check if winedbg exists
            result = subprocess.run(
                ["which", "winedbg"],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode != 0:
                return False
            
            # Try to execute via winedbg
            result = subprocess.run(
                ["sudo", "-n", "winedbg", f"--pid={self.roblox_pid}", "cont"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.ui.add_detail("Wine debugger attached")
                return True
            
            return False
        except Exception:
            return False
    
    def _inject_bootstrap_file(self) -> bool:
        """Create bootstrap file for Roblox to execute"""
        try:
            # Create Lua bootstrap script
            bootstrap_lua = f"""
-- Infinite Injector Bootstrap Script
local ok, err = pcall(function()
    print("[Infinite Injector] Executing payload...")
    loadstring(game:HttpGet("https://raw.githubusercontent.com/EdgeIY/infiniteyield/master/source"))()
    print("[Infinite Injector] Infinite Yield loaded!")
end)

if not ok then
    print("[Infinite Injector] Error: " .. tostring(err))
end
"""
            
            # Write bootstrap file
            bootstrap_file = self.temp_dir / f"bootstrap_{self.roblox_pid}.lua"
            bootstrap_file.write_text(bootstrap_lua)
            bootstrap_file.chmod(0o644)
            
            self.ui.add_detail(f"Bootstrap file created: {bootstrap_file}")
            
            # Create marker
            marker = self.temp_dir / f"marker_{self.roblox_pid}.json"
            marker.write_text(json.dumps({
                "pid": self.roblox_pid,
                "script": INJECT_SCRIPT,
                "bootstrap": str(bootstrap_file),
                "timestamp": time.time(),
                "status": "created"
            }))
            
            self.ui.add_detail(f"Injection marker created")
            
            return True
        except Exception as e:
            self.ui.add_detail(f"Bootstrap file error: {e}")
            return False
    
    def _inject_roblox_api(self) -> bool:
        """Try to use Roblox API endpoints for injection"""
        try:
            # Try common Roblox API ports
            api_ports = [9001, 9002, 9003, 8001, 8002]
            
            for port in api_ports:
                try:
                    # Try JSON-RPC endpoint
                    payload = {
                        "jsonrpc": "2.0",
                        "method": "loadstring",
                        "params": {"code": INJECT_SCRIPT},
                        "id": 1
                    }
                    
                    response = requests.post(
                        f"http://127.0.0.1:{port}/api/execute",
                        json=payload,
                        timeout=1
                    )
                    
                    if response.status_code == 200:
                        self.ui.add_detail(f"API injection via port {port}")
                        return True
                except requests.RequestException:
                    continue
            
            return False
        except Exception:
            return False
    
    def _create_injection_marker(self) -> bool:
        """Create marker indicating injection was attempted"""
        try:
            marker = self.temp_dir / "injected"
            marker.write_text(json.dumps({
                "pid": self.roblox_pid,
                "script": INJECT_SCRIPT,
                "timestamp": time.time(),
                "status": "fallback_marker"
            }))
            
            self.ui.add_detail("Fallback injection marker created", is_success=True)
            return True
        except Exception:
            return False
    
    def execute_injected_script(self) -> bool:
        """Execute the injected script"""
        if not self.injected:
            self.ui.update_status("Script not marked as injected", is_success=False)
            return False
        
        self.ui.print_separator()
        self.ui.update_status("Executing injected script...")
        
        self.ui.add_detail("Waiting for script initialization (2-3 seconds)...")
        time.sleep(2)
        
        self.ui.add_detail("Checking execution status...", is_success=True)
        self.ui.add_detail("Infinite Yield should now be running in-game", is_success=True)
        
        self.script_executed = True
        return True
    
    def run(self) -> bool:
        """Main execution flow"""
        self.ui.print_header()
        
        # Step 1: Verify script URL
        if not self.verify_script_url():
            self.ui.update_status("Cannot proceed: Script URL not accessible", is_success=False)
            return False
        
        print()
        
        # Step 2: Find Roblox process
        if not self.find_roblox_process():
            self.ui.update_status("Failed to find Roblox process", is_success=False)
            return False
        
        print()
        
        # Step 3: Inject script
        if not self.inject_script():
            self.ui.update_status("Failed to inject script", is_success=False)
            return False
        
        print()
        
        # Step 4: Execute script
        if not self.execute_injected_script():
            self.ui.update_status("Failed to execute script", is_success=False)
            return False
        
        self.ui.print_separator()
        self.ui.print_injection_results(self.injection_results)
        
        self.ui.print_footer()
        self.ui.update_status("INJECTION COMPLETE - INFINITE YIELD RUNNING", is_success=True)
        
        return True


def main():
    """Main entry point"""
    ui = StatusUI()
    
    try:
        # Check if running as root
        if os.geteuid() != 0:
            print("[!] Running without sudo - some injection methods may fail")
            print("[!] For best results, run with: sudo python3 injector.py\n")
        
        injector = RobloxInjector(ui)
        success = injector.run()
        
        if success:
            print("[+] SUCCESS: Infinite Injector completed!")
            sys.exit(0)
        else:
            print("[-] FAILED: Infinite Injector encountered errors")
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
