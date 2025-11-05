import os, aiohttp
from utils.discord_utils import post_log, post_error

OPENAI_KEY = os.getenv("OPENAI_API_KEY")


async def llm_rewrite(path: str, err: str):
    if not OPENAI_KEY:
        return
    prompt = f"Fix async Python error in {path}. Trace:\n{err}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
                timeout=60,
            ) as r:
                if r.status != 200:
                    await post_error(f"LLM {r.status}")
                    return
                data = await r.json()
                code = data.get("choices", [{}])[0].get("message", {}).get("content")
                if not code:
                    await post_error("LLM returned empty content")
                    return
                # Write raw content as provided. Caller should ensure path points to a .py file.
                with open(path, "w", encoding="utf8") as f:
                    f.write(code)
                await post_log(f"LLM rewrote {path}")
                return True
    except Exception as e:
        await post_error(f"LLM error: {e}")
        return
