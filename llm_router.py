import os, openai, requests

def call_openai(prompt):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    try:
        resp = openai.ChatCompletion.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=float(os.getenv("LLM_TEMPERATURE", 0.7)),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", 400))
        )
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        print("OpenAI fail:", e)
        return None

def call_anthropic(prompt):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}]
        }
        r = requests.post(url, headers=headers, json=data, timeout=20)
        return r.json().get("content", [{}])[0].get("text")
    except Exception as e:
        print("Claude fail:", e)
        return None

def call_gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(url, json=data, timeout=20)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print("Gemini fail:", e)
        return None

def enrich_text(prompt):
    """Tries all LLMs sequentially until one returns."""
    for fn in [call_openai, call_anthropic, call_gemini]:
        try:
            result = fn(prompt)
            if result:
                return result
        except Exception as e:
            print("LLM fallback:", e)
            continue
    return "LLM enrichment unavailable"
