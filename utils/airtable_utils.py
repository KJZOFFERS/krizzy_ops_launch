from pyairtable import Table
import os

def write_record(table_name, data):
    base_id = os.getenv("AIRTABLE_BASE_ID")
    api_key = os.getenv("AIRTABLE_API_KEY")
    table = Table(api_key, base_id, table_name)
    table.create(data)
    return True
