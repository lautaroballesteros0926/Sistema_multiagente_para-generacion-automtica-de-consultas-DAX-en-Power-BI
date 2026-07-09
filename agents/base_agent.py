from __future__ import annotations

import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from google import genai
from google.genai import types as genai_types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from config.logging_config import get_logger
from config.settings import settings

log = get_logger(__name__)


class BaseAgent:
    """
    Base común para GeneratorAgent y EvaluatorAgent: conexión al servidor MCP
    (como subproceso stdio) y chat contra un LLM.

    El proveedor principal es Gemini (`google-genai`). Si la llamada a Gemini
    falla por cualquier motivo (sin API key, rate limit, sin conexión...),
    `_chat` cae automáticamente a un modelo local servido por Ollama a través
    de su endpoint compatible con la API de OpenAI — el sistema nunca queda
    completamente bloqueado por falta de acceso a Gemini.
    """

    def __init__(self, model: str, temperature: float) -> None:
        self.model = model
        self.temperature = temperature

        self._gemini = genai.Client(api_key=settings.gemini_api_key) if settings.gemini_api_key else None
        self._local = AsyncOpenAI(api_key=settings.local_api_key, base_url=settings.local_base_url)

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
        try:
            await self._exit_stack.aclose()
        except BaseException as exc:
            # anyio puede lanzar un (Base)ExceptionGroup —a veces envolviendo
            # un CancelledError, que no hereda de Exception— al cerrar el
            # subproceso stdio cuando hay más de un agente MCP activo en la
            # misma corrida (known issue de anyio/mcp en Windows). No afecta
            # el resultado ya calculado: el subproceso ya terminó, esto solo
            # ensucia el cierre.
            log.debug("mcp_stdio_cleanup_warning", error=str(exc), error_type=type(exc).__name__)
        finally:
            self._session = None

    async def call_tool(self, name: str, **kwargs: Any) -> Any:
        if self._session is None:
            await self.connect_mcp()

        result = await self._session.call_tool(name, arguments=kwargs)
        if result.isError:
            text = result.content[0].text if result.content else "error desconocido"
            raise RuntimeError(f"La herramienta MCP '{name}' falló: {text}")

        return json.loads(result.content[0].text)

    async def _chat(self, messages: list[dict], **kwargs: Any) -> str:
        if self._gemini is not None:
            try:
                return await self._chat_gemini(messages, **kwargs)
            except Exception as exc:
                log.warning("gemini_chat_failed_fallback_local", error=str(exc), model=self.model)
        else:
            log.info("gemini_api_key_no_configurada_usando_local", local_model=settings.local_model)

        return await self._chat_local(messages, **kwargs)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def _chat_gemini(self, messages: list[dict], **kwargs: Any) -> str:
        system_instruction, contents = self._split_messages(messages)
        temperature = kwargs.get("temperature", self.temperature)

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        )
        if kwargs.get("response_format", {}).get("type") == "json_object":
            config.response_mime_type = "application/json"

        response = await self._gemini.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return response.text or ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
    async def _chat_local(self, messages: list[dict], **kwargs: Any) -> str:
        params = {"temperature": self.temperature, **kwargs}
        response = await self._local.chat.completions.create(
            model=settings.local_model,
            messages=messages,
            **params,
        )
        return response.choices[0].message.content or ""

    @staticmethod
    def _split_messages(messages: list[dict]) -> tuple[str | None, str]:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        other_parts = [m["content"] for m in messages if m["role"] != "system"]

        system_instruction = "\n".join(system_parts) if system_parts else None
        contents = "\n".join(other_parts)
        return system_instruction, contents
