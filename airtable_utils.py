"""
Airtable utilities with safe write operations, deduplication, and error handling.
"""
import os
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple
from pyairtable import Table
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
from kpi import kpi_push


class AirtableManager:
    """Safe Airtable operations with retry logic and deduplication."""
    
    def __init__(self):
        self.api_key = os.getenv("AIRTABLE_API_KEY")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        if not self.api_key or not self.base_id:
            raise ValueError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set")
    
    def _get_table(self, table_name: str) -> Table:
        """Get Airtable table instance."""
        return Table(self.api_key, self.base_id, table_name)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.RequestException, Exception))
    )
    def _safe_airtable_operation(self, operation, *args, **kwargs):
        """Execute Airtable operation with retry logic."""
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                kpi_push("error", {
                    "error_type": "rate_limit",
                    "message": f"Airtable rate limit exceeded: {e}",
                    "table": kwargs.get("table_name", "unknown")
                })
            elif "403" in str(e) or "unauthorized" in str(e).lower():
                kpi_push("error", {
                    "error_type": "auth_error",
                    "message": f"Airtable authentication failed: {e}",
                    "table": kwargs.get("table_name", "unknown")
                })
            else:
                kpi_push("error", {
                    "error_type": "airtable_error",
                    "message": f"Airtable operation failed: {e}",
                    "table": kwargs.get("table_name", "unknown")
                })
            raise
    
    def _generate_dedup_key(self, record: Dict[str, Any], key_fields: List[str]) -> str:
        """Generate deduplication key from specified fields."""
        key_values = []
        for field in key_fields:
            value = record.get(field, "")
            if isinstance(value, (dict, list)):
                value = json.dumps(value, sort_keys=True)
            key_values.append(str(value).lower().strip())
        return hashlib.md5("|".join(key_values).encode()).hexdigest()
    
    def safe_airtable_write(self, table_name: str, record: Dict[str, Any], 
                          key_fields: List[str] = None) -> Tuple[bool, str]:
        """
        Safely write record to Airtable with deduplication.
        
        Args:
            table_name: Name of the Airtable table
            record: Record data to write
            key_fields: Fields to use for deduplication (default: ['source_id'])
        
        Returns:
            Tuple of (success: bool, record_id: str)
        """
        if key_fields is None:
            key_fields = ['source_id']
        
        try:
            table = self._get_table(table_name)
            
            # Generate deduplication key
            dedup_key = self._generate_dedup_key(record, key_fields)
            record['dedup_key'] = dedup_key
            
            # Check for existing records with same dedup key
            existing_records = self._safe_airtable_operation(
                table.all,
                formula=f"{{dedup_key}} = '{dedup_key}'"
            )
            
            if existing_records:
                # Update existing record
                existing_id = existing_records[0]['id']
                updated_record = self._safe_airtable_operation(
                    table.update,
                    existing_id,
                    record
                )
                return True, existing_id
            else:
                # Create new record
                new_record = self._safe_airtable_operation(
                    table.create,
                    record
                )
                return True, new_record['id']
                
        except Exception as e:
            kpi_push("error", {
                "error_type": "airtable_write_error",
                "message": f"Failed to write to {table_name}: {e}",
                "record": str(record)[:200]
            })
            return False, str(e)
    
    def fetch_all(self, table_name: str, max_records: int = None) -> List[Dict[str, Any]]:
        """Fetch all records from table with error handling."""
        try:
            table = self._get_table(table_name)
            records = self._safe_airtable_operation(
                table.all,
                max_records=max_records
            )
            return records
        except Exception as e:
            kpi_push("error", {
                "error_type": "airtable_fetch_error",
                "message": f"Failed to fetch from {table_name}: {e}"
            })
            return []
    
    def batch_create(self, table_name: str, records: List[Dict[str, Any]], 
                    batch_size: int = 10) -> List[Tuple[bool, str]]:
        """Create multiple records in batches with error handling."""
        results = []
        table = self._get_table(table_name)
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            try:
                created_records = self._safe_airtable_operation(
                    table.batch_create,
                    batch
                )
                for record in created_records:
                    results.append((True, record['id']))
            except Exception as e:
                kpi_push("error", {
                    "error_type": "airtable_batch_error",
                    "message": f"Batch create failed for {table_name}: {e}",
                    "batch_size": len(batch)
                })
                for _ in batch:
                    results.append((False, str(e)))
        
        return results


# Global Airtable manager instance (lazy initialization)
_airtable_instance = None

def get_airtable_manager():
    """Get or create Airtable manager instance."""
    global _airtable_instance
    if _airtable_instance is None:
        _airtable_instance = AirtableManager()
    return _airtable_instance

# For backward compatibility - create a property-like object
class AirtableManagerProxy:
    def __getattr__(self, name):
        return getattr(get_airtable_manager(), name)

airtable = AirtableManagerProxy()


# Convenience functions for backward compatibility
def safe_airtable_write(table_name: str, record: Dict[str, Any], 
                       key_fields: List[str] = None) -> Tuple[bool, str]:
    """Convenience function for safe Airtable write."""
    return get_airtable_manager().safe_airtable_write(table_name, record, key_fields)


def add_record(table_name: str, record: Dict[str, Any]) -> bool:
    """Legacy function - use safe_airtable_write for new code."""
    success, _ = get_airtable_manager().safe_airtable_write(table_name, record)
    return success


def fetch_all(table_name: str, max_records: int = None) -> List[Dict[str, Any]]:
    """Convenience function for fetching all records."""
    return get_airtable_manager().fetch_all(table_name, max_records)


def push_record(table_name: str, data: Dict[str, Any]) -> bool:
    """Legacy function - use safe_airtable_write for new code."""
    return add_record(table_name, data)


def log_kpi(event: str, data: Dict[str, Any]) -> None:
    """Legacy function - use kpi.kpi_push for new code."""
    kpi_push(event, data)
