"""
Process Guard for KRIZZY OPS v3.0.0
Monitors and restarts the main application with exponential backoff.
"""
import subprocess
import time
import os
import signal
import sys
from datetime import datetime
from logging_config import logger
from kpi import kpi_push


class ProcessGuard:
    """Process monitoring and restart system."""
    
    def __init__(self):
        self.process = None
        self.restart_count = 0
        self.max_restarts = 10
        self.base_delay = 5
        self.max_delay = 300  # 5 minutes
        self.start_time = datetime.now()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.log_info(f"Received signal {signum}, shutting down gracefully")
        self.shutdown()
        sys.exit(0)
    
    def _calculate_delay(self) -> int:
        """Calculate exponential backoff delay."""
        delay = min(self.base_delay * (2 ** self.restart_count), self.max_delay)
        return delay
    
    def _start_process(self) -> bool:
        """Start the main KRIZZY OPS process."""
        try:
            logger.log_info("Starting KRIZZY OPS v3.0.0 process")
            
            self.process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            
            logger.log_info(f"Process started with PID: {self.process.pid}")
            kpi_push("boot", {
                "version": "3.0.0",
                "process_guard": True,
                "pid": self.process.pid,
                "restart_count": self.restart_count
            })
            
            return True
            
        except Exception as e:
            logger.log_error("process_start_error", f"Failed to start process: {e}")
            return False
    
    def _monitor_process(self) -> bool:
        """Monitor the running process."""
        if not self.process:
            return False
        
        try:
            # Check if process is still running
            return_code = self.process.poll()
            
            if return_code is None:
                # Process is still running
                return True
            else:
                # Process has terminated
                logger.log_error("process_terminated", 
                    f"Process terminated with code {return_code}")
                
                # Log stderr if available
                if self.process.stderr:
                    stderr_output = self.process.stderr.read().decode('utf-8')
                    if stderr_output:
                        logger.log_error("process_stderr", stderr_output)
                
                return False
                
        except Exception as e:
            logger.log_error("process_monitor_error", f"Error monitoring process: {e}")
            return False
    
    def _restart_process(self) -> bool:
        """Restart the process with backoff."""
        if self.restart_count >= self.max_restarts:
            logger.log_error("max_restarts_exceeded", 
                f"Maximum restarts ({self.max_restarts}) exceeded. Stopping.")
            kpi_push("error", {
                "error_type": "max_restarts_exceeded",
                "message": f"Process guard stopped after {self.restart_count} restarts",
                "max_restarts": self.max_restarts
            })
            return False
        
        self.restart_count += 1
        delay = self._calculate_delay()
        
        logger.log_warning(f"Restarting process in {delay} seconds (attempt {self.restart_count})")
        kpi_push("cycle_end", {
            "engine": "process_guard",
            "action": "restart",
            "restart_count": self.restart_count,
            "delay_seconds": delay
        })
        
        time.sleep(delay)
        return self._start_process()
    
    def shutdown(self):
        """Gracefully shutdown the process."""
        if self.process and self.process.poll() is None:
            logger.log_info("Shutting down main process")
            try:
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.log_warning("Process did not shutdown gracefully, force killing")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait()
                
            except Exception as e:
                logger.log_error("shutdown_error", f"Error during shutdown: {e}")
    
    def run(self):
        """Main process guard loop."""
        logger.log_boot("3.0.0", os.getenv("ENVIRONMENT", "production"))
        
        while True:
            try:
                # Start process if not running
                if not self.process or self.process.poll() is not None:
                    if not self._start_process():
                        logger.log_error("startup_failed", "Failed to start process, retrying...")
                        time.sleep(10)
                        continue
                
                # Monitor process
                if not self._monitor_process():
                    # Process died, restart it
                    if not self._restart_process():
                        logger.log_error("restart_failed", "Failed to restart process, exiting")
                        break
                
                # Reset restart count on successful run
                if self.restart_count > 0:
                    uptime = (datetime.now() - self.start_time).total_seconds()
                    if uptime > 3600:  # Reset after 1 hour of uptime
                        logger.log_info(f"Resetting restart count after {uptime:.0f}s uptime")
                        self.restart_count = 0
                        self.start_time = datetime.now()
                
                # Sleep before next check
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.log_info("Received keyboard interrupt, shutting down")
                break
            except Exception as e:
                logger.log_error("guard_loop_error", f"Unexpected error in guard loop: {e}")
                time.sleep(10)
        
        self.shutdown()
        logger.log_info("Process guard stopped")


def main():
    """Main entry point for process guard."""
    guard = ProcessGuard()
    guard.run()


if __name__ == "__main__":
    main()
