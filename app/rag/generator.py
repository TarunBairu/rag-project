import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Optional

from app.config.settings import get_settings

logger = logging.getLogger("rag.generator")
settings = get_settings()


class BaseGenerator(ABC):
    """Abstract interface for LLM answer generation."""

    @abstractmethod
    async def generate(self, prompt_data: Dict[str, str]) -> str:
        """Generate full completion for the given prompt payload."""
        pass

    @abstractmethod
    async def generate_stream(self, prompt_data: Dict[str, str]) -> AsyncGenerator[str, None]:
        """Stream generated completion tokens."""
        pass


class MockGenerator(BaseGenerator):
    """Local offline answer generator that synthesizes response using context snippets."""

    async def generate(self, prompt_data: Dict[str, str]) -> str:
        user_prompt = prompt_data.get("user_prompt", "")
        # Check if context exists
        if "No relevant context found." in user_prompt:
            return (
                "Based on the provided documents, I do not have enough information to answer this question. "
                "Please upload relevant files to populate the knowledge base."
            )

        # Synthesize from context lines
        lines = user_prompt.split("\n")
        context_snippets = []
        is_context = False
        for line in lines:
            if "Context Information:" in line:
                is_context = True
                continue
            if "User Question:" in line:
                is_context = False
                break
            if is_context and line.strip() and not line.startswith("---"):
                context_snippets.append(line.strip())

        extracted_highlights = [s for s in context_snippets if not s.startswith("[Source")]
        summary = " ".join(extracted_highlights[:3]) if extracted_highlights else "Information extracted from documents."

        return (
            f"Based on the retrieved documents, here is the answer to your question:\n\n"
            f"{summary}\n\n"
            f"Sources referenced: [Source 1]"
        )

    async def generate_stream(self, prompt_data: Dict[str, str]) -> AsyncGenerator[str, None]:
        full_text = await self.generate(prompt_data)
        words = full_text.split(" ")
        for word in words:
            yield word + " "
            await asyncio.sleep(0.02)


class OpenAIGenerator(BaseGenerator):
    """OpenAI Chat Completion API Generator."""

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        if not self.api_key:
            raise ValueError("OpenAI API Key is required for OpenAIGenerator.")

    async def generate(self, prompt_data: Dict[str, str]) -> str:
        import httpx
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt_data["system_prompt"]},
                {"role": "user", "content": prompt_data["user_prompt"]},
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(self, prompt_data: Dict[str, str]) -> AsyncGenerator[str, None]:
        import httpx
        import json
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt_data["system_prompt"]},
                {"role": "user", "content": prompt_data["user_prompt"]},
            ],
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        raw_json = line[6:]
                        try:
                            chunk = json.loads(raw_json)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue


class GeminiGenerator(BaseGenerator):
    """Google Gemini REST API Generator."""

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        if not self.api_key:
            raise ValueError("Gemini API Key is required for GeminiGenerator.")

    async def generate(self, prompt_data: Dict[str, str]) -> str:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        combined_prompt = f"{prompt_data['system_prompt']}\n\n{prompt_data['user_prompt']}"
        payload = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "temperature": settings.LLM_TEMPERATURE,
                "maxOutputTokens": settings.LLM_MAX_TOKENS,
            },
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def generate_stream(self, prompt_data: Dict[str, str]) -> AsyncGenerator[str, None]:
        # For simplicity and robustness, generate and stream tokenized chunks
        full_text = await self.generate(prompt_data)
        words = full_text.split(" ")
        for word in words:
            yield word + " "
            await asyncio.sleep(0.02)


class GroqGenerator(BaseGenerator):
    """Groq API Generator for ultra-fast Llama 3 inference."""

    def __init__(self, api_key: str = "", model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or "llama-3.3-70b-versatile"
        if not self.api_key:
            raise ValueError("Groq API Key is required for GroqGenerator.")

    async def _resolve_best_model(self, client) -> str:
        """Query Groq API to discover active chat models available on this key."""
        try:
            models_list = await client.models.list()
            active_ids = [m.id for m in models_list.data]
            logger.info(f"Active Groq models for this account: {active_ids}")

            # Filter out audio, prompt guard, and terms-restricted models
            usable_models = [
                m for m in active_ids
                if "whisper" not in m and "guard" not in m and "orpheus" not in m
            ]

            # Priority preference list
            preferred = [
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "qwen/qwen3.8-27b",
                "allam-2-7b",
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
            ]
            for pref in preferred:
                if pref in usable_models:
                    return pref

            if usable_models:
                return usable_models[0]
            if active_ids:
                return active_ids[0]
        except Exception as exc:
            logger.warning(f"Could not query Groq models list ({exc}).")
        return "openai/gpt-oss-120b"

    async def generate(self, prompt_data: Dict[str, str]) -> str:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self.api_key)
            chosen_model = await self._resolve_best_model(client)
            self.model = chosen_model

            logger.info(f"Generating answer using Groq model: {chosen_model}")
            try:
                completion = await client.chat.completions.create(
                    model=chosen_model,
                    messages=[
                        {"role": "system", "content": prompt_data["system_prompt"]},
                        {"role": "user", "content": prompt_data["user_prompt"]},
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                return completion.choices[0].message.content or ""
            except Exception as call_exc:
                logger.warning(f"Failed with {chosen_model}: {call_exc}. Trying backup 'openai/gpt-oss-20b'...")
                completion = await client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[
                        {"role": "system", "content": prompt_data["system_prompt"]},
                        {"role": "user", "content": prompt_data["user_prompt"]},
                    ],
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                self.model = "openai/gpt-oss-20b"
                return completion.choices[0].message.content or ""
        except Exception as exc:
            logger.warning(f"Groq API call failed ({exc}). Falling back to MockGenerator.")
            return await MockGenerator().generate(prompt_data)

    async def generate_stream(self, prompt_data: Dict[str, str]) -> AsyncGenerator[str, None]:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self.api_key)
            chosen_model = await self._resolve_best_model(client)
            self.model = chosen_model

            stream = await client.chat.completions.create(
                model=chosen_model,
                messages=[
                    {"role": "system", "content": prompt_data["system_prompt"]},
                    {"role": "user", "content": prompt_data["user_prompt"]},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                stream=True,
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content
        except Exception as exc:
            logger.warning(f"Groq streaming failed ({exc}). Falling back to MockGenerator.")
            async for token in MockGenerator().generate_stream(prompt_data):
                yield token


def get_generator() -> BaseGenerator:
    """Factory to retrieve configured generator with graceful fallback."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq" and settings.GROQ_API_KEY:
        try:
            return GroqGenerator(api_key=settings.GROQ_API_KEY, model=settings.LLM_MODEL)
        except Exception as exc:
            logger.warning(f"Failed to initialize GroqGenerator ({exc}). Falling back to MockGenerator.")

    elif provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            return GeminiGenerator(api_key=settings.GEMINI_API_KEY, model=settings.LLM_MODEL)
        except Exception as exc:
            logger.warning(f"Failed to initialize GeminiGenerator ({exc}). Falling back to MockGenerator.")

    elif provider == "openai" and settings.OPENAI_API_KEY:
        try:
            return OpenAIGenerator(api_key=settings.OPENAI_API_KEY, model=settings.LLM_MODEL)
        except Exception as exc:
            logger.warning(f"Failed to initialize OpenAIGenerator ({exc}). Falling back to MockGenerator.")

    return MockGenerator()

