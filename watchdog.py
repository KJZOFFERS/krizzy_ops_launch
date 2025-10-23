import os
import time
import random
import logging
import subprocess
import requests
from typing import List, Dict, Any, Optional
from airtable_utils import fetch_all, safe_airtable_write
from discord_utils import post_ops, post_error
from kpi import track_cycle_start, track_cycle_end, track_error
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Proxy rotation list (add your proxy endpoints here)
PROXY_ENDPOINTS = [
    None,  # Direct connection
    # Add proxy URLs here if needed
    # "http://proxy1:port",
    # "http://proxy2:port",
]

class WatchdogError(Exception):
    """Custom exception for watchdog operations"""
    pass

def get_proxy_config() -> Optional[Dict[str, str]]:
    """Get random proxy configuration for rotation"""
    proxy_url = random.choice(PROXY_ENDPOINTS)
    if proxy_url:
        return {
            "http": proxy_url,
            "https": proxy_url
        }
    return None

def make_request_with_retry(url: str, max_retries: int = 3) -> Optional[requests.Response]:
    """Make HTTP request with proxy rotation and retry logic"""
    for attempt in range(max_retries):
        try:
            proxy_config = get_proxy_config()
            response = requests.get(url, proxies=proxy_config, timeout=30)
            
            if response.status_code == 403:
                logger.warning(f"403 error on attempt {attempt + 1}, rotating proxy")
                continue
            elif response.status_code == 429:
                wait_time = 2 ** attempt + random.uniform(0, 1)  # Exponential backoff with jitter
                logger.warning(f"Rate limited, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                continue
            elif response.status_code >= 500:
                logger.warning(f"Server error {response.status_code} on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    
    return None

def run_watchdog() -> int:
    """Run data integrity scan and cleanup"""
    try:
        track_cycle_start("Watchdog")
        
        tables = ["Leads_REI", "GovCon_Opportunities"]
        cleaned = 0
        
        for table_name in tables:
            try:
                records = fetch_all(table_name)
                invalid_records = []
                
                for record in records:
                    fields = record.get("fields", {})
                    
                    # Check for invalid records
                    is_invalid = False
                    if table_name == "Leads_REI":
                        is_invalid = not fields.get("Source_URL") or not (fields.get("Phone") or fields.get("Email"))
                    elif table_name == "GovCon_Opportunities":
                        is_invalid = not fields.get("Solicitation #") or not fields.get("Email")
                    
                    if is_invalid:
                        invalid_records.append(record["id"])
                        cleaned += 1
                
                # Clean up invalid records
                if invalid_records:
                    logger.info(f"Cleaning {len(invalid_records)} invalid records from {table_name}")
                    # Note: Airtable doesn't have batch delete, so we'd need to delete one by one
                    # For now, just log the invalid records
                    for record_id in invalid_records:
                        logger.info(f"Invalid record {record_id} in {table_name}")
                
            except Exception as e:
                logger.error(f"Error processing table {table_name}: {e}")
                track_error("Watchdog", f"Table {table_name} processing failed: {e}")
        
        track_cycle_end("Watchdog", cleaned, success=True)
        post_ops(f"Watchdog scan completed {datetime.datetime.utcnow().isoformat()} | Invalid: {cleaned}")
        
        return cleaned
        
    except Exception as e:
        track_error("Watchdog", str(e))
        post_error(f"Watchdog scan failed: {e}")
        logger.error(f"Watchdog scan failed: {e}")
        return 0

def restart_failed_loop(loop_name: str, max_restarts: int = 5) -> bool:
    """Restart a failed loop with exponential backoff"""
    restart_count = 0
    
    while restart_count < max_restarts:
        try:
            logger.info(f"Starting {loop_name} (attempt {restart_count + 1})")
            
            if loop_name == "rei":
                from rei_dispo_engine import run_rei
                run_rei()
            elif loop_name == "govcon":
                from govcon_subtrap_engine import run_govcon
                run_govcon()
            elif loop_name == "watchdog":
                run_watchdog()
            else:
                logger.error(f"Unknown loop: {loop_name}")
                return False
            
            logger.info(f"{loop_name} completed successfully")
            return True
            
        except Exception as e:
            restart_count += 1
            wait_time = min(2 ** restart_count, 60) + random.uniform(0, 5)  # Cap at 60s + jitter
            
            logger.error(f"{loop_name} failed (attempt {restart_count}): {e}")
            track_error("Watchdog", f"Loop {loop_name} restart failed: {e}")
            
            if restart_count < max_restarts:
                logger.info(f"Restarting {loop_name} in {wait_time:.2f}s")
                time.sleep(wait_time)
            else:
                logger.error(f"{loop_name} failed after {max_restarts} attempts")
                post_error(f"Loop {loop_name} failed after {max_restarts} attempts")
                return False
    
    return False

def monitor_system() -> None:
    """Main watchdog monitoring loop"""
    logger.info("Starting KRIZZY OPS Watchdog v3.0.0")
    
    while True:
        try:
            # Run data integrity check
            cleaned = run_watchdog()
            
            # Check if any critical loops need restarting
            # This would typically check process status or health endpoints
            # For now, we'll just run the watchdog scan periodically
            
            # Wait before next check (configurable interval)
            sleep_interval = int(os.getenv("WATCHDOG_INTERVAL", "3600"))  # Default 1 hour
            logger.info(f"Watchdog sleeping for {sleep_interval}s")
            time.sleep(sleep_interval)
            
        except KeyboardInterrupt:
            logger.info("Watchdog stopped by user")
            break
        except Exception as e:
            logger.error(f"Watchdog monitoring error: {e}")
            track_error("Watchdog", f"Monitoring error: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    monitor_system()
