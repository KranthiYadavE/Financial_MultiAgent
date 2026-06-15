"""Free local LLM via Ollama — no paid API keys required."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from shared.config import Settings


class OllamaClient:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model = self.settings.ollama_model

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
    async def generate(self, prompt: str, system: str = "") -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 512},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
