def compute_kpi(data):
    result = sum(data) / len(data) if data else 0
    return result
