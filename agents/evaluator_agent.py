from __future__ import annotations

import json

from agents.base_agent import BaseAgent
from config.logging_config import get_logger
from models import DAXQuery, Decision, EvaluationResult, SchemaContext
from prompts.evaluator_prompts import build_evaluator_prompt

log = get_logger(__name__)


class EvaluatorAgent(BaseAgent):
    async def run(self, question: str, dax_query: DAXQuery) -> EvaluationResult:
        schema_dict = await self.call_tool("get_schema")
        schema = SchemaContext.model_validate(schema_dict)

        syntax_result = await self.call_tool("validate_syntax", dax_query=dax_query.query_text)

        messages = build_evaluator_prompt(question, dax_query, schema, syntax_result)
        raw_response = await self._chat(
            messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        try:
            payload = json.loads(raw_response)
            return EvaluationResult.model_validate(payload)
        except Exception as exc:
            log.warning("evaluator_json_parse_failed", error=str(exc), raw_response=raw_response[:500])
            return EvaluationResult(
                score=0.0,
                decision=Decision.REJECT,
                explanation="No se pudo interpretar la respuesta del evaluador como JSON válido.",
                syntax_valid=bool(syntax_result.get("valid", False)),
            )
