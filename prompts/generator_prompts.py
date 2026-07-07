from __future__ import annotations

from models import SchemaContext

GENERATOR_SYSTEM = """Eres un experto en DAX para Power BI.

Reglas estrictas:
- Usa ÚNICAMENTE las tablas, columnas y medidas que aparecen en el esquema proporcionado. Nunca inventes nombres.
- La consulta debe empezar siempre con EVALUATE.
- Prioriza reutilizar medidas existentes del modelo en vez de recalcular la misma lógica con SUM/CALCULATE manuales.
- Devuelve ÚNICAMENTE el bloque de código DAX, sin explicaciones ni texto adicional.
- Si se te da una sección de "CORRECCIONES REQUERIDAS", corrige exactamente esos problemas en tu nueva respuesta.
"""


def build_generator_prompt(
    question: str,
    schema: SchemaContext,
    feedback: str | None = None,
) -> list[dict]:
    user_parts = [schema.to_prompt_text(), "", f"PREGUNTA: {question}"]

    if feedback:
        user_parts += ["", "CORRECCIONES REQUERIDAS:", feedback]

    return [
        {"role": "system", "content": GENERATOR_SYSTEM},
        {"role": "user", "content": "\n".join(user_parts)},
    ]
