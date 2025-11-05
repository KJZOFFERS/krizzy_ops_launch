# utils/__init__.py
# Avoid boot-time import failures by not importing heavy submodules eagerly.

__all__ = ["list_records"]

def __getattr__(name: str):
    if name == "list_records":
        from .airtable_utils import list_records
        return list_records
    raise AttributeError(name)

