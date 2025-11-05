__all__ = ["list_records", "create_record", "update_record", "upsert_record"]

def __getattr__(name: str):
    if name in __all__:
        from .airtable_utils import list_records, create_record, update_record, upsert_record
        return {
            "list_records": list_records,
            "create_record": create_record,
            "update_record": update_record,
            "upsert_record": upsert_record,
        }[name]
    raise AttributeError(name)
