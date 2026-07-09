from __future__ import annotations

import json

from config.settings import settings
from models import DAXQuery, SchemaContext

EVALUATOR_SYSTEM = f"""Eres un juez experto en DAX para Power BI (patrón LLM-as-a-Judge).

Evalúas una consulta DAX generada por otro modelo, en base a estos criterios:
- Coherencia semántica: ¿la consulta responde realmente lo que se preguntó?
- Conformidad de esquema: ¿usa únicamente tablas, columnas y medidas que existen en el esquema dado?
- Corrección sintáctica: ¿el resultado de la validación de sintaxis fue válido?
- Eficiencia: ¿evita recálculos innecesarios cuando ya existe una medida que resuelve lo mismo?
- Completitud: ¿cubre todos los elementos de la pregunta (filtros, agrupaciones, medidas)?

Reglas de decisión según el puntaje global (score, de 0.0 a 1.0):
- score >= {settings.accept_threshold} -> decision = "ACCEPT"
- {settings.reject_threshold} <= score < {settings.accept_threshold} -> decision = "REGENERATE", con feedback_for_generator concreto y accionable
- score < {settings.reject_threshold} -> decision = "REJECT"

Si la sintaxis no es válida (syntax_valid=false), el score no puede ser ACCEPT.

Devuelve ÚNICAMENTE un objeto JSON, sin texto adicional ni bloques de código, con exactamente estas claves:
score, decision, explanation, semantic_coherence, schema_compliance, syntax_valid, feedback_for_generator
"""


def build_evaluator_prompt(
    question: str,
    dax_query: DAXQuery,
    schema: SchemaContext,
    syntax_result: dict,
) -> list[dict]:
    user_parts = [
        schema.to_prompt_text(),
        "",
        f"PREGUNTA: {question}",
        "",
        "CONSULTA DAX GENERADA:",
        dax_query.query_text,
        "",
        "RESULTADO DE VALIDACIÓN DE SINTAXIS:",
        json.dumps(syntax_result, ensure_ascii=False),
    ]

    return [
        {"role": "system", "content": EVALUATOR_SYSTEM},
        {"role": "user", "content": "\n".join(user_parts)},
    ]
