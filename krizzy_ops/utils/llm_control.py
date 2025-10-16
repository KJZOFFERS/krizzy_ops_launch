import os, aiohttp
from krizzy_ops.utils.discord_utils import post_log, post_error
OPENAI_KEY=os.getenv("OPENAI_API_KEY")

async def llm_rewrite(path,err):
    if not OPENAI_KEY:
        return
    prompt=f"Fix async Python error in {path}. Trace:\n{err}"
    payload={
        "model":"gpt-5",
        "messages":[{"role":"user","content":prompt}],
        "temperature":0
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.openai.com/v1/chat/completions",
                headers={"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"},
                json=payload
            ) as r:
                if r.status!=200:
                    await post_error(f"LLM {r.status}")
                    return
                d=await r.json()
                code=d["choices"][0]["message"]["content"]
                with open(path,"w",encoding="utf8") as f:
                    f.write(code)
                await post_log(f"LLM rewrote {path}")
                return True
    except Exception as e:
        await post_error(f"LLM error: {e}")
        return
