# utils/llm.py
# Minimal OpenAI Chat JSON caller without third-party deps.

import json
import os
import time
import urllib.request

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # set explicitly if needed
TIMEOUT = float(os.getenv("OPENAI_TIMEOUT_S", "20"))

JSON_INSTRUCTIONS = """
You MUST return a single JSON object matching the Output Schema. Do not include backticks. Do not include any text outside the JSON.
If you cannot fully comply, still return the best-effort JSON and set "intent" and "decision" accordingly.
"""

class LLMError(Exception):
    pass

def _chat(system_prompt: str, user_text: str) -> str:
    if not OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text + "\n\n" + JSON_INSTRUCTIONS},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {OPENAI_API_KEY}")
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode("utf-8")
    with urllib.request.urlopen(req, data, timeout=TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
    return raw

def chat_json(system_prompt: str, user_text: str) -> dict:
    raw = _chat(system_prompt, user_text)
    try:
        obj = json.loads(raw)
        # OpenAI format: { choices: [ { message: { content: "<json>" } } ] }
        if "choices" in obj:
            content = obj["choices"][0]["message"]["content"]
            return json.loads(content)
        # Direct JSON
        return obj
    except Exception as e:
        raise LLMError(f"Failed to parse LLM JSON: {e}") from e
