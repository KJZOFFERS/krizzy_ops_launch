"""
Watchdog system for KRIZZY OPS with restart logic and proxy rotation.
"""
import time
import subprocess
import signal
import os
import sys
import requests
from typing import Dict, Any, List, Optional
from airtable_utils import fetch_all, airtable
from discord_utils import post_ops, post_err
from kpi import kpi_push
import datetime


class ProcessManager:
    """Manages process lifecycle with restart logic and error handling."""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.restart_counts: Dict[str, int] = {}
        self.max_restarts = 5
        self.restart_delay = 5
        self.proxy_rotation_enabled = True
        self.current_proxy_index = 0
        
        # Proxy list for rotation on 403/5xx errors
        self.proxies = [
            None,  # Direct connection
            # Add proxy configurations here if needed
        ]
    
    def start_process(self, name: str, command: List[str], cwd: str = None) -> bool:
        """Start a process with error handling."""
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            self.processes[name] = process
            self.restart_counts[name] = 0
            kpi_push("cycle_start", {
                "engine": "watchdog",
                "action": f"started_process_{name}",
                "pid": process.pid
            })
            return True
        except Exception as e:
            kpi_push("error", {
                "error_type": "process_start_error",
                "message": f"Failed to start {name}: {e}",
                "command": " ".join(command)
            })
            return False
    
    def restart_process(self, name: str) -> bool:
        """Restart a failed process with exponential backoff."""
        if name not in self.processes:
            return False
        
        restart_count = self.restart_counts.get(name, 0)
        if restart_count >= self.max_restarts:
            kpi_push("error", {
                "error_type": "max_restarts_exceeded",
                "message": f"Process {name} exceeded max restarts ({self.max_restarts})",
                "restart_count": restart_count
            })
            return False
        
        # Kill existing process
        try:
            process = self.processes[name]
            if process.poll() is None:  # Process is still running
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=10)
        except Exception as e:
            print(f"Error killing process {name}: {e}")
        
        # Wait with exponential backoff
        delay = self.restart_delay * (2 ** restart_count)
        time.sleep(min(delay, 60))  # Cap at 60 seconds
        
        # Restart process
        self.restart_counts[name] = restart_count + 1
        kpi_push("cycle_end", {
            "engine": "watchdog",
            "action": f"restarting_process_{name}",
            "restart_count": restart_count + 1
        })
        
        # For now, just restart the main process
        if name == "main":
            return self.start_process("main", ["python", "main.py"])
        
        return True
    
    def check_process_health(self, name: str) -> bool:
        """Check if a process is healthy."""
        if name not in self.processes:
            return False
        
        process = self.processes[name]
        return process.poll() is None  # None means still running
    
    def rotate_proxy(self) -> Optional[Dict[str, str]]:
        """Rotate to next proxy in the list."""
        if not self.proxy_rotation_enabled or not self.proxies:
            return None
        
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        proxy = self.proxies[self.current_proxy_index]
        
        if proxy:
            return {"http": proxy, "https": proxy}
        return None
    
    def make_request_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with proxy rotation on 403/5xx errors."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                proxy = self.rotate_proxy()
                if proxy:
                    kwargs['proxies'] = proxy
                
                response = requests.get(url, timeout=10, **kwargs)
                
                if response.status_code in [403, 500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        kpi_push("error", {
                            "error_type": "http_error",
                            "message": f"HTTP {response.status_code} on attempt {attempt + 1}, rotating proxy",
                            "url": url
                        })
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    kpi_push("error", {
                        "error_type": "request_error",
                        "message": f"Request failed on attempt {attempt + 1}: {e}",
                        "url": url
                    })
                    time.sleep(2 ** attempt)
                    continue
                else:
                    kpi_push("error", {
                        "error_type": "request_failed",
                        "message": f"All request attempts failed: {e}",
                        "url": url
                    })
                    return None
        
        return None


def run_watchdog() -> int:
    """Run data integrity scan and process monitoring."""
    try:
        kpi_push("cycle_start", {"engine": "watchdog"})
        
        # Data integrity scan
        tables = ["Leads_REI", "GovCon_Opportunities"]
        cleaned = 0
        
        for table_name in tables:
            records = fetch_all(table_name)
            for record in records:
                fields = record.get("fields", {})
                
                # Check for invalid records
                if not fields.get("Source_URL") or not (fields.get("Phone") or fields.get("Email")):
                    cleaned += 1
                    
                    # Optionally delete invalid records
                    # airtable._get_table(table_name).delete(record["id"])
        
        # Process monitoring
        process_manager = ProcessManager()
        
        # Check if main process is running
        if not process_manager.check_process_health("main"):
            kpi_push("error", {
                "error_type": "process_down",
                "message": "Main process is down, attempting restart"
            })
            process_manager.restart_process("main")
        
        post_ops(f"Watchdog scan completed {datetime.datetime.utcnow().isoformat()} | Invalid records: {cleaned}")
        
        kpi_push("cycle_end", {
            "engine": "watchdog",
            "count": cleaned,
            "action": "data_integrity_scan"
        })
        
        return cleaned
        
    except Exception as e:
        kpi_push("error", {
            "error_type": "watchdog_error",
            "message": f"Watchdog failed: {e}"
        })
        post_err(f"Watchdog error: {e}")
        return 0


def run_watchdog_daemon():
    """Run watchdog as a daemon process."""
    kpi_push("boot", {
        "engine": "watchdog_daemon",
        "version": "3.0.0"
    })
    
    while True:
        try:
            run_watchdog()
            time.sleep(300)  # Run every 5 minutes
        except KeyboardInterrupt:
            kpi_push("cycle_end", {
                "engine": "watchdog_daemon",
                "action": "shutdown"
            })
            break
        except Exception as e:
            kpi_push("error", {
                "error_type": "watchdog_daemon_error",
                "message": f"Watchdog daemon error: {e}"
            })
            time.sleep(60)  # Wait before retrying


if __name__ == "__main__":
    run_watchdog_daemon()
