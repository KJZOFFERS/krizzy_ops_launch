import json, os, urllib.request

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TIMEOUT = float(os.getenv("OPENAI_TIMEOUT_S", "20"))

class LLMError(Exception): pass

def _chat(system_prompt: str, user_text: str) -> dict:
    if not OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text + "\nReturn a single JSON object only."}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }
    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {OPENAI_API_KEY}")
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode("utf-8")
    with urllib.request.urlopen(req, data, timeout=TIMEOUT) as resp:
        raw = resp.read().decode("utf-8")
    obj = json.loads(raw)
    return json.loads(obj["choices"][0]["message"]["content"])

def chat_json(system_prompt: str, user_text: str) -> dict:
    return _chat(system_prompt, user_text)

