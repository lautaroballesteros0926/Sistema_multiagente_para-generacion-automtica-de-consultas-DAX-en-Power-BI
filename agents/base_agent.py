from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings


class BaseAgent:
    """
    Base común para GeneratorAgent y EvaluatorAgent: conexión al servidor MCP
    (como subproceso stdio) y cliente de chat contra un LLM compatible con la
    API de OpenAI (OpenAI real, o cualquier servidor que exponga el mismo
    contrato, como Ollama vía `openai_base_url`).
    """

    def __init__(self, model: str, temperature: float) -> None:
        self.model = model
        self.temperature = temperature
        self._openai = AsyncOpenAI(
            api_key=settings.openai_api_key or "not-needed",
            base_url=settings.openai_base_url,
        )
        self._session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()

    async def connect_mcp(self) -> None:
        if self._session is not None:
            return

        params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"])
        read, write = await self._exit_stack.enter_async_context(stdio_client(params))
        self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

    async def close(self) -> None:
        await self._exit_stack.aclose()
        self._session = None

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        if self._session is None:
            await self.connect_mcp()

        result = await self._session.call_tool(name, arguments=kwargs)
        if result.isError:
            text = result.content[0].text if result.content else "error desconocido"
            raise RuntimeError(f"La herramienta MCP '{name}' falló: {text}")

        return json.loads(result.content[0].text)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _chat(self, messages: list[dict], **kwargs: Any) -> str:
        response = await self._openai.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""
