"""AI client abstraction supporting multiple providers."""

import os
from abc import ABC, abstractmethod
from typing import Optional

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from google import genai
from google.genai import types

from ..models import AIConfig, AIProvider
from .tokens import record_usage


class AIClient(ABC):
    """Abstract base class for AI clients."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        pass


class AnthropicClient(AIClient):
    """Client for Anthropic Claude models."""

    def __init__(self, config: AIConfig):
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {config.api_key_env}")

        kwargs = {"api_key": api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url

        self.client = AsyncAnthropic(**kwargs)
        self.model = config.model
        self.max_tokens = config.max_tokens

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        usage = getattr(message, "usage", None)
        if usage is not None:
            record_usage(
                "anthropic",
                input_tokens=getattr(usage, "input_tokens", 0),
                output_tokens=getattr(usage, "output_tokens", 0),
            )
        return message.content[0].text


class OpenAIClient(AIClient):
    """Client for OpenAI models."""

    def __init__(self, config: AIConfig):
        api_key = (
            os.getenv(config.api_key_env)
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            raise ValueError(f"Missing API key: {config.api_key_env}")

        kwargs = {"api_key": api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url

        self.client = AsyncOpenAI(**kwargs)
        self.model = config.model
        self.max_tokens = config.max_tokens

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_usage(
                "openai",
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
            )
        return response.choices[0].message.content


class MiniMaxClient(AIClient):
    """Client for MiniMax models via OpenAI-compatible API."""

    def __init__(self, config: AIConfig):
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {config.api_key_env}")

        kwargs = {
            "api_key": api_key,
            "base_url": config.base_url or "https://api.minimax.io/v1",
        }

        self.client = AsyncOpenAI(**kwargs)
        self.model = config.model
        self.max_tokens = config.max_tokens

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        if temperature <= 0:
            temperature = 0.01

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_usage(
                "minimax",
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
            )
        return response.choices[0].message.content


class AliClient(AIClient):
    """Client for Alibaba DashScope (OpenAI-compatible API)."""

    def __init__(self, config: AIConfig):
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {config.api_key_env}")

        kwargs = {
            "api_key": api_key,
            "base_url": config.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        self.client = AsyncOpenAI(**kwargs)
        self.model = config.model
        self.max_tokens = config.max_tokens

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content


class GeminiClient(AIClient):
    """Client for Google Gemini models."""

    def __init__(self, config: AIConfig):
        api_key = os.getenv(config.api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key: {config.api_key_env}")

        self.client = genai.Client(api_key=api_key)
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

    async def complete(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=temperature,
                max_output_tokens=max_tokens,
                response_mime_type="application/json"
            )
        )
        usage = getattr(response, "usage_metadata", None)
        if usage is not None:
            total = getattr(usage, "total_token_count", 0) or 0
            prompt = getattr(usage, "prompt_token_count", 0) or 0
            completion = max(0, total - prompt)
            record_usage("gemini", input_tokens=prompt, output_tokens=completion)
        return response.text


def create_ai_client(config: AIConfig) -> AIClient:
    if config.provider == AIProvider.ANTHROPIC:
        return AnthropicClient(config)
    elif config.provider == AIProvider.OPENAI:
        return OpenAIClient(config)
    elif config.provider == AIProvider.ALI:
        return AliClient(config)
    elif config.provider == AIProvider.GEMINI:
        return GeminiClient(config)
    elif config.provider == AIProvider.DOUBAO:
        return OpenAIClient(config)
    elif config.provider == AIProvider.MINIMAX:
        return MiniMaxClient(config)
    else:
        raise ValueError(f"Unsupported AI provider: {config.provider}")
