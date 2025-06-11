import asyncio
import json
import os

import aiohttp


async def invoke_chute():
    api_token = os.getenv("CHUTES_KEY")

    headers = {
        "Authorization": "Bearer " + api_token,
        "Content-Type": "application/json",
    }

    body = {
        "model": "Qwen/Qwen3-32B",
        "messages": [{"role": "user", "content": "Tell me a 100 word story."}],
        "stream": True,
        "max_tokens": 1024,
        "temperature": 0.7,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://llm.chutes.ai/v1/chat/completions", headers=headers, json=body
        ) as response:
            async for line in response.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = data.strip()
                        if chunk:
                            print(
                                json.loads(chunk)["choices"][0]["delta"]["content"],
                                sep="",
                                end="",
                                flush=True,
                            )
                    except Exception as e:
                        print(f"Error parsing chunk: {e}")


asyncio.run(invoke_chute())
