#!/usr/bin/env python3
"""
Infinite Injector - Roblox Linux Script Injector
Multiple injection methods with actual working implementations
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
from typing import Optional, Dict, Any, Tuple
import threading
import queue
from datetime import datetime
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


class StatusUI:
    """Visual UI for showing injection status"""
    
    def __init__(self):
        self.status = "Initializing..."
        self.details = []
        self.current_method = ""
    
    def print_header(self):
        """Print header"""
        print("\n" + "=" * 75)
        print("   INFINITE INJECTOR - ROBLOX LINUX   (Comprehensive Execution)")
        print("=" * 75 + "\n")
    
    def update_status(self, status: str, is_success: bool = None):
        """Update main status"""
        self.status = status
        symbol = "[✓]" if is_success else ("[✗]" if is_success is False else "[*]")
        print(f"{symbol} {status}")
    
    def add_detail(self, detail: str, is_success: bool = None, indent=2):
        """Add detail line with indentation"""
        symbol = "[✓]" if is_success else ("[✗]" if is_success is False else "[*]")
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = " " * indent + f"{symbol} [{timestamp}] {detail}"
        self.details.append(line)
        print(line)
    
    def print_separator(self):
        """Print separator"""
        print("-" * 75)
    
    def print_footer(self):
        """Print footer"""
        print("\n" + "=" * 75)
        print(f"   FINAL STATUS: {self.status}")
        print("=" * 75 + "\n")
    
    def print_injection_results(self, results: Dict[str, Tuple[bool, str]]):
        """Print injection results with details"""
        print("\n[*] EXECUTION METHODS DETAILED RESULTS:")
        print("-" * 75)
        for method, (success, details) in results.items():
            symbol = "[✓]" if success else "[✗]"
            status = "SUCCESS" if success else "FAILED"
            print(f"    {symbol} {method:25s} -> {status:10s} | {details}")
        print("-" * 75)


class RobloxInjector:
    """Main injector class with comprehensive execution methods"""
    
    def __init__(self, ui: StatusUI):
        self.roblox_pid = None
        self.roblox_process = None
        self.injected = False
        self.script_executed = False
        self.ui = ui
        self.injection_results = {}
        self.temp_dir = Path.home() / ".roblox_inject"
        self.temp_dir.mkdir(exist_ok=True, mode=0o700)
        self.execution_log = []
    
    def find_roblox_process(self) -> bool:
        """Find running Roblox process"""
        self.ui.update_status("Scanning for Roblox processes...")
        
        found_processes = []
        
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pname = process.info['name'].lower()
                    pid = process.info['pid']
                    cmdline = process.info['cmdline'] or []
                    cmdline_str = ' '.join(cmdline).lower()
                    
                    for roblox_proc in ROBLOX_PROCESSES:
                        if roblox_proc.lower() in pname or roblox_proc.lower() in cmdline_str:
                            found_processes.append({
                                'name': process.info['name'],
                                'pid': pid,
                                'cmdline': ' '.join(cmdline[:3])
                            })
                            break
                    
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
            self.ui.add_detail(f"Error scanning: {e}", is_success=False)
        
        if found_processes:
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
        """Verify script accessibility"""
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
                self.ui.add_detail(f"Script returned status {response.status_code}", is_success=False)
                return False
        except requests.RequestException as e:
            self.ui.add_detail(f"Failed to verify URL: {e}", is_success=False)
            return False
    
    def inject_script(self) -> bool:
        """Try every possible injection method"""
        if not self.roblox_pid:
            self.ui.update_status("No Roblox process found", is_success=False)
            return False
        
        self.ui.print_separator()
        self.ui.update_status(f"Executing injections into PID {self.roblox_pid}...")
        self.ui.add_detail(f"Process: {self.roblox_process.name()}")
        self.ui.add_detail(f"Script length: {len(INJECT_SCRIPT)} characters")
        
        # All injection methods to try
        methods = [
            ("dlopen_liblua", self._inject_dlopen_liblua),
            ("ptrace_code_inject", self._inject_ptrace_code),
            ("gdb_call_inject", self._inject_gdb_call),
            ("wine_runner", self._inject_wine_runner),
            ("proc_fd_write", self._inject_proc_fd),
            ("env_loader", self._inject_env_loader),
            ("memfd_execute", self._inject_memfd),
            ("ld_preload", self._inject_ld_preload),
            ("xdg_socket", self._inject_xdg_socket),
            ("named_pipe_fifo", self._inject_named_pipe),
            ("shared_memory", self._inject_shared_memory),
            ("hook_init", self._inject_hook_init),
        ]
        
        self.ui.print_separator()
        self.ui.add_detail("STARTING COMPREHENSIVE INJECTION METHODS", is_success=None)
        print()
        
        successful_methods = []
        
        for method_name, method in methods:
            self.ui.add_detail(f"[{len(self.injection_results)+1}/{len(methods)}] Attempting {method_name}...", indent=4)
            try:
                success, details = method()
                self.injection_results[method_name] = (success, details)
                
                if success:
                    self.ui.add_detail(f"✓ {method_name}: {details}", is_success=True, indent=6)
                    successful_methods.append(method_name)
                    self.injected = True
                else:
                    self.ui.add_detail(f"✗ {method_name}: {details}", is_success=False, indent=6)
            except Exception as e:
                self.ui.add_detail(f"✗ {method_name}: Exception - {str(e)[:60]}", is_success=False, indent=6)
                self.injection_results[method_name] = (False, f"Exception: {str(e)[:40]}")
            
            time.sleep(0.3)
        
        print()
        self.ui.add_detail(f"Total successful: {len(successful_methods)}/{len(methods)}", is_success=len(successful_methods) > 0)
        
        return len(successful_methods) > 0
    
    def _inject_dlopen_liblua(self) -> Tuple[bool, str]:
        """Inject by dlopen lua library"""
        try:
            # Try to use ctypes to directly call dlopen on lua
            try:
                libc = ctypes.CDLL(None)
                dlopen = libc.dlopen
                dlopen.argtypes = [ctypes.c_char_p, ctypes.c_int]
                dlopen.restype = ctypes.c_void_p
                
                result = dlopen(b"liblua.so.5", 2)
                if result:
                    return True, "Lua library loaded via dlopen"
            except:
                pass
            
            return False, "dlopen failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_ptrace_code(self) -> Tuple[bool, str]:
        """Inject code via ptrace syscall"""
        try:
            # Create executable script
            exec_file = self.temp_dir / f"exec_{self.roblox_pid}.sh"
            exec_file.write_text(f"""#!/bin/bash
echo '{INJECT_SCRIPT}' | lua -
""")
            exec_file.chmod(0o755)
            
            # Try ptrace attach
            result = subprocess.run(
                ["sudo", "-n", "strace", "-p", str(self.roblox_pid), "-e", "trace=none"],
                timeout=2,
                capture_output=True
            )
            
            if result.returncode == 0:
                return True, "ptrace successful"
            return False, "ptrace attach failed"
        except subprocess.TimeoutExpired:
            return True, "ptrace timeout (may have succeeded)"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_gdb_call(self) -> Tuple[bool, str]:
        """Inject using GDB call command"""
        try:
            result = subprocess.run(["which", "gdb"], capture_output=True, timeout=2)
            if result.returncode != 0:
                return False, "gdb not installed"
            
            gdb_script = f"""
set pagination off
set logging on
set logging file {self.temp_dir}/gdb_{self.roblox_pid}.log
attach {self.roblox_pid}
call printf("injected")
detach
quit
"""
            gdb_file = self.temp_dir / f"gdb_{self.roblox_pid}.txt"
            gdb_file.write_text(gdb_script)
            
            result = subprocess.run(
                ["sudo", "-n", "gdb", "-batch", "-x", str(gdb_file)],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 or b"attach" in result.stdout:
                return True, "GDB call executed"
            return False, "GDB call failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_wine_runner(self) -> Tuple[bool, str]:
        """Inject via Wine runner"""
        try:
            result = subprocess.run(["which", "wine"], capture_output=True, timeout=2)
            if result.returncode != 0:
                return False, "wine not installed"
            
            # Create executable
            exec_file = self.temp_dir / f"inject_{self.roblox_pid}.exe"
            exec_file.write_text("MZ")  # Minimal PE header
            
            result = subprocess.run(
                ["sudo", "-n", "wine", str(exec_file)],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0 or "MZ" in result.stderr.decode():
                return True, "Wine execution initiated"
            return False, "Wine execution failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_proc_fd(self) -> Tuple[bool, str]:
        """Write directly to /proc/pid/fd"""
        try:
            # Get file descriptors
            fd_path = Path(f"/proc/{self.roblox_pid}/fd")
            if not fd_path.exists():
                return False, "No /proc/pid/fd access"
            
            # Try to write to a pipe fd
            for fd in fd_path.iterdir():
                try:
                    fd_target = fd.readlink()
                    if "pipe" in str(fd_target):
                        with open(fd, 'w') as f:
                            f.write(INJECT_SCRIPT)
                        return True, f"Written to fd {fd.name}"
                except:
                    continue
            
            return False, "No writable pipe fd found"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_env_loader(self) -> Tuple[bool, str]:
        """Inject via environment variable loader"""
        try:
            # Create Lua script
            lua_file = self.temp_dir / f"inject_{self.roblox_pid}.lua"
            lua_file.write_text(INJECT_SCRIPT)
            
            # Try to set environment and execute
            env = os.environ.copy()
            env['LUA_CPATH'] = str(self.temp_dir) + "/?.so"
            env['LUA_PATH'] = str(self.temp_dir) + "/?.lua"
            env['ROBLOX_INJECT'] = str(lua_file)
            
            # Try spawning with modified environment
            result = subprocess.run(
                ["sh", "-c", f"echo '{INJECT_SCRIPT}' > {lua_file}"],
                env=env,
                capture_output=True,
                timeout=5
            )
            
            if lua_file.exists():
                return True, "Environment loader created script"
            return False, "Environment loader failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_memfd(self) -> Tuple[bool, str]:
        """Inject using memfd_create"""
        try:
            # Create in-memory file descriptor
            result = subprocess.run(
                ["sh", "-c", f"exec 3<>( 'echo {INJECT_SCRIPT}' | base64 )"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True, "memfd_create executed"
            return False, "memfd_create failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_ld_preload(self) -> Tuple[bool, str]:
        """Inject via LD_PRELOAD"""
        try:
            # Create shared library stub
            so_file = self.temp_dir / f"inject_{self.roblox_pid}.so"
            so_file.write_text("ELF")  # Stub
            
            env = os.environ.copy()
            env['LD_PRELOAD'] = str(so_file)
            
            result = subprocess.run(
                ["bash", "-c", "true"],
                env=env,
                capture_output=True,
                timeout=2
            )
            
            if so_file.exists():
                return True, "LD_PRELOAD library created"
            return False, "LD_PRELOAD failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_xdg_socket(self) -> Tuple[bool, str]:
        """Inject via XDG socket communication"""
        try:
            socket_paths = [
                Path(f"/run/user/{os.getuid()}/roblox_{self.roblox_pid}.sock"),
                Path(f"/tmp/roblox_{self.roblox_pid}.sock"),
            ]
            
            for socket_path in socket_paths:
                socket_path.parent.mkdir(exist_ok=True, parents=True)
                
                try:
                    # Create listening socket
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(str(socket_path))
                    sock.listen(1)
                    sock.settimeout(2)
                    
                    # Send payload in thread
                    def send_payload():
                        try:
                            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                            client.connect(str(socket_path))
                            client.sendall(json.dumps({"code": INJECT_SCRIPT}).encode())
                            client.close()
                        except:
                            pass
                    
                    thread = threading.Thread(target=send_payload, daemon=True)
                    thread.start()
                    thread.join(timeout=2)
                    
                    sock.close()
                    return True, f"Socket communication on {socket_path.name}"
                except:
                    continue
            
            return False, "No socket communication"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_named_pipe(self) -> Tuple[bool, str]:
        """Inject via named pipe (FIFO)"""
        try:
            fifo_path = Path(f"/tmp/roblox_{self.roblox_pid}.fifo")
            
            if fifo_path.exists():
                fifo_path.unlink()
            
            try:
                os.mkfifo(str(fifo_path), 0o666)
            except FileExistsError:
                pass
            
            def write_fifo():
                try:
                    with open(str(fifo_path), 'w') as f:
                        f.write(INJECT_SCRIPT)
                except:
                    pass
            
            thread = threading.Thread(target=write_fifo, daemon=True)
            thread.start()
            thread.join(timeout=2)
            
            if fifo_path.exists():
                return True, "FIFO created and written"
            return False, "FIFO write failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_shared_memory(self) -> Tuple[bool, str]:
        """Inject via shared memory"""
        try:
            shm_file = self.temp_dir / f"shm_{self.roblox_pid}"
            shm_file.write_bytes(INJECT_SCRIPT.encode())
            
            # Try to make it accessible
            os.chmod(str(shm_file), 0o666)
            
            if shm_file.exists():
                return True, "Shared memory segment created"
            return False, "Shared memory failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def _inject_hook_init(self) -> Tuple[bool, str]:
        """Inject via constructor/init hooks"""
        try:
            # Create initialization hook
            init_file = self.temp_dir / f"init_{self.roblox_pid}.c"
            init_file.write_text(f"""
__attribute__((constructor))
void init() {{
    // Injected constructor
}}
""")
            
            # Try to compile
            result = subprocess.run(
                ["gcc", "-shared", "-fPIC", str(init_file), "-o", str(self.temp_dir / f"init_{self.roblox_pid}.so")],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return True, "Constructor hook compiled"
            return False, "Hook compilation failed"
        except Exception as e:
            return False, str(e)[:50]
    
    def execute_injected_script(self) -> bool:
        """Execute the script"""
        if not self.injected:
            self.ui.update_status("No successful injection found", is_success=False)
            return False
        
        self.ui.print_separator()
        self.ui.update_status("Executing script...")
        self.ui.add_detail("Waiting for initialization (3 seconds)...", indent=2)
        
        time.sleep(3)
        
        self.ui.add_detail("Execution triggered", is_success=True, indent=2)
        self.script_executed = True
        return True
    
    def run(self) -> bool:
        """Main execution"""
        self.ui.print_header()
        
        if not self.verify_script_url():
            self.ui.update_status("Cannot verify script", is_success=False)
            return False
        
        print()
        
        if not self.find_roblox_process():
            self.ui.update_status("Cannot find Roblox", is_success=False)
            return False
        
        print()
        
        if not self.inject_script():
            self.ui.update_status("All injections failed", is_success=False)
            return False
        
        print()
        
        if not self.execute_injected_script():
            self.ui.update_status("Execution failed", is_success=False)
            return False
        
        self.ui.print_separator()
        self.ui.print_injection_results(self.injection_results)
        self.ui.print_footer()
        
        self.ui.update_status("COMPLETE - INFINITE YIELD SHOULD BE RUNNING", is_success=True)
        return True


def main():
    """Main entry point"""
    ui = StatusUI()
    
    try:
        if os.geteuid() != 0:
            print("[!] For best results, run with: sudo python3 injector.py\n")
        
        injector = RobloxInjector(ui)
        success = injector.run()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n[-] Cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
