from pyairtable import Table
import os

def write_record(table_name, data):
    t = Table(os.getenv("AIRTABLE_API_KEY"), os.getenv("AIRTABLE_BASE_ID"), table_name)
    t.create(data)
