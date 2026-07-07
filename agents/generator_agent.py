from __future__ import annotations

import re

from agents.base_agent import BaseAgent
from models import DAXQuery, SchemaContext
from prompts.generator_prompts import build_generator_prompt

_DAX_FENCE = re.compile(r"```(?:dax)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class GeneratorAgent(BaseAgent):
    async def run(self, question: str, feedback: str | None = None) -> DAXQuery:
        schema = await self._gather_context()
        messages = build_generator_prompt(question, schema, feedback)
        raw_response = await self._chat(messages)
        query_text = self._extract_dax(raw_response)

        return DAXQuery(
            query_text=query_text,
            natural_language=question,
            iteration=0 if feedback is None else 1,
        )

    async def _gather_context(self) -> SchemaContext:
        tables = await self.call_tool("get_tables")
        relationships = await self.call_tool("get_relationships")
        measures = await self.call_tool("get_measures")

        return SchemaContext.model_validate(
            {"tables": tables, "relationships": relationships, "measures": measures}
        )

    @staticmethod
    def _extract_dax(raw_response: str) -> str:
        match = _DAX_FENCE.search(raw_response)
        if match:
            return match.group(1).strip()
        return raw_response.strip()
