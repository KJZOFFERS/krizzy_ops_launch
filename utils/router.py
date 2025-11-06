# utils/router.py
from typing import Dict
from .brain import SYSTEM_PROMPT
from .llm import chat_json, LLMError

def _fallback(text: str) -> Dict:
    # Deterministic rules if LLM unavailable.
    if ":" not in text:
        return {"intent":"REPORT","decision":"Malformed","signals":{"confidence":0.2,"why":["Missing prefix"]},
                "actions":[{"type":"Discord","endpoint":"none","method":"none","body":{"msg":"Malformed command"},"kpi_effect":"none"}],
                "kpis":{"roi_target_daily":0.0,"expected_conversion":0.0,"latency_slo_ms":0},
                "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}
    prefix, payload = text.split(":", 1)
    kind = prefix.strip().upper()
    body = payload.strip()
    if kind == "STRAT":
        return {"intent":"STRAT","decision":"Plan staged","signals":{"confidence":0.6,"why":["Rule-based"]},
                "actions":[{"type":"HTTP","endpoint":"/command","method":"POST","body":{"input":"REPORT: init"},"kpi_effect":"boot KPIs"}],
                "kpis":{"roi_target_daily":0.02,"expected_conversion":0.1,"latency_slo_ms":500},
                "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}
    if kind == "EXEC":
        return {"intent":"EXEC","decision":"Queued","signals":{"confidence":0.6,"why":["Rule-based"]},
                "actions":[{"type":"HTTP","endpoint":"/ingest/lead","method":"POST","body":{"key":body},"kpi_effect":"adds lead"}],
                "kpis":{"roi_target_daily":0.02,"expected_conversion":0.1,"latency_slo_ms":500},
                "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}
    if kind == "WATCH":
        return {"intent":"WATCH","decision":"Monitor","signals":{"confidence":0.6,"why":["Rule-based"]},
                "actions":[{"type":"Calc","endpoint":"none","method":"none","body":{"check":"health"},"kpi_effect":"uptime"}],
                "kpis":{"roi_target_daily":0.0,"expected_conversion":0.0,"latency_slo_ms":200},
                "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}
    if kind == "ADAPT":
        return {"intent":"ADAPT","decision":"Weights queued","signals":{"confidence":0.6,"why":["Rule-based"]},
                "actions":[{"type":"Calc","endpoint":"none","method":"none","body":{"weights":{"govcon_naics":"+15%","rei_school_score":"-10%"}},"kpi_effect":"hit rate"}],
                "kpis":{"roi_target_daily":0.03,"expected_conversion":0.2,"latency_slo_ms":0},
                "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}
    if kind == "REPORT":
        return {"intent":"REPORT","decision":"Report ready","signals":{"confidence":0.6,"why":["Rule-based"]},
                "actions":[{"type":"Discord","endpoint":"none","method":"none","body":{"msg":"Report emitted"},"kpi_effect":"visibility"}],
                "kpis":{"roi_target_daily":0.0,"expected_conversion":0.0,"latency_slo_ms":0},
                "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}
    return {"intent":"REPORT","decision":"Unknown prefix","signals":{"confidence":0.2,"why":[kind]},
            "actions":[],"kpis":{"roi_target_daily":0.0,"expected_conversion":0.0,"latency_slo_ms":0},
            "memory_updates":[],"next_check_in":"1970-01-01T00:00:00Z"}

def handle_command(text: str) -> Dict:
    try:
        return chat_json(SYSTEM_PROMPT, text)
    except LLMError:
        return _fallback(text)
