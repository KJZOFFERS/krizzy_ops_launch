import os, aiohttp, json
from utils.discord_utils import post_log, post_error
OPENAI_KEY=os.getenv("OPENAI_API_KEY")

async def llm_rewrite(path,err):
    if not OPENAI_KEY: 
        await post_error("No OpenAI API key configured for LLM rewrite")
        return False
    prompt=f"Fix async Python error in {path}. Trace:\n{err}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"},
                json={"model":"gpt-4","messages":[{"role":"user","content":prompt}],"temperature":0}) as r:
                if r.status!=200: 
                    await post_error(f"LLM API error {r.status}")
                    return False
                d=await r.json()
                if not d.get("choices") or not d["choices"][0].get("message", {}).get("content"):
                    await post_error("Invalid LLM response format")
                    return False
                code=d["choices"][0]["message"]["content"]
                with open(path,"w",encoding="utf8") as f:
                    f.write(code)
                await post_log(f"LLM rewrote {path}")
                return True
    except Exception as e:
        await post_error(f"LLM rewrite failed: {e}")
        return False