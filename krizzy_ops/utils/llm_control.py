import os, aiohttp, json
from utils.discord_utils import post_log, post_error
OPENAI_KEY=os.getenv("OPENAI_API_KEY")

async def llm_rewrite(path,err):
    if not OPENAI_KEY: return
    prompt=f"Fix async Python error in {path}. Trace:\n{err}"
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"},
            json={"model":"gpt-4o","messages":[{"role":"user","content":prompt}],"temperature":0}) as r:
            if r.status!=200: await post_error(f"LLM {r.status}"); return
            d=await r.json(); code=d["choices"][0]["message"]["content"]
            open(path,"w",encoding="utf8").write(code)
            await post_log(f"LLM rewrote {path}")
            return True
