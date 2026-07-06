from __future__ import annotations

from pydantic import BaseModel, Field


class DAXQuery(BaseModel):
    """Una consulta DAX producida por el generador."""

    query_text: str = Field(..., description="El texto DAX, p. ej. 'EVALUATE SUMMARIZECOLUMNS(...)'")
    natural_language: str = Field(..., description="La pregunta original del usuario que originó la consulta")
    iteration: int = Field(default=0, description="Número de iteración del bucle en que se generó (0 = primer intento)")

    # Espacio para información extra que queramos adjuntar más adelante
    # (por ejemplo, qué herramientas MCP se consultaron, tiempo de generación, etc.).
    metadata: dict = Field(default_factory=dict, description="Metadatos libres para depuración/análisis")

    def is_empty(self) -> bool:
        """True si la consulta está vacía (el generador no produjo nada útil)."""
        return not self.query_text.strip()

    def starts_with_evaluate(self) -> bool:
        """
        Verificación rápida y barata: toda consulta DAX de tabla debe empezar
        con la palabra clave EVALUATE. Sirve como primer filtro antes incluso
        de llamar al validador de sintaxis.
        """
        return self.query_text.strip().upper().startswith("EVALUATE")
