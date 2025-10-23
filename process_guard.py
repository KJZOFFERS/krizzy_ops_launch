import subprocess
import time
import os
import logging
from kpi import track_boot, track_error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main process guard loop with KPI tracking"""
    track_boot()
    logger.info("🧠 Launching KRIZZY OPS v3.0.0 Enterprise Engine...")
    
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        try:
            logger.info(f"Starting KRIZZY OPS (attempt {restart_count + 1})")
            subprocess.run(["python3", "main.py"], check=True)
            
            # If we get here, the process exited cleanly
            logger.info("KRIZZY OPS exited cleanly")
            break
            
        except subprocess.CalledProcessError as e:
            restart_count += 1
            wait_time = min(2 ** restart_count, 60)  # Exponential backoff, cap at 60s
            
            logger.error(f"⚠️ Engine crashed (attempt {restart_count}): {e}")
            track_error("ProcessGuard", f"Engine crashed: {e}", {
                "restart_count": restart_count,
                "exit_code": e.returncode
            })
            
            if restart_count < max_restarts:
                logger.info(f"Restarting in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max restarts ({max_restarts}) reached. Giving up.")
                track_error("ProcessGuard", "Max restarts reached", {
                    "restart_count": restart_count
                })
                break
                
        except KeyboardInterrupt:
            logger.info("Process guard stopped by user")
            break
            
        except Exception as ex:
            restart_count += 1
            wait_time = min(2 ** restart_count, 60)
            
            logger.error(f"Unexpected error (attempt {restart_count}): {ex}")
            track_error("ProcessGuard", f"Unexpected error: {ex}", {
                "restart_count": restart_count
            })
            
            if restart_count < max_restarts:
                logger.info(f"Rebooting in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Max restarts ({max_restarts}) reached. Giving up.")
                track_error("ProcessGuard", "Max restarts reached after unexpected errors", {
                    "restart_count": restart_count
                })
                break

if __name__ == "__main__":
    main()
