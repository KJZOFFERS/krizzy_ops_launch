# utils/__init__.py
__all__ = ["list_records", "create_record"]

def __getattr__(name: str):
    if name in ("list_records", "create_record"):
        from .airtable_utils import list_records, create_record
        return {"list_records": list_records, "create_record": create_record}[name]
    raise AttributeError(name)
