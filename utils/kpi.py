from utils.airtable_utils import write_record

def kpi_push(event_type: str, payload: dict):
    return write_record("KPI_Log", {"event_type": event_type, **payload})

    fields = {"Event": event}
    fields.update(data)
    write_record("KPI_Log", fields)
