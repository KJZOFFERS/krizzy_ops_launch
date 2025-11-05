# FILE: utils/__init__.py
# Import-safe lazy exports
__all__ = [
    "list_records", "create_record", "update_record", "upsert_record",
    "safe_airtable_write", "safe_upsert",
    "fetch_table", "resolve_table",
]

def __getattr__(name: str):
    if name in __all__:
        from .airtable_utils import (
            list_records, create_record, update_record, upsert_record,
            safe_airtable_write, safe_upsert,
            fetch_table, resolve_table,
        )
        return {
            "list_records": list_records,
            "create_record": create_record,
            "update_record": update_record,
            "upsert_record": upsert_record,
            "safe_airtable_write": safe_airtable_write,
            "safe_upsert": safe_upsert,
            "fetch_table": fetch_table,
            "resolve_table": resolve_table,
        }[name]
    raise AttributeError(name)
