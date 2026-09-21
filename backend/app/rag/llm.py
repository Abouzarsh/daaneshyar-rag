from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any, Protocol

import httpx


class LLMProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        history: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]: ...

    async def health(self) -> dict[str, str | bool]: ...


class OllamaLLM:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        temperature: float,
        context_window: int,
        timeout_seconds: float,
        keep_alive: str,
    ):
        self.base_url = base_url.rstrip("/")
        self._model_name = model
        self.temperature = temperature
        self.context_window = context_window
        self.timeout = httpx.Timeout(timeout_seconds, connect=10)
        self.keep_alive = keep_alive

    @property
    def model_name(self) -> str:
        return self._model_name

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        history: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            *[
                {"role": item["role"], "content": item["content"]}
                for item in history
                if item.get("role") in {"user", "assistant"}
            ],
            {"role": "user", "content": user_prompt},
        ]
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "think": False,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.context_window,
            },
        }
        async with (
            httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client,
            client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                item = json.loads(line)
                content = (item.get("message") or {}).get("content", "")
                if content:
                    yield content
                if item.get("done"):
                    break

    async def health(self) -> dict[str, str | bool]:
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                models = {
                    item.get("name", "").split(":")[0]
                    for item in response.json().get("models", [])
                }
            wanted = self.model_name.split(":")[0]
            return {
                "ok": wanted in models,
                "provider": "ollama",
                "model": self.model_name,
                "detail": "ready" if wanted in models else "model_not_pulled",
            }
        except Exception as exc:
            return {
                "ok": False,
                "provider": "ollama",
                "model": self.model_name,
                "detail": type(exc).__name__,
            }


class OpenAICompatibleLLM:
    """Minimal streaming adapter for OpenAI-compatible chat endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        timeout_seconds: float,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._model_name = model
        self.temperature = temperature
        self.timeout = httpx.Timeout(timeout_seconds, connect=10)

    @property
    def model_name(self) -> str:
        return self._model_name

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        history: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        messages = [
            {"role": "system", "content": system_prompt},
            *[
                {"role": item["role"], "content": item["content"]}
                for item in history
                if item.get("role") in {"user", "assistant"}
            ],
            {"role": "user", "content": user_prompt},
        ]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }
        async with (
            httpx.AsyncClient(timeout=self.timeout) as client,
            client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                item = json.loads(data)
                delta = item.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta

    async def health(self) -> dict[str, str | bool]:
        if not self.api_key:
            return {
                "ok": False,
                "provider": "openai-compatible",
                "model": self.model_name,
                "detail": "api_key_missing",
            }
        return {
            "ok": True,
            "provider": "openai-compatible",
            "model": self.model_name,
            "detail": "configured",
        }


class ExtractiveDemoLLM:
    """Predictable local provider for tests and screenshots."""

    @property
    def model_name(self) -> str:
        return "extractive-demo"

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        history: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        del system_prompt, history
        marker = '<source index="1">'
        excerpt = ""
        if marker in user_prompt:
            excerpt = user_prompt.split(marker, 1)[1].split("</source>", 1)[0]
            excerpt = excerpt.split("\n", 1)[-1].strip()
        if excerpt:
            answer = "بر اساس سند بازیابی‌شده، " + excerpt[:260].rstrip() + " [1]"
        else:
            answer = "برای این پرسش، اطلاعات کافی در اسناد پیدا نشد."
        for start in range(0, len(answer), 28):
            yield answer[start : start + 28]

    async def health(self) -> dict[str, str | bool]:
        return {
            "ok": True,
            "provider": "demo",
            "model": self.model_name,
            "detail": "ready",
        }


def build_llm_provider(
    *,
    provider: str,
    ollama_base_url: str,
    ollama_model: str,
    ollama_keep_alive: str,
    openai_base_url: str,
    openai_api_key: str | None,
    openai_model: str,
    temperature: float,
    context_window: int,
    timeout_seconds: float,
) -> LLMProvider:
    if provider == "demo":
        return ExtractiveDemoLLM()
    if provider == "ollama":
        return OllamaLLM(
            base_url=ollama_base_url,
            model=ollama_model,
            temperature=temperature,
            context_window=context_window,
            timeout_seconds=timeout_seconds,
            keep_alive=ollama_keep_alive,
        )
    if provider in {"openai", "openai-compatible"}:
        if not openai_api_key:
            raise ValueError("RAG_OPENAI_API_KEY is required for the OpenAI provider")
        return OpenAICompatibleLLM(
            base_url=openai_base_url,
            api_key=openai_api_key,
            model=openai_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")
