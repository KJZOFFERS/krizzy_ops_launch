from utils.airtable_utils import write_record

def kpi_push(event, data):
    fields = {"Event": event}
    fields.update(data)
    write_record("KPI_Log", fields)
