"""LLM provider abstraction.

Default: Ollama (qwen2.5:3b) — fully local, free, no key, offline. This runs
reliably on your machine with zero per-call cost.
Optional: Hermes local API (tencent/hy3:free) when HERMES_API_KEY is set in the
env — also free, but requires the gateway key (never hardcoded).

The interface is small so a hosted provider can drop in later.
"""

import json
import os
import httpx
from pydantic import BaseModel
from typing import Optional


class LLMConfig(BaseModel):
    provider: str = "ollama"  # ollama | hermes
    base_url: str = "http://127.0.0.1:8642/v1"
    model: str = "tencent/hy3:free"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    timeout: int = 90


def _extract_json(text: str):
    """Pull a JSON object or array out of an LLM response (handles ```fences```, prose)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
    t = t.strip()
    # array
    a_start, a_end = t.find("["), t.rfind("]")
    # object
    o_start, o_end = t.find("{"), t.rfind("}")
    # pick whichever span is larger / valid
    if a_start != -1 and a_end > a_start and (o_start == -1 or (a_end - a_start) >= (o_end - o_start)):
        return json.loads(t[a_start : a_end + 1])
    if o_start != -1 and o_end > o_start:
        return json.loads(t[o_start : o_end + 1])
    raise ValueError("no json found in LLM response")


class LLMProvider:
    def __init__(self, config: LLMConfig | None = None):
        self.cfg = config or LLMConfig()

    async def complete(self, system: str, user: str) -> str:
        if self.cfg.provider == "hermes":
            return await self._hermes(system, user)
        return await self._ollama(system, user)

    async def _hermes(self, system: str, user: str) -> str:
        key = os.environ.get("HERMES_API_KEY")
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        payload = {
            "model": self.cfg.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=self.cfg.timeout) as c:
            r = await c.post(f"{self.cfg.base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def _ollama(self, system: str, user: str) -> str:
        payload = {
            "model": self.cfg.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.cfg.timeout) as c:
            r = await c.post(f"{self.cfg.ollama_base_url}/api/chat", json=payload)
            r.raise_for_status()
            return r.json()["message"]["content"]


async def complete_json(system: str, user: str, config: LLMConfig | None = None) -> dict:
    """Call the LLM and parse structured JSON out of the reply."""
    provider = LLMProvider(config)
    raw = await provider.complete(system, user)
    return _extract_json(raw)
